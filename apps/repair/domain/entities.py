"""Domain entities for the Repair bounded context.

Vehicle and Fault are referenced by UUID only — no cross-domain imports.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from apps.repair.domain.exceptions import (
    RepairActivityNotFoundError,
    RepairOrderInvalidStateError,
    RepairOrderInvalidStateTransitionError,
)
from apps.repair.domain.value_objects import (
    LaborHours,
    PartQuantity,
    TechnicianAssignment,
)


class RepairOrderStatus(StrEnum):
    """Lifecycle states of a repair order.

    Attributes:
        CREATED: Order has been created and awaits transport approval or assignment.
        APPROVED: Transport supervisor approved continuing the repair process.
        WORKSHOP_ASSIGNED: Workshop type (internal/external) has been selected.
        ASSIGNED: A technician has been assigned.
        IN_PROGRESS: Active repair work is underway.
        COMPLETED: All repair activities are done; order is closed successfully.
        CANCELLED: Order was cancelled before completion.
    """

    CREATED = "CREATED"
    APPROVED = "APPROVED"
    WORKSHOP_ASSIGNED = "WORKSHOP_ASSIGNED"
    WAITING_EXTERNAL_REFERRAL_APPROVAL = "WAITING_EXTERNAL_REFERRAL_APPROVAL"
    WAITING_EXTERNAL_DELIVERY = "WAITING_EXTERNAL_DELIVERY"
    EXTERNAL_REPAIR_IN_PROGRESS = "EXTERNAL_REPAIR_IN_PROGRESS"
    WAITING_EXTERNAL_PICKUP = "WAITING_EXTERNAL_PICKUP"
    WAITING_EXTERNAL_ADMIN_REVIEW = "WAITING_EXTERNAL_ADMIN_REVIEW"
    WAITING_WORKSHOP_CONFIRMATION = "WAITING_WORKSHOP_CONFIRMATION"
    WAITING_PARTS = "WAITING_PARTS"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_DRIVER_CONFIRMATION = "WAITING_DRIVER_CONFIRMATION"
    WAITING_TRANSPORT_FINAL_APPROVAL = "WAITING_TRANSPORT_FINAL_APPROVAL"
    ACCEPTED_BY_DRIVER = "ACCEPTED_BY_DRIVER"
    REJECTED_BY_DRIVER = "REJECTED_BY_DRIVER"
    REJECTED_BY_TRANSPORT = "REJECTED_BY_TRANSPORT"
    NO_REPAIR_NEEDED = "NO_REPAIR_NEEDED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class WorkshopType(StrEnum):
    """Where the repair work will be performed.

    Attributes:
        INTERNAL: Repair handled by the fleet's own workshop.
        EXTERNAL: Repair outsourced to an external workshop.
    """

    INTERNAL = "INTERNAL"
    EXTERNAL = "EXTERNAL"


_ALLOWED_TRANSITIONS: dict[RepairOrderStatus, frozenset[RepairOrderStatus]] = {
    RepairOrderStatus.CREATED: frozenset(
        {
            RepairOrderStatus.APPROVED,
            RepairOrderStatus.ASSIGNED,
            RepairOrderStatus.CANCELLED,
        }
    ),
    RepairOrderStatus.APPROVED: frozenset(
        {
            RepairOrderStatus.WORKSHOP_ASSIGNED,
            RepairOrderStatus.WAITING_EXTERNAL_REFERRAL_APPROVAL,
            RepairOrderStatus.WAITING_EXTERNAL_DELIVERY,
            RepairOrderStatus.CANCELLED,
        }
    ),
    RepairOrderStatus.WAITING_EXTERNAL_REFERRAL_APPROVAL: frozenset(
        {
            RepairOrderStatus.WAITING_DRIVER_CONFIRMATION,
            RepairOrderStatus.WAITING_EXTERNAL_DELIVERY,
            RepairOrderStatus.CANCELLED,
        }
    ),
    RepairOrderStatus.WAITING_EXTERNAL_DELIVERY: frozenset(
        {
            RepairOrderStatus.EXTERNAL_REPAIR_IN_PROGRESS,
            RepairOrderStatus.WAITING_EXTERNAL_DELIVERY,
            RepairOrderStatus.CANCELLED,
        }
    ),
    RepairOrderStatus.EXTERNAL_REPAIR_IN_PROGRESS: frozenset(
        {
            RepairOrderStatus.WAITING_EXTERNAL_PICKUP,
            RepairOrderStatus.CANCELLED,
        }
    ),
    RepairOrderStatus.WAITING_EXTERNAL_PICKUP: frozenset(
        {
            RepairOrderStatus.WAITING_EXTERNAL_ADMIN_REVIEW,
            RepairOrderStatus.CANCELLED,
        }
    ),
    RepairOrderStatus.WAITING_EXTERNAL_ADMIN_REVIEW: frozenset(
        {
            RepairOrderStatus.COMPLETED,
            RepairOrderStatus.CANCELLED,
        }
    ),
    RepairOrderStatus.WORKSHOP_ASSIGNED: frozenset(
        {
            RepairOrderStatus.ASSIGNED,
            RepairOrderStatus.WAITING_WORKSHOP_CONFIRMATION,
            RepairOrderStatus.IN_PROGRESS,
            RepairOrderStatus.NO_REPAIR_NEEDED,
            RepairOrderStatus.WAITING_DRIVER_CONFIRMATION,
            RepairOrderStatus.CANCELLED,
        }
    ),
    RepairOrderStatus.WAITING_WORKSHOP_CONFIRMATION: frozenset(
        {
            RepairOrderStatus.IN_PROGRESS,
            RepairOrderStatus.NO_REPAIR_NEEDED,
            RepairOrderStatus.CANCELLED,
        }
    ),
    RepairOrderStatus.WAITING_PARTS: frozenset(
        {RepairOrderStatus.IN_PROGRESS, RepairOrderStatus.CANCELLED}
    ),
    RepairOrderStatus.ASSIGNED: frozenset(
        {
            RepairOrderStatus.IN_PROGRESS,
            RepairOrderStatus.CREATED,
            RepairOrderStatus.CANCELLED,
        }
    ),
    RepairOrderStatus.IN_PROGRESS: frozenset(
        {
            RepairOrderStatus.COMPLETED,
            RepairOrderStatus.WAITING_PARTS,
            RepairOrderStatus.WAITING_DRIVER_CONFIRMATION,
            RepairOrderStatus.CANCELLED,
        }
    ),
    RepairOrderStatus.WAITING_DRIVER_CONFIRMATION: frozenset(
        {
            RepairOrderStatus.WAITING_TRANSPORT_FINAL_APPROVAL,
            RepairOrderStatus.ACCEPTED_BY_DRIVER,
            RepairOrderStatus.REJECTED_BY_DRIVER,
        }
    ),
    RepairOrderStatus.WAITING_TRANSPORT_FINAL_APPROVAL: frozenset(
        {RepairOrderStatus.COMPLETED, RepairOrderStatus.CANCELLED}
    ),
    RepairOrderStatus.ACCEPTED_BY_DRIVER: frozenset({RepairOrderStatus.COMPLETED}),
    RepairOrderStatus.REJECTED_BY_DRIVER: frozenset(),
    RepairOrderStatus.REJECTED_BY_TRANSPORT: frozenset(),
    RepairOrderStatus.NO_REPAIR_NEEDED: frozenset(),
    RepairOrderStatus.COMPLETED: frozenset(),
    RepairOrderStatus.CANCELLED: frozenset(),
}

_MUTABLE_STATUSES: frozenset[RepairOrderStatus] = frozenset(
    {
        RepairOrderStatus.CREATED,
        RepairOrderStatus.APPROVED,
        RepairOrderStatus.WORKSHOP_ASSIGNED,
        RepairOrderStatus.WAITING_EXTERNAL_REFERRAL_APPROVAL,
        RepairOrderStatus.WAITING_EXTERNAL_DELIVERY,
        RepairOrderStatus.EXTERNAL_REPAIR_IN_PROGRESS,
        RepairOrderStatus.WAITING_EXTERNAL_PICKUP,
        RepairOrderStatus.WAITING_EXTERNAL_ADMIN_REVIEW,
        RepairOrderStatus.WAITING_WORKSHOP_CONFIRMATION,
        RepairOrderStatus.WAITING_PARTS,
        RepairOrderStatus.ASSIGNED,
        RepairOrderStatus.IN_PROGRESS,
    }
)

_TERMINAL_STATUSES: frozenset[RepairOrderStatus] = frozenset(
    {
        RepairOrderStatus.COMPLETED,
        RepairOrderStatus.CANCELLED,
        RepairOrderStatus.REJECTED_BY_DRIVER,
        RepairOrderStatus.REJECTED_BY_TRANSPORT,
        RepairOrderStatus.NO_REPAIR_NEEDED,
    }
)


@dataclass
class RepairActivity:
    """A single work activity performed during a repair order.

    Attributes:
        id: Unique identifier for this activity.
        description: Label of the work performed — the SAP activity's
            ``CodeText`` when picked from the catalog.
        labor_hours: Hours spent on this activity.
        performed_by_id: UUID of the technician who performed the activity.
        performed_at: UTC timestamp when the activity was completed.
        notes: Optional free-text detail about this particular job.
        activity_code: SAP activity ``Code`` (``ZC_REPAIR01_CODE_CDS``).
            Blank on activities recorded before the catalog was introduced.
        activity_code_group: SAP activity ``CodeGroup``.
    """

    id: uuid.UUID
    description: str
    labor_hours: LaborHours
    performed_by_id: uuid.UUID
    performed_at: datetime
    notes: str | None = field(default=None)
    activity_code: str = field(default="")
    activity_code_group: str = field(default="")


@dataclass
class RepairPart:
    """A spare part consumed during a repair order.

    Attributes:
        id: Unique identifier for this part record.
        part_quantity: Material number, quantity, and unit of measure.
        goods_issue_id: UUID of the associated goods issue document, if posted.
        posted_at: UTC timestamp when the goods issue was posted (optional).
    """

    id: uuid.UUID
    part_quantity: PartQuantity
    goods_issue_id: uuid.UUID | None = field(default=None)
    posted_at: datetime | None = field(default=None)


@dataclass
class RepairOrder:
    """Aggregate root for the Repair bounded context.

    A repair order manages the lifecycle of repair work on a vehicle fault.
    Parts and activities can only be added while the order is in a mutable state.

    Attributes:
        id: Unique identifier for this repair order.
        vehicle_id: UUID of the vehicle being repaired (cross-domain by ID).
        fault_id: UUID of the originating fault (cross-domain by ID).
        status: Current lifecycle status.
        assignment: Current technician assignment, if any.
        activities: List of repair activities performed.
        parts: List of spare parts consumed.
        sap_order_number: SAP PM order number after SAP sync (optional).
        workshop_type: Internal or external workshop selection (optional).
        created_by_id: UUID of the user who created this order.
        created_at: UTC timestamp of creation.
        updated_at: UTC timestamp of the last update.
        completed_at: UTC timestamp of completion (optional).
    """

    id: uuid.UUID
    vehicle_id: uuid.UUID
    fault_id: uuid.UUID
    status: RepairOrderStatus
    created_by_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    assignment: TechnicianAssignment | None = field(default=None)
    activities: list[RepairActivity] = field(default_factory=list)
    parts: list[RepairPart] = field(default_factory=list)
    sap_order_number: str | None = field(default=None)
    workshop_type: WorkshopType | None = field(default=None)
    workshop_id: str | None = field(default=None)
    transport_rejection_reason: str | None = field(default=None)
    transport_approval_note: str | None = field(default=None)
    workshop_decision_note: str | None = field(default=None)
    completed_at: datetime | None = field(default=None)
    estimated_delivery_at: datetime | None = field(default=None)

    def _assert_mutable(self, operation: str) -> None:
        """Assert that the order is in a mutable state.

        Args:
            operation: Name of the operation being attempted (for error messages).

        Raises:
            RepairOrderInvalidStateError: If the order is COMPLETED or CANCELLED.
        """
        if self.status not in _MUTABLE_STATUSES:
            raise RepairOrderInvalidStateError(
                order_id=self.id,
                current_status=self.status.value,
                operation=operation,
            )

    def transition_to(self, target: RepairOrderStatus) -> None:
        """Guard and apply a status transition.

        Args:
            target: The desired new status.

        Raises:
            RepairOrderInvalidStateTransitionError: If the transition is not allowed.
        """
        allowed = _ALLOWED_TRANSITIONS.get(self.status, frozenset())
        if target not in allowed:
            raise RepairOrderInvalidStateTransitionError(
                current_status=self.status.value,
                target_status=target.value,
            )
        self.status = target

    def assign_technician(self, assignment: TechnicianAssignment) -> None:
        """Assign a technician to this repair order.

        Allowed from ``CREATED`` (legacy path) or ``WORKSHOP_ASSIGNED``
        (transport-approved demo path).

        Args:
            assignment: The ``TechnicianAssignment`` value object.

        Raises:
            RepairOrderInvalidStateError: If the order is not in a mutable state.
            RepairOrderInvalidStateTransitionError: If transition is not allowed.
        """
        self._assert_mutable("assign_technician")
        self.transition_to(RepairOrderStatus.ASSIGNED)
        self.assignment = assignment

    def approve(self, note: str | None = None) -> None:
        """Approve the repair order for continuation (transport supervisor).

        Raises:
            RepairOrderInvalidStateTransitionError: If not in CREATED status.
        """
        if note:
            self.transport_approval_note = note
        self.transition_to(RepairOrderStatus.APPROVED)

    def reject_by_transport(self, reason: str) -> None:
        """Reject the repair request during initial transport review."""
        if self.status != RepairOrderStatus.CREATED:
            raise RepairOrderInvalidStateTransitionError(
                current_status=self.status.value,
                target_status=RepairOrderStatus.REJECTED_BY_TRANSPORT.value,
            )
        self.status = RepairOrderStatus.REJECTED_BY_TRANSPORT
        self.transport_rejection_reason = reason

    def assign_workshop(
        self, workshop_type: WorkshopType, workshop_id: str | None = None
    ) -> None:
        """Select internal or external workshop after transport approval.

        Args:
            workshop_type: ``INTERNAL`` or ``EXTERNAL``.

        Raises:
            RepairOrderInvalidStateTransitionError: If not in APPROVED status
                or a workshop was already assigned.
        """
        if self.status != RepairOrderStatus.APPROVED:
            raise RepairOrderInvalidStateTransitionError(
                current_status=self.status.value,
                target_status=(
                    RepairOrderStatus.WAITING_EXTERNAL_REFERRAL_APPROVAL.value
                    if workshop_type == WorkshopType.EXTERNAL
                    else RepairOrderStatus.WORKSHOP_ASSIGNED.value
                ),
            )
        if self.workshop_type is not None:
            raise RepairOrderInvalidStateTransitionError(
                current_status=self.status.value,
                target_status=(
                    RepairOrderStatus.WAITING_EXTERNAL_REFERRAL_APPROVAL.value
                    if workshop_type == WorkshopType.EXTERNAL
                    else RepairOrderStatus.WORKSHOP_ASSIGNED.value
                ),
            )
        self.workshop_type = workshop_type
        self.workshop_id = workshop_id
        if workshop_type == WorkshopType.EXTERNAL:
            self.transition_to(RepairOrderStatus.WAITING_EXTERNAL_REFERRAL_APPROVAL)
            return
        self.transition_to(RepairOrderStatus.WORKSHOP_ASSIGNED)

    def assign_external_workshop(self, workshop_id: str | None = None) -> None:
        """Assign an external workshop and wait for driver delivery."""
        if self.status not in {
            RepairOrderStatus.APPROVED,
            RepairOrderStatus.WAITING_EXTERNAL_DELIVERY,
        }:
            raise RepairOrderInvalidStateTransitionError(
                current_status=self.status.value,
                target_status=RepairOrderStatus.WAITING_EXTERNAL_DELIVERY.value,
            )
        self.workshop_type = WorkshopType.EXTERNAL
        self.workshop_id = workshop_id
        self.transition_to(RepairOrderStatus.WAITING_EXTERNAL_DELIVERY)

    def confirm_external_delivery(self) -> None:
        """Move external repair to in-progress immediately after delivery."""
        if self.workshop_type != WorkshopType.EXTERNAL:
            raise RepairOrderInvalidStateTransitionError(
                current_status=self.status.value,
                target_status=RepairOrderStatus.EXTERNAL_REPAIR_IN_PROGRESS.value,
            )
        self.transition_to(RepairOrderStatus.EXTERNAL_REPAIR_IN_PROGRESS)

    def wait_for_external_pickup(self) -> None:
        """Mark external repair ready for driver pickup."""
        if self.workshop_type != WorkshopType.EXTERNAL:
            raise RepairOrderInvalidStateTransitionError(
                current_status=self.status.value,
                target_status=RepairOrderStatus.WAITING_EXTERNAL_PICKUP.value,
            )
        self.transition_to(RepairOrderStatus.WAITING_EXTERNAL_PICKUP)

    def confirm_external_pickup(self) -> None:
        """Move external repair to transport administrative review."""
        if self.workshop_type != WorkshopType.EXTERNAL:
            raise RepairOrderInvalidStateTransitionError(
                current_status=self.status.value,
                target_status=RepairOrderStatus.WAITING_EXTERNAL_ADMIN_REVIEW.value,
            )
        if self.status == RepairOrderStatus.EXTERNAL_REPAIR_IN_PROGRESS:
            self.wait_for_external_pickup()
        self.transition_to(RepairOrderStatus.WAITING_EXTERNAL_ADMIN_REVIEW)

    def close_external_repair(self, completed_at: datetime) -> None:
        """Close an externally repaired order after administrative review."""
        if self.workshop_type != WorkshopType.EXTERNAL:
            raise RepairOrderInvalidStateTransitionError(
                current_status=self.status.value,
                target_status=RepairOrderStatus.COMPLETED.value,
            )
        self.transition_to(RepairOrderStatus.COMPLETED)
        self.completed_at = completed_at

    def accept_internal_workshop(self) -> None:
        """Accept an internally assigned workshop before work starts."""
        if self.workshop_type != WorkshopType.INTERNAL:
            raise RepairOrderInvalidStateTransitionError(
                current_status=self.status.value,
                target_status=RepairOrderStatus.WAITING_WORKSHOP_CONFIRMATION.value,
            )
        self.transition_to(RepairOrderStatus.WAITING_WORKSHOP_CONFIRMATION)

    def mark_repairable(
        self,
        note: str | None = None,
        estimated_delivery_at: datetime | None = None,
    ) -> None:
        """Workshop confirms the vehicle needs repair (before PM Order / start)."""
        if self.workshop_type != WorkshopType.INTERNAL:
            raise RepairOrderInvalidStateTransitionError(
                current_status=self.status.value,
                target_status=RepairOrderStatus.IN_PROGRESS.value,
            )
        if self.status not in (
            RepairOrderStatus.WORKSHOP_ASSIGNED,
            RepairOrderStatus.WAITING_WORKSHOP_CONFIRMATION,
        ):
            raise RepairOrderInvalidStateTransitionError(
                current_status=self.status.value,
                target_status=RepairOrderStatus.IN_PROGRESS.value,
            )
        if note:
            self.workshop_decision_note = note
        self.estimated_delivery_at = estimated_delivery_at
        self.transition_to(RepairOrderStatus.IN_PROGRESS)

    def mark_no_repair_needed(self, note: str | None = None) -> None:
        """Workshop decides the vehicle does not need repair (عدم نیاز به تعمیر)."""
        if self.workshop_type != WorkshopType.INTERNAL:
            raise RepairOrderInvalidStateTransitionError(
                current_status=self.status.value,
                target_status=RepairOrderStatus.NO_REPAIR_NEEDED.value,
            )
        if self.status not in (
            RepairOrderStatus.WORKSHOP_ASSIGNED,
            RepairOrderStatus.WAITING_WORKSHOP_CONFIRMATION,
        ):
            raise RepairOrderInvalidStateTransitionError(
                current_status=self.status.value,
                target_status=RepairOrderStatus.NO_REPAIR_NEEDED.value,
            )
        if note:
            self.workshop_decision_note = note
        self.transition_to(RepairOrderStatus.NO_REPAIR_NEEDED)

    def start_work(self) -> None:
        """Mark the repair order as actively in progress.

        Allowed from ``ASSIGNED`` (technician assigned) or ``WORKSHOP_ASSIGNED``
        (simplified demo path without explicit technician assignment).

        Raises:
            RepairOrderInvalidStateTransitionError: If not in a startable state.
        """
        if self.workshop_type == WorkshopType.EXTERNAL:
            raise RepairOrderInvalidStateTransitionError(
                current_status=self.status.value,
                target_status=RepairOrderStatus.IN_PROGRESS.value,
            )
        if self.status not in (
            RepairOrderStatus.ASSIGNED,
            RepairOrderStatus.WORKSHOP_ASSIGNED,
            RepairOrderStatus.WAITING_WORKSHOP_CONFIRMATION,
        ):
            raise RepairOrderInvalidStateTransitionError(
                current_status=self.status.value,
                target_status=RepairOrderStatus.IN_PROGRESS.value,
            )
        self.transition_to(RepairOrderStatus.IN_PROGRESS)

    def complete(self, completed_at: datetime) -> None:
        """Mark the repair order as completed.

        Args:
            completed_at: UTC timestamp of completion.

        Raises:
            RepairOrderInvalidStateTransitionError: If not IN_PROGRESS.
        """
        self.transition_to(RepairOrderStatus.COMPLETED)
        self.completed_at = completed_at

    def complete_waiting_driver_confirmation(self, completed_at: datetime) -> None:
        """Mark technical work complete and wait for driver handover decision."""
        if (
            self.status == RepairOrderStatus.WORKSHOP_ASSIGNED
            and self.workshop_type != WorkshopType.EXTERNAL
        ):
            raise RepairOrderInvalidStateTransitionError(
                current_status=self.status.value,
                target_status=RepairOrderStatus.WAITING_DRIVER_CONFIRMATION.value,
            )
        self.transition_to(RepairOrderStatus.WAITING_DRIVER_CONFIRMATION)
        self.completed_at = completed_at

    def wait_for_parts(self) -> None:
        """Pause repair while waiting for parts."""
        self.transition_to(RepairOrderStatus.WAITING_PARTS)

    def resume_after_parts(self) -> None:
        """Resume repair after parts are available."""
        self.transition_to(RepairOrderStatus.IN_PROGRESS)

    def confirm_handover(self, accepted: bool) -> None:
        """Apply driver handover decision."""
        if accepted:
            self.transition_to(RepairOrderStatus.WAITING_TRANSPORT_FINAL_APPROVAL)
            return
        self.transition_to(RepairOrderStatus.REJECTED_BY_DRIVER)

    def complete_after_transport_handover(self, completed_at: datetime) -> None:
        """Finalize a driver-accepted repair order after transport validation.

        Args:
            completed_at: UTC timestamp when transport approved completion.

        Raises:
            RepairOrderInvalidStateTransitionError: If not waiting for transport.
        """
        self.transition_to(RepairOrderStatus.COMPLETED)
        self.completed_at = completed_at

    def cancel(self) -> None:
        """Cancel the repair order.

        Raises:
            RepairOrderInvalidStateTransitionError: If already COMPLETED or CANCELLED.
        """
        self.transition_to(RepairOrderStatus.CANCELLED)

    def add_activity(self, activity: RepairActivity) -> None:
        """Add a repair activity to this order.

        Args:
            activity: The ``RepairActivity`` to add.

        Raises:
            RepairOrderInvalidStateError: If the order is not in a mutable state.
        """
        self._assert_mutable("add_activity")
        self.activities.append(activity)

    def update_activity(
        self,
        activity_id: uuid.UUID,
        *,
        description: str,
        labor_hours: LaborHours,
        notes: str | None,
        activity_code: str = "",
        activity_code_group: str = "",
    ) -> None:
        """Update an existing repair activity on a mutable order."""
        self._assert_mutable("update_activity")
        for activity in self.activities:
            if activity.id == activity_id:
                activity.description = description
                activity.labor_hours = labor_hours
                activity.notes = notes
                activity.activity_code = activity_code
                activity.activity_code_group = activity_code_group
                return
        raise RepairActivityNotFoundError(activity_id)

    def delete_activity(self, activity_id: uuid.UUID) -> None:
        """Remove an existing repair activity from a mutable order."""
        self._assert_mutable("delete_activity")
        next_activities = [
            activity for activity in self.activities if activity.id != activity_id
        ]
        if len(next_activities) == len(self.activities):
            raise RepairActivityNotFoundError(activity_id)
        self.activities = next_activities

    def add_part(self, part: RepairPart) -> None:
        """Add a spare part consumption record to this order.

        Args:
            part: The ``RepairPart`` to add.

        Raises:
            RepairOrderInvalidStateError: If the order is not in a mutable state.
        """
        self._assert_mutable("add_part")
        self.parts.append(part)

    def link_sap_order(self, sap_order_number: str) -> None:
        """Record the SAP PM order number after successful SAP sync.

        Args:
            sap_order_number: The SAP-assigned order number.
        """
        self.sap_order_number = sap_order_number

    @property
    def total_labor_hours(self) -> Decimal:
        """Sum of all labor hours across repair activities."""
        return sum((a.labor_hours.hours for a in self.activities), Decimal("0"))

    @property
    def is_active(self) -> bool:
        """Return True if the repair order is not in a terminal status."""
        return self.status not in _TERMINAL_STATUSES


class RepairOrderEventType(StrEnum):
    """Canonical repair-order lifecycle events recorded for audit/timeline."""

    FAULT_CREATED = "FAULT_CREATED"
    DISTRIBUTION_APPROVED = "DISTRIBUTION_APPROVED"
    DISTRIBUTION_APPROVED_USABLE = "DISTRIBUTION_APPROVED_USABLE"
    TRANSPORT_APPROVED = "TRANSPORT_APPROVED"
    TRANSPORT_REJECTED = "TRANSPORT_REJECTED"
    WORKSHOP_ASSIGNED = "WORKSHOP_ASSIGNED"
    EXTERNAL_REFERRAL_REQUESTED = "EXTERNAL_REFERRAL_REQUESTED"
    EXTERNAL_REFERRAL_APPROVED = "EXTERNAL_REFERRAL_APPROVED"
    EXTERNAL_REFERRAL_REJECTED = "EXTERNAL_REFERRAL_REJECTED"
    EXTERNAL_WORKSHOP_ASSIGNED = "EXTERNAL_WORKSHOP_ASSIGNED"
    EXTERNAL_WORKSHOP_ASSIGNMENT_CANCELLED = "EXTERNAL_WORKSHOP_ASSIGNMENT_CANCELLED"
    EXTERNAL_VEHICLE_DELIVERED = "EXTERNAL_VEHICLE_DELIVERED"
    EXTERNAL_REPAIR_IN_PROGRESS = "EXTERNAL_REPAIR_IN_PROGRESS"
    EXTERNAL_VEHICLE_PICKED_UP = "EXTERNAL_VEHICLE_PICKED_UP"
    EXTERNAL_ADMIN_REVIEW_SAVED = "EXTERNAL_ADMIN_REVIEW_SAVED"
    EXTERNAL_REPAIR_CLOSED = "EXTERNAL_REPAIR_CLOSED"
    TECHNICIAN_ACCEPTED = "TECHNICIAN_ACCEPTED"
    TECHNICIAN_REJECTED = "TECHNICIAN_REJECTED"
    REPAIR_REJECTED = "REPAIR_REJECTED"
    REPAIRABLE_CONFIRMED = "REPAIRABLE_CONFIRMED"
    NO_REPAIR_NEEDED = "NO_REPAIR_NEEDED"
    MATERIAL_REQUESTED = "MATERIAL_REQUESTED"
    MATERIAL_APPROVED = "MATERIAL_APPROVED"
    MATERIAL_REJECTED = "MATERIAL_REJECTED"
    MATERIAL_WAITING_STOCK = "MATERIAL_WAITING_STOCK"
    STOCK_ISSUED = "STOCK_ISSUED"
    PURCHASE_REQUIRED = "PURCHASE_REQUIRED"
    PART_RECEIVED = "PART_RECEIVED"
    PARTS_RECEIVED = "PARTS_RECEIVED"
    REPAIR_STARTED = "REPAIR_STARTED"
    REPAIR_COMPLETED = "REPAIR_COMPLETED"
    WAITING_DRIVER_CONFIRMATION = "WAITING_DRIVER_CONFIRMATION"
    WAITING_TRANSPORT_FINAL_APPROVAL = "WAITING_TRANSPORT_FINAL_APPROVAL"
    DRIVER_ACCEPTED = "DRIVER_ACCEPTED"
    DRIVER_REJECTED = "DRIVER_REJECTED"
    TRANSPORT_HANDOVER_APPROVED = "TRANSPORT_HANDOVER_APPROVED"
    TRANSPORT_HANDOVER_REJECTED = "TRANSPORT_HANDOVER_REJECTED"
    INVOICE_UPLOADED = "INVOICE_UPLOADED"
    INVOICE_APPROVED = "INVOICE_APPROVED"
    EXTERNAL_INVOICE_UPLOADED = "EXTERNAL_INVOICE_UPLOADED"
    EXTERNAL_INVOICE_APPROVED = "EXTERNAL_INVOICE_APPROVED"


@dataclass(frozen=True)
class RepairOrderEvent:
    """Immutable repair-order lifecycle event.

    Attributes:
        id: Event UUID.
        repair_order_id: Parent repair order.
        event_type: Canonical event code.
        description: Human-readable Persian/English description.
        created_at: UTC timestamp when the event occurred.
        created_by_id: Optional actor UUID.
    """

    id: uuid.UUID
    repair_order_id: uuid.UUID
    event_type: RepairOrderEventType
    description: str
    created_at: datetime
    created_by_id: uuid.UUID | None = None


class ExternalWorkshopReferralStatus(StrEnum):
    """Lifecycle states for external-workshop referral permission requests."""

    REQUESTED = "REQUESTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


_EXTERNAL_REFERRAL_ALLOWED_TRANSITIONS: dict[
    ExternalWorkshopReferralStatus, frozenset[ExternalWorkshopReferralStatus]
] = {
    ExternalWorkshopReferralStatus.REQUESTED: frozenset(
        {
            ExternalWorkshopReferralStatus.APPROVED,
            ExternalWorkshopReferralStatus.REJECTED,
            ExternalWorkshopReferralStatus.CANCELLED,
        }
    ),
    ExternalWorkshopReferralStatus.APPROVED: frozenset(),
    ExternalWorkshopReferralStatus.REJECTED: frozenset(),
    ExternalWorkshopReferralStatus.CANCELLED: frozenset(),
}


@dataclass
class ExternalWorkshopReferralRequest:
    """Permission request for sending a repair order to an external workshop."""

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

    def transition_to(self, target: ExternalWorkshopReferralStatus) -> None:
        """Transition the referral request to a permitted target status."""
        allowed = _EXTERNAL_REFERRAL_ALLOWED_TRANSITIONS.get(self.status, frozenset())
        if target not in allowed:
            raise RepairOrderInvalidStateTransitionError(
                current_status=self.status.value,
                target_status=target.value,
            )
        self.status = target

    def approve(self, approved_by_id: uuid.UUID, approved_at: datetime) -> None:
        """Approve external workshop referral permission."""
        self.transition_to(ExternalWorkshopReferralStatus.APPROVED)
        self.approved_by_id = approved_by_id
        self.approved_at = approved_at

    def reject(
        self,
        rejected_by_id: uuid.UUID,
        rejected_at: datetime,
        reason: str,
    ) -> None:
        """Reject external workshop referral permission."""
        self.transition_to(ExternalWorkshopReferralStatus.REJECTED)
        self.rejected_by_id = rejected_by_id
        self.rejected_at = rejected_at
        self.rejection_reason = reason
