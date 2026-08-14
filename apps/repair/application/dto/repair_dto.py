"""Application-layer DTOs for the Repair domain.

Rules:
- No ORM models, no Django objects, no database objects.
- All fields are primitive Python types or domain enums.
- Mapping DTO <-> Domain Entity happens explicitly inside each service.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

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


@dataclass(frozen=True)
class CreateRepairOrderDTO:
    """Input DTO for creating a new repair order.

    Attributes:
        vehicle_id: UUID of the vehicle requiring repair.
        fault_id: UUID of the originating fault.
        request_id: Correlation ID for tracing.
        created_by: UUID of the authenticated user creating the order.
    """

    vehicle_id: uuid.UUID
    fault_id: uuid.UUID
    request_id: str
    created_by: uuid.UUID


@dataclass(frozen=True)
class AssignRepairOrderDTO:
    """Input DTO for assigning a technician to a repair order.

    Attributes:
        repair_order_id: UUID of the repair order to assign.
        technician_id: UUID of the technician receiving the assignment.
        request_id: Correlation ID for tracing.
        assigned_by: UUID of the user performing the assignment.
    """

    repair_order_id: uuid.UUID
    technician_id: uuid.UUID
    request_id: str
    assigned_by: uuid.UUID


@dataclass(frozen=True)
class CloseRepairOrderDTO:
    """Input DTO for cancelling a repair order.

    Attributes:
        repair_order_id: UUID of the repair order to cancel.
        request_id: Correlation ID for tracing.
        requested_by: UUID of the user requesting cancellation.
    """

    repair_order_id: uuid.UUID
    request_id: str
    requested_by: uuid.UUID


@dataclass(frozen=True)
class CompleteRepairOrderDTO:
    """Input DTO for completing a repair order (IN_PROGRESS → COMPLETED).

    Attributes:
        repair_order_id: UUID of the repair order to complete.
        completed_at: UTC timestamp when the repair was physically completed.
        request_id: Correlation ID for tracing.
        completed_by: UUID of the user marking the order complete.
        no_parts_consumed: When True, allows completion without consumed-part rows
            even if parts were requested and received.
    """

    repair_order_id: uuid.UUID
    completed_at: datetime
    request_id: str
    completed_by: uuid.UUID
    no_parts_consumed: bool = False


@dataclass(frozen=True)
class AddRepairActivityDTO:
    """Input DTO for adding a repair activity to an active order.

    Attributes:
        repair_order_id: UUID of the target repair order (must be mutable).
        description: Description of the work performed.
        labor_hours: Hours spent expressed as a decimal.
        performed_by_id: UUID of the technician who performed the activity.
        performed_at: UTC timestamp when the activity was completed.
        request_id: Correlation ID for tracing.
        notes: Optional additional technician notes.
    """

    repair_order_id: uuid.UUID
    description: str
    labor_hours: Decimal
    performed_by_id: uuid.UUID
    performed_at: datetime
    request_id: str
    notes: str | None = field(default=None)


@dataclass(frozen=True)
class UpdateRepairActivityDTO:
    """Input DTO for editing a repair activity on an active order."""

    repair_order_id: uuid.UUID
    activity_id: uuid.UUID
    description: str
    labor_hours: Decimal
    request_id: str
    notes: str | None = field(default=None)


@dataclass(frozen=True)
class DeleteRepairActivityDTO:
    """Input DTO for deleting a repair activity."""

    repair_order_id: uuid.UUID
    activity_id: uuid.UUID
    request_id: str


@dataclass(frozen=True)
class SyncRepairToSAPDTO:
    """Input DTO for syncing a repair order to SAP as a PM Order.

    The service depends only on ``ISAPPMOrderPort`` (from ``core/sap/ports``).
    Idempotency and transaction tracking are wired at the composition root
    around the port — never imported as concrete infrastructure here.

    Attributes:
        repair_order_id: UUID of the repair order to sync.
        order_type: SAP order type code (e.g. corrective maintenance).
        description: Short description of the work for SAP.
        planned_start: UTC datetime when work is planned to begin.
        request_id: Correlation ID for tracing.
        requested_by: UUID of the user initiating the sync.
        plant: Optional SAP plant code.
        work_center: Optional SAP work centre.
    """

    repair_order_id: uuid.UUID
    order_type: str
    description: str
    planned_start: datetime
    request_id: str
    requested_by: uuid.UUID
    plant: str | None = field(default=None)
    work_center: str | None = field(default=None)


DEFAULT_REPAIR_PART_UOM = "-"


@dataclass(frozen=True)
class AddRepairPartDTO:
    """Input DTO for recording a spare part consumed during a repair.

    Attributes:
        repair_order_id: UUID of the target repair order (must be mutable).
        material_number: SAP material number for the part.
        quantity: Positive integer quantity consumed for this part.
        request_id: Correlation ID for tracing.
        unit_of_measure: Internal persistence default; not collected from clients.
    """

    repair_order_id: uuid.UUID
    material_number: str
    quantity: int
    request_id: str
    unit_of_measure: str = DEFAULT_REPAIR_PART_UOM


@dataclass(frozen=True)
class RepairActivityResponseDTO:
    """Output DTO for a single repair activity."""

    id: uuid.UUID
    description: str
    labor_hours: Decimal
    performed_by_id: uuid.UUID
    performed_at: datetime
    notes: str | None = field(default=None)


@dataclass(frozen=True)
class RepairPartResponseDTO:
    """Output DTO for a single repair part record."""

    id: uuid.UUID
    material_number: str
    quantity: int
    unit_of_measure: str
    goods_issue_id: uuid.UUID | None = field(default=None)
    posted_at: datetime | None = field(default=None)


@dataclass(frozen=True)
class ApproveRepairOrderDTO:
    """Input DTO for transport-supervisor repair approval.

    Attributes:
        repair_order_id: UUID of the repair order to approve.
        request_id: Correlation ID for tracing.
        approved_by: UUID of the supervisor/admin approving the order.
        note: Optional transport approval note.
    """

    repair_order_id: uuid.UUID
    request_id: str
    approved_by: uuid.UUID
    note: str = ""


@dataclass(frozen=True)
class WorkshopTechnicalDecisionDTO:
    """Input DTO for central-workshop repairable / no-repair-needed decision.

    Attributes:
        estimated_delivery_at: Estimated vehicle delivery date/time, required
            when ``repairable`` is True.
    """

    repair_order_id: uuid.UUID
    repairable: bool
    request_id: str
    decided_by: uuid.UUID
    note: str = ""
    estimated_delivery_at: datetime | None = field(default=None)


@dataclass(frozen=True)
class RejectRepairOrderByTransportDTO:
    """Input DTO for initial transport rejection of a repair request."""

    repair_order_id: uuid.UUID
    reason: str
    request_id: str
    rejected_by: uuid.UUID


@dataclass(frozen=True)
class AssignWorkshopDTO:
    """Input DTO for selecting internal/external workshop after approval.

    Attributes:
        repair_order_id: UUID of the approved repair order.
        workshop_type: ``INTERNAL`` or ``EXTERNAL``.
        request_id: Correlation ID for tracing.
        assigned_by: UUID of the supervisor/admin selecting the workshop.
    """

    repair_order_id: uuid.UUID
    workshop_type: WorkshopType
    request_id: str
    assigned_by: uuid.UUID
    workshop_id: str | None = field(default=None)
    reason: str = ""


@dataclass(frozen=True)
class RepairDecisionResponseDTO:
    """Compact response for transport approval / workshop assignment actions.

    Attributes:
        id: Repair order UUID.
        status: Resulting lifecycle status.
        message: Human-readable confirmation message (Persian for demo UX).
        workshop_type: Selected workshop type when applicable.
    """

    id: uuid.UUID
    status: RepairOrderStatus
    message: str
    workshop_type: WorkshopType | None = field(default=None)
    workshop_id: str | None = field(default=None)
    external_referral_request_id: uuid.UUID | None = field(default=None)
    transport_rejection_reason: str | None = field(default=None)
    estimated_delivery_at: datetime | None = field(default=None)


@dataclass(frozen=True)
class RepairOrderResponseDTO:
    """Output DTO returned by all repair order read and write operations.

    Contains only primitive types safe to serialise directly to JSON.
    """

    id: uuid.UUID
    vehicle_id: uuid.UUID
    fault_id: uuid.UUID
    status: RepairOrderStatus
    created_by_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    activities: list[RepairActivityResponseDTO] = field(default_factory=list)
    parts: list[RepairPartResponseDTO] = field(default_factory=list)
    technician_id: uuid.UUID | None = field(default=None)
    assigned_at: datetime | None = field(default=None)
    sap_order_number: str | None = field(default=None)
    workshop_type: WorkshopType | None = field(default=None)
    workshop_id: str | None = field(default=None)
    transport_rejection_reason: str | None = field(default=None)
    transport_approval_note: str | None = field(default=None)
    workshop_decision_note: str | None = field(default=None)
    completed_at: datetime | None = field(default=None)
    estimated_delivery_at: datetime | None = field(default=None)


@dataclass(frozen=True)
class TransportHandoverApproveDTO:
    """Input DTO for transport post-handover approval."""

    repair_order_id: uuid.UUID
    request_id: str
    approved_by: uuid.UUID


@dataclass(frozen=True)
class TransportHandoverRejectDTO:
    """Input DTO for transport post-handover rejection."""

    repair_order_id: uuid.UUID
    request_id: str
    rejected_by: uuid.UUID
    comment: str | None = field(default=None)


@dataclass(frozen=True)
class RepairOrderTimelineEventDTO:
    """One repair-order workflow event for timeline APIs."""

    event: str
    description: str
    created_at: datetime
    created_by_id: uuid.UUID | None = field(default=None)


@dataclass(frozen=True)
class UploadExternalInvoiceDTO:
    """Input DTO for uploading an external repair invoice."""

    repair_order_id: uuid.UUID
    amount: Decimal
    currency: str
    request_id: str
    uploaded_by: uuid.UUID
    vendor_id: str | None = field(default=None)
    document: str | None = field(default=None)


@dataclass(frozen=True)
class ApproveExternalInvoiceDTO:
    """Input DTO for approving an external repair invoice."""

    invoice_id: uuid.UUID
    request_id: str
    approved_by: uuid.UUID


@dataclass(frozen=True)
class ExternalInvoiceResponseDTO:
    """Output DTO for external repair invoice APIs."""

    id: uuid.UUID
    repair_order_id: uuid.UUID
    amount: Decimal
    currency: str
    status: ExternalRepairInvoiceStatus
    created_by_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    vendor_id: str | None = field(default=None)
    document: str | None = field(default=None)


@dataclass(frozen=True)
class ExternalWorkshopReferralResponseDTO:
    """Output DTO for external-workshop referral permission requests."""

    id: uuid.UUID
    repair_order_id: uuid.UUID
    vehicle_id: uuid.UUID
    fault_id: uuid.UUID
    status: ExternalWorkshopReferralStatus
    requested_by_id: uuid.UUID
    requested_at: datetime
    created_at: datetime
    updated_at: datetime
    workshop_id: str | None = field(default=None)
    reason: str = ""
    approved_by_id: uuid.UUID | None = field(default=None)
    approved_at: datetime | None = field(default=None)
    rejected_by_id: uuid.UUID | None = field(default=None)
    rejected_at: datetime | None = field(default=None)
    rejection_reason: str | None = field(default=None)


@dataclass(frozen=True)
class AssignExternalWorkshopDTO:
    """Input for assigning a repair order to an external workshop."""

    repair_order_id: uuid.UUID
    workshop_name: str
    workshop_address: str
    assignment_date: datetime
    repair_reason: str
    description: str
    request_id: str
    assigned_by: uuid.UUID
    workshop_id: str | None = field(default=None)


@dataclass(frozen=True)
class ConfirmExternalWorkshopDeliveryDTO:
    """Input for driver delivery confirmation."""

    assignment_id: uuid.UUID
    delivery_datetime: datetime
    workshop_name: str
    workshop_address: str
    workshop_phone: str
    vehicle_odometer: int
    notes: str
    request_id: str
    delivered_by: uuid.UUID


@dataclass(frozen=True)
class ConfirmExternalWorkshopPickupDTO:
    """Input for driver pickup confirmation."""

    assignment_id: uuid.UUID
    pickup_datetime: datetime
    vehicle_odometer: int
    notes: str
    request_id: str
    picked_up_by: uuid.UUID


@dataclass(frozen=True)
class ReviewExternalRepairDTO:
    """Input for draft/completed transportation review save."""

    assignment_id: uuid.UUID
    invoice_attachment: str | None
    repair_services: list[dict[str, object]]
    replaced_parts: list[dict[str, object]]
    repair_cost: Decimal | None
    additional_notes: str
    request_id: str
    reviewed_by: uuid.UUID


@dataclass(frozen=True)
class CloseExternalRepairDTO:
    """Input for closing the external repair workflow."""

    assignment_id: uuid.UUID
    request_id: str
    closed_by: uuid.UUID


@dataclass(frozen=True)
class CancelExternalWorkshopAssignmentDTO:
    """Input for cancelling an external workshop assignment."""

    assignment_id: uuid.UUID
    reason: ExternalWorkshopAssignmentCancellationReason
    request_id: str
    cancelled_by: uuid.UUID
    note: str | None = field(default=None)


@dataclass(frozen=True)
class ExternalWorkshopDeliveryResponseDTO:
    """Output for delivery confirmation."""

    id: uuid.UUID
    assignment_id: uuid.UUID
    repair_order_id: uuid.UUID
    vehicle_id: uuid.UUID
    delivery_datetime: datetime
    workshop_name: str
    workshop_address: str
    workshop_phone: str
    vehicle_odometer: int
    notes: str
    delivered_by_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class ExternalWorkshopPickupResponseDTO:
    """Output for pickup confirmation."""

    id: uuid.UUID
    assignment_id: uuid.UUID
    repair_order_id: uuid.UUID
    vehicle_id: uuid.UUID
    pickup_datetime: datetime
    vehicle_odometer: int
    notes: str
    picked_up_by_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class ExternalRepairReviewResponseDTO:
    """Output for transportation administrative review."""

    id: uuid.UUID
    assignment_id: uuid.UUID
    repair_order_id: uuid.UUID
    invoice_attachment: str | None
    repair_services: list[dict[str, object]]
    replaced_parts: list[dict[str, object]]
    repair_cost: Decimal | None
    additional_notes: str
    sap_purchase_order_number: str | None
    sap_invoice_document_number: str | None
    status: ExternalRepairReviewStatus
    reviewed_by_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class ExternalWorkshopAssignmentResponseDTO:
    """Output for external workshop assignment detail and queues."""

    id: uuid.UUID
    repair_order_id: uuid.UUID
    vehicle_id: uuid.UUID
    fault_id: uuid.UUID
    workshop_id: str | None
    workshop_name: str
    workshop_address: str
    assignment_date: datetime
    repair_reason: str
    description: str
    status: ExternalWorkshopAssignmentStatus
    assigned_by_id: uuid.UUID
    cancellation_reason: ExternalWorkshopAssignmentCancellationReason | None
    cancellation_note: str | None
    cancelled_by_id: uuid.UUID | None
    cancelled_at: datetime | None
    created_at: datetime
    updated_at: datetime
    delivery: ExternalWorkshopDeliveryResponseDTO | None = field(default=None)
    pickup: ExternalWorkshopPickupResponseDTO | None = field(default=None)
    review: ExternalRepairReviewResponseDTO | None = field(default=None)
