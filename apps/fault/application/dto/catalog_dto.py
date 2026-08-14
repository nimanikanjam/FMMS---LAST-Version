"""Application DTOs for SAP-synced fault catalog rows."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class FaultCatalogResponseDTO:
    """Output DTO for one fault catalog row."""

    id: uuid.UUID
    code_group: str
    code: str
    group_text: str
    code_text: str
    defect_class: str
    defect_class_text: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class FaultCatalogSyncResultDTO:
    """Summary of a bulk SAP defect-catalog synchronisation."""

    total_received: int
    created: int
    updated: int
    failed: int
    deactivated: int = 0
