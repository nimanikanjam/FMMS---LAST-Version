"""Thin repair activity-catalog-option REST API view set."""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from core.permissions import IsReadOnlyOrDriverOrTechnicianOrAbove
from interfaces.api.v1 import deps
from interfaces.api.v1.repair.activity_option_serializers import (
    RepairActivityOptionResponseSerializer,
)
from interfaces.api.v1.schema_tags import API_TAGS
from interfaces.api.v1.utils import paginate_dto_list, request_id_from


class RepairActivityOptionViewSet(GenericViewSet):
    """Expose SAP's activity catalog as the work picker for repair orders.

    Used when a technician records the work performed — offers a standard SAP
    activity code instead of free text.
    """

    permission_classes = [IsReadOnlyOrDriverOrTechnicianOrAbove]

    @extend_schema(
        tags=[API_TAGS.repair],
        responses=RepairActivityOptionResponseSerializer(many=True),
    )
    def list(self, request: Request) -> Response:
        """List active repair activity-catalog options."""
        items = deps.get_list_repair_activity_options_service().execute(
            request_id=request_id_from(request),
        )
        page = paginate_dto_list(self, items)
        serializer = RepairActivityOptionResponseSerializer(
            page if page is not None else items, many=True
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)
