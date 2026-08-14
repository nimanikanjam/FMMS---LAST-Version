"""Unit tests for fault catalog OData adapter."""

from __future__ import annotations

from infrastructure.sap.adapters.odata.fault_catalog_odata_adapter import (
    FaultCatalogODataAdapter,
)
from infrastructure.sap.client.mock.mock_client import MockSAPClient, SAPMockScenario


class TestFaultCatalogODataAdapter:
    """Cover XML-backed SAP fault catalog reads.

    ``FaultCatalogODataAdapter``'s default service now points at the object-
    part catalog (manual fault reporting reuses that source — see
    ``sync_fault_catalog_from_sap_service``), which carries no DefectClass
    columns. The real defect catalog (with DefectClass/severity) is still
    read through this same adapter class, just with an explicit
    ``ZI_B_DEFECTCATALOG9_CDS`` service — the way
    ``sync_inspection_defect_options_from_sap_service`` uses it for the
    daily-inspection fault-type picker. These tests exercise that path.
    """

    def test_reads_fault_catalog_from_xml_fixture(self) -> None:
        client = MockSAPClient(scenario=SAPMockScenario.SUCCESS)
        adapter = FaultCatalogODataAdapter(client, service="ZI_B_DEFECTCATALOG9_CDS")

        result = adapter.list_defect_codes()

        assert len(result) >= 4
        code_texts = {item.code_text for item in result}
        assert "ترمز ضعیف" in code_texts
        assert "چراغ جلو معیوب" in code_texts
        assert {item.defect_class for item in result}
        assert {item.defect_class_text for item in result}

    def test_get_defect_code_by_code_and_group(self) -> None:
        client = MockSAPClient(scenario=SAPMockScenario.SUCCESS)
        adapter = FaultCatalogODataAdapter(client, service="ZI_B_DEFECTCATALOG9_CDS")

        result = adapter.get_defect_code("B001", "BRAKE-D")

        assert result.code_text == "ترمز ضعیف"
        assert result.defect_class == "S1"
