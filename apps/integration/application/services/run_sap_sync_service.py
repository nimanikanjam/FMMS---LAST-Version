"""Application service for running all SAP read synchronisations."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

from django.db import transaction

from apps.fault.application.services.sync_fault_catalog_from_sap_service import (
    SyncFaultCatalogFromSAPService,
)
from apps.inspection.application.services.sync_inspection_defect_options_from_sap_service import (
    SyncInspectionDefectOptionsFromSAPService,
)
from apps.inspection.application.services.sync_inspection_templates_from_sap_service import (
    SyncInspectionTemplatesFromSAPService,
)
from apps.integration.infrastructure.models import SAPSyncRunItemModel, SAPSyncRunModel
from apps.material.application.services.sync_central_stock_from_sap_service import (
    SyncCentralStockFromSAPService,
)
from apps.repair.application.services.sync_repair_activity_options_from_sap_service import (
    SyncRepairActivityOptionsFromSAPService,
)
from apps.vehicle.application.services.sync_vehicles_from_sap_service import (
    SyncVehiclesFromSAPService,
)
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("integration", __name__)

SAP_SYNC_SUCCESS = "SUCCESS"
SAP_SYNC_FAILED = "FAILED"
SAP_SYNC_PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
SAP_SYNC_IN_PROGRESS = "IN_PROGRESS"
SAP_SYNC_TRIGGER_API = "API"
SAP_SYNC_TRIGGER_CELERY = "CELERY"
SAP_SYNC_TRIGGER_JOB = "JOB"
SAP_SYNC_TRIGGER_SOURCES = frozenset(
    {SAP_SYNC_TRIGGER_API, SAP_SYNC_TRIGGER_CELERY, SAP_SYNC_TRIGGER_JOB}
)


@dataclass(frozen=True)
class SAPSyncItemResultDTO:
    """Result of one SAP read synchronisation."""

    name: str
    status: str
    started_at: datetime
    finished_at: datetime
    summary: dict[str, Any]
    error: str | None = None


@dataclass(frozen=True)
class RunSAPSyncResultDTO:
    """Result of the global SAP read synchronisation run."""

    id: str
    trigger_source: str
    status: str
    started_at: datetime
    finished_at: datetime
    items: list[SAPSyncItemResultDTO]


class RunSAPSyncService:
    """Run every currently supported SAP read sync in a single workflow.

    Args:
        vehicle_sync_service: Imports vehicle and driver master data from SAP.
        inspection_template_sync_service: Imports inspection templates from SAP.
        fault_catalog_sync_service: Imports fault catalog rows from SAP.
        inspection_defect_option_sync_service: Imports the real SAP defect
            catalog used as fault-type options during daily inspection.
        repair_activity_option_sync_service: Imports SAP's activity catalog
            used as the work picker when recording repair activities.
        central_stock_sync_service: Imports central warehouse stock from SAP.
    """

    def __init__(
        self,
        vehicle_sync_service: SyncVehiclesFromSAPService,
        inspection_template_sync_service: SyncInspectionTemplatesFromSAPService,
        fault_catalog_sync_service: SyncFaultCatalogFromSAPService,
        inspection_defect_option_sync_service: SyncInspectionDefectOptionsFromSAPService,
        repair_activity_option_sync_service: SyncRepairActivityOptionsFromSAPService,
        central_stock_sync_service: SyncCentralStockFromSAPService,
    ) -> None:
        self._vehicle_sync_service = vehicle_sync_service
        self._inspection_template_sync_service = inspection_template_sync_service
        self._fault_catalog_sync_service = fault_catalog_sync_service
        self._inspection_defect_option_sync_service = inspection_defect_option_sync_service
        self._repair_activity_option_sync_service = repair_activity_option_sync_service
        self._central_stock_sync_service = central_stock_sync_service

    def execute(
        self,
        *,
        request_id: str = "",
        trigger_source: str = SAP_SYNC_TRIGGER_API,
        triggered_by: uuid.UUID | None = None,
    ) -> RunSAPSyncResultDTO:
        """Run all SAP read syncs and return a per-sync status summary.

        Args:
            request_id: Correlation id for structured logging.
            trigger_source: Caller type: API, CELERY, or JOB.
            triggered_by: Optional user UUID for API-triggered syncs.

        Returns:
            A ``RunSAPSyncResultDTO`` containing global and item-level statuses.
        """
        if trigger_source not in SAP_SYNC_TRIGGER_SOURCES:
            trigger_source = SAP_SYNC_TRIGGER_JOB
        started_at = datetime.now(tz=UTC)
        sync_run = SAPSyncRunModel.objects.create(
            trigger_source=trigger_source,
            status=SAP_SYNC_IN_PROGRESS,
            request_id=request_id,
            triggered_by_id=triggered_by,
            started_at=started_at,
            summary={},
        )
        logger.info(
            "Running global SAP read sync",
            extra={
                "domain": "integration",
                "service": "RunSAPSyncService",
                "operation": "execute",
                "request_id": request_id,
            },
        )
        items = [
            self._run_item(
                sync_run=sync_run,
                name="vehicles",
                sync=lambda: self._vehicle_sync_service.execute(request_id=request_id),
            ),
            self._run_item(
                sync_run=sync_run,
                name="inspection_templates",
                sync=lambda: self._inspection_template_sync_service.execute(
                    request_id=request_id
                ),
            ),
            self._run_item(
                sync_run=sync_run,
                name="fault_catalog",
                sync=lambda: self._fault_catalog_sync_service.execute(
                    request_id=request_id
                ),
            ),
            self._run_item(
                sync_run=sync_run,
                name="inspection_defect_options",
                sync=lambda: self._inspection_defect_option_sync_service.execute(
                    request_id=request_id
                ),
            ),
            self._run_item(
                sync_run=sync_run,
                name="repair_activity_options",
                sync=lambda: self._repair_activity_option_sync_service.execute(
                    request_id=request_id
                ),
            ),
            self._run_item(
                sync_run=sync_run,
                name="central_stock",
                sync=lambda: self._central_stock_sync_service.execute(
                    request_id=request_id
                ),
            ),
        ]
        finished_at = datetime.now(tz=UTC)
        status = _global_status(items)
        sync_run.status = status
        sync_run.finished_at = finished_at
        sync_run.summary = {
            "items": {item.name: item.summary for item in items},
            "failed_items": [item.name for item in items if item.error],
        }
        sync_run.error_message = "\n".join(item.error or "" for item in items).strip()
        sync_run.save(
            update_fields=[
                "status",
                "finished_at",
                "summary",
                "error_message",
                "updated_at",
            ]
        )
        logger.info(
            "Global SAP read sync completed",
            extra={
                "domain": "integration",
                "service": "RunSAPSyncService",
                "operation": "execute",
                "request_id": request_id,
                "result": status,
            },
        )
        return RunSAPSyncResultDTO(
            id=str(sync_run.id),
            trigger_source=trigger_source,
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            items=items,
        )

    def _run_item(
        self,
        *,
        sync_run: SAPSyncRunModel,
        name: str,
        sync: Callable[[], object],
    ) -> SAPSyncItemResultDTO:
        """Run one sync and isolate its failure from the remaining syncs."""
        started_at = datetime.now(tz=UTC)
        try:
            # Savepoint around the whole step: under ATOMIC_REQUESTS the
            # request is one transaction, so a DB error escaping ``sync()``
            # would leave it unusable and _save_item below could not record
            # the failure — turning a handled failure into a 500.
            with transaction.atomic():
                result = sync()
        except Exception as exc:  # noqa: BLE001 - global sync must continue.
            finished_at = datetime.now(tz=UTC)
            _save_item(
                sync_run=sync_run,
                name=name,
                status=SAP_SYNC_FAILED,
                started_at=started_at,
                finished_at=finished_at,
                summary={},
                error_message=str(exc),
            )
            logger.error(
                "SAP read sync item failed",
                extra={
                    "domain": "integration",
                    "service": "RunSAPSyncService",
                    "operation": "_run_item",
                    "sync_name": name,
                    "exception": str(exc),
                },
                exc_info=True,
            )
            return SAPSyncItemResultDTO(
                name=name,
                status=SAP_SYNC_FAILED,
                started_at=started_at,
                finished_at=finished_at,
                summary={},
                error=str(exc),
            )
        finished_at = datetime.now(tz=UTC)
        summary = asdict(result) if hasattr(result, "__dataclass_fields__") else {}
        _save_item(
            sync_run=sync_run,
            name=name,
            status=SAP_SYNC_SUCCESS,
            started_at=started_at,
            finished_at=finished_at,
            summary=summary,
            error_message="",
        )
        return SAPSyncItemResultDTO(
            name=name,
            status=SAP_SYNC_SUCCESS,
            started_at=started_at,
            finished_at=finished_at,
            summary=summary,
        )


def _global_status(items: list[SAPSyncItemResultDTO]) -> str:
    """Return the aggregate status for a global SAP sync run."""
    succeeded = sum(1 for item in items if item.status == SAP_SYNC_SUCCESS)
    if succeeded == len(items):
        return SAP_SYNC_SUCCESS
    if succeeded == 0:
        return SAP_SYNC_FAILED
    return SAP_SYNC_PARTIAL_SUCCESS


@transaction.atomic
def _save_item(
    *,
    sync_run: SAPSyncRunModel,
    name: str,
    status: str,
    started_at: datetime,
    finished_at: datetime,
    summary: dict[str, Any],
    error_message: str,
) -> None:
    """Persist one sync item result."""
    SAPSyncRunItemModel.objects.create(
        sync_run=sync_run,
        name=name,
        status=status,
        started_at=started_at,
        finished_at=finished_at,
        summary=summary,
        error_message=error_message,
    )
