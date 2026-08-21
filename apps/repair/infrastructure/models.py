"""Django ORM models for the Repair bounded context.

RepairOrder is the aggregate root. RepairActivity and RepairPart are child
records that must not be accessed outside the repository boundary.
"""

from __future__ import annotations

from django.db import models

from infrastructure.database.model_mixins import BusinessRecordModel


class RepairOrderModel(BusinessRecordModel):
    """Persistence model for a repair order aggregate root.

    TechnicianAssignment is denormalized into two nullable columns rather
    than a separate table, as it is a small value object with no independent
    lifecycle.
    """

    vehicle_id = models.UUIDField(db_index=True)
    fault_id = models.UUIDField(db_index=True)
    status = models.CharField(max_length=40, db_index=True)
    # 'initiator_id' stores the domain-level "who created the order".
    # We cannot use 'created_by_id' as it is the auto-generated attname
    # of UserAuditMixin.created_by (a ForeignKey).
    initiator_id = models.UUIDField()
    sap_order_number = models.CharField(max_length=30, blank=True, default="")
    workshop_type = models.CharField(max_length=20, blank=True, default="")
    workshop_id = models.CharField(max_length=64, blank=True, default="")
    transport_rejection_reason = models.CharField(
        max_length=500, blank=True, default=""
    )
    transport_approval_note = models.CharField(max_length=500, blank=True, default="")
    workshop_decision_note = models.CharField(max_length=500, blank=True, default="")
    completed_at = models.DateTimeField(null=True, blank=True, default=None)
    estimated_delivery_at = models.DateTimeField(null=True, blank=True, default=None)
    # TechnicianAssignment (value object — denormalized)
    assigned_technician_id = models.UUIDField(null=True, blank=True, default=None)
    assigned_at = models.DateTimeField(null=True, blank=True, default=None)

    class Meta:
        app_label = "repair"
        db_table = "repair_order"
        verbose_name = "Repair Order"
        verbose_name_plural = "Repair Orders"
        indexes = [
            models.Index(
                fields=["vehicle_id", "status", "is_deleted"],
                name="repair_vehicle_status_idx",
            ),
            models.Index(
                fields=["fault_id", "is_deleted"],
                name="repair_fault_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"RepairOrder {self.id} [{self.status}]"


class RepairActivityModel(models.Model):
    """Persistence model for a single repair activity within a repair order."""

    repair_order = models.ForeignKey(
        RepairOrderModel,
        on_delete=models.CASCADE,
        related_name="activities",
        db_index=True,
    )
    activity_id = models.UUIDField()
    # SAP activity-catalog key (ZC_REPAIR01_CODE_CDS). Blank on activities
    # recorded before the catalog was introduced.
    activity_code = models.CharField(max_length=40, blank=True, default="", db_index=True)
    activity_code_group = models.CharField(max_length=40, blank=True, default="")
    description = models.CharField(max_length=500)
    labor_hours = models.DecimalField(max_digits=6, decimal_places=2)
    performed_by_id = models.UUIDField()
    performed_at = models.DateTimeField()
    notes = models.TextField(blank=True, default="")

    class Meta:
        app_label = "repair"
        db_table = "repair_activity"
        verbose_name = "Repair Activity"
        verbose_name_plural = "Repair Activities"
        constraints = [
            models.UniqueConstraint(
                fields=["repair_order", "activity_id"],
                name="unique_repair_activity",
            )
        ]


class RepairPartModel(models.Model):
    """Persistence model for a spare part consumed during a repair order."""

    repair_order = models.ForeignKey(
        RepairOrderModel,
        on_delete=models.CASCADE,
        related_name="parts",
        db_index=True,
    )
    part_id = models.UUIDField()
    material_number = models.CharField(max_length=18)
    quantity = models.PositiveIntegerField()
    unit_of_measure = models.CharField(max_length=10)
    goods_issue_id = models.UUIDField(null=True, blank=True, default=None)
    posted_at = models.DateTimeField(null=True, blank=True, default=None)

    class Meta:
        app_label = "repair"
        db_table = "repair_part"
        verbose_name = "Repair Part"
        verbose_name_plural = "Repair Parts"
        constraints = [
            models.UniqueConstraint(
                fields=["repair_order", "part_id"],
                name="unique_repair_part",
            )
        ]


class RepairOrderEventModel(BusinessRecordModel):
    """Append-only timeline events for a repair order aggregate."""

    repair_order = models.ForeignKey(
        RepairOrderModel,
        on_delete=models.CASCADE,
        related_name="events",
        db_index=True,
    )
    event_type = models.CharField(max_length=40, db_index=True)
    description = models.CharField(max_length=500)
    actor_id = models.UUIDField(null=True, blank=True, default=None)

    class Meta:
        app_label = "repair"
        db_table = "repair_order_event"
        verbose_name = "Repair Order Event"
        verbose_name_plural = "Repair Order Events"
        ordering = ["created_at"]


class ExternalRepairInvoiceModel(BusinessRecordModel):
    """Persistence model for external workshop invoices."""

    repair_order = models.ForeignKey(
        RepairOrderModel,
        on_delete=models.CASCADE,
        related_name="external_invoices",
        db_index=True,
    )
    vendor_id = models.CharField(max_length=64, blank=True, default="")
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=3)
    document = models.CharField(max_length=500, blank=True, default="")
    status = models.CharField(max_length=20, db_index=True)
    uploaded_by_id = models.UUIDField()

    class Meta:
        app_label = "repair"
        db_table = "external_repair_invoice"


class InternalRepairCostModel(BusinessRecordModel):
    """Financial registration for INTERNAL central-workshop repairs."""

    repair_order_id = models.UUIDField(db_index=True)
    invoice_number = models.CharField(max_length=64, blank=True, default="")
    labor_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    parts_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    service_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="IRR")
    status = models.CharField(max_length=20, db_index=True)
    notes = models.CharField(max_length=500, blank=True, default="")
    registered_by_id = models.UUIDField()

    class Meta:
        app_label = "repair"
        db_table = "internal_repair_cost"
        indexes = [
            models.Index(
                fields=["repair_order_id", "is_deleted"],
                name="internal_cost_order_idx",
            ),
        ]


class ExternalWorkshopReferralRequestModel(BusinessRecordModel):
    """Permission request for referring a repair order to an external workshop."""

    repair_order_id = models.UUIDField(db_index=True)
    vehicle_id = models.UUIDField(db_index=True)
    fault_id = models.UUIDField(db_index=True)
    status = models.CharField(max_length=20, db_index=True)
    workshop_id = models.CharField(max_length=64, blank=True, default="")
    reason = models.CharField(max_length=500, blank=True, default="")
    requested_by_id = models.UUIDField()
    requested_at = models.DateTimeField()
    approved_by_id = models.UUIDField(null=True, blank=True, default=None)
    approved_at = models.DateTimeField(null=True, blank=True, default=None)
    rejected_by_id = models.UUIDField(null=True, blank=True, default=None)
    rejected_at = models.DateTimeField(null=True, blank=True, default=None)
    rejection_reason = models.CharField(max_length=500, blank=True, default="")

    class Meta:
        app_label = "repair"
        db_table = "external_workshop_referral_request"
        verbose_name = "External Workshop Referral Request"
        verbose_name_plural = "External Workshop Referral Requests"
        indexes = [
            models.Index(
                fields=["repair_order_id", "status", "is_deleted"],
                name="ext_ref_order_status_idx",
            ),
            models.Index(
                fields=["status", "is_deleted"],
                name="ext_ref_status_idx",
            ),
        ]


class ExternalWorkshopAssignmentModel(BusinessRecordModel):
    """External workshop assignment created by Transportation."""

    repair_order_id = models.UUIDField(db_index=True)
    vehicle_id = models.UUIDField(db_index=True)
    fault_id = models.UUIDField(db_index=True)
    workshop_id = models.CharField(max_length=64, blank=True, default="")
    workshop_name = models.CharField(max_length=255, blank=True, default="")
    workshop_address = models.CharField(max_length=500, blank=True, default="")
    assignment_date = models.DateTimeField()
    repair_reason = models.CharField(max_length=500, blank=True, default="")
    description = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, db_index=True)
    assigned_by_id = models.UUIDField()
    cancellation_reason = models.CharField(max_length=40, blank=True, default="")
    cancellation_note = models.CharField(max_length=500, blank=True, default="")
    cancelled_by_id = models.UUIDField(null=True, blank=True, default=None)
    cancelled_at = models.DateTimeField(null=True, blank=True, default=None)

    class Meta:
        app_label = "repair"
        db_table = "external_workshop_assignment"
        indexes = [
            models.Index(
                fields=["repair_order_id", "status", "is_deleted"],
                name="ext_assign_order_status_idx",
            ),
            models.Index(
                fields=["vehicle_id", "status", "is_deleted"],
                name="ext_assign_vehicle_status_idx",
            ),
        ]


class ExternalWorkshopDeliveryModel(BusinessRecordModel):
    """Driver confirmation of delivery to an external workshop."""

    assignment = models.OneToOneField(
        ExternalWorkshopAssignmentModel,
        on_delete=models.CASCADE,
        related_name="delivery",
    )
    repair_order_id = models.UUIDField(db_index=True)
    vehicle_id = models.UUIDField(db_index=True)
    delivery_datetime = models.DateTimeField()
    workshop_name = models.CharField(max_length=255)
    workshop_address = models.CharField(max_length=500)
    workshop_phone = models.CharField(max_length=40)
    vehicle_odometer = models.PositiveIntegerField()
    notes = models.TextField(blank=True, default="")
    delivered_by_id = models.UUIDField()

    class Meta:
        app_label = "repair"
        db_table = "external_workshop_delivery"


class ExternalWorkshopPickupModel(BusinessRecordModel):
    """Driver confirmation of pickup from an external workshop."""

    assignment = models.OneToOneField(
        ExternalWorkshopAssignmentModel,
        on_delete=models.CASCADE,
        related_name="pickup",
    )
    repair_order_id = models.UUIDField(db_index=True)
    vehicle_id = models.UUIDField(db_index=True)
    pickup_datetime = models.DateTimeField()
    vehicle_odometer = models.PositiveIntegerField()
    notes = models.TextField(blank=True, default="")
    picked_up_by_id = models.UUIDField()

    class Meta:
        app_label = "repair"
        db_table = "external_workshop_pickup"


class ExternalRepairReviewModel(BusinessRecordModel):
    """Transportation administrative review after external repair pickup."""

    assignment = models.OneToOneField(
        ExternalWorkshopAssignmentModel,
        on_delete=models.CASCADE,
        related_name="repair_review",
    )
    repair_order_id = models.UUIDField(db_index=True)
    invoice_attachment = models.CharField(max_length=500, blank=True, default="")
    repair_services = models.JSONField(default=list, blank=True)
    replaced_parts = models.JSONField(default=list, blank=True)
    repair_cost = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True, default=None
    )
    additional_notes = models.TextField(blank=True, default="")
    sap_purchase_order_number = models.CharField(max_length=64, blank=True, default="")
    sap_invoice_document_number = models.CharField(
        max_length=64, blank=True, default=""
    )
    status = models.CharField(max_length=20, db_index=True)
    reviewed_by_id = models.UUIDField()

    class Meta:
        app_label = "repair"
        db_table = "external_repair_review"


class RepairActivityOptionModel(BusinessRecordModel):
    """Local cache of SAP's activity catalog (type "A").

    Offered as the pick-list when a technician records the work performed on
    a repair order.
    """

    catalog_type = models.CharField(max_length=10, db_index=True)
    code_group = models.CharField(max_length=40, db_index=True)
    code = models.CharField(max_length=40, db_index=True)
    code_text = models.CharField(max_length=500)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        app_label = "repair"
        db_table = "repair_activity_option"
        verbose_name = "Repair Activity Option"
        verbose_name_plural = "Repair Activity Options"
        constraints = [
            models.UniqueConstraint(
                fields=["code", "code_group"],
                condition=models.Q(is_deleted=False),
                name="unique_active_repair_activity_option_sap_key",
            ),
        ]
        indexes = [
            models.Index(
                fields=["is_active", "is_deleted"],
                name="repair_act_opt_active_idx",
            ),
        ]

    def __str__(self) -> str:
        """Return the SAP code and its label."""
        return f"{self.code} — {self.code_text}"
