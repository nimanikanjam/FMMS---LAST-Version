"""Reset workflow/demo data while keeping selected master records.

This destructive operational command is restricted to environments with
``settings.DEBUG`` enabled.
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.driver.infrastructure.models import DriverModel
from apps.fault.infrastructure.models import FaultItemModel, FaultModel
from apps.handover.infrastructure.models import VehicleHandoverModel
from apps.inspection.infrastructure.models import InspectionModel
from apps.integration.infrastructure.models import (
    SAPSyncRunItemModel,
    SAPSyncRunModel,
    SAPTransactionModel,
)
from apps.material.infrastructure.models import (
    InventoryTransactionModel,
    MaterialRequestModel,
)
from apps.preventive_maintenance.infrastructure.models import (
    PMPlanModel,
    PMWorkOrderModel,
)
from apps.procurement.infrastructure.models import (
    PurchaseOrderModel,
    PurchaseRequisitionModel,
)
from apps.repair.infrastructure.models import (
    ExternalRepairInvoiceModel,
    RepairOrderEventModel,
    RepairOrderModel,
)
from apps.vehicle.infrastructure.models import (
    VehicleComponentHistoryModel,
    VehicleDriverAssignmentHistoryModel,
    VehicleModel,
    VehicleOdometerReadingModel,
)

# Delete children/dependents first where hard foreign keys exist.
_DELETE_TARGETS: tuple[tuple[str, type], ...] = (
    ("inventory_transaction", InventoryTransactionModel),
    ("material_request", MaterialRequestModel),
    ("vehicle_handover", VehicleHandoverModel),
    ("external_repair_invoice", ExternalRepairInvoiceModel),
    ("repair_order_event", RepairOrderEventModel),
    ("repair_order", RepairOrderModel),
    ("purchase_order", PurchaseOrderModel),
    ("purchase_requisition", PurchaseRequisitionModel),
    ("fault_item", FaultItemModel),
    ("fault", FaultModel),
    ("inspection", InspectionModel),
    ("pm_work_order", PMWorkOrderModel),
    ("pm_plan", PMPlanModel),
    ("sap_transaction", SAPTransactionModel),
    ("sap_sync_run_item", SAPSyncRunItemModel),
    ("sap_sync_run", SAPSyncRunModel),
    ("vehicle_odometer_reading", VehicleOdometerReadingModel),
    ("vehicle_component_history", VehicleComponentHistoryModel),
    ("vehicle_driver_assignment_history", VehicleDriverAssignmentHistoryModel),
    ("vehicle", VehicleModel),
    ("driver", DriverModel),
)


class Command(BaseCommand):
    """Wipe operational workflow data and preserve templates and users."""

    help = (
        "DEBUG only: delete all workflow data (inspections, faults, repairs, "
        "materials, handovers, procurement, SAP txs, odometer readings, "
        "vehicle histories, vehicles, drivers, PM) while keeping inspection "
        "checklist templates and users."
    )

    def add_arguments(self, parser: Any) -> None:
        """Register CLI flags."""
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Skip interactive confirmation.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print row counts that would be deleted without writing.",
        )

    def handle(self, *args: object, **options: object) -> None:
        """Execute the reset.

        Raises:
            CommandError: When DEBUG is off or the user aborts.
        """
        if not settings.DEBUG:
            raise CommandError(
                "reset_workflow_data is only allowed when DEBUG=True "
                "(local development). Refusing to run."
            )

        dry_run = bool(options.get("dry_run"))
        skip_confirm = bool(options.get("yes"))
        counts = self._collect_counts()

        self.stdout.write(self.style.WARNING("Tables that will be cleared:"))
        for label, count in counts:
            self.stdout.write(f"  - {label}: {count} row(s)")
        self.stdout.write(self.style.SUCCESS("Preserved:"))
        self.stdout.write("  - inspection_template")
        self.stdout.write("  - users (AUTH_USER_MODEL)")

        if dry_run:
            self.stdout.write(self.style.NOTICE("Dry run — no changes written."))
            return

        if not skip_confirm:
            answer = input("Type 'RESET' to confirm irreversible delete: ").strip()
            if answer != "RESET":
                raise CommandError("Aborted.")

        with transaction.atomic():
            deleted_summary = self._delete_all()

        for label, deleted in deleted_summary:
            self.stdout.write(f"Deleted {label}: {deleted}")
        self.stdout.write(self.style.SUCCESS("Workflow data and vehicles cleared."))

    def _collect_counts(self) -> list[tuple[str, int]]:
        """Return (label, count) for each wipe target."""
        return [(label, model.objects.count()) for label, model in _DELETE_TARGETS]

    def _delete_all(self) -> list[tuple[str, int]]:
        """Hard-delete all wipe targets; return (label, deleted_count)."""
        results: list[tuple[str, int]] = []
        for label, model in _DELETE_TARGETS:
            deleted, _details = model.objects.all().delete()
            results.append((label, deleted))
        return results
