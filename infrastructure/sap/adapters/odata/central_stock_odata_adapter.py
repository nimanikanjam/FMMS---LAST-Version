"""Central warehouse stock OData adapter — implements ISAPCentralStockPort.

Reads stock from SAP CDS ``ZI_STOCK_KH08_CDS`` (storage location KH08).
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from decimal import Decimal, InvalidOperation
from typing import Any

from apps.integration.domain.exceptions import SAPIntegrationError
from core.sap.dtos.central_stock import SAPCentralStockDTO
from core.sap.ports.central_stock_port import ISAPCentralStockPort
from infrastructure.sap.client.base import ISAPClient, SAPClientError

logger = logging.getLogger(__name__)

_SERVICE = "ZI_STOCK_KH08_CDS"
_DEFAULT_ENTITY_SET = ""


class CentralStockODataAdapter(ISAPCentralStockPort):
    """Reads central spare-parts warehouse stock via OData XML.

    Args:
        client: An ``ISAPClient`` instance.
        service: OData service name (default ``ZI_STOCK_KH08_CDS``).
        entity_set: Optional entity set path; empty for root feed.
    """

    def __init__(
        self,
        client: ISAPClient,
        service: str = _SERVICE,
        entity_set: str = _DEFAULT_ENTITY_SET,
    ) -> None:
        self._client = client
        self._service = service
        self._entity_set = entity_set

    def list_stock(self) -> list[SAPCentralStockDTO]:
        """Retrieve all central warehouse stock rows.

        Returns:
            A list of ``SAPCentralStockDTO`` objects.

        Raises:
            SAPIntegrationError: On SAP error or transport failure.
        """
        logger.info(
            "Listing SAP central warehouse stock",
            extra={"service": self._service, "domain": "integration"},
        )
        try:
            xml_text = self._client.odata_get_xml(
                service=self._service,
                entity=self._entity_set,
            )
        except SAPClientError as exc:
            raise SAPIntegrationError(
                f"Failed to list central warehouse stock: {exc}"
            ) from exc

        rows = [self._map_single(item) for item in _parse_simple_table_xml(xml_text)]
        return _deduplicate_stock_rows(rows)

    @staticmethod
    def _map_single(data: dict[str, Any]) -> SAPCentralStockDTO:
        """Map a raw SAP stock record to ``SAPCentralStockDTO``."""
        material = _normalize_material(str(data.get("Material", "")).strip())
        material_code = str(data.get("MaterialCode", "")).strip()
        return SAPCentralStockDTO(
            material=material,
            plant=str(data.get("Plant", "")).strip(),
            storage_location=str(data.get("StorageLocation", "")).strip(),
            inventory_stock_type=str(data.get("InventoryStockType", "")).strip(),
            material_code=material_code or (material.lstrip("0") or "0"),
            material_name=_material_name_from_row(data),
            inventory_stock_type_text=str(
                data.get("InventoryStockTypeText", "")
            ).strip(),
            quantity=_to_decimal(data.get("MatlWrhsStkQtyInMatlBaseUnit")),
            base_unit=str(data.get("MaterialBaseUnit", "")).strip(),
            stock_value=_to_decimal(data.get("StockValueInDisplayCurrency")),
            display_currency=str(data.get("DisplayCurrency", "")).strip(),
        )


def _normalize_material(raw: str) -> str:
    """Normalize numeric SAP material keys to their canonical 18 characters."""
    if raw.isdigit() and len(raw) <= 18:
        return raw.zfill(18)
    return raw


def _deduplicate_stock_rows(
    rows: list[SAPCentralStockDTO],
) -> list[SAPCentralStockDTO]:
    """Collapse CDS join duplicates to one preferred row per SAP key.

    The legacy sync already produced last-row-wins behavior because repeated
    keys were saved sequentially. Deduplicating here avoids redundant writes;
    when only valuation differs, the populated valuation is retained.
    """
    unique: dict[tuple[str, str, str, str], SAPCentralStockDTO] = {}
    for row in rows:
        key = (
            row.material,
            row.plant,
            row.storage_location,
            row.inventory_stock_type,
        )
        existing = unique.get(key)
        if existing is not None and existing != row:
            logger.warning(
                "Conflicting duplicate central-stock row; selecting preferred row",
                extra={
                    "material": row.material,
                    "plant": row.plant,
                    "storage_location": row.storage_location,
                    "inventory_stock_type": row.inventory_stock_type,
                    "domain": "integration",
                },
            )
            unique[key] = _prefer_duplicate(existing, row)
        else:
            unique[key] = row
    return list(unique.values())


def _prefer_duplicate(
    existing: SAPCentralStockDTO,
    incoming: SAPCentralStockDTO,
) -> SAPCentralStockDTO:
    """Keep a populated valuation when duplicate rows differ only by stock value."""
    if (
        existing.material == incoming.material
        and existing.plant == incoming.plant
        and existing.storage_location == incoming.storage_location
        and existing.inventory_stock_type == incoming.inventory_stock_type
        and existing.material_code == incoming.material_code
        and existing.material_name == incoming.material_name
        and existing.inventory_stock_type_text == incoming.inventory_stock_type_text
        and existing.quantity == incoming.quantity
        and existing.base_unit == incoming.base_unit
        and existing.display_currency == incoming.display_currency
    ):
        return max(
            (existing, incoming),
            key=lambda item: abs(item.stock_value),
        )
    return incoming


def _material_name_from_row(data: dict[str, Any]) -> str:
    """Extract material description from known SAP column aliases."""
    for key in (
        "MaterialName",
        "MaterialDescription",
        "ProductDescription",
        "MaterialText",
        "ProductDesc",
        "MaterialDesc",
    ):
        value = str(data.get(key, "")).strip()
        if value:
            return value
    return ""


def _to_decimal(raw: Any) -> Decimal:
    """Parse SAP numeric string to Decimal; invalid values become zero."""
    text = str(raw or "0").strip().replace(",", "")
    if not text:
        return Decimal("0")
    try:
        return Decimal(text)
    except InvalidOperation:
        return Decimal("0")


def _parse_simple_table_xml(xml_text: str) -> list[dict[str, str]]:
    """Parse legacy table XML or a standard OData v2 Atom feed.

    SAP's mock/export fixtures use ``Root/Columns/Rows`` while the live
    Gateway returns ``feed/entry/content/m:properties``. Supporting both
    formats keeps local fixtures backward-compatible with the real service.
    """
    root = ET.fromstring(xml_text)  # noqa: S314

    if _local_name(root.tag) == "feed":
        return _parse_atom_feed(root)

    columns = [
        str(column.attrib.get("Name", "")).strip()
        for column in root.findall("./Columns/Column")
    ]
    rows: list[dict[str, str]] = []
    for row in root.findall("./Rows/Row"):
        values = [value.text or "" for value in row.findall("./Value")]
        rows.append(
            {
                column: values[index].strip() if index < len(values) else ""
                for index, column in enumerate(columns)
                if column
            }
        )
    return rows


def _parse_atom_feed(root: ET.Element) -> list[dict[str, str]]:
    """Map OData Atom entries to property dictionaries."""
    rows: list[dict[str, str]] = []
    for entry in root.iter():
        if _local_name(entry.tag) != "entry":
            continue
        properties = next(
            (
                element
                for element in entry.iter()
                if _local_name(element.tag) == "properties"
            ),
            None,
        )
        if properties is None:
            continue
        rows.append(
            {
                _local_name(property_element.tag): (property_element.text or "").strip()
                for property_element in properties
            }
        )
    return rows


def _local_name(tag: str) -> str:
    """Return an XML tag without its namespace."""
    return tag.rsplit("}", 1)[-1]
