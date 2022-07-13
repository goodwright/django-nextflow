from pathlib import Path
import sys
sys.path.append("../..")

BASE_DIR = Path(__file__).resolve().parent
SECRET_KEY = "$$$"
DEBUG = True
ALLOWED_HOSTS = []

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django_nextflow"
]

MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = __name__
urlpatterns = []

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:"
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"