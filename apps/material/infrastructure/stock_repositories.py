"""Django ORM repository for SAP-synced central warehouse stock."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from django.db.models import Q, Sum

from apps.material.domain.interfaces.central_stock_repository import (
    ICentralStockRepository,
)
from apps.material.domain.stock_entities import CentralStock
from apps.material.infrastructure.models import CentralStockModel
from core.domain.exceptions import DomainNotFoundError
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger(domain="material", module=__name__)


def _to_domain(orm: CentralStockModel) -> CentralStock:
    """Map ORM row to domain entity."""
    return CentralStock(
        id=uuid.UUID(str(orm.id)),
        material=orm.material,
        plant=orm.plant,
        storage_location=orm.storage_location,
        inventory_stock_type=orm.inventory_stock_type,
        material_code=orm.material_code,
        inventory_stock_type_text=orm.inventory_stock_type_text,
        quantity=orm.quantity,
        base_unit=orm.base_unit,
        stock_value=orm.stock_value,
        display_currency=orm.display_currency,
        is_active=orm.is_active,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
        material_name=orm.material_name or "",
    )


def _normalize_material(material_number: str) -> tuple[str, str]:
    """Return padded and stripped forms of a material number for matching."""
    raw = material_number.strip()
    stripped = raw.lstrip("0") or "0"
    return raw, stripped


class DjangoCentralStockRepository(ICentralStockRepository):
    """ORM-backed repository for central warehouse stock rows."""

    # Enables per-row savepoints during SAP sync (see _atomic_if_supported).
    uses_transactions = True

    def get_by_id(self, stock_id: uuid.UUID) -> CentralStock:
        """Retrieve one stock row by UUID."""
        try:
            orm = CentralStockModel.objects.get(id=stock_id, is_deleted=False)
        except CentralStockModel.DoesNotExist as exc:
            raise DomainNotFoundError(
                f"Central stock row '{stock_id}' not found."
            ) from exc
        return _to_domain(orm)

    def get_by_sap_key(
        self,
        material: str,
        plant: str,
        storage_location: str,
        inventory_stock_type: str,
    ) -> CentralStock | None:
        """Retrieve one stock row by SAP natural key."""
        orm = CentralStockModel.objects.filter(
            material=material,
            plant=plant,
            storage_location=storage_location,
            inventory_stock_type=inventory_stock_type,
            is_deleted=False,
        ).first()
        return _to_domain(orm) if orm else None

    def get_available_quantity(self, material_number: str) -> Decimal:
        """Return unrestricted quantity for a material across KH08 rows."""
        qs = self._matching_active_rows(material_number).filter(
            inventory_stock_type="01"
        )
        total = qs.aggregate(total=Sum("quantity"))["total"]
        return total if total is not None else Decimal("0")

    def material_exists(self, material_number: str) -> bool:
        """Return whether any active KH08 stock row exists for the material."""
        return self._matching_active_rows(material_number).exists()

    def get_material_name(self, material_number: str) -> str:
        """Return the first non-empty material name for the material, if any."""
        row = (
            self._matching_active_rows(material_number)
            .exclude(material_name="")
            .order_by("material_code")
            .first()
        )
        if row is None:
            return ""
        return row.material_name or ""

    def _matching_active_rows(self, material_number: str):
        """Filter active stock rows matching padded or short material number."""
        padded, stripped = _normalize_material(material_number)
        return CentralStockModel.objects.filter(
            is_active=True,
            is_deleted=False,
        ).filter(
            Q(material=padded)
            | Q(material_code=stripped)
            | Q(material_code=padded)
            | Q(material__endswith=stripped)
        )

    def list_active(
        self,
        *,
        plant: str = "",
        storage_location: str = "",
        search: str = "",
    ) -> list[CentralStock]:
        """Return active stock rows ordered by material code."""
        qs = CentralStockModel.objects.filter(is_active=True, is_deleted=False)
        if plant:
            qs = qs.filter(plant=plant)
        if storage_location:
            qs = qs.filter(storage_location=storage_location)
        if search:
            qs = qs.filter(
                Q(material__icontains=search)
                | Q(material_code__icontains=search)
                | Q(material_name__icontains=search)
                | Q(inventory_stock_type_text__icontains=search)
            )
        return [
            _to_domain(orm)
            for orm in qs.order_by("material_code", "inventory_stock_type")
        ]

    def save(self, stock: CentralStock) -> CentralStock:
        """Persist a new or updated stock row."""
        defaults = {
            "material": stock.material,
            "plant": stock.plant,
            "storage_location": stock.storage_location,
            "inventory_stock_type": stock.inventory_stock_type,
            "material_code": stock.material_code,
            "material_name": stock.material_name,
            "inventory_stock_type_text": stock.inventory_stock_type_text,
            "quantity": stock.quantity,
            "base_unit": stock.base_unit,
            "stock_value": stock.stock_value,
            "display_currency": stock.display_currency,
            "is_active": stock.is_active,
            "updated_at": datetime.now(tz=UTC),
        }
        obj, created = CentralStockModel.objects.update_or_create(
            id=stock.id,
            defaults=defaults,
        )
        if created:
            obj.created_at = stock.created_at
            obj.save(update_fields=["created_at"])
        logger.debug(
            "saved central stock row",
            extra={"stock_id": str(stock.id), "is_new": created},
        )
        return stock
