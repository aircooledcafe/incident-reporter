"""
Django settings for config project.

Tagged to Django 5.1.14.
"""

import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv_file(dotenv_path: Path) -> None:
    """Load key=value pairs from a .env file into os.environ if not already set."""
    if not dotenv_path.is_file():
        return
    for raw_line in dotenv_path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, _, value = line.partition('=')
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


# Automatically load root .env or backend/.env for local commands if present
_load_dotenv_file(BASE_DIR.parent / '.env')
_load_dotenv_file(BASE_DIR / '.env')

# SECURITY: Require DJANGO_SECRET_KEY from environment (no hardcoded fallback secrets)
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', '').strip()
if not SECRET_KEY:
    raise ImproperlyConfigured(
        'The DJANGO_SECRET_KEY environment variable is required and must not be empty. '
        'Copy .env.example to .env and set a generated secret key before starting.'
    )

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DJANGO_DEBUG', 'False').lower() in ('1', 'true', 'yes')

ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get('DJANGO_ALLOWED_HOSTS', '*').split(',')
    if h.strip()
]

# Reverse-proxy & CSRF support for Docker / Nginx / LAN / HTTPS deployments
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

_csrf_origins_raw = os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS', '').strip()
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in _csrf_origins_raw.split(',')
    if origin.strip()
]


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'rest_framework',
    'rest_framework.authtoken',
    'incidents',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# Persist all user sessions in the external/mapped database (never ephemeral container memory)
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

ROOT_URLCONF = 'config.urls'

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

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases
# Supports DJANGO_DB_PATH for mapped Docker volume / external storage persistence
# across container rebuilds, updates, and restarts (includes users, profiles, tokens, sessions, and projects).
DB_PATH = Path(os.environ.get('DJANGO_DB_PATH', str(BASE_DIR / 'db.sqlite3')))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': DB_PATH,
        'OPTIONS': {
            'timeout': 20,
        },
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images) for Django /admin/
# Uses /django-static/ so it never collides with frontend SPA assets behind Nginx/Vite
STATIC_URL = '/django-static/'
STATIC_ROOT = Path(os.environ.get('DJANGO_STATIC_ROOT', str(BASE_DIR / 'staticfiles')))

# Artifacts & Media directory for incident investigations and archives
# Supports DJANGO_ARTIFACTS_ROOT for mapped Docker volume / external storage persistence.
ARTIFACTS_ROOT = Path(os.environ.get('DJANGO_ARTIFACTS_ROOT', str(BASE_DIR.parent / 'artifacts')))
ARTIFACTS_ROOT.mkdir(parents=True, exist_ok=True)
MEDIA_URL = '/artifacts/'
MEDIA_ROOT = ARTIFACTS_ROOT

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
