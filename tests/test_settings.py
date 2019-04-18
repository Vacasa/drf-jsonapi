import os

SECRET_KEY = os.getenv("SECRET_KEY", "!INSECURE!")

DEBUG = True

PROJECT_PATH = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
INSTALLED_APPS = [
    "django.contrib",
    "drf_jsonapi",
    "tests",
    "tests.nested_includes",
    "tests.relationship_handlers",
]
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(PROJECT_PATH, "drf_jsonapi.sqlite"),
    }
}
SWAGGER_SETTINGS = {
    "DEFAULT_AUTO_SCHEMA_CLASS": "drf_jsonapi.inspectors.EntitySwaggerAutoSchema",
    "SECURITY_DEFINITIONS": {
        "Bearer": {"type": "apiKey", "name": "Authorization", "in": "header"}
    },
}
DEFAULT_PAGE_SIZE = 10
BASE_URL = "junk"
ROOT_URLCONF = "tests.urls"
TIME_ZONE = "UTC"
