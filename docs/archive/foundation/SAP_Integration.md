# SAP Integration

## Integration Objective

FMMS integrates with SAP while keeping internal domains independent from
SAP implementation details.

## Ownership

SAP owns: - Equipment - Material - Inventory - Vendor - Fault Catalog

FMMS owns: - Maintenance workflow - Repair execution - Inspection
process - Operational data

## Read Integration

SAP to FMMS:

-   Equipment
-   Object Part Catalog
-   Fault Catalog
-   Material Master
-   Inventory

Main APIs / CDS services:

-   API_EQUIPMENT
-   API_DEFECTCODE_SRV
-   API_PRODUCT_SRV
-   API_MATERIAL_STOCK_SRV
-   ZI_STOCK_KH08_CDS (central spare-parts warehouse stock, SLoc KH08)

## Write Integration

FMMS to SAP:

-   PM Notification
-   PM Order
-   Purchase Requisition
-   Purchase Order
-   Goods Receipt
-   Goods Issue
-   Service PO

## SAPTransaction

All SAP writes must create SAPTransaction records.

Responsibilities:

-   Tracking
-   Idempotency
-   Retry
-   Error handling
-   Audit

Required fields:

-   business_object_type
-   business_object_id
-   sap_document_number
-   idempotency_key
-   request_payload
-   response_payload
-   status

## Integration Architecture

Domain Service \| SAP Interface \| SAP Adapter \| BAPI / OData / RFC \|
SAP
