"""
Django settings for fashbowl project.

Generated by 'django-admin startproject' using Django 2

For more information on this file, see
https://docs.djangoproject.com/en/dev/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/dev/ref/settings/
"""

import os

import dj_database_url
# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
from os.path import join

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = BASE_DIR

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/dev/howto/deployment/checklist/

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', '').lower() == 'true'
print("Debug:", DEBUG, type(DEBUG))
# SECURITY WARNING: keep the secret key used in production secret!
if DEBUG is False:
    SECRET_KEY = os.environ.get('SECRET_KEY',
                                "asne4zs=zy!cotslx96-j-$4yy0hz87rqh44+rwih$_e6jq7h+fafd")
else:
    SECRET_KEY = 'asdfjkl;'
# Application definition

INSTALLED_APPS = [
    'whitenoise.runserver_nostatic',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Apps
    'core',

    # 3rd party
    'rest_framework',
    'channels',
    'django_extensions',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'fashbowl.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [join(BASE_DIR, 'fashbowl', 'templates')],
        # 'DIRS': [],
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

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/dev/howto/static-files/

# http://whitenoise.evans.io/en/stable/
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
#STATICFILES_DIRS = (os.path.join(BASE_DIR, 'static'), )
# STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.0/howto/static-files/

STATIC_URL = '/static/'

# if DEBUG is False:
#     STATIC_ROOT = os.path.join(BASE_DIR, 'static')
# else:
#     STATICFILES_DIRS = (os.path.join(BASE_DIR, 'static'), )

WSGI_APPLICATION = 'fashbowl.wsgi.application'

# https://channels.readthedocs.io/en/latest/deploying.html
ASGI_APPLICATION = "fashbowl.routing.application"

CHANNEL_LAYERS = {
    "default": {
        # "BACKEND": "asgi_redis.RedisChannelLayer",
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [os.environ.get('REDIS_URL', 'redis://localhost:6379')],
        },
        #  ROUTING key found for default - this is no longer needed in Channels 2.
        # "ROUTING": "fashbowl.routing.application",
    },
}

# CHANNEL_LAYERS = {
#     "default": {
#         "BACKEND": "channels_redis.core.RedisChannelLayer",
#         "CONFIG": {
#             "hosts": [("redis-server-name", 6379)],
#         },
#     },
# }
# CHANNEL_LAYERS = {
#     'default': {
#         'BACKEND': 'channels_redis.core.RedisChannelLayer',
#         'CONFIG': {
#             "hosts": [('127.0.0.1', 6379)],
#         },
#     },
# }

# Could be changed to the config below to scale:
# "BACKEND": "asgi_redis.RedisChannelLayer",
# "CONFIG": {
#     "hosts": [("localhost", 6379)],
# },
# Database
# https://docs.djangoproject.com/en/dev/ref/settings/#databases

if DEBUG is True:  # or True:
    print("DATABASE DEBUG YES")
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': 'fashbowl',
            'HOST': 'localhost',
            'PORT': '5432'
        },
    }
else:
    print("DATABASE DEBUG NO")
    DATABASES = {'default': dj_database_url.config()}

# Password validation
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = []

# {
#     'NAME':
#  'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
# },
# {
#     'NAME':
# 'django.contrib.auth.password_validation.MinimumLengthValidator',
# },
# {
#     'NAME':
# 'django.contrib.auth.password_validation.CommonPasswordValidator',
# },
# {
#     'NAME':
# 'django.contrib.auth.password_validation.NumericPasswordValidator',
# },

# Internationalization
# https://docs.djangoproject.com/en/dev/topics/i18n/

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 100
}

MESSAGES_TO_LOAD = 15

# In settings.py

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

LOGIN_REDIRECT_URL = '/'
LOGIN_URL = '/login/'

ALLOWED_HOSTS = ['*']

# # Import local_settings.py
# try:
#     from local_settings import *
# except ImportError:
#     pass

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'ERROR'),
        },
    },
}