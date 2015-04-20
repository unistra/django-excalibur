# -*- coding: utf-8 -*-
from django.test import TestCase
from .decorators import is_excalibur
from .middleware import ExcaliburMiddleware
from .exceptions import excalibur_exception_handler
from django.http import HttpRequest
from django.http import HttpResponse
from django.http import QueryDict
from rest_framework.request import Request
from rest_framework.response import Response
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from .models import Configuration
from django.core.exceptions import ValidationError
from .utils import ExcaliburAttack
from .models import ExcaliburConf
from excalibur.core import PluginsRunner
from mock import patch, Mock
import json
from django.conf import settings


ACL = """
proj:
    myetab:
        members:
            - method1
            - method2
            - method3
    myetab2:
        members:
            - method2
"""

RESSOURCES = """
members:
    method1:
        request method: GET
        arguments:
            id:
                checks:
                    min length: 1
                    max length: 50
            project:
                checks:
                    min length: 1
                    max length: 50
            establishment:
                checks:
                    min length: 1
                    max length: 50
            base_url:
                checks:
                    min length: 1
                    max length: 50

    method2:
        request method: GET
        arguments:
            id:
                checks:
                    min length: 1
                    max length: 50
            project:
                checks:
                    min length: 1
                    max length: 50
            establishment:
                checks:
                    min length: 1
                    max length: 50
            base_url:
                checks:
                    min length: 1
                    max length: 50

    method3:
        request method: GET
        arguments:
            id:
                checks:
                    min length: 1
                    max length: 50
            project:
                checks:
                    min length: 1
                    max length: 50
            establishment:
                checks:
                    min length: 1
                    max length: 50
            base_url:
                checks:
                    min length: 1
                    max length: 50
"""

SOURCES = """
proj:
     sources:
        myetab:
            plugins:

                Ldapuds:
                    -   spore: http://myurl/description.json
                        token: S3CR3T

                Apogee:
                    -   spore: http://myurl/description.json
                        token: S3CR3T

                Harpege:
                    -   spore: http://myurl/description.json
                        token: S3CR3T

        myetab2:
            plugins:

                Bnu:
                    -   spore: http://myurl/description.json
                        token: S3CR3T
"""


class DecoratorIsExcaliburTest(TestCase):

    """
    Decorator isExcalibur test
    """

    def setUp(self):
        # create a mock decorator
        self.function = Mock()
        self.function.__name__ = 'mock'
        self.decorated_function = is_excalibur(self.function)
        self.middleware = ExcaliburMiddleware()
        # create user with token
        self.user = User.objects.create(username="arthur")
        self.token = Token.objects.create(
            user=self.user,
            key=b'S3CR3T')
        # create a right request
        self.httprequest = HttpRequest()
        self.httprequest.method = "GET"
        self.httprequest.encoding = 'utf-8'
        self.httprequest.GET = QueryDict("project=proj&establishment=myetab")
        self.httprequest.REQUEST = self.httprequest.GET
        self.httprequest.META["HTTP_AUTHORIZATION"] = "Token " + \
            self.token.key.decode(encoding='UTF-8')
        self.httprequest.META['REQUEST_EXCALIBUR_PARAMS'] = {
            "ressource": "members",
            "method": "method2",
            "id": "32"
        }
        self.request = Request(self.httprequest)
        # create a right response
        self.httpresponse = HttpResponse()
        self.response = Response(self.httpresponse)
        self.response['Content-Type'] = 'application/json'
        self.response['encoding'] = 'utf-8'
        self.response.status_code = 200

    def test_ok(self):
        self.decorated_function(self.middleware, self.request, self.response)
        self.assertTrue(self.function.called)

    def test_wrong_status_code(self):
        self.response.status_code = 500
        self.decorated_function(self.middleware, self.request, self.response)
        self.assertFalse(self.function.called)

    def test_wrong_content_type(self):
        self.response['Content-Type'] = 'text/html'
        self.decorated_function(self.middleware, self.request, self.response)
        self.assertFalse(self.function.called)

    def test_wrong_method(self):
        self.httprequest.method = "POST"
        self.request = Request(self.httprequest)
        self.decorated_function(self.middleware, self.request, self.response)
        self.assertFalse(self.function.called)

    def test_wrong_args(self):
        self.httprequest.GET = QueryDict("error=error")
        self.httprequest.REQUEST = self.httprequest.GET
        self.request = Request(self.httprequest)
        self.decorated_function(self.middleware, self.request, self.response)
        self.assertFalse(self.function.called)

    def tearDown(self):
        self.function = None
        self.decorated_function = None
        self.request = None
        self.response = None


class ExceptionTest(TestCase):
    """
    test the custom exception of excalibur
    """

    def setUp(self):
        self.exception = Exception("FATAL ERROR")
        # create a right response
        self.httpresponse = HttpResponse()
        self.response = Response(self.httpresponse)
        self.response['Content-Type'] = 'application/json'
        self.response['encoding'] = 'utf-8'
        self.response.status_code = 200

    def test_exception_handler(self):
        response_err = excalibur_exception_handler(self.exception,
                                                   self.response)
        self.assertIsInstance(response_err, Response)
        self.assertEqual(response_err.status_code, 500)
        self.assertEqual(response_err.content.decode('utf-8'),
                         '{"error": "FATAL ERROR"}')


class ConfigurationModelTest(TestCase):
    """
    test for the configuration Model
    """

    def setUp(self):
        self.conf_acl = Configuration.objects.create(name="acl.yml",
                                                     configuration=ACL)
        self.conf_ressources = Configuration.objects.create(
            name="ressources.yml",
            configuration=RESSOURCES)
        self.conf_sources = Configuration.objects.create(
            name="sources.yml",
            configuration=SOURCES)

    def test_get(self):
        self.assertEqual(self.conf_acl,
                         Configuration.objects.get(name="acl.yml"))
        self.assertEqual(self.conf_ressources,
                         Configuration.objects.get(name="ressources.yml"))
        self.assertEqual(self.conf_sources,
                         Configuration.objects.get(name="sources.yml"))

    def test_yaml_error(self):
        with self.assertRaises(ValidationError):
            Configuration.objects.create(name="error.notayml",
                                         configuration="iamnoymal\t")

    def test_excalibur_conf(self):
        ExcaliburConf()
        self.assertIsNotNone(ExcaliburConf.instance)

    def tearDown(self):
        ExcaliburConf.removeInstance()


class ExcaliburAttackAndMiddlewareTest(TestCase):
    """
    test the excalbur attack class
    """

    plugin_mock1 = Mock()
    instance = plugin_mock1.return_value
    instance.members_method2.return_value = {"key1": "val1"}

    plugin_mock2 = Mock()
    instance = plugin_mock2.return_value
    instance.members_method2.return_value = {"key2": "val2"}

    plugin_mock3 = Mock()
    instance = plugin_mock3.return_value
    instance.members_method2.return_value = {"key3": "val3"}

    plugin_mock4 = Mock()
    instance = plugin_mock4.return_value
    instance.members_method2.return_value = ["item1", "item2"]

    plugin_mock5 = Mock()
    instance = plugin_mock5.return_value
    instance.members_method2.return_value = ["item3", "item4"]

    plugin_mock6 = Mock()
    instance = plugin_mock6.return_value
    instance.members_method2.return_value = ["item5", "item6"]

    plugin_mock7 = Mock()
    instance = plugin_mock7.return_value
    instance.members_method2.return_value = {"key11": "val11"}

    def raiseException(*args, **kwargs):
        raise Exception()
    plugin_mock8 = Mock()
    instance = plugin_mock8.return_value
    instance.members_method2 = raiseException

    def setUp(self):
        # create user with token
        self.user = User.objects.create(username="arthur")
        self.token = Token.objects.create(
            user=self.user,
            key=b'S3CR3T')
        # create a right request
        self.httprequest = HttpRequest()
        self.httprequest.path = "/warehouse/members/method2/32.json?\
project=sigb&establishment=uds"
        self.httprequest.method = "GET"
        self.httprequest.encoding = 'utf-8'
        self.httprequest.GET = QueryDict("project=proj&establishment=myetab")
        self.httprequest.REQUEST = self.httprequest.GET
        self.httprequest.META["REMOTE_ADDR"] = "127.0.0.1"
        self.httprequest.META["HTTP_AUTHORIZATION"] = "Token " + \
            self.token.key.decode(encoding='UTF-8')
        self.httprequest.META['SERVER_NAME'] = "myserverurl.com"
        self.httprequest.META['SERVER_PORT'] = 80
        self.httprequest.META['REQUEST_EXCALIBUR_PARAMS'] = {
            "ressource": "members",
            "method": "method2",
            "id": "32"
        }
        self.request = Request(self.httprequest)
        # create a right response
        self.httpresponse = HttpResponse()
        self.response = Response(self.httpresponse)
        self.response['Content-Type'] = 'application/json'
        self.response['encoding'] = 'utf-8'
        self.response.status_code = 200
        self.response.content = '{"key1":"prioritary","name":"toto","age":18}'
        # conf
        self.conf_acl = Configuration.objects.create(name="acl.yml",
                                                     configuration=ACL)
        self.conf_ressources = Configuration.objects.create(
            name="ressources.yml",
            configuration=RESSOURCES)
        self.conf_sources = Configuration.objects.create(
            name="sources.yml",
            configuration=SOURCES)
        self.attack = ExcaliburAttack(self.request, self.response)
        self.middleware = ExcaliburMiddleware()
        # Excalibur Conf
        self.excconf = ExcaliburConf()

    def test_attack_ok(self):
        self.assertEqual(self.attack.request, self.request)
        self.assertEqual(self.attack.response, self.response)
        self.assertEqual(
            self.attack.arguments,
            {'project': 'proj', 'establishment': 'myetab', 'id': '32',
             'base_url': 'http://myserverurl.com'})
        self.assertEqual(self.attack.ressource, "members")
        self.assertEqual(self.attack.token, self.token.key.decode('utf-8'))
        self.assertEqual(self.attack.remote_ip, "127.0.0.1")
        self.assertEqual(self.attack.request_method, "GET")
        self.assertEqual(self.attack.project, "proj")
        self.assertEqual(self.attack.source, "myetab")
        self.assertEqual(self.attack.data, {'key1': 'prioritary',
                                            'age': 18, 'name': 'toto'})
        self.assertEqual(self.attack.method, "method2")
        self.assertEqual(self.attack.signature,
                         "d7b3487b278d076467a1482eeb6432980a0e49e8")

    @patch('%s.Harpege.Harpege' % settings.EXCALIBUR_PLUGINS_MODULE, plugin_mock1)
    @patch('%s.Apogee.Apogee' % settings.EXCALIBUR_PLUGINS_MODULE, plugin_mock2)
    @patch('%s.Ldapuds.Ldapuds' % settings.EXCALIBUR_PLUGINS_MODULE, plugin_mock3)
    def test_make_and_run_query(self):

        plugin_runner = PluginsRunner(
            self.excconf.acl_conf.configuration,
            self.excconf.sources_conf.configuration,
            self.excconf.ressource_conf.configuration,
            self.excconf.plugins_module,
            raw_yaml_content=True
        )

        newdata, errors = self.attack.make_and_run_query(plugin_runner)

        self.assertEqual(errors, {})
        self.assertEqual(
            newdata,
            {'Harpege': {'key1': 'val1'}, 'Ldapuds': {'key3': 'val3'},
             'Apogee': {'key2': 'val2'}})

    @patch('%s.Harpege.Harpege' % settings.EXCALIBUR_PLUGINS_MODULE, plugin_mock8)
    @patch('%s.Apogee.Apogee' % settings.EXCALIBUR_PLUGINS_MODULE, plugin_mock8)
    @patch('%s.Ldapuds.Ldapuds' % settings.EXCALIBUR_PLUGINS_MODULE, plugin_mock8)
    def test_manage_errors(self):

        plugin_runner = PluginsRunner(
            self.excconf.acl_conf.configuration,
            self.excconf.sources_conf.configuration,
            self.excconf.ressource_conf.configuration,
            self.excconf.plugins_module,
            raw_yaml_content=True
        )

        newdata, errors = self.attack.make_and_run_query(plugin_runner)

        self.assertEqual(newdata, {})
        self.assertTrue(errors)

    @patch('%s.Harpege.Harpege' % settings.EXCALIBUR_PLUGINS_MODULE, plugin_mock1)
    @patch('%s.Apogee.Apogee' % settings.EXCALIBUR_PLUGINS_MODULE, plugin_mock2)
    @patch('%s.Ldapuds.Ldapuds' % settings.EXCALIBUR_PLUGINS_MODULE, plugin_mock3)
    def test_aggregate_data_dict_dict(self):

        plugin_runner = PluginsRunner(
            self.excconf.acl_conf.configuration,
            self.excconf.sources_conf.configuration,
            self.excconf.ressource_conf.configuration,
            self.excconf.plugins_module,
            raw_yaml_content=True
        )

        newdata, errors = self.attack.make_and_run_query(plugin_runner)

        response = self.attack.aggregate_data(newdata)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            json.loads(response.content.decode('utf-8')),
            {"key3": "val3", "key2": "val2", "age": 18,
             "name": "toto", "key1": "prioritary"})

    @patch('%s.Harpege.Harpege' % settings.EXCALIBUR_PLUGINS_MODULE, plugin_mock1)
    @patch('%s.Apogee.Apogee' % settings.EXCALIBUR_PLUGINS_MODULE, plugin_mock2)
    @patch('%s.Ldapuds.Ldapuds' % settings.EXCALIBUR_PLUGINS_MODULE, plugin_mock3)
    def test_aggregate_data_with_404(self):
        self.response.status_code = 404
        self.response.content = '{"error":"404 not found"}'
        self.attack = ExcaliburAttack(self.request, self.response)

        plugin_runner = PluginsRunner(
            self.excconf.acl_conf.configuration,
            self.excconf.sources_conf.configuration,
            self.excconf.ressource_conf.configuration,
            self.excconf.plugins_module,
            raw_yaml_content=True
        )

        newdata, errors = self.attack.make_and_run_query(plugin_runner)

        response = self.attack.aggregate_data(newdata)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            json.loads(response.content.decode('utf-8')),
            {"key3": "val3", "key2": "val2", "key1": "val1"})

    @patch('%s.Harpege.Harpege' % settings.EXCALIBUR_PLUGINS_MODULE, plugin_mock1)
    @patch('%s.Apogee.Apogee' % settings.EXCALIBUR_PLUGINS_MODULE, plugin_mock2)
    @patch('%s.Ldapuds.Ldapuds' % settings.EXCALIBUR_PLUGINS_MODULE, plugin_mock3)
    def test_aggregate_data_with_list_dict(self):
        self.response.content = '["item1", "item2"]'
        self.attack = ExcaliburAttack(self.request, self.response)


        plugin_runner = PluginsRunner(
            self.excconf.acl_conf.configuration,
            self.excconf.sources_conf.configuration,
            self.excconf.ressource_conf.configuration,
            self.excconf.plugins_module,
            raw_yaml_content=True
        )

        newdata, errors = self.attack.make_and_run_query(plugin_runner)

        response = self.attack.aggregate_data(newdata)
        self.assertEqual(response.status_code, 200)
#         self.assertEqual(
#             json.loads(response.content.decode('utf-8')),
#             ['item1', 'item2', {'key1': 'val1'}, {'key3': 'val3'},
#                                {'key2': 'val2'}])
        items = ['item1', 'item2', {'key1': 'val1'}, {'key3': 'val3'},
                               {'key2': 'val2'}]
        loaded_json = json.loads(response.content.decode('utf-8'))
        not_found = lambda x : x[0] not in x[1]
        not_found_list = [thing for thing in items \
                          if not_found([thing,loaded_json])]
        self.assertEqual([],not_found_list) 

    @patch('%s.Harpege.Harpege' % settings.EXCALIBUR_PLUGINS_MODULE, plugin_mock4)
    @patch('%s.Apogee.Apogee' % settings.EXCALIBUR_PLUGINS_MODULE, plugin_mock5)
    @patch('%s.Ldapuds.Ldapuds' % settings.EXCALIBUR_PLUGINS_MODULE, plugin_mock6)
    def test_aggregate_data_with_list_list(self):
        self.response.content = '["item99", "item98"]'
        self.attack = ExcaliburAttack(self.request, self.response)


        plugin_runner = PluginsRunner(
            self.excconf.acl_conf.configuration,
            self.excconf.sources_conf.configuration,
            self.excconf.ressource_conf.configuration,
            self.excconf.plugins_module,
            raw_yaml_content=True
        )

        newdata, errors = self.attack.make_and_run_query(plugin_runner)

        response = self.attack.aggregate_data(newdata)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            json.loads(response.content.decode('utf-8')).sort(),
            ["item99", "item98", "item1", "item2", "item5", "item6",
             "item3", "item4"].sort())

    @patch('%s.Harpege.Harpege' % settings.EXCALIBUR_PLUGINS_MODULE, plugin_mock4)
    @patch('%s.Apogee.Apogee' % settings.EXCALIBUR_PLUGINS_MODULE, plugin_mock5)
    @patch('%s.Ldapuds.Ldapuds' % settings.EXCALIBUR_PLUGINS_MODULE, plugin_mock6)
    def test_aggregate_data_with_dict_list(self):
        self.attack = ExcaliburAttack(self.request, self.response)

        plugin_runner = PluginsRunner(
            self.excconf.acl_conf.configuration,
            self.excconf.sources_conf.configuration,
            self.excconf.ressource_conf.configuration,
            self.excconf.plugins_module,
            raw_yaml_content=True
        )

        newdata, errors = self.attack.make_and_run_query(plugin_runner)

        response = self.attack.aggregate_data(newdata)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            json.loads(response.content.decode('utf-8')),
            {'name': 'toto', 'age': 18, 'Apogee': ['item3', 'item4'],
             'Harpege': ['item1', 'item2'], 'Ldapuds': ['item5', 'item6'],
             'key1': 'prioritary'})

    @patch('%s.Harpege.Harpege' % settings.EXCALIBUR_PLUGINS_MODULE, plugin_mock1)
    @patch('%s.Apogee.Apogee' % settings.EXCALIBUR_PLUGINS_MODULE, plugin_mock2)
    @patch('%s.Ldapuds.Ldapuds' % settings.EXCALIBUR_PLUGINS_MODULE, plugin_mock3)
    def test_middleware_no_is_excalbur(self):
        self.response['Content-Type'] = 'text/html'
        response = self.middleware.process_response(self.request,
                                                    self.response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            json.loads(response.content.decode('utf-8')),
            {"key1": "prioritary", "name": "toto", "age": 18})

    @patch('%s.Harpege.Harpege' % settings.EXCALIBUR_PLUGINS_MODULE, plugin_mock8)
    @patch('%s.Apogee.Apogee' % settings.EXCALIBUR_PLUGINS_MODULE, plugin_mock8)
    @patch('%s.Ldapuds.Ldapuds' % settings.EXCALIBUR_PLUGINS_MODULE, plugin_mock8)
    def test_middleware_with_errors(self):
        response = self.middleware.process_response(self.request,
                                                    self.response)
        self.assertEqual(response.status_code, 500)
        self.assertTrue('error' in json.loads(
            response.content.decode('utf-8')).keys())

    @patch('%s.Harpege.Harpege' % settings.EXCALIBUR_PLUGINS_MODULE, plugin_mock1)
    @patch('%s.Apogee.Apogee' % settings.EXCALIBUR_PLUGINS_MODULE, plugin_mock2)
    @patch('%s.Ldapuds.Ldapuds' % settings.EXCALIBUR_PLUGINS_MODULE, plugin_mock3)
    def test_middleware_one_establishement(self):
        response = self.middleware.process_response(self.request,
                                                    self.response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            json.loads(response.content.decode('utf-8')),
            {"key3": "val3", "age": 18, "key1": "prioritary",
             "name": "toto", "key2": "val2"})

    @patch('%s.Harpege.Harpege' % settings.EXCALIBUR_PLUGINS_MODULE, plugin_mock1)
    @patch('%s.Apogee.Apogee' % settings.EXCALIBUR_PLUGINS_MODULE, plugin_mock2)
    @patch('%s.Ldapuds.Ldapuds' % settings.EXCALIBUR_PLUGINS_MODULE, plugin_mock3)
    @patch('%s.Bnu.Bnu' % settings.EXCALIBUR_PLUGINS_MODULE, plugin_mock7)
    def test_middleware_all_establishement(self):
        self.httprequest.GET = QueryDict("project=proj&establishment=all")
        self.httprequest.REQUEST = self.httprequest.GET
        response = self.middleware.process_response(self.request,
                                                    self.response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            json.loads(response.content.decode('utf-8')),
            {"name": "toto", "key3": "val3", "key2": "val2",
             "age": 18, "key1": "prioritary", "key11": "val11"})

    @patch('%s.Harpege.Harpege' % settings.EXCALIBUR_PLUGINS_MODULE, plugin_mock1)
    @patch('%s.Apogee.Apogee' % settings.EXCALIBUR_PLUGINS_MODULE, plugin_mock2)
    @patch('%s.Ldapuds.Ldapuds' % settings.EXCALIBUR_PLUGINS_MODULE, plugin_mock3)
    def test_middleware_wrong_auth(self):
        self.response.status_code = 404
        self.response.content = "{\"error\": \"not found\"}"
        self.request.META["HTTP_AUTHORIZATION"] = "Token ERROR"
        response = self.middleware.process_response(self.request,
                                                    self.response)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(json.loads(response.content.decode('utf-8')),
                         {"error": "not found"})

    @patch('%s.Harpege.Harpege' % settings.EXCALIBUR_PLUGINS_MODULE, plugin_mock1)
    @patch('%s.Apogee.Apogee' % settings.EXCALIBUR_PLUGINS_MODULE, plugin_mock2)
    @patch('%s.Ldapuds.Ldapuds' % settings.EXCALIBUR_PLUGINS_MODULE, plugin_mock3)
    def test_middleware_no_auth(self):
        self.response.status_code = 404
        self.response.content = "{\"error\": \"not found\"}"
        self.request.META.pop("HTTP_AUTHORIZATION", None)
        response = self.middleware.process_response(self.request,
                                                    self.response)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(json.loads(response.content.decode('utf-8')),
                         {"error": "not found"})

    def tearDown(self):
        ExcaliburConf.removeInstance()
