import os
import dj_database_url

"""
Django settings for quiznet project.
"""
from dotenv import load_dotenv
load_dotenv()


from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent



# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'unsafe-default-for-local')
DEBUG = os.environ.get('DEBUG', '') == '1'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost').split(',')



INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "account",
    "quiz",
    "channels"
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",   # MUST BE AT TOP for cookies
    "django.middleware.security.SecurityMiddleware",
    "account.middleware.RefreshAccessMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
     
    "django.middleware.common.CommonMiddleware",
    'whitenoise.middleware.WhiteNoiseMiddleware',
]

ROOT_URLCONF = "quiznet.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "quiznet.wsgi.application"
ASGI_APPLICATION = "quiznet.asgi.application"

# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

# 1. Try to read DATABASE_URL (Render / local override)
DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    # Use Render (or any external) Postgres when DATABASE_URL is set
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,        # keep connections open
            ssl_require=True        # Render usually needs SSL; set False if local
        )
    }
else:
    # 2. Fallback to your old local Postgres settings
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": "quizdb",
            "USER": "quiz",
            "PASSWORD": "root",
            "HOST": "127.0.0.1",
            "PORT": "5432",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field
SESSION_COOKIE_SECURE = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ------------------------------------------------------------
# ✅ ALLOWED ORIGINS updated to include 127.0.0.1 (important)
# ------------------------------------------------------------
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",  # ← Added for Vite alternate origin
]

# ------------------------------------------------------------
# ✅ CSRF TRUSTED ORIGINS updated similarly
# ------------------------------------------------------------
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",  # ← Added
]

# ------------------------------------------------------------
# Already correct for cookie-based authentication
# ------------------------------------------------------------
CORS_ALLOW_CREDENTIALS = True

# ------------------------------------------------------------
# ✅ MUST ADD to allow Set-Cookie + Authorization headers
# ------------------------------------------------------------
CORS_ALLOW_HEADERS = [
    "Content-Type",
    "X-CSRFToken",
    "X-Requested-With",
    "Authorization",  # ← Added (important for JWT cookies)
]

# ------------------------------------------------------------
# ✅ MUST ADD so browser accepts Set-Cookie response
# ------------------------------------------------------------
CORS_EXPOSE_HEADERS = ["Set-Cookie"]  # ← Required for cookies to be visible

# ------------------------------------------------------------

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("redis", 6379)],
        },
    },
}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
}

from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=5),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': False,
}

CSRF_COOKIE_SECURE = True

# CSRF_COOKIE_HTTPONLY typically False (so frontend can read CSRF if you use double-submit)

# in settings.py
# seconds for tokens; align with your SIMPLE_JWT lifetimes
ACCESS_TOKEN_LIFETIME_SECONDS = int(SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds())
REFRESH_TOKEN_LIFETIME_SECONDS = int(SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds())

# from pathlib import Path

# STATIC_URL = '/static/'
# STATIC_ROOT = BASE_DIR / 'staticfiles'   # or str(BASE_DIR / 'staticfiles')
# STATICFILES_DIRS = [BASE_DIR / 'static'] # if you keep static in project 'static' folder

# # WhiteNoise storage for compression & cache-busting
# STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD")


STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),   # only if you actually have a 'static' folder at project root
]


STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"


SESSION_COOKIE_SAMESITE = "None"
CSRF_COOKIE_SAMESITE    = "None"

SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY    = True

SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY    = True 