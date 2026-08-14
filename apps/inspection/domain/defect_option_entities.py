"""Domain entity for SAP defect-catalog rows offered during daily inspection.

Distinct from ``apps.fault.domain.catalog_entities.FaultCatalog`` (which is
synced from the object-part catalog for manual fault reporting) — this one
is synced from SAP's real defect catalog (``ZI_B_DEFECTCATALOG9_CDS``) so a
driver can pick a proper fault type, with severity, while failing a checklist
item during daily inspection.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass
class InspectionDefectOption:
    """Local cache of one SAP defect-catalog row.

    Attributes:
        id: Universally unique identifier for this row.
        code_group: SAP ``CodeGroup``.
        code: SAP ``Code``.
        group_text: SAP ``GroupText`` — matched against a checklist item's
            category (object-part catalog group text) where possible.
        code_text: SAP ``CodeText`` — the fault type label shown to drivers.
        defect_class: SAP ``DefectClass`` — maps to fault severity.
        defect_class_text: SAP ``DefectClassText``.
        is_active: Whether the option is offered to drivers.
        created_at: UTC timestamp when the local row was created.
        updated_at: UTC timestamp of the last sync update.
    """

    id: uuid.UUID
    code_group: str
    code: str
    group_text: str
    code_text: str
    defect_class: str
    defect_class_text: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
