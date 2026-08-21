"""Unit tests for repair activity-catalog option services."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from apps.repair.application.services.sync_repair_activity_options_from_sap_service import (
    ListRepairActivityOptionsService,
    SyncRepairActivityOptionsFromSAPService,
)
from apps.repair.domain.activity_option_entities import RepairActivityOption
from apps.repair.domain.interfaces.repair_activity_option_repository import (
    IRepairActivityOptionRepository,
)
from core.domain.exceptions import DomainNotFoundError
from core.sap.dtos.repair_activity_catalog import SAPRepairActivityDTO
from core.sap.ports.repair_activity_catalog_port import ISAPRepairActivityCatalogPort


class FakeRepairActivityOptionRepository(IRepairActivityOptionRepository):
    """In-memory repository for the activity-catalog cache."""

    def __init__(self, seed: list[RepairActivityOption] | None = None) -> None:
        self._store: dict[uuid.UUID, RepairActivityOption] = {
            item.id: item for item in (seed or [])
        }

    def get_by_id(self, option_id: uuid.UUID) -> RepairActivityOption:
        if option_id not in self._store:
            raise DomainNotFoundError(f"Repair activity option '{option_id}' not found.")
        return self._store[option_id]

    def get_by_sap_key(self, code: str, code_group: str) -> RepairActivityOption | None:
        return next(
            (
                item
                for item in self._store.values()
                if item.code == code and item.code_group == code_group
            ),
            None,
        )

    def list_active(self) -> list[RepairActivityOption]:
        items = [item for item in self._store.values() if item.is_active]
        return sorted(items, key=lambda item: item.code)

    def save(self, option: RepairActivityOption) -> RepairActivityOption:
        self._store[option.id] = option
        return option

    def deactivate_missing(self, seen_keys: set[tuple[str, str]]) -> int:
        count = 0
        for item in self._store.values():
            if item.is_active and (item.code, item.code_group) not in seen_keys:
                item.is_active = False
                count += 1
        return count


class FakeActivityCatalogPort(ISAPRepairActivityCatalogPort):
    """Returns a canned SAP activity catalog."""

    def __init__(self, rows: list[SAPRepairActivityDTO]) -> None:
        self._rows = rows

    def list_activities(self) -> list[SAPRepairActivityDTO]:
        return self._rows


def _sap_row(code: str, text: str) -> SAPRepairActivityDTO:
    return SAPRepairActivityDTO(
        catalog_type="A",
        code_group="REPAIR01",
        code=code,
        code_text=text,
    )


def _option(code: str, text: str, *, is_active: bool = True) -> RepairActivityOption:
    now = datetime.now(tz=UTC)
    return RepairActivityOption(
        id=uuid.uuid4(),
        catalog_type="A",
        code_group="REPAIR01",
        code=code,
        code_text=text,
        is_active=is_active,
        created_at=now,
        updated_at=now,
    )


class TestSyncRepairActivityOptionsFromSAPService:
    def test_creates_rows_from_sap(self) -> None:
        repo = FakeRepairActivityOptionRepository()
        port = FakeActivityCatalogPort(
            [_sap_row("0001", "تعويض روغن"), _sap_row("0004", "آچارکشي")]
        )

        result = SyncRepairActivityOptionsFromSAPService(repo, port).execute()

        assert result.total_received == 2
        assert result.created == 2
        assert result.updated == 0
        assert {row.code_text for row in repo.list_active()} == {
            "تعويض روغن",
            "آچارکشي",
        }

    def test_updates_existing_row_and_relabels_it(self) -> None:
        existing = _option("0001", "برچسب قديمي")
        repo = FakeRepairActivityOptionRepository([existing])
        port = FakeActivityCatalogPort([_sap_row("0001", "تعويض روغن")])

        result = SyncRepairActivityOptionsFromSAPService(repo, port).execute()

        assert result.created == 0
        assert result.updated == 1
        assert repo.get_by_sap_key("0001", "REPAIR01").code_text == "تعويض روغن"

    def test_deactivates_rows_sap_no_longer_returns(self) -> None:
        retired = _option("0099", "فعاليت حذف‌شده")
        repo = FakeRepairActivityOptionRepository([retired])
        port = FakeActivityCatalogPort([_sap_row("0001", "تعويض روغن")])

        result = SyncRepairActivityOptionsFromSAPService(repo, port).execute()

        assert result.deactivated == 1
        assert [row.code for row in repo.list_active()] == ["0001"]


class TestListRepairActivityOptionsService:
    def test_lists_active_options_ordered_by_code(self) -> None:
        repo = FakeRepairActivityOptionRepository(
            [_option("0004", "آچارکشي"), _option("0001", "تعويض روغن")]
        )

        result = ListRepairActivityOptionsService(repo).execute()

        assert [row.code for row in result] == ["0001", "0004"]

    def test_skips_inactive_options(self) -> None:
        repo = FakeRepairActivityOptionRepository(
            [_option("0099", "بازنشسته", is_active=False)]
        )

        assert ListRepairActivityOptionsService(repo).execute() == []


class TestPerRowSavepointWiring:
    """Guard the wiring for a bug the suite structurally cannot reproduce.

    The failure needs PostgreSQL's abort-on-error plus ATOMIC_REQUESTS; tests
    run on SQLite with ATOMIC_REQUESTS disabled, so no test here can trigger
    it. These assert the savepoint is wired the way the fix requires.
    """

    def test_orm_backed_repository_gets_a_real_savepoint(self) -> None:
        from django.db.transaction import Atomic

        from apps.repair.infrastructure.activity_option_repositories import (
            DjangoRepairActivityOptionRepository,
        )

        # The ORM repository opts in, so each row is wrapped in a savepoint.
        assert DjangoRepairActivityOptionRepository.uses_transactions is True

        service = SyncRepairActivityOptionsFromSAPService(
            DjangoRepairActivityOptionRepository(), FakeActivityCatalogPort([])
        )
        assert isinstance(service._atomic_if_supported(), Atomic)

    def test_in_memory_repository_skips_the_savepoint(self) -> None:
        from contextlib import nullcontext

        service = SyncRepairActivityOptionsFromSAPService(
            FakeRepairActivityOptionRepository(), FakeActivityCatalogPort([])
        )
        # No database to nest in — must not attempt a savepoint.
        assert isinstance(service._atomic_if_supported(), nullcontext)
