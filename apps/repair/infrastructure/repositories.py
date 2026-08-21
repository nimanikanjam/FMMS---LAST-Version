"""Concrete Django ORM implementation of IRepairOrderRepository.

``save()`` uses ``transaction.atomic()`` because it writes three tables
atomically: repair_order, repair_activity, and repair_part.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from django.db import transaction

from apps.repair.domain.entities import (
    ExternalWorkshopReferralRequest,
    ExternalWorkshopReferralStatus,
    RepairActivity,
    RepairOrder,
    RepairOrderStatus,
    RepairPart,
    WorkshopType,
)
from apps.repair.domain.exceptions import RepairOrderNotFoundError
from apps.repair.domain.interfaces.external_referral_repository import (
    IExternalWorkshopReferralRepository,
)
from apps.repair.domain.interfaces.repair_repository import IRepairOrderRepository
from apps.repair.domain.value_objects import (
    LaborHours,
    PartQuantity,
    TechnicianAssignment,
)
from apps.repair.infrastructure.models import (
    ExternalWorkshopReferralRequestModel,
    RepairActivityModel,
    RepairOrderModel,
    RepairPartModel,
)
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger(domain="repair", module=__name__)

_TERMINAL_STATUSES = {
    RepairOrderStatus.COMPLETED,
    RepairOrderStatus.CANCELLED,
    RepairOrderStatus.ACCEPTED_BY_DRIVER,
    RepairOrderStatus.REJECTED_BY_DRIVER,
    RepairOrderStatus.REJECTED_BY_TRANSPORT,
    RepairOrderStatus.NO_REPAIR_NEEDED,
}


def _to_domain(
    orm: RepairOrderModel,
    activities: list[RepairActivityModel],
    parts: list[RepairPartModel],
) -> RepairOrder:
    """Map ORM rows to the RepairOrder domain aggregate."""
    assignment: TechnicianAssignment | None = None
    if orm.assigned_technician_id is not None and orm.assigned_at is not None:
        assignment = TechnicianAssignment(
            technician_id=orm.assigned_technician_id,
            assigned_at=orm.assigned_at,
        )

    domain_activities = [
        RepairActivity(
            id=a.activity_id,
            description=a.description,
            labor_hours=LaborHours(hours=a.labor_hours),
            performed_by_id=a.performed_by_id,
            performed_at=a.performed_at,
            notes=a.notes or None,
            activity_code=a.activity_code,
            activity_code_group=a.activity_code_group,
        )
        for a in activities
    ]

    domain_parts = [
        RepairPart(
            id=p.part_id,
            part_quantity=PartQuantity(
                material_number=p.material_number,
                quantity=p.quantity,
                unit_of_measure=p.unit_of_measure,
            ),
            goods_issue_id=p.goods_issue_id,
            posted_at=p.posted_at,
        )
        for p in parts
    ]

    return RepairOrder(
        id=uuid.UUID(str(orm.id)),
        vehicle_id=orm.vehicle_id,
        fault_id=orm.fault_id,
        status=RepairOrderStatus(orm.status),
        created_by_id=orm.initiator_id,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
        assignment=assignment,
        activities=domain_activities,
        parts=domain_parts,
        sap_order_number=orm.sap_order_number or None,
        workshop_type=WorkshopType(orm.workshop_type) if orm.workshop_type else None,
        workshop_id=orm.workshop_id or None,
        transport_rejection_reason=orm.transport_rejection_reason or None,
        transport_approval_note=orm.transport_approval_note or None,
        workshop_decision_note=orm.workshop_decision_note or None,
        completed_at=orm.completed_at,
        estimated_delivery_at=orm.estimated_delivery_at,
    )


def _referral_to_domain(
    orm: ExternalWorkshopReferralRequestModel,
) -> ExternalWorkshopReferralRequest:
    """Map an external referral ORM row to its domain entity."""
    return ExternalWorkshopReferralRequest(
        id=uuid.UUID(str(orm.id)),
        repair_order_id=orm.repair_order_id,
        vehicle_id=orm.vehicle_id,
        fault_id=orm.fault_id,
        status=ExternalWorkshopReferralStatus(orm.status),
        workshop_id=orm.workshop_id or None,
        reason=orm.reason,
        requested_by_id=orm.requested_by_id,
        requested_at=orm.requested_at,
        approved_by_id=orm.approved_by_id,
        approved_at=orm.approved_at,
        rejected_by_id=orm.rejected_by_id,
        rejected_at=orm.rejected_at,
        rejection_reason=orm.rejection_reason or None,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


def _fetch_orm(order_id: uuid.UUID) -> RepairOrderModel:
    """Fetch a non-deleted RepairOrderModel or raise RepairOrderNotFoundError."""
    try:
        return RepairOrderModel.objects.get(id=order_id, is_deleted=False)
    except RepairOrderModel.DoesNotExist:
        raise RepairOrderNotFoundError(order_id) from None


class DjangoRepairOrderRepository(IRepairOrderRepository):
    """Concrete repository for RepairOrder aggregates backed by Django ORM.

    All writes are wrapped in ``transaction.atomic()`` to guarantee that the
    parent record and all child rows (activities, parts) are saved together.
    """

    def get_by_id(self, order_id: uuid.UUID) -> RepairOrder:
        """Retrieve a repair order by UUID, including activities and parts."""
        orm = _fetch_orm(order_id)
        return _to_domain(orm, list(orm.activities.all()), list(orm.parts.all()))

    def list_by_vehicle(
        self,
        vehicle_id: uuid.UUID,
        status: RepairOrderStatus | None = None,
    ) -> list[RepairOrder]:
        """Return repair orders for a vehicle, optionally filtered by status."""
        qs = RepairOrderModel.objects.filter(vehicle_id=vehicle_id, is_deleted=False)
        if status is not None:
            qs = qs.filter(status=status.value)
        return [
            _to_domain(orm, list(orm.activities.all()), list(orm.parts.all()))
            for orm in qs
        ]

    def list_by_fault(self, fault_id: uuid.UUID) -> list[RepairOrder]:
        """Return all repair orders linked to a fault."""
        qs = RepairOrderModel.objects.filter(fault_id=fault_id, is_deleted=False)
        return [
            _to_domain(orm, list(orm.activities.all()), list(orm.parts.all()))
            for orm in qs
        ]

    def list_all(
        self,
        status: RepairOrderStatus | None = None,
        workshop_type: WorkshopType | None = None,
    ) -> list[RepairOrder]:
        """Return all non-deleted repair orders, optionally filtered."""
        qs = RepairOrderModel.objects.filter(is_deleted=False).order_by("-created_at")
        if status is not None:
            qs = qs.filter(status=status.value)
        if workshop_type is not None:
            qs = qs.filter(workshop_type=workshop_type.value)
        return [
            _to_domain(orm, list(orm.activities.all()), list(orm.parts.all()))
            for orm in qs
        ]

    def list_active_by_vehicle(self, vehicle_id: uuid.UUID) -> list[RepairOrder]:
        """Return all non-terminal repair orders for a vehicle.

        Used by Application Service to enforce the cross-domain invariant
        "vehicle cannot be deactivated with active repair orders".
        """
        terminal = [s.value for s in _TERMINAL_STATUSES]
        qs = RepairOrderModel.objects.filter(
            vehicle_id=vehicle_id, is_deleted=False
        ).exclude(status__in=terminal)
        return [
            _to_domain(orm, list(orm.activities.all()), list(orm.parts.all()))
            for orm in qs
        ]

    def has_open_repair_order_for_vehicle(self, vehicle_id: uuid.UUID) -> bool:
        """Return True when the vehicle has any non-terminal repair order."""
        terminal = [s.value for s in _TERMINAL_STATUSES]
        return (
            RepairOrderModel.objects.filter(vehicle_id=vehicle_id, is_deleted=False)
            .exclude(status__in=terminal)
            .exists()
        )

    def save(self, order: RepairOrder) -> RepairOrder:
        """Atomically persist the repair order aggregate and all child rows."""
        with transaction.atomic():
            obj, created = RepairOrderModel.objects.update_or_create(
                id=order.id,
                defaults={
                    "vehicle_id": order.vehicle_id,
                    "fault_id": order.fault_id,
                    "status": order.status.value,
                    "initiator_id": order.created_by_id,
                    "sap_order_number": order.sap_order_number or "",
                    "workshop_type": (
                        order.workshop_type.value if order.workshop_type else ""
                    ),
                    "workshop_id": order.workshop_id or "",
                    "transport_rejection_reason": (
                        order.transport_rejection_reason or ""
                    ),
                    "transport_approval_note": order.transport_approval_note or "",
                    "workshop_decision_note": order.workshop_decision_note or "",
                    "completed_at": order.completed_at,
                    "estimated_delivery_at": order.estimated_delivery_at,
                    "assigned_technician_id": (
                        order.assignment.technician_id if order.assignment else None
                    ),
                    "assigned_at": (
                        order.assignment.assigned_at if order.assignment else None
                    ),
                    "updated_at": datetime.now(tz=UTC),
                },
            )
            if created:
                obj.created_at = order.created_at
                obj.save(update_fields=["created_at"])

            obj.activities.all().delete()
            RepairActivityModel.objects.bulk_create(
                [
                    RepairActivityModel(
                        repair_order=obj,
                        activity_id=a.id,
                        description=a.description,
                        labor_hours=a.labor_hours.hours,
                        performed_by_id=a.performed_by_id,
                        performed_at=a.performed_at,
                        notes=a.notes or "",
                        activity_code=a.activity_code,
                        activity_code_group=a.activity_code_group,
                    )
                    for a in order.activities
                ]
            )

            obj.parts.all().delete()
            RepairPartModel.objects.bulk_create(
                [
                    RepairPartModel(
                        repair_order=obj,
                        part_id=p.id,
                        material_number=p.part_quantity.material_number,
                        quantity=p.part_quantity.quantity,
                        unit_of_measure=p.part_quantity.unit_of_measure,
                        goods_issue_id=p.goods_issue_id,
                        posted_at=p.posted_at,
                    )
                    for p in order.parts
                ]
            )

        logger.debug("saved", extra={"order_id": str(order.id), "is_new": created})
        return order

    def delete(self, order_id: uuid.UUID) -> None:
        """Soft-delete a repair order record."""
        updated = RepairOrderModel.objects.filter(id=order_id, is_deleted=False).update(
            is_deleted=True,
            deleted_at=datetime.now(tz=UTC),
        )
        if updated == 0:
            raise RepairOrderNotFoundError(order_id)


class DjangoExternalWorkshopReferralRepository(IExternalWorkshopReferralRepository):
    """Django repository for external-workshop referral requests."""

    def get_by_id(self, request_id: uuid.UUID) -> ExternalWorkshopReferralRequest:
        """Return one referral request by ID."""
        try:
            orm = ExternalWorkshopReferralRequestModel.objects.get(
                id=request_id,
                is_deleted=False,
            )
        except ExternalWorkshopReferralRequestModel.DoesNotExist:
            raise RepairOrderNotFoundError(request_id) from None
        return _referral_to_domain(orm)

    def get_open_by_repair_order(
        self, repair_order_id: uuid.UUID
    ) -> ExternalWorkshopReferralRequest | None:
        """Return the active referral request for a repair order, when present."""
        orm = (
            ExternalWorkshopReferralRequestModel.objects.filter(
                repair_order_id=repair_order_id,
                status=ExternalWorkshopReferralStatus.REQUESTED.value,
                is_deleted=False,
            )
            .order_by("-created_at")
            .first()
        )
        return _referral_to_domain(orm) if orm is not None else None

    def list_all(
        self,
        status: ExternalWorkshopReferralStatus | None = None,
    ) -> list[ExternalWorkshopReferralRequest]:
        """Return referral requests, newest first."""
        qs = ExternalWorkshopReferralRequestModel.objects.filter(
            is_deleted=False
        ).order_by("-requested_at")
        if status is not None:
            qs = qs.filter(status=status.value)
        return [_referral_to_domain(row) for row in qs]

    def save(
        self,
        request: ExternalWorkshopReferralRequest,
    ) -> ExternalWorkshopReferralRequest:
        """Persist a referral request."""
        obj, created = ExternalWorkshopReferralRequestModel.objects.update_or_create(
            id=request.id,
            defaults={
                "repair_order_id": request.repair_order_id,
                "vehicle_id": request.vehicle_id,
                "fault_id": request.fault_id,
                "status": request.status.value,
                "workshop_id": request.workshop_id or "",
                "reason": request.reason,
                "requested_by_id": request.requested_by_id,
                "requested_at": request.requested_at,
                "approved_by_id": request.approved_by_id,
                "approved_at": request.approved_at,
                "rejected_by_id": request.rejected_by_id,
                "rejected_at": request.rejected_at,
                "rejection_reason": request.rejection_reason or "",
                "updated_at": datetime.now(tz=UTC),
            },
        )
        if created:
            obj.created_at = request.created_at
            obj.save(update_fields=["created_at"])
        return request
