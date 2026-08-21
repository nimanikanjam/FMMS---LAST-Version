"""Concrete Django ORM implementation of IInspectionTemplateRepository."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from apps.inspection.domain.interfaces.inspection_template_repository import (
    IInspectionTemplateRepository,
)
from apps.inspection.domain.template_entities import InspectionTemplate
from apps.inspection.infrastructure.models import InspectionTemplateModel
from core.domain.exceptions import DomainNotFoundError
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger(domain="inspection", module=__name__)


def _to_domain(orm: InspectionTemplateModel) -> InspectionTemplate:
    """Map ORM row to domain entity."""
    return InspectionTemplate(
        id=uuid.UUID(str(orm.id)),
        code_group=orm.code_group,
        code=orm.code,
        group_text=orm.group_text,
        code_text=orm.code_text,
        is_active=orm.is_active,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


class DjangoInspectionTemplateRepository(IInspectionTemplateRepository):
    """ORM-backed repository for inspection checklist templates."""

    # Enables per-row savepoints during SAP sync (see _atomic_if_supported).
    uses_transactions = True

    def get_by_id(self, template_id: uuid.UUID) -> InspectionTemplate:
        """Retrieve a template by UUID."""
        try:
            orm = InspectionTemplateModel.objects.get(id=template_id, is_deleted=False)
        except InspectionTemplateModel.DoesNotExist as exc:
            raise DomainNotFoundError(
                f"Inspection template '{template_id}' not found."
            ) from exc
        return _to_domain(orm)

    def get_by_sap_key(
        self, code: str, code_group: str
    ) -> InspectionTemplate | None:
        """Retrieve a template by SAP natural key."""
        orm = InspectionTemplateModel.objects.filter(
            code=code,
            code_group=code_group,
            is_deleted=False,
        ).first()
        return _to_domain(orm) if orm else None

    def list_active(self) -> list[InspectionTemplate]:
        """Return active templates ordered by SAP group text, then code."""
        qs = InspectionTemplateModel.objects.filter(
            is_active=True, is_deleted=False
        ).order_by("group_text", "code")
        return [_to_domain(orm) for orm in qs]

    def save(self, template: InspectionTemplate) -> InspectionTemplate:
        """Persist a new or updated template."""
        defaults = {
            "code_group": template.code_group,
            "code": template.code,
            "group_text": template.group_text,
            "code_text": template.code_text,
            "is_active": template.is_active,
            "updated_at": datetime.now(tz=UTC),
        }
        obj, created = InspectionTemplateModel.objects.update_or_create(
            id=template.id,
            defaults=defaults,
        )
        if created:
            obj.created_at = template.created_at
            obj.save(update_fields=["created_at"])
        logger.debug(
            "saved inspection template",
            extra={"template_id": str(template.id), "is_new": created},
        )
        return template
