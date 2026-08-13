"""Django ORM models for material requests."""

from __future__ import annotations

from decimal import Decimal

from django.db import models

from infrastructure.database.model_mixins import BusinessRecordModel


class MaterialRequestModel(BusinessRecordModel):
    """Persistence model for material requests."""

    repair_order_id = models.UUIDField(db_index=True)
    status = models.CharField(max_length=30, db_index=True)
    # Domain "requested_by" — cannot use created_by_id (UserAuditMixin FK attname).
    requested_by_id = models.UUIDField()

    class Meta:
        app_label = "material"
        db_table = "material_request"
        indexes = [
            models.Index(
                fields=["repair_order_id", "is_deleted"], name="mr_repair_idx"
            ),
            models.Index(fields=["status", "is_deleted"], name="mr_status_idx"),
        ]


class MaterialRequestItemModel(models.Model):
    """Persistence model for material request items."""

    material_request = models.ForeignKey(
        MaterialRequestModel,
        on_delete=models.CASCADE,
        related_name="items",
    )
    item_id = models.UUIDField()
    material_number = models.CharField(max_length=18)
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit_of_measure = models.CharField(max_length=10)
    from_catalog = models.BooleanField(default=True)
    decision = models.CharField(max_length=20, default="PENDING")
    item_status = models.CharField(max_length=30, default="PENDING")
    available_quantity_snapshot = models.DecimalField(
        max_digits=18, decimal_places=3, null=True, blank=True
    )

    class Meta:
        app_label = "material"
        db_table = "material_request_item"


class InventoryTransactionModel(models.Model):
    """Placeholder inventory transaction for issued stock."""

    material_request_id = models.UUIDField(db_index=True)
    quantity = models.DecimalField(
        max_digits=12, decimal_places=3, default=Decimal("0")
    )
    transaction_type = models.CharField(max_length=30, default="STOCK_ISSUE")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "material"
        db_table = "inventory_transaction"


class CentralStockModel(BusinessRecordModel):
    """Local cache of SAP central spare-parts warehouse stock (KH08)."""

    material = models.CharField(max_length=40, db_index=True)
    plant = models.CharField(max_length=10, db_index=True)
    storage_location = models.CharField(max_length=10, db_index=True)
    inventory_stock_type = models.CharField(max_length=10, db_index=True)
    material_code = models.CharField(max_length=40, db_index=True)
    material_name = models.CharField(max_length=255, blank=True, default="")
    inventory_stock_type_text = models.CharField(max_length=100)
    quantity = models.DecimalField(
        max_digits=18, decimal_places=3, default=Decimal("0")
    )
    base_unit = models.CharField(max_length=10)
    stock_value = models.DecimalField(
        max_digits=18, decimal_places=2, default=Decimal("0")
    )
    display_currency = models.CharField(max_length=5, default="")
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        app_label = "material"
        db_table = "central_stock"
        verbose_name = "Central Stock"
        verbose_name_plural = "Central Stock"
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "material",
                    "plant",
                    "storage_location",
                    "inventory_stock_type",
                ],
                condition=models.Q(is_deleted=False),
                name="unique_active_central_stock_sap_key",
            ),
        ]
        indexes = [
            models.Index(
                fields=["is_active", "is_deleted"],
                name="central_stock_active_del_idx",
            ),
            models.Index(
                fields=["plant", "storage_location"],
                name="central_stock_plant_sloc_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.material_code}@{self.storage_location}: {self.quantity}"
