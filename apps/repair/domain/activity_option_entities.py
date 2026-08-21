"""Domain entity for SAP activity-catalog rows offered when recording repairs.

Synced from SAP's activity catalog (``ZC_REPAIR01_CODE_CDS``, catalog type
``A``) so a technician records the work done by picking a standard SAP job
code rather than typing free text.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass
class RepairActivityOption:
    """Local cache of one SAP activity-catalog row.

    Attributes:
        id: Universally unique identifier for this row.
        catalog_type: SAP ``CatalogType`` (``A`` for activities).
        code_group: SAP ``CodeGroup``.
        code: SAP ``Code``.
        code_text: SAP ``CodeText`` — the activity label shown to technicians.
        is_active: Whether the option is offered when recording work.
        created_at: UTC timestamp when the local row was created.
        updated_at: UTC timestamp of the last sync update.
    """

    id: uuid.UUID
    catalog_type: str
    code_group: str
    code: str
    code_text: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
