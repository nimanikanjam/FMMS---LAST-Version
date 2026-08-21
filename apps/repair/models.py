"""Model shim — re-exports ORM models for Django auto-discovery."""

from apps.repair.infrastructure.models import (
    ExternalRepairInvoiceModel,
    ExternalRepairReviewModel,
    ExternalWorkshopAssignmentModel,
    ExternalWorkshopDeliveryModel,
    ExternalWorkshopPickupModel,
    InternalRepairCostModel,
    RepairActivityModel,
    RepairActivityOptionModel,
    RepairOrderEventModel,
    RepairOrderModel,
    RepairPartModel,
)

__all__ = [
    "RepairOrderModel",
    "RepairActivityModel",
    "RepairPartModel",
    "RepairOrderEventModel",
    "ExternalRepairInvoiceModel",
    "ExternalWorkshopAssignmentModel",
    "ExternalWorkshopDeliveryModel",
    "ExternalWorkshopPickupModel",
    "ExternalRepairReviewModel",
    "InternalRepairCostModel",
    "RepairActivityOptionModel",
]
