"""Repair activity catalog OData adapter — implements ISAPRepairActivityCatalogPort."""

from __future__ import annotations

import logging
from typing import Any

from apps.integration.domain.exceptions import SAPIntegrationError
from core.sap.dtos.repair_activity_catalog import SAPRepairActivityDTO
from core.sap.ports.repair_activity_catalog_port import ISAPRepairActivityCatalogPort
from infrastructure.sap.adapters.odata.simple_table_xml import parse_simple_table_xml
from infrastructure.sap.client.base import ISAPClient, SAPClientError

logger = logging.getLogger(__name__)

# SAP's activity catalog (catalog type "A") — the standard jobs a workshop
# performs ("تعويض روغن"), picked when recording work on a repair order.
_SERVICE = "ZC_REPAIR01_CODE_CDS"
_DEFAULT_ENTITY_SET = ""


class RepairActivityCatalogODataAdapter(ISAPRepairActivityCatalogPort):
    """Reads SAP repair activity codes via OData XML.

    Args:
        client: An ``ISAPClient`` instance.
        service: OData service name.
        entity_set: OData entity set name.
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

    def list_activities(self) -> list[SAPRepairActivityDTO]:
        """Retrieve every repair activity in the SAP catalog.

        Returns:
            A list of ``SAPRepairActivityDTO`` objects.

        Raises:
            SAPIntegrationError: On SAP error or transport failure.
        """
        logger.info(
            "Listing SAP repair activities",
            extra={"service": self._service, "domain": "integration"},
        )
        try:
            xml_text = self._client.odata_get_xml(
                service=self._service,
                entity=self._entity_set,
            )
        except SAPClientError as exc:
            raise SAPIntegrationError(
                f"Failed to list repair activities: {exc}"
            ) from exc

        return [self._map_single(item) for item in parse_simple_table_xml(xml_text)]

    @staticmethod
    def _map_single(data: dict[str, Any]) -> SAPRepairActivityDTO:
        """Map a raw SAP activity record to ``SAPRepairActivityDTO``."""
        return SAPRepairActivityDTO(
            catalog_type=str(data.get("CatalogType", "")).strip(),
            code_group=str(data.get("CodeGroup", "")).strip(),
            code=str(data.get("Code", "")).strip(),
            code_text=str(data.get("CodeText", "")).strip(),
        )
