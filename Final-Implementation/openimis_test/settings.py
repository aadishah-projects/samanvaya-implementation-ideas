"""
Django settings for the OpenIMIS + Samanvaya test harness.
This simulates the OpenIMIS environment enough to run the Samanvaya module.
"""
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Add parent dirs to path so openimis-be-samanvaya is importable
sys.path.insert(0, os.path.join(BASE_DIR, "openimis-be-samanvaya"))

SECRET_KEY = "test-harness-secret-key-not-for-production"
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Graphene (GraphQL)
    "graphene_django",
    # Mock OpenIMIS claim module
    "openimis_test.claim",
    # Samanvaya — the actual module being tested
    "samanvaya",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    # CSRF disabled for test harness — real OpenIMIS uses JWT auth
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

ROOT_URLCONF = "openimis_test.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

# Database — PostgreSQL (same as real OpenIMIS)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "samanvaya_db",
        "USER": "samanvaya",
        "PASSWORD": "samanvaya123",
        "HOST": "127.0.0.1",
        "PORT": "5433",
    }
}

# Graphene (GraphQL) config
GRAPHENE = {
    "SCHEMA": "openimis_test.schema.schema",
}

# Static files
STATIC_URL = "/static/"

# Default auto field
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Celery config (disabled for test harness — tasks run synchronously)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
