"""
FMMS Base Settings.

Shared configuration for all environments.
Never import environment-specific settings from this file.
"""

import os
from datetime import timedelta
from pathlib import Path

import environ
from celery.schedules import crontab

# ──────────────────────────────────────────────────────────────────────────────
# Environment
# ──────────────────────────────────────────────────────────────────────────────
env = environ.Env(
    DEBUG=(bool, False),
    LOG_LEVEL=(str, "INFO"),
    ALLOWED_HOSTS=(list, []),
    CORS_ALLOWED_ORIGINS=(list, []),
    VEHICLE_SYNC_INTERVAL_HOURS=(int, 24),
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Local files are convenience only; deployed environments receive real env vars.
_SETTINGS_MODULE = os.environ.get("DJANGO_SETTINGS_MODULE", "")
if _SETTINGS_MODULE.endswith((".development", ".demo", ".test")):
    environ.Env.read_env(BASE_DIR / ".env", overwrite=False)

# ──────────────────────────────────────────────────────────────────────────────
# Core
# ──────────────────────────────────────────────────────────────────────────────
SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

# ──────────────────────────────────────────────────────────────────────────────
# Applications
# ──────────────────────────────────────────────────────────────────────────────
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt",
    "drf_spectacular",
    "django_celery_beat",
    "django_celery_results",
]

FMMS_APPS = [
    "apps.authentication",
    # Phase 1 domain apps — registered in Milestone 3:
    "apps.vehicle",
    "apps.driver",
    "apps.inspection",
    "apps.fault",
    "apps.repair",
    "apps.material",
    "apps.handover",
    "apps.preventive_maintenance",
    "apps.procurement",
    "apps.integration",
    # Project-wide operational management commands:
    "infrastructure.operations.apps.OperationsConfig",
    # "apps.reporting",  # Phase 2 — not activated until reporting domain is implemented
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + FMMS_APPS

# ──────────────────────────────────────────────────────────────────────────────
# Authentication
# ──────────────────────────────────────────────────────────────────────────────
AUTH_USER_MODEL = "authentication.FMMSUser"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ──────────────────────────────────────────────────────────────────────────────
# Middleware — order matters
# ──────────────────────────────────────────────────────────────────────────────
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # FMMS middleware — active from Milestone 1
    "core.middleware.request_id.RequestIDMiddleware",
    "core.middleware.audit_log.AuditLogMiddleware",
]

ROOT_URLCONF = "config.urls"

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ──────────────────────────────────────────────────────────────────────────────
# Templates
# ──────────────────────────────────────────────────────────────────────────────
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

# ──────────────────────────────────────────────────────────────────────────────
# Database — PostgreSQL is provisioned outside Django
# ──────────────────────────────────────────────────────────────────────────────
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB"),
        "USER": env("POSTGRES_USER"),
        "PASSWORD": env("POSTGRES_PASSWORD"),
        "HOST": env("POSTGRES_HOST"),
        "PORT": env.int("POSTGRES_PORT", default=5432),
        "CONN_MAX_AGE": env.int("POSTGRES_CONN_MAX_AGE", default=60),
        "CONN_HEALTH_CHECKS": True,
        "ATOMIC_REQUESTS": True,
        "OPTIONS": {
            "connect_timeout": env.int("POSTGRES_CONNECT_TIMEOUT", default=5),
            "options": (
                f"-c statement_timeout={env.int('POSTGRES_STATEMENT_TIMEOUT_MS', default=30000)}"
            ),
        },
    }
}

# ──────────────────────────────────────────────────────────────────────────────
# Cache — Redis
# ──────────────────────────────────────────────────────────────────────────────
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://localhost:6379/0"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "IGNORE_EXCEPTIONS": True,  # Degrade gracefully if Redis is unavailable
        },
        "KEY_PREFIX": "fmms",
    }
}

# ──────────────────────────────────────────────────────────────────────────────
# Migration Modules — maps apps to infrastructure/migrations/
# Extended in Milestone 3 when domain apps are registered.
# ──────────────────────────────────────────────────────────────────────────────
MIGRATION_MODULES = {
    "authentication": "apps.authentication.infrastructure.migrations",
    # Phase 1 domain apps — migrations live inside each app's infrastructure package:
    "vehicle": "apps.vehicle.infrastructure.migrations",
    "driver": "apps.driver.infrastructure.migrations",
    "inspection": "apps.inspection.infrastructure.migrations",
    "fault": "apps.fault.infrastructure.migrations",
    "repair": "apps.repair.infrastructure.migrations",
    "material": "apps.material.infrastructure.migrations",
    "handover": "apps.handover.infrastructure.migrations",
    "preventive_maintenance": "apps.preventive_maintenance.infrastructure.migrations",
    "procurement": "apps.procurement.infrastructure.migrations",
    "integration": "apps.integration.infrastructure.migrations",
}

# ──────────────────────────────────────────────────────────────────────────────
# Internationalization
# ──────────────────────────────────────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ──────────────────────────────────────────────────────────────────────────────
# Static & Media Files
# ──────────────────────────────────────────────────────────────────────────────
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "mediafiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ──────────────────────────────────────────────────────────────────────────────
# Django REST Framework — baseline config (endpoints added in Milestone 7)
# ──────────────────────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
    ],
    "EXCEPTION_HANDLER": "core.exceptions.http_exception_handler.fmms_exception_handler",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "auth_token_obtain": "10/min",
        "auth_token_refresh": "30/min",
    },
    "DEFAULT_PAGINATION_CLASS": "core.pagination.standard_pagination.FMMSPageNumberPagination",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "FMMS API",
    "DESCRIPTION": "Fleet Maintenance Management System REST API.",
    "VERSION": "v1",
    "SERVE_INCLUDE_SCHEMA": False,
    "TAGS": [
        {"name": "auth", "description": "Authentication and current user APIs."},
        {"name": "vehicle", "description": "Vehicle master data and odometer APIs."},
        {"name": "driver", "description": "Driver master data APIs."},
        {
            "name": "inspection",
            "description": "Inspection and checklist template APIs.",
        },
        {"name": "fault", "description": "Fault registration and workflow APIs."},
        {"name": "repair", "description": "Repair order workflow APIs."},
        {"name": "material", "description": "Material request APIs."},
        {"name": "handover", "description": "Vehicle handover APIs."},
        {
            "name": "preventive-maintenance",
            "description": "Preventive maintenance plan and work-order APIs.",
        },
        {"name": "procurement", "description": "Purchase requisition and order APIs."},
        {"name": "integration", "description": "SAP integration transaction APIs."},
    ],
}

# ──────────────────────────────────────────────────────────────────────────────
# Celery — broker, result backend, and reduced M8 beat schedule
# ──────────────────────────────────────────────────────────────────────────────
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/1")
CELERY_RESULT_BACKEND = env("REDIS_URL", default="redis://localhost:6379/2")
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = "UTC"
CELERY_ENABLE_UTC = True
CELERY_TASK_TRACK_STARTED = True
CELERY_RESULT_EXTENDED = True
CELERY_IMPORTS = (
    "infrastructure.messaging.tasks.sap_retry_tasks",
    "infrastructure.messaging.tasks.sap_sync_tasks",
    "infrastructure.messaging.tasks.maintenance_tasks",
)
VEHICLE_SYNC_INTERVAL_HOURS = env("VEHICLE_SYNC_INTERVAL_HOURS")

CELERY_BEAT_SCHEDULE = {
    "retry-failed-sap-every-15m": {
        "task": "fmms.retry_failed_sap_transactions",
        "schedule": 15 * 60,
    },
    "sync-vehicles-from-sap": {
        "task": "fmms.sync_vehicles_from_sap",
        "schedule": VEHICLE_SYNC_INTERVAL_HOURS * 60 * 60,
    },
    "trigger-overdue-pm-daily": {
        "task": "fmms.trigger_overdue_pm_work_orders",
        "schedule": crontab(hour=2, minute=0),
    },
}

# ──────────────────────────────────────────────────────────────────────────────
# Logging — structured JSON, all FMMS logs use fmms.* namespace
# ──────────────────────────────────────────────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "core.logging.formatters.FMMSJSONFormatter",
        },
        "simple": {
            "format": "[{levelname}] {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": env("LOG_LEVEL"),
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "fmms": {
            "handlers": ["console"],
            "level": env("LOG_LEVEL"),
            "propagate": False,
        },
    },
}

# ──────────────────────────────────────────────────────────────────────────────
# SAP Integration — credentials loaded from environment
# ──────────────────────────────────────────────────────────────────────────────
SAP_HOST = env("SAP_HOST", default="")
SAP_CLIENT = env("SAP_CLIENT", default="")
SAP_USER = env("SAP_USER", default="")
SAP_PASSWORD = env("SAP_PASSWORD", default="")
SAP_SYSTEM_ID = env("SAP_SYSTEM_ID", default="")
SAP_MAX_RETRIES = env.int("SAP_MAX_RETRIES", default=3)
SAP_RETRY_BACKOFF_FACTOR = env.float("SAP_RETRY_BACKOFF_FACTOR", default=2.0)
SAP_REQUEST_TIMEOUT = env.int("SAP_REQUEST_TIMEOUT", default=30)

# ──────────────────────────────────────────────────────────────────────────────
# CORS — overridden per environment (development allows all local origins)
# ──────────────────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOW_CREDENTIALS = False

# ──────────────────────────────────────────────────────────────────────────────
# FMMS Application Settings
# ──────────────────────────────────────────────────────────────────────────────
FMMS_SERVICE_NAME = "fmms"
FMMS_API_VERSION = "v1"
