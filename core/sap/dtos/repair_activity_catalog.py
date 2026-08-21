"""SAP Repair Activity Catalog DTOs.

Represents SAP's activity catalog (catalog type ``A``) — the standard list
of jobs a workshop can perform, recorded against a repair order.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SAPRepairActivityDTO:
    """A single repair activity entry from the SAP catalog.

    Attributes:
        catalog_type: SAP ``CatalogType`` (``A`` for activities).
        code_group: SAP ``CodeGroup``.
        code: SAP ``Code``.
        code_text: SAP ``CodeText`` — the activity label shown to technicians.
    """

    catalog_type: str
    code_group: str
    code: str
    code_text: str
