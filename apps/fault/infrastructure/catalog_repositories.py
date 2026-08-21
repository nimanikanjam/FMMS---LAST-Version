"""Django ORM repository for SAP-synced fault catalog rows."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from django.db.models import Q

from apps.fault.domain.catalog_entities import FaultCatalog
from apps.fault.domain.interfaces.fault_catalog_repository import (
    IFaultCatalogRepository,
)
from apps.fault.infrastructure.models import FaultCatalogModel
from core.domain.exceptions import DomainNotFoundError
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger(domain="fault", module=__name__)


def _to_domain(orm: FaultCatalogModel) -> FaultCatalog:
    """Map ORM row to domain entity."""
    return FaultCatalog(
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


class DjangoFaultCatalogRepository(IFaultCatalogRepository):
    """ORM-backed repository for fault catalog rows."""

    # Enables per-row savepoints during SAP sync (see _atomic_if_supported).
    uses_transactions = True

    def get_by_id(self, catalog_id: uuid.UUID) -> FaultCatalog:
        """Retrieve one catalog row by UUID."""
        try:
            orm = FaultCatalogModel.objects.get(id=catalog_id, is_deleted=False)
        except FaultCatalogModel.DoesNotExist as exc:
            raise DomainNotFoundError(
                f"Fault catalog row '{catalog_id}' not found."
            ) from exc
        return _to_domain(orm)

    def get_by_sap_key(self, code: str, code_group: str) -> FaultCatalog | None:
        """Retrieve one catalog row by SAP natural key."""
        orm = FaultCatalogModel.objects.filter(
            code=code,
            code_group=code_group,
            is_deleted=False,
        ).first()
        return _to_domain(orm) if orm else None

    def list_active(
        self,
        *,
        code_group: str = "",
        defect_class: str = "",
        search: str = "",
    ) -> list[FaultCatalog]:
        """Return active catalog rows ordered by SAP group text, then code."""
        qs = FaultCatalogModel.objects.filter(is_active=True, is_deleted=False)
        if code_group:
            qs = qs.filter(code_group=code_group)
        if defect_class:
            qs = qs.filter(defect_class=defect_class)
        if search:
            qs = qs.filter(
                Q(code__icontains=search)
                | Q(code_text__icontains=search)
                | Q(group_text__icontains=search)
            )
        return [_to_domain(orm) for orm in qs.order_by("group_text", "code")]

    def save(self, catalog: FaultCatalog) -> FaultCatalog:
        """Persist a new or updated catalog row."""
        defaults = {
            "code_group": catalog.code_group,
            "code": catalog.code,
            "group_text": catalog.group_text,
            "code_text": catalog.code_text,
            "defect_class": catalog.defect_class,
            "defect_class_text": catalog.defect_class_text,
            "is_active": catalog.is_active,
            "updated_at": datetime.now(tz=UTC),
        }
        obj, created = FaultCatalogModel.objects.update_or_create(
            id=catalog.id,
            defaults=defaults,
        )
        if created:
            obj.created_at = catalog.created_at
            obj.save(update_fields=["created_at"])
        logger.debug(
            "saved fault catalog row",
            extra={"catalog_id": str(catalog.id), "is_new": created},
        )
        return catalog

    def deactivate_missing(self, seen_keys: set[tuple[str, str]]) -> int:
        """Deactivate active rows whose (code, code_group) is absent from seen_keys."""
        qs = FaultCatalogModel.objects.filter(is_active=True, is_deleted=False)
        if seen_keys:
            keep = Q()
            for code, code_group in seen_keys:
                keep |= Q(code=code, code_group=code_group)
            qs = qs.exclude(keep)
        return qs.update(is_active=False, updated_at=datetime.now(tz=UTC))
