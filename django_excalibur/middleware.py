# -*- coding: utf-8 -*-
from excalibur.core import PluginsRunner
from excalibur.exceptions import ConfigurationLoaderError, ExcaliburError
import logging
from .decorators import is_excalibur
from .models import ExcaliburConf
from .utils import ExcaliburAttack
from .exceptions import excalibur_exception_handler
from django.core.exceptions import ObjectDoesNotExist

logger = logging.getLogger(__name__)


class ExcaliburMiddleware(object):

    """ The excalibur middleware """

    @is_excalibur
    def process_response(self, request, response):
        """
            use excalibur when optional "project" and "source" params
            are in the url
        """
        try:
            # get all params for query
            excalibur = ExcaliburAttack(request, response)
            # get user
            user = excalibur.get_request_user()

            if user:
                try:
                    excconf = ExcaliburConf()
                except (AttributeError, ObjectDoesNotExist) as e:
                    raise ConfigurationLoaderError(str(e))

                # run plugins
                plugin_runner = PluginsRunner(
                    excconf.acl_conf.configuration,
                    excconf.sources_conf.configuration,
                    excconf.ressource_conf.configuration,
                    excconf.plugins_module,
                    raw_yaml_content=True,
                    check_signature=False if user.is_superuser else True
                )

                newdata, errors = excalibur.make_and_run_query(plugin_runner)
                if not errors:
                    response = excalibur.aggregate_data(newdata)
                else:
                    response = excalibur.manage_errors(errors)

        except ExcaliburError as e:
            logger.error(e.message)
            response = excalibur_exception_handler(e, response)

        return response
