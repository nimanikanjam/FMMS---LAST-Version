# Database Design

## Database

Primary database: - PostgreSQL

## Design Principles

-   SAP master data separated from operational data
-   Auditability
-   Soft delete
-   UTC timestamps
-   Transaction consistency

## BaseModel

Common fields:

-   id
-   created_at
-   created_by
-   updated_at
-   updated_by
-   is_deleted
-   deleted_at
-   deleted_by

## Main Entities

### Vehicle

Stores operational vehicle information and SAP references.

### Inspection

Stores inspection results.

### Fault

Stores reported faults and diagnostic information.

### RepairOrder

Stores maintenance execution workflow.

### RepairActivity

Stores performed repair activities.

### RepairPart

Stores consumed parts.

### PreventiveMaintenance

Stores scheduled maintenance plans.

### SAPTransaction

Stores SAP integration tracking.

## Rules

-   No physical deletion of business records.
-   All important changes are audited.
-   Repositories separate persistence from business logic.
