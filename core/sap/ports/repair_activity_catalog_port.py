"""SAP Repair Activity Catalog Port — abstract contract for activity codes.

SAP maintains an activity catalog (catalog type ``A``) listing the standard
jobs a workshop performs. Technicians pick from it when recording the work
done on a repair order.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from core.sap.dtos.repair_activity_catalog import SAPRepairActivityDTO


class ISAPRepairActivityCatalogPort(ABC):
    """Business contract for reading repair activity codes from SAP.

    Implementations handle all transport, encoding, and SAP-specific details.
    """

    @abstractmethod
    def list_activities(self) -> list[SAPRepairActivityDTO]:
        """Retrieve every repair activity in the SAP catalog.

        Returns:
            A list of ``SAPRepairActivityDTO`` objects.

        Raises:
            SAPIntegrationError: If SAP returns an error response.
        """
