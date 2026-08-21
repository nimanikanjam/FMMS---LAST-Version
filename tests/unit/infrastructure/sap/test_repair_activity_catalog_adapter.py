"""Unit tests for the repair activity catalog OData adapter."""

from __future__ import annotations

import pytest

from apps.integration.domain.exceptions import SAPIntegrationError
from infrastructure.sap.adapters.odata.repair_activity_catalog_odata_adapter import (
    RepairActivityCatalogODataAdapter,
)
from infrastructure.sap.client.mock.mock_client import MockSAPClient, SAPMockScenario


class TestRepairActivityCatalogODataAdapter:
    """Cover XML-backed SAP activity catalog reads (ZC_REPAIR01_CODE_CDS)."""

    def test_reads_activity_catalog_from_xml_fixture(self) -> None:
        adapter = RepairActivityCatalogODataAdapter(
            MockSAPClient(scenario=SAPMockScenario.SUCCESS)
        )

        result = adapter.list_activities()

        assert len(result) == 10
        code_texts = {item.code_text for item in result}
        assert "تعويض روغن" in code_texts
        assert "آچارکشي" in code_texts
        # Catalog type "A" (activities) on every row.
        assert {item.catalog_type for item in result} == {"A"}
        assert {item.code_group for item in result} == {"REPAIR01"}

    def test_transport_error_is_wrapped(self) -> None:
        adapter = RepairActivityCatalogODataAdapter(
            MockSAPClient(scenario=SAPMockScenario.TRANSPORT_ERROR)
        )

        with pytest.raises(SAPIntegrationError):
            adapter.list_activities()
