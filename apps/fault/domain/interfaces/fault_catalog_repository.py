"""Abstract repository interface for SAP-synced fault catalog rows."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from apps.fault.domain.catalog_entities import FaultCatalog


class IFaultCatalogRepository(ABC):
    """Port for persisting and reading fault catalog cache rows."""

    @abstractmethod
    def get_by_id(self, catalog_id: uuid.UUID) -> FaultCatalog:
        """Retrieve one catalog row by UUID."""

    @abstractmethod
    def get_by_sap_key(self, code: str, code_group: str) -> FaultCatalog | None:
        """Retrieve one catalog row by SAP ``Code`` and ``CodeGroup``."""

    @abstractmethod
    def list_active(
        self,
        *,
        code_group: str = "",
        defect_class: str = "",
        search: str = "",
    ) -> list[FaultCatalog]:
        """Return active catalog rows with optional filters."""

    @abstractmethod
    def save(self, catalog: FaultCatalog) -> FaultCatalog:
        """Persist a new or updated catalog row."""

    @abstractmethod
    def deactivate_missing(self, seen_keys: set[tuple[str, str]]) -> int:
        """Deactivate active rows whose ``(code, code_group)`` wasn't in the latest SAP fetch.

        Used after a full sync to stop showing catalog rows SAP no longer
        returns (e.g. after switching the synced CDS view) without deleting
        their history. Returns the number of rows deactivated.
        """
