from django.db import models
import yaml
from django.core.exceptions import ValidationError
from django.conf import settings


class Configuration(models.Model):
    """
    yaml configuration in database
    """
    name = models.CharField(max_length=53, unique=True)
    configuration = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        try:
            yaml.load(self.configuration)
        except Exception as e:
            raise ValidationError(e)
        else:
            super(Configuration, self).save(*args, **kwargs)
            # reinitialize the excalbur conf singleton
            ExcaliburConf.removeInstance()

    class Meta:
        db_table = 'excalibur_configuration'


class ExcaliburConf():

    """
    load the configuration from database
    """

    instance = None

    class __ExcaliburConf:

        def __init__(self):
            self.sources_conf = Configuration.objects.get(
                name=settings.EXCALIBUR_SOURCES)
            self.ressource_conf = Configuration.objects.get(
                name=settings.EXCALIBUR_RESSOURCES)
            self.acl_conf = Configuration.objects.get(
                name=settings.EXCALIBUR_ACL)
            self.plugins_module = settings.EXCALIBUR_PLUGINS_MODULE

    def __new__(cls):
        if not ExcaliburConf.instance:
            ExcaliburConf.instance = ExcaliburConf.__ExcaliburConf()
        return ExcaliburConf.instance

    def __getattr__(self, name):
        return getattr(self.instance, name)

    def __setattr__(self, name):
        return setattr(self.instance, name)

    @staticmethod
    def removeInstance():
        ExcaliburConf.instance = None