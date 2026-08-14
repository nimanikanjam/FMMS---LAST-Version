"""Model shim — re-exports ORM models for Django auto-discovery."""

from apps.inspection.infrastructure.models import (
    InspectionDefectOptionModel,
    InspectionItemModel,
    InspectionModel,
    InspectionTemplateModel,
)

__all__ = [
    "InspectionModel",
    "InspectionItemModel",
    "InspectionTemplateModel",
    "InspectionDefectOptionModel",
]
