from dotenv import load_dotenv
load_dotenv()
from .base import *
import logging
import logging.handlers
import os
from pathlib import Path


ALLOWED_HOSTS = ["*"]

DATABASES = {
    'default': {
        'ENGINE': os.getenv("ENGINE"),
        'NAME': os.getenv("NAME"),
        'USER': os.getenv("USER"),
        'PASSWORD': os.getenv("DB_PASSWORD"),
        'HOST': os.getenv("HOST"),
        'PORT': os.getenv("PORT"),
    }
}

# email
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_USE_SSL = True
EMAIL_USE_TSL = False
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 465
EMAIL_HOST_USER = os.getenv("EMAIL")
EMAIL_HOST_PASSWORD = os.getenv("PASSWORD")
DEFAULT_FROM_EMAIL = os.getenv("EMAIL")

# Ensure the logs/ directory exists
LOG_DIR = os.path.join(BASE_DIR, "logs")

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "debug_file": {
            "level": "DEBUG",
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": os.path.join(LOG_DIR, "debug.log"),
            "when": "midnight",
            "interval": 1,
            "backupCount": 7,
            "formatter": "verbose",
        },
        "error_file": {
            "level": "ERROR",
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": os.path.join(LOG_DIR, "errors.log"),
            "when": "midnight",
            "interval": 1,
            "backupCount": 7,
            "formatter": "verbose",
        },
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["debug_file", "error_file", "console"],
            "level": "DEBUG",
            "propagate": True,
        },
    },
}
