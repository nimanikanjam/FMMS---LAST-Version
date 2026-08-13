"""Central workshop technical inspection decision (repairable / no repair needed)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from apps.fault.application.dto.fault_dto import CloseFaultDTO
from apps.fault.application.services.close_fault_service import CloseFaultService
from apps.fault.domain.exceptions import FaultInvalidStateTransitionError
from apps.fault.domain.interfaces.fault_repository import IFaultRepository
from apps.handover.domain.entities import VehicleHandover, VehicleHandoverStatus
from apps.handover.domain.interfaces.handover_repository import (
    IVehicleHandoverRepository,
)
from apps.repair.application.dto.repair_dto import (
    RepairDecisionResponseDTO,
    SyncRepairToSAPDTO,
    WorkshopTechnicalDecisionDTO,
)
from apps.repair.application.services._timeline_helper import (
    record_repair_timeline_event,
)
from apps.repair.application.services.repair_order_timeline_service import (
    RecordRepairOrderEventService,
)
from apps.repair.application.services.sync_repair_to_sap_service import (
    SyncRepairToSAPService,
)
from apps.repair.domain.entities import (
    RepairOrderEventType,
    RepairOrderStatus,
    WorkshopType,
)
from apps.repair.domain.interfaces.repair_repository import IRepairOrderRepository
from apps.vehicle.domain.entities import VehicleStatus
from apps.vehicle.domain.interfaces.vehicle_repository import IVehicleRepository
from core.exceptions.base_exception import FMMSConflictError
from core.exceptions.translation import load_or_not_found
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("repair", __name__)

_REPAIRABLE_MESSAGE = "نیاز به تعمیر تأیید شد؛ سفارش کار PM ایجاد و تعمیر آغاز شد."
_REPAIRABLE_LOCAL_MESSAGE = (
    "نیاز به تعمیر تأیید شد؛ تعمیر محلی بدون ایجاد سفارش کار SAP آغاز شد."
)
_NO_REPAIR_MESSAGE = "عدم نیاز به تعمیر ثبت شد؛ خودرو به راننده تحویل داده می‌شود."


class WorkshopTechnicalDecisionService:
    """Apply central-workshop technical inspection decision.

    Repairable:
        Create PM Order (via SyncRepairToSAP), move RO to IN_PROGRESS, set
        vehicle UNDER_REPAIR.

    No repair needed (عدم نیاز به تعمیر):
        Terminal NO_REPAIR_NEEDED, close fault, activate vehicle, create
        accepted handover so the driver may exit.
    """

    def __init__(
        self,
        repair_order_repository: IRepairOrderRepository,
        vehicle_repository: IVehicleRepository,
        fault_repository: IFaultRepository,
        sync_repair_to_sap_service: SyncRepairToSAPService | None,
        handover_repository: IVehicleHandoverRepository,
        event_recorder: RecordRepairOrderEventService | None = None,
    ) -> None:
        self._repo = repair_order_repository
        self._vehicle_repo = vehicle_repository
        self._fault_repo = fault_repository
        self._sync_sap = sync_repair_to_sap_service
        self._handover_repo = handover_repository
        self._event_recorder = event_recorder

    def execute(self, dto: WorkshopTechnicalDecisionDTO) -> RepairDecisionResponseDTO:
        """Execute repairable or no-repair-needed decision for INTERNAL orders."""
        order = load_or_not_found(
            lambda: self._repo.get_by_id(dto.repair_order_id),
            message=f"Repair order '{dto.repair_order_id}' not found.",
            details={"repair_order_id": str(dto.repair_order_id)},
        )
        if order.workshop_type != WorkshopType.INTERNAL:
            raise FMMSConflictError(
                message="Technical decision is only allowed for internal workshop.",
                error_code="WORKSHOP_TECHNICAL_DECISION_INTERNAL_ONLY",
                details={
                    "repair_order_id": str(order.id),
                    "workshop_type": (
                        order.workshop_type.value if order.workshop_type else None
                    ),
                },
            )
        if order.status not in (
            RepairOrderStatus.WORKSHOP_ASSIGNED,
            RepairOrderStatus.WAITING_WORKSHOP_CONFIRMATION,
        ):
            raise FMMSConflictError(
                message="Technical decision is only allowed in workshop queue.",
                error_code="WORKSHOP_TECHNICAL_DECISION_INVALID_STATUS",
                details={
                    "repair_order_id": str(order.id),
                    "status": order.status.value,
                },
            )

        if dto.repairable:
            return self._mark_repairable(dto)
        return self._mark_no_repair_needed(dto)

    def _mark_repairable(
        self, dto: WorkshopTechnicalDecisionDTO
    ) -> RepairDecisionResponseDTO:
        """Confirm repair needed, create PM Order, start repair under UNDER_REPAIR."""
        sap_sync_enabled = self._sync_sap is not None
        if self._sync_sap is not None:
            # Create PM Order while still in workshop queue, then start repair.
            self._sync_sap.execute(
                SyncRepairToSAPDTO(
                    repair_order_id=dto.repair_order_id,
                    order_type="PM01",
                    description=dto.note or "Central workshop repair order",
                    planned_start=datetime.now(tz=UTC),
                    request_id=dto.request_id,
                    requested_by=dto.decided_by,
                )
            )

        order = self._repo.get_by_id(dto.repair_order_id)
        order.mark_repairable(dto.note or None)
        order.updated_at = datetime.now(tz=UTC)
        saved = self._repo.save(order)

        vehicle = load_or_not_found(
            lambda: self._vehicle_repo.get_by_id(saved.vehicle_id),
            message=f"Vehicle '{saved.vehicle_id}' not found.",
            details={"vehicle_id": str(saved.vehicle_id)},
        )
        if vehicle.status != VehicleStatus.UNDER_REPAIR:
            vehicle.mark_under_repair()
            vehicle.updated_at = datetime.now(tz=UTC)
            self._vehicle_repo.save(vehicle)

        fault = load_or_not_found(
            lambda: self._fault_repo.get_by_id(saved.fault_id),
            message=f"Fault '{saved.fault_id}' not found.",
            details={"fault_id": str(saved.fault_id)},
        )
        if fault.status.value not in {"IN_REPAIR", "CLOSED"}:
            try:
                fault.start_repair()
                fault.updated_at = datetime.now(tz=UTC)
                self._fault_repo.save(fault)
            except FaultInvalidStateTransitionError:
                logger.info(
                    "Fault could not transition to IN_REPAIR during repairable decision",
                    extra={
                        "domain": "repair",
                        "fault_id": str(fault.id),
                        "fault_status": fault.status.value,
                        "request_id": dto.request_id,
                    },
                )

        record_repair_timeline_event(
            self._event_recorder,
            saved.id,
            RepairOrderEventType.REPAIRABLE_CONFIRMED,
            _REPAIRABLE_MESSAGE if sap_sync_enabled else _REPAIRABLE_LOCAL_MESSAGE,
            created_by_id=dto.decided_by,
            request_id=dto.request_id,
        )
        record_repair_timeline_event(
            self._event_recorder,
            saved.id,
            RepairOrderEventType.REPAIR_STARTED,
            "تعمیر آغاز شد.",
            created_by_id=dto.decided_by,
            request_id=dto.request_id,
        )
        logger.info(
            "Workshop confirmed repairable",
            extra={
                "domain": "repair",
                "service": "WorkshopTechnicalDecisionService",
                "repair_order_id": str(saved.id),
                "sap_order_number": saved.sap_order_number,
                "request_id": dto.request_id,
            },
        )
        return RepairDecisionResponseDTO(
            id=saved.id,
            status=saved.status,
            message=(
                _REPAIRABLE_MESSAGE if sap_sync_enabled else _REPAIRABLE_LOCAL_MESSAGE
            ),
            workshop_type=saved.workshop_type,
            workshop_id=saved.workshop_id,
        )

    def _mark_no_repair_needed(
        self, dto: WorkshopTechnicalDecisionDTO
    ) -> RepairDecisionResponseDTO:
        """Register عدم نیاز به تعمیر and release vehicle to driver."""
        order = self._repo.get_by_id(dto.repair_order_id)
        order.mark_no_repair_needed(dto.note or None)
        order.updated_at = datetime.now(tz=UTC)
        saved = self._repo.save(order)

        CloseFaultService(
            self._fault_repo,
            self._repo,
            self._event_recorder,
        ).execute(
            CloseFaultDTO(
                fault_id=saved.fault_id,
                request_id=dto.request_id,
                closed_by=dto.decided_by,
            )
        )

        vehicle = load_or_not_found(
            lambda: self._vehicle_repo.get_by_id(saved.vehicle_id),
            message=f"Vehicle '{saved.vehicle_id}' not found.",
            details={"vehicle_id": str(saved.vehicle_id)},
        )
        if vehicle.status != VehicleStatus.ACTIVE:
            vehicle.activate()
            vehicle.updated_at = datetime.now(tz=UTC)
            self._vehicle_repo.save(vehicle)

        existing = self._handover_repo.get_by_repair_order(saved.id)
        if existing is None:
            now = datetime.now(tz=UTC)
            self._handover_repo.save(
                VehicleHandover(
                    id=uuid.uuid4(),
                    repair_order_id=saved.id,
                    vehicle_id=saved.vehicle_id,
                    status=VehicleHandoverStatus.ACCEPTED,
                    created_at=now,
                    updated_at=now,
                    confirmed_at=now,
                    comment=dto.note or "عدم نیاز به تعمیر — تحویل مستقیم به راننده",
                    driver_id=dto.decided_by,
                )
            )

        record_repair_timeline_event(
            self._event_recorder,
            saved.id,
            RepairOrderEventType.NO_REPAIR_NEEDED,
            _NO_REPAIR_MESSAGE,
            created_by_id=dto.decided_by,
            request_id=dto.request_id,
        )
        logger.info(
            "Workshop marked no repair needed",
            extra={
                "domain": "repair",
                "service": "WorkshopTechnicalDecisionService",
                "repair_order_id": str(saved.id),
                "request_id": dto.request_id,
            },
        )
        return RepairDecisionResponseDTO(
            id=saved.id,
            status=saved.status,
            message=_NO_REPAIR_MESSAGE,
            workshop_type=saved.workshop_type,
            workshop_id=saved.workshop_id,
        )
