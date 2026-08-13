"""Unit tests for central workshop technical decision service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from apps.fault.domain.entities import Fault, FaultStatus
from apps.fault.domain.value_objects import FaultCode, FaultDescription, FaultSeverity
from apps.handover.domain.entities import VehicleHandover, VehicleHandoverStatus
from apps.repair.application.dto.repair_dto import (
    RepairOrderResponseDTO,
    SyncRepairToSAPDTO,
    WorkshopTechnicalDecisionDTO,
)
from apps.repair.application.services.workshop_technical_decision_service import (
    WorkshopTechnicalDecisionService,
)
from apps.repair.domain.entities import RepairOrder, RepairOrderStatus, WorkshopType
from apps.vehicle.domain.entities import Vehicle, VehicleStatus
from apps.vehicle.domain.value_objects import PlateNumber, SAPVehicleNumber
from core.exceptions.base_exception import FMMSConflictError


class FakeRepairRepo:
    def __init__(self, orders: list[RepairOrder]) -> None:
        self._orders = {order.id: order for order in orders}

    def get_by_id(self, order_id: uuid.UUID) -> RepairOrder:
        return self._orders[order_id]

    def list_by_fault(self, fault_id: uuid.UUID) -> list[RepairOrder]:
        return [o for o in self._orders.values() if o.fault_id == fault_id]

    def save(self, order: RepairOrder) -> RepairOrder:
        self._orders[order.id] = order
        return order


class FakeVehicleRepo:
    def __init__(self, vehicles: list[Vehicle]) -> None:
        self._vehicles = {vehicle.id: vehicle for vehicle in vehicles}

    def get_by_id(self, vehicle_id: uuid.UUID) -> Vehicle:
        return self._vehicles[vehicle_id]

    def save(self, vehicle: Vehicle) -> Vehicle:
        self._vehicles[vehicle.id] = vehicle
        return vehicle


class FakeFaultRepo:
    def __init__(self, faults: list[Fault]) -> None:
        self._faults = {fault.id: fault for fault in faults}

    def get_by_id(self, fault_id: uuid.UUID) -> Fault:
        return self._faults[fault_id]

    def save(self, fault: Fault) -> Fault:
        self._faults[fault.id] = fault
        return fault


class FakeHandoverRepo:
    def __init__(self) -> None:
        self.items: list[VehicleHandover] = []

    def get_by_repair_order(self, repair_order_id: uuid.UUID) -> VehicleHandover | None:
        for item in self.items:
            if item.repair_order_id == repair_order_id:
                return item
        return None

    def save(self, handover: VehicleHandover) -> VehicleHandover:
        self.items.append(handover)
        return handover


class FakeSyncSap:
    def __init__(self) -> None:
        self.called = False

    def execute(self, dto: SyncRepairToSAPDTO) -> RepairOrderResponseDTO:
        self.called = True
        del dto
        # Caller reloads order after sync; we just mark sap number on the live repo via side effect later.
        raise AssertionError("tests wire sync via side-effect helper")


def _vehicle() -> Vehicle:
    now = datetime.now(tz=UTC)
    return Vehicle(
        id=uuid.uuid4(),
        vehicle_number=SAPVehicleNumber("100001"),
        license_plate=PlateNumber("12B34567"),
        status=VehicleStatus.OUT_OF_SERVICE,
        created_at=now,
        updated_at=now,
    )


def _fault(vehicle_id: uuid.UUID) -> Fault:
    now = datetime.now(tz=UTC)
    return Fault(
        id=uuid.uuid4(),
        vehicle_id=vehicle_id,
        code=FaultCode("F-1"),
        description=FaultDescription("brake issue"),
        severity=FaultSeverity.HIGH,
        status=FaultStatus.AWAITING_TRANSPORT,
        reported_by_id=uuid.uuid4(),
        reported_at=now,
        created_at=now,
        updated_at=now,
    )


def _order(vehicle_id: uuid.UUID, fault_id: uuid.UUID) -> RepairOrder:
    now = datetime.now(tz=UTC)
    return RepairOrder(
        id=uuid.uuid4(),
        vehicle_id=vehicle_id,
        fault_id=fault_id,
        status=RepairOrderStatus.WORKSHOP_ASSIGNED,
        created_by_id=uuid.uuid4(),
        created_at=now,
        updated_at=now,
        workshop_type=WorkshopType.INTERNAL,
    )


class _SyncThatLinksOrder:
    def __init__(self, repair_repo: FakeRepairRepo) -> None:
        self._repo = repair_repo
        self.called = False

    def execute(self, dto: SyncRepairToSAPDTO) -> RepairOrderResponseDTO:
        self.called = True
        order = self._repo.get_by_id(dto.repair_order_id)
        order.link_sap_order("40001234")
        self._repo.save(order)
        return RepairOrderResponseDTO(
            id=order.id,
            vehicle_id=order.vehicle_id,
            fault_id=order.fault_id,
            status=order.status,
            created_by_id=order.created_by_id,
            created_at=order.created_at,
            updated_at=order.updated_at,
            sap_order_number=order.sap_order_number,
            workshop_type=order.workshop_type,
        )


def test_repairable_creates_pm_and_under_repair() -> None:
    vehicle = _vehicle()
    fault = _fault(vehicle.id)
    order = _order(vehicle.id, fault.id)
    repair_repo = FakeRepairRepo([order])
    sync = _SyncThatLinksOrder(repair_repo)
    service = WorkshopTechnicalDecisionService(
        repair_repo,
        FakeVehicleRepo([vehicle]),
        FakeFaultRepo([fault]),
        sync,  # type: ignore[arg-type]
        FakeHandoverRepo(),
    )

    result = service.execute(
        WorkshopTechnicalDecisionDTO(
            repair_order_id=order.id,
            repairable=True,
            request_id="req-1",
            decided_by=uuid.uuid4(),
            note="needs brake work",
        )
    )

    assert result.status == RepairOrderStatus.IN_PROGRESS
    assert sync.called is True
    assert repair_repo.get_by_id(order.id).sap_order_number == "40001234"
    assert vehicle.status == VehicleStatus.UNDER_REPAIR
    assert fault.status == FaultStatus.IN_REPAIR


def test_repairable_without_sap_write_starts_local_repair() -> None:
    vehicle = _vehicle()
    fault = _fault(vehicle.id)
    order = _order(vehicle.id, fault.id)
    repair_repo = FakeRepairRepo([order])
    service = WorkshopTechnicalDecisionService(
        repair_repo,
        FakeVehicleRepo([vehicle]),
        FakeFaultRepo([fault]),
        None,
        FakeHandoverRepo(),
    )

    result = service.execute(
        WorkshopTechnicalDecisionDTO(
            repair_order_id=order.id,
            repairable=True,
            request_id="req-local",
            decided_by=uuid.uuid4(),
            note="local read-only SAP test",
        )
    )

    assert result.status == RepairOrderStatus.IN_PROGRESS
    assert "بدون ایجاد سفارش کار SAP" in result.message
    assert repair_repo.get_by_id(order.id).sap_order_number is None
    assert vehicle.status == VehicleStatus.UNDER_REPAIR
    assert fault.status == FaultStatus.IN_REPAIR


def test_no_repair_needed_releases_vehicle() -> None:
    vehicle = _vehicle()
    fault = _fault(vehicle.id)
    order = _order(vehicle.id, fault.id)
    repair_repo = FakeRepairRepo([order])
    handovers = FakeHandoverRepo()
    service = WorkshopTechnicalDecisionService(
        repair_repo,
        FakeVehicleRepo([vehicle]),
        FakeFaultRepo([fault]),
        _SyncThatLinksOrder(repair_repo),  # type: ignore[arg-type]
        handovers,
    )

    result = service.execute(
        WorkshopTechnicalDecisionDTO(
            repair_order_id=order.id,
            repairable=False,
            request_id="req-2",
            decided_by=uuid.uuid4(),
            note="false alarm",
        )
    )

    assert result.status == RepairOrderStatus.NO_REPAIR_NEEDED
    assert "عدم نیاز به تعمیر" in result.message
    assert vehicle.status == VehicleStatus.ACTIVE
    assert fault.status == FaultStatus.CLOSED
    assert len(handovers.items) == 1
    assert handovers.items[0].status == VehicleHandoverStatus.ACCEPTED


def test_external_workshop_rejected() -> None:
    vehicle = _vehicle()
    fault = _fault(vehicle.id)
    order = _order(vehicle.id, fault.id)
    order.workshop_type = WorkshopType.EXTERNAL
    repair_repo = FakeRepairRepo([order])
    service = WorkshopTechnicalDecisionService(
        repair_repo,
        FakeVehicleRepo([vehicle]),
        FakeFaultRepo([fault]),
        _SyncThatLinksOrder(repair_repo),  # type: ignore[arg-type]
        FakeHandoverRepo(),
    )

    with pytest.raises(FMMSConflictError):
        service.execute(
            WorkshopTechnicalDecisionDTO(
                repair_order_id=order.id,
                repairable=True,
                request_id="req-3",
                decided_by=uuid.uuid4(),
            )
        )
