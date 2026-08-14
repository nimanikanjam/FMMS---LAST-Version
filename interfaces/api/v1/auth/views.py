"""JWT authentication endpoints."""

from __future__ import annotations

from typing import Any

from drf_spectacular.utils import extend_schema
from rest_framework import mixins
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.authentication.infrastructure.models import FMMSUser
from core.permissions import IsAdminRole
from interfaces.api.v1.auth.serializers import (
    FMMSJWTTokenRefreshSerializer,
    TokenObtainPairResponseSerializer,
    TokenRefreshResponseSerializer,
    UserAccountSerializer,
    UsernameTokenObtainPairSerializer,
    UserProfileSerializer,
)
from interfaces.api.v1.schema_tags import API_TAGS


class FMMSJWTTokenObtainPairView(TokenObtainPairView):
    """Issue an access and refresh JWT pair."""

    serializer_class = UsernameTokenObtainPairSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_token_obtain"

    @extend_schema(tags=[API_TAGS.auth], responses=TokenObtainPairResponseSerializer)
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Issue a JWT pair for valid username credentials."""
        return super().post(request, *args, **kwargs)


class FMMSJWTTokenRefreshView(TokenRefreshView):
    """Refresh an FMMS access token."""

    serializer_class = FMMSJWTTokenRefreshSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_token_refresh"

    @extend_schema(tags=[API_TAGS.auth], responses=TokenRefreshResponseSerializer)
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Issue a new access token from a refresh token."""
        return super().post(request, *args, **kwargs)


class CurrentUserView(APIView):
    """Return the authenticated FMMS user profile."""

    permission_classes = [IsAuthenticated]

    @extend_schema(tags=[API_TAGS.auth], responses=UserProfileSerializer)
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Return the current user's session profile."""
        return Response(UserProfileSerializer(request.user).data)


@extend_schema(tags=[API_TAGS.auth])
class UserAccountViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    GenericViewSet,
):
    """Admin-only CRUD for FMMS login accounts.

    No destroy action — accounts are deactivated via ``is_active``
    rather than hard-deleted.
    """

    queryset = FMMSUser.objects.all().order_by("full_name")
    serializer_class = UserAccountSerializer
    permission_classes = [IsAdminRole]
