"""DTOs for SAP activity-catalog options offered when recording repair work."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class RepairActivityOptionResponseDTO:
    """One activity option returned to the workshop UI."""

    id: uuid.UUID
    catalog_type: str
    code_group: str
    code: str
    code_text: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class RepairActivityOptionSyncResultDTO:
    """Outcome of one SAP activity-catalog synchronisation run."""

    total_received: int
    created: int
    updated: int
    failed: int
    deactivated: int
