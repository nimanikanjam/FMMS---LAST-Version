"""Django ORM repository for SAP-synced inspection defect-catalog rows."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from django.db.models import Q

from apps.inspection.domain.defect_option_entities import InspectionDefectOption
from apps.inspection.domain.interfaces.inspection_defect_option_repository import (
    IInspectionDefectOptionRepository,
)
from apps.inspection.infrastructure.models import InspectionDefectOptionModel
from core.domain.exceptions import DomainNotFoundError
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger(domain="inspection", module=__name__)


def _to_domain(orm: InspectionDefectOptionModel) -> InspectionDefectOption:
    """Map ORM row to domain entity."""
    return InspectionDefectOption(
        id=uuid.UUID(str(orm.id)),
        code_group=orm.code_group,
        code=orm.code,
        group_text=orm.group_text,
        code_text=orm.code_text,
        defect_class=orm.defect_class,
        defect_class_text=orm.defect_class_text,
        is_active=orm.is_active,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


class DjangoInspectionDefectOptionRepository(IInspectionDefectOptionRepository):
    """ORM-backed repository for inspection defect-catalog rows."""

    # Enables per-row savepoints during SAP sync (see _atomic_if_supported).
    uses_transactions = True

    def get_by_id(self, option_id: uuid.UUID) -> InspectionDefectOption:
        """Retrieve one row by UUID."""
        try:
            orm = InspectionDefectOptionModel.objects.get(id=option_id, is_deleted=False)
        except InspectionDefectOptionModel.DoesNotExist as exc:
            raise DomainNotFoundError(
                f"Inspection defect option '{option_id}' not found."
            ) from exc
        return _to_domain(orm)

    def get_by_sap_key(self, code: str, code_group: str) -> InspectionDefectOption | None:
        """Retrieve one row by SAP natural key."""
        orm = InspectionDefectOptionModel.objects.filter(
            code=code,
            code_group=code_group,
            is_deleted=False,
        ).first()
        return _to_domain(orm) if orm else None

    def list_active(self) -> list[InspectionDefectOption]:
        """Return active rows ordered by group text, then code."""
        qs = InspectionDefectOptionModel.objects.filter(is_active=True, is_deleted=False)
        return [_to_domain(orm) for orm in qs.order_by("group_text", "code")]

    def save(self, option: InspectionDefectOption) -> InspectionDefectOption:
        """Persist a new or updated row."""
        defaults = {
            "code_group": option.code_group,
            "code": option.code,
            "group_text": option.group_text,
            "code_text": option.code_text,
            "defect_class": option.defect_class,
            "defect_class_text": option.defect_class_text,
            "is_active": option.is_active,
            "updated_at": datetime.now(tz=UTC),
        }
        obj, created = InspectionDefectOptionModel.objects.update_or_create(
            id=option.id,
            defaults=defaults,
        )
        if created:
            obj.created_at = option.created_at
            obj.save(update_fields=["created_at"])
        logger.debug(
            "saved inspection defect option row",
            extra={"option_id": str(option.id), "is_new": created},
        )
        return option

    def deactivate_missing(self, seen_keys: set[tuple[str, str]]) -> int:
        """Deactivate active rows whose (code, code_group) is absent from seen_keys."""
        qs = InspectionDefectOptionModel.objects.filter(is_active=True, is_deleted=False)
        if seen_keys:
            keep = Q()
            for code, code_group in seen_keys:
                keep |= Q(code=code, code_group=code_group)
            qs = qs.exclude(keep)
        return qs.update(is_active=False, updated_at=datetime.now(tz=UTC))
