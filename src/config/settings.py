import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR.parent / ".env")

SECRET_KEY = os.environ.get("SECRET_KEY")
DEBUG = os.environ.get("DEBUG", "False").lower() in ("true", "1", "t")

# --- CHỈNH SỬA DUY NHẤT Ở ĐÂY ---
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "django_web"]

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.uploads",
    "apps.ai_processing.apps.AiProcessingConfig",
    'rest_framework',
    'corsheaders',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

CORS_ALLOW_ALL_ORIGINS = True

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB"),
        "USER": os.environ.get("POSTGRES_USER"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD"),
        "HOST": os.environ.get("DB_HOST"),
        "PORT": os.environ.get("DB_PORT"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,  # giữ lại log mặc định của Django
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name}:{lineno} - {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",   # hiển thị tất cả log >= DEBUG
            "class": "logging.StreamHandler",
            "formatter": "verbose",  # hoặc "simple"
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "DEBUG",  # cho phép tất cả log hiển thị
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",   # log của Django core
            "propagate": False,
        },
        "apps.ai_processing": {   # app bạn muốn log (ví dụ services.py trong app ai_processing)
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

CELERY_BROKER_URL = "redis://redis:6379/0"
CELERY_RESULT_BACKEND = "redis://redis:6379/0"
CELERY_ACCEPT_CONTENT = ["json", "pickle"]
CELERY_TASK_SERIALIZER = "pickle"
CELERY_RESULT_SERIALIZER = "pickle"

MEDIA_URL = "/media/"
MEDIA_ROOT = os.environ.get("MEDIA_ROOT", os.path.join(BASE_DIR, "mediafiles"))

# STATIC
STATIC_URL = "/static/"
STATIC_ROOT = os.environ.get("STATIC_ROOT", os.path.join(BASE_DIR, "staticfiles"))

# Auto field
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"