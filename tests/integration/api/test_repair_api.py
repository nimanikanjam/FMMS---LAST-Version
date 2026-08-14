"""API integration tests for repair order endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from rest_framework.test import APIClient

from tests.integration.api.conftest import create_repair_order_via_distribution

pytestmark = pytest.mark.django_db


class TestRepairAPI:
    """Cover repair order lifecycle endpoints."""

    def test_direct_create_repair_order_is_blocked(
        self, authenticated_client: APIClient
    ) -> None:
        """POST /repair-orders/ is closed; RO comes from distribution-unusable."""
        order = create_repair_order_via_distribution(
            authenticated_client,
            plate="12REP000",
            vin="1HGCM82633A004355",
        )
        blocked = authenticated_client.post(
            "/api/v1/repair-orders/",
            {
                "vehicle_id": order["vehicle_id"],
                "fault_id": order["fault_id"],
            },
            format="json",
        )
        assert blocked.status_code == 409
        assert blocked.data["error_code"] == "REPAIR_ORDER_CREATE_VIA_DISTRIBUTION_ONLY"

    def test_repair_lifecycle(self, authenticated_client: APIClient) -> None:
        """Create, assign, start, and complete a repair order."""
        created = create_repair_order_via_distribution(
            authenticated_client,
            plate="12REP001",
            vin="1HGCM82633A004356",
            code="ENG-01",
            description="Engine noise",
        )
        vehicle = created["vehicle"]
        order_id = created["id"]
        assert created["status"] == "CREATED"

        technician_id = str(uuid4())
        assigned = authenticated_client.post(
            f"/api/v1/repair-orders/{order_id}/assign/",
            {"technician_id": technician_id},
            format="json",
        )
        assert assigned.status_code == 200, assigned.data
        assert assigned.data["status"] == "ASSIGNED"

        started = authenticated_client.post(
            f"/api/v1/repair-orders/{order_id}/start/",
            {},
            format="json",
        )
        assert started.status_code == 200, started.data
        assert started.data["status"] == "IN_PROGRESS"

        with_activity = authenticated_client.post(
            f"/api/v1/repair-orders/{order_id}/activities/",
            {
                "description": "Inspected engine bay",
                "labor_hours": "1.50",
            },
            format="json",
        )
        assert with_activity.status_code == 200, with_activity.data
        assert len(with_activity.data["activities"]) == 1
        activity_id = with_activity.data["activities"][0]["id"]

        edited_activity = authenticated_client.patch(
            f"/api/v1/repair-orders/{order_id}/activities/{activity_id}/",
            {
                "description": "Replaced alternator",
                "labor_hours": "3.00",
                "notes": "Bench tested",
            },
            format="json",
        )
        assert edited_activity.status_code == 200, edited_activity.data
        assert edited_activity.data["activities"][0]["description"] == "Replaced alternator"
        assert edited_activity.data["activities"][0]["labor_hours"] == "3.00"

        deleted_activity = authenticated_client.delete(
            f"/api/v1/repair-orders/{order_id}/activities/{activity_id}/",
            format="json",
        )
        assert deleted_activity.status_code == 200, deleted_activity.data
        assert deleted_activity.data["activities"] == []

        with_part = authenticated_client.post(
            f"/api/v1/repair-orders/{order_id}/parts/",
            {
                "material_number": "4000001",
                "quantity": 2,
                "unit_of_measure": "EA",
            },
            format="json",
        )
        assert with_part.status_code == 200, with_part.data
        assert len(with_part.data["parts"]) == 1

        completed = authenticated_client.post(
            f"/api/v1/repair-orders/{order_id}/complete/",
            {
                "completed_at": datetime.now(tz=UTC).isoformat(),
            },
            format="json",
        )
        assert completed.status_code == 200, completed.data
        assert completed.data["status"] == "WAITING_DRIVER_CONFIRMATION"

        listed = authenticated_client.get(
            f"/api/v1/repair-orders/?vehicle_id={vehicle['id']}"
        )
        assert listed.status_code == 200
        assert listed.data["count"] >= 1
