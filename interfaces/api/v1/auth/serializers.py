"""Authentication serializers for API v1."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from rest_framework import serializers
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer,
)
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken, Token

from apps.authentication.infrastructure.models import FMMSUser, FMMSUserRole

_TOKEN_TYPE = "Bearer"


def _resolve_assigned_vehicle_plate(assigned_vehicle_id: Any) -> str | None:
    """Best-effort lookup of the license plate for an admin-assigned vehicle.

    Cross-domain by ID only — never imports the vehicle app's ORM models.
    Returns None if unassigned or if the vehicle app is unreachable.
    """
    if not assigned_vehicle_id:
        return None
    try:
        from interfaces.api.v1 import deps  # noqa: PLC0415

        vehicle = deps.get_vehicle_repository().get_by_id(assigned_vehicle_id)
    except Exception:  # noqa: BLE001 — profile must not fail if vehicle lookup errors
        return None
    return vehicle.license_plate.value


def _expires_at(token: Token) -> str:
    """Return the JWT expiration timestamp as an ISO-8601 UTC string."""
    return datetime.fromtimestamp(int(token["exp"]), tz=UTC).isoformat()


class UsernameTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Obtain JWTs using FMMS username credentials."""

    username_field = "username"

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Return tokens, expiry metadata, and the authenticated user profile."""
        data = super().validate(attrs)
        data["token_type"] = _TOKEN_TYPE
        data["access_expires_at"] = _expires_at(AccessToken(data["access"]))
        data["refresh_expires_at"] = _expires_at(RefreshToken(data["refresh"]))
        data["user"] = UserProfileSerializer(self.user).data
        return data


class FMMSJWTTokenRefreshSerializer(TokenRefreshSerializer):
    """Refresh access tokens and return frontend-friendly expiry metadata."""

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Return a refreshed access token plus its expiration timestamp."""
        data = super().validate(attrs)
        data["token_type"] = _TOKEN_TYPE
        data["access_expires_at"] = _expires_at(AccessToken(data["access"]))
        return data


class LinkedDriverSerializer(serializers.Serializer):
    """SAP driver linked to the login user via personnel number."""

    id = serializers.UUIDField()
    customer_number = serializers.CharField()
    name = serializers.CharField()
    personnel_number = serializers.CharField(allow_blank=True)


class UserProfileSerializer(serializers.Serializer):
    """Serialize the authenticated FMMS user for frontend session state."""

    id = serializers.UUIDField(read_only=True)
    username = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    full_name = serializers.CharField(read_only=True)
    role = serializers.CharField(read_only=True)
    personnel_number = serializers.CharField(read_only=True, allow_blank=True)
    is_staff = serializers.BooleanField(read_only=True)
    is_superuser = serializers.BooleanField(read_only=True)
    linked_driver = LinkedDriverSerializer(read_only=True, allow_null=True, required=False)
    assigned_vehicle_id = serializers.UUIDField(read_only=True, allow_null=True, required=False)
    assigned_vehicle_plate = serializers.CharField(read_only=True, allow_null=True, required=False)

    def to_representation(self, instance: Any) -> dict[str, Any]:
        """Include SAP driver link and admin-assigned vehicle plate when present."""
        data = super().to_representation(instance)
        data["assigned_vehicle_plate"] = _resolve_assigned_vehicle_plate(
            getattr(instance, "assigned_vehicle_id", None)
        )
        personnel = str(getattr(instance, "personnel_number", "") or "").strip()
        data["personnel_number"] = personnel
        data["linked_driver"] = None
        if not personnel:
            return data
        try:
            from interfaces.api.v1 import deps  # noqa: PLC0415

            driver = deps.get_driver_repository().find_by_personnel_number(personnel)
        except Exception:  # noqa: BLE001 — profile must not fail if driver sync is down
            return data
        if driver is None:
            return data
        data["linked_driver"] = {
            "id": driver.id,
            "customer_number": driver.customer_number.value,
            "name": driver.name,
            "personnel_number": driver.personnel_number or "",
        }
        return data


class TokenObtainPairResponseSerializer(serializers.Serializer):
    """Document token obtain response fields."""

    access = serializers.CharField()
    refresh = serializers.CharField()
    token_type = serializers.CharField()
    access_expires_at = serializers.DateTimeField()
    refresh_expires_at = serializers.DateTimeField()
    user = UserProfileSerializer()


class TokenRefreshResponseSerializer(serializers.Serializer):
    """Document token refresh response fields."""

    access = serializers.CharField()
    token_type = serializers.CharField()
    access_expires_at = serializers.DateTimeField()


class UserAccountSerializer(serializers.ModelSerializer):
    """Admin-facing CRUD serializer for FMMS login accounts.

    ``assigned_vehicle_id`` is a loose cross-domain reference (no FK) that
    lets an admin manually pin a vehicle/plate to a user, independent of
    the SAP personnel-number driver linkage.
    """

    password = serializers.CharField(
        write_only=True, required=False, allow_blank=True, style={"input_type": "password"}
    )
    assigned_vehicle_plate = serializers.SerializerMethodField()

    class Meta:
        model = FMMSUser
        fields = [
            "id",
            "username",
            "email",
            "full_name",
            "role",
            "personnel_number",
            "assigned_vehicle_id",
            "assigned_vehicle_plate",
            "is_active",
            "password",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_assigned_vehicle_plate(self, instance: FMMSUser) -> str | None:
        """Resolve the license plate for the assigned vehicle, if any."""
        return _resolve_assigned_vehicle_plate(instance.assigned_vehicle_id)

    def validate_role(self, value: str) -> str:
        """Restrict role to known FMMS roles."""
        if value not in FMMSUserRole.values:
            raise serializers.ValidationError("Unknown role.")
        return value

    def validate_personnel_number(self, value: str) -> str:
        """Every FMMS user is tied to a SAP personnel number — never optional."""
        if not value.strip():
            raise serializers.ValidationError("Personnel number is required.")
        return value

    def create(self, validated_data: dict[str, Any]) -> FMMSUser:
        """Create a user via the manager so the password is hashed."""
        password = validated_data.pop("password", "") or None
        return FMMSUser.objects.create_user(
            username=validated_data.pop("username"),
            email=validated_data.pop("email"),
            full_name=validated_data.pop("full_name"),
            password=password,
            **validated_data,
        )

    def update(self, instance: FMMSUser, validated_data: dict[str, Any]) -> FMMSUser:
        """Update account fields; only touch the password when provided."""
        password = validated_data.pop("password", "")
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance
