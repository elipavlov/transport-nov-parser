"""
Django settings for tn_parser project.

Generated by 'django-admin startproject' using Django 1.10.5.

For more information on this file, see
https://docs.djangoproject.com/en/1.10/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.10/ref/settings/
"""

import os
import sys
import re

import environ

from .. import __version__ as version


root = environ.Path(os.getcwd())
env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(root('.env'))

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = root()
SITE_ROOT = root()

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env('DEBUG')

BASE_URL = env('BASE_URL')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS')

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'tn_parser.transport',

    'raven.contrib.django.raven_compat',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


ROOT_URLCONF = 'tn_parser.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'tn_parser.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.8/ref/settings/#databases

DATABASES = {
    'default': env.db(),
}

if DATABASES['default']['ENGINE'] == 'django.db.backends.mysql':
    DATABASES['default']['CHARSET'] = 'utf8'
    DATABASES['default']['OPTIONS'] = {
        'init_command': 'SET default_storage_engine=MyISAM; '
                        # 'SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED; '
                        'SET foreign_key_checks = 0; '
                        'SET character_set_connection=utf8; '
                        'SET collation_connection=utf8_general_ci;'
                        'SET sql_mode="STRICT_TRANS_TABLES";',
    }

DEFAULT_CHARSET = 'utf-8'

# emailing
EMAIL_CONFIG = env.email_url(
    'EMAIL_URL', default='console://')

vars().update(EMAIL_CONFIG)

DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL')


def parse_admins(adm):
    res = []
    for grp in adm.split(','):
        grp = re.match('^\s*([\w\.]+)\s*<(.+)>\s*$', grp)
        try:
            res.append((grp.group(1), grp.group(2)))
        except AttributeError:
            pass

    return res

ADMINS = env('ADMINS', cast=parse_admins, default=[])
MANAGERS = env('MANAGERS', cast=parse_admins, default=[])

# Password validation
# https://docs.djangoproject.com/en/1.10/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

if DEBUG:
    AUTH_PASSWORD_VALIDATORS = []


# Internationalization
# https://docs.djangoproject.com/en/1.10/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.10/howto/static-files/

STATIC_URL = '/static/'


# Logging
LOGLEVEL = 'DEBUG' if DEBUG else 'ERROR'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(message)s'  # %(thread)d
        },
        'simple': {
            'format': '%(levelname)s %(message)s',
             'datefmt': '%y %b %d, %H:%M:%S',
        },
        "custom_console": {
            "format": "%(asctime)s %(levelname)s %(message)s",
            "datefmt": "%H:%M:%S",
        },
    },
    'handlers': {
        'sentry': {
            'level': 'ERROR',  # To capture more than ERROR, change to WARNING, INFO, etc.
            'class': 'raven.contrib.django.raven_compat.handlers.SentryHandler',
            'tags': {'custom-tag': 'x'},
        },
        'console': {
            'level': LOGLEVEL,
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
            'stream': sys.stdout,
        },
    },

    'loggers': {
        'root': {
            'level': LOGLEVEL,
            'handlers': ['sentry'],
        },
        'django.request': {
            'level': LOGLEVEL,
            'handlers': ['console'],
            'propagate': True,
        },
        'django.server': {
            'level': LOGLEVEL,
            'handlers': ['console'],
            'propagate': True,
        },
        'tn_parser': {
            'level': LOGLEVEL,
            'handlers': ['console'],
            # 'propagate': True,
        },
        # 'celery': {
        #     'level': 'WARNING',
        #     'handlers': ['console'],
        # },
        'raven': {
            'level': 'DEBUG',
            'handlers': ['console', 'sentry'],
            'propagate': False,
        },
        'sentry.errors': {
            'level': 'DEBUG',
            'handlers': ['console'],
            'propagate': False,
        },
    },
}


# raven / sentry config

RAVEN_CONFIG = {
    'dsn': env('RAVEN_DSN', default=''),
    'release': version,
}
