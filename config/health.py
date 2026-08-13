"""Minimal unauthenticated health endpoints for container orchestration."""

from __future__ import annotations

from django.core.cache import cache
from django.db import connection
from django.http import HttpRequest, JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET


@never_cache
@require_GET
def liveness(_request: HttpRequest) -> JsonResponse:
    """Report that the Django process can serve HTTP."""
    return JsonResponse({"status": "ok"})


@never_cache
@require_GET
def readiness(_request: HttpRequest) -> JsonResponse:
    """Report whether required database and cache dependencies are usable."""
    checks = {"database": False, "cache": False}
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            checks["database"] = cursor.fetchone() == (1,)
    except Exception:  # Dependency details belong in server logs, not the response.
        checks["database"] = False

    try:
        key = "health:readiness"
        cache.set(key, "ok", timeout=5)
        checks["cache"] = cache.get(key) == "ok"
    except Exception:
        checks["cache"] = False

    ready = all(checks.values())
    return JsonResponse(
        {"status": "ok" if ready else "unavailable", "checks": checks},
        status=200 if ready else 503,
    )
