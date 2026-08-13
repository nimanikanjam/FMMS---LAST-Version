"""Django ORM models for handovers."""

from django.db import models

from infrastructure.database.model_mixins import BusinessRecordModel


class VehicleHandoverModel(BusinessRecordModel):
    """Persistence model for vehicle handover."""

    repair_order_id = models.UUIDField(db_index=True, unique=True)
    vehicle_id = models.UUIDField(db_index=True)
    driver_id = models.UUIDField(null=True, blank=True, default=None)
    status = models.CharField(max_length=40, db_index=True)
    comment = models.CharField(max_length=500, blank=True, default="")
    confirmed_at = models.DateTimeField(null=True, blank=True, default=None)

    class Meta:
        app_label = "handover"
        db_table = "vehicle_handover"
