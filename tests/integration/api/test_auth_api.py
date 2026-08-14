"""API integration tests for JWT authentication endpoints."""

from __future__ import annotations

from datetime import datetime

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from interfaces.api.v1.auth.views import (
    FMMSJWTTokenObtainPairView,
    FMMSJWTTokenRefreshView,
)
from tests.factories.user_factory import FMMSUserFactory

pytestmark = pytest.mark.django_db


class TestAuthTokenAPI:
    """Cover token obtain and refresh flows."""

    def test_obtain_token_with_valid_credentials(self, api_client: APIClient) -> None:
        """Issue access and refresh tokens for a valid username/password."""
        user = FMMSUserFactory(role="ADMIN", password="testpass123!")
        response = api_client.post(
            "/api/v1/auth/token/",
            {"username": user.username, "password": "testpass123!"},
            format="json",
        )
        assert response.status_code == 200
        assert "access" in response.data
        assert "refresh" in response.data
        assert response.data["token_type"] == "Bearer"
        assert datetime.fromisoformat(response.data["access_expires_at"])
        assert datetime.fromisoformat(response.data["refresh_expires_at"])
        assert response.data["user"]["username"] == user.username
        claims = AccessToken(response.data["access"])
        assert claims["user_id"] == str(user.id)
        assert "username" not in claims
        assert "email" not in claims
        assert "full_name" not in claims
        assert "role" not in claims

    def test_obtain_token_rejects_invalid_credentials(
        self, api_client: APIClient
    ) -> None:
        """Reject invalid credentials with 401."""
        user = FMMSUserFactory(role="ADMIN", password="testpass123!")
        response = api_client.post(
            "/api/v1/auth/token/",
            {"username": user.username, "password": "wrong-password"},
            format="json",
        )
        assert response.status_code == 401

    def test_refresh_token(self, api_client: APIClient) -> None:
        """Refresh an access token from a valid refresh token."""
        user = FMMSUserFactory(role="ADMIN", password="testpass123!")
        obtain = api_client.post(
            "/api/v1/auth/token/",
            {"username": user.username, "password": "testpass123!"},
            format="json",
        )
        assert obtain.status_code == 200
        refresh = api_client.post(
            "/api/v1/auth/token/refresh/",
            {"refresh": obtain.data["refresh"]},
            format="json",
        )
        assert refresh.status_code == 200
        assert "access" in refresh.data
        assert refresh.data["token_type"] == "Bearer"
        assert datetime.fromisoformat(refresh.data["access_expires_at"])

    def test_current_user_profile(self, api_client: APIClient) -> None:
        """Return the authenticated user's profile."""
        user = FMMSUserFactory(role="WORKSHOP_SUPERVISOR", password="testpass123!")
        obtain = api_client.post(
            "/api/v1/auth/token/",
            {"username": user.username, "password": "testpass123!"},
            format="json",
        )
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {obtain.data['access']}")
        response = api_client.get("/api/v1/auth/me/")
        assert response.status_code == 200
        assert response.data["username"] == user.username
        assert response.data["role"] == "WORKSHOP_SUPERVISOR"

    def test_auth_token_views_have_scoped_throttling(self) -> None:
        """Token endpoints use dedicated throttle scopes."""
        assert FMMSJWTTokenObtainPairView.throttle_scope == "auth_token_obtain"
        assert FMMSJWTTokenRefreshView.throttle_scope == "auth_token_refresh"
