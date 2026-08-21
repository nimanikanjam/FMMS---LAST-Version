"""Services for listing and syncing fault catalog rows from SAP."""

from __future__ import annotations

import uuid
from contextlib import AbstractContextManager, nullcontext
from datetime import UTC, datetime

from django.db import transaction

from apps.fault.application.dto.catalog_dto import (
    FaultCatalogResponseDTO,
    FaultCatalogSyncResultDTO,
)
from apps.fault.domain.catalog_entities import FaultCatalog
from apps.fault.domain.interfaces.fault_catalog_repository import (
    IFaultCatalogRepository,
)
from core.logging.structured_logger import get_structured_logger
from core.sap.dtos.fault_catalog import SAPDefectCodeDTO
from core.sap.ports.fault_catalog_port import ISAPFaultCatalogPort

logger = get_structured_logger("fault", __name__)


def _to_response_dto(catalog: FaultCatalog) -> FaultCatalogResponseDTO:
    """Map domain catalog row to response DTO."""
    return FaultCatalogResponseDTO(
        id=catalog.id,
        code_group=catalog.code_group,
        code=catalog.code,
        group_text=catalog.group_text,
        code_text=catalog.code_text,
        defect_class=catalog.defect_class,
        defect_class_text=catalog.defect_class_text,
        is_active=catalog.is_active,
        created_at=catalog.created_at,
        updated_at=catalog.updated_at,
    )


class ListFaultCatalogService:
    """Return active fault catalog rows for manual fault reporting."""

    def __init__(self, catalog_repository: IFaultCatalogRepository) -> None:
        self._repo = catalog_repository

    def execute(
        self,
        *,
        code_group: str = "",
        defect_class: str = "",
        search: str = "",
        request_id: str = "",
    ) -> list[FaultCatalogResponseDTO]:
        """List active catalog rows with optional filters."""
        logger.info(
            "Listing fault catalog",
            extra={
                "domain": "fault",
                "service": "ListFaultCatalogService",
                "operation": "execute",
                "request_id": request_id,
                "code_group": code_group,
                "defect_class": defect_class,
                "search": search,
            },
        )
        rows = self._repo.list_active(
            code_group=code_group,
            defect_class=defect_class,
            search=search,
        )
        return [_to_response_dto(row) for row in rows]


class SyncFaultCatalogFromSAPService:
    """Import SAP defect catalog rows into FMMS."""

    def __init__(
        self,
        catalog_repository: IFaultCatalogRepository,
        fault_catalog_port: ISAPFaultCatalogPort,
    ) -> None:
        self._repo = catalog_repository
        self._sap = fault_catalog_port

    def execute(self, request_id: str = "") -> FaultCatalogSyncResultDTO:
        """Synchronise SAP defect catalog rows into FMMS."""
        logger.info(
            "Syncing fault catalog from SAP",
            extra={
                "domain": "fault",
                "service": "SyncFaultCatalogFromSAPService",
                "operation": "execute",
                "request_id": request_id,
            },
        )
        rows = self._sap.list_defect_codes()
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
                    "Failed to sync fault catalog row from SAP",
                    extra={
                        "domain": "fault",
                        "service": "SyncFaultCatalogFromSAPService",
                        "operation": "execute",
                        "request_id": request_id,
                        "code": sap_dto.code,
                        "code_group": sap_dto.code_group,
                        "exception": str(exc),
                    },
                    exc_info=True,
                )

        # Rows left over from a previous sync (e.g. a different CDS view,
        # or a code SAP dropped) must stop being offered, not linger forever.
        deactivated = self._repo.deactivate_missing(seen_keys)

        return FaultCatalogSyncResultDTO(
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

    def _sync_one(self, sap_dto: SAPDefectCodeDTO) -> bool:
        """Create or update one catalog row from SAP data."""
        existing = self._repo.get_by_sap_key(sap_dto.code, sap_dto.code_group)
        now = datetime.now(tz=UTC)
        if existing is not None:
            existing.group_text = sap_dto.group_text
            existing.code_text = sap_dto.code_text
            existing.defect_class = sap_dto.defect_class
            existing.defect_class_text = sap_dto.defect_class_text
            existing.is_active = True
            existing.updated_at = now
            self._repo.save(existing)
            return False

        catalog = FaultCatalog(
            id=uuid.uuid4(),
            code_group=sap_dto.code_group,
            code=sap_dto.code,
            group_text=sap_dto.group_text,
            code_text=sap_dto.code_text,
            defect_class=sap_dto.defect_class,
            defect_class_text=sap_dto.defect_class_text,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        self._repo.save(catalog)
        return True
