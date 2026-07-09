"""
Django settings for makeabilitylab project.

Generated initially by 'django-admin startproject' using Django 1.9 but
then with many manual modifications since then. See:
https://docs.djangoproject.com/en/4.2/topics/settings/

A few things:
* We read in a config file on both test and production. These files are diff
  depending on the server
* Do not alter any of these settings at runtime (e.g., in a view)
  https://docs.djangoproject.com/en/4.2/topics/settings/#altering-settings-at-runtime
"""

import os
from configparser import ConfigParser 
import datetime # for DATE_MAKEABILITYLAB_FORMED global

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load a ConfigParser object from a file called config.ini at the base level
# of the django project.
config = ConfigParser()

OS_ENVIRONMENT = os.environ
config_file = os.path.join(BASE_DIR, 'config.ini')
config.read(config_file)
if not config:
    CONFIG_FILE = "No config file set"
else:
    CONFIG_FILE = config_file

print(f"CONFIG_FILE: {CONFIG_FILE}")

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.9/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
if config.has_option('Django', 'SECRET_KEY'):
    SECRET_KEY = config.get('Django', 'SECRET_KEY')
else:
    # We should never be in production with this key
    SECRET_KEY = 'pe)-#st8rk!pomy!_1ha7=cpypp_(8%1xqmtw%!u@kw-f5&w^e' 

# SECURITY WARNING: don't run with debug turned on in production!
# we will default to True if not overriden in the config file
# this is to support localdev
DJANGO_ENV = os.environ.get('DJANGO_ENV')
if os.environ.get('DJANGO_ENV') == 'PROD':
    DEBUG = False
    DEBUG_SET = "Debug set to False because we're on production"
elif config.has_option('Django', 'DEBUG'):
    DEBUG = config.getboolean('Django', 'DEBUG')
    DEBUG_SET = f"DEBUG was set by {CONFIG_FILE} file"
elif os.environ.get('DJANGO_ENV') == 'DEBUG':
    DEBUG = True
    DEBUG_SET = f"DEBUG set by DJANGO_ENV variable, which is DJANGO_ENV={DJANGO_ENV}"
else:
    DEBUG = False
    # DEBUG_SET = "Debug set to True because we appear not to be on production or using an .ini file"
    DEBUG_SET = "Debug set to False as a default (appear not to be on production or using an .ini file)"

print(f"DJANGO_ENV: {DJANGO_ENV}")
print(f"DEBUG_SET: {DEBUG_SET}")
print(f"DEBUG: {DEBUG}")

if config.has_option('Django', 'ALLOWED_HOSTS'):
    USE_X_FORWARDED_HOST = True
    ALLOWED_HOSTS = config.get('Django', 'ALLOWED_HOSTS').split(',')
else:
    ALLOWED_HOSTS = ['*']

# Trust the X-Forwarded-Proto header from UW CSE's TLS-terminating Apache proxy so
# request.scheme / request.is_secure() report the real (https) scheme (#1329).
#
# The deployed Django container is reached over plain HTTP from Apache, so without
# this Django thinks every request is http even though visitors arrive over https.
# This is ONLY safe because the proxy is trusted: Apache sets X-Forwarded-Proto and
# the backend binds to the host's loopback only, so a client can't reach Django
# directly to spoof the header (confirmed with UW CSE IT). Gated to the deployed
# environments — in local dev there is no such proxy, so we must NOT trust the
# header (a direct client could forge it). Supersedes the in-app site_scheme
# workaround from #1236, which we keep for now and remove once verified on -test.
if DJANGO_ENV in ('PROD', 'TEST'):
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Makeability Lab Global Variables, including Makeability Lab version
ML_WEBSITE_VERSION = "2.26.0" # Keep this updated with each release and also change the short description below
ML_WEBSITE_VERSION_DESCRIPTION = "Improves image handling on the Awards admin badge plus a Data Health polish. The badge field now has an instant client-side preview and square (1:1) cropping via Cropper.js (#1408), and a new 'Pad badge to a square (don't crop)' option (#1410) that pads a non-square upload to a centered square -- white margins for JPEG, transparent for PNG/WebP -- instead of cropping off content, so editors no longer need to pad logos in an external tool before uploading. Padding is done server-side with Pillow: it re-encodes JPEG at quality 92, saves WebP lossless so a lossless source isn't degraded, and leaves already-square uploads untouched; a full-image crop box is stored so the public render isn't cropped. Also standardizes the per-row action links across the Data Health checks (#1405)."
DATE_MAKEABILITYLAB_FORMED = datetime.date(2012, 1, 1)  # Date Makeability Lab was formed
MAX_BANNERS = 7 # Maximum number of banners on a page

# With the upgrade to Django 3.2, we now need to specify the default auto field for primary keys
# See: 
#  - https://docs.djangoproject.com/en/3.2/releases/3.2/#customizing-type-of-auto-created-primary-keys
#  - https://stackoverflow.com/a/66971813
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

# With the upgrade to Django 4.1.2, we now need to specify trusted origins
# See: https://docs.djangoproject.com/en/4.0/ref/settings/#csrf-trusted-origins
# See also: https://stackoverflow.com/a/70326426
CSRF_TRUSTED_ORIGINS = ['https://*.cs.washington.edu']

# See: https://docs.djangoproject.com/en/2.0/topics/logging/
# https://lincolnloop.com/blog/django-logging-right-way/
# For the log format, see: https://stackoverflow.com/a/26276689/388117
#
# Log-file path (issue #1283): this used to be hardcoded to /code/media/debug.log,
# an absolute container-specific path. Django evaluates LOGGING at django.setup(),
# so on any host lacking that exact directory (e.g. GitHub Actions CI) startup died
# with FileNotFoundError before a single request/test ran. Derive the path from
# BASE_DIR instead (still under media/ so it stays reachable via the intentional
# /logs/ URL — see docs/DEPLOYMENT.md), allow an ML_LOG_DIR env override, and if
# the directory can't be created or written, fall back to a NullHandler so a bad
# log path never crashes startup.
def _log_dir_is_writable(log_dir):
    """Return True if ``log_dir`` exists (or can be created) and looks writable.

    Used to decide whether the file log handler is active or degrades to a
    NullHandler so a bad log path never crashes ``django.setup()`` (issue #1283).

    Note: this checks the *directory*, not the eventual log file. A dir that is
    writable but already holds a root-owned, read-only ``debug.log`` would still
    let RotatingFileHandler raise on open — an edge case we accept, since it is
    strictly better than the previous unconditional crash and matches the real
    deploy model (media/ is owned by the app's own user).
    """
    try:
        os.makedirs(log_dir, exist_ok=True)
        return os.access(log_dir, os.W_OK)
    except OSError:
        return False


LOG_DIR = os.environ.get('ML_LOG_DIR', os.path.join(BASE_DIR, 'media'))
LOG_FILE = os.path.join(LOG_DIR, 'debug.log')
_LOG_TO_FILE = _log_dir_is_writable(LOG_DIR)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(funcName)s %(process)d %(thread)d %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        # The file handler writes LOG_FILE (media/debug.log by default), which
        # lands in the bind-mounted web root and is intentionally exposed via the
        # /logs/ URL per docs/DEPLOYMENT.md (Jason Howe's design — convenient
        # remote debugging in exchange for some info disclosure). To shrink that
        # exposure in production, we log at INFO when DEBUG is off, but keep
        # DEBUG-level file logging in local dev where DEBUG is on and the file
        # isn't publicly reachable. If the log dir isn't writable (_LOG_TO_FILE
        # is False), degrade to a NullHandler so startup never dies (issue #1283).
        'file': {
            'level': 'DEBUG' if DEBUG else 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_FILE,
            'maxBytes': 1024*1024*5,  # 5 MB
            'backupCount': 6,
            'formatter': 'verbose',  # can switch between verbose and simple
        } if _LOG_TO_FILE else {
            'class': 'logging.NullHandler',
        },
        'console': {
            'level': 'DEBUG',
            'filters': ['require_debug_true'],
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'website': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'django.utils.autoreload': {
            'level': 'INFO',  # Change to 'INFO' or 'WARNING'
        },
        # This logger captures information about incoming HTTP requests, including details 
        # about the request method, URL, and any exceptions that occur during request 
        # processing. It’s useful for getting a high-level overview of the requests 
        # your application is handling and for debugging issues related to request handling.
        'django.request': { 
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },

        # This logger specifically captures information about URL resolution. It logs 
        # details about how Django is matching incoming URLs to your URL patterns. This is 
        # particularly useful for debugging issues where URLs are not resolving as expected, 
        # such as NoReverseMatch errors.
        'django.urls': { # Adds logging for URL routing
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# Application definition
INSTALLED_APPS = [
    'website.apps.WebsiteConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'django.contrib.humanize', # for humanizing numbers in templates: https://docs.djangoproject.com/en/4.2/ref/contrib/humanize/

    # Generates a dynamic /sitemap.xml from our querysets for SEO (issue #1252).
    # NOTE: we deliberately do NOT install django.contrib.sites — without it,
    # the sitemap framework falls back to RequestSite, deriving the domain from
    # the incoming request host. That makes the sitemap emit the correct domain
    # across all three environments (local / test / prod) with no per-env config
    # and no extra DB migration. See website/sitemaps.py.
    'django.contrib.sitemaps',

    # Image handling = two cooperating pieces: easy-thumbnails resizes/scales,
    # while image_cropping lets editors pick the crop box. easy-thumbnails then
    # renders that box at any size on demand (see crop_corners in
    # THUMBNAIL_PROCESSORS below).
    # NOTE: 'image_cropping' is an IN-REPO fork (top-level image_cropping/), not
    # the PyPI django-image-cropping package. It ships a modern Cropper.js admin
    # widget (instant client-side preview/crop). See image_cropping/README.md
    # and issues #1299 / #1269. Treated as project source, like sortedm2m below.
    'image_cropping',
    'easy_thumbnails', # for dynamically creating thumbnails: https://github.com/SmileyChris/easy-thumbnails
    'sortedm2m', # Used for SortedManyToManyFields in admin interface: https://pypi.org/project/django-sortedm2m-filter-horizontal-widget/
    'django_prose_editor', # ProseMirror rich-text editor for the News admin (replaced django-ckeditor; issue #1269)

    # This sortedm2m_filter_horizontal_widget widget was originally from:
    # https://github.com/svleeuwen/sortedm2m-filter-horizontal-widget
    # However, it was incompatible with Django 5.2.9, so we forked it and made some changes.
    # The new version is local to our project under the sortedm2m_filter_horizontal_widget directory.
    'sortedm2m_filter_horizontal_widget', 
    'rest_framework',

    # Adding django-debug-toolbar, which is recommended by Django
    # https://docs.djangoproject.com/en/4.2/topics/performance/#performance-benchmarking
    # https://django-debug-toolbar.readthedocs.io/en/latest/installation.html
    "debug_toolbar",
]

# JEF: Added 9/22/2023
# The Debug Toolbar is shown only if your IP address is listed in Django’s INTERNAL_IPS setting.
INTERNAL_IPS = [
    "127.0.0.1",
]

if DEBUG:
    # This code is from: https://django-debug-toolbar.readthedocs.io/en/stable/installation.html#configure-internal-ips
    import socket  # only if you haven't already imported this
    hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())

    # I added 128.208.5.106, which is the current ip for the makeabilitylab-test server
    INTERNAL_IPS = [ip[: ip.rfind(".")] + ".1" for ip in ips] + ["127.0.0.1", "10.0.2.2", "128.208.5.106"]

MIDDLEWARE = [
    # 'website.middleware.RenderTimingMiddleware', # couldn't get this work, see file for details

    # JEF (9/22/2023) The order of MIDDLEWARE is important. You should include the Debug Toolbar middleware as 
    # early as possible in the list. However, it must come after any other middleware that 
    # encodes the response’s content, such as GZipMiddleware.
    # See: https://django-debug-toolbar.readthedocs.io/en/latest/installation.html
    'debug_toolbar.middleware.DebugToolbarMiddleware',

    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# A string representing the full Python import path to your root URLconf.
# See: https://docs.djangoproject.com/en/4.2/ref/settings/#root-urlconf
ROOT_URLCONF = 'makeabilitylab.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'website.context_processors.recent_news',
                'website.context_processors.admin_version_info',
            ],
        },
    },
]

# Database
# https://docs.djangoproject.com/en/1.9/ref/settings/#databases
if config.has_section('Postgres'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': config.get('Postgres', 'DATABASE'),
            'USER': config.get('Postgres', 'USER'),
            'PASSWORD': config.get('Postgres', 'PASSWORD'),
            'HOST': config.get('Postgres', 'HOSTNAME'),
            'PORT': '',
        }
    }
else:
     DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'makeability',
        'USER': 'admin',
        'PASSWORD': 'password',
        'HOST': 'db', # set in docker-compose.yml
        'PORT': 5432 # default postgres port
    }
}


# Password validation
# https://docs.djangoproject.com/en/1.9/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME':'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
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


# Internationalization
# https://docs.djangoproject.com/en/1.9/topics/i18n/
LANGUAGE_CODE = 'en-us'

# Change timezone for server: https://stackoverflow.com/questions/29311354/how-to-set-the-timezone-in-django
TIME_ZONE = 'America/Los_Angeles'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# JEF: I added these for uploading files.
# See:
#   http://stackoverflow.com/questions/22570723/handling-uploading-image-django-admin-python
#   https://github.com/axelpale/minimal-django-file-upload-example
# The MEDIA_URL is required by Django see and is a URL that handles the media served 
# from MEDIA_ROOT, used for managing stored files. 
# See: https://docs.djangoproject.com/en/4.2/ref/settings/#media-url
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.9/howto/static-files/
# URL to use when referring to static files located in STATIC_ROOT.
# See: https://docs.djangoproject.com/en/4.2/ref/settings/#static-url
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

# Rich text editing for the News admin is handled by django-prose-editor
# (issue #1269). Configuration is per-field on website/models/news.py
# (ProseEditorField extensions + sanitize), so no project-level settings are
# needed here. Image uploads go through our own staff-only picker view
# (website/views/news.py: news_image_upload), which still saves into
# media/uploads/ via website.utils.fileutils.get_ckeditor_image_filename.

# Thumbnail processing
# LS: from https://github.com/jonasundderwolf/django-image-cropping
from easy_thumbnails.conf import Settings as thumbnail_settings
THUMBNAIL_PROCESSORS = (
    'image_cropping.thumbnail_processors.crop_corners',
) + thumbnail_settings.THUMBNAIL_PROCESSORS

# https://easy-thumbnails.readthedocs.io/en/latest/ref/settings/#easy_thumbnails.conf.Settings.THUMBNAIL_DEFAULT_OPTIONS
THUMBNAIL_DEFAULT_OPTIONS = {
    # The default quality level for JPG images on a scale from 1 (worst) to 95 (best). 
    # Technically, values up to 100 are allowed, but this is not recommended.
    'quality': 90, # default is 85
    
    # 'bw': True, Would set all images to b&w
}