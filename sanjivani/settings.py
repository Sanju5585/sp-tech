"""
Django settings for SP-Tech Software Solution project.
"""

import os
import socket
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-fallback-key-change-in-production')

DEBUG = os.getenv('DEBUG', 'False') == 'True'


def _local_host_ips() -> list[str]:
    """IPs on this machine so probes by public/private IP don't trip DisallowedHost."""
    found: set[str] = {'127.0.0.1', 'localhost'}
    try:
        hostname = socket.gethostname()
        found.add(hostname)
        for info in socket.getaddrinfo(hostname, None):
            ip = info[4][0]
            if ip and not ip.startswith('fe80:'):
                found.add(ip)
    except OSError:
        pass
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(('8.8.8.8', 80))
            found.add(sock.getsockname()[0])
    except OSError:
        pass
    # AWS EC2 public IPv4 (IMDSv2, then IMDSv1)
    try:
        import urllib.request

        token = ''
        try:
            token_req = urllib.request.Request(
                'http://169.254.169.254/latest/api/token',
                method='PUT',
                headers={'X-aws-ec2-metadata-token-ttl-seconds': '60'},
            )
            with urllib.request.urlopen(token_req, timeout=0.5) as resp:
                token = resp.read().decode('ascii').strip()
        except Exception:
            token = ''
        meta_headers = {'X-aws-ec2-metadata-token': token} if token else {}
        req = urllib.request.Request(
            'http://169.254.169.254/latest/meta-data/public-ipv4',
            headers=meta_headers,
            method='GET',
        )
        with urllib.request.urlopen(req, timeout=0.5) as resp:
            public_ip = resp.read().decode('ascii').strip()
            if public_ip:
                found.add(public_ip)
    except Exception:
        pass
    extra = os.getenv('PUBLIC_IP', '').strip()
    if extra:
        found.add(extra)
    return sorted(found)


ALLOWED_HOSTS = [
    h.strip() for h in os.getenv(
        'ALLOWED_HOSTS',
        'localhost,127.0.0.1,'
        'sanjivani.com,www.sanjivani.com,'
        'sanjivanione.com,www.sanjivanione.com,'
        'sanjivanione.in,www.sanjivanione.in',
    ).split(',')
    if h.strip()
]
# Always permit this server's own addresses (bots/scanners hit the raw IP).
for _ip in _local_host_ips():
    if _ip not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(_ip)

SITE_ID = 1

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',
    'django.contrib.sites',
    # Third-party
    'compressor',
    # Local apps
    'core',
    'products',
    'blog',
    'contact',
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

ROOT_URLCONF = 'sanjivani.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': False,
        'OPTIONS': {
            'loaders': [
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            ],
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.seo_defaults',
            ],
        },
    },
]

WSGI_APPLICATION = 'sanjivani.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
]

# WhiteNoise compression
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Auth
LOGIN_URL = '/contact/login/'
LOGIN_REDIRECT_URL = '/apps/'
LOGOUT_REDIRECT_URL = '/'

TIMETABLE_API_URL = os.getenv('TIMETABLE_API_URL', 'http://127.0.0.1:8001')
TIMETABLE_SPA_DIR = BASE_DIR / 'static' / 'timetable-app'
PORTAL_SSO_SECRET = os.getenv('PORTAL_SSO_SECRET', 'sanjivani-portal-sso-change-me')
CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.getenv(
        'CSRF_TRUSTED_ORIGINS',
        'http://127.0.0.1:8000,http://localhost:8000,'
        'https://127.0.0.1,https://localhost,'
        'https://sanjivani.com,https://www.sanjivani.com,'
        'https://sanjivanione.com,https://www.sanjivanione.com,'
        'https://sanjivanione.in,https://www.sanjivanione.in',
    ).split(',')
    if o.strip()
]
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
X_FRAME_OPTIONS = 'SAMEORIGIN'

# Email
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@sanjivani.com')
CONTACT_EMAIL = os.getenv('CONTACT_EMAIL', 'contact@sanjivani.com')

# Site metadata
SITE_NAME = 'SP-Tech Software Solution'
SITE_URL = os.getenv('SITE_URL', 'https://www.sanjivanione.in')
SITE_TAGLINE = 'SanjivaniOne ERP and business software for SMB growth'
SITE_DESCRIPTION = (
    'SP-Tech Software Solution builds SanjivaniOne ERP—the flagship platform for '
    'finance, inventory, HR, sales, and operations—plus supporting tools that help '
    'small and medium businesses replace outdated systems and grow faster.'
)
WHATSAPP_NUMBER = os.getenv('WHATSAPP_NUMBER', '918447695372')

# Django Compressor
COMPRESS_ENABLED = not DEBUG
COMPRESS_CSS_FILTERS = [
    'compressor.filters.css_default.CssAbsoluteFilter',
    'compressor.filters.cssmin.rCSSMinFilter',
]
COMPRESS_JS_FILTERS = ['compressor.filters.jsmin.JSMinFilter']

# Cache (file-based for dev; use Redis/Memcached in prod)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': BASE_DIR / '.cache',
        'TIMEOUT': 300,
        'OPTIONS': {'MAX_ENTRIES': 1000},
    }
}

# Security headers (active in production)
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

# Quiet scanner noise (raw-IP Host probes); real app errors still log.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'loggers': {
        'django.security.DisallowedHost': {
            'handlers': ['console'],
            'level': 'CRITICAL',
            'propagate': False,
        },
    },
}
