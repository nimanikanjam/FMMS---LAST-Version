"""Django ORM models for the Fault bounded context."""

from __future__ import annotations

from django.db import models

from infrastructure.database.model_mixins import BusinessRecordModel


class FaultModel(BusinessRecordModel):
    """Persistence model for a vehicle fault aggregate root.

    Cross-domain references (vehicle, inspection) are UUIDFields — not FKs —
    to maintain aggregate boundary independence.
    """

    vehicle_id = models.UUIDField(db_index=True)
    code = models.CharField(max_length=20, db_index=True)
    description = models.CharField(max_length=500)
    reported_at = models.DateTimeField()
    severity = models.CharField(max_length=10, db_index=True)
    status = models.CharField(max_length=32, db_index=True)
    reported_by_id = models.UUIDField()
    inspection_id = models.UUIDField(null=True, blank=True, default=None)
    sap_defect_code = models.CharField(max_length=30, blank=True, default="")
    sap_notification_number = models.CharField(max_length=30, blank=True, default="")
    assigned_to_id = models.UUIDField(null=True, blank=True, default=None)
    distribution_decision_note = models.CharField(
        max_length=500, blank=True, default=""
    )

    class Meta:
        app_label = "fault"
        db_table = "fault"
        verbose_name = "Fault"
        verbose_name_plural = "Faults"
        indexes = [
            models.Index(
                fields=["vehicle_id", "status", "is_deleted"],
                name="fault_vehicle_status_idx",
            ),
            models.Index(
                fields=["severity", "status", "is_deleted"],
                name="fault_severity_status_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"Fault {self.id} [{self.severity}/{self.status}]"


class FaultItemModel(BusinessRecordModel):
    """Persistence model for a failed component within a fault incident."""

    fault_id = models.UUIDField(db_index=True)
    inspection_item_id = models.UUIDField(null=True, blank=True, default=None)
    component = models.CharField(max_length=100)
    description = models.CharField(max_length=500)
    severity = models.CharField(max_length=10, db_index=True)

    class Meta:
        app_label = "fault"
        db_table = "fault_item"
        verbose_name = "Fault Item"
        verbose_name_plural = "Fault Items"
        indexes = [
            models.Index(
                fields=["fault_id", "is_deleted"],
                name="fault_item_fault_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"FaultItem {self.id} [{self.component}]"


class FaultCatalogModel(BusinessRecordModel):
    """Local cache of SAP defect catalog rows used for manual fault reporting."""

    code_group = models.CharField(max_length=40, db_index=True)
    code = models.CharField(max_length=40, db_index=True)
    group_text = models.CharField(max_length=100)
    code_text = models.CharField(max_length=500)
    defect_class = models.CharField(max_length=20, db_index=True)
    defect_class_text = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        app_label = "fault"
        db_table = "fault_catalog"
        verbose_name = "Fault Catalog"
        verbose_name_plural = "Fault Catalogs"
        constraints = [
            models.UniqueConstraint(
                fields=["code", "code_group"],
                condition=models.Q(is_deleted=False),
                name="unique_active_fault_catalog_sap_key",
            ),
        ]
        indexes = [
            models.Index(
                fields=["is_active", "is_deleted"],
                name="fault_cat_active_deleted_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.code_group}/{self.code}: {self.code_text}"
