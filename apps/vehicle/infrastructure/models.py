"""Django ORM models for the Vehicle bounded context.

These models are the persistence layer only. Business logic lives in
``apps.vehicle.domain.entities``. No domain rules are enforced here.
"""

from __future__ import annotations

from django.db import models

from apps.vehicle.domain.entities import VehicleStatus
from infrastructure.database.model_mixins import BusinessRecordModel


class VehicleModel(BusinessRecordModel):
    """Persistence model for a SAP-sourced fleet vehicle.

    Stores all vehicle attributes as flat fields. Cross-domain references
    (e.g. repair orders) are resolved at the repository or service layer —
    never through Django ForeignKey to other app models.

    Vehicles are SAP-owned master data. Composite audit fields are retained
    for consistency, but FMMS workflow visibility is controlled by ``status``;
    SAP decommissioning must not soft-delete rows.

    Attributes:
        vehicle_number: SAP ``VehicleNumber`` and unique vehicle identifier.
        license_plate: SAP ``LicensePlate``.
        commissioning_date: SAP ``CommissioningDate`` in source format.
        driver1_customer_number: SAP customer number for the main driver.
        driver2_customer_number: SAP customer number for the assistant driver.
        status: Current lifecycle status.
    """

    vehicle_number = models.CharField(max_length=18, db_index=True)
    license_plate = models.CharField(max_length=20, db_index=True)
    commissioning_date = models.CharField(max_length=8, blank=True, default="")
    driver1_customer_number = models.CharField(
        max_length=20, blank=True, default="", db_index=True
    )
    driver2_customer_number = models.CharField(
        max_length=20, blank=True, default="", db_index=True
    )
    status = models.CharField(
        max_length=30,
        choices=[(status.value, status.value) for status in VehicleStatus],
        db_index=True,
    )

    class Meta:
        app_label = "vehicle"
        db_table = "vehicle"
        verbose_name = "Vehicle"
        verbose_name_plural = "Vehicles"
        constraints = [
            models.UniqueConstraint(
                fields=["license_plate"],
                name="unique_vehicle_license_plate",
            ),
            models.UniqueConstraint(
                fields=["vehicle_number"],
                name="unique_vehicle_number",
            ),
        ]
        indexes = [
            models.Index(fields=["status"], name="vehicle_status_idx"),
            models.Index(fields=["vehicle_number"], name="vehicle_number_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.vehicle_number} ({self.license_plate})"


class VehicleDriverAssignmentHistoryModel(BusinessRecordModel):
    """SAP driver assignment snapshot captured during every vehicle sync."""

    class DriverRole(models.TextChoices):
        DRIVER = "DRIVER", "Driver"
        ASSISTANT = "ASSISTANT", "Assistant"

    sync_run_id = models.UUIDField(db_index=True)
    request_id = models.CharField(max_length=100, blank=True, default="")
    synced_at = models.DateTimeField(db_index=True)
    vehicle_id = models.UUIDField(db_index=True)
    vehicle_number = models.CharField(max_length=18, db_index=True)
    license_plate = models.CharField(max_length=20, blank=True, default="")
    driver_role = models.CharField(
        max_length=20,
        choices=DriverRole.choices,
        db_index=True,
    )
    driver_customer_number = models.CharField(
        max_length=20, blank=True, default="", db_index=True
    )

    class Meta:
        app_label = "vehicle"
        db_table = "vehicle_driver_assignment_history"
        verbose_name = "Vehicle Driver Assignment History"
        verbose_name_plural = "Vehicle Driver Assignment Histories"
        indexes = [
            models.Index(
                fields=["vehicle_number", "synced_at"],
                name="veh_drv_hist_vehicle_time_idx",
            ),
            models.Index(
                fields=["driver_customer_number", "synced_at"],
                name="veh_drv_hist_driver_time_idx",
            ),
            models.Index(
                fields=["sync_run_id", "vehicle_number"],
                name="veh_drv_hist_run_vehicle_idx",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.synced_at.isoformat()} {self.vehicle_number} "
            f"{self.driver_role}: {self.driver_customer_number or '-'}"
        )


class VehicleComponentHistoryModel(BusinessRecordModel):
    """Installed/replaced component history for maintenance decisions."""

    vehicle_id = models.UUIDField(db_index=True)
    repair_order_id = models.UUIDField(db_index=True)
    component_type = models.CharField(max_length=30, db_index=True)
    material_number = models.CharField(max_length=40, db_index=True)
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit_of_measure = models.CharField(max_length=10)
    description = models.CharField(max_length=255, blank=True, default="")
    installed_at = models.DateTimeField(db_index=True)
    recorded_by_id = models.UUIDField()

    class Meta:
        app_label = "vehicle"
        db_table = "vehicle_component_history"
        verbose_name = "Vehicle Component History"
        verbose_name_plural = "Vehicle Component Histories"
        indexes = [
            models.Index(
                fields=["vehicle_id", "installed_at"],
                name="veh_comp_hist_vehicle_time_idx",
            ),
            models.Index(
                fields=["vehicle_id", "component_type"],
                name="veh_comp_hist_type_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.vehicle_id} {self.component_type}: {self.material_number}"


class VehicleOdometerReadingModel(BusinessRecordModel):
    """Daily odometer reading recorded inside FMMS by operational users."""

    vehicle_id = models.UUIDField(db_index=True)
    reading_date = models.DateField(db_index=True)
    odometer_km = models.PositiveIntegerField()
    source = models.CharField(max_length=30, default="DRIVER")
    recorded_by_id = models.UUIDField()
    recorded_at = models.DateTimeField()

    class Meta:
        app_label = "vehicle"
        db_table = "vehicle_odometer_reading"
        verbose_name = "Vehicle Odometer Reading"
        verbose_name_plural = "Vehicle Odometer Readings"
        constraints = [
            models.UniqueConstraint(
                fields=["vehicle_id", "reading_date"],
                condition=models.Q(is_deleted=False),
                name="unique_vehicle_odometer_per_day",
            ),
        ]
        indexes = [
            models.Index(
                fields=["vehicle_id", "reading_date", "is_deleted"],
                name="vehicle_odo_vehicle_date_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.vehicle_id} {self.reading_date}: {self.odometer_km} km"
