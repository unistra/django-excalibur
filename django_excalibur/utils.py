# -*- coding: utf-8 -*-
import hashlib
import json
from excalibur.core import Query
from excalibur.exceptions import ExcaliburError
import logging
from .exceptions import excalibur_exception_handler
from rest_framework.authtoken.models import Token
from django.core.exceptions import ObjectDoesNotExist
from britney.errors import SporeMethodStatusError, SporeMethodCallError
from britney.middleware import auth
import britney_utils
from rest_framework.reverse import reverse
from django.core.urlresolvers import NoReverseMatch


"""
Tools for the excalibur middleware

"""

logger = logging.getLogger(__name__)


class ExcaliburAttack():

    """
    params for excalibur
    """

    def __init__(self, request, response):
        # base attribute
        self.request = request
        self.response = response
        # secondary attribute (use request and response)
        self.arguments = self.__arguments()
        self.ressource = self.__ressource()
        self.token = self.__token()
        self.remote_ip = self.__remote_ip()
        self.request_method = self.__request_method()
        self.project = self.__project()
        self.source = self.__source()
        self.data = self.__data()
        self.method = self.__method()
        # signature needs all other params to be set
        self.signature = self.__signature()

    def __arguments(self):
        """ get arguments id from the path """
        try:
            arguments = {}
            arguments["id"] = self. __find_id()
            arguments["project"] = self.__project()
            arguments["establishment"] = self.__source()
            arguments["base_url"] = self.__find_base_url()
            arguments.update(self.__optionnal_args())
        except IndexError:
            return None

        return arguments

    def __find_base_url(self):
        return '%s://%s' % \
                ('https' if self.request.is_secure() else 'http',
                 self.request.get_host())

    def __find_id(self):
        return self.request.META["REQUEST_EXCALIBUR_PARAMS"]["id"]

    def __ressource(self):
        """ get the ressource from the path """
        try:
            return self.request.META["REQUEST_EXCALIBUR_PARAMS"]["ressource"]
        except KeyError:
            return None

    def __method(self):
        """ get the method from the path """
        try:
            return self.request.META["REQUEST_EXCALIBUR_PARAMS"]["method"]
        except KeyError:
            return None

    def __token(self):
        """ get the token from the request header """
        token = self.request.META["HTTP_AUTHORIZATION"].split(' ')[-1] \
            if "HTTP_AUTHORIZATION" in self.request.META.keys() else None
        return token

    def __remote_ip(self):
        """ get remote ip from the request """
        remote_ip = self.request.META[
            'HTTP_X_REAL_IP'] if 'HTTP_X_REAL_IP' in self.request.META \
            else self.request.META['REMOTE_ADDR']
        return remote_ip

    def __request_method(self):
        """ get the request method """
        return self.request.method

    def __project(self):
        """ get the project from the request args """
        return self.request.REQUEST['project']

    def __source(self):
        """ get the source from the request args """
        return self.request.REQUEST['establishment']

    def __optionnal_args(self):
        "get all other args"
        return {k:v for k,v in self.request.REQUEST.items()
                if k not in ['project','establishment']}

    def __data(self):
        """ load data from responce content """
        return json.loads(str(self.response.content, 'utf-8'))

    def __signature(self):
        """ build the excalibur signature with the user's token """
        signkey = None
        if self.token:
            arguments_list = sorted(self.arguments)
            to_hash = self.token
            for argument in arguments_list:
                to_hash += (argument + self.arguments[argument])
            signkey = hashlib.sha1(to_hash.encode("utf-8")).hexdigest()

        return signkey

    def make_and_run_query(self, plugin_runner, etab=None):
        """
        make and run the query depending on etab
        """
        # create the query
        query = Query(
            source=etab if etab else self.source,
            remote_ip=self.remote_ip,
            arguments=self.arguments,
            ressource=self.ressource,
            method=self.method,
            request_method=self.request_method,
            project=self.project,
            signature=self.signature
        )

        newdata, errors = plugin_runner(query)

        return newdata, errors

    def manage_errors(self, errors):
        """ manage errors """
        # log each plugin's errors
        for plugin_name, err_par in errors.items():
            myerror = "error: %s:%s, plugin name: %s, source: %s, \
        ressource: %s, method: %s, arguments: %s, parameters index: %s" % (
                err_par['error'],
                err_par['error_message'],
                plugin_name,
                err_par['source'],
                err_par['ressource'],
                err_par['method'],
                err_par['arguments'],
                err_par['parameters_index'])

            logger.warning(myerror)

        return excalibur_exception_handler(ExcaliburError(myerror),
                                           self.response)

    def aggregate_data(self, newdata):
        """
        Aggregate plugins data to camelot data.
        Priority for the referentiel data, except if the data is null,empty...
        """
        if newdata:

            # aggregate in a dictionnary
            if isinstance(self.data, dict):

                # Remove not found message of referentiel if 404
                if self.response.status_code == 404:
                    self.response.status_code = 200
                    if 'error' in self.data:
                        del self.data['error']

                # Aggregate data if not exists
                for key, values in newdata.items():
                    # update the new dict with data from referentiel
                    if isinstance(values, dict):
                        self.data.update(
                            {k: v for k, v in values.items(
                            ) if k not in self.data.keys()}
                        )
                    # if its a list or other, just add a new key named
                    # like the plugin
                    else:
                        self.data.update({key: values})

            # aggregate in a list
            elif isinstance(self.data, list):
                for values in newdata.values():
                    # if the plugin return a list, merge the two lists
                    if isinstance(values, list):
                        self.data += values
                    # if the plugin return something else, just append
                    else:
                        self.data.append(values)

        self.response.content = json.dumps(self.data)

        return self.response

    def get_request_user(self):
        """
        get the user from the request
        """
        user = None
        token = self.request.META["HTTP_AUTHORIZATION"].split(' ')[-1] \
            if "HTTP_AUTHORIZATION" in self.request.META.keys() else None

        if token:
            try:
                token = Token.objects.get(key=token)
                if token.user:
                    user = token.user
            except ObjectDoesNotExist:
                user = None

        return user


def generate_client_and_get_data(spore, token, method_name, method_args):
    """
    Generate a britney client and get data from method
    """

    client_name = hashlib.sha1(('%s%s' % (spore, token)).encode('utf-8')).hexdigest()
    data = None

    try:
        middlewares = (
            (auth.ApiKey, {'key_name': 'Authorization',
             'key_value': 'Token %s' % (token,)}),
        )

        client = britney_utils.get_client(client_name,
                                          spore,
                                          middlewares=middlewares)

        func = getattr(client, method_name)
        user = func(**method_args)
        data = json.loads(user.text)

    except SporeMethodStatusError:
        raise
    except SporeMethodCallError:
        raise
    else:
        return data


def build_route_updates_data(users_list, project, establishment, member_label, member_code_key, base_url, reverse_name):
    """
    build the updates route
    """

    res_list = []

    try:

        for result in users_list:

            url_reverse = reverse("%s" % reverse_name,
                                  kwargs={'memberskey': member_label,
                                          'memberscode': result[member_code_key]},
                                  format='json', request=None)

            url_args = "?establishment=%s&project=%s" % (establishment,
                                                         project)
            url = "%s%s%s" % (base_url, url_reverse, url_args)

            res_list.append({'project': project,
                             'establishment': establishment,
                             'source': member_label, 'code': result[member_code_key],
                             'url': url})
    except SporeMethodStatusError:
        raise
    except SporeMethodCallError:
        raise
    except KeyError as e:
        logger.critical(str(e))
    except NoReverseMatch as e:
        logger.critical(str(e))

    return res_list
