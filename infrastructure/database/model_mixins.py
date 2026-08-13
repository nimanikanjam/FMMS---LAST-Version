"""Composable abstract Django model mixins shared by persistence models."""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class UUIDPrimaryKeyMixin(models.Model):
    """Provide a UUID4 primary key without creating a standalone table."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique record identifier (UUID4).",
    )

    class Meta:
        abstract = True


class TimestampMixin(models.Model):
    """Record creation and last-save timestamps."""

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="UTC timestamp when this record was created.",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="UTC timestamp of the last update to this record.",
    )

    class Meta:
        abstract = True


class UserAuditMixin(models.Model):
    """Record the users responsible for creation and the latest update."""

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_created",
        help_text="User who created this record.",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_updated",
        help_text="User who last updated this record.",
    )

    class Meta:
        abstract = True


class SoftDeleteMixin(models.Model):
    """Provide the shared logical-deletion state and deletion audit fields."""

    is_deleted = models.BooleanField(
        default=False,
        db_index=True,
        help_text="True if this record has been soft-deleted. Never physically remove records.",
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="UTC timestamp of soft deletion.",
    )
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_deleted",
        help_text="User who soft-deleted this record.",
    )

    class Meta:
        abstract = True


class BusinessRecordModel(
    UUIDPrimaryKeyMixin,
    TimestampMixin,
    UserAuditMixin,
    SoftDeleteMixin,
):
    """Preserve the existing full record contract for current ORM models.

    New models should inherit only the individual mixins they actually need.
    This composite keeps the existing database schema stable while legacy
    models are evaluated individually.
    """

    class Meta:
        abstract = True

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.id!r})"
