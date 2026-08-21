"""Unit tests for fault catalog OData adapter."""

from __future__ import annotations

from infrastructure.sap.adapters.odata.fault_catalog_odata_adapter import (
    FaultCatalogODataAdapter,
)
from infrastructure.sap.client.mock.mock_client import MockSAPClient, SAPMockScenario


class TestFaultCatalogODataAdapter:
    """Cover XML-backed SAP fault catalog reads.

    The adapter reads SAP's real defect catalog ``ZI_B_DEFECTCATALOG9_CDS``
    — the faults a part can have, carrying DefectClass/severity — for both
    manual fault reporting and the daily-inspection fault-type picker.
    """

    def test_defaults_to_the_real_defect_catalog_not_the_part_catalog(self) -> None:
        """Regression: defaulting to ZI_FLEET_CAT_B_CDS listed parts, not faults.

        That view names the parts themselves ("ترمز جلو") and has no
        DefectClass column, so every reported fault silently fell back to
        LOW severity and drivers never saw the real defect list.
        """
        adapter = FaultCatalogODataAdapter(MockSAPClient(scenario=SAPMockScenario.SUCCESS))

        result = adapter.list_defect_codes()

        code_texts = {item.code_text for item in result}
        assert "ترمز ضعیف" in code_texts
        assert "ترمز جلو" not in code_texts
        assert all(item.defect_class for item in result)

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
