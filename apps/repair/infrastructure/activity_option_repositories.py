"""Django ORM repository for SAP-synced repair activity-catalog rows."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from django.db.models import Q

from apps.repair.domain.activity_option_entities import RepairActivityOption
from apps.repair.domain.interfaces.repair_activity_option_repository import (
    IRepairActivityOptionRepository,
)
from apps.repair.infrastructure.models import RepairActivityOptionModel
from core.domain.exceptions import DomainNotFoundError
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger(domain="repair", module=__name__)


def _to_domain(orm: RepairActivityOptionModel) -> RepairActivityOption:
    """Map ORM row to domain entity."""
    return RepairActivityOption(
        id=uuid.UUID(str(orm.id)),
        catalog_type=orm.catalog_type,
        code_group=orm.code_group,
        code=orm.code,
        code_text=orm.code_text,
        is_active=orm.is_active,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


class DjangoRepairActivityOptionRepository(IRepairActivityOptionRepository):
    """ORM-backed repository for repair activity-catalog rows."""

    # Enables per-row savepoints during SAP sync (see _atomic_if_supported).
    uses_transactions = True

    def get_by_id(self, option_id: uuid.UUID) -> RepairActivityOption:
        """Retrieve one row by UUID."""
        try:
            orm = RepairActivityOptionModel.objects.get(id=option_id, is_deleted=False)
        except RepairActivityOptionModel.DoesNotExist as exc:
            raise DomainNotFoundError(
                f"Repair activity option '{option_id}' not found."
            ) from exc
        return _to_domain(orm)

    def get_by_sap_key(self, code: str, code_group: str) -> RepairActivityOption | None:
        """Retrieve one row by SAP natural key."""
        orm = RepairActivityOptionModel.objects.filter(
            code=code,
            code_group=code_group,
            is_deleted=False,
        ).first()
        return _to_domain(orm) if orm else None

    def list_active(self) -> list[RepairActivityOption]:
        """Return active rows ordered by code."""
        qs = RepairActivityOptionModel.objects.filter(is_active=True, is_deleted=False)
        return [_to_domain(orm) for orm in qs.order_by("code")]

    def save(self, option: RepairActivityOption) -> RepairActivityOption:
        """Persist a new or updated row."""
        defaults = {
            "catalog_type": option.catalog_type,
            "code_group": option.code_group,
            "code": option.code,
            "code_text": option.code_text,
            "is_active": option.is_active,
            "updated_at": datetime.now(tz=UTC),
        }
        obj, created = RepairActivityOptionModel.objects.update_or_create(
            id=option.id,
            defaults=defaults,
        )
        if created:
            obj.created_at = option.created_at
            obj.save(update_fields=["created_at"])
        logger.debug(
            "saved repair activity option row",
            extra={"option_id": str(option.id), "is_new": created},
        )
        return option

    def deactivate_missing(self, seen_keys: set[tuple[str, str]]) -> int:
        """Deactivate active rows whose (code, code_group) is absent from seen_keys."""
        qs = RepairActivityOptionModel.objects.filter(is_active=True, is_deleted=False)
        if seen_keys:
            keep = Q()
            for code, code_group in seen_keys:
                keep |= Q(code=code, code_group=code_group)
            qs = qs.exclude(keep)
        return qs.update(is_active=False, updated_at=datetime.now(tz=UTC))
