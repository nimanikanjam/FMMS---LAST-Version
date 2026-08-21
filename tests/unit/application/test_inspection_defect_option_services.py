"""Unit tests for inspection defect-option sync/list services."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from apps.inspection.application.services.sync_inspection_defect_options_from_sap_service import (
    ListInspectionDefectOptionsService,
    SyncInspectionDefectOptionsFromSAPService,
)
from apps.inspection.domain.defect_option_entities import InspectionDefectOption
from apps.inspection.domain.interfaces.inspection_defect_option_repository import (
    IInspectionDefectOptionRepository,
)
from core.sap.dtos.fault_catalog import SAPDefectCodeDTO
from core.sap.ports.fault_catalog_port import ISAPFaultCatalogPort


class FakeInspectionDefectOptionRepository(IInspectionDefectOptionRepository):
    """In-memory inspection defect-option repository."""

    def __init__(self, initial: list[InspectionDefectOption] | None = None) -> None:
        self._store: dict[uuid.UUID, InspectionDefectOption] = {
            item.id: item for item in (initial or [])
        }

    def get_by_id(self, option_id: uuid.UUID) -> InspectionDefectOption | None:
        return self._store.get(option_id)

    def get_by_sap_key(self, code: str, code_group: str) -> InspectionDefectOption | None:
        return next(
            (
                item
                for item in self._store.values()
                if item.code == code and item.code_group == code_group
            ),
            None,
        )

    def list_active(self) -> list[InspectionDefectOption]:
        items = [item for item in self._store.values() if item.is_active]
        return sorted(items, key=lambda item: (item.group_text, item.code))

    def save(self, option: InspectionDefectOption) -> InspectionDefectOption:
        self._store[option.id] = option
        return option

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
    group_text: str = "سیستم ترمز",
    defect_class: str = "S2",
) -> SAPDefectCodeDTO:
    return SAPDefectCodeDTO(
        code_group=code_group,
        code=code,
        group_text=group_text,
        code_text=code_text,
        defect_class=defect_class,
        defect_class_text="Major / جدی",
    )


class TestSyncInspectionDefectOptionsFromSAPService:
    def test_creates_rows_from_sap(self) -> None:
        repo = FakeInspectionDefectOptionRepository()
        sap = FakeSAPFaultCatalogPort(
            [
                _row("B001", "BRAKE-D", "ترمز ضعیف", defect_class="S1"),
                _row("B002", "BRAKE-D", "لرزش هنگام ترمز"),
            ]
        )

        result = SyncInspectionDefectOptionsFromSAPService(repo, sap).execute()

        assert result.total_received == 2
        assert result.created == 2
        assert result.updated == 0
        assert result.failed == 0
        assert len(repo.list_active()) == 2

    def test_deactivates_rows_no_longer_returned_by_sap(self) -> None:
        now = datetime.now(tz=UTC)
        stale = InspectionDefectOption(
            id=uuid.uuid4(),
            code_group="OLD-GROUP",
            code="Z001",
            group_text="قدیمی",
            code_text="مورد قدیمی",
            defect_class="S1",
            defect_class_text="Critical / بحرانی",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        repo = FakeInspectionDefectOptionRepository([stale])
        sap = FakeSAPFaultCatalogPort([_row("C001", "NEW-GROUP", "چراغ خراب", group_text="روشنایی")])

        result = SyncInspectionDefectOptionsFromSAPService(repo, sap).execute()

        assert result.created == 1
        assert result.deactivated == 1
        assert repo.get_by_id(stale.id).is_active is False


class TestListInspectionDefectOptionsService:
    def test_returns_whole_catalog_in_its_own_group_order(self) -> None:
        """The defect catalog is never cross-filtered by a checklist category.

        Its grouping is unrelated to the checklist catalog's, so every active
        option is returned, ordered by its own group text for UI grouping.
        """
        now = datetime.now(tz=UTC)
        brake = InspectionDefectOption(
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
        light = InspectionDefectOption(
            id=uuid.uuid4(),
            code_group="LIGHT-D",
            code="L001",
            group_text="روشنایی و برق",
            code_text="چراغ خراب",
            defect_class="S2",
            defect_class_text="Major / جدی",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        repo = FakeInspectionDefectOptionRepository([brake, light])

        result = ListInspectionDefectOptionsService(repo).execute()

        assert {row.code for row in result} == {"B001", "L001"}

    def test_skips_inactive_options(self) -> None:
        """Deactivated rows (dropped from SAP) are not offered to drivers."""
        now = datetime.now(tz=UTC)
        retired = InspectionDefectOption(
            id=uuid.uuid4(),
            code_group="BRAKE-D",
            code="B009",
            group_text="سیستم ترمز",
            code_text="کد بازنشسته",
            defect_class="S3",
            defect_class_text="Minor / جزئی",
            is_active=False,
            created_at=now,
            updated_at=now,
        )
        repo = FakeInspectionDefectOptionRepository([retired])

        assert ListInspectionDefectOptionsService(repo).execute() == []
