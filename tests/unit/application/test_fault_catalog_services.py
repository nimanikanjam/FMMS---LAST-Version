"""Unit tests for fault catalog sync/list services."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from apps.fault.application.services.sync_fault_catalog_from_sap_service import (
    ListFaultCatalogService,
    SyncFaultCatalogFromSAPService,
)
from apps.fault.domain.catalog_entities import FaultCatalog
from apps.fault.domain.interfaces.fault_catalog_repository import (
    IFaultCatalogRepository,
)
from core.sap.dtos.fault_catalog import SAPDefectCodeDTO
from core.sap.ports.fault_catalog_port import ISAPFaultCatalogPort


class FakeFaultCatalogRepository(IFaultCatalogRepository):
    """In-memory fault catalog repository."""

    def __init__(self, initial: list[FaultCatalog] | None = None) -> None:
        self._store: dict[uuid.UUID, FaultCatalog] = {
            item.id: item for item in (initial or [])
        }

    def get_by_id(self, catalog_id: uuid.UUID) -> FaultCatalog | None:
        return self._store.get(catalog_id)

    def get_by_sap_key(self, code: str, code_group: str) -> FaultCatalog | None:
        return next(
            (
                item
                for item in self._store.values()
                if item.code == code and item.code_group == code_group
            ),
            None,
        )

    def list_active(
        self,
        *,
        code_group: str = "",
        defect_class: str = "",
        search: str = "",
    ) -> list[FaultCatalog]:
        items = [item for item in self._store.values() if item.is_active]
        if code_group:
            items = [item for item in items if item.code_group == code_group]
        if defect_class:
            items = [item for item in items if item.defect_class == defect_class]
        if search:
            items = [
                item
                for item in items
                if search in item.code
                or search in item.code_text
                or search in item.group_text
            ]
        return sorted(items, key=lambda item: (item.group_text, item.code))

    def save(self, catalog: FaultCatalog) -> FaultCatalog:
        self._store[catalog.id] = catalog
        return catalog

    def deactivate_missing(self, seen_keys: set[tuple[str, str]]) -> int:
        deactivated = 0
        for item in self._store.values():
            if item.is_active and (item.code, item.code_group) not in seen_keys:
                item.is_active = False
                deactivated += 1
        return deactivated


class FakeSAPFaultCatalogPort(ISAPFaultCatalogPort):
    """Returns canned SAP defect catalog entries."""

    def __init__(self, rows: list[SAPDefectCodeDTO]) -> None:
        self._rows = rows

    def list_defect_codes(self) -> list[SAPDefectCodeDTO]:
        return self._rows

    def get_defect_code(self, code: str, code_group: str) -> SAPDefectCodeDTO:
        return next(
            item
            for item in self._rows
            if item.code == code and item.code_group == code_group
        )


def _row(
    code: str,
    code_group: str,
    code_text: str,
    defect_class: str = "S2",
) -> SAPDefectCodeDTO:
    return SAPDefectCodeDTO(
        code_group=code_group,
        code=code,
        group_text="سیستم ترمز",
        code_text=code_text,
        defect_class=defect_class,
        defect_class_text="Major / جدی",
    )


class TestSyncFaultCatalogFromSAPService:
    def test_creates_fault_catalog_rows_from_sap(self) -> None:
        repo = FakeFaultCatalogRepository()
        sap = FakeSAPFaultCatalogPort(
            [
                _row("B001", "BRAKE-D", "ترمز ضعیف", "S1"),
                _row("B002", "BRAKE-D", "لرزش هنگام ترمز"),
            ]
        )

        result = SyncFaultCatalogFromSAPService(repo, sap).execute()

        assert result.total_received == 2
        assert result.created == 2
        assert result.updated == 0
        assert result.failed == 0
        assert len(repo.list_active()) == 2

    def test_updates_existing_fault_catalog_row(self) -> None:
        now = datetime.now(tz=UTC)
        existing = FaultCatalog(
            id=uuid.uuid4(),
            code_group="BRAKE-D",
            code="B001",
            group_text="سیستم ترمز",
            code_text="Old",
            defect_class="S3",
            defect_class_text="Minor / جزئی",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        repo = FakeFaultCatalogRepository([existing])
        sap = FakeSAPFaultCatalogPort([_row("B001", "BRAKE-D", "ترمز ضعیف", "S1")])

        result = SyncFaultCatalogFromSAPService(repo, sap).execute()

        assert result.created == 0
        assert result.updated == 1
        saved = repo.get_by_id(existing.id)
        assert saved is not None
        assert saved.code_text == "ترمز ضعیف"
        assert saved.defect_class == "S1"

    def test_deactivates_rows_no_longer_returned_by_sap(self) -> None:
        """Switching SAP source (or SAP dropping a code) must not leave stale rows active."""
        now = datetime.now(tz=UTC)
        stale = FaultCatalog(
            id=uuid.uuid4(),
            code_group="OLD-GROUP",
            code="B001",
            group_text="سیستم ترمز",
            code_text="ترمز ضعیف (قدیمی)",
            defect_class="S1",
            defect_class_text="Critical / بحرانی",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        repo = FakeFaultCatalogRepository([stale])
        sap = FakeSAPFaultCatalogPort([_row("C001", "NEW-GROUP", "چراغ خراب", "S2")])

        result = SyncFaultCatalogFromSAPService(repo, sap).execute()

        assert result.created == 1
        assert result.deactivated == 1
        assert repo.get_by_id(stale.id).is_active is False
        assert len(repo.list_active()) == 1


class TestListFaultCatalogService:
    def test_lists_active_rows_with_filters(self) -> None:
        now = datetime.now(tz=UTC)
        active = FaultCatalog(
            id=uuid.uuid4(),
            code_group="BRAKE-D",
            code="B001",
            group_text="سیستم ترمز",
            code_text="ترمز ضعیف",
            defect_class="S1",
            defect_class_text="Critical / بحرانی",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        inactive = FaultCatalog(
            id=uuid.uuid4(),
            code_group="BODY-D",
            code="C001",
            group_text="بدنه و کابین",
            code_text="در/شیشه معیوب",
            defect_class="S3",
            defect_class_text="Minor / جزئی",
            is_active=False,
            created_at=now,
            updated_at=now,
        )
        repo = FakeFaultCatalogRepository([active, inactive])

        result = ListFaultCatalogService(repo).execute(
            code_group="BRAKE-D",
            defect_class="S1",
            search="ترمز",
        )

        assert len(result) == 1
        assert result[0].code == "B001"
