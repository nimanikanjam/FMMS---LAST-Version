"""Read-only services for retrieving fault data.

No mutations happen here. These services are query-side only.
"""

from __future__ import annotations

import uuid

from apps.authentication.application.ports.user_profile_reader import IUserProfileReader
from apps.fault.application.dto.fault_dto import FaultResponseDTO
from apps.fault.application.services.report_fault_service import _to_response_dto
from apps.fault.domain.entities import FaultStatus
from apps.fault.domain.interfaces.fault_repository import IFaultRepository
from apps.fault.domain.value_objects import FaultSeverity
from core.exceptions.translation import load_or_not_found
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("fault", __name__)


class GetFaultService:
    """Fetch a single fault by its UUID.

    Args:
        fault_repository: Concrete ``IFaultRepository``.
        profile_reader: Optional user profile resolver for ``created_by``.
    """

    def __init__(
        self,
        fault_repository: IFaultRepository,
        profile_reader: IUserProfileReader | None = None,
    ) -> None:
        self._repo = fault_repository
        self._profile_reader = profile_reader

    def execute(self, fault_id: uuid.UUID, request_id: str = "") -> FaultResponseDTO:
        """Return the fault identified by ``fault_id``.

        Args:
            fault_id: Target fault UUID.
            request_id: Optional correlation ID for structured logging.

        Returns:
            ``FaultResponseDTO`` for the requested fault.

        Raises:
            FMMSNotFoundError: If no fault with ``fault_id`` exists.
        """
        logger.info(
            "Fetching fault",
            extra={
                "domain": "fault",
                "service": "GetFaultService",
                "operation": "execute",
                "request_id": request_id,
                "entity_id": str(fault_id),
            },
        )

        fault = load_or_not_found(
            lambda: self._repo.get_by_id(fault_id),
            message=f"Fault '{fault_id}' not found.",
            details={"fault_id": str(fault_id)},
        )

        logger.info(
            "Fault fetched",
            extra={
                "domain": "fault",
                "service": "GetFaultService",
                "operation": "execute",
                "request_id": request_id,
                "entity_id": str(fault_id),
                "result": "success",
            },
        )

        return _to_response_dto(fault, self._profile_reader)


class ListFaultsService:
    """Fetch faults, optionally filtered by vehicle or severity.

    Args:
        fault_repository: Concrete ``IFaultRepository``.
        profile_reader: Optional user profile resolver for ``created_by``.
    """

    def __init__(
        self,
        fault_repository: IFaultRepository,
        profile_reader: IUserProfileReader | None = None,
    ) -> None:
        self._repo = fault_repository
        self._profile_reader = profile_reader

    def execute(
        self,
        vehicle_id: uuid.UUID | None = None,
        status: FaultStatus | None = None,
        open_by_severity: FaultSeverity | None = None,
        request_id: str = "",
    ) -> list[FaultResponseDTO]:
        """Return faults filtered by vehicle or open-by-severity.

        When ``vehicle_id`` is provided: returns all faults for that vehicle.
        When ``open_by_severity`` is provided: returns open faults at that level.
        When both are provided: vehicle filter takes precedence.
        When neither is provided: returns an empty list (explicit filter required).

        Args:
            vehicle_id: Optional vehicle UUID filter.
            open_by_severity: Optional severity filter for OPEN faults.
            request_id: Optional correlation ID for structured logging.

        Returns:
            Ordered list of ``FaultResponseDTO`` objects.
        """
        logger.info(
            "Listing faults",
            extra={
                "domain": "fault",
                "service": "ListFaultsService",
                "operation": "execute",
                "request_id": request_id,
                "vehicle_id": str(vehicle_id) if vehicle_id else None,
                "severity_filter": open_by_severity.value if open_by_severity else None,
            },
        )

        if vehicle_id is not None:
            faults = self._repo.list_by_vehicle(vehicle_id)
        elif open_by_severity is not None:
            faults = self._repo.list_open_by_severity(open_by_severity)
        else:
            faults = self._repo.list_all(status=status)

        logger.info(
            "Faults listed",
            extra={
                "domain": "fault",
                "service": "ListFaultsService",
                "operation": "execute",
                "request_id": request_id,
                "result": "success",
                "count": len(faults),
            },
        )

        return [_to_response_dto(f, self._profile_reader) for f in faults]
