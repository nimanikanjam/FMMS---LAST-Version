# API Contract

## API Principles

-   REST based APIs
-   Versioned endpoints
-   Standard request/response format
-   Validation
-   Error handling
-   Documentation

## API Layers

Controller \| Service \| Repository \| Database

## Rules

-   Controllers must not contain business logic.
-   Database models must not be exposed directly.
-   Use DTOs / Schemas.
-   All APIs require validation.

## Error Response

Standard format:

-   error_code
-   message
-   details
-   request_id

## Security

Required:

-   Authentication
-   Authorization
-   Audit logging

## Documentation

All endpoints must have:

-   Description
-   Request schema
-   Response schema
-   Error cases
-   Examples
