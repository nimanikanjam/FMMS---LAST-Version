"""API tests for transport supervisor repair approval and workshop assignment."""

from __future__ import annotations

import uuid

import pytest
from rest_framework.test import APIClient

from apps.fault.infrastructure.models import FaultModel
from apps.integration.infrastructure.models import SAPTransactionModel
from apps.repair.infrastructure.models import RepairOrderModel
from apps.vehicle.infrastructure.models import VehicleModel
from tests.integration.api.conftest import create_repair_order_via_distribution

pytestmark = pytest.mark.django_db


def _create_repair_order(client: APIClient, plate: str, vin: str) -> dict:
    """Create vehicle + fault + repair order via distribution-unusable."""
    return create_repair_order_via_distribution(client, plate=plate, vin=vin)


class TestRepairApproveAPI:
    """Cover POST /api/v1/repair-orders/{id}/approve/."""

    def test_admin_can_approve_repair(self, authenticated_client: APIClient) -> None:
        order = _create_repair_order(
            authenticated_client, "12APR001", "1HGCM82633A004371"
        )
        response = authenticated_client.post(
            f"/api/v1/repair-orders/{order['id']}/approve/", {}, format="json"
        )
        assert response.status_code == 200, response.data
        assert response.data["status"] == "APPROVED"
        assert response.data["id"] == order["id"]
        assert "ترابری" in response.data["message"]

    def test_transport_can_approve_repair(
        self, authenticated_client: APIClient, transport_client: APIClient
    ) -> None:
        order = _create_repair_order(
            authenticated_client, "12APR002", "1HGCM82633A004372"
        )
        response = transport_client.post(
            f"/api/v1/repair-orders/{order['id']}/approve/", {}, format="json"
        )
        assert response.status_code == 200, response.data
        assert response.data["status"] == "APPROVED"

    def test_distribution_cannot_approve_transport_repair(
        self, authenticated_client: APIClient, distribution_client: APIClient
    ) -> None:
        order = _create_repair_order(
            authenticated_client, "12APR006", "1HGCM82633A004382"
        )
        response = distribution_client.post(
            f"/api/v1/repair-orders/{order['id']}/approve/", {}, format="json"
        )
        assert response.status_code == 403

    def test_viewer_cannot_approve_repair(
        self, authenticated_client: APIClient, viewer_client: APIClient
    ) -> None:
        order = _create_repair_order(
            authenticated_client, "12APR003", "1HGCM82633A004373"
        )
        response = viewer_client.post(
            f"/api/v1/repair-orders/{order['id']}/approve/", {}, format="json"
        )
        assert response.status_code == 403

    def test_technician_cannot_approve_repair(
        self, authenticated_client: APIClient, technician_client: APIClient
    ) -> None:
        order = _create_repair_order(
            authenticated_client, "12APR004", "1HGCM82633A004374"
        )
        response = technician_client.post(
            f"/api/v1/repair-orders/{order['id']}/approve/", {}, format="json"
        )
        assert response.status_code == 403

    def test_approve_missing_repair_order_returns_404(
        self, authenticated_client: APIClient
    ) -> None:
        missing_id = uuid.uuid4()
        response = authenticated_client.post(
            f"/api/v1/repair-orders/{missing_id}/approve/", {}, format="json"
        )
        assert response.status_code == 404

    def test_approve_invalid_state_returns_422(
        self, authenticated_client: APIClient
    ) -> None:
        order = _create_repair_order(
            authenticated_client, "12APR005", "1HGCM82633A004375"
        )
        first = authenticated_client.post(
            f"/api/v1/repair-orders/{order['id']}/approve/", {}, format="json"
        )
        assert first.status_code == 200
        second = authenticated_client.post(
            f"/api/v1/repair-orders/{order['id']}/approve/", {}, format="json"
        )
        assert second.status_code == 422


class TestRepairAssignWorkshopAPI:
    """Cover POST /api/v1/repair-orders/{id}/assign-workshop/."""

    def _approved_order(self, client: APIClient, plate: str, vin: str) -> dict:
        order = _create_repair_order(client, plate, vin)
        approved = client.post(
            f"/api/v1/repair-orders/{order['id']}/approve/", {}, format="json"
        )
        assert approved.status_code == 200, approved.data
        return approved.data

    def test_admin_can_assign_internal_workshop(
        self, authenticated_client: APIClient
    ) -> None:
        order = self._approved_order(
            authenticated_client, "12WS001", "1HGCM82633A004376"
        )
        response = authenticated_client.post(
            f"/api/v1/repair-orders/{order['id']}/assign-workshop/",
            {"workshop_type": "INTERNAL"},
            format="json",
        )
        assert response.status_code == 200, response.data
        assert response.data["status"] == "WORKSHOP_ASSIGNED"
        assert response.data["workshop_type"] == "INTERNAL"
        assert "تعمیرگاه" in response.data["message"]

    def test_transport_can_assign_external_workshop_and_create_referral_request(
        self, authenticated_client: APIClient, transport_client: APIClient
    ) -> None:
        order = self._approved_order(
            authenticated_client, "12WS002", "1HGCM82633A004377"
        )
        response = transport_client.post(
            f"/api/v1/repair-orders/{order['id']}/assign-workshop/",
            {
                "workshop_type": "EXTERNAL",
                "workshop_id": "EXT-001",
                "reason": "Central workshop unavailable",
            },
            format="json",
        )
        assert response.status_code == 200, response.data
        assert response.data["workshop_type"] == "EXTERNAL"
        assert response.data["status"] == "WAITING_EXTERNAL_REFERRAL_APPROVAL"
        assert response.data["external_referral_request_id"]
        assert "مجوز" in response.data["message"]

        referrals = authenticated_client.get("/api/v1/external-workshop-referrals/")
        assert referrals.status_code == 200, referrals.data
        results = (
            referrals.data["results"] if "results" in referrals.data else referrals.data
        )
        assert any(item["repair_order_id"] == order["id"] for item in results)

    def test_distribution_cannot_assign_transport_workshop(
        self, authenticated_client: APIClient, distribution_client: APIClient
    ) -> None:
        order = self._approved_order(
            authenticated_client, "12WS007", "1HGCM82633A004383"
        )
        response = distribution_client.post(
            f"/api/v1/repair-orders/{order['id']}/assign-workshop/",
            {"workshop_type": "INTERNAL"},
            format="json",
        )
        assert response.status_code == 403

    def test_transport_reject_records_reason_and_returns_to_distribution(
        self, authenticated_client: APIClient, transport_client: APIClient
    ) -> None:
        order = _create_repair_order(
            authenticated_client, "12APR007", "1HGCM82633A004384"
        )
        response = transport_client.post(
            f"/api/v1/repair-orders/{order['id']}/transport-reject/",
            {"reason": "Repair is not required"},
            format="json",
        )
        assert response.status_code == 200, response.data
        assert response.data["status"] == "REJECTED_BY_TRANSPORT"
        assert response.data["transport_rejection_reason"] == "Repair is not required"

    def test_assign_workshop_before_approval_returns_422(
        self, authenticated_client: APIClient
    ) -> None:
        order = _create_repair_order(
            authenticated_client, "12WS003", "1HGCM82633A004378"
        )
        response = authenticated_client.post(
            f"/api/v1/repair-orders/{order['id']}/assign-workshop/",
            {"workshop_type": "INTERNAL"},
            format="json",
        )
        assert response.status_code == 422

    def test_cannot_reassign_workshop_after_assignment(
        self, authenticated_client: APIClient
    ) -> None:
        order = self._approved_order(
            authenticated_client, "12WS008", "1HGCM82633A004385"
        )
        first = authenticated_client.post(
            f"/api/v1/repair-orders/{order['id']}/assign-workshop/",
            {"workshop_type": "INTERNAL"},
            format="json",
        )
        assert first.status_code == 200, first.data
        second = authenticated_client.post(
            f"/api/v1/repair-orders/{order['id']}/assign-workshop/",
            {"workshop_type": "EXTERNAL", "workshop_id": "EXT-009"},
            format="json",
        )
        assert second.status_code == 422

    def test_invalid_workshop_type_returns_400(
        self, authenticated_client: APIClient
    ) -> None:
        order = self._approved_order(
            authenticated_client, "12WS004", "1HGCM82633A004379"
        )
        response = authenticated_client.post(
            f"/api/v1/repair-orders/{order['id']}/assign-workshop/",
            {"workshop_type": "UNKNOWN"},
            format="json",
        )
        assert response.status_code == 400

    def test_external_workshop_requires_workshop_id(
        self, authenticated_client: APIClient
    ) -> None:
        order = self._approved_order(
            authenticated_client, "12WS008", "1HGCM82633A004385"
        )
        response = authenticated_client.post(
            f"/api/v1/repair-orders/{order['id']}/assign-workshop/",
            {"workshop_type": "EXTERNAL"},
            format="json",
        )
        assert response.status_code == 400

    def test_viewer_cannot_assign_workshop(
        self, authenticated_client: APIClient, viewer_client: APIClient
    ) -> None:
        order = self._approved_order(
            authenticated_client, "12WS005", "1HGCM82633A004380"
        )
        response = viewer_client.post(
            f"/api/v1/repair-orders/{order['id']}/assign-workshop/",
            {"workshop_type": "INTERNAL"},
            format="json",
        )
        assert response.status_code == 403

    def test_technician_cannot_assign_workshop(
        self, authenticated_client: APIClient, technician_client: APIClient
    ) -> None:
        order = self._approved_order(
            authenticated_client, "12WS006", "1HGCM82633A004381"
        )
        response = technician_client.post(
            f"/api/v1/repair-orders/{order['id']}/assign-workshop/",
            {"workshop_type": "EXTERNAL"},
            format="json",
        )
        assert response.status_code == 403


class TestReadOnlySAPWorkshopDecisionAPI:
    """Keep the local workshop workflow available when SAP writes are disabled."""

    def test_repairable_decision_starts_local_repair_without_sap_transaction(
        self,
        authenticated_client: APIClient,
        workshop_supervisor_client: APIClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("SAP_USE_MOCK", "False")
        monkeypatch.setenv("SAP_WRITE", "False")
        monkeypatch.setenv("SAP_BASE_URL", "https://sap.example.test")
        monkeypatch.setenv("SAP_CLIENT", "100")
        monkeypatch.setenv("SAP_USERNAME", "readonly-user")
        monkeypatch.setenv("SAP_PASSWORD", "readonly-password")
        monkeypatch.setenv("SAP_ASHOST", "sap.example.test")

        order = _create_repair_order(
            authenticated_client,
            "12LOCAL1",
            "1HGCM82633A004390",
        )
        approved = authenticated_client.post(
            f"/api/v1/repair-orders/{order['id']}/approve/",
            {},
            format="json",
        )
        assert approved.status_code == 200, approved.data
        assigned = authenticated_client.post(
            f"/api/v1/repair-orders/{order['id']}/assign-workshop/",
            {"workshop_type": "INTERNAL", "workshop_id": "WS-LOCAL"},
            format="json",
        )
        assert assigned.status_code == 200, assigned.data

        decision = workshop_supervisor_client.post(
            f"/api/v1/repair-orders/{order['id']}/technical-decision/",
            {"repairable": True, "note": "Proceed with local repair"},
            format="json",
        )

        assert decision.status_code == 200, decision.data
        assert decision.data["status"] == "IN_PROGRESS"
        assert "بدون ایجاد سفارش کار SAP" in decision.data["message"]
        persisted = RepairOrderModel.objects.get(id=order["id"])
        assert persisted.status == "IN_PROGRESS"
        assert not persisted.sap_order_number
        assert (
            VehicleModel.objects.get(id=persisted.vehicle_id).status == "UNDER_REPAIR"
        )
        assert FaultModel.objects.get(id=persisted.fault_id).status == "IN_REPAIR"
        assert SAPTransactionModel.objects.filter(object_id=persisted.id).count() == 0
