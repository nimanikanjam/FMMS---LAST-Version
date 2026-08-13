"""Django ORM models for the Driver bounded context."""

from __future__ import annotations

from django.db import models

from apps.driver.domain.entities import DriverStatus
from infrastructure.database.model_mixins import BusinessRecordModel


class DriverModel(BusinessRecordModel):
    """Persistence model for a SAP-sourced fleet driver.

    TODO: Select mixins for SAP master-data models once the shared audit
    model is reviewed. Drivers are never deleted by FMMS, so ``is_deleted`` is
    inherited for now but must not drive business visibility.
    """

    customer_number = models.CharField(max_length=20, db_index=True)
    name = models.CharField(max_length=200)
    mobile = models.CharField(max_length=20, blank=True, default="")
    personnel_number = models.CharField(max_length=20, blank=True, default="")
    gender = models.CharField(max_length=20, blank=True, default="")
    nilofar_code = models.CharField(max_length=20, blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=[(status.value, status.value) for status in DriverStatus],
        db_index=True,
    )

    class Meta:
        app_label = "driver"
        db_table = "driver"
        verbose_name = "Driver"
        verbose_name_plural = "Drivers"
        constraints = [
            models.UniqueConstraint(
                fields=["customer_number"],
                name="unique_driver_customer_number",
            ),
        ]
        indexes = [
            models.Index(fields=["status"], name="driver_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.customer_number})"
