"""Abstract repository interface for SAP activity-catalog rows."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from apps.repair.domain.activity_option_entities import RepairActivityOption


class IRepairActivityOptionRepository(ABC):
    """Port for persisting and reading repair activity-catalog cache rows."""

    @abstractmethod
    def get_by_id(self, option_id: uuid.UUID) -> RepairActivityOption:
        """Retrieve one row by UUID."""

    @abstractmethod
    def get_by_sap_key(self, code: str, code_group: str) -> RepairActivityOption | None:
        """Retrieve one row by SAP ``Code`` and ``CodeGroup``."""

    @abstractmethod
    def list_active(self) -> list[RepairActivityOption]:
        """Return active rows ordered by code."""

    @abstractmethod
    def save(self, option: RepairActivityOption) -> RepairActivityOption:
        """Persist a new or updated row."""

    @abstractmethod
    def deactivate_missing(self, seen_keys: set[tuple[str, str]]) -> int:
        """Deactivate active rows absent from the latest SAP fetch.

        Returns the number of rows deactivated.
        """
