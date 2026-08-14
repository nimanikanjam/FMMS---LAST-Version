"""Thin inspection defect-catalog-option REST API view set."""

from __future__ import annotations

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from core.permissions import IsReadOnlyOrDriverOrTechnicianOrAbove
from interfaces.api.v1 import deps
from interfaces.api.v1.inspection.defect_option_serializers import (
    InspectionDefectOptionResponseSerializer,
)
from interfaces.api.v1.schema_tags import API_TAGS
from interfaces.api.v1.utils import paginate_dto_list, request_id_from


class InspectionDefectOptionViewSet(GenericViewSet):
    """Expose SAP's real defect catalog as fault-type options for daily inspection.

    Used when a driver fails a checklist item — offers a proper SAP fault
    type (with severity) instead of a free-text description.
    """

    permission_classes = [IsReadOnlyOrDriverOrTechnicianOrAbove]

    @extend_schema(
        tags=[API_TAGS.inspection],
        parameters=[
            OpenApiParameter(
                name="category",
                required=False,
                type=str,
                description=(
                    "Checklist item category (object-part catalog group text). "
                    "Options are filtered to a matching group_text; if none "
                    "match, the full active catalog is returned instead."
                ),
            ),
        ],
        responses=InspectionDefectOptionResponseSerializer(many=True),
    )
    def list(self, request: Request) -> Response:
        """List active inspection defect-catalog options."""
        items = deps.get_list_inspection_defect_options_service().execute(
            category=request.query_params.get("category", "").strip(),
            request_id=request_id_from(request),
        )
        page = paginate_dto_list(self, items)
        serializer = InspectionDefectOptionResponseSerializer(
            page if page is not None else items, many=True
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)
