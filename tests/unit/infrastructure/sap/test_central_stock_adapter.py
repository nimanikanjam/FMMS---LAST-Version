"""Unit tests for central warehouse stock OData adapter."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

from infrastructure.sap.adapters.odata.central_stock_odata_adapter import (
    CentralStockODataAdapter,
)
from infrastructure.sap.client.base import ISAPClient
from infrastructure.sap.client.mock.mock_client import MockSAPClient, SAPMockScenario

_ATOM_STOCK_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:d="http://schemas.microsoft.com/ado/2007/08/dataservices"
      xmlns:m="http://schemas.microsoft.com/ado/2007/08/dataservices/metadata">
  <entry>
    <content type="application/xml">
      <m:properties>
        <d:Material>000000000060001764</d:Material>
        <d:Plant>1000</d:Plant>
        <d:StorageLocation>KH08</d:StorageLocation>
        <d:InventoryStockType>01</d:InventoryStockType>
        <d:MaterialCode>60001764</d:MaterialCode>
        <d:MaterialDescription>روغن موتور 40</d:MaterialDescription>
        <d:InventoryStockTypeText>Unrestricted-Use Stock</d:InventoryStockTypeText>
        <d:MatlWrhsStkQtyInMatlBaseUnit>149.500</d:MatlWrhsStkQtyInMatlBaseUnit>
        <d:MaterialBaseUnit>L</d:MaterialBaseUnit>
        <d:StockValueInDisplayCurrency>0</d:StockValueInDisplayCurrency>
        <d:DisplayCurrency>IRR</d:DisplayCurrency>
      </m:properties>
    </content>
  </entry>
  <entry>
    <content type="application/xml">
      <m:properties>
        <d:Material>000000000060001765</d:Material>
        <d:Plant>1000</d:Plant>
        <d:StorageLocation>KH08</d:StorageLocation>
        <d:InventoryStockType>01</d:InventoryStockType>
        <d:MaterialCode>60001765</d:MaterialCode>
        <d:MaterialDescription m:null="true" />
        <d:InventoryStockTypeText>Unrestricted-Use Stock</d:InventoryStockTypeText>
        <d:MatlWrhsStkQtyInMatlBaseUnit>11</d:MatlWrhsStkQtyInMatlBaseUnit>
        <d:MaterialBaseUnit>EA</d:MaterialBaseUnit>
        <d:StockValueInDisplayCurrency>0</d:StockValueInDisplayCurrency>
        <d:DisplayCurrency>IRR</d:DisplayCurrency>
      </m:properties>
    </content>
  </entry>
</feed>
"""

_ATOM_DUPLICATE_STOCK_XML = _ATOM_STOCK_XML.replace(
    "</feed>",
    """
  <entry>
    <content type="application/xml">
      <m:properties>
        <d:Material>60001764</d:Material>
        <d:Plant>1000</d:Plant>
        <d:StorageLocation>KH08</d:StorageLocation>
        <d:InventoryStockType>01</d:InventoryStockType>
        <d:MaterialCode>60001764</d:MaterialCode>
        <d:MaterialDescription>روغن موتور 40</d:MaterialDescription>
        <d:InventoryStockTypeText>Unrestricted-Use Stock</d:InventoryStockTypeText>
        <d:MatlWrhsStkQtyInMatlBaseUnit>149.500</d:MatlWrhsStkQtyInMatlBaseUnit>
        <d:MaterialBaseUnit>L</d:MaterialBaseUnit>
        <d:StockValueInDisplayCurrency>3225552.20</d:StockValueInDisplayCurrency>
        <d:DisplayCurrency>IRR</d:DisplayCurrency>
      </m:properties>
    </content>
  </entry>
</feed>
""",
)


class TestCentralStockODataAdapter:
    """Cover XML-backed SAP central stock reads."""

    def test_reads_central_stock_from_xml_fixture(self) -> None:
        client = MockSAPClient(scenario=SAPMockScenario.SUCCESS)
        adapter = CentralStockODataAdapter(client)

        result = adapter.list_stock()

        assert len(result) >= 10
        first = result[0]
        assert first.material == "000000000060001764"
        assert first.plant == "1000"
        assert first.storage_location == "KH08"
        assert first.inventory_stock_type == "01"
        assert first.material_code == "60001764"
        # Fixture XML has no MaterialName/Description column.
        assert first.material_name == ""
        assert first.quantity == Decimal("149.500")
        assert first.base_unit == "L"
        assert first.display_currency == "IRR"
        assert {row.storage_location for row in result} == {"KH08"}

    def test_reads_material_description_from_live_atom_format(self) -> None:
        client = MagicMock(spec=ISAPClient)
        client.odata_get_xml.return_value = _ATOM_STOCK_XML
        adapter = CentralStockODataAdapter(client)

        result = adapter.list_stock()

        assert len(result) == 2
        assert result[0].material_code == "60001764"
        assert result[0].material == "000000000060001764"
        assert result[0].material_name == "روغن موتور 40"
        assert result[0].quantity == Decimal("149.500")
        assert result[1].material_name == ""
        assert result[1].quantity == Decimal("11")
        client.odata_get_xml.assert_called_once_with(
            service="ZI_STOCK_KH08_CDS",
            entity="",
        )

    def test_deduplicates_identical_atom_rows_after_material_normalization(
        self,
    ) -> None:
        client = MagicMock(spec=ISAPClient)
        client.odata_get_xml.return_value = _ATOM_DUPLICATE_STOCK_XML

        result = CentralStockODataAdapter(client).list_stock()

        assert len(result) == 2
        normalized = next(row for row in result if row.material == "000000000060001764")
        assert normalized.stock_value == Decimal("3225552.20")

    def test_conflicting_duplicate_atom_rows_preserve_last_row_wins(self) -> None:
        client = MagicMock(spec=ISAPClient)
        client.odata_get_xml.return_value = _ATOM_DUPLICATE_STOCK_XML.replace(
            "<d:MatlWrhsStkQtyInMatlBaseUnit>149.500</d:MatlWrhsStkQtyInMatlBaseUnit>",
            "<d:MatlWrhsStkQtyInMatlBaseUnit>999</d:MatlWrhsStkQtyInMatlBaseUnit>",
            1,
        )

        result = CentralStockODataAdapter(client).list_stock()

        normalized = next(row for row in result if row.material == "000000000060001764")
        assert normalized.quantity == Decimal("149.500")
