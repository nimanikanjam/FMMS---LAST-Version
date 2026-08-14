"""Domain exceptions for the Repair bounded context."""

from __future__ import annotations

from core.domain.exceptions import DomainError, DomainNotFoundError, DomainStateError


class RepairDomainError(DomainError):
    """Base class for all Repair domain exceptions."""


class RepairOrderNotFoundError(RepairDomainError, DomainNotFoundError):
    """Raised when a repair order cannot be located.

    Args:
        order_id: The identifier that was searched for.
    """

    def __init__(self, order_id: object) -> None:
        super().__init__(f"Repair order not found: '{order_id}'.")
        self.order_id = order_id


class RepairOrderInvalidStateError(RepairDomainError, DomainStateError):
    """Raised when an operation is not valid in the current repair order state.

    Args:
        order_id: The ID of the repair order.
        current_status: The current status of the repair order.
        operation: The name of the operation that was attempted.
    """

    def __init__(self, order_id: object, current_status: str, operation: str) -> None:
        super().__init__(
            f"Cannot perform '{operation}' on repair order '{order_id}' "
            f"with status '{current_status}'."
        )
        self.order_id = order_id
        self.current_status = current_status
        self.operation = operation


class RepairOrderInvalidStateTransitionError(RepairDomainError, DomainStateError):
    """Raised when a repair order status transition is not permitted.

    Args:
        current_status: The current status.
        target_status: The attempted target status.
    """

    def __init__(self, current_status: str, target_status: str) -> None:
        super().__init__(
            f"Cannot transition repair order from '{current_status}' to '{target_status}'."
        )
        self.current_status = current_status
        self.target_status = target_status


class RepairActivityNotFoundError(RepairDomainError, DomainNotFoundError):
    """Raised when a repair activity cannot be located.

    Args:
        activity_id: The identifier that was searched for.
    """

    def __init__(self, activity_id: object) -> None:
        super().__init__(f"Repair activity not found: '{activity_id}'.")
        self.activity_id = activity_id


class ExternalRepairInvoiceNotFoundError(RepairDomainError, DomainNotFoundError):
    """Raised when an external repair invoice cannot be located."""

    def __init__(self, invoice_id: object) -> None:
        super().__init__(f"External repair invoice not found: '{invoice_id}'.")
        self.invoice_id = invoice_id
