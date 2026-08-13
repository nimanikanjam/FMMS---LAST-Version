# FMMS Architecture

## Overview

Fleet Maintenance Management System (FMMS) is an enterprise maintenance
platform acting as an operational layer between users and SAP.

## Architecture Principles

-   Clean Architecture
-   Domain separation
-   Service Layer
-   Separation of business logic and infrastructure
-   SAP integration through adapters

## Main Layers

### Interface Layer

Responsible for: - REST APIs - Request validation - Authentication -
Serialization

### Application / Service Layer

Responsible for: - Business workflows - Use Cases - Domain orchestration

### Domain Layer

Responsible for: - Entities - Business rules - Domain exceptions

### Infrastructure Layer

Responsible for: - Database access - SAP adapters - External
integrations - Storage - Messaging

## Core Domains

-   Vehicle Management
-   Driver Management
-   Inspection
-   Fault Management
-   Repair Management
-   Preventive Maintenance
-   Procurement
-   Integration
-   Reporting

## Coding Rules

-   SOLID principles
-   SRP
-   Dependency inversion
-   Type hinting
-   Docstrings
-   Structured logging
