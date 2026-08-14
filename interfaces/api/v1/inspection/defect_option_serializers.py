"""Serializers for inspection defect-catalog option API v1."""

from __future__ import annotations

from rest_framework import serializers


class InspectionDefectOptionResponseSerializer(serializers.Serializer):
    """Serialize SAP-synced inspection defect-catalog option DTOs."""

    id = serializers.UUIDField()
    code_group = serializers.CharField()
    code = serializers.CharField()
    group_text = serializers.CharField()
    code_text = serializers.CharField()
    defect_class = serializers.CharField()
    defect_class_text = serializers.CharField()
    is_active = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
