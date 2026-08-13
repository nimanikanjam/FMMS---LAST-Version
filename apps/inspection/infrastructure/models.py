"""Django ORM models for the Inspection bounded context.

InspectionItemModel is a child record of InspectionModel — it is part of the
Inspection aggregate and must not be accessed outside the repository.
"""

from __future__ import annotations

from django.db import models

from infrastructure.database.model_mixins import BusinessRecordModel


class InspectionModel(BusinessRecordModel):
    """Persistence model for a vehicle inspection aggregate root."""

    vehicle_id = models.UUIDField(db_index=True)
    driver_id = models.UUIDField(null=True, blank=True, default=None)
    inspection_type = models.CharField(max_length=20)
    odometer_value = models.PositiveIntegerField()
    odometer_unit = models.CharField(max_length=10)
    status = models.CharField(max_length=20, db_index=True)
    inspected_at = models.DateTimeField()
    reviewed_by_id = models.UUIDField(null=True, blank=True, default=None)
    review_notes = models.TextField(blank=True, default="")

    class Meta:
        app_label = "inspection"
        db_table = "inspection"
        verbose_name = "Inspection"
        verbose_name_plural = "Inspections"
        indexes = [
            models.Index(
                fields=["vehicle_id", "status", "is_deleted"],
                name="insp_vehicle_status_idx",
            ),
            models.Index(
                fields=["inspected_at"],
                name="insp_inspected_at_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"Inspection {self.id} [{self.status}]"


class InspectionItemModel(models.Model):
    """Persistence model for a single checklist item within an inspection.

    Does not extend BusinessRecordModel — items follow their parent's lifecycle
    and are never soft-deleted independently.
    """

    inspection = models.ForeignKey(
        InspectionModel,
        on_delete=models.CASCADE,
        related_name="items",
        db_index=True,
    )
    item_id = models.UUIDField()
    category = models.CharField(max_length=100)
    description = models.CharField(max_length=500)
    result = models.CharField(max_length=20)
    notes = models.TextField(blank=True, default="")
    severity = models.CharField(max_length=10, blank=True, default="")

    class Meta:
        app_label = "inspection"
        db_table = "inspection_item"
        verbose_name = "Inspection Item"
        verbose_name_plural = "Inspection Items"
        constraints = [
            models.UniqueConstraint(
                fields=["inspection", "item_id"],
                name="unique_inspection_item",
            )
        ]

    def __str__(self) -> str:
        return f"Item {self.item_id} [{self.result}]"


class InspectionTemplateModel(BusinessRecordModel):
    """Local cache of SAP inspection-template catalog entries."""

    code_group = models.CharField(max_length=40, db_index=True)
    code = models.CharField(max_length=40, db_index=True)
    group_text = models.CharField(max_length=100)
    code_text = models.CharField(max_length=500)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        app_label = "inspection"
        db_table = "inspection_template"
        verbose_name = "Inspection Template"
        verbose_name_plural = "Inspection Templates"
        constraints = [
            models.UniqueConstraint(
                fields=["code", "code_group"],
                condition=models.Q(is_deleted=False),
                name="unique_active_inspection_template_sap_key",
            ),
        ]
        indexes = [
            models.Index(
                fields=["is_active", "is_deleted"],
                name="insp_tmpl_active_deleted_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.code_group}/{self.code}: {self.code_text}"
