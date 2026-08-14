"""Application services for material requests."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from apps.material.application.dto.material_request_dto import (
    CreateMaterialRequestDTO,
    MaterialRequestDecisionDTO,
    PartsAvailabilityDecisionDTO,
    PartsItemDecisionDTO,
)
from apps.material.application.services.material_request_mapper import (
    to_material_request_response,
)
from apps.material.application.services.parts_availability_decision_service import (
    DecidePartsAvailabilityService,
)
from apps.material.domain.entities import (
    MaterialItemDecision,
    MaterialRequest,
    MaterialRequestItem,
    MaterialRequestStatus,
)
from apps.material.domain.interfaces.central_stock_repository import (
    ICentralStockRepository,
)
from apps.material.domain.interfaces.inventory_availability_port import (
    IInventoryAvailabilityPort,
)
from apps.material.domain.interfaces.material_request_repository import (
    IMaterialRequestRepository,
)
from apps.repair.application.services._timeline_helper import (
    record_repair_timeline_event,
)
from apps.repair.application.services.repair_order_timeline_service import (
    RecordRepairOrderEventService,
)
from apps.repair.domain.entities import RepairOrderEventType
from apps.repair.domain.interfaces.repair_repository import IRepairOrderRepository
from core.exceptions.translation import load_or_not_found


class CreateMaterialRequestService:
    """Create material request linked to a repair order."""

    def __init__(
        self,
        material_request_repository: IMaterialRequestRepository,
        repair_order_repository: IRepairOrderRepository,
        central_stock_repository: ICentralStockRepository | None = None,
        event_recorder: RecordRepairOrderEventService | None = None,
    ) -> None:
        self._repo = material_request_repository
        self._repair_repo = repair_order_repository
        self._stock = central_stock_repository
        self._event_recorder = event_recorder

    def execute(self, dto: CreateMaterialRequestDTO):
        """Create material request in REQUESTED status and pause repair for parts."""
        from apps.repair.domain.entities import RepairOrderStatus  # noqa: PLC0415
        from core.exceptions.base_exception import FMMSConflictError  # noqa: PLC0415

        order = load_or_not_found(
            lambda: self._repair_repo.get_by_id(dto.repair_order_id),
            message=f"Repair order '{dto.repair_order_id}' not found.",
            details={"repair_order_id": str(dto.repair_order_id)},
        )
        if order.status != RepairOrderStatus.IN_PROGRESS:
            raise FMMSConflictError(
                message="Parts can only be requested while repair is in progress.",
                error_code="MATERIAL_REQUEST_REQUIRES_IN_PROGRESS",
                details={
                    "repair_order_id": str(order.id),
                    "status": order.status.value,
                },
            )
        now = datetime.now(tz=UTC)
        material_request = MaterialRequest(
            id=uuid.uuid4(),
            repair_order_id=dto.repair_order_id,
            status=MaterialRequestStatus.REQUESTED,
            created_by_id=dto.requested_by,
            created_at=now,
            updated_at=now,
            items=[
                MaterialRequestItem(
                    id=uuid.uuid4(),
                    material_number=item.material_number,
                    quantity=item.quantity,
                    unit_of_measure=item.unit_of_measure,
                    from_catalog=item.from_catalog,
                )
                for item in dto.items
            ],
        )
        saved = self._repo.save(material_request)
        order.wait_for_parts()
        order.updated_at = now
        self._repair_repo.save(order)
        record_repair_timeline_event(
            self._event_recorder,
            saved.repair_order_id,
            RepairOrderEventType.MATERIAL_REQUESTED,
            "درخواست قطعه ثبت شد؛ تعمیر در انتظار قطعات است.",
            created_by_id=dto.requested_by,
            request_id=dto.request_id,
        )
        return to_material_request_response(saved, self._stock)


class ListMaterialRequestsService:
    """List material requests."""

    def __init__(
        self,
        material_request_repository: IMaterialRequestRepository,
        central_stock_repository: ICentralStockRepository | None = None,
    ) -> None:
        self._repo = material_request_repository
        self._stock = central_stock_repository

    def execute(self, status: MaterialRequestStatus | None = None):
        """List material requests optionally by status."""
        return [
            to_material_request_response(item, self._stock)
            for item in self._repo.list_all(status=status)
        ]


class ApproveMaterialRequestService:
    """Compatibility wrapper: auto-detect availability then decide stock vs purchase."""

    def __init__(
        self,
        material_request_repository: IMaterialRequestRepository,
        inventory_availability_port: IInventoryAvailabilityPort,
        decide_parts_availability_service: DecidePartsAvailabilityService,
        event_recorder: RecordRepairOrderEventService | None = None,
    ) -> None:
        self._repo = material_request_repository
        self._inventory = inventory_availability_port
        self._decide = decide_parts_availability_service
        self._event_recorder = event_recorder

    def execute(self, dto: MaterialRequestDecisionDTO):
        """Approve by inferring per-item availability from the inventory port."""
        _ = self._event_recorder
        material_request = load_or_not_found(
            lambda: self._repo.get_by_id(dto.material_request_id),
            message=f"Material request '{dto.material_request_id}' not found.",
            details={"material_request_id": str(dto.material_request_id)},
        )
        item_decisions = tuple(
            PartsItemDecisionDTO(
                item_id=item.id,
                decision=(
                    MaterialItemDecision.FROM_STOCK
                    if self._inventory.is_available(item)
                    else MaterialItemDecision.PURCHASE
                ),
            )
            for item in material_request.items
        )
        return self._decide.execute(
            PartsAvailabilityDecisionDTO(
                material_request_id=dto.material_request_id,
                items=item_decisions,
                request_id=dto.request_id,
                decided_by=dto.decided_by,
                note="Auto availability decision from inventory check.",
                # Compat approve path uses stub inventory; skip KH08 re-check.
                enforce_stock_check=False,
            )
        )


class ReceiveMaterialRequestService:
    """Workshop confirms physical receipt of parts and resumes repair."""

    def __init__(
        self,
        material_request_repository: IMaterialRequestRepository,
        repair_order_repository: IRepairOrderRepository,
        central_stock_repository: ICentralStockRepository | None = None,
        event_recorder: RecordRepairOrderEventService | None = None,
    ) -> None:
        self._repo = material_request_repository
        self._repair_repo = repair_order_repository
        self._stock = central_stock_repository
        self._event_recorder = event_recorder

    def execute(self, dto: MaterialRequestDecisionDTO):
        """Mark material request received, record consumed parts, resume repair."""
        from apps.repair.domain.entities import (  # noqa: PLC0415
            RepairOrderStatus,
            RepairPart,
        )
        from apps.repair.domain.value_objects import PartQuantity  # noqa: PLC0415
        from core.exceptions.base_exception import FMMSConflictError  # noqa: PLC0415

        material_request = load_or_not_found(
            lambda: self._repo.get_by_id(dto.material_request_id),
            message=f"Material request '{dto.material_request_id}' not found.",
            details={"material_request_id": str(dto.material_request_id)},
        )
        if material_request.status != MaterialRequestStatus.STOCK_ISSUED:
            raise FMMSConflictError(
                message="Parts can only be received after stock issue/transfer to workshop.",
                error_code="MATERIAL_RECEIVE_REQUIRES_STOCK_ISSUED",
                details={
                    "material_request_id": str(material_request.id),
                    "status": material_request.status.value,
                },
            )
        material_request.receive()
        material_request.updated_at = datetime.now(tz=UTC)
        saved = self._repo.save(material_request)

        order = load_or_not_found(
            lambda: self._repair_repo.get_by_id(saved.repair_order_id),
            message=f"Repair order '{saved.repair_order_id}' not found.",
            details={"repair_order_id": str(saved.repair_order_id)},
        )
        for item in saved.items:
            order.add_part(
                RepairPart(
                    id=uuid.uuid4(),
                    part_quantity=PartQuantity(
                        material_number=item.material_number,
                        quantity=int(item.quantity),
                        unit_of_measure=item.unit_of_measure,
                    ),
                )
            )
        if order.status == RepairOrderStatus.WAITING_PARTS:
            order.resume_after_parts()
        order.updated_at = datetime.now(tz=UTC)
        self._repair_repo.save(order)

        record_repair_timeline_event(
            self._event_recorder,
            saved.repair_order_id,
            RepairOrderEventType.PARTS_RECEIVED,
            "دریافت قطعات در تعمیرگاه ثبت شد؛ تعمیر ادامه می‌یابد.",
            created_by_id=dto.decided_by,
            request_id=dto.request_id,
        )
        return to_material_request_response(saved, self._stock)
