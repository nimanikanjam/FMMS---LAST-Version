"""Services for listing and syncing SAP activity-catalog rows for repairs.

Syncs SAP's activity catalog ``ZC_REPAIR01_CODE_CDS`` (catalog type ``A``) —
the standard jobs a workshop performs — so a technician records the work done
by picking a real SAP code instead of typing free text.
"""

from __future__ import annotations

import uuid
from contextlib import AbstractContextManager, nullcontext
from datetime import UTC, datetime

from django.db import transaction

from apps.repair.application.dto.activity_option_dto import (
    RepairActivityOptionResponseDTO,
    RepairActivityOptionSyncResultDTO,
)
from apps.repair.domain.activity_option_entities import RepairActivityOption
from apps.repair.domain.interfaces.repair_activity_option_repository import (
    IRepairActivityOptionRepository,
)
from core.logging.structured_logger import get_structured_logger
from core.sap.dtos.repair_activity_catalog import SAPRepairActivityDTO
from core.sap.ports.repair_activity_catalog_port import ISAPRepairActivityCatalogPort

logger = get_structured_logger("repair", __name__)


def _to_response_dto(option: RepairActivityOption) -> RepairActivityOptionResponseDTO:
    """Map domain row to response DTO."""
    return RepairActivityOptionResponseDTO(
        id=option.id,
        catalog_type=option.catalog_type,
        code_group=option.code_group,
        code=option.code,
        code_text=option.code_text,
        is_active=option.is_active,
        created_at=option.created_at,
        updated_at=option.updated_at,
    )


class ListRepairActivityOptionsService:
    """Return the active SAP activity catalog for the workshop's work picker."""

    def __init__(self, option_repository: IRepairActivityOptionRepository) -> None:
        self._repo = option_repository

    def execute(self, *, request_id: str = "") -> list[RepairActivityOptionResponseDTO]:
        """List every active activity option, ordered by SAP code."""
        logger.info(
            "Listing repair activity options",
            extra={
                "domain": "repair",
                "service": "ListRepairActivityOptionsService",
                "operation": "execute",
                "request_id": request_id,
            },
        )
        return [_to_response_dto(row) for row in self._repo.list_active()]


class SyncRepairActivityOptionsFromSAPService:
    """Import SAP's activity catalog into FMMS for the repair work picker."""

    def __init__(
        self,
        option_repository: IRepairActivityOptionRepository,
        activity_catalog_port: ISAPRepairActivityCatalogPort,
    ) -> None:
        self._repo = option_repository
        self._sap = activity_catalog_port

    def execute(self, request_id: str = "") -> RepairActivityOptionSyncResultDTO:
        """Synchronise SAP activity catalog rows into FMMS."""
        logger.info(
            "Syncing repair activity options from SAP",
            extra={
                "domain": "repair",
                "service": "SyncRepairActivityOptionsFromSAPService",
                "operation": "execute",
                "request_id": request_id,
            },
        )
        rows = self._sap.list_activities()
        created = 0
        updated = 0
        failed = 0
        seen_keys: set[tuple[str, str]] = set()
        for sap_dto in rows:
            seen_keys.add((sap_dto.code, sap_dto.code_group))
            try:
                with self._atomic_if_supported():
                    created_row = self._sync_one(sap_dto)
                if created_row:
                    created += 1
                else:
                    updated += 1
            except Exception as exc:  # noqa: BLE001 - per-row isolation
                failed += 1
                logger.error(
                    "Failed to sync repair activity option from SAP",
                    extra={
                        "domain": "repair",
                        "service": "SyncRepairActivityOptionsFromSAPService",
                        "operation": "execute",
                        "request_id": request_id,
                        "code": sap_dto.code,
                        "code_group": sap_dto.code_group,
                        "exception": str(exc),
                    },
                    exc_info=True,
                )

        deactivated = self._repo.deactivate_missing(seen_keys)

        return RepairActivityOptionSyncResultDTO(
            total_received=len(rows),
            created=created,
            updated=updated,
            failed=failed,
            deactivated=deactivated,
        )

    def _atomic_if_supported(self) -> AbstractContextManager[object]:
        """Wrap one row in a savepoint, for ORM-backed repositories only.

        Requests run inside a single transaction (``ATOMIC_REQUESTS``), so
        without a savepoint per row one failing row poisons that transaction
        and every later query — including the sync-run bookkeeping — dies
        with "transaction is aborted", turning an isolated row failure into
        a 500. In-memory test repositories have no transactions to nest in.
        """
        if getattr(self._repo, "uses_transactions", False):
            return transaction.atomic()
        return nullcontext()

    def _sync_one(self, sap_dto: SAPRepairActivityDTO) -> bool:
        """Create or update one row from SAP data. Returns True if created."""
        existing = self._repo.get_by_sap_key(sap_dto.code, sap_dto.code_group)
        now = datetime.now(tz=UTC)
        if existing is not None:
            existing.catalog_type = sap_dto.catalog_type
            existing.code_text = sap_dto.code_text
            existing.is_active = True
            existing.updated_at = now
            self._repo.save(existing)
            return False

        option = RepairActivityOption(
            id=uuid.uuid4(),
            catalog_type=sap_dto.catalog_type,
            code_group=sap_dto.code_group,
            code=sap_dto.code,
            code_text=sap_dto.code_text,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        self._repo.save(option)
        return True
