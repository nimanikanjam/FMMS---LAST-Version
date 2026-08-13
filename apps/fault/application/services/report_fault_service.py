"""Service that orchestrates reporting of a new fault.

Cross-domain check performed here:
- Vehicle must exist (verified via IVehicleRepository).

Value-object validation (FaultCode format, FaultDescription length) is
delegated to the domain layer.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from apps.authentication.application.ports.user_profile_reader import IUserProfileReader
from apps.fault.application.dto.fault_dto import (
    FaultItemResponseDTO,
    FaultResponseDTO,
    ReportFaultDTO,
    ReportFaultItemDTO,
)
from apps.fault.application.interfaces.vehicle_odometer_reader import (
    IFaultVehicleOdometerReader,
)
from apps.fault.domain.entities import Fault, FaultItem, FaultStatus
from apps.fault.domain.interfaces.fault_repository import IFaultRepository
from apps.fault.domain.value_objects import FaultCode, FaultDescription, FaultSeverity
from apps.integration.domain.entities import SAPObjectType
from apps.integration.domain.exceptions import SAPIntegrationError
from apps.repair.domain.interfaces.repair_repository import IRepairOrderRepository
from apps.vehicle.domain.interfaces.vehicle_repository import IVehicleRepository
from core.exceptions.translation import load_or_not_found
from core.logging.structured_logger import get_structured_logger
from core.sap.dtos.measurement_document import UpdateVehicleMeasurementRequest
from core.sap.dtos.pm_notification import CreatePMNotificationRequest
from core.sap.ports.measurement_document_port import ISAPMeasurementDocumentPort
from core.sap.ports.pm_notification_port import ISAPPMNotificationPort
from core.sap.ports.sap_transaction_manager_port import ISAPTransactionManager
from core.workflow import assert_vehicle_has_no_open_flow

logger = get_structured_logger("fault", __name__)

_MULTI_FAULT_CODE = "MULTI"
_MULTI_FAULT_DESCRIPTION = "Multiple reported faults"
_SEVERITY_RANK: dict[FaultSeverity, int] = {
    FaultSeverity.LOW: 0,
    FaultSeverity.MEDIUM: 1,
    FaultSeverity.HIGH: 2,
    FaultSeverity.CRITICAL: 3,
}


def _to_response_dto(
    fault: Fault,
    profile_reader: IUserProfileReader | None = None,
) -> FaultResponseDTO:
    """Map a ``Fault`` domain entity to a ``FaultResponseDTO``."""
    created_by = None
    if profile_reader is not None:
        created_by = profile_reader.get_profile(fault.reported_by_id)
    return FaultResponseDTO(
        id=fault.id,
        vehicle_id=fault.vehicle_id,
        code=fault.code.value,
        description=fault.description.value,
        severity=fault.severity,
        status=fault.status,
        reported_by_id=fault.reported_by_id,
        reported_at=fault.reported_at,
        created_at=fault.created_at,
        updated_at=fault.updated_at,
        inspection_id=fault.inspection_id,
        assigned_to_id=fault.assigned_to_id,
        sap_notification_number=fault.sap_notification_number,
        distribution_decision_note=fault.distribution_decision_note,
        items=[
            FaultItemResponseDTO(
                id=item.id,
                component=item.component,
                description=item.description,
                severity=item.severity,
                inspection_item_id=item.inspection_item_id,
            )
            for item in fault.items
        ],
        created_by=created_by,
    )


class ReportFaultService:
    """Orchestrates reporting of a new fault.

    Args:
        fault_repository: Concrete ``IFaultRepository``.
        vehicle_repository: Concrete ``IVehicleRepository`` for cross-domain
            vehicle existence check.
        repair_order_repository: Used to enforce one open fault/repair flow
            per vehicle.
        profile_reader: Optional resolver for ``created_by`` enrichment.
        sap_transaction_manager: Optional SAP write gateway.
        sap_pm_notification_port: Optional SAP PM notification write port.
        sap_measurement_port: Optional SAP measurement document write port.
        odometer_reader: Optional latest odometer read model.
    """

    def __init__(
        self,
        fault_repository: IFaultRepository,
        vehicle_repository: IVehicleRepository,
        repair_order_repository: IRepairOrderRepository,
        profile_reader: IUserProfileReader | None = None,
        sap_transaction_manager: ISAPTransactionManager | None = None,
        sap_pm_notification_port: ISAPPMNotificationPort | None = None,
        sap_measurement_port: ISAPMeasurementDocumentPort | None = None,
        odometer_reader: IFaultVehicleOdometerReader | None = None,
    ) -> None:
        self._fault_repo = fault_repository
        self._vehicle_repo = vehicle_repository
        self._repair_repo = repair_order_repository
        self._profile_reader = profile_reader
        self._sap_tx = sap_transaction_manager
        self._sap_pm_notification = sap_pm_notification_port
        self._sap_measurement = sap_measurement_port
        self._odometer_reader = odometer_reader

    def execute(self, dto: ReportFaultDTO) -> FaultResponseDTO:
        """Report and persist a new fault.

        Args:
            dto: Input data for the fault to report.

        Returns:
            ``FaultResponseDTO`` in OPEN status.

        Raises:
            FMMSNotFoundError: If no vehicle with ``dto.vehicle_id`` exists.
            FMMSStateError: If the vehicle already has an open fault or repair flow.
            ValueError: If ``FaultCode`` or ``FaultDescription`` validation fails.
        """
        logger.info(
            "Reporting fault",
            extra={
                "domain": "fault",
                "service": "ReportFaultService",
                "operation": "execute",
                "request_id": dto.request_id,
                "vehicle_id": str(dto.vehicle_id),
                "severity": dto.severity,
                "item_count": len(dto.items),
            },
        )

        vehicle = load_or_not_found(
            lambda: self._vehicle_repo.get_by_id(dto.vehicle_id),
            message=f"Vehicle '{dto.vehicle_id}' not found.",
            details={"vehicle_id": str(dto.vehicle_id)},
        )

        assert_vehicle_has_no_open_flow(
            dto.vehicle_id,
            fault_repository=self._fault_repo,
            repair_order_repository=self._repair_repo,
        )

        now = datetime.now(tz=UTC)
        fault_id = uuid.uuid4()
        code, description, severity, items = _resolve_fault_payload(
            dto=dto,
            fault_id=fault_id,
            now=now,
        )
        fault = Fault(
            id=fault_id,
            vehicle_id=dto.vehicle_id,
            code=FaultCode(code),
            description=FaultDescription(description),
            severity=severity,
            status=FaultStatus.OPEN,
            reported_by_id=dto.reported_by,
            reported_at=now,
            inspection_id=dto.inspection_id,
            created_at=now,
            updated_at=now,
            items=items,
        )

        saved = self._fault_repo.save(fault)
        sap_notification_number = self._sync_fault_to_sap(
            fault=saved,
            vehicle_number=vehicle.vehicle_number.value,
            request_id=dto.request_id,
        )
        if sap_notification_number:
            saved.link_sap_notification(sap_notification_number)
            saved.updated_at = datetime.now(tz=UTC)
            saved = self._fault_repo.save(saved)

        # Vehicle stays in its current status until distribution confirms the
        # fault (usable/unusable). UNDER_REPAIR is applied later by repair flow.

        logger.info(
            "Fault reported successfully",
            extra={
                "domain": "fault",
                "service": "ReportFaultService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(saved.id),
                "result": "success",
            },
        )

        return _to_response_dto(saved, self._profile_reader)

    def _sync_fault_to_sap(
        self,
        *,
        fault: Fault,
        vehicle_number: str,
        request_id: str,
    ) -> str | None:
        """Create SAP PM notification and update odometer measurement if configured."""
        if self._sap_tx is None or self._sap_pm_notification is None:
            return None

        notification_number = _create_sap_pm_notification(
            sap_tx=self._sap_tx,
            sap_pm_notification=self._sap_pm_notification,
            fault=fault,
            vehicle_number=vehicle_number,
            request_id=request_id,
        )
        if notification_number and self._sap_measurement and self._odometer_reader:
            _update_sap_vehicle_measurement(
                sap_tx=self._sap_tx,
                sap_measurement=self._sap_measurement,
                odometer_reader=self._odometer_reader,
                fault=fault,
                vehicle_number=vehicle_number,
                notification_number=notification_number,
                request_id=request_id,
            )
        return notification_number


def _safe_parent_code(raw: str, fallback: str = _MULTI_FAULT_CODE) -> str:
    """Normalise a catalog code into a valid parent ``FaultCode`` value."""
    cleaned = "".join(ch for ch in raw.strip().upper() if ch.isalnum() or ch == "-")[
        :20
    ]
    if len(cleaned) >= 3:
        return cleaned
    return fallback


def _resolve_fault_payload(
    dto: ReportFaultDTO,
    fault_id: uuid.UUID,
    now: datetime,
) -> tuple[str, str, FaultSeverity, list[FaultItem]]:
    """Derive aggregate fields and child items from the report DTO."""
    if not dto.items:
        return dto.code, dto.description, dto.severity, []

    items = [
        _build_fault_item(fault_id=fault_id, item=item, now=now) for item in dto.items
    ]
    severities = [item.severity for item in dto.items]
    overall_severity = max(severities, key=lambda level: _SEVERITY_RANK[level])

    if len(dto.items) == 1:
        only = dto.items[0]
        code = _safe_parent_code(dto.code.strip() or only.code, fallback="MANUAL")
        description = dto.description.strip() or only.description
        return code, description, overall_severity, items

    code = _safe_parent_code(dto.code.strip() or _MULTI_FAULT_CODE)
    description = dto.description.strip() or _MULTI_FAULT_DESCRIPTION
    return code, description, overall_severity, items


def _build_fault_item(
    fault_id: uuid.UUID,
    item: ReportFaultItemDTO,
    now: datetime,
) -> FaultItem:
    """Construct a ``FaultItem`` from a manual report item DTO."""
    label = (item.component or item.description or item.code).strip()
    component = label[:100] or item.code[:100]
    detail = item.description.strip() or item.code
    if item.code and item.code not in detail:
        detail = f"[{item.code}] {detail}"
    return FaultItem(
        id=uuid.uuid4(),
        fault_id=fault_id,
        component=component,
        description=detail[:500],
        severity=item.severity,
        created_at=now,
        updated_at=now,
    )


def _create_sap_pm_notification(
    *,
    sap_tx: ISAPTransactionManager,
    sap_pm_notification: ISAPPMNotificationPort,
    fault: Fault,
    vehicle_number: str,
    request_id: str,
) -> str | None:
    """Create the SAP PM notification for a fault through the write gateway."""
    create_request = CreatePMNotificationRequest(
        equipment_number=vehicle_number,
        fault_description=fault.description.value,
        defect_code=(
            fault.sap_defect_code.value if fault.sap_defect_code else fault.code.value
        ),
        priority=_sap_priority(fault.severity),
        reported_by=str(fault.reported_by_id),
        reported_at=fault.reported_at,
        notification_type="EM",
    )
    payload = _pm_notification_payload(
        fault=fault,
        request=create_request,
        request_id=request_id,
    )

    def adapter_call(_: dict[str, Any]) -> tuple[dict[str, Any], str]:
        response = sap_pm_notification.create_notification(create_request)
        return (
            {
                "notification_number": response.notification_number,
                "equipment_number": response.equipment_number,
                "status": response.status,
            },
            response.notification_number,
        )

    try:
        _response, sap_document_number = sap_tx.execute(
            object_type=SAPObjectType.FAULT,
            object_id=fault.id,
            idempotency_key=f"fault-pm-notification:{fault.id}",
            request_payload=payload,
            adapter_call=adapter_call,
        )
    except SAPIntegrationError as exc:
        logger.error(
            "SAP PM notification creation failed",
            extra={
                "domain": "fault",
                "fault_id": str(fault.id),
                "request_id": request_id,
                "error": str(exc),
            },
        )
        return None
    return sap_document_number


def _update_sap_vehicle_measurement(
    *,
    sap_tx: ISAPTransactionManager,
    sap_measurement: ISAPMeasurementDocumentPort,
    odometer_reader: IFaultVehicleOdometerReader,
    fault: Fault,
    vehicle_number: str,
    notification_number: str,
    request_id: str,
) -> None:
    """Update SAP with the latest known vehicle odometer at fault-report time."""
    reading = odometer_reader.get_latest(fault.vehicle_id)
    if reading is None:
        logger.warning(
            "Skipping SAP measurement update because vehicle has no odometer reading",
            extra={
                "domain": "fault",
                "fault_id": str(fault.id),
                "vehicle_id": str(fault.vehicle_id),
                "request_id": request_id,
            },
        )
        return

    update_request = UpdateVehicleMeasurementRequest(
        equipment_number=vehicle_number,
        notification_number=notification_number,
        odometer_km=reading.odometer_km,
        recorded_at=fault.reported_at,
        notification_type="EM",
    )
    payload = _measurement_payload(
        fault=fault,
        request=update_request,
        request_id=request_id,
    )

    def adapter_call(_: dict[str, Any]) -> tuple[dict[str, Any], str]:
        response = sap_measurement.update_vehicle_odometer(update_request)
        return (
            {
                "measurement_document_number": response.measurement_document_number,
                "equipment_number": response.equipment_number,
                "notification_number": response.notification_number,
                "odometer_km": response.odometer_km,
            },
            response.measurement_document_number,
        )

    try:
        sap_tx.execute(
            object_type=SAPObjectType.MEASUREMENT_DOCUMENT,
            object_id=fault.id,
            idempotency_key=f"fault-odometer-measurement:{fault.id}",
            request_payload=payload,
            adapter_call=adapter_call,
        )
    except SAPIntegrationError as exc:
        logger.error(
            "SAP vehicle measurement update failed",
            extra={
                "domain": "fault",
                "fault_id": str(fault.id),
                "request_id": request_id,
                "error": str(exc),
            },
        )


def _pm_notification_payload(
    *,
    fault: Fault,
    request: CreatePMNotificationRequest,
    request_id: str,
) -> dict[str, Any]:
    """Build audit/retry payload for SAP PM notification creation."""
    return {
        "fault_id": str(fault.id),
        "request_id": request_id,
        "equipment_number": request.equipment_number,
        "fault_description": request.fault_description,
        "defect_code": request.defect_code,
        "priority": request.priority,
        "reported_by": request.reported_by,
        "reported_at": request.reported_at.isoformat(),
        "notification_type": request.notification_type,
    }


def _measurement_payload(
    *,
    fault: Fault,
    request: UpdateVehicleMeasurementRequest,
    request_id: str,
) -> dict[str, Any]:
    """Build audit/retry payload for SAP vehicle measurement updates."""
    return {
        "fault_id": str(fault.id),
        "request_id": request_id,
        "equipment_number": request.equipment_number,
        "notification_number": request.notification_number,
        "odometer_km": request.odometer_km,
        "recorded_at": request.recorded_at.isoformat(),
        "notification_type": request.notification_type,
    }


def _sap_priority(severity: FaultSeverity) -> str:
    """Map FMMS fault severity to SAP PM priority code."""
    return {
        FaultSeverity.CRITICAL: "1",
        FaultSeverity.HIGH: "2",
        FaultSeverity.MEDIUM: "3",
        FaultSeverity.LOW: "4",
    }[severity]
