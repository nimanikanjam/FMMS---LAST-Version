"""API integration tests for demo workflow backend contracts."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from rest_framework.test import APIClient

from apps.fault.infrastructure.models import FaultItemModel, FaultModel
from apps.material.infrastructure.models import CentralStockModel
from apps.repair.infrastructure.models import RepairOrderModel
from apps.vehicle.domain.entities import VehicleStatus
from apps.vehicle.infrastructure.models import VehicleModel
from tests.integration.api.conftest import create_vehicle

pytestmark = pytest.mark.django_db


class TestVehicleSAPBulkSyncAPI:
    """Vehicle SAP sync is scheduled/operational, not a phase-1 public API."""

    def test_vehicle_sync_api_is_not_available_in_phase_1(
        self, authenticated_client: APIClient
    ) -> None:
        response = authenticated_client.post(
            "/api/v1/vehicles/sync-sap/", {}, format="json"
        )

        assert response.status_code == 405


class TestInspectionTemplateSAPSyncAPI:
    """Cover inspection-template list API after global SAP sync."""

    def test_sync_and_list_templates(
        self, authenticated_client: APIClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SAP_USE_MOCK", "True")

        synced = authenticated_client.post("/api/v1/sap-sync/", {}, format="json")
        assert synced.status_code == 200, synced.data
        items = {item["name"]: item for item in synced.data["items"]}
        assert items["inspection_templates"]["summary"]["total_received"] >= 4
        assert items["inspection_templates"]["summary"]["failed"] == 0

        listed = authenticated_client.get("/api/v1/inspection-templates/")
        assert listed.status_code == 200
        results = listed.data["results"] if "results" in listed.data else listed.data
        descriptions = {item["code_text"] for item in results}
        assert all("group_text" in item and "code_text" in item for item in results)
        assert all("code_group" in item and "code" in item for item in results)
        assert all(
            "GroupText" not in item and "CodeText" not in item for item in results
        )
        assert all("CodeGroup" not in item and "Code" not in item for item in results)
        assert "ترمز جلو" in descriptions
        assert "چراغ جلو" in descriptions
        assert "موتور اصلی" in descriptions
        assert "باتری/دینام" in descriptions
        brake_item = next(
            item
            for item in results
            if item["code_group"] == "FL-BRK" and item["code"] == "B002"
        )
        assert brake_item["group_text"] == "سیستم ترمز"
        assert brake_item["code_text"] == "ترمز عقب"
        for group_text in {item["group_text"] for item in results}:
            group_codes = [
                item["code"] for item in results if item["group_text"] == group_text
            ]
            assert group_codes == sorted(group_codes)

    def test_manual_template_sync_api_is_not_available(
        self, authenticated_client: APIClient
    ) -> None:
        response = authenticated_client.post(
            "/api/v1/inspection-templates/sync-sap/", {}, format="json"
        )

        assert response.status_code == 404


class TestFaultCatalogAPI:
    """Cover fault catalog list API after global SAP sync."""

    def test_sync_and_list_fault_catalog(
        self, authenticated_client: APIClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SAP_USE_MOCK", "True")
        synced = authenticated_client.post("/api/v1/sap-sync/", {}, format="json")
        assert synced.status_code == 200, synced.data

        listed = authenticated_client.get("/api/v1/fault-catalogs/?search=ترمز")

        assert listed.status_code == 200, listed.data
        results = listed.data["results"] if "results" in listed.data else listed.data
        assert {item["code_text"] for item in results}
        assert all("defect_class" in item for item in results)
        ordered = [(item["group_text"], item["code"]) for item in results]
        assert ordered == sorted(ordered)


class TestCentralStockAPI:
    """Cover central warehouse stock list API after global SAP sync."""

    def test_sync_and_list_central_stock(
        self, authenticated_client: APIClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SAP_USE_MOCK", "True")
        synced = authenticated_client.post("/api/v1/sap-sync/", {}, format="json")
        assert synced.status_code == 200, synced.data

        listed = authenticated_client.get(
            "/api/v1/central-stock/?storage_location=KH08&search=60001764"
        )

        assert listed.status_code == 200, listed.data
        results = listed.data["results"] if "results" in listed.data else listed.data
        assert len(results) >= 1
        assert all(item["storage_location"] == "KH08" for item in results)
        assert all("quantity" in item for item in results)
        assert any(item["material_code"] == "60001764" for item in results)

    def test_list_includes_material_description_for_frontend_picker(
        self,
        authenticated_client: APIClient,
    ) -> None:
        CentralStockModel.objects.create(
            material="000000000060009999",
            plant="1000",
            storage_location="KH08",
            inventory_stock_type="01",
            material_code="60009999",
            material_name="فیلتر روغن",
            inventory_stock_type_text="Unrestricted-Use Stock",
            quantity="7.000",
            base_unit="EA",
            stock_value="0.00",
            display_currency="IRR",
            is_active=True,
        )

        listed = authenticated_client.get(
            "/api/v1/central-stock/?storage_location=KH08&search=فیلتر روغن"
        )

        assert listed.status_code == 200, listed.data
        results = listed.data["results"] if "results" in listed.data else listed.data
        assert len(results) == 1
        assert results[0]["material_code"] == "60009999"
        assert results[0]["material_name"] == "فیلتر روغن"


class TestDriverInspectionWorkflowAPI:
    """Cover PASS vs FAIL inspection submit side-effects."""

    def test_submit_all_pass_keeps_vehicle_active(
        self, authenticated_client: APIClient
    ) -> None:
        vehicle = create_vehicle(
            authenticated_client, plate="12PASS01", vin="1HGCM82633A004361"
        )
        created = authenticated_client.post(
            "/api/v1/inspections/",
            {
                "vehicle_id": vehicle["id"],
                "inspection_type": "PRE_TRIP",
                "odometer_value": 1000,
                "odometer_unit": "KM",
                "inspected_at": datetime.now(tz=UTC).isoformat(),
                "items": [
                    {
                        "category": "SAFETY",
                        "description": "Seat belt",
                        "result": "PASS",
                    }
                ],
            },
            format="json",
        )
        assert created.status_code == 201, created.data

        submitted = authenticated_client.post(
            f"/api/v1/inspections/{created.data['id']}/submit/", {}, format="json"
        )
        assert submitted.status_code == 200, submitted.data
        assert submitted.data["status"] == "SUBMITTED"
        assert submitted.data["has_failures"] is False

        detail = authenticated_client.get(f"/api/v1/vehicles/{vehicle['id']}/")
        assert detail.data["status"] == VehicleStatus.ACTIVE.value
        assert FaultModel.objects.filter(vehicle_id=vehicle["id"]).count() == 0
        assert RepairOrderModel.objects.filter(vehicle_id=vehicle["id"]).count() == 0

    def test_failed_inspection_requires_explicit_fault_report(
        self, authenticated_client: APIClient
    ) -> None:
        vehicle = create_vehicle(
            authenticated_client, plate="12FAIL01", vin="1HGCM82633A004362"
        )
        created = authenticated_client.post(
            "/api/v1/inspections/",
            {
                "vehicle_id": vehicle["id"],
                "inspection_type": "PRE_TRIP",
                "odometer_value": 1000,
                "odometer_unit": "KM",
                "inspected_at": datetime.now(tz=UTC).isoformat(),
                "items": [
                    {
                        "category": "LIGHTS",
                        "description": "Front light",
                        "result": "FAIL",
                        "notes": "Broken",
                        "severity": "MEDIUM",
                    }
                ],
            },
            format="json",
        )
        assert created.status_code == 201, created.data

        submitted = authenticated_client.post(
            f"/api/v1/inspections/{created.data['id']}/submit/", {}, format="json"
        )
        assert submitted.status_code == 200, submitted.data
        assert submitted.data["has_failures"] is True

        assert (
            FaultModel.objects.filter(
                vehicle_id=vehicle["id"], inspection_id=created.data["id"]
            ).count()
            == 0
        )
        reported = authenticated_client.post(
            f"/api/v1/inspections/{created.data['id']}/report-fault/",
            {},
            format="json",
        )
        assert reported.status_code == 201, reported.data
        assert (
            FaultModel.objects.filter(
                vehicle_id=vehicle["id"], inspection_id=created.data["id"]
            ).count()
            == 1
        )
        # Repair order is deferred until distribution marks the vehicle unusable.
        assert RepairOrderModel.objects.filter(vehicle_id=vehicle["id"]).count() == 0

        orm = VehicleModel.objects.get(id=vehicle["id"])
        assert orm.status == VehicleStatus.ACTIVE.value

        fault = FaultModel.objects.get(
            vehicle_id=vehicle["id"], inspection_id=created.data["id"]
        )
        unusable = authenticated_client.post(
            f"/api/v1/faults/{fault.id}/distribution-unusable/",
            {"note": "needs repair"},
            format="json",
        )
        assert unusable.status_code == 200, unusable.data
        assert unusable.data["status"] == "AWAITING_TRANSPORT"
        assert RepairOrderModel.objects.filter(vehicle_id=vehicle["id"]).count() == 1
        order = RepairOrderModel.objects.get(vehicle_id=vehicle["id"])
        assert order.status == "CREATED"

    def test_distribution_supervisor_can_deactivate_after_failed_inspection(
        self, authenticated_client: APIClient
    ) -> None:
        vehicle = create_vehicle(
            authenticated_client, plate="12DIST01", vin="1HGCM82633A004364"
        )
        created = authenticated_client.post(
            "/api/v1/inspections/",
            {
                "vehicle_id": vehicle["id"],
                "inspection_type": "PRE_TRIP",
                "odometer_value": 1000,
                "odometer_unit": "KM",
                "inspected_at": datetime.now(tz=UTC).isoformat(),
                "items": [
                    {
                        "category": "LIGHTS",
                        "description": "Front light",
                        "result": "FAIL",
                        "notes": "Broken",
                        "severity": "MEDIUM",
                    }
                ],
            },
            format="json",
        )
        assert created.status_code == 201, created.data

        submitted = authenticated_client.post(
            f"/api/v1/inspections/{created.data['id']}/submit/", {}, format="json"
        )
        assert submitted.status_code == 200, submitted.data

        detail = authenticated_client.get(f"/api/v1/vehicles/{vehicle['id']}/")
        assert detail.data["status"] == VehicleStatus.ACTIVE.value

        deactivated = authenticated_client.post(
            f"/api/v1/vehicles/{vehicle['id']}/status/",
            {"status": VehicleStatus.INACTIVE.value},
            format="json",
        )
        assert deactivated.status_code == 200, deactivated.data
        assert deactivated.data["status"] == VehicleStatus.INACTIVE.value

    def test_report_failed_inspection_creates_one_fault_with_items(
        self, authenticated_client: APIClient
    ) -> None:
        vehicle = create_vehicle(
            authenticated_client, plate="12FAIL02", vin="1HGCM82633A004363"
        )
        created = authenticated_client.post(
            "/api/v1/inspections/",
            {
                "vehicle_id": vehicle["id"],
                "inspection_type": "PRE_TRIP",
                "odometer_value": 1000,
                "odometer_unit": "KM",
                "inspected_at": datetime.now(tz=UTC).isoformat(),
                "items": [
                    {
                        "category": "LIGHTS",
                        "description": "Front light",
                        "result": "FAIL",
                        "notes": "Broken",
                        "severity": "MEDIUM",
                    },
                    {
                        "category": "COOLING",
                        "description": "Refrigerator",
                        "result": "FAIL",
                        "notes": "Cooling failure",
                        "severity": "HIGH",
                    },
                ],
            },
            format="json",
        )
        assert created.status_code == 201, created.data

        submitted = authenticated_client.post(
            f"/api/v1/inspections/{created.data['id']}/submit/", {}, format="json"
        )
        assert submitted.status_code == 200, submitted.data
        assert submitted.data["has_failures"] is True

        reported = authenticated_client.post(
            f"/api/v1/inspections/{created.data['id']}/report-fault/",
            {},
            format="json",
        )
        assert reported.status_code == 201, reported.data
        faults = FaultModel.objects.filter(
            vehicle_id=vehicle["id"], inspection_id=created.data["id"]
        )
        assert faults.count() == 1
        fault = faults.first()
        assert fault is not None
        assert fault.description == "Multiple inspection failures"
        assert FaultItemModel.objects.filter(fault_id=fault.id).count() == 2
        # Repair order is deferred until distribution marks the vehicle unusable.
        assert RepairOrderModel.objects.filter(vehicle_id=vehicle["id"]).count() == 0

        retrieved = authenticated_client.get(f"/api/v1/faults/{fault.id}/")
        assert retrieved.status_code == 200
        assert len(retrieved.data["items"]) == 2
        components = {item["component"] for item in retrieved.data["items"]}
        assert components == {"Front light", "Refrigerator"}


class TestDistributionUsableWorkflowAPI:
    """Distribution usable closes fault and cancels early repair orders."""

    def test_distribution_usable_allows_next_driver_inspection(
        self, authenticated_client: APIClient
    ) -> None:
        vehicle = create_vehicle(
            authenticated_client, plate="12USE001", vin="1HGCM82633A004371"
        )
        created = authenticated_client.post(
            "/api/v1/inspections/",
            {
                "vehicle_id": vehicle["id"],
                "inspection_type": "PRE_TRIP",
                "odometer_value": 1000,
                "odometer_unit": "KM",
                "inspected_at": datetime.now(tz=UTC).isoformat(),
                "items": [
                    {
                        "category": "LIGHTS",
                        "description": "Front light",
                        "result": "FAIL",
                        "notes": "Broken",
                        "severity": "MEDIUM",
                    }
                ],
            },
            format="json",
        )
        assert created.status_code == 201, created.data

        submitted = authenticated_client.post(
            f"/api/v1/inspections/{created.data['id']}/submit/", {}, format="json"
        )
        assert submitted.status_code == 200, submitted.data
        assert submitted.data["has_failures"] is True

        reported = authenticated_client.post(
            f"/api/v1/inspections/{created.data['id']}/report-fault/",
            {},
            format="json",
        )
        assert reported.status_code == 201, reported.data
        faults = authenticated_client.get(f"/api/v1/faults/?vehicle_id={vehicle['id']}")
        assert faults.status_code == 200
        assert faults.data["count"] == 1
        fault = faults.data["results"][0]
        assert fault["status"] == "OPEN"

        orders = authenticated_client.get(
            f"/api/v1/repair-orders/?vehicle_id={vehicle['id']}"
        )
        assert orders.status_code == 200
        assert orders.data["count"] == 0

        vehicle_detail = authenticated_client.get(f"/api/v1/vehicles/{vehicle['id']}/")
        assert vehicle_detail.data["status"] == VehicleStatus.ACTIVE.value

        usable = authenticated_client.post(
            f"/api/v1/faults/{fault['id']}/distribution-usable/",
            {"note": "usable"},
            format="json",
        )
        assert usable.status_code == 200, usable.data
        assert usable.data["status"] == "CLOSED"

        vehicle_after = authenticated_client.get(f"/api/v1/vehicles/{vehicle['id']}/")
        assert vehicle_after.data["status"] == VehicleStatus.ACTIVE.value

        next_inspection = authenticated_client.post(
            "/api/v1/inspections/",
            {
                "vehicle_id": vehicle["id"],
                "inspection_type": "PRE_TRIP",
                "odometer_value": 1100,
                "odometer_unit": "KM",
                "inspected_at": datetime.now(tz=UTC).isoformat(),
                "items": [
                    {
                        "category": "SAFETY",
                        "description": "Seat belt",
                        "result": "PASS",
                    }
                ],
            },
            format="json",
        )
        assert next_inspection.status_code == 201, next_inspection.data

        next_submitted = authenticated_client.post(
            f"/api/v1/inspections/{next_inspection.data['id']}/submit/",
            {},
            format="json",
        )
        assert next_submitted.status_code == 200, next_submitted.data
        assert next_submitted.data["status"] == "SUBMITTED"
        assert next_submitted.data["has_failures"] is False
