"""Read-only application port for resolving user profile summaries."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from apps.authentication.application.dto.user_profile_dto import UserProfileSummaryDTO


class IUserProfileReader(ABC):
    """Resolve display metadata without exposing Django ORM models."""

    @abstractmethod
    def get_profile(self, user_id: uuid.UUID) -> UserProfileSummaryDTO | None:
        """Return an active user summary, or ``None`` when it does not exist."""
