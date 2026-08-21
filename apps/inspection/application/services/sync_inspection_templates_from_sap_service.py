"""Services for listing and syncing inspection checklist templates from SAP."""

from __future__ import annotations

import uuid
from contextlib import AbstractContextManager, nullcontext
from datetime import UTC, datetime

from django.db import transaction

from apps.inspection.application.dto.template_dto import (
    InspectionTemplateResponseDTO,
    InspectionTemplateSyncResultDTO,
)
from apps.inspection.domain.interfaces.inspection_template_repository import (
    IInspectionTemplateRepository,
)
from apps.inspection.domain.template_entities import InspectionTemplate
from core.logging.structured_logger import get_structured_logger
from core.sap.dtos.object_part_catalog import SAPObjectPartDTO
from core.sap.ports.object_part_catalog_port import ISAPObjectPartCatalogPort

logger = get_structured_logger("inspection", __name__)

_DEFAULT_CATALOG_TYPE = "B"


def _to_response_dto(template: InspectionTemplate) -> InspectionTemplateResponseDTO:
    """Map domain template → response DTO."""
    return InspectionTemplateResponseDTO(
        id=template.id,
        code_group=template.code_group,
        code=template.code,
        group_text=template.group_text,
        code_text=template.code_text,
        is_active=template.is_active,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


class ListInspectionTemplatesService:
    """Return active inspection checklist templates for driver UIs.

    Args:
        template_repository: Concrete ``IInspectionTemplateRepository``.
    """

    def __init__(self, template_repository: IInspectionTemplateRepository) -> None:
        self._repo = template_repository

    def execute(self, request_id: str = "") -> list[InspectionTemplateResponseDTO]:
        """List active templates stored locally in FMMS.

        Args:
            request_id: Optional correlation ID for structured logging.

        Returns:
            Ordered list of active template DTOs.
        """
        logger.info(
            "Listing inspection templates",
            extra={
                "domain": "inspection",
                "service": "ListInspectionTemplatesService",
                "operation": "execute",
                "request_id": request_id,
            },
        )
        templates = self._repo.list_active()
        logger.info(
            "Inspection templates listed",
            extra={
                "domain": "inspection",
                "service": "ListInspectionTemplatesService",
                "operation": "execute",
                "request_id": request_id,
                "result": "success",
                "count": len(templates),
            },
        )
        return [_to_response_dto(t) for t in templates]


class SyncInspectionTemplatesFromSAPService:
    """Import SAP object-part catalog entries as local checklist templates.

    Args:
        template_repository: Concrete ``IInspectionTemplateRepository``.
        object_part_catalog_port: Concrete ``ISAPObjectPartCatalogPort``.
    """

    def __init__(
        self,
        template_repository: IInspectionTemplateRepository,
        object_part_catalog_port: ISAPObjectPartCatalogPort,
    ) -> None:
        self._repo = template_repository
        self._sap = object_part_catalog_port

    def execute(
        self,
        request_id: str = "",
    ) -> InspectionTemplateSyncResultDTO:
        """Synchronise SAP catalog entries into FMMS inspection templates.

        Matching key is ``(code, code_group)``. Existing
        templates are updated; missing ones are created.

        Args:
            request_id: Optional correlation ID for structured logging.

        Returns:
            ``InspectionTemplateSyncResultDTO`` with create/update/fail counts.
        """
        logger.info(
            "Syncing inspection templates from SAP",
            extra={
                "domain": "inspection",
                "service": "SyncInspectionTemplatesFromSAPService",
                "operation": "execute",
                "request_id": request_id,
            },
        )

        catalog = self._sap.get_catalog(_DEFAULT_CATALOG_TYPE)
        created = 0
        updated = 0
        failed = 0

        for sap_dto in catalog:
            try:
                with self._atomic_if_supported():
                    created_row = self._sync_one(sap_dto)
                if created_row:
                    created += 1
                else:
                    updated += 1
            except Exception as exc:  # noqa: BLE001 — per-record isolation
                failed += 1
                logger.error(
                    "Failed to sync inspection template from SAP",
                    extra={
                        "domain": "inspection",
                        "service": "SyncInspectionTemplatesFromSAPService",
                        "operation": "execute",
                        "request_id": request_id,
                        "code": sap_dto.code,
                        "code_group": sap_dto.code_group,
                        "exception": str(exc),
                    },
                    exc_info=True,
                )

        result = InspectionTemplateSyncResultDTO(
            total_received=len(catalog),
            created=created,
            updated=updated,
            failed=failed,
        )
        logger.info(
            "Inspection template SAP sync completed",
            extra={
                "domain": "inspection",
                "service": "SyncInspectionTemplatesFromSAPService",
                "operation": "execute",
                "request_id": request_id,
                "result": "success",
                "total_received": result.total_received,
                "created_count": result.created,
                "updated_count": result.updated,
                "failed_count": result.failed,
            },
        )
        return result


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

    def _sync_one(self, sap_dto: SAPObjectPartDTO) -> bool:
        """Create or update one template from an SAP catalog entry.

        Args:
            sap_dto: SAP object-part catalog DTO.

        Returns:
            ``True`` when created, ``False`` when updated.
        """
        existing = self._repo.get_by_sap_key(sap_dto.code, sap_dto.code_group)
        now = datetime.now(tz=UTC)
        if existing is not None:
            existing.group_text = sap_dto.group_text
            existing.code_text = sap_dto.code_text
            existing.is_active = True
            existing.updated_at = now
            self._repo.save(existing)
            return False

        template = InspectionTemplate(
            id=uuid.uuid4(),
            code_group=sap_dto.code_group,
            code=sap_dto.code,
            group_text=sap_dto.group_text,
            code_text=sap_dto.code_text,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        self._repo.save(template)
        return True
