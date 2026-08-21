"""Fault catalog OData adapter — implements ISAPFaultCatalogPort."""

from __future__ import annotations

import logging
from typing import Any

from apps.integration.domain.exceptions import SAPIntegrationError
from core.sap.dtos.fault_catalog import SAPDefectCodeDTO
from core.sap.ports.fault_catalog_port import ISAPFaultCatalogPort
from infrastructure.sap.adapters.odata.simple_table_xml import (
    parse_simple_table_xml,
)
from infrastructure.sap.client.base import ISAPClient, SAPClientError

logger = logging.getLogger(__name__)

# SAP's real defect catalog: the faults a part can have ("ترمز ضعیف"),
# with DefectClass/DefectClassText driving severity. Distinct from the
# object-part catalog (see ObjectPartCatalogODataAdapter), which lists the
# parts themselves ("ترمز جلو") and carries no DefectClass columns.
_SERVICE = "ZI_B_DEFECTCATALOG9_CDS"
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

        return [self._map_single(item) for item in parse_simple_table_xml(xml_text)]

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
