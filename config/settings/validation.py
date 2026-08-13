"""Fail-fast validation helpers for environment-backed settings."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from urllib.parse import urlparse

from django.core.exceptions import ImproperlyConfigured


def require_non_empty(values: Mapping[str, object]) -> None:
    """Reject missing, blank, or empty required configuration values."""
    missing = [name for name, value in values.items() if value in (None, "", [], ())]
    if missing:
        raise ImproperlyConfigured(
            "Missing required environment settings: " + ", ".join(sorted(missing))
        )


def require_no_wildcard(name: str, values: Sequence[str]) -> None:
    """Reject wildcard host/origin configuration in production."""
    if "*" in values:
        raise ImproperlyConfigured(f"{name} must not contain '*' in production.")


def require_redis_url(name: str, value: str) -> None:
    """Validate a Redis URL without exposing credentials in errors."""
    parsed = urlparse(value)
    if parsed.scheme not in {"redis", "rediss"} or not parsed.hostname:
        raise ImproperlyConfigured(f"{name} must be a valid redis:// or rediss:// URL.")
