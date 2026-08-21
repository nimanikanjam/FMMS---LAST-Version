"""Thin repair REST API view set."""

from __future__ import annotations

import json
import uuid

from django.core.files.storage import default_storage
from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.repair.application.dto.repair_dto import (
    AddRepairActivityDTO,
    AddRepairPartDTO,
    ApproveRepairOrderDTO,
    AssignExternalWorkshopDTO,
    AssignRepairOrderDTO,
    AssignWorkshopDTO,
    CancelExternalWorkshopAssignmentDTO,
    CloseExternalRepairDTO,
    CloseRepairOrderDTO,
    CompleteRepairOrderDTO,
    ConfirmExternalWorkshopDeliveryDTO,
    ConfirmExternalWorkshopPickupDTO,
    CreateRepairOrderDTO,
    DeleteRepairActivityDTO,
    RejectRepairOrderByTransportDTO,
    ReviewExternalRepairDTO,
    SyncRepairToSAPDTO,
    TransportHandoverApproveDTO,
    TransportHandoverRejectDTO,
    UpdateRepairActivityDTO,
    WorkshopTechnicalDecisionDTO,
)
from apps.repair.application.services.register_internal_repair_cost_service import (
    RegisterInternalRepairCostDTO,
)
from apps.repair.domain.entities import (
    ExternalWorkshopReferralStatus,
    RepairOrderStatus,
    WorkshopType,
)
from apps.repair.domain.external_workshop_entities import (
    ExternalWorkshopAssignmentCancellationReason,
    ExternalWorkshopAssignmentStatus,
)
from core.permissions import (
    IsDistributionSupervisorOrAbove,
    IsDriverOrTechnicianOrAbove,
    IsReadOnlyOrTechnicianOrAbove,
    IsTransportSupervisorOrAbove,
    IsWorkshopSupervisorOrAbove,
)
from interfaces.api.v1 import deps
from interfaces.api.v1.material.views import RepairOrderMaterialRequestMixin
from interfaces.api.v1.repair.external_invoice_views import (
    RepairOrderExternalInvoiceMixin,
)
from interfaces.api.v1.repair.serializers import (
    ExternalRepairReviewSerializer,
    ExternalWorkshopAssignmentResponseSerializer,
    ExternalWorkshopAssignSerializer,
    ExternalWorkshopCancelSerializer,
    ExternalWorkshopDeliverySerializer,
    ExternalWorkshopPickupSerializer,
    ExternalWorkshopReferralResponseSerializer,
    InternalRepairCostRegisterSerializer,
    InternalRepairCostResponseSerializer,
    RepairActivityCreateSerializer,
    RepairApproveSerializer,
    RepairAssignSerializer,
    RepairAssignWorkshopSerializer,
    RepairCompleteSerializer,
    RepairDecisionResponseSerializer,
    RepairOrderCreateSerializer,
    RepairOrderResponseSerializer,
    RepairOrderTimelineEventSerializer,
    RepairPartCreateSerializer,
    RepairSyncSAPSerializer,
    RepairTransportRejectSerializer,
    TransportHandoverRejectSerializer,
    WorkshopTechnicalDecisionSerializer,
)
from interfaces.api.v1.schema_tags import API_TAGS
from interfaces.api.v1.utils import paginate_dto_list, request_id_from, user_id_from


def _json_safe_parts(items: list[dict]) -> list[dict]:
    """Convert serializer values to JSON-safe primitive dicts."""
    result: list[dict] = []
    for item in items:
        next_item = dict(item)
        if "quantity" in next_item and next_item["quantity"] is not None:
            next_item["quantity"] = str(next_item["quantity"])
        if "cost" in next_item and next_item["cost"] is not None:
            next_item["cost"] = str(next_item["cost"])
        result.append(next_item)
    return result


def _json_safe_services(items: list[dict]) -> list[dict]:
    """Convert external service rows to JSON-safe primitive dicts."""
    result: list[dict] = []
    for item in items:
        next_item = dict(item)
        if "labor_hours" in next_item and next_item["labor_hours"] is not None:
            next_item["labor_hours"] = str(next_item["labor_hours"])
        if "cost" in next_item and next_item["cost"] is not None:
            next_item["cost"] = str(next_item["cost"])
        result.append(next_item)
    return result


def _review_request_data(request: Request) -> dict:
    """Normalize JSON and multipart review payloads into serializer-friendly data."""
    data = {key: request.data.get(key) for key in request.data.keys()}
    for key in ("repair_services", "replaced_parts"):
        value = data.get(key)
        if isinstance(value, str):
            try:
                data[key] = json.loads(value or "[]")
            except json.JSONDecodeError as exc:
                raise ValidationError({key: "Invalid JSON payload."}) from exc
    return data


def _save_external_invoice_file(request: Request, assignment_id: str) -> str | None:
    uploaded = request.FILES.get("invoice_file")
    if uploaded is None:
        return None
    saved_path = default_storage.save(
        f"external-repair-invoices/{assignment_id}/{uploaded.name}",
        uploaded,
    )
    return default_storage.url(saved_path)


class RepairOrderViewSet(
    RepairOrderMaterialRequestMixin, RepairOrderExternalInvoiceMixin, GenericViewSet
):
    """Expose repair application services through REST endpoints."""

    permission_classes = [IsReadOnlyOrTechnicianOrAbove]

    @extend_schema(tags=[API_TAGS.repair], responses=RepairOrderResponseSerializer)
    def retrieve(self, request: Request, pk: str | None = None) -> Response:
        """Retrieve one repair order."""
        result = deps.get_get_repair_order_service().execute(
            uuid.UUID(str(pk)), request_id_from(request)
        )
        return Response(RepairOrderResponseSerializer(result).data)

    @extend_schema(
        tags=[API_TAGS.repair], responses=RepairOrderResponseSerializer(many=True)
    )
    def list(self, request: Request) -> Response:
        """List repair orders, optionally filtered by vehicle/status/workshop."""
        vehicle_id_raw = request.query_params.get("vehicle_id")
        status_raw = request.query_params.get("status")
        workshop_type_raw = request.query_params.get("workshop_type")
        order_status = RepairOrderStatus(status_raw) if status_raw else None
        workshop_type = (
            WorkshopType(workshop_type_raw) if workshop_type_raw else None
        )
        items = deps.get_list_repair_orders_service().execute(
            uuid.UUID(vehicle_id_raw) if vehicle_id_raw else None,
            status=order_status,
            workshop_type=workshop_type,
            request_id=request_id_from(request),
        )
        page = paginate_dto_list(self, items)
        serializer = RepairOrderResponseSerializer(
            page if page is not None else items, many=True
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @extend_schema(
        tags=[API_TAGS.repair],
        request=RepairOrderCreateSerializer,
        responses=RepairOrderResponseSerializer,
    )
    def create(self, request: Request) -> Response:
        """Create a repair order."""
        serializer = RepairOrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = deps.get_create_repair_order_service().execute(
            CreateRepairOrderDTO(
                vehicle_id=serializer.validated_data["vehicle_id"],
                fault_id=serializer.validated_data["fault_id"],
                request_id=request_id_from(request),
                created_by=user_id_from(request),
            )
        )
        return Response(
            RepairOrderResponseSerializer(result).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        tags=[API_TAGS.repair],
        request=RepairApproveSerializer,
        responses=RepairDecisionResponseSerializer,
    )
    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsTransportSupervisorOrAbove],
    )
    def approve(self, request: Request, pk: str | None = None) -> Response:
        """Transport supervisor approves continuing the repair process."""
        serializer = RepairApproveSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        result = deps.get_approve_repair_order_service().execute(
            ApproveRepairOrderDTO(
                repair_order_id=uuid.UUID(str(pk)),
                request_id=request_id_from(request),
                approved_by=user_id_from(request),
                note=serializer.validated_data.get("note", ""),
            )
        )
        return Response(RepairDecisionResponseSerializer(result).data)

    @extend_schema(
        tags=[API_TAGS.repair],
        request=WorkshopTechnicalDecisionSerializer,
        responses=RepairDecisionResponseSerializer,
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="technical-decision",
        permission_classes=[IsWorkshopSupervisorOrAbove],
    )
    def technical_decision(self, request: Request, pk: str | None = None) -> Response:
        """Central workshop decides repairable vs عدم نیاز به تعمیر."""
        serializer = WorkshopTechnicalDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = deps.get_workshop_technical_decision_service().execute(
            WorkshopTechnicalDecisionDTO(
                repair_order_id=uuid.UUID(str(pk)),
                repairable=serializer.validated_data["repairable"],
                note=serializer.validated_data.get("note", ""),
                estimated_delivery_at=serializer.validated_data.get(
                    "estimated_delivery_at"
                ),
                request_id=request_id_from(request),
                decided_by=user_id_from(request),
            )
        )
        return Response(RepairDecisionResponseSerializer(result).data)

    @extend_schema(
        tags=[API_TAGS.repair],
        request=RepairAssignWorkshopSerializer,
        responses=RepairDecisionResponseSerializer,
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="assign-workshop",
        permission_classes=[IsTransportSupervisorOrAbove],
    )
    def assign_workshop(self, request: Request, pk: str | None = None) -> Response:
        """Transport supervisor selects INTERNAL or EXTERNAL workshop."""
        serializer = RepairAssignWorkshopSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = deps.get_assign_workshop_service().execute(
            AssignWorkshopDTO(
                repair_order_id=uuid.UUID(str(pk)),
                workshop_type=WorkshopType(serializer.validated_data["workshop_type"]),
                workshop_id=serializer.validated_data.get("workshop_id") or None,
                reason=serializer.validated_data.get("reason", ""),
                request_id=request_id_from(request),
                assigned_by=user_id_from(request),
            )
        )
        return Response(RepairDecisionResponseSerializer(result).data)

    @extend_schema(
        tags=[API_TAGS.repair],
        request=ExternalWorkshopAssignSerializer,
        responses=ExternalWorkshopAssignmentResponseSerializer,
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="assign-external-workshop",
        permission_classes=[IsTransportSupervisorOrAbove],
    )
    def assign_external_workshop(
        self, request: Request, pk: str | None = None
    ) -> Response:
        """Transportation assigns an external workshop."""
        serializer = ExternalWorkshopAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = deps.get_assign_external_workshop_service().execute(
            AssignExternalWorkshopDTO(
                repair_order_id=uuid.UUID(str(pk)),
                request_id=request_id_from(request),
                assigned_by=user_id_from(request),
                **serializer.validated_data,
            )
        )
        return Response(ExternalWorkshopAssignmentResponseSerializer(result).data)

    @extend_schema(
        tags=[API_TAGS.repair],
        request=RepairTransportRejectSerializer,
        responses=RepairDecisionResponseSerializer,
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="transport-reject",
        permission_classes=[IsTransportSupervisorOrAbove],
    )
    def transport_reject(self, request: Request, pk: str | None = None) -> Response:
        """Transport supervisor rejects the initial repair request."""
        serializer = RepairTransportRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = deps.get_reject_repair_order_by_transport_service().execute(
            RejectRepairOrderByTransportDTO(
                repair_order_id=uuid.UUID(str(pk)),
                reason=serializer.validated_data["reason"],
                request_id=request_id_from(request),
                rejected_by=user_id_from(request),
            )
        )
        return Response(RepairDecisionResponseSerializer(result).data)

    @extend_schema(
        tags=[API_TAGS.repair],
        request=None,
        responses=RepairDecisionResponseSerializer,
    )
    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsWorkshopSupervisorOrAbove],
    )
    def accept(self, request: Request, pk: str | None = None) -> Response:
        """Compatibility: maps to repairable technical decision."""
        result = deps.get_accept_repair_order_service().execute(
            repair_order_id=uuid.UUID(str(pk)),
            request_id=request_id_from(request),
            accepted_by=user_id_from(request),
        )
        return Response(RepairDecisionResponseSerializer(result).data)

    @extend_schema(
        tags=[API_TAGS.repair],
        request=None,
        responses=RepairDecisionResponseSerializer,
    )
    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsWorkshopSupervisorOrAbove],
    )
    def reject(self, request: Request, pk: str | None = None) -> Response:
        """Compatibility: maps to عدم نیاز به تعمیر."""
        result = deps.get_reject_repair_order_service().execute(
            repair_order_id=uuid.UUID(str(pk)),
            request_id=request_id_from(request),
            rejected_by=user_id_from(request),
        )
        return Response(RepairDecisionResponseSerializer(result).data)

    @extend_schema(
        tags=[API_TAGS.repair],
        request=RepairAssignSerializer,
        responses=RepairOrderResponseSerializer,
    )
    @action(detail=True, methods=["post"])
    def assign(self, request: Request, pk: str | None = None) -> Response:
        """Assign a technician to a repair order."""
        serializer = RepairAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = deps.get_assign_repair_order_service().execute(
            AssignRepairOrderDTO(
                repair_order_id=uuid.UUID(str(pk)),
                technician_id=serializer.validated_data["technician_id"],
                request_id=request_id_from(request),
                assigned_by=user_id_from(request),
            )
        )
        return Response(RepairOrderResponseSerializer(result).data)

    @extend_schema(
        tags=[API_TAGS.repair], request=None, responses=RepairOrderResponseSerializer
    )
    @action(detail=True, methods=["post"])
    @transaction.atomic
    def start(self, request: Request, pk: str | None = None) -> Response:
        """Start work on an assigned repair order."""
        result = deps.get_start_repair_service().execute(
            uuid.UUID(str(pk)),
            request_id_from(request),
            started_by=user_id_from(request),
        )
        return Response(RepairOrderResponseSerializer(result).data)

    @extend_schema(
        tags=[API_TAGS.repair],
        responses=RepairOrderTimelineEventSerializer(many=True),
    )
    @action(detail=True, methods=["get"], url_path="timeline")
    def timeline(self, request: Request, pk: str | None = None) -> Response:
        """Return chronological workflow events for a repair order."""
        events = deps.get_get_repair_order_timeline_service().execute(
            uuid.UUID(str(pk)),
            request_id_from(request),
        )
        return Response(RepairOrderTimelineEventSerializer(events, many=True).data)

    @extend_schema(
        tags=[API_TAGS.repair],
        request=RepairCompleteSerializer,
        responses=RepairOrderResponseSerializer,
    )
    @action(detail=True, methods=["post"])
    @transaction.atomic
    def complete(self, request: Request, pk: str | None = None) -> Response:
        """Complete a repair order."""
        serializer = RepairCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = deps.get_complete_repair_order_service().execute(
            CompleteRepairOrderDTO(
                repair_order_id=uuid.UUID(str(pk)),
                completed_at=serializer.validated_data["completed_at"],
                request_id=request_id_from(request),
                completed_by=user_id_from(request),
                no_parts_consumed=bool(
                    serializer.validated_data.get("no_parts_consumed", False)
                ),
            )
        )
        return Response(RepairOrderResponseSerializer(result).data)

    @extend_schema(
        tags=[API_TAGS.repair], request=None, responses=RepairOrderResponseSerializer
    )
    @action(detail=True, methods=["post"])
    def cancel(self, request: Request, pk: str | None = None) -> Response:
        """Cancel a repair order."""
        result = deps.get_cancel_repair_order_service().execute(
            CloseRepairOrderDTO(
                repair_order_id=uuid.UUID(str(pk)),
                request_id=request_id_from(request),
                requested_by=user_id_from(request),
            )
        )
        return Response(RepairOrderResponseSerializer(result).data)

    @extend_schema(
        tags=[API_TAGS.repair],
        request=RepairActivityCreateSerializer,
        responses=RepairOrderResponseSerializer,
    )
    @action(detail=True, methods=["post"], url_path="activities")
    def activities(self, request: Request, pk: str | None = None) -> Response:
        """Add a repair activity."""
        serializer = RepairActivityCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        performed_by_id = serializer.validated_data.get("performed_by_id")
        performed_at = serializer.validated_data.get("performed_at")
        result = deps.get_add_repair_activity_service().execute(
            AddRepairActivityDTO(
                repair_order_id=uuid.UUID(str(pk)),
                description=serializer.validated_data["description"],
                labor_hours=serializer.validated_data["labor_hours"],
                performed_by_id=performed_by_id or user_id_from(request),
                performed_at=performed_at or timezone.now(),
                request_id=request_id_from(request),
                notes=serializer.validated_data.get("notes") or None,
                activity_code=serializer.validated_data["activity_code"],
                activity_code_group=serializer.validated_data["activity_code_group"],
            )
        )
        return Response(RepairOrderResponseSerializer(result).data)

    @extend_schema(
        tags=[API_TAGS.repair],
        request=RepairActivityCreateSerializer,
        responses=RepairOrderResponseSerializer,
    )
    @action(
        detail=True,
        methods=["patch", "delete"],
        url_path=r"activities/(?P<activity_id>[^/.]+)",
    )
    def update_activity(
        self, request: Request, pk: str | None = None, activity_id: str | None = None
    ) -> Response:
        """Edit or delete a repair activity."""
        if request.method == "DELETE":
            result = deps.get_delete_repair_activity_service().execute(
                DeleteRepairActivityDTO(
                    repair_order_id=uuid.UUID(str(pk)),
                    activity_id=uuid.UUID(str(activity_id)),
                    request_id=request_id_from(request),
                )
            )
            return Response(RepairOrderResponseSerializer(result).data)

        serializer = RepairActivityCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = deps.get_update_repair_activity_service().execute(
            UpdateRepairActivityDTO(
                repair_order_id=uuid.UUID(str(pk)),
                activity_id=uuid.UUID(str(activity_id)),
                description=serializer.validated_data["description"],
                labor_hours=serializer.validated_data["labor_hours"],
                request_id=request_id_from(request),
                notes=serializer.validated_data.get("notes") or None,
                activity_code=serializer.validated_data["activity_code"],
                activity_code_group=serializer.validated_data["activity_code_group"],
            )
        )
        return Response(RepairOrderResponseSerializer(result).data)

    @extend_schema(
        tags=[API_TAGS.repair],
        request=RepairPartCreateSerializer,
        responses=RepairOrderResponseSerializer,
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="parts",
        permission_classes=[IsWorkshopSupervisorOrAbove],
    )
    def parts(self, request: Request, pk: str | None = None) -> Response:
        """Record a consumed spare part (distinct from requested material items)."""
        serializer = RepairPartCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = deps.get_add_repair_part_service().execute(
            AddRepairPartDTO(
                repair_order_id=uuid.UUID(str(pk)),
                material_number=serializer.validated_data["material_number"],
                quantity=serializer.validated_data["quantity"],
                request_id=request_id_from(request),
            )
        )
        return Response(RepairOrderResponseSerializer(result).data)

    @extend_schema(
        tags=[API_TAGS.repair],
        request=InternalRepairCostRegisterSerializer,
        responses=InternalRepairCostResponseSerializer,
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="internal-cost",
        permission_classes=[IsTransportSupervisorOrAbove],
    )
    def internal_cost(self, request: Request, pk: str | None = None) -> Response:
        """Register INTERNAL workshop financial/invoice document."""
        serializer = InternalRepairCostRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = deps.get_register_internal_repair_cost_service().execute(
            RegisterInternalRepairCostDTO(
                repair_order_id=uuid.UUID(str(pk)),
                request_id=request_id_from(request),
                registered_by=user_id_from(request),
                **serializer.validated_data,
            )
        )
        return Response(InternalRepairCostResponseSerializer(result).data)

    @extend_schema(
        tags=[API_TAGS.repair], request=None, responses=RepairOrderResponseSerializer
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="transport-handover-approve",
        permission_classes=[IsTransportSupervisorOrAbove],
    )
    @transaction.atomic
    def transport_handover_approve(
        self, request: Request, pk: str | None = None
    ) -> Response:
        """Transport supervisor approves post-driver handover validation."""
        result = deps.get_approve_transport_handover_service().execute(
            TransportHandoverApproveDTO(
                repair_order_id=uuid.UUID(str(pk)),
                request_id=request_id_from(request),
                approved_by=user_id_from(request),
            )
        )
        return Response(RepairOrderResponseSerializer(result).data)

    @extend_schema(
        tags=[API_TAGS.repair],
        request=TransportHandoverRejectSerializer,
        responses=RepairOrderResponseSerializer,
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="transport-handover-reject",
        permission_classes=[IsTransportSupervisorOrAbove],
    )
    @transaction.atomic
    def transport_handover_reject(
        self, request: Request, pk: str | None = None
    ) -> Response:
        """Transport supervisor rejects post-driver handover validation."""
        serializer = TransportHandoverRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = deps.get_reject_transport_handover_service().execute(
            TransportHandoverRejectDTO(
                repair_order_id=uuid.UUID(str(pk)),
                request_id=request_id_from(request),
                rejected_by=user_id_from(request),
                comment=serializer.validated_data.get("comment") or None,
            )
        )
        return Response(RepairOrderResponseSerializer(result).data)

    @extend_schema(
        tags=[API_TAGS.repair],
        request=RepairSyncSAPSerializer,
        responses=RepairOrderResponseSerializer,
    )
    @action(detail=True, methods=["post"], url_path="sync-sap")
    def sync_sap(self, request: Request, pk: str | None = None) -> Response:
        """Sync a repair order to SAP as a PM order."""
        serializer = RepairSyncSAPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = deps.get_sync_repair_to_sap_service().execute(
            SyncRepairToSAPDTO(
                repair_order_id=uuid.UUID(str(pk)),
                request_id=request_id_from(request),
                requested_by=user_id_from(request),
                **serializer.validated_data,
            )
        )
        return Response(RepairOrderResponseSerializer(result).data)


class ExternalWorkshopReferralViewSet(GenericViewSet):
    """Expose external-workshop referral permission requests."""

    permission_classes = [IsDistributionSupervisorOrAbove]

    @extend_schema(
        tags=[API_TAGS.repair],
        responses=ExternalWorkshopReferralResponseSerializer(many=True),
    )
    def list(self, request: Request) -> Response:
        """List external-workshop referral permission requests."""
        status_raw = request.query_params.get("status")
        items = deps.get_list_external_workshop_referral_requests_service().execute(
            ExternalWorkshopReferralStatus(status_raw) if status_raw else None
        )
        page = paginate_dto_list(self, items)
        serializer = ExternalWorkshopReferralResponseSerializer(
            page if page is not None else items, many=True
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)


class ExternalWorkshopAssignmentViewSet(GenericViewSet):
    """Expose external workshop assignment workflow endpoints."""

    permission_classes = [IsReadOnlyOrTechnicianOrAbove]

    @extend_schema(
        tags=[API_TAGS.repair],
        responses=ExternalWorkshopAssignmentResponseSerializer(many=True),
    )
    def list(self, request: Request) -> Response:
        """List external workshop assignments."""
        status_raw = request.query_params.get("status")
        assignment_status = (
            ExternalWorkshopAssignmentStatus(status_raw) if status_raw else None
        )
        items = deps.get_list_external_workshop_assignments_service().execute(
            assignment_status
        )
        page = paginate_dto_list(self, items)
        serializer = ExternalWorkshopAssignmentResponseSerializer(
            page if page is not None else items, many=True
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @extend_schema(
        tags=[API_TAGS.repair],
        responses=ExternalWorkshopAssignmentResponseSerializer,
    )
    def retrieve(self, request: Request, pk: str | None = None) -> Response:
        """Driver/transport can read full assignment detail."""
        result = deps.get_get_external_workshop_assignment_service().execute(
            uuid.UUID(str(pk))
        )
        return Response(ExternalWorkshopAssignmentResponseSerializer(result).data)

    @extend_schema(
        tags=[API_TAGS.repair],
        request=ExternalWorkshopDeliverySerializer,
        responses=ExternalWorkshopAssignmentResponseSerializer,
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="confirm-delivery",
        permission_classes=[IsDriverOrTechnicianOrAbove],
    )
    def confirm_delivery(self, request: Request, pk: str | None = None) -> Response:
        """Driver confirms delivery to external workshop."""
        serializer = ExternalWorkshopDeliverySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = deps.get_confirm_external_workshop_delivery_service().execute(
            ConfirmExternalWorkshopDeliveryDTO(
                assignment_id=uuid.UUID(str(pk)),
                request_id=request_id_from(request),
                delivered_by=user_id_from(request),
                **serializer.validated_data,
            )
        )
        return Response(ExternalWorkshopAssignmentResponseSerializer(result).data)

    @extend_schema(
        tags=[API_TAGS.repair],
        request=ExternalWorkshopPickupSerializer,
        responses=ExternalWorkshopAssignmentResponseSerializer,
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="confirm-pickup",
        permission_classes=[IsDriverOrTechnicianOrAbove],
    )
    def confirm_pickup(self, request: Request, pk: str | None = None) -> Response:
        """Driver confirms pickup from external workshop."""
        serializer = ExternalWorkshopPickupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = deps.get_confirm_external_workshop_pickup_service().execute(
            ConfirmExternalWorkshopPickupDTO(
                assignment_id=uuid.UUID(str(pk)),
                request_id=request_id_from(request),
                picked_up_by=user_id_from(request),
                **serializer.validated_data,
            )
        )
        return Response(ExternalWorkshopAssignmentResponseSerializer(result).data)

    @extend_schema(
        tags=[API_TAGS.repair],
        request=ExternalRepairReviewSerializer,
        responses=ExternalWorkshopAssignmentResponseSerializer,
    )
    @action(
        detail=True,
        methods=["post", "patch"],
        url_path="review",
        permission_classes=[IsTransportSupervisorOrAbove],
        parser_classes=[JSONParser, MultiPartParser, FormParser],
    )
    def review(self, request: Request, pk: str | None = None) -> Response:
        """Transportation saves external repair review draft."""
        serializer = ExternalRepairReviewSerializer(data=_review_request_data(request))
        serializer.is_valid(raise_exception=True)
        invoice_attachment = _save_external_invoice_file(request, str(pk))
        result = deps.get_review_external_repair_service().execute(
            ReviewExternalRepairDTO(
                assignment_id=uuid.UUID(str(pk)),
                request_id=request_id_from(request),
                reviewed_by=user_id_from(request),
                invoice_attachment=invoice_attachment
                or serializer.validated_data.get("invoice_attachment"),
                repair_services=_json_safe_services(
                    serializer.validated_data.get("repair_services", [])
                ),
                replaced_parts=_json_safe_parts(
                    serializer.validated_data.get("replaced_parts", [])
                ),
                repair_cost=serializer.validated_data.get("repair_cost"),
                additional_notes=serializer.validated_data.get("additional_notes", ""),
            )
        )
        return Response(ExternalWorkshopAssignmentResponseSerializer(result).data)

    @extend_schema(
        tags=[API_TAGS.repair],
        request=None,
        responses=ExternalWorkshopAssignmentResponseSerializer,
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="close",
        permission_classes=[IsTransportSupervisorOrAbove],
    )
    def close(self, request: Request, pk: str | None = None) -> Response:
        """Transportation closes completed external repair workflow."""
        result = deps.get_close_external_repair_service().execute(
            CloseExternalRepairDTO(
                assignment_id=uuid.UUID(str(pk)),
                request_id=request_id_from(request),
                closed_by=user_id_from(request),
            )
        )
        return Response(ExternalWorkshopAssignmentResponseSerializer(result).data)

    @extend_schema(
        tags=[API_TAGS.repair],
        request=ExternalWorkshopCancelSerializer,
        responses=ExternalWorkshopAssignmentResponseSerializer,
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="cancel",
        permission_classes=[IsTransportSupervisorOrAbove],
    )
    def cancel(self, request: Request, pk: str | None = None) -> Response:
        """Cancel external workshop assignment before delivery."""
        serializer = ExternalWorkshopCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = deps.get_cancel_external_workshop_assignment_service().execute(
            CancelExternalWorkshopAssignmentDTO(
                assignment_id=uuid.UUID(str(pk)),
                reason=ExternalWorkshopAssignmentCancellationReason(
                    serializer.validated_data["reason"]
                ),
                note=serializer.validated_data.get("note") or None,
                request_id=request_id_from(request),
                cancelled_by=user_id_from(request),
            )
        )
        return Response(ExternalWorkshopAssignmentResponseSerializer(result).data)
