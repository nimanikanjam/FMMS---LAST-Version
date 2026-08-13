"""
FMMS Production Settings.

Full security hardening. Never enable DEBUG.
All secrets loaded from environment — never hardcoded.
"""

from .base import *  # noqa: F401, F403
from .base import BASE_DIR, CACHES, DATABASES, SECRET_KEY, env
from .validation import require_no_wildcard, require_non_empty, require_redis_url

# ──────────────────────────────────────────────────────────────────────────────
# Core
# ──────────────────────────────────────────────────────────────────────────────
DEBUG = False
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS")
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS")

require_non_empty(
    {
        "SECRET_KEY": SECRET_KEY,
        "ALLOWED_HOSTS": ALLOWED_HOSTS,
        "CORS_ALLOWED_ORIGINS": CORS_ALLOWED_ORIGINS,
        "CSRF_TRUSTED_ORIGINS": CSRF_TRUSTED_ORIGINS,
        "POSTGRES_DB": DATABASES["default"]["NAME"],
        "POSTGRES_USER": DATABASES["default"]["USER"],
        "POSTGRES_PASSWORD": DATABASES["default"]["PASSWORD"],
        "POSTGRES_HOST": DATABASES["default"]["HOST"],
        "REDIS_URL": env("REDIS_URL"),
        "CELERY_BROKER_URL": env("CELERY_BROKER_URL"),
        "MEDIA_ROOT": env("MEDIA_ROOT"),
    }
)
require_no_wildcard("ALLOWED_HOSTS", ALLOWED_HOSTS)
require_no_wildcard("CORS_ALLOWED_ORIGINS", CORS_ALLOWED_ORIGINS)
require_redis_url("REDIS_URL", env("REDIS_URL"))
require_redis_url("CELERY_BROKER_URL", env("CELERY_BROKER_URL"))

# ──────────────────────────────────────────────────────────────────────────────
# Security hardening
# ──────────────────────────────────────────────────────────────────────────────
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31_536_000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"

CORS_ALLOW_CREDENTIALS = False
CORS_URLS_REGEX = r"^/api/.*$"

# Redis is required infrastructure in production. Never hide cache failures.
CACHES["default"]["OPTIONS"]["IGNORE_EXCEPTIONS"] = False

# Persistent connections are health-checked. Native pooling requires psycopg 3.
if env.bool("POSTGRES_POOL_ENABLED", default=False):
    DATABASES["default"]["CONN_MAX_AGE"] = 0
    DATABASES["default"]["OPTIONS"]["pool"] = {
        "min_size": env.int("POSTGRES_POOL_MIN_SIZE", default=1),
        "max_size": env.int("POSTGRES_POOL_MAX_SIZE", default=10),
        "timeout": env.int("POSTGRES_POOL_TIMEOUT", default=10),
    }

# Static assets are immutable build output; media lives on a persistent mount.
STATIC_ROOT = env.path("STATIC_ROOT", default=BASE_DIR / "staticfiles")
MEDIA_ROOT = env.path("MEDIA_ROOT")
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"
    },
}

# ──────────────────────────────────────────────────────────────────────────────
# Sentry — error tracking for production
# ──────────────────────────────────────────────────────────────────────────────
SENTRY_DSN = env("SENTRY_DSN", default="")
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.redis import RedisIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
            RedisIntegration(),
        ],
        environment="production",
        traces_sample_rate=0.05,
        send_default_pii=False,
    )

# ──────────────────────────────────────────────────────────────────────────────
# Email
# ──────────────────────────────────────────────────────────────────────────────
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@fmms.local")
