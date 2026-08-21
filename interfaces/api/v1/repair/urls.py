"""Repair URL routes."""

from rest_framework.routers import DefaultRouter

from interfaces.api.v1.repair.activity_option_views import RepairActivityOptionViewSet
from interfaces.api.v1.repair.external_invoice_views import ExternalInvoiceViewSet
from interfaces.api.v1.repair.views import (
    ExternalWorkshopAssignmentViewSet,
    ExternalWorkshopReferralViewSet,
    RepairOrderViewSet,
)

router = DefaultRouter()
router.register("repair-orders", RepairOrderViewSet, basename="repair-order")
router.register(
    "repair-activity-options",
    RepairActivityOptionViewSet,
    basename="repair-activity-option",
)
router.register(
    "external-invoices", ExternalInvoiceViewSet, basename="external-invoice"
)
router.register(
    "external-workshop-referrals",
    ExternalWorkshopReferralViewSet,
    basename="external-workshop-referral",
)
router.register(
    "external-workshop-assignments",
    ExternalWorkshopAssignmentViewSet,
    basename="external-workshop-assignment",
)

urlpatterns = router.urls
