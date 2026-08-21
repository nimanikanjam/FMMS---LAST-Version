"""Serializers for SAP activity-catalog options offered when recording work."""

from __future__ import annotations

from rest_framework import serializers


class RepairActivityOptionResponseSerializer(serializers.Serializer):
    """Serialize repair activity-catalog option DTOs."""

    id = serializers.UUIDField()
    catalog_type = serializers.CharField()
    code_group = serializers.CharField()
    code = serializers.CharField()
    code_text = serializers.CharField()
    is_active = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
