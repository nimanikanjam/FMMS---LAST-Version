"""Services for listing and syncing SAP defect-catalog rows for daily inspection.

Syncs SAP's real defect catalog ``ZI_B_DEFECTCATALOG9_CDS`` (with
``DefectClass``/severity), offered as fault-type options while a driver
fails a checklist item during daily inspection.

``apps.fault``'s fault-catalog sync reads the same SAP view for manual
fault reporting, but keeps its own local cache and lifecycle.

The checklist itself comes from a different SAP view
(``ZI_FLEET_CAT_B_CDS``, see ``sync_inspection_templates_from_sap_service``)
with its own unrelated grouping, so the two catalogs are never cross-filtered.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from apps.inspection.application.dto.defect_option_dto import (
    InspectionDefectOptionResponseDTO,
    InspectionDefectOptionSyncResultDTO,
)
from apps.inspection.domain.defect_option_entities import InspectionDefectOption
from apps.inspection.domain.interfaces.inspection_defect_option_repository import (
    IInspectionDefectOptionRepository,
)
from core.logging.structured_logger import get_structured_logger
from core.sap.dtos.fault_catalog import SAPDefectCodeDTO
from core.sap.ports.fault_catalog_port import ISAPFaultCatalogPort

logger = get_structured_logger("inspection", __name__)


def _to_response_dto(option: InspectionDefectOption) -> InspectionDefectOptionResponseDTO:
    """Map domain row to response DTO."""
    return InspectionDefectOptionResponseDTO(
        id=option.id,
        code_group=option.code_group,
        code=option.code,
        group_text=option.group_text,
        code_text=option.code_text,
        defect_class=option.defect_class,
        defect_class_text=option.defect_class_text,
        is_active=option.is_active,
        created_at=option.created_at,
        updated_at=option.updated_at,
    )


class ListInspectionDefectOptionsService:
    """Return the active defect catalog for the daily-inspection fault picker.

    The defect catalog (``ZI_B_DEFECTCATALOG9_CDS``) carries its own
    grouping, which does not line up with the checklist catalog's
    (``ZI_FLEET_CAT_B_CDS``) — different code groups, different group
    texts, and defect groups such as tyres or general safety that have no
    checklist counterpart at all. So the two taxonomies are kept separate:
    the full catalog is returned, ordered by its own ``group_text``, and
    the UI groups the picker by that same field.
    """

    def __init__(self, option_repository: IInspectionDefectOptionRepository) -> None:
        self._repo = option_repository

    def execute(self, *, request_id: str = "") -> list[InspectionDefectOptionResponseDTO]:
        """List every active defect option, ordered by its own group text."""
        logger.info(
            "Listing inspection defect options",
            extra={
                "domain": "inspection",
                "service": "ListInspectionDefectOptionsService",
                "operation": "execute",
                "request_id": request_id,
            },
        )
        return [_to_response_dto(row) for row in self._repo.list_active()]


class SyncInspectionDefectOptionsFromSAPService:
    """Import SAP's real defect catalog into FMMS for the inspection fault picker."""

    def __init__(
        self,
        option_repository: IInspectionDefectOptionRepository,
        fault_catalog_port: ISAPFaultCatalogPort,
    ) -> None:
        self._repo = option_repository
        self._sap = fault_catalog_port

    def execute(self, request_id: str = "") -> InspectionDefectOptionSyncResultDTO:
        """Synchronise SAP defect catalog rows into FMMS."""
        logger.info(
            "Syncing inspection defect options from SAP",
            extra={
                "domain": "inspection",
                "service": "SyncInspectionDefectOptionsFromSAPService",
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
                if self._sync_one(sap_dto):
                    created += 1
                else:
                    updated += 1
            except Exception as exc:  # noqa: BLE001 - per-row isolation
                failed += 1
                logger.error(
                    "Failed to sync inspection defect option from SAP",
                    extra={
                        "domain": "inspection",
                        "service": "SyncInspectionDefectOptionsFromSAPService",
                        "operation": "execute",
                        "request_id": request_id,
                        "code": sap_dto.code,
                        "code_group": sap_dto.code_group,
                        "exception": str(exc),
                    },
                    exc_info=True,
                )

        deactivated = self._repo.deactivate_missing(seen_keys)

        return InspectionDefectOptionSyncResultDTO(
            total_received=len(rows),
            created=created,
            updated=updated,
            failed=failed,
            deactivated=deactivated,
        )

    def _sync_one(self, sap_dto: SAPDefectCodeDTO) -> bool:
        """Create or update one row from SAP data. Returns True if created."""
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

        option = InspectionDefectOption(
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
        self._repo.save(option)
        return True
