"""Model-free serializers for repair API v1."""

from __future__ import annotations

from rest_framework import serializers

from apps.repair.domain.entities import (
    ExternalWorkshopReferralStatus,
    RepairOrderStatus,
    WorkshopType,
)
from apps.repair.domain.external_workshop_entities import (
    ExternalRepairReviewStatus,
    ExternalWorkshopAssignmentCancellationReason,
    ExternalWorkshopAssignmentStatus,
)
from apps.repair.domain.invoice_entities import ExternalRepairInvoiceStatus


class RepairOrderCreateSerializer(serializers.Serializer):
    """Validate repair order creation input."""

    vehicle_id = serializers.UUIDField()
    fault_id = serializers.UUIDField()


class RepairAssignSerializer(serializers.Serializer):
    """Validate repair assignment input."""

    technician_id = serializers.UUIDField()


class RepairApproveSerializer(serializers.Serializer):
    """Optional note for transport approval."""

    note = serializers.CharField(
        max_length=500, required=False, allow_blank=True, trim_whitespace=True
    )


class WorkshopTechnicalDecisionSerializer(serializers.Serializer):
    """Validate central-workshop technical inspection decision."""

    repairable = serializers.BooleanField()
    note = serializers.CharField(
        max_length=500, required=False, allow_blank=True, trim_whitespace=True
    )
    estimated_delivery_at = serializers.DateTimeField(required=False, allow_null=True)

    def validate(self, attrs: dict) -> dict:
        """Require estimated delivery date when confirming repair is needed."""
        if attrs.get("repairable") and not attrs.get("estimated_delivery_at"):
            raise serializers.ValidationError(
                {
                    "estimated_delivery_at": (
                        "estimated_delivery_at is required when repairable=True."
                    )
                }
            )
        return attrs


class RepairAssignWorkshopSerializer(serializers.Serializer):
    """Validate workshop type selection after transport approval."""

    workshop_type = serializers.ChoiceField(
        choices=[item.value for item in WorkshopType]
    )
    workshop_id = serializers.CharField(
        max_length=64, required=False, allow_null=True, allow_blank=True
    )
    reason = serializers.CharField(
        max_length=500, required=False, allow_blank=True, trim_whitespace=True
    )

    def validate(self, attrs: dict) -> dict:
        """Require workshop ID when selecting an external workshop."""
        if attrs.get("workshop_type") == WorkshopType.EXTERNAL.value and not attrs.get(
            "workshop_id"
        ):
            raise serializers.ValidationError(
                {"workshop_id": "workshop_id is required for external workshop."}
            )
        return attrs


class ExternalWorkshopAssignSerializer(serializers.Serializer):
    """Validate external workshop assignment payload."""

    workshop_id = serializers.CharField(
        max_length=64, required=False, allow_null=True, allow_blank=True
    )
    workshop_name = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default="", trim_whitespace=True
    )
    workshop_address = serializers.CharField(
        max_length=500, required=False, allow_blank=True, default="", trim_whitespace=True
    )
    assignment_date = serializers.DateTimeField()
    repair_reason = serializers.CharField(
        max_length=500, required=False, allow_blank=True, default="", trim_whitespace=True
    )
    description = serializers.CharField(
        required=False, allow_blank=True, default="", trim_whitespace=True
    )


class ExternalWorkshopDeliverySerializer(serializers.Serializer):
    """Validate driver delivery confirmation payload."""

    delivery_datetime = serializers.DateTimeField()
    workshop_name = serializers.CharField(max_length=255, trim_whitespace=True)
    workshop_address = serializers.CharField(max_length=500, trim_whitespace=True)
    workshop_phone = serializers.CharField(max_length=40, trim_whitespace=True)
    vehicle_odometer = serializers.IntegerField(min_value=0)
    notes = serializers.CharField(
        required=False, allow_blank=True, default="", trim_whitespace=True
    )


class ExternalWorkshopPickupSerializer(serializers.Serializer):
    """Validate driver pickup confirmation payload."""

    pickup_datetime = serializers.DateTimeField()
    vehicle_odometer = serializers.IntegerField(min_value=0)
    notes = serializers.CharField(
        required=False, allow_blank=True, default="", trim_whitespace=True
    )


class ExternalReplacedPartSerializer(serializers.Serializer):
    """Validate one replaced part row in external repair review."""

    material_number = serializers.CharField(
        max_length=40, required=False, allow_blank=True, trim_whitespace=True
    )
    name = serializers.CharField(
        max_length=255, required=False, allow_blank=True, trim_whitespace=True
    )
    quantity = serializers.DecimalField(
        max_digits=12, decimal_places=3, required=False, min_value=0
    )
    cost = serializers.DecimalField(
        max_digits=15, decimal_places=2, required=False, allow_null=True, min_value=0
    )
    unit_of_measure = serializers.CharField(
        max_length=10, required=False, allow_blank=True, trim_whitespace=True
    )


class ExternalRepairServiceLineSerializer(serializers.Serializer):
    """Validate one external repair service row."""

    description = serializers.CharField(max_length=500, trim_whitespace=True)
    labor_hours = serializers.DecimalField(
        max_digits=8, decimal_places=2, required=False, allow_null=True, min_value=0
    )
    cost = serializers.DecimalField(
        max_digits=15, decimal_places=2, required=False, allow_null=True, min_value=0
    )
    notes = serializers.CharField(
        required=False, allow_blank=True, default="", trim_whitespace=True
    )


class ExternalRepairReviewSerializer(serializers.Serializer):
    """Validate transportation external repair review draft payload."""

    invoice_attachment = serializers.CharField(
        max_length=500, required=False, allow_null=True, allow_blank=True
    )
    invoice_file = serializers.FileField(
        required=False, allow_null=True, allow_empty_file=False
    )
    repair_services = ExternalRepairServiceLineSerializer(
        many=True, required=False, default=list
    )
    replaced_parts = ExternalReplacedPartSerializer(many=True, required=False, default=list)
    repair_cost = serializers.DecimalField(
        max_digits=15, decimal_places=2, required=False, allow_null=True, min_value=0
    )
    additional_notes = serializers.CharField(required=False, allow_blank=True, default="")


class ExternalWorkshopCancelSerializer(serializers.Serializer):
    """Validate external workshop assignment cancellation."""

    reason = serializers.ChoiceField(
        choices=[item.value for item in ExternalWorkshopAssignmentCancellationReason]
    )
    note = serializers.CharField(
        max_length=500, required=False, allow_null=True, allow_blank=True
    )


class RepairTransportRejectSerializer(serializers.Serializer):
    """Validate initial transport rejection payload."""

    reason = serializers.CharField(max_length=500, trim_whitespace=True)


class RepairCompleteSerializer(serializers.Serializer):
    """Validate repair completion input."""

    completed_at = serializers.DateTimeField()
    no_parts_consumed = serializers.BooleanField(required=False, default=False)


class InternalRepairCostRegisterSerializer(serializers.Serializer):
    """Validate INTERNAL workshop financial registration."""

    invoice_number = serializers.CharField(max_length=64, allow_blank=True, default="")
    labor_cost = serializers.DecimalField(max_digits=15, decimal_places=2, default=0)
    parts_cost = serializers.DecimalField(max_digits=15, decimal_places=2, default=0)
    service_cost = serializers.DecimalField(max_digits=15, decimal_places=2, default=0)
    currency = serializers.CharField(max_length=3, default="IRR")
    notes = serializers.CharField(max_length=500, allow_blank=True, default="")


class InternalRepairCostResponseSerializer(serializers.Serializer):
    """Serialize internal repair cost documents."""

    id = serializers.UUIDField()
    repair_order_id = serializers.UUIDField()
    invoice_number = serializers.CharField()
    labor_cost = serializers.DecimalField(max_digits=15, decimal_places=2)
    parts_cost = serializers.DecimalField(max_digits=15, decimal_places=2)
    service_cost = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_cost = serializers.DecimalField(max_digits=15, decimal_places=2)
    currency = serializers.CharField()
    status = serializers.CharField()
    notes = serializers.CharField()
    registered_by_id = serializers.UUIDField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class TransportHandoverRejectSerializer(serializers.Serializer):
    """Validate transport post-handover rejection input."""

    comment = serializers.CharField(
        max_length=500, required=False, allow_null=True, allow_blank=True
    )


class RepairActivityCreateSerializer(serializers.Serializer):
    """Validate repair activity creation input.

    The activity itself is picked from SAP's activity catalog
    (``ZC_REPAIR01_CODE_CDS``), so ``activity_code`` is required and the
    stored label is resolved from the catalog server-side. ``description`` is
    accepted but ignored whenever a code is given; ``notes`` carries any
    free-text detail about the particular job.
    """

    activity_code = serializers.CharField(max_length=40)
    activity_code_group = serializers.CharField(max_length=40)
    description = serializers.CharField(
        max_length=500, required=False, allow_blank=True, default=""
    )
    labor_hours = serializers.DecimalField(max_digits=8, decimal_places=2)
    performed_by_id = serializers.UUIDField(required=False)
    performed_at = serializers.DateTimeField(required=False)
    notes = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class RepairPartCreateSerializer(serializers.Serializer):
    """Validate repair part creation input."""

    material_number = serializers.CharField(max_length=18)
    quantity = serializers.IntegerField(min_value=1)


class RepairSyncSAPSerializer(serializers.Serializer):
    """Validate repair-to-SAP sync input."""

    order_type = serializers.CharField(max_length=10)
    description = serializers.CharField(max_length=200)
    planned_start = serializers.DateTimeField()
    plant = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    work_center = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )


class RepairActivityResponseSerializer(serializers.Serializer):
    """Serialize repair activity DTOs."""

    id = serializers.UUIDField()
    description = serializers.CharField()
    labor_hours = serializers.DecimalField(max_digits=8, decimal_places=2)
    performed_by_id = serializers.UUIDField()
    performed_at = serializers.DateTimeField()
    notes = serializers.CharField(allow_null=True)
    activity_code = serializers.CharField()
    activity_code_group = serializers.CharField()


class RepairPartResponseSerializer(serializers.Serializer):
    """Serialize repair part DTOs."""

    id = serializers.UUIDField()
    material_number = serializers.CharField()
    quantity = serializers.IntegerField()
    goods_issue_id = serializers.UUIDField(allow_null=True)
    posted_at = serializers.DateTimeField(allow_null=True)


class RepairOrderTimelineEventSerializer(serializers.Serializer):
    """Serialize one repair-order timeline event."""

    event = serializers.CharField()
    description = serializers.CharField()
    created_at = serializers.DateTimeField()
    created_by_id = serializers.UUIDField(allow_null=True, required=False)


class RepairOrderResponseSerializer(serializers.Serializer):
    """Serialize application repair order response DTOs."""

    id = serializers.UUIDField()
    vehicle_id = serializers.UUIDField()
    fault_id = serializers.UUIDField()
    status = serializers.ChoiceField(choices=[item.value for item in RepairOrderStatus])
    created_by_id = serializers.UUIDField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    activities = RepairActivityResponseSerializer(many=True)
    parts = RepairPartResponseSerializer(many=True)
    technician_id = serializers.UUIDField(allow_null=True)
    assigned_at = serializers.DateTimeField(allow_null=True)
    sap_order_number = serializers.CharField(allow_null=True)
    workshop_type = serializers.ChoiceField(
        choices=[item.value for item in WorkshopType], allow_null=True
    )
    workshop_id = serializers.CharField(allow_null=True)
    transport_rejection_reason = serializers.CharField(allow_null=True, required=False)
    transport_approval_note = serializers.CharField(allow_null=True, required=False)
    workshop_decision_note = serializers.CharField(allow_null=True, required=False)
    completed_at = serializers.DateTimeField(allow_null=True)
    estimated_delivery_at = serializers.DateTimeField(allow_null=True, required=False)


class RepairDecisionResponseSerializer(serializers.Serializer):
    """Serialize transport approval / workshop assignment action responses."""

    id = serializers.UUIDField()
    status = serializers.ChoiceField(choices=[item.value for item in RepairOrderStatus])
    message = serializers.CharField()
    workshop_type = serializers.ChoiceField(
        choices=[item.value for item in WorkshopType],
        allow_null=True,
        required=False,
    )
    workshop_id = serializers.CharField(allow_null=True, required=False)
    external_referral_request_id = serializers.UUIDField(
        allow_null=True, required=False
    )
    transport_rejection_reason = serializers.CharField(allow_null=True, required=False)
    estimated_delivery_at = serializers.DateTimeField(allow_null=True, required=False)


class ExternalWorkshopReferralResponseSerializer(serializers.Serializer):
    """Serialize external-workshop referral permission requests."""

    id = serializers.UUIDField()
    repair_order_id = serializers.UUIDField()
    vehicle_id = serializers.UUIDField()
    fault_id = serializers.UUIDField()
    status = serializers.ChoiceField(
        choices=[item.value for item in ExternalWorkshopReferralStatus]
    )
    workshop_id = serializers.CharField(allow_null=True, required=False)
    reason = serializers.CharField()
    requested_by_id = serializers.UUIDField()
    requested_at = serializers.DateTimeField()
    approved_by_id = serializers.UUIDField(allow_null=True, required=False)
    approved_at = serializers.DateTimeField(allow_null=True, required=False)
    rejected_by_id = serializers.UUIDField(allow_null=True, required=False)
    rejected_at = serializers.DateTimeField(allow_null=True, required=False)
    rejection_reason = serializers.CharField(allow_null=True, required=False)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class ExternalWorkshopDeliveryResponseSerializer(serializers.Serializer):
    """Serialize external workshop delivery confirmation."""

    id = serializers.UUIDField()
    assignment_id = serializers.UUIDField()
    repair_order_id = serializers.UUIDField()
    vehicle_id = serializers.UUIDField()
    delivery_datetime = serializers.DateTimeField()
    workshop_name = serializers.CharField()
    workshop_address = serializers.CharField()
    workshop_phone = serializers.CharField()
    vehicle_odometer = serializers.IntegerField()
    notes = serializers.CharField()
    delivered_by_id = serializers.UUIDField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class ExternalWorkshopPickupResponseSerializer(serializers.Serializer):
    """Serialize external workshop pickup confirmation."""

    id = serializers.UUIDField()
    assignment_id = serializers.UUIDField()
    repair_order_id = serializers.UUIDField()
    vehicle_id = serializers.UUIDField()
    pickup_datetime = serializers.DateTimeField()
    vehicle_odometer = serializers.IntegerField()
    notes = serializers.CharField()
    picked_up_by_id = serializers.UUIDField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class ExternalRepairReviewResponseSerializer(serializers.Serializer):
    """Serialize external repair review."""

    id = serializers.UUIDField()
    assignment_id = serializers.UUIDField()
    repair_order_id = serializers.UUIDField()
    invoice_attachment = serializers.CharField(allow_null=True, required=False)
    repair_services = serializers.ListField(child=serializers.DictField())
    replaced_parts = serializers.ListField(child=serializers.DictField())
    repair_cost = serializers.DecimalField(
        max_digits=15, decimal_places=2, allow_null=True
    )
    additional_notes = serializers.CharField()
    sap_purchase_order_number = serializers.CharField(allow_null=True, required=False)
    sap_invoice_document_number = serializers.CharField(allow_null=True, required=False)
    status = serializers.ChoiceField(
        choices=[item.value for item in ExternalRepairReviewStatus]
    )
    reviewed_by_id = serializers.UUIDField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class ExternalWorkshopAssignmentResponseSerializer(serializers.Serializer):
    """Serialize external workshop assignment detail."""

    id = serializers.UUIDField()
    repair_order_id = serializers.UUIDField()
    vehicle_id = serializers.UUIDField()
    fault_id = serializers.UUIDField()
    workshop_id = serializers.CharField(allow_null=True, required=False)
    workshop_name = serializers.CharField()
    workshop_address = serializers.CharField()
    assignment_date = serializers.DateTimeField()
    repair_reason = serializers.CharField()
    description = serializers.CharField()
    status = serializers.ChoiceField(
        choices=[item.value for item in ExternalWorkshopAssignmentStatus]
    )
    assigned_by_id = serializers.UUIDField()
    cancellation_reason = serializers.ChoiceField(
        choices=[item.value for item in ExternalWorkshopAssignmentCancellationReason],
        allow_null=True,
        required=False,
    )
    cancellation_note = serializers.CharField(allow_null=True, required=False)
    cancelled_by_id = serializers.UUIDField(allow_null=True, required=False)
    cancelled_at = serializers.DateTimeField(allow_null=True, required=False)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    delivery = ExternalWorkshopDeliveryResponseSerializer(allow_null=True)
    pickup = ExternalWorkshopPickupResponseSerializer(allow_null=True)
    review = ExternalRepairReviewResponseSerializer(allow_null=True)


class ExternalInvoiceUploadSerializer(serializers.Serializer):
    """Validate external invoice upload payload."""

    amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    currency = serializers.CharField(max_length=3)
    vendor_id = serializers.CharField(
        max_length=64, required=False, allow_null=True, allow_blank=True
    )
    document = serializers.CharField(
        max_length=500, required=False, allow_null=True, allow_blank=True
    )


class ExternalInvoiceResponseSerializer(serializers.Serializer):
    """Serialize external invoice response DTO."""

    id = serializers.UUIDField()
    repair_order_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    currency = serializers.CharField()
    status = serializers.ChoiceField(
        choices=[item.value for item in ExternalRepairInvoiceStatus]
    )
    created_by_id = serializers.UUIDField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    vendor_id = serializers.CharField(allow_null=True, required=False)
    document = serializers.CharField(allow_null=True, required=False)
