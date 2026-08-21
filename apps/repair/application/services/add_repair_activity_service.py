"""Service that orchestrates adding a repair activity or part to a repair order.

The domain entity's ``add_activity()`` and ``add_part()`` enforce that only
mutable (CREATED/ASSIGNED/IN_PROGRESS) orders may receive new items.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from apps.repair.application.dto.repair_dto import (
    AddRepairActivityDTO,
    AddRepairPartDTO,
    DeleteRepairActivityDTO,
    RepairOrderResponseDTO,
    UpdateRepairActivityDTO,
)
from apps.repair.application.services.create_repair_order_service import (
    _to_response_dto,
)
from apps.repair.domain.entities import RepairActivity, RepairPart
from apps.repair.domain.exceptions import RepairActivityCodeNotInCatalogError
from apps.repair.domain.interfaces.repair_activity_option_repository import (
    IRepairActivityOptionRepository,
)
from apps.repair.domain.interfaces.repair_repository import IRepairOrderRepository
from apps.repair.domain.value_objects import LaborHours, PartQuantity
from core.exceptions.translation import load_or_not_found
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("repair", __name__)


def _resolve_catalog_label(
    option_repository: IRepairActivityOptionRepository | None,
    code: str,
    code_group: str,
    fallback: str,
) -> str:
    """Return the SAP catalog label for ``code``, or ``fallback`` if no code.

    Resolving the label server-side keeps the stored description in step with
    the SAP code, so a client cannot pair a code with a mismatched label.

    Raises:
        RepairActivityCodeNotInCatalogError: If ``code`` is not in the
            active catalog.
    """
    if not code:
        return fallback
    if option_repository is None:
        return fallback
    option = option_repository.get_by_sap_key(code, code_group)
    if option is None or not option.is_active:
        raise RepairActivityCodeNotInCatalogError(code, code_group)
    return option.code_text


class AddRepairActivityService:
    """Orchestrates addition of a repair activity to an active order.

    Args:
        repair_order_repository: Concrete ``IRepairOrderRepository``.
    """

    def __init__(
        self,
        repair_order_repository: IRepairOrderRepository,
        activity_option_repository: IRepairActivityOptionRepository | None = None,
    ) -> None:
        self._repo = repair_order_repository
        self._options = activity_option_repository

    def execute(self, dto: AddRepairActivityDTO) -> RepairOrderResponseDTO:
        """Add a repair activity to a mutable repair order.

        Args:
            dto: Activity details.

        Returns:
            ``RepairOrderResponseDTO`` updated with the new activity.

        Raises:
            FMMSNotFoundError: If no order with ``dto.repair_order_id`` exists.
            RepairOrderInvalidStateError: If the order is not mutable (entity).
        """
        logger.info(
            "Adding repair activity",
            extra={
                "domain": "repair",
                "service": "AddRepairActivityService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(dto.repair_order_id),
            },
        )

        order = load_or_not_found(
            lambda: self._repo.get_by_id(dto.repair_order_id),
            message=f"Repair order '{dto.repair_order_id}' not found.",
            details={"repair_order_id": str(dto.repair_order_id)},
        )

        activity = RepairActivity(
            id=uuid.uuid4(),
            description=_resolve_catalog_label(
                self._options,
                dto.activity_code,
                dto.activity_code_group,
                dto.description,
            ),
            labor_hours=LaborHours(hours=dto.labor_hours),
            performed_by_id=dto.performed_by_id,
            performed_at=dto.performed_at,
            notes=dto.notes,
            activity_code=dto.activity_code,
            activity_code_group=dto.activity_code_group,
        )

        order.add_activity(activity)
        order.updated_at = datetime.now(tz=UTC)
        saved = self._repo.save(order)

        logger.info(
            "Repair activity added",
            extra={
                "domain": "repair",
                "service": "AddRepairActivityService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(saved.id),
                "result": "success",
                "activity_count": len(saved.activities),
            },
        )

        return _to_response_dto(saved)


class UpdateRepairActivityService:
    """Orchestrates editing a repair activity on a mutable order."""

    def __init__(
        self,
        repair_order_repository: IRepairOrderRepository,
        activity_option_repository: IRepairActivityOptionRepository | None = None,
    ) -> None:
        self._repo = repair_order_repository
        self._options = activity_option_repository

    def execute(self, dto: UpdateRepairActivityDTO) -> RepairOrderResponseDTO:
        """Update an existing repair activity."""
        logger.info(
            "Updating repair activity",
            extra={
                "domain": "repair",
                "service": "UpdateRepairActivityService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(dto.repair_order_id),
                "activity_id": str(dto.activity_id),
            },
        )

        order = load_or_not_found(
            lambda: self._repo.get_by_id(dto.repair_order_id),
            message=f"Repair order '{dto.repair_order_id}' not found.",
            details={"repair_order_id": str(dto.repair_order_id)},
        )
        order.update_activity(
            dto.activity_id,
            description=_resolve_catalog_label(
                self._options,
                dto.activity_code,
                dto.activity_code_group,
                dto.description,
            ),
            labor_hours=LaborHours(hours=dto.labor_hours),
            notes=dto.notes,
            activity_code=dto.activity_code,
            activity_code_group=dto.activity_code_group,
        )
        order.updated_at = datetime.now(tz=UTC)
        saved = self._repo.save(order)

        logger.info(
            "Repair activity updated",
            extra={
                "domain": "repair",
                "service": "UpdateRepairActivityService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(saved.id),
                "activity_id": str(dto.activity_id),
                "result": "success",
            },
        )
        return _to_response_dto(saved)


class DeleteRepairActivityService:
    """Orchestrates deleting a repair activity from a mutable order."""

    def __init__(self, repair_order_repository: IRepairOrderRepository) -> None:
        self._repo = repair_order_repository

    def execute(self, dto: DeleteRepairActivityDTO) -> RepairOrderResponseDTO:
        """Delete an existing repair activity."""
        order = load_or_not_found(
            lambda: self._repo.get_by_id(dto.repair_order_id),
            message=f"Repair order '{dto.repair_order_id}' not found.",
            details={"repair_order_id": str(dto.repair_order_id)},
        )
        order.delete_activity(dto.activity_id)
        order.updated_at = datetime.now(tz=UTC)
        saved = self._repo.save(order)
        logger.info(
            "Repair activity deleted",
            extra={
                "domain": "repair",
                "service": "DeleteRepairActivityService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(saved.id),
                "activity_id": str(dto.activity_id),
                "result": "success",
            },
        )
        return _to_response_dto(saved)


class AddRepairPartService:
    """Orchestrates recording of a spare part consumed during a repair.

    Args:
        repair_order_repository: Concrete ``IRepairOrderRepository``.
    """

    def __init__(self, repair_order_repository: IRepairOrderRepository) -> None:
        self._repo = repair_order_repository

    def execute(self, dto: AddRepairPartDTO) -> RepairOrderResponseDTO:
        """Add a spare part record to a mutable repair order.

        Args:
            dto: Part details.

        Returns:
            ``RepairOrderResponseDTO`` updated with the new part record.

        Raises:
            FMMSNotFoundError: If no order with ``dto.repair_order_id`` exists.
            RepairOrderInvalidStateError: If the order is not mutable (entity).
        """
        logger.info(
            "Adding repair part",
            extra={
                "domain": "repair",
                "service": "AddRepairPartService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(dto.repair_order_id),
                "material_number": dto.material_number,
            },
        )

        order = load_or_not_found(
            lambda: self._repo.get_by_id(dto.repair_order_id),
            message=f"Repair order '{dto.repair_order_id}' not found.",
            details={"repair_order_id": str(dto.repair_order_id)},
        )

        part = RepairPart(
            id=uuid.uuid4(),
            part_quantity=PartQuantity(
                material_number=dto.material_number,
                quantity=dto.quantity,
                unit_of_measure=dto.unit_of_measure,
            ),
        )

        order.add_part(part)
        order.updated_at = datetime.now(tz=UTC)
        saved = self._repo.save(order)

        logger.info(
            "Repair part added",
            extra={
                "domain": "repair",
                "service": "AddRepairPartService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(saved.id),
                "result": "success",
                "part_count": len(saved.parts),
            },
        )

        return _to_response_dto(saved)
