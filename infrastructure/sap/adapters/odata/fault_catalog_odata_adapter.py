"""Fault catalog OData adapter — implements ISAPFaultCatalogPort."""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from typing import Any

from apps.integration.domain.exceptions import SAPIntegrationError
from core.sap.dtos.fault_catalog import SAPDefectCodeDTO
from core.sap.ports.fault_catalog_port import ISAPFaultCatalogPort
from infrastructure.sap.client.base import ISAPClient, SAPClientError

logger = logging.getLogger(__name__)

# Same CDS view manual fault reporting shares with the daily-inspection
# object-part catalog (see ObjectPartCatalogODataAdapter). It carries no
# DefectClass/DefectClassText columns, so those DTO fields come back empty.
_SERVICE = "ZI_FLEET_CAT_B_CDS"
_DEFAULT_ENTITY_SET = ""


class FaultCatalogODataAdapter(ISAPFaultCatalogPort):
    """Reads SAP fault/defect catalog rows via OData XML.

    Args:
        client: An ``ISAPClient`` instance.
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

    def list_defect_codes(self) -> list[SAPDefectCodeDTO]:
        """Retrieve defect codes.

        Returns:
            A list of ``SAPDefectCodeDTO`` objects.

        Raises:
            SAPIntegrationError: On SAP error or transport failure.
        """
        logger.info(
            "Listing SAP defect codes",
            extra={"service": self._service, "domain": "integration"},
        )
        try:
            xml_text = self._client.odata_get_xml(
                service=self._service,
                entity=self._entity_set,
            )
        except SAPClientError as exc:
            raise SAPIntegrationError(f"Failed to list defect codes: {exc}") from exc

        return [self._map_single(item) for item in _parse_simple_table_xml(xml_text)]

    def get_defect_code(
        self,
        code: str,
        code_group: str,
    ) -> SAPDefectCodeDTO:
        """Retrieve a single defect code from the SAP catalog.

        Args:
            code: The defect code identifier.
            code_group: SAP code group.

        Returns:
            A populated ``SAPDefectCodeDTO``.

        Raises:
            SAPIntegrationError: On SAP error or transport failure.
        """
        logger.info(
            "Fetching SAP defect code",
            extra={
                "code": code,
                "code_group": code_group,
                "domain": "integration",
            },
        )
        for item in self.list_defect_codes():
            if item.code == code and item.code_group == code_group:
                return item
        raise SAPIntegrationError(
            f"Defect code {code!r}/{code_group!r} was not found in SAP."
        )

    @staticmethod
    def _map_single(data: dict[str, Any]) -> SAPDefectCodeDTO:
        """Map a raw SAP defect code record to ``SAPDefectCodeDTO``."""
        return SAPDefectCodeDTO(
            code_group=str(data.get("CodeGroup", "")).strip(),
            code=str(data.get("Code", "")).strip(),
            group_text=str(data.get("GroupText", "")).strip(),
            code_text=str(data.get("CodeText", "")).strip(),
            defect_class=str(data.get("DefectClass", "")).strip(),
            defect_class_text=str(data.get("DefectClassText", "")).strip(),
        )


def _parse_simple_table_xml(xml_text: str) -> list[dict[str, str]]:
    """Parse SAP XML shaped as ``Root/Columns/Rows`` into dictionaries."""
    root = ET.fromstring(xml_text)  # noqa: S314
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
