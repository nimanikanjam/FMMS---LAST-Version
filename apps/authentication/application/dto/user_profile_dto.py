"""Shared user profile DTOs for cross-domain read models."""

from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class UserProfileSummaryDTO:
    """Minimal user profile for API enrichment.

    Attributes:
        id: User UUID.
        name: Display name.
        role: FMMS role code (e.g. ADMIN, WORKSHOP_SUPERVISOR, VIEWER).
    """

    id: uuid.UUID
    name: str
    role: str
