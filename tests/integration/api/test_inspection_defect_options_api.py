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
        """A synced defect catalog is readable by DRIVER, whole and self-grouped."""
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

        # The defect catalog keeps its own grouping (unrelated to the checklist
        # catalog's), so the whole catalog comes back — several distinct groups,
        # including ones with no checklist counterpart.
        full = client.get("/api/v1/inspection-defect-options/", {"page_size": 100})
        assert full.status_code == 200, full.data
        rows = full.data.get("results", full.data)
        groups = {row["group_text"] for row in rows}
        assert len(groups) > 1
        assert "سیستم ترمز" in groups
        assert "لاستیک و چرخ" in groups
        # Ordered by the catalog's own group text, so the UI can group by it.
        assert [r["group_text"] for r in rows] == sorted(r["group_text"] for r in rows)

    def test_viewer_cannot_see_defect_options_when_none_synced(
        self, viewer_client: APIClient
    ) -> None:
        """No sync has run yet: the endpoint still responds 200 with an empty list."""
        response = viewer_client.get("/api/v1/inspection-defect-options/")
        assert response.status_code == 200, response.data
        results = response.data.get("results", response.data)
        assert results == []
