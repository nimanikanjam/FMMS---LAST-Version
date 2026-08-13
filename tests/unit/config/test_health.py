"""Tests for orchestration health endpoints."""

from unittest.mock import patch

import pytest
from django.test import Client


def test_liveness_has_no_dependency_checks() -> None:
    response = Client().get("/api/health/live/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.django_db
def test_readiness_reports_available_dependencies() -> None:
    response = Client().get("/api/health/ready/")

    assert response.status_code == 200
    assert response.json()["checks"] == {"database": True, "cache": True}


@patch("config.health.cache.set", side_effect=ConnectionError)
@pytest.mark.django_db
def test_readiness_returns_503_when_cache_is_unavailable(_cache_set: object) -> None:
    response = Client().get("/api/health/ready/")

    assert response.status_code == 503
    assert response.json()["status"] == "unavailable"
    assert response.json()["checks"]["cache"] is False
