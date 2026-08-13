"""API integration tests for inspection endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from rest_framework.test import APIClient

from apps.fault.infrastructure.models import FaultModel
from apps.integration.infrastructure.models import SAPTransactionModel
from apps.repair.infrastructure.models import RepairOrderModel
from tests.integration.api.conftest import create_vehicle

pytestmark = pytest.mark.django_db


class TestInspectionAPI:
    """Cover inspection create, item add, and submit flows."""

    def test_create_add_item_submit(self, authenticated_client: APIClient) -> None:
        """Create an inspection, add an item, and submit it."""
        vehicle = create_vehicle(
            authenticated_client, plate="12INSP01", vin="1HGCM82633A004354"
        )
        created = authenticated_client.post(
            "/api/v1/inspections/",
            {
                "vehicle_id": vehicle["id"],
                "inspection_type": "PRE_TRIP",
                "odometer_value": 12000,
                "odometer_unit": "KM",
                "inspected_at": datetime.now(tz=UTC).isoformat(),
            },
            format="json",
        )
        assert created.status_code == 201, created.data
        inspection_id = created.data["id"]
        assert created.data["status"] == "DRAFT"

        with_item = authenticated_client.post(
            f"/api/v1/inspections/{inspection_id}/items/",
            {
                "category": "Brakes",
                "description": "Pad thickness",
                "result": "PASS",
            },
            format="json",
        )
        assert with_item.status_code == 200, with_item.data
        assert len(with_item.data["items"]) == 1

        submitted = authenticated_client.post(
            f"/api/v1/inspections/{inspection_id}/submit/",
            {},
            format="json",
        )
        assert submitted.status_code == 200, submitted.data
        assert submitted.data["status"] != "DRAFT"

        listed = authenticated_client.get(
            f"/api/v1/inspections/?vehicle_id={vehicle['id']}"
        )
        assert listed.status_code == 200
        assert listed.data["count"] >= 1

        inspected_at = submitted.data["inspected_at"][:10]
        ranged = authenticated_client.get(
            f"/api/v1/inspections/?vehicle_id={vehicle['id']}"
            f"&from_date={inspected_at}&to_date={inspected_at}"
        )
        assert ranged.status_code == 200, ranged.data
        assert ranged.data["count"] >= 1

        invalid = authenticated_client.get(
            f"/api/v1/inspections/?vehicle_id={vehicle['id']}"
            "&from_date=2026-07-20&to_date=2026-07-10"
        )
        assert invalid.status_code == 400
        assert "to_date" in invalid.data.get("details", invalid.data)

    @pytest.mark.parametrize(
        ("sap_use_mock", "sap_write"),
        [("True", "True"), ("False", "False")],
    )
    def test_failed_checklist_requires_explicit_fault_report(
        self,
        authenticated_client: APIClient,
        monkeypatch: pytest.MonkeyPatch,
        sap_use_mock: str,
        sap_write: str,
    ) -> None:
        """Submitting a failed checklist does not create a fault until requested."""
        monkeypatch.setenv("SAP_USE_MOCK", sap_use_mock)
        monkeypatch.setenv("SAP_WRITE", sap_write)
        if sap_use_mock == "False":
            monkeypatch.setenv("SAP_BASE_URL", "https://sap.example.test")
            monkeypatch.setenv("SAP_CLIENT", "100")
            monkeypatch.setenv("SAP_USERNAME", "readonly-user")
            monkeypatch.setenv("SAP_PASSWORD", "readonly-password")
            monkeypatch.setenv("SAP_ASHOST", "sap.example.test")
        vehicle = create_vehicle(
            authenticated_client,
            plate=f"12FAIL{sap_use_mock[0]}{sap_write[0]}",
            vin="1HGCM82633A004355",
        )
        created = authenticated_client.post(
            "/api/v1/inspections/",
            {
                "vehicle_id": vehicle["id"],
                "inspection_type": "PRE_TRIP",
                "odometer_value": 12000,
                "odometer_unit": "KM",
                "inspected_at": datetime.now(tz=UTC).isoformat(),
                "items": [
                    {
                        "category": "Brakes",
                        "description": "Pad thickness",
                        "result": "FAIL",
                        "notes": "Pad worn",
                        "severity": "HIGH",
                    }
                ],
            },
            format="json",
        )
        assert created.status_code == 201, created.data
        inspection_id = created.data["id"]

        submitted = authenticated_client.post(
            f"/api/v1/inspections/{inspection_id}/submit/",
            {},
            format="json",
        )
        assert submitted.status_code == 200, submitted.data
        assert submitted.data["has_failures"] is True
        assert FaultModel.objects.filter(inspection_id=inspection_id).count() == 0

        reported = authenticated_client.post(
            f"/api/v1/inspections/{inspection_id}/report-fault/",
            {},
            format="json",
        )

        assert reported.status_code == 201, reported.data
        assert reported.data["inspection_id"] == inspection_id
        assert len(reported.data["items"]) == 1
        assert FaultModel.objects.filter(inspection_id=inspection_id).count() == 1
        assert (
            RepairOrderModel.objects.filter(fault_id=reported.data["id"]).count() == 0
        )

    def test_real_odata_read_mode_reports_fault_with_jwt_and_no_sap_write(
        self,
        admin_user: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Real OData mode keeps the authenticated local fault workflow available."""
        monkeypatch.setenv("SAP_USE_MOCK", "False")
        monkeypatch.setenv("SAP_WRITE", "False")
        monkeypatch.setenv("SAP_BASE_URL", "https://sap.example.test")
        monkeypatch.setenv("SAP_CLIENT", "100")
        monkeypatch.setenv("SAP_USERNAME", "readonly-user")
        monkeypatch.setenv("SAP_PASSWORD", "readonly-password")
        monkeypatch.setenv("SAP_ASHOST", "sap.example.test")

        client = APIClient()
        token_response = client.post(
            "/api/v1/auth/token/",
            {
                "username": admin_user.username,
                "password": "testpass123!",
            },
            format="json",
        )
        assert token_response.status_code == 200, token_response.data
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token_response.data['access']}")

        vehicle = create_vehicle(
            client,
            plate="12JWT001",
            vin="1HGCM82633A004356",
        )
        created = client.post(
            "/api/v1/inspections/",
            {
                "vehicle_id": vehicle["id"],
                "inspection_type": "PRE_TRIP",
                "odometer_value": 13000,
                "odometer_unit": "KM",
                "inspected_at": datetime.now(tz=UTC).isoformat(),
                "items": [
                    {
                        "category": "Brakes",
                        "description": "Brake pressure",
                        "result": "FAIL",
                        "notes": "Pressure below threshold",
                        "severity": "HIGH",
                    }
                ],
            },
            format="json",
        )
        assert created.status_code == 201, created.data

        submitted = client.post(
            f"/api/v1/inspections/{created.data['id']}/submit/",
            {},
            format="json",
        )
        assert submitted.status_code == 200, submitted.data

        reported = client.post(
            f"/api/v1/inspections/{created.data['id']}/report-fault/",
            {},
            format="json",
        )

        assert reported.status_code == 201, reported.data
        assert reported.data["inspection_id"] == created.data["id"]
        fault = FaultModel.objects.get(inspection_id=created.data["id"])
        assert fault.status == "OPEN"
        assert not fault.sap_notification_number

        distribution_decision = client.post(
            f"/api/v1/faults/{reported.data['id']}/distribution-unusable/",
            {"note": "Vehicle must enter the local repair workflow"},
            format="json",
        )

        assert distribution_decision.status_code == 200, distribution_decision.data
        assert distribution_decision.data["status"] == "AWAITING_TRANSPORT"
        assert RepairOrderModel.objects.filter(fault_id=fault.id).count() == 1
        assert SAPTransactionModel.objects.count() == 0
