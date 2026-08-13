"""Django ORM models for the Procurement bounded context.

Two aggregates: PurchaseRequisition and PurchaseOrder.
Line items are child records (part of each aggregate) stored in separate tables.
"""

from __future__ import annotations

from decimal import Decimal

from django.db import models

from infrastructure.database.model_mixins import BusinessRecordModel


class PurchaseRequisitionModel(BusinessRecordModel):
    """Persistence model for a Purchase Requisition aggregate root."""

    repair_order_id = models.UUIDField(db_index=True)
    status = models.CharField(max_length=20, db_index=True)
    requested_by_id = models.UUIDField()
    material_request_id = models.UUIDField(null=True, blank=True, default=None)
    sap_pr_number = models.CharField(max_length=10, blank=True, default="")
    approved_by_id = models.UUIDField(null=True, blank=True, default=None)

    class Meta:
        app_label = "procurement"
        db_table = "purchase_requisition"
        verbose_name = "Purchase Requisition"
        verbose_name_plural = "Purchase Requisitions"
        indexes = [
            models.Index(
                fields=["repair_order_id", "is_deleted"],
                name="pr_repair_order_idx",
            ),
            models.Index(
                fields=["status", "is_deleted"],
                name="pr_status_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"PR {self.id} [{self.status}]"


class PRLineItemModel(models.Model):
    """Persistence model for a line item within a Purchase Requisition."""

    pr = models.ForeignKey(
        PurchaseRequisitionModel,
        on_delete=models.CASCADE,
        related_name="line_items",
        db_index=True,
    )
    item_id = models.UUIDField()
    material_number = models.CharField(max_length=18)
    quantity_value = models.DecimalField(max_digits=12, decimal_places=3)
    quantity_uom = models.CharField(max_length=10)
    description = models.CharField(max_length=500)
    estimated_price_amount = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True, default=None
    )
    estimated_price_currency = models.CharField(max_length=3, blank=True, default="")

    class Meta:
        app_label = "procurement"
        db_table = "pr_line_item"
        verbose_name = "PR Line Item"
        verbose_name_plural = "PR Line Items"
        constraints = [
            models.UniqueConstraint(
                fields=["pr", "item_id"], name="unique_pr_line_item"
            )
        ]


class PurchaseOrderModel(BusinessRecordModel):
    """Persistence model for a Purchase Order aggregate root."""

    pr_id = models.UUIDField(db_index=True)
    vendor_number = models.CharField(max_length=10, db_index=True)
    status = models.CharField(max_length=20, db_index=True)
    # 'po_initiator_id' avoids the UserAuditMixin.created_by FK attname clash.
    po_initiator_id = models.UUIDField()
    sap_po_number = models.CharField(max_length=10, blank=True, default="")
    approved_by_id = models.UUIDField(null=True, blank=True, default=None)

    class Meta:
        app_label = "procurement"
        db_table = "purchase_order"
        verbose_name = "Purchase Order"
        verbose_name_plural = "Purchase Orders"
        indexes = [
            models.Index(
                fields=["pr_id", "is_deleted"],
                name="po_pr_idx",
            ),
            models.Index(
                fields=["status", "is_deleted"],
                name="po_status_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["sap_po_number"],
                condition=models.Q(is_deleted=False, sap_po_number__gt=""),
                name="unique_active_sap_po_number",
            )
        ]

    def __str__(self) -> str:
        return f"PO {self.id} [{self.status}]"


class POLineItemModel(models.Model):
    """Persistence model for a line item within a Purchase Order."""

    po = models.ForeignKey(
        PurchaseOrderModel,
        on_delete=models.CASCADE,
        related_name="line_items",
        db_index=True,
    )
    item_id = models.UUIDField()
    material_number = models.CharField(max_length=18)
    quantity_value = models.DecimalField(max_digits=12, decimal_places=3)
    quantity_uom = models.CharField(max_length=10)
    unit_price_amount = models.DecimalField(max_digits=15, decimal_places=2)
    unit_price_currency = models.CharField(max_length=3)
    received_quantity = models.DecimalField(
        max_digits=12, decimal_places=3, default=Decimal("0")
    )

    class Meta:
        app_label = "procurement"
        db_table = "po_line_item"
        verbose_name = "PO Line Item"
        verbose_name_plural = "PO Line Items"
        constraints = [
            models.UniqueConstraint(
                fields=["po", "item_id"], name="unique_po_line_item"
            )
        ]
