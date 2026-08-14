"""Inspection URL routes."""

from rest_framework.routers import DefaultRouter

from interfaces.api.v1.inspection.defect_option_views import (
    InspectionDefectOptionViewSet,
)
from interfaces.api.v1.inspection.template_views import InspectionTemplateViewSet
from interfaces.api.v1.inspection.views import InspectionViewSet

router = DefaultRouter()
router.register("inspections", InspectionViewSet, basename="inspection")
router.register(
    "inspection-templates",
    InspectionTemplateViewSet,
    basename="inspection-template",
)
router.register(
    "inspection-defect-options",
    InspectionDefectOptionViewSet,
    basename="inspection-defect-option",
)

urlpatterns = router.urls
