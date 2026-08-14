"""P0 — API security: role permission matrix and JWT failure scenarios.

Asserts current permission behaviour without changing production code.
"""

from __future__ import annotations

from datetime import timedelta
from typing import cast

import pytest
from django.contrib.auth.base_user import AbstractBaseUser
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from apps.driver.domain.entities import DriverStatus
from apps.driver.infrastructure.models import DriverModel
from tests.factories.user_factory import FMMSUserFactory
from tests.integration.api.conftest import create_vehicle

pytestmark = pytest.mark.django_db


class TestUnauthenticatedAccess:
    """Unauthenticated clients must receive 401 on protected resources."""

    @pytest.mark.parametrize(
        "method,path",
        [
            ("get", "/api/v1/vehicles/"),
            ("get", "/api/v1/drivers/"),
            ("get", "/api/v1/faults/"),
            ("get", "/api/v1/repair-orders/"),
            ("get", "/api/v1/pm-plans/"),
            ("get", "/api/v1/purchase-requisitions/"),
            ("get", "/api/v1/sap-transactions/"),
            ("post", "/api/v1/vehicles/"),
        ],
    )
    def test_unauthenticated_returns_401(
        self, api_client: APIClient, method: str, path: str
    ) -> None:
        """Protected endpoints reject anonymous callers."""
        response = getattr(api_client, method)(path, format="json")
        assert response.status_code == 401
        assert response.data["error_code"] == "AUTHENTICATION_REQUIRED"


class TestViewerPermissions:
    """VIEWER may read; mutating methods require WORKSHOP_SUPERVISOR+."""

    def test_viewer_can_list_vehicles(self, viewer_client: APIClient) -> None:
        """Authenticated viewers may perform SAFE reads."""
        response = viewer_client.get("/api/v1/vehicles/")
        assert response.status_code == 200

    def test_viewer_cannot_create_vehicle(self, viewer_client: APIClient) -> None:
        """VIEWER write attempts are forbidden."""
        response = viewer_client.post(
            "/api/v1/vehicles/",
            {
                "plate_number": "12VIEW01",
                "vin": "1HGCM82633A004399",
                "make": "Toyota",
                "model": "Hilux",
                "year": 2022,
                "category": "LIGHT",
            },
            format="json",
        )
        assert response.status_code == 403
        assert response.data["error_code"] == "PERMISSION_DENIED"

    def test_viewer_cannot_report_fault(
        self, authenticated_client: APIClient, viewer_client: APIClient
    ) -> None:
        """VIEWER cannot create faults."""
        vehicle = create_vehicle(
            authenticated_client, plate="12VIEW02", vin="1HGCM82633A004398"
        )
        response = viewer_client.post(
            "/api/v1/faults/",
            {
                "vehicle_id": vehicle["id"],
                "code": "BRK-01",
                "description": "Brake wear",
                "severity": "MEDIUM",
            },
            format="json",
        )
        assert response.status_code == 403


class TestTechnicianVsSupervisorActions:
    """Supervisor-gated actions: read-only vs. operational-unit-supervisor roles."""

    def test_technician_cannot_create_vehicle(
        self, technician_client: APIClient
    ) -> None:
        """Vehicle creation is SAP-only; manual API create is unavailable."""
        response = technician_client.post(
            "/api/v1/vehicles/",
            {
                "plate_number": "12TECH01",
                "vin": "1HGCM82633A004397",
                "make": "Toyota",
                "model": "Hilux",
                "year": 2022,
                "category": "LIGHT",
            },
            format="json",
        )
        assert response.status_code == 405

    def test_workshop_supervisor_can_change_vehicle_status(
        self, authenticated_client: APIClient, technician_client: APIClient
    ) -> None:
        """WORKSHOP_SUPERVISOR is an operational-unit supervisor and may change status.

        ``technician_client`` is a WORKSHOP_SUPERVISOR-role user in the
        current 6-role model (the old standalone TECHNICIAN role was merged
        into WORKSHOP_SUPERVISOR — see FMMSUserRole), which IS one of the
        supervisor roles IsSupervisorOrAbove grants write access to.
        """
        vehicle = create_vehicle(
            authenticated_client, plate="12TECH02", vin="1HGCM82633A004396"
        )
        response = technician_client.post(
            f"/api/v1/vehicles/{vehicle['id']}/status/",
            {"status": "INACTIVE"},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["status"] == "INACTIVE"

    def test_supervisor_can_change_vehicle_status(
        self, authenticated_client: APIClient, supervisor_client: APIClient
    ) -> None:
        """ADMIN-role users may change vehicle status."""
        vehicle = create_vehicle(
            authenticated_client, plate="12SUP001", vin="1HGCM82633A004395"
        )
        response = supervisor_client.post(
            f"/api/v1/vehicles/{vehicle['id']}/status/",
            {"status": "INACTIVE"},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["status"] == "INACTIVE"

    def test_driver_suspend_endpoint_is_unavailable(
        self, authenticated_client: APIClient, technician_client: APIClient
    ) -> None:
        """Driver status changes are SAP-sync driven, not manual API actions."""
        driver = DriverModel.objects.create(
            customer_number="6000007777",
            name="Ali Driver",
            mobile="09121111111",
            status=DriverStatus.ACTIVE.value,
        )
        response = technician_client.post(
            f"/api/v1/drivers/{driver.id}/suspend/",
            {},
            format="json",
        )
        assert response.status_code == 404


class TestJWTFailureScenarios:
    """JWT obtain/refresh and bearer-token failure paths."""

    def test_invalid_bearer_token_returns_401(self, api_client: APIClient) -> None:
        """Garbage Bearer tokens are rejected."""
        api_client.credentials(HTTP_AUTHORIZATION="Bearer not-a-real-jwt")
        response = api_client.get("/api/v1/vehicles/")
        assert response.status_code == 401

    def test_refresh_with_invalid_token_returns_401(
        self, api_client: APIClient
    ) -> None:
        """Refresh endpoint rejects invalid refresh tokens."""
        response = api_client.post(
            "/api/v1/auth/token/refresh/",
            {"refresh": "invalid.refresh.token"},
            format="json",
        )
        assert response.status_code == 401

    def test_expired_access_token_returns_401(self, api_client: APIClient) -> None:
        """Expired access tokens cannot access protected endpoints."""
        user = cast(
            AbstractBaseUser, FMMSUserFactory(role="ADMIN", password="testpass123!")
        )
        token = AccessToken.for_user(user)
        token.set_exp(lifetime=timedelta(seconds=-60))  # already expired
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        response = api_client.get("/api/v1/vehicles/")
        assert response.status_code == 401

    def test_valid_jwt_access_token_allows_read(self, api_client: APIClient) -> None:
        """A valid access token authenticates API reads."""
        user = cast(
            AbstractBaseUser, FMMSUserFactory(role="VIEWER", password="testpass123!")
        )
        refresh = RefreshToken.for_user(user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        response = api_client.get("/api/v1/vehicles/")
        assert response.status_code == 200
