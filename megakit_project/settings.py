from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

CSRF_TRUSTED_ORIGINS = [
    "https://ratelmovement.academicdigital.space",
    "https://www.ratelmovement.academicdigital.space",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
]

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-lmow79k@vx=%fhdh(17xnhylx%6xotl5-#rqz7(q@&z=h&u5##"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["*", ".academicdigital.space", "localhost", "127.0.0.1"]

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "main",
    "whitenoise",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "megakit_project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "main.context_processors.paystack_public_key",
            ],
        },
    },
]

WSGI_APPLICATION = "megakit_project.wsgi.application"

# Database

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Supabase configuration (same as provided snippet)
SUPABASE_URL = os.getenv(
    "SUPABASE_URL", "https://vhovrdqfpsdeynsmvleu.supabase.co"
)
SUPABASE_KEY = os.getenv(
    "SUPABASE_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZob3ZyZHFmcHNkZXluc212bGV1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkzNTU4MjgsImV4cCI6MjA4NDkzMTgyOH0.4v6gbWs-3sLqWD0dcEQHIpHGCbuWeLgteI5myRHvDXQ",
)
SUPABASE_SERVICE_KEY = os.getenv(
    "SUPABASE_SERVICE_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZob3ZyZHFmcHNkZXluc212bGV1Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2OTM1NTgyOCwiZXhwIjoyMDg0OTMxODI4fQ.YZ2Y6U7YxyfnjpvXTXSNSUSdR-tsrXmm60ofzRoJum8",
)
SUPABASE_STORAGE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "project-files")

if not SUPABASE_URL or not SUPABASE_KEY or not SUPABASE_SERVICE_KEY:
    print("\n" + "=" * 80)
    print("WARNING: Supabase configuration is incomplete!")
    print("=" * 80)
    print(f"SUPABASE_URL: {'OK' if SUPABASE_URL else 'MISSING'}")
    print(
        "SUPABASE_KEY: "
        + (
            "OK"
            if SUPABASE_KEY and len(SUPABASE_KEY) > 100
            else f"MISSING or INVALID (length: {len(SUPABASE_KEY or '')})"
        )
    )
    print(
        "SUPABASE_SERVICE_KEY: "
        + (
            "OK"
            if SUPABASE_SERVICE_KEY and len(SUPABASE_SERVICE_KEY) > 100
            else f"MISSING or INVALID (length: {len(SUPABASE_SERVICE_KEY or '')})"
        )
    )
    print()
    print("To fix this:")
    print("1. Ensure your environment or .env file has valid Supabase keys")
    print("2. Or update SUPABASE_URL, SUPABASE_KEY, SUPABASE_SERVICE_KEY in settings")
    print("=" * 80 + "\n")

# Paystack configuration for membership payments
PAYSTACK_PUBLIC_KEY = os.getenv("PAYSTACK_PUBLIC_KEY", "pk_test_af37d26c0fa360522c4e66495f3877e498c18850")
PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY", "sk_test_185fc53d96addab7232060c86f4221918ab59d1c")

# Password validation

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

# Static files

STATIC_URL = "/static/"
STATICFILES_DIRS = [
    BASE_DIR,  # so existing css/, js/, images/ work without moving
]
STATIC_ROOT = BASE_DIR / "staticfiles"

# Media files

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Email configuration (same as provided snippet)

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").lower() == "true"
EMAIL_HOST_USER = os.getenv(
    "EMAIL_HOST_USER", "metascholarlimited@gmail.com"
)
EMAIL_HOST_PASSWORD = os.getenv(
    "EMAIL_HOST_PASSWORD", "votj pkhj iiqi abwr"
)
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

