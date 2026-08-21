"""Shared XML parsing for SAP OData reads that return a flat table.

Several SAP CDS views are consumed as raw XML rather than JSON. They arrive
in one of two shapes depending on where the response comes from:

* ``Root/Columns/Rows`` — the shape of the captured fixtures under
  ``docs/odata/`` and of SAP's own table exports.
* ``feed/entry/content/m:properties`` — a standard OData v2 Atom feed, what
  the live SAP Gateway actually returns.

Both are mapped to the same ``list[dict[str, str]]`` so adapters can share
one row-mapping path and local fixtures stay interchangeable with the real
service.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET


def parse_simple_table_xml(xml_text: str) -> list[dict[str, str]]:
    """Parse legacy table XML or a standard OData v2 Atom feed.

    Args:
        xml_text: Raw XML returned by SAP.

    Returns:
        One dictionary per row, keyed by column/property name.
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
