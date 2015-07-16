import os
import sys
from django.conf import settings
from django.conf.urls import patterns
from django.http import HttpResponse

me = os.path.splitext(os.path.split(__file__)[1])[0]
here = lambda x: os.path.join(os.path.abspath(os.path.dirname(__file__)), x)

DEBUG = True
ROOT_URLCONF = me
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': 'test_ex.db'}}     
TEMPLATE_DIRS = (here('.'), )
SECRET_KEY = 'so so secret'
REST_FRAMEWORK = {                                                              
    'DEFAULT_FILTER_BACKENDS': (                                                
        'rest_framework.filters.DjangoFilterBackend',                           
        'rest_framework_fine_permissions.filters.FilterPermissionBackend'       
    ),                                                                          
    'DEFAULT_AUTHENTICATION_CLASSES': (                                         
        'rest_framework.authentication.TokenAuthentication',                    
    ),                                                                          
    'DEFAULT_PERMISSION_CLASSES': (                                             
        'rest_framework_fine_permissions.permissions.FullDjangoModelPermissions',
        'camelot.apps.person.permissions.SourceMemberPermission',               
    ),                                                                          
    'EXCEPTION_HANDLER': 'rest_framework_custom_exceptions.exceptions.simple_error_handler',
    'DEFAULT_PAGINATION_SERIALIZER_CLASS': 'rest_framework_custom_paginations.paginations.SporePaginationSerializer'
}
EXCALIBUR_SOURCES = "sources.yml"                                               
EXCALIBUR_RESSOURCES = "ressources.yml"                                         
EXCALIBUR_ACL = "acl.yml"                                                       
EXCALIBUR_PLUGINS_MODULE = "django_excalibur.tests.plugins"
INSTALLED_APPS = ( 'django.contrib.auth', 'django.contrib.contenttypes',    
    'django.contrib.sessions', 'django.contrib.sites', 'django.contrib.messages',    
    'django.contrib.staticfiles', 'rest_framework', 'rest_framework.authtoken',    
    'django_excalibur'
)

if not settings.configured:
    settings.configure(**locals())

from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def index(request):
    return HttpResponse("Hello from django excalibur test")

urlpatterns = patterns('', (r'^$', index))

if __name__ == '__main__':
    sys.path += (here('.'),)
    from django.core import management
    management.execute_from_command_line()
