import os

SECRET_KEY = os.getenv('SECRET_KEY', '!INSECURE!')

PROJECT_PATH = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
INSTALLED_APPS = [
    'django.contrib',
    'drf_jsonapi',
    'tests',
]
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(PROJECT_PATH, 'drf_jsonapi.sqlite'),
    }
}
REST_FRAMEWORK = {'EXCEPTION_HANDLER': 'drf_jsonapi.exception_handlers.jsonapi_exception_handler'}
DEFAULT_PAGE_SIZE = 10
BASE_URL = 'junk'
ROOT_URLCONF = 'tests.urls'
TIME_ZONE = 'UTC'
