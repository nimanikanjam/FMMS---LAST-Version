"""API integration tests for the daily-inspection defect-catalog options endpoint."""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from tests.factories.user_factory import FMMSUserFactory

pytestmark = pytest.mark.django_db


class TestInspectionDefectOptionsAPI:
    """Cover listing fault-type options for the daily-inspection fail step."""

    def test_driver_can_list_defect_options_after_sync(
        self, authenticated_client: APIClient
    ) -> None:
        """A synced defect catalog is readable by DRIVER, with category filtering."""
        synced = authenticated_client.post("/api/v1/sap-sync/", {}, format="json")
        assert synced.status_code == 200, synced.data

        driver = FMMSUserFactory(role="DRIVER", password="testpass123!")
        client = APIClient()
        client.force_authenticate(user=driver)

        response = client.get("/api/v1/inspection-defect-options/")
        assert response.status_code == 200, response.data
        results = response.data.get("results", response.data)
        assert len(results) > 0
        first = results[0]
        assert {"code", "code_group", "group_text", "code_text", "defect_class"} <= set(
            first.keys()
        )

        filtered = client.get(
            "/api/v1/inspection-defect-options/",
            {"category": "سیستم ترمز"},
        )
        assert filtered.status_code == 200, filtered.data
        filtered_results = filtered.data.get("results", filtered.data)
        assert len(filtered_results) > 0
        assert all(row["group_text"] == "سیستم ترمز" for row in filtered_results)

    def test_viewer_cannot_see_defect_options_when_none_synced(
        self, viewer_client: APIClient
    ) -> None:
        """No sync has run yet: the endpoint still responds 200 with an empty list."""
        response = viewer_client.get("/api/v1/inspection-defect-options/")
        assert response.status_code == 200, response.data
        results = response.data.get("results", response.data)
        assert results == []
