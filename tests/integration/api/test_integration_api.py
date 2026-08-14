"""API integration tests for SAP transaction read endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from rest_framework.test import APIClient

from apps.integration.domain.entities import (
    SAPObjectType,
    SAPTransaction,
    SAPTransactionStatus,
)
from apps.integration.infrastructure.models import SAPSyncRunModel
from apps.integration.infrastructure.repositories import DjangoSAPTransactionRepository
from apps.vehicle.infrastructure.models import VehicleModel

pytestmark = pytest.mark.django_db


class TestIntegrationAPI:
    """Cover SAP transaction list and retrieve endpoints."""

    def test_list_and_retrieve_sap_transactions(
        self, authenticated_client: APIClient
    ) -> None:
        """Seed a transaction and read it through the API."""
        now = datetime.now(tz=UTC)
        txn = SAPTransaction(
            id=uuid.uuid4(),
            object_type=SAPObjectType.FAULT,
            object_id=uuid.uuid4(),
            idempotency_key=f"FAULT-{uuid.uuid4()}",
            status=SAPTransactionStatus.PENDING,
            created_at=now,
            updated_at=now,
            request_payload={"action": "CREATE_NOTIFICATION"},
        )
        saved = DjangoSAPTransactionRepository().save(txn)

        listed = authenticated_client.get("/api/v1/sap-transactions/")
        assert listed.status_code == 200
        assert listed.data["count"] >= 1

        filtered = authenticated_client.get("/api/v1/sap-transactions/?status=PENDING")
        assert filtered.status_code == 200
        assert filtered.data["count"] >= 1

        retrieved = authenticated_client.get(f"/api/v1/sap-transactions/{saved.id}/")
        assert retrieved.status_code == 200
        assert retrieved.data["id"] == str(saved.id)
        assert retrieved.data["status"] == "PENDING"
        assert retrieved.data["section"] == "خرابی / اعلان PM"
        assert retrieved.data["protocol"] == "BAPI"
        assert retrieved.data["request_payload"] == {"action": "CREATE_NOTIFICATION"}

        by_type = authenticated_client.get(
            "/api/v1/sap-transactions/?object_type=FAULT"
        )
        assert by_type.status_code == 200
        assert by_type.data["count"] >= 1

        summary = authenticated_client.get("/api/v1/sap-transactions/summary/")
        assert summary.status_code == 200
        assert summary.data["total"] >= 1
        assert summary.data["pending"] >= 1

    def test_global_sap_sync_uses_mock_odata_fixtures(
        self, authenticated_client: APIClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Run all read syncs through XML mock fixtures when mock mode is active."""
        monkeypatch.setenv("SAP_USE_MOCK", "True")

        response = authenticated_client.post("/api/v1/sap-sync/", {}, format="json")

        assert response.status_code == 200, response.data
        assert response.data["status"] == "SUCCESS"
        items = {item["name"]: item for item in response.data["items"]}
        assert items["vehicles"]["summary"]["total_received"] >= 1
        assert items["vehicles"]["summary"]["failed"] == 0
        assert items["inspection_templates"]["summary"]["total_received"] >= 4
        assert items["inspection_templates"]["summary"]["failed"] == 0
        assert items["fault_catalog"]["summary"]["total_received"] >= 4
        assert items["fault_catalog"]["summary"]["failed"] == 0
        assert items["central_stock"]["summary"]["total_received"] >= 10
        assert items["central_stock"]["summary"]["failed"] == 0
        assert VehicleModel.objects.exists()
        assert SAPSyncRunModel.objects.filter(
            id=response.data["id"],
            trigger_source="API",
            status="SUCCESS",
        ).exists()

    def test_global_sap_sync_history_is_listed(
        self, authenticated_client: APIClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Expose persisted SAP read-sync history for API and job runs."""
        monkeypatch.setenv("SAP_USE_MOCK", "True")
        created = authenticated_client.post("/api/v1/sap-sync/", {}, format="json")
        assert created.status_code == 200, created.data

        response = authenticated_client.get("/api/v1/sap-sync/history/")

        assert response.status_code == 200, response.data
        assert response.data["count"] >= 1
        first = response.data["results"][0]
        assert first["id"] == created.data["id"]
        assert first["trigger_source"] == "API"
        assert first["status"] == "SUCCESS"
        assert {item["name"] for item in first["items"]} == {
            "vehicles",
            "inspection_templates",
            "fault_catalog",
            "inspection_defect_options",
            "central_stock",
        }
