"""Abstract repository interface for SAP defect-catalog rows (inspection use)."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from apps.inspection.domain.defect_option_entities import InspectionDefectOption


class IInspectionDefectOptionRepository(ABC):
    """Port for persisting and reading inspection defect-catalog cache rows."""

    @abstractmethod
    def get_by_id(self, option_id: uuid.UUID) -> InspectionDefectOption:
        """Retrieve one row by UUID."""

    @abstractmethod
    def get_by_sap_key(self, code: str, code_group: str) -> InspectionDefectOption | None:
        """Retrieve one row by SAP ``Code`` and ``CodeGroup``."""

    @abstractmethod
    def list_active(self) -> list[InspectionDefectOption]:
        """Return active rows ordered by the catalog's own group text, then code."""

    @abstractmethod
    def save(self, option: InspectionDefectOption) -> InspectionDefectOption:
        """Persist a new or updated row."""

    @abstractmethod
    def deactivate_missing(self, seen_keys: set[tuple[str, str]]) -> int:
        """Deactivate active rows whose (code, code_group) wasn't in the latest SAP fetch.

        Returns the number of rows deactivated.
        """
