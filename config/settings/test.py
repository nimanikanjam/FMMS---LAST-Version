"""
FMMS Test Settings.

Overrides database to SQLite for fast, dependency-free test execution.
PostgreSQL is used in development (docker-compose) and production.
"""

import os
from pathlib import Path

# Test execution must never inherit SAP mode toggles from a developer's local .env.
os.environ["SAP_USE_MOCK"] = "True"
os.environ["SAP_WRITE"] = "True"
os.environ.setdefault("POSTGRES_DB", "fmms_test")
os.environ.setdefault("POSTGRES_USER", "fmms_test")
os.environ.setdefault("POSTGRES_PASSWORD", "test-only")
os.environ.setdefault("POSTGRES_HOST", "localhost")

from .base import *  # noqa: F401, F403
from .base import BASE_DIR  # noqa: F401

# ──────────────────────────────────────────────────────────────────────────────
# Database — SQLite for tests (no external service required)
# ──────────────────────────────────────────────────────────────────────────────
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": Path(BASE_DIR) / "test.db",
        "TEST": {
            "NAME": Path(BASE_DIR) / "test_fmms.db",
        },
    }
}

# Disable ATOMIC_REQUESTS for test compatibility with pytest-django fixtures
DATABASES["default"]["ATOMIC_REQUESTS"] = False

# ──────────────────────────────────────────────────────────────────────────────
# Speed — disable password hashing in tests
# ──────────────────────────────────────────────────────────────────────────────
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# ──────────────────────────────────────────────────────────────────────────────
# Disable caching in tests
# ──────────────────────────────────────────────────────────────────────────────
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# Suppress debug toolbar in tests
DEBUG = False
