"""Django-backed implementation of ``IUserProfileReader``."""

from __future__ import annotations

import uuid

from django.contrib.auth import get_user_model

from apps.authentication.application.dto.user_profile_dto import UserProfileSummaryDTO
from apps.authentication.application.ports.user_profile_reader import IUserProfileReader


class DjangoUserProfileReader(IUserProfileReader):
    """Resolve FMMS user profiles from the authentication persistence model."""

    def get_profile(self, user_id: uuid.UUID) -> UserProfileSummaryDTO | None:
        """Return profile summary for an existing FMMS user."""
        user_model = get_user_model()
        user = user_model.objects.filter(id=user_id, is_active=True).first()
        if user is None:
            return None
        return UserProfileSummaryDTO(
            id=user.id,
            name=user.full_name,
            role=user.role,
        )
