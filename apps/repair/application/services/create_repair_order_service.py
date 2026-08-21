"""Repair-order creation entrypoint (distribution-only).

Direct API creation is closed. Distribution creates orders via
``DistributionFaultDecisionService.mark_unusable``.
"""

from __future__ import annotations

from apps.fault.domain.interfaces.fault_repository import IFaultRepository
from apps.repair.application.dto.repair_dto import (
    CreateRepairOrderDTO,
    RepairOrderResponseDTO,
)
from apps.repair.application.services.repair_order_timeline_service import (
    RecordRepairOrderEventService,
)
from apps.repair.domain.entities import RepairOrder
from apps.repair.domain.interfaces.repair_repository import IRepairOrderRepository
from apps.vehicle.domain.interfaces.vehicle_repository import IVehicleRepository
from core.exceptions.base_exception import FMMSConflictError
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("repair", __name__)


def _to_response_dto(order: RepairOrder) -> RepairOrderResponseDTO:
    """Map a ``RepairOrder`` domain entity → ``RepairOrderResponseDTO``."""
    from apps.repair.application.dto.repair_dto import (  # noqa: PLC0415
        RepairActivityResponseDTO,
        RepairPartResponseDTO,
    )

    return RepairOrderResponseDTO(
        id=order.id,
        vehicle_id=order.vehicle_id,
        fault_id=order.fault_id,
        status=order.status,
        created_by_id=order.created_by_id,
        created_at=order.created_at,
        updated_at=order.updated_at,
        completed_at=order.completed_at,
        estimated_delivery_at=order.estimated_delivery_at,
        sap_order_number=order.sap_order_number,
        workshop_type=order.workshop_type,
        workshop_id=order.workshop_id,
        transport_rejection_reason=order.transport_rejection_reason,
        transport_approval_note=order.transport_approval_note,
        workshop_decision_note=order.workshop_decision_note,
        technician_id=order.assignment.technician_id if order.assignment else None,
        assigned_at=order.assignment.assigned_at if order.assignment else None,
        activities=[
            RepairActivityResponseDTO(
                id=a.id,
                description=a.description,
                labor_hours=a.labor_hours.hours,
                performed_by_id=a.performed_by_id,
                performed_at=a.performed_at,
                notes=a.notes,
                activity_code=a.activity_code,
                activity_code_group=a.activity_code_group,
            )
            for a in order.activities
        ],
        parts=[
            RepairPartResponseDTO(
                id=p.id,
                material_number=p.part_quantity.material_number,
                quantity=p.part_quantity.quantity,
                unit_of_measure=p.part_quantity.unit_of_measure,
                goods_issue_id=p.goods_issue_id,
                posted_at=p.posted_at,
            )
            for p in order.parts
        ],
    )


class CreateRepairOrderService:
    """Reject direct repair-order creation; keep wiring for dependency injection.

    Args:
        repair_order_repository: Concrete ``IRepairOrderRepository``.
        vehicle_repository: Concrete ``IVehicleRepository``.
        fault_repository: Concrete ``IFaultRepository``.
        event_recorder: Optional timeline recorder (unused; kept for DI compat).
    """

    def __init__(
        self,
        repair_order_repository: IRepairOrderRepository,
        vehicle_repository: IVehicleRepository,
        fault_repository: IFaultRepository,
        event_recorder: RecordRepairOrderEventService | None = None,
    ) -> None:
        self._repair_repo = repair_order_repository
        self._vehicle_repo = vehicle_repository
        self._fault_repo = fault_repository
        self._event_recorder = event_recorder

    def execute(self, dto: CreateRepairOrderDTO) -> RepairOrderResponseDTO:
        """Reject direct repair-order creation.

        Repair orders are created only by distribution when a fault vehicle is
        marked unusable. Direct ``POST /repair-orders/`` is closed.

        Args:
            dto: Input data (used only for logging/details).

        Raises:
            FMMSConflictError: Always — creation is distribution-only.
        """
        logger.info(
            "Rejecting direct repair order creation",
            extra={
                "domain": "repair",
                "service": "CreateRepairOrderService",
                "operation": "execute",
                "request_id": dto.request_id,
                "vehicle_id": str(dto.vehicle_id),
                "fault_id": str(dto.fault_id),
            },
        )
        raise FMMSConflictError(
            message=(
                "Repair orders are created only when distribution marks the "
                "vehicle as unusable."
            ),
            error_code="REPAIR_ORDER_CREATE_VIA_DISTRIBUTION_ONLY",
            details={
                "vehicle_id": str(dto.vehicle_id),
                "fault_id": str(dto.fault_id),
            },
        )
