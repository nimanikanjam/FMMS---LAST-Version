"""Django ORM models for the Preventive Maintenance bounded context.

Two independent aggregates: PMPlanModel and PMWorkOrderModel.
PMWorkOrderModel references its plan by UUID (cross-aggregate reference),
not by FK, to preserve aggregate boundary independence.
"""

from __future__ import annotations

from django.db import models

from infrastructure.database.model_mixins import BusinessRecordModel


class PMPlanModel(BusinessRecordModel):
    """Persistence model for a Preventive Maintenance Plan aggregate root.

    MaintenanceInterval and TriggerCondition value objects are stored as
    flat columns — they are small and do not have independent lifecycle.
    'initiator_id' holds the domain created_by_id (avoids clash with
    UserAuditMixin.created_by FK auto-column).
    """

    vehicle_id = models.UUIDField(db_index=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, db_index=True)
    # MaintenanceInterval
    interval_value = models.PositiveIntegerField()
    interval_unit = models.CharField(max_length=10)
    # TriggerCondition
    trigger_type = models.CharField(max_length=20)
    trigger_threshold = models.PositiveIntegerField()
    initiator_id = models.UUIDField()
    last_triggered_at = models.DateTimeField(null=True, blank=True, default=None)
    next_due_at = models.DateTimeField(null=True, blank=True, default=None)

    class Meta:
        app_label = "preventive_maintenance"
        db_table = "pm_plan"
        verbose_name = "PM Plan"
        verbose_name_plural = "PM Plans"
        indexes = [
            models.Index(
                fields=["vehicle_id", "status", "is_deleted"],
                name="pm_plan_vehicle_status_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"PMPlan {self.name} [{self.status}]"


class PMWorkOrderModel(BusinessRecordModel):
    """Persistence model for a PM Work Order aggregate root.

    References PMPlanModel via plan_id (UUID) to respect aggregate boundaries.
    """

    plan_id = models.UUIDField(db_index=True)
    vehicle_id = models.UUIDField(db_index=True)
    status = models.CharField(max_length=20, db_index=True)
    scheduled_date = models.DateTimeField()
    triggered_at = models.DateTimeField(null=True, blank=True, default=None)
    completed_at = models.DateTimeField(null=True, blank=True, default=None)
    notes = models.TextField(blank=True, default="")
    sap_order_number = models.CharField(max_length=30, blank=True, default="")

    class Meta:
        app_label = "preventive_maintenance"
        db_table = "pm_work_order"
        verbose_name = "PM Work Order"
        verbose_name_plural = "PM Work Orders"
        indexes = [
            models.Index(
                fields=["plan_id", "status", "is_deleted"],
                name="pm_wo_plan_status_idx",
            ),
            models.Index(
                fields=["scheduled_date", "status"],
                name="pm_wo_scheduled_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"PMWorkOrder {self.id} [{self.status}]"
