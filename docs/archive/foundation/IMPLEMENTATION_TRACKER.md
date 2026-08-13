# FMMS Implementation Tracker

> Single source of truth for all development progress.
> This file must be updated after every completed milestone — no exceptions.

---

## Project Status

| Field                   | Value                                                              |
|-------------------------|--------------------------------------------------------------------|
| **Current Phase**       | Implementation — Phase 1                                           |
| **Current Milestone**   | Demo Backend Workflow Prep (Complete)                              |
| **Last Commit**         | `d0a5ecd` — feat(demo): prepare backend workflow APIs for FMMS demonstration |
| **Completed**           | M0 ✓ … M9 ✓ + demo backend workflow APIs                           |
| **In Progress**         | — (demo-frontend deferred until backend APIs approved)             |
| **Blocked**             | —                                                                  |
| **Last Updated**        | 2026-07-10                                                         |
| **Validation Status**   | 593/593 tests; black/isort/ruff PASS; mypy on changed modules PASS |

---

## Development Rules

Every milestone must follow this exact sequence. No step may be skipped.

1. **Explain** the milestone goal before writing any code.
2. **List** all required tasks for that milestone.
3. **Implement** only that milestone — no scope creep.
4. **Run tests** — all must pass before committing.
5. **Run code quality checks** — `black`, `isort`, `ruff`, `mypy` must all pass.
6. **Create Git commit** using the prescribed commit message.
7. **Update this file** — mark tasks complete, update Project Status table.

> **Never start the next milestone without completing and committing the previous one.**
> **Every Git commit must represent one logical change.**

---

## Scope Boundaries

| Scope    | Domains                                                                 |
|----------|-------------------------------------------------------------------------|
| Phase 1  | Vehicle, Driver, Inspection, Fault, Repair, PM, Procurement, Integration |
| Phase 2  | Reporting (deferred — no ORM model, no API, no services in Phase 1)     |

> Reporting domain entities are defined in M2 as a boundary placeholder only.
> Full implementation is deferred to Phase 2 unless explicitly required by a Phase 1 feature.

---

## Milestones

---

### Milestone 1 — Project Foundation

| Field         | Value                                                       |
|---------------|-------------------------------------------------------------|
| **Status**    | `Complete ✓`                                                |
| **Branch**    | `feat/milestone-1-foundation`                               |
| **Commit**    | `feat(core): initialize project foundation and configuration` |
| **Started**   | 2026-07-09                                                  |
| **Completed** | 2026-07-09                                                  |

**Goal:**
Establish a working, runnable Django project skeleton with environment-aware configuration,
custom User model, structured logging, core exception hierarchy, base database model,
tool configuration (`pyproject.toml`), test infrastructure baseline, and full local
development environment (Docker, Makefile). No business features — infrastructure only.

**Tasks:**

**Project Layout**
- [ ] Create top-level directory structure: `config/`, `core/`, `apps/`, `infrastructure/`, `interfaces/`, `tests/`
- [ ] Create `manage.py`
- [ ] Initialize Django project under `config/`

**Dependency Management**
- [ ] Create `requirements/base.txt` — Django, DRF, psycopg2, redis, celery, django-environ, Pillow, gunicorn
- [ ] Create `requirements/development.txt` — black, isort, ruff, mypy, pytest, pytest-django, factory-boy, django-debug-toolbar, coverage
- [ ] Create `requirements/staging.txt`
- [ ] Create `requirements/production.txt` — sentry-sdk, gunicorn

**Tool Configuration**
- [ ] Create `pyproject.toml` with sections:
  - `[tool.black]` — line-length = 88
  - `[tool.isort]` — profile = "black", known_first_party = ["apps", "core", "infrastructure", "interfaces"]
  - `[tool.ruff]` — rule sets, ignored rules, per-file ignores
  - `[tool.mypy]` — strict = true, ignore_missing_imports for third-party stubs
  - `[tool.pytest.ini_options]` — testpaths, markers, django_settings_module
  - `[tool.coverage.run]` — source, omit patterns
  - `[tool.coverage.report]` — fail_under = 80

**Settings Hierarchy**
- [ ] Create `config/settings/__init__.py`
- [ ] Create `config/settings/base.py` — INSTALLED_APPS, DATABASES, CACHES, REST_FRAMEWORK, MIDDLEWARE, LOGGING, AUTH_USER_MODEL
- [ ] Create `config/settings/development.py` — DEBUG=True, django-debug-toolbar, verbose logging
- [ ] Create `config/settings/staging.py`
- [ ] Create `config/settings/production.py` — security headers, SECURE_SSL_REDIRECT, HSTS
- [ ] Configure `DJANGO_SETTINGS_MODULE` to be loaded from environment via django-environ
- [ ] Create `.env.example` with all required variables fully documented

**Environment Configuration**
- [ ] Install and configure `django-environ` for `.env` file loading in `base.py`
- [ ] Document all required env vars in `.env.example`:
  - `DJANGO_SETTINGS_MODULE`
  - `SECRET_KEY`
  - `DATABASE_URL`
  - `REDIS_URL`
  - `CELERY_BROKER_URL`
  - `SAP_HOST`, `SAP_CLIENT`, `SAP_USER`, `SAP_PASSWORD`, `SAP_SYSTEM_ID`
  - `LOG_LEVEL`
  - `ALLOWED_HOSTS`
  - `CORS_ALLOWED_ORIGINS`
  - `SENTRY_DSN` (empty in development)

**Custom User Model (CRITICAL — must precede first migration)**
- [ ] Create `apps/authentication/` Django app
- [ ] Create `apps/authentication/__init__.py`
- [ ] Create `apps/authentication/apps.py` — AppConfig: name=`apps.authentication`, label=`authentication`
- [ ] Create `apps/authentication/infrastructure/models.py` — `FMMSUser(AbstractBaseUser)` with fields:
  - `id` (UUID primary key)
  - `email` (unique, login identifier)
  - `full_name`
  - `role` (choices: ADMIN, SUPERVISOR, TECHNICIAN, VIEWER)
  - `is_active`, `is_staff`, `is_superuser`
  - `created_at`, `updated_at`
- [ ] Create `apps/authentication/infrastructure/managers.py` — `FMMSUserManager`
- [ ] Set `AUTH_USER_MODEL = 'authentication.FMMSUser'` in `config/settings/base.py`
- [ ] Register `apps.authentication` in `INSTALLED_APPS`

**Core Infrastructure**
- [ ] Create `infrastructure/database/base_model.py` — abstract `BaseModel`:
  - `id` (UUID, primary key, auto-generated)
  - `created_at` (DateTimeField, auto_now_add, UTC)
  - `created_by` (ForeignKey to `settings.AUTH_USER_MODEL`, nullable, SET_NULL)
  - `updated_at` (DateTimeField, auto_now, UTC)
  - `updated_by` (ForeignKey to `settings.AUTH_USER_MODEL`, nullable, SET_NULL)
  - `is_deleted` (BooleanField, default=False, db_index=True)
  - `deleted_at` (DateTimeField, nullable)
  - `deleted_by` (ForeignKey to `settings.AUTH_USER_MODEL`, nullable, SET_NULL)
  - `class Meta: abstract = True`

**Structured Logging**
- [ ] Create `core/logging/__init__.py`
- [ ] Create `core/logging/structured_logger.py` — `get_structured_logger(domain, module)` factory
- [ ] Create `core/logging/formatters.py` — JSON formatter with mandatory fields:
  `timestamp`, `level`, `service=fmms`, `domain`, `module`, `request_id`, `user_id`, `message`, `exception`
- [ ] Configure `LOGGING` dict in `config/settings/base.py` using the custom formatter
- [ ] Valid `domain` values: `vehicle`, `driver`, `inspection`, `fault`, `repair`, `pm`, `procurement`, `integration`, `authentication`, `security`, `core`

**Core Exceptions**
- [ ] Create `core/exceptions/__init__.py`
- [ ] Create `core/exceptions/base_exception.py` — `FMMSBaseException`, `FMMSValidationError`, `FMMSNotFoundError`, `FMMSPermissionError`, `FMMSConflictError`
- [ ] Create `core/exceptions/http_exception_handler.py` — DRF custom handler mapping domain exceptions to standard HTTP error response:
  `{ "error_code": ..., "message": ..., "details": ..., "request_id": ... }`

**Middleware (wired in M1 settings)**
- [ ] Create `core/middleware/__init__.py`
- [ ] Create `core/middleware/request_id.py` — generates/propagates `X-Request-ID` on every request
- [ ] Create `core/middleware/audit_log.py` — logs all POST/PUT/PATCH/DELETE requests with user, path, status
- [ ] Add both to `MIDDLEWARE` in `config/settings/base.py` (not deferred to later milestones)

**Docker & Developer Environment**
- [ ] Create `Dockerfile` (Python 3.12 slim, non-root user)
- [ ] Create `docker-compose.yml` with services: `db` (PostgreSQL 16), `redis` (Redis 7), `app` (Django)
- [ ] Create `Makefile` with targets:
  - `make run` — start docker-compose
  - `make test` — run pytest with coverage
  - `make lint` — run black check + isort check + ruff + mypy
  - `make format` — run black + isort
  - `make migrate` — run Django migrations
  - `make shell` — Django shell
  - `make createsuperuser`
- [ ] Create `.gitignore` (Python, Django, env files, IDE files)

**Test Infrastructure Baseline**
- [ ] Create `tests/__init__.py`
- [ ] Create `tests/conftest.py` — `django_db` marker, `api_client` fixture, `authenticated_client` fixture, `admin_user` fixture
- [ ] Create `tests/unit/__init__.py`
- [ ] Create `tests/integration/__init__.py`
- [ ] Create `tests/factories/__init__.py`
- [ ] Create `tests/factories/user_factory.py` — `FMMSUserFactory` (factory_boy + django)

**Verification**
- [ ] Run `python manage.py check` — zero errors
- [ ] Run `python manage.py migrate` — applies `authentication` initial migration cleanly
- [ ] Run `pytest` — baseline suite passes (no tests yet = pass)
- [ ] Run `black --check .` — zero violations
- [ ] Run `isort --check .` — zero violations
- [ ] Run `ruff check .` — zero violations
- [ ] Run `mypy .` — zero errors

---

### Milestone 2 — Domain Layer

| Field         | Value                                                      |
|---------------|------------------------------------------------------------|
| **Status**    | `Complete ✓`                                               |
| **Branch**    | `feat/milestone-2-domain` → merged to `main`               |
| **Commit**    | `85b6d28` feat(domain): define domain entities and repository interfaces |
| **Started**   | 2026-07-09                                                 |
| **Completed** | 2026-07-09                                                 |

**Goal:**
Define all Phase 1 domain boundaries in pure Python. Zero Django or ORM dependency
allowed in this layer. Every entity, value object, domain exception, and abstract
repository interface is established here. This layer is the heart of the system.
Reporting domain is defined as a boundary placeholder only (Phase 2).

**Tasks:**

**Django App Scaffolding (required before any domain code)**
- [ ] Create `apps/__init__.py`
- [ ] Create `apps/vehicle/__init__.py` and `apps/vehicle/apps.py` (AppConfig: label=`vehicle`)
- [ ] Create `apps/driver/__init__.py` and `apps/driver/apps.py` (AppConfig: label=`driver`)
- [ ] Create `apps/inspection/__init__.py` and `apps/inspection/apps.py` (AppConfig: label=`inspection`)
- [ ] Create `apps/fault/__init__.py` and `apps/fault/apps.py` (AppConfig: label=`fault`)
- [ ] Create `apps/repair/__init__.py` and `apps/repair/apps.py` (AppConfig: label=`repair`)
- [ ] Create `apps/preventive_maintenance/__init__.py` and `apps/preventive_maintenance/apps.py` (AppConfig: label=`preventive_maintenance`)
- [ ] Create `apps/procurement/__init__.py` and `apps/procurement/apps.py` (AppConfig: label=`procurement`)
- [ ] Create `apps/integration/__init__.py` and `apps/integration/apps.py` (AppConfig: label=`integration`)
- [ ] Create `apps/reporting/__init__.py` and `apps/reporting/apps.py` (AppConfig: label=`reporting`) — boundary placeholder

**Vehicle Domain**
- [ ] Create `apps/vehicle/domain/__init__.py`
- [ ] Create `apps/vehicle/domain/entities.py` — `Vehicle`, `VehicleStatus` (enum: ACTIVE, INACTIVE, UNDER_REPAIR, DECOMMISSIONED)
- [ ] Create `apps/vehicle/domain/value_objects.py` — `PlateNumber`, `VIN`, `ChassisNumber`, `SAPEquipmentNumber`
- [ ] Create `apps/vehicle/domain/exceptions.py` — `VehicleNotFoundError`, `VehicleInactiveError`, `VehicleAlreadyExistsError`
- [ ] Create `apps/vehicle/domain/interfaces/__init__.py`
- [ ] Create `apps/vehicle/domain/interfaces/vehicle_repository.py` — `IVehicleRepository` (ABC)

**Driver Domain**
- [ ] Create `apps/driver/domain/__init__.py`
- [ ] Create `apps/driver/domain/entities.py` — `Driver`, `DriverStatus` (enum: ACTIVE, SUSPENDED, TERMINATED)
- [ ] Create `apps/driver/domain/value_objects.py` — `LicenseNumber`, `LicenseClass`, `DriverContact`
- [ ] Create `apps/driver/domain/exceptions.py` — `DriverNotFoundError`, `DriverSuspendedError`, `DriverAlreadyAssignedError`
- [ ] Create `apps/driver/domain/interfaces/__init__.py`
- [ ] Create `apps/driver/domain/interfaces/driver_repository.py` — `IDriverRepository` (ABC)

**Inspection Domain**
- [ ] Create `apps/inspection/domain/__init__.py`
- [ ] Create `apps/inspection/domain/entities.py` — `Inspection`, `InspectionItem`, `InspectionStatus` (enum: DRAFT, SUBMITTED, APPROVED, REJECTED)
- [ ] Create `apps/inspection/domain/value_objects.py` — `OdometerReading`, `ChecklistResult`, `InspectionScore`
- [ ] Create `apps/inspection/domain/exceptions.py` — `InspectionNotFoundError`, `InspectionAlreadySubmittedError`, `InspectionItemRequiredError`
- [ ] Create `apps/inspection/domain/interfaces/__init__.py`
- [ ] Create `apps/inspection/domain/interfaces/inspection_repository.py` — `IInspectionRepository` (ABC)

**Fault Domain**
- [ ] Create `apps/fault/domain/__init__.py`
- [ ] Create `apps/fault/domain/entities.py` — `Fault`, `FaultItem`, `FaultStatus` (enum: OPEN, ASSIGNED, IN_REPAIR, CLOSED), `FaultSeverity` (enum: LOW, MEDIUM, HIGH, CRITICAL)
- [ ] Create `apps/fault/domain/value_objects.py` — `FaultCode`, `FaultDescription`, `SAPDefectCode`
- [ ] Create `apps/fault/domain/exceptions.py` — `FaultNotFoundError`, `FaultAlreadyClosedError`, `InvalidFaultTransitionError`
- [ ] Create `apps/fault/domain/interfaces/__init__.py`
- [ ] Create `apps/fault/domain/interfaces/fault_repository.py` — `IFaultRepository` (ABC)

**Repair Domain**
- [ ] Create `apps/repair/domain/__init__.py`
- [ ] Create `apps/repair/domain/entities.py` — `RepairOrder`, `RepairActivity`, `RepairPart`, `RepairOrderStatus` (enum: CREATED, ASSIGNED, IN_PROGRESS, COMPLETED, CANCELLED)
- [ ] Create `apps/repair/domain/value_objects.py` — `TechnicianAssignment`, `PartQuantity`, `LaborHours`
- [ ] Create `apps/repair/domain/exceptions.py` — `RepairOrderNotFoundError`, `RepairOrderStateError`, `InvalidStateTransitionError`, `TechnicianNotAvailableError`
- [ ] Create `apps/repair/domain/interfaces/__init__.py`
- [ ] Create `apps/repair/domain/interfaces/repair_repository.py` — `IRepairOrderRepository`, `IRepairActivityRepository`, `IRepairPartRepository` (ABCs)

**Preventive Maintenance Domain**
- [ ] Create `apps/preventive_maintenance/domain/__init__.py`
- [ ] Create `apps/preventive_maintenance/domain/entities.py` — `PMPlan`, `PMWorkOrder`, `PMStatus` (enum: SCHEDULED, TRIGGERED, IN_PROGRESS, COMPLETED, OVERDUE)
- [ ] Create `apps/preventive_maintenance/domain/value_objects.py` — `MaintenanceInterval`, `TriggerCondition`, `OdometerThreshold`
- [ ] Create `apps/preventive_maintenance/domain/exceptions.py` — `PMPlanNotFoundError`, `PMAlreadyTriggeredError`, `PMWorkOrderNotFoundError`
- [ ] Create `apps/preventive_maintenance/domain/interfaces/__init__.py`
- [ ] Create `apps/preventive_maintenance/domain/interfaces/pm_repository.py` — `IPMPlanRepository`, `IPMWorkOrderRepository` (ABCs)

**Procurement Domain**
- [ ] Create `apps/procurement/domain/__init__.py`
- [ ] Create `apps/procurement/domain/entities.py` — `PurchaseRequisition`, `PurchaseOrder`, `GoodsReceipt`, `GoodsIssue`
- [ ] Create `apps/procurement/domain/value_objects.py` — `MaterialNumber`, `Quantity`, `Currency`, `VendorNumber`, `SAPDocumentNumber`
- [ ] Create `apps/procurement/domain/exceptions.py` — `PRNotFoundError`, `PONotFoundError`, `POAlreadyApprovedError`, `GoodsReceiptNotFoundError`
- [ ] Create `apps/procurement/domain/interfaces/__init__.py`
- [ ] Create `apps/procurement/domain/interfaces/procurement_repository.py` — `IPurchaseRequisitionRepository`, `IPurchaseOrderRepository`, `IGoodsRepository` (ABCs)

**Integration Domain**
- [ ] Create `apps/integration/domain/__init__.py`
- [ ] Create `apps/integration/domain/entities.py` — `SAPTransaction`, `SAPTransactionStatus` (enum: PENDING, IN_PROGRESS, SUCCESS, FAILED, RETRYING, EXHAUSTED)
- [ ] Create `apps/integration/domain/exceptions.py` — `SAPIntegrationError`, `SAPRetryExhaustedError`, `SAPIdempotencyError`, `SAPResponseError`
- [ ] Create `apps/integration/domain/interfaces/__init__.py`
- [ ] Create `apps/integration/domain/interfaces/sap_transaction_repository.py` — `ISAPTransactionRepository` (ABC)

**Reporting Domain (Phase 2 — boundary placeholder only)**
- [ ] Create `apps/reporting/domain/__init__.py`
- [ ] Create `apps/reporting/domain/entities.py` — `Report`, `ReportType` (enum placeholder)
- [ ] Create `apps/reporting/domain/exceptions.py` — `ReportNotFoundError`
- [ ] Add `# Phase 2 — not implemented in Phase 1` header comment to each reporting domain file

**Domain Layer Integrity**
- [ ] Verify zero imports from `django`, `rest_framework`, or any ORM in any `domain/` file (automated grep check in CI)
- [ ] Write domain unit tests:
  - [ ] `tests/unit/domain/test_vehicle_domain.py` — entity creation, status transitions, value object validation
  - [ ] `tests/unit/domain/test_fault_domain.py` — severity rules, state machine
  - [ ] `tests/unit/domain/test_repair_domain.py` — state transition rules, invalid transition raises error
  - [ ] `tests/unit/domain/test_pm_domain.py` — trigger condition evaluation
  - [ ] `tests/unit/domain/test_procurement_domain.py` — entity rules
- [ ] Run `pytest tests/unit/domain/` — all pass
- [ ] Run `black --check .` — zero violations
- [ ] Run `isort --check .` — zero violations
- [ ] Run `ruff check .` — zero violations
- [ ] Run `mypy .` — zero errors

---

### Milestone 3 — Infrastructure: Database Models & Repositories

| Field         | Value                                                                       |
|---------------|-----------------------------------------------------------------------------|
| **Status**    | `Complete ✓`                                                                |
| **Branch**    | `main`                                                                      |
| **Commit**    | `e6d15e7` (final domain — Integration)                                      |
| **Started**   | 2026-07-09                                                                  |
| **Completed** | 2026-07-09                                                                  |

**Goal:**
Implement Django ORM models inheriting `BaseModel` for all Phase 1 domains. Implement
concrete repository classes satisfying the abstract interfaces from Milestone 2. Generate
initial migrations per app. No business logic in this layer. Reporting ORM is Phase 2.

**Tasks:**

**App Registration**
- [x] Register all Phase 1 apps in `INSTALLED_APPS` in `config/settings/base.py`
- [x] Extend `MIGRATION_MODULES` for all 8 Phase 1 domain apps
- [x] Add `config/settings/test.py` — SQLite override for fast CI tests

**Vehicle Infrastructure** — commit `08c11f6`
- [x] `apps/vehicle/infrastructure/models.py` — `VehicleModel(BaseModel)`, UniqueConstraint on `plate_number` (active records), composite index on `(status, is_deleted)`
- [x] `apps/vehicle/infrastructure/repositories.py` — `DjangoVehicleRepository(IVehicleRepository)`
- [x] `apps/vehicle/models.py` — Django auto-discovery shim
- [x] `apps/vehicle/infrastructure/migrations/0001_initial.py` — `makemigrations` generated
- [x] `tests/integration/infrastructure/test_vehicle_repository.py` — 15 tests

**Driver Infrastructure** — commit `b9c0838`
- [x] `apps/driver/infrastructure/models.py` — `DriverModel(BaseModel)`, assigned_vehicle_id as UUIDField (cross-domain by UUID, not FK)
- [x] `apps/driver/infrastructure/repositories.py` — `DjangoDriverRepository(IDriverRepository)`
- [x] `apps/driver/models.py` — shim
- [x] `apps/driver/infrastructure/migrations/0001_initial.py`
- [x] `tests/integration/infrastructure/test_driver_repository.py` — 13 tests

**Inspection Infrastructure** — commit `6a7f294`
- [x] `apps/inspection/infrastructure/models.py` — `InspectionModel(BaseModel)` + `InspectionItemModel` child table (FK cascade)
- [x] `apps/inspection/infrastructure/repositories.py` — `DjangoInspectionRepository`, `save()` uses `transaction.atomic()` + item replacement
- [x] `apps/inspection/models.py` — shim
- [x] `apps/inspection/infrastructure/migrations/0001_initial.py`
- [x] `tests/integration/infrastructure/test_inspection_repository.py` — 10 tests

**Fault Infrastructure** — commit `d3601c5`
- [x] `apps/fault/infrastructure/models.py` — `FaultModel(BaseModel)`, composite indexes on `(vehicle_id, status)` and `(severity, status)`
- [x] `apps/fault/infrastructure/models.py` — `FaultItemModel(BaseModel)` child rows for aggregated inspection failures
- [x] `apps/fault/infrastructure/repositories.py` — `DjangoFaultRepository(IFaultRepository)`
- [x] `apps/fault/models.py` — shim
- [x] `apps/fault/infrastructure/migrations/0001_initial.py`
- [x] `apps/fault/infrastructure/migrations/0002_faultitem.py`
- [x] `tests/integration/infrastructure/test_fault_repository.py` — 12 tests

**Repair Infrastructure** — commit `1d05fa6`
- [x] `apps/repair/infrastructure/models.py` — `RepairOrderModel(BaseModel)`, `RepairActivityModel`, `RepairPartModel` (child tables), TechnicianAssignment denormalized, `initiator_id` (avoids BaseModel FK clash)
- [x] `apps/repair/infrastructure/repositories.py` — `DjangoRepairOrderRepository`, `save()` uses `transaction.atomic()`, `list_active_by_vehicle()` for cross-domain deactivation guard
- [x] `apps/repair/models.py` — shim
- [x] `apps/repair/infrastructure/migrations/0001_initial.py`
- [x] `tests/integration/infrastructure/test_repair_repository.py` — 12 tests

**Preventive Maintenance Infrastructure** — commit `de13d4d`
- [x] `apps/preventive_maintenance/infrastructure/models.py` — `PMPlanModel(BaseModel)`, `PMWorkOrderModel(BaseModel)`, value objects denormalized as flat columns
- [x] `apps/preventive_maintenance/infrastructure/repositories.py` — `DjangoPMPlanRepository`, `DjangoPMWorkOrderRepository`
- [x] `apps/preventive_maintenance/models.py` — shim
- [x] `apps/preventive_maintenance/infrastructure/migrations/0001_initial.py`
- [x] `tests/integration/infrastructure/test_pm_repository.py` — 13 tests

**Procurement Infrastructure** — commit `97a810a`
- [x] `apps/procurement/infrastructure/models.py` — `PurchaseRequisitionModel` + `PRLineItemModel` child; `PurchaseOrderModel` + `POLineItemModel` child; UniqueConstraint on active `sap_po_number`; `po_initiator_id` (avoids FK clash)
- [x] `apps/procurement/infrastructure/repositories.py` — `DjangoPurchaseRequisitionRepository`, `DjangoPurchaseOrderRepository`, both with `transaction.atomic()` on `save()`
- [x] `apps/procurement/models.py` — shim
- [x] `apps/procurement/infrastructure/migrations/0001_initial.py`
- [x] `tests/integration/infrastructure/test_procurement_repository.py` — 16 tests

**Integration Infrastructure** — commit `e6d15e7`
- [x] `apps/integration/infrastructure/models.py` — `SAPTransactionModel(BaseModel)`, JSONField for payloads, UniqueConstraint on `idempotency_key`, composite indexes on `(object_type, object_id)` and `(status, retry_count)`
- [x] `apps/integration/infrastructure/repositories.py` — `DjangoSAPTransactionRepository(ISAPTransactionRepository)`, `save()` uses `transaction.atomic()`
- [x] `apps/integration/models.py` — shim
- [x] `apps/integration/infrastructure/migrations/0001_initial.py`
- [x] `tests/integration/infrastructure/test_sap_transaction_repository.py` — 13 tests (including idempotency key uniqueness, retry lifecycle, exhaustion)

**Quality Gates — All Passed**
- [x] `pytest` — 316 passed (was 213 at M2 completion)
- [x] `black` — zero violations
- [x] `isort` — zero violations
- [x] `ruff check .` — zero violations
- [x] `mypy .` — zero errors (185 source files)

---

### Milestone 4 — SAP Integration Layer

| Field         | Value                                                              |
|---------------|--------------------------------------------------------------------|
| **Status**    | `Complete ✓`                                                       |
| **Branch**    | `feat/milestone-4-sap-integration`                                 |
| **Commit**    | `c3dd46c` — test(sap): add unit tests for mock client, adapters, and transaction manager |
| **Started**   | 2026-07-09                                                         |
| **Completed** | 2026-07-09                                                         |

**Goal:**
Build the complete SAP communication stack. Port interfaces (ABCs) live in `core/sap/ports/`
so the application layer can import them without depending on infrastructure. Concrete adapters
live in `infrastructure/sap/adapters/`. Every SAP write is routed through `SAPTransactionManager`.

**SAP Layer Architecture (ADR-008 applied):**
```
application/services/
    → imports from core/sap/ports/           (abstractions)

infrastructure/sap/adapters/
    → implements core/sap/ports/             (concrete)
    → uses infrastructure/sap/client/        (HTTP / RFC)

infrastructure/sap/transaction/
    → SAPTransactionManager (idempotency, retry, audit)
```

**Tasks:**

**SAP Port Interfaces — `core/sap/ports/` (application-layer-visible abstractions)**
- [x] Create `core/sap/__init__.py`
- [x] Create `core/sap/ports/__init__.py`
- [x] Create `core/sap/ports/equipment_port.py` — `ISAPEquipmentPort` (ABC): `get_equipment_by_id`, `list_equipment`
- [x] Create `core/sap/ports/object_part_catalog_port.py` — `ISAPObjectPartCatalogPort` (ABC): `get_catalog`, `get_part_by_code`
- [x] Create `core/sap/ports/fault_catalog_port.py` — `ISAPFaultCatalogPort` (ABC): `list_defect_codes`, `get_defect_code`
- [x] Create `core/sap/ports/material_port.py` — `ISAPMaterialPort` (ABC): `get_material_by_number`, `list_materials`
- [x] Create `core/sap/ports/inventory_port.py` — `ISAPInventoryPort` (ABC): `get_stock_by_material`, `get_stock_by_plant`
- [x] Create `core/sap/ports/pm_notification_port.py` — `ISAPPMNotificationPort` (ABC): `create_notification`, `close_notification`
- [x] Create `core/sap/ports/pm_order_port.py` — `ISAPPMOrderPort` (ABC): `create_pm_order`, `complete_pm_order`, `get_pm_order`
- [x] Create `core/sap/ports/purchase_requisition_port.py` — `ISAPPurchaseRequisitionPort` (ABC): `create_purchase_requisition`, `get_purchase_requisition`
- [x] Create `core/sap/ports/purchase_order_port.py` — `ISAPPurchaseOrderPort` (ABC): `create_purchase_order`, `approve_purchase_order`, `get_purchase_order`
- [x] Create `core/sap/ports/goods_receipt_port.py` — `ISAPGoodsReceiptPort` (ABC): `post_goods_receipt`, `reverse_goods_receipt`
- [x] Create `core/sap/ports/goods_issue_port.py` — `ISAPGoodsIssuePort` (ABC): `post_goods_issue`, `reverse_goods_issue`
- [x] Create `core/sap/ports/service_po_port.py` — `ISAPServicePOPort` (ABC): `create_service_po`, `confirm_service`, `get_service_po`

**SAP Clients — `infrastructure/sap/client/`**
- [x] Create `infrastructure/sap/__init__.py`
- [x] Create `infrastructure/sap/client/__init__.py`
- [x] Create `infrastructure/sap/client/sap_odata_client.py` — reusable OData HTTP client (requests/httpx, auth, base URL, headers, timeout, error handling)
- [x] Create `infrastructure/sap/client/sap_bapi_client.py` — RFC/BAPI wrapper (abstracted so `pyrfc` can be swapped; raises `SAPIntegrationError` on failure)

**SAP OData Adapters — Read integrations (`infrastructure/sap/adapters/odata/`)**
- [x] Create `infrastructure/sap/adapters/__init__.py`
- [x] Create `infrastructure/sap/adapters/odata/__init__.py`
- [x] Create `infrastructure/sap/adapters/odata/equipment_odata_adapter.py` — implements `ISAPEquipmentPort`, calls `API_EQUIPMENT`
- [x] Create `infrastructure/sap/adapters/odata/object_part_catalog_odata_adapter.py` — implements `ISAPObjectPartCatalogPort`
- [x] Create `infrastructure/sap/adapters/odata/fault_catalog_odata_adapter.py` — implements `ISAPFaultCatalogPort`, calls `API_DEFECTCODE_SRV`
- [x] Create `infrastructure/sap/adapters/odata/material_odata_adapter.py` — implements `ISAPMaterialPort`, calls `API_PRODUCT_SRV`
- [x] Create `infrastructure/sap/adapters/odata/inventory_odata_adapter.py` — implements `ISAPInventoryPort`, calls `API_MATERIAL_STOCK_SRV`

**SAP BAPI Adapters — Write integrations (`infrastructure/sap/adapters/bapi/`)**
- [x] Create `infrastructure/sap/adapters/bapi/__init__.py`
- [x] Create `infrastructure/sap/adapters/bapi/pm_notification_bapi_adapter.py` — implements `ISAPPMNotificationPort`
- [x] Create `infrastructure/sap/adapters/bapi/pm_order_bapi_adapter.py` — implements `ISAPPMOrderPort`
- [x] Create `infrastructure/sap/adapters/bapi/purchase_requisition_bapi_adapter.py` — implements `ISAPPurchaseRequisitionPort` (separate from PO — different BAPI)
- [x] Create `infrastructure/sap/adapters/bapi/purchase_order_bapi_adapter.py` — implements `ISAPPurchaseOrderPort`
- [x] Create `infrastructure/sap/adapters/bapi/goods_receipt_bapi_adapter.py` — implements `ISAPGoodsReceiptPort`
- [x] Create `infrastructure/sap/adapters/bapi/goods_issue_bapi_adapter.py` — implements `ISAPGoodsIssuePort`
- [x] Create `infrastructure/sap/adapters/bapi/service_po_bapi_adapter.py` — implements `ISAPServicePOPort`

**SAP Transaction Manager**
- [x] Create `infrastructure/sap/transaction/__init__.py`
- [x] Create `infrastructure/sap/transaction/sap_transaction_manager.py`:
  - Check idempotency key — if `SAPTransaction` with key exists and status is SUCCESS, return cached response
  - Create `SAPTransaction` record with status `PENDING`
  - Execute SAP call via adapter
  - On success: update status to `SUCCESS`, store `response_payload`, `sap_document_number`
  - On failure: update status to `FAILED`, store `last_error`, increment `retry_count`
  - On retry (Celery): status transitions `FAILED → RETRYING`
  - On retry exhaustion: status `EXHAUSTED`, raise `SAPRetryExhaustedError`
  - All steps use structured logging with `domain=integration`

**SAP Error Mapping**
- [x] Map SAP HTTP 4xx/5xx and BAPI return codes to domain exceptions:
  - Connection failure → `SAPIntegrationError`
  - Duplicate key → `SAPIdempotencyError`
  - BAPI error return → `SAPResponseError` with SAP message
  - Retry limit reached → `SAPRetryExhaustedError`

**Testing**
- [x] Write unit tests with mocked SAP HTTP responses:
  - [x] `tests/unit/infrastructure/sap/test_sap_transaction_manager.py` — success path, failure path, idempotency check, retry behavior
  - [x] `tests/unit/infrastructure/sap/test_equipment_adapter.py` — mocked OData response
  - [x] `tests/unit/infrastructure/sap/test_pm_order_adapter.py` — mocked BAPI response
- [x] Verify no application or domain file imports from `infrastructure/sap/adapters/` directly
- [x] Verify application services can only import from `core/sap/ports/`
- [x] Run `pytest tests/unit/infrastructure/sap/` — all pass
- [x] Run `black --check .` — zero violations
- [x] Run `isort --check .` — zero violations
- [x] Run `ruff check .` — zero violations
- [x] Run `mypy .` — zero errors

---

### Milestone 5 — Application Services: Core Domains

| Field         | Value                                                                              |
|---------------|------------------------------------------------------------------------------------|
| **Status**    | `Complete` ✓                                                                       |
| **Branch**    | `feat/milestone-5-services-core`                                                   |
| **Commit**    | `1dd38a8` — feat(application): implement Fault application services — M5           |
| **Started**   | 2026-07-10                                                                         |
| **Completed** | 2026-07-10                                                                         |

**Goal:**
Implement all use case services for Vehicle, Driver, Inspection, and Fault domains.
Services receive injected repository interfaces and SAP ports — no ORM, no HTTP, no
concrete infrastructure classes imported. Each service has one responsibility (SRP).

**Tasks:**

**Vehicle Application** ✓ COMPLETE — commit `4db243a`
- [x] Create `apps/vehicle/application/__init__.py`
- [x] Create `apps/vehicle/application/dto/__init__.py`
- [x] Create `apps/vehicle/application/dto/vehicle_dto.py` — `CreateVehicleDTO`, `UpdateVehicleDTO`, `DeactivateVehicleDTO`, `VehicleResponseDTO`
- [x] Create `apps/vehicle/application/services/__init__.py`
- [x] Create `apps/vehicle/application/services/create_vehicle_service.py` — `CreateVehicleService`
- [x] Create `apps/vehicle/application/services/update_vehicle_service.py` — `UpdateVehicleService`
- [x] Create `apps/vehicle/application/services/deactivate_vehicle_service.py` — `DeactivateVehicleService` (distribution supervisor decision)
- [x] Create `apps/vehicle/application/services/get_vehicle_service.py` — `GetVehicleService`, `ListVehiclesService`
- [x] Create `apps/vehicle/application/services/sync_sap_equipment_service.py` — `SyncSAPEquipmentService`
- [x] Create `tests/unit/application/test_vehicle_services.py` — 19 unit tests, all passing

**Driver Application** ✓ COMPLETE — commit `df5913f`
- [x] Create `apps/driver/application/dto/driver_dto.py` — `RegisterDriverDTO`, `AssignDriverToVehicleDTO`, `SuspendDriverDTO`, `DriverResponseDTO`
- [x] Create `apps/driver/application/services/register_driver_service.py` — `RegisterDriverService`
- [x] Create `apps/driver/application/services/assign_driver_to_vehicle_service.py` — `AssignDriverToVehicleService` (cross-domain: driver availability + vehicle ACTIVE + no double-assignment)
- [x] Create `apps/driver/application/services/suspend_driver_service.py` — `SuspendDriverService`
- [x] Create `apps/driver/application/services/get_driver_service.py` — `GetDriverService`, `ListDriversService`
- [x] Create `tests/unit/application/test_driver_services.py` — 20 unit tests, all passing

**Inspection Application** ✓ COMPLETE — commit `e12500e`
- [x] Create `apps/inspection/application/dto/inspection_dto.py` — `CreateInspectionDTO`, `AddInspectionItemDTO`, `SubmitInspectionDTO`, `InspectionResponseDTO`, `InspectionItemResponseDTO`
- [x] Create `apps/inspection/application/services/create_inspection_service.py` — `CreateInspectionService` (cross-domain: vehicle existence check)
- [x] Create `apps/inspection/application/services/add_inspection_item_service.py` — `AddInspectionItemService`
- [x] Create `apps/inspection/application/services/submit_inspection_service.py` — `SubmitInspectionService` (multi-step: DRAFT→SUBMITTED + aggregate FAIL items into one Fault with FaultItems + one RepairOrder)
- [x] Create `apps/inspection/application/services/get_inspection_service.py` — `GetInspectionService`, `ListInspectionsService`
- [x] Create `tests/unit/application/test_inspection_services.py` — 16 unit tests, all passing

**Fault Application** ✓ COMPLETE — commit `1dd38a8`
- [x] Create `apps/fault/application/dto/fault_dto.py` — `ReportFaultDTO`, `AssignFaultDTO`, `CloseFaultDTO`, `FaultResponseDTO`
- [x] Create `apps/fault/application/services/report_fault_service.py` — `ReportFaultService` (cross-domain: vehicle existence check)
- [x] Create `apps/fault/application/services/assign_fault_service.py` — `AssignFaultService`
- [x] Create `apps/fault/application/services/close_fault_service.py` — `CloseFaultService`
- [x] Create `apps/fault/application/services/get_fault_service.py` — `GetFaultService`, `ListFaultsService`
- [x] Create `tests/unit/application/test_fault_services.py` — 17 unit tests, all passing

**Test Factories (milestone-scoped)**
- [ ] Create `tests/factories/vehicle_factory.py` — `VehicleModelFactory`
- [ ] Create `tests/factories/driver_factory.py` — `DriverModelFactory`
- [ ] Create `tests/factories/inspection_factory.py` — `InspectionModelFactory`
- [ ] Create `tests/factories/fault_factory.py` — `FaultModelFactory`

**Service Unit Tests (repositories and ports mocked — no DB)**
- [ ] `tests/unit/apps/vehicle/test_create_vehicle_service.py`
- [ ] `tests/unit/apps/vehicle/test_sync_sap_equipment_service.py`
- [ ] `tests/unit/apps/driver/test_register_driver_service.py`
- [ ] `tests/unit/apps/driver/test_assign_driver_service.py`
- [ ] `tests/unit/apps/inspection/test_create_inspection_service.py`
- [ ] `tests/unit/apps/inspection/test_submit_inspection_service.py`
- [ ] `tests/unit/apps/fault/test_report_fault_service.py`
- [ ] `tests/unit/apps/fault/test_close_fault_service.py`

**Layer Integrity Check** ✓ ALL PASSED
- [x] Verify no ORM model import exists inside any `application/` directory — PASSED (AST scan)
- [x] Verify no `infrastructure/` import exists inside any `application/` directory — PASSED
- [x] Run `pytest tests/unit/application/` — 72/72 passed
- [x] Run `black --check .` — zero violations
- [x] Run `isort --check .` — zero violations
- [x] Run `ruff check .` — zero violations
- [x] Run `mypy .` — zero errors

---

### Milestone 6 — Application Services: Maintenance Domains

| Field         | Value                                                                                  |
|---------------|----------------------------------------------------------------------------------------|
| **Status**    | `Complete` ✓                                                                       |
| **Branch**    | `feat/milestone-6-services-maintenance`                                                |
| **Commit**    | `feat(application): implement maintenance domain services (repair, pm, procurement)`   |
| **Started**   | 2026-07-10                                                                             |
| **Completed** | 2026-07-10                                                                             |

**Goal:**
Implement all use case services for Repair, Preventive Maintenance, and Procurement.
Services that interact with SAP must import only from `core/sap/ports/` — never from
`infrastructure/sap/adapters/` directly.

**Tasks:**

**Repair Application** ✓ COMPLETE
- [x] Create `apps/repair/application/dto/repair_dto.py` — create/assign/complete/cancel/activity/part/sync DTOs + response DTOs
- [x] Create `apps/repair/application/services/create_repair_order_service.py` — `CreateRepairOrderService` (vehicle + fault existence, vehicle match)
- [x] Create `apps/repair/application/services/assign_repair_order_service.py` — `AssignRepairOrderService` (delegates to `assign_technician()`)
- [x] Create `apps/repair/application/services/update_repair_status_service.py` — `StartRepairService`, `CompleteRepairOrderService`, `CancelRepairOrderService`
- [x] Create `apps/repair/application/services/add_repair_activity_service.py` — `AddRepairActivityService`, `AddRepairPartService`
- [x] Create `apps/repair/application/services/sync_repair_to_sap_service.py` — `SyncRepairToSAPService` (depends only on `ISAPPMOrderPort`)
- [x] Create `apps/repair/application/services/get_repair_order_service.py` — `GetRepairOrderService`, `ListRepairOrdersService`
- [x] Create `tests/unit/application/test_repair_services.py` — 23 unit tests, all passing

**Preventive Maintenance Application** ✓ COMPLETE
- [x] Create `apps/preventive_maintenance/application/dto/pm_dto.py` — create/trigger/complete DTOs + response DTOs
- [x] Create `apps/preventive_maintenance/application/services/create_pm_plan_service.py` — `CreatePMPlanService`
- [x] Create `apps/preventive_maintenance/application/services/trigger_pm_work_order_service.py` — `TriggerPMWorkOrderService` (optional `ISAPPMNotificationPort` only; no Celery/schedulers)
- [x] Create `apps/preventive_maintenance/application/services/complete_pm_work_order_service.py` — `CompletePMWorkOrderService`
- [x] Create `apps/preventive_maintenance/application/services/get_pm_service.py` — `GetPMPlanService`, `ListPMPlansService`, `ListPMWorkOrdersService`
- [x] Create `tests/unit/application/test_pm_services.py` — 16 unit tests, all passing

**Procurement Application** ✓ COMPLETE
- [x] Create `apps/procurement/application/dto/procurement_dto.py` — create/add-line/submit/receive DTOs + response DTOs
- [x] Create `apps/procurement/application/services/create_purchase_requisition_service.py` — `CreatePurchaseRequisitionService`
- [x] Create `apps/procurement/application/services/add_pr_line_item_service.py` — `AddPRLineItemService`
- [x] Create `apps/procurement/application/services/submit_pr_to_sap_service.py` — `SubmitPRToSAPService` (SAPTransaction lifecycle + `ISAPPurchaseRequisitionPort` only)
- [x] Create `apps/procurement/application/services/receive_po_from_sap_service.py` — `ReceivePOFromSAPService`
- [x] Create `apps/procurement/application/services/get_procurement_service.py` — get/list PR + get PO
- [x] Create `tests/unit/application/test_procurement_services.py` — 16 unit tests (incl. idempotency + retry), all passing

**Layer Integrity Check**
- [x] Verify all SAP-calling services import only from `core/sap/ports/`
- [x] Run `pytest tests/unit/application/test_repair_services.py tests/unit/application/test_pm_services.py tests/unit/application/test_procurement_services.py` — all pass
- [x] Run `black` / `isort` / `ruff` / `mypy` on M6 application packages — zero errors
- [ ] Create milestone-scoped factories (deferred — unit tests use in-memory fakes)

---

### Milestone 7 — Interface Layer: REST API v1

| Field         | Value                                                  |
|---------------|--------------------------------------------------------|
| **Status**    | `Complete ✓`                                           |
| **Branch**    | `feat/milestone-7-api-v1`                              |
| **Commit**    | `feat(api): implement REST API v1 for all domains`     |
| **Started**   | 2026-07-10                                             |
| **Completed** | 2026-07-10                                             |

**Goal:**
Expose all Phase 1 domain services via a versioned REST API. Controllers are thin — they
validate input, call one service, and return a response. No business logic in views.
Middleware is already wired (from M1). Full OpenAPI schema generated by `drf-spectacular`.

**Tasks:**

**DRF & Auth Configuration**
- [x] Add `djangorestframework`, `djangorestframework-simplejwt`, `drf-spectacular` to `requirements/base.txt`
- [x] Configure DRF in `config/settings/base.py`: default authentication, permission classes, renderer classes, exception handler pointing to `core/exceptions/http_exception_handler.py`
- [x] Configure JWT settings: access token lifetime, refresh token lifetime, algorithm
- [x] Create `interfaces/api/v1/auth/views.py` — `TokenObtainPairView`, `TokenRefreshView`
- [x] Create `interfaces/api/v1/auth/urls.py`

**Shared API Infrastructure**
- [x] Create `interfaces/__init__.py`
- [x] Create `interfaces/api/__init__.py`
- [x] Create `interfaces/api/v1/__init__.py`
- [x] Create `interfaces/api/v1/urls.py` — root URL router for v1
- [x] Create `core/pagination/standard_pagination.py` — `FMMSPageNumberPagination` (page_size=20, max=100)
- [x] Create `core/permissions/role_permissions.py` — role gates (`IsAdminRole`, `IsSupervisorOrAbove`, `IsTechnicianOrAbove`, `IsReadOnlyOrTechnicianOrAbove`)

**Vehicle API**
- [x] Create `interfaces/api/v1/vehicle/serializers.py` — `VehicleRequestSerializer`, `VehicleResponseSerializer`
- [x] Create `interfaces/api/v1/vehicle/views.py` — `VehicleViewSet` (thin: calls services, no ORM)
- [x] Create `interfaces/api/v1/vehicle/urls.py`

**Driver API**
- [x] Create `interfaces/api/v1/driver/serializers.py`
- [x] Create `interfaces/api/v1/driver/views.py` — `DriverViewSet`
- [x] Create `interfaces/api/v1/driver/urls.py`

**Inspection API**
- [x] Create `interfaces/api/v1/inspection/serializers.py`
- [x] Create `interfaces/api/v1/inspection/views.py` — `InspectionViewSet`
- [x] Create `interfaces/api/v1/inspection/urls.py`

**Fault API**
- [x] Create `interfaces/api/v1/fault/serializers.py`
- [x] Create `interfaces/api/v1/fault/views.py` — `FaultViewSet`
- [x] Create `interfaces/api/v1/fault/urls.py`

**Repair API**
- [x] Create `interfaces/api/v1/repair/serializers.py`
- [x] Create `interfaces/api/v1/repair/views.py` — `RepairOrderViewSet` (activities/parts as `@action`)
- [x] Create `interfaces/api/v1/repair/urls.py`

**Preventive Maintenance API**
- [x] Create `interfaces/api/v1/preventive_maintenance/serializers.py`
- [x] Create `interfaces/api/v1/preventive_maintenance/views.py` — `PMPlanViewSet`, `PMWorkOrderViewSet`
- [x] Create `interfaces/api/v1/preventive_maintenance/urls.py`

**Procurement API**
- [x] Create `interfaces/api/v1/procurement/serializers.py`
- [x] Create `interfaces/api/v1/procurement/views.py` — `PurchaseRequisitionViewSet`, `PurchaseOrderViewSet` (GR/GI deferred)
- [x] Create `interfaces/api/v1/procurement/urls.py`

**Integration Status API (SAP transaction tracking)**
- [x] Create `interfaces/api/v1/integration/serializers.py`
- [x] Create `interfaces/api/v1/integration/views.py` — `SAPTransactionViewSet` (read-only: list, retrieve)
- [x] Create `interfaces/api/v1/integration/urls.py`

**OpenAPI Documentation**
- [x] Configure `drf-spectacular` in `config/settings/base.py`
- [x] Expose `GET /api/schema/` — raw OpenAPI JSON/YAML
- [x] Expose `GET /api/schema/swagger-ui/` — Swagger UI
- [x] Expose `GET /api/schema/redoc/` — Redoc UI
- [x] Annotate all views with `@extend_schema` (description, request, response, error examples)

**API Integration Tests**
- [x] `tests/integration/api/test_vehicle_api.py` — CRUD + auth + validation errors
- [x] `tests/integration/api/test_fault_api.py` — report + close flow
- [x] `tests/integration/api/test_repair_api.py` — full repair order lifecycle
- [x] `tests/integration/api/test_procurement_api.py` — PR creation + SAP submit + PO receive
- [x] `tests/integration/api/test_auth_api.py` — token obtain, refresh, invalid credentials
- [x] Verify OpenAPI schema generates without errors: `python manage.py spectacular --validate`
- [x] Run `pytest tests/integration/api/` — all pass
- [x] Run `black --check .` — zero violations
- [x] Run `isort --check .` — zero violations
- [x] Run `ruff check .` — zero violations
- [x] Run `mypy interfaces/ core/pagination core/permissions` — zero errors

---

### Milestone 8 — Async Background Tasks

| Field         | Value                                                                       |
|---------------|-----------------------------------------------------------------------------|
| **Status**    | `Complete ✓`                                                                |
| **Branch**    | `feat/milestone-8-celery-tasks`                                             |
| **Commit**    | `feat(messaging): implement Celery tasks for SAP sync and PM scheduling`    |
| **Started**   | 2026-07-10                                                                  |
| **Completed** | 2026-07-10                                                                  |

**Goal:**
Enable asynchronous processing for the reduced M8 scope using Celery with Redis.
Tasks are thin: resolve dependencies → call application services / manager facade →
structured logging. No business logic and no ORM access in tasks.

**SAP write architecture (mandatory):**

```
Application Service
        |
ISAPTransactionManager  (port) / SAPTransactionManager (infra)
        |
SAP Port
        |
SAP Adapter
```

`SAPTransactionManager` is the **sole gateway** for all SAP WRITE operations.
Application services must not manage `SAPTransaction` lifecycle independently.

**In-scope Beat jobs (reduced):**
- `retry_failed_sap_transactions` — every 15 min (via `SAPTransactionManager.retry` / facade)
- `trigger_overdue_pm_work_orders` — daily (via `TriggerPMWorkOrderService`)
- `sync_equipment_from_sap` — single-equipment sync via `SyncSAPEquipmentService` (not bulk)

**Deferred (out of M8):**
- Bulk equipment sync
- Fault catalog bulk sync
- Material master bulk sync
- Maintenance due notification jobs

**Tasks:**

**Celery Configuration**
- [x] Create `infrastructure/messaging/__init__.py`
- [x] Create `infrastructure/messaging/celery_app.py` — Celery application factory + explicit task imports
- [x] Update `config/__init__.py` to load Celery app on Django startup
- [x] Configure Celery in `config/settings/base.py`: broker, result backend, serializers, timezone
- [x] Configure `CELERY_BEAT_SCHEDULE` in `base.py` (reduced scope only):
  - `retry-failed-sap-every-15m`: `fmms.retry_failed_sap_transactions` — every 15 min
  - `trigger-overdue-pm-daily`: `fmms.trigger_overdue_pm_work_orders` — daily 02:00 UTC
  - Single-equipment sync is **on-demand only** (requires `sap_equipment_number`; not beat-scheduled)
- [x] `celery-worker` / `celery-beat` services present in `docker-compose.yml`
- [x] `make worker` and `make beat` targets in `Makefile`

**SAP Sync Tasks (in scope)**
- [x] Create `infrastructure/messaging/tasks/__init__.py`
- [x] Create `infrastructure/messaging/tasks/sap_sync_tasks.py`:
  - [x] `sync_equipment_from_sap` — calls `SyncSAPEquipmentService` only (single equipment)

**SAP Retry Tasks**
- [x] Create `infrastructure/messaging/tasks/sap_retry_tasks.py`:
  - [x] `retry_failed_sap_transactions` — calls `RetryFailedSAPTransactionsService`
        (manager `retry_all_pending`); **never** queries ORM models from the task

**Maintenance Scheduling Tasks**
- [x] Create `infrastructure/messaging/tasks/maintenance_tasks.py`:
  - [x] `trigger_overdue_pm_work_orders` — calls `TriggerOverduePMWorkOrdersService`
        (delegates to `TriggerPMWorkOrderService`; SAP writes via `ISAPTransactionManager`)

**Task Quality Standards (mandatory)**
- [x] All tasks decorated with `@shared_task(bind=True, max_retries=3)`
- [x] Tasks may only: resolve dependencies, call application services or manager facade, log
- [x] Tasks must never: query ORM directly, contain business logic
- [x] All tasks use `try/except` with structured logging — zero silent failures
- [x] Every task log includes: `domain`, `task_name`, `task_id`, `correlation_id`
- [x] Use `get_structured_logger` (not stdlib logger alone)

**Task Tests**
- [x] `tests/unit/infrastructure/messaging/test_sap_sync_tasks.py` — mocked services
- [x] `tests/unit/infrastructure/messaging/test_sap_retry_tasks.py` — mocked manager/service facade
- [x] `tests/unit/infrastructure/messaging/test_maintenance_tasks.py` — mocked PM service
- [x] Run `pytest tests/unit/infrastructure/messaging/` — all pass
- [x] Run `black --check .` — zero violations
- [x] Run `isort --check .` — zero violations
- [x] Run `ruff check .` — zero violations
- [x] Run `mypy` on messaging + new services — zero errors

---

### Milestone 9 — Testing Completeness & Production Hardening

| Field         | Value                                                              |
|---------------|--------------------------------------------------------------------|
| **Status**    | `Complete`                                                         |
| **Branch**    | `feat/milestone-9-testing`                                         |
| **Commit**    | `4bb270d` — test(all): harden production scenarios and integration coverage |
| **Started**   | 2026-07-10                                                         |
| **Completed** | 2026-07-10                                                         |

**Goal:**
Harden production scenarios (not raw coverage expansion). P0 security/JWT/SAP
retry/API errors/Celery failures; P1 workflows/transaction rollback/soft-delete/
domain edges. Do not change architecture, weaken permissions, or bypass domain
rules to make tests pass. Production defects require approval before fixes.

**Priority strategy applied**

**P0 — Complete**
- [x] Security & permission matrix (`test_security_permissions_api.py`)
- [x] JWT failure scenarios (invalid bearer, invalid refresh, expired access)
- [x] SAP retry lifecycle (`test_sap_retry_lifecycle.py`) — SUCCESS / skip / EXHAUSTED / continue-on-failure + payload rebuild
- [x] Error handling through API (`test_error_handling_api.py`) — 400/404(FMMS)/502; defects locked as current 500s
- [x] Celery failure scenarios (`test_celery_failure_scenarios.py`) — log fields, re-raise, partial PM sweep

**P1 — Complete**
- [x] Repair workflow edges (`test_repair_workflow_edges_api.py`)
- [x] Transaction rollback / non-mutation (`test_transaction_rollback_scenarios.py`)
- [x] Soft-delete visibility via API/list (`test_soft_delete_visibility_api.py`)
- [x] Driver domain edges (`test_driver_domain.py`)

**P2 — Deferred (as approved)**
- [ ] Deferred unused adapter tests (only if Phase 1 later requires them)
- [ ] Broad coverage hunt beyond critical scenarios

**Fixture fix (tests only)**
- [x] Role clients use distinct `APIClient` instances (shared client overwrote auth)

**Production defects — fixed (2026-07-10)**

| ID | Resolution |
|----|------------|
| **DEFECT-M9-01** | **Option C** — `load_or_not_found()` in application services translates `DomainNotFoundError` → `FMMSNotFoundError`; handler unchanged (404). Repositories still raise domain not-found. |
| **DEFECT-M9-02** | Shared `DomainStateError` hierarchy; repair/state exceptions inherit it; handler maps `DomainStateError` → HTTP **422** by category (no domain-specific types in handler). |

**Final Verification**
- [x] `pytest --cov --cov-fail-under=80` — **569 passed**, coverage **88.05%**
- [x] `black --check .` — pass
- [x] `isort --check-only .` — pass
- [x] `ruff check .` — pass
- [x] `mypy .` — baseline unchanged (no new from this fix)

---

### Milestone 10 — Hardening & Documentation

| Field         | Value                                                                              |
|---------------|------------------------------------------------------------------------------------|
| **Status**    | `Pending`                                                                          |
| **Branch**    | `feat/milestone-10-hardening`                                                      |
| **Commit**    | `docs(project): finalize documentation, health checks, and production configuration` |
| **Started**   | —                                                                                  |
| **Completed** | —                                                                                  |

**Goal:**
Prepare the project for production baseline delivery. Health checks, Sentry observability,
N+1 query audit, final security hardening, complete README, and Phase 1 release tag.

**Tasks:**

**Health Check Endpoint**
- [ ] Create `interfaces/api/v1/health/views.py` — `HealthCheckView`
- [ ] Check DB connectivity (simple query)
- [ ] Check Redis connectivity (ping)
- [ ] Check Celery broker reachability
- [ ] Return `{ "status": "ok", "checks": { "db": ..., "redis": ..., "celery": ... } }`
- [ ] Expose at `GET /api/health/` — exempt from authentication

**Observability**
- [ ] Add `sentry-sdk[django]` to `requirements/staging.txt` and `requirements/production.txt`
- [ ] Configure Sentry in `config/settings/staging.py` and `production.py` using `SENTRY_DSN` env var
- [ ] Ensure Sentry captures unhandled exceptions and links to `request_id`

**Performance — N+1 Query Audit**
- [ ] Enable `django-debug-toolbar` in development settings (already in dev requirements)
- [ ] Audit all list endpoints with Django Silk or debug toolbar
- [ ] Add `select_related` / `prefetch_related` to all identified N+1 queries in repositories
- [ ] Document query counts per endpoint in this tracker after audit

**Production Settings Hardening**
- [ ] `SECURE_SSL_REDIRECT = True`
- [ ] `SECURE_HSTS_SECONDS = 31536000`
- [ ] `SECURE_HSTS_INCLUDE_SUBDOMAINS = True`
- [ ] `SESSION_COOKIE_SECURE = True`
- [ ] `CSRF_COOKIE_SECURE = True`
- [ ] `ALLOWED_HOSTS` — loaded from env, not hardcoded
- [ ] `CORS_ALLOWED_ORIGINS` — loaded from env per environment
- [ ] `DEBUG = False` enforced in production settings

**Documentation**
- [ ] Complete `README.md`:
  - Project overview and architecture diagram
  - Local setup with Docker
  - Environment variable reference
  - `make` target reference
  - API documentation link
  - Git workflow and commit format
- [ ] Final `.env.example` — every variable has a description, type, and example value
- [ ] Add `docs/ARCHITECTURE_DECISIONS.md` summarizing all ADRs from this tracker

**Final Quality Pass**
- [ ] Run `black .` — format entire codebase
- [ ] Run `isort .` — sort entire codebase
- [ ] Run `ruff check . --fix` — auto-fix remaining lint issues
- [ ] Run `mypy .` — zero errors (strict mode)
- [ ] Run full test suite: `pytest --cov --cov-fail-under=80` — passes
- [ ] Run `python manage.py check --deploy` — zero warnings

**Release**
- [ ] Tag: `git tag v0.1.0-phase1-foundation`
- [ ] Update `Project Status` table in this file: `Completed: 10 / 10`

---

## Git History

| #  | Date       | Commit    | Message                                         | Branch | Files | Status      |
|----|-----------|-----------|-------------------------------------------------|--------|-------|-------------|
| 1  | 2026-07-09 | `05a006b` | chore(repo): initialize FMMS repository         | `main` | 14    | ✓ Committed |
| 2  | 2026-07-09 | `5895a8f` | docs(repo): update tracker for M0 completion    | `main` | 1     | ✓ Committed |
| 3  | 2026-07-09 | `cb3dfa2` | feat(core): initialize project foundation       | `main` | 58    | ✓ Committed |
| 4  | 2026-07-09 | `cc7ff30` | docs(repo): update tracker with M1 completion  | `main` | 1     | ✓ Committed |
| 5  | 2026-07-09 | `3a4c73f` | docs(repo): set Milestone 2 as In Progress     | `main` | 1     | ✓ Committed |
| 6  | 2026-07-09 | `85b6d28` | feat(domain): define domain entities and repository interfaces | `main` | 79 | ✓ Committed |
| 7  | 2026-07-09 | `8270379` | test(procurement): correct Money currency normalisation test   | `main` | 1  | ✓ Committed |
| 8  | 2026-07-09 | `08c11f6` | feat(infrastructure): implement Vehicle ORM model and repository | `main` | 26 | ✓ Committed |
| 9  | 2026-07-09 | `07aa21a` | chore(repo): add SQLite test DB files to .gitignore           | `main` | 1  | ✓ Committed |
| 10 | 2026-07-09 | `b9c0838` | feat(infrastructure): implement Driver ORM model and repository | `main` | 10 | ✓ Committed |
| 11 | 2026-07-09 | `6a7f294` | feat(infrastructure): implement Inspection ORM models and repository | `main` | 5 | ✓ Committed |
| 12 | 2026-07-09 | `d3601c5` | feat(infrastructure): implement Fault ORM model and repository | `main` | 5  | ✓ Committed |
| 13 | 2026-07-09 | `1d05fa6` | feat(infrastructure): implement Repair ORM models and repository | `main` | 5  | ✓ Committed |
| 14 | 2026-07-09 | `de13d4d` | feat(infrastructure): implement Preventive Maintenance ORM models and repositories | `main` | 5 | ✓ Committed |
| 15 | 2026-07-09 | `97a810a` | feat(infrastructure): implement Procurement ORM models and repositories | `main` | 5 | ✓ Committed |
| 16 | 2026-07-09 | `e6d15e7` | feat(infrastructure): implement SAP Integration ORM model and repository | `main` | 5 | ✓ Committed |
| 17 | 2026-07-09 | `e00e6f8` | docs(repo): update IMPLEMENTATION_TRACKER.md with M3 completion | `feat/milestone-4-sap-integration` | 4 | ✓ Committed |
| 18 | 2026-07-09 | `c2f3f51` | feat(sap): add SAP port interfaces and DTOs (Step 1 of M4) | `feat/milestone-4-sap-integration` | 4 | ✓ Committed |
| 19 | 2026-07-09 | `259c82e` | feat(sap): add ISAPClient ABC, MockSAPClient, and canned SAP scenarios (Step 2 of M4) | `feat/milestone-4-sap-integration` | 4 | ✓ Committed |
| 20 | 2026-07-09 | `37d2f96` | feat(sap): add OData and BAPI adapters for all SAP integrations (Step 3 of M4) | `feat/milestone-4-sap-integration` | 4 | ✓ Committed |
| 21 | 2026-07-09 | `b92ee59` | feat(sap): add SAPTransactionManager, SAPConfig, and Celery task scaffold (Step 4 of M4) | `feat/milestone-4-sap-integration` | 4 | ✓ Committed |
| 22 | 2026-07-09 | `c3dd46c` | test(sap): add unit tests for mock client, adapters, and transaction manager (Step 5 of M4) | `feat/milestone-4-sap-integration` | 4 | ✓ Committed |
| 23 | 2026-07-10 | `fb13b26` | fix(sap): add BAPI_PR_GET_DETAIL mock route (M4 architecture review) | `feat/milestone-4-sap-integration` | 4 | ✓ Committed |
| 24 | 2026-07-10 | `bdcaebd` | docs(tracker): M4 architecture review results — 6/6 checks passed | `feat/milestone-5-services-core` | 1 | ✓ Committed |
| 25 | 2026-07-10 | `4be6740` | docs(tracker): start M5 — Application Services: Core Domains | `feat/milestone-5-services-core` | 1 | ✓ Committed |
| 26 | 2026-07-10 | `4db243a` | feat(application): implement Vehicle application services — M5 | `feat/milestone-5-services-core` | 11 | ✓ Committed |
| 27 | 2026-07-10 | `4ae8d3b` | docs(tracker): mark Vehicle application services complete (M5) | `feat/milestone-5-services-core` | 1 | ✓ Committed |
| 28 | 2026-07-10 | `df5913f` | feat(application): implement Driver application services — M5 | `feat/milestone-5-services-core` | 9 | ✓ Committed |
| 29 | 2026-07-10 | `df4249a` | docs(tracker): mark Driver application services complete (M5) | `feat/milestone-5-services-core` | 1 | ✓ Committed |
| 30 | 2026-07-10 | `e12500e` | feat(application): implement Inspection application services — M5 | `feat/milestone-5-services-core` | 9 | ✓ Committed |
| 31 | 2026-07-10 | `1dd38a8` | feat(application): implement Fault application services — M5 | `feat/milestone-5-services-core` | 9 | ✓ Committed |
| 32 | 2026-07-10 | `e041276` | docs(tracker): complete M5 — Application Services: Core Domains | `feat/milestone-5-services-core` | 1 | ✓ Committed |
| 33 | 2026-07-10 | `42ea524` | docs(tracker): M5 final — integrity PASSED, 72 tests | `feat/milestone-5-services-core` | 1 | ✓ Committed |
| 34 | 2026-07-10 | `39a5317` | docs(tracker): start M6 — Application Services: Maintenance Domains | `feat/milestone-6-services-maintenance` | 1 | ✓ Committed |
| 35 | 2026-07-10 | `b375fed` | feat(application): implement Repair application services — M6 | `feat/milestone-6-services-maintenance` | 12 | ✓ Committed |
| 36 | 2026-07-10 | `5f635ad` | docs(tracker): mark Repair application services complete (M6) | `feat/milestone-6-services-maintenance` | 1 | ✓ Committed |
| 37 | 2026-07-10 | `795f0a4` | feat(application): implement Preventive Maintenance application services — M6 | `feat/milestone-6-services-maintenance` | 10 | ✓ Committed |
| 38 | 2026-07-10 | `06e4484` | docs(tracker): mark PM application services complete (M6) | `feat/milestone-6-services-maintenance` | 1 | ✓ Committed |
| 39 | 2026-07-10 | `e29418f` | feat(application): implement Procurement application services — M6 | `feat/milestone-6-services-maintenance` | 11 | ✓ Committed |
| 40 | 2026-07-10 | `cc919aa` | docs(tracker): set M6 Last Commit to e29418f (Procurement complete) | `feat/milestone-6-services-maintenance` | 1 | ✓ Committed |
| 41 | 2026-07-10 | `9dce208` | docs(tracker): finalize M6 — Git history rows 33-40, validation PASSED | `feat/milestone-6-services-maintenance` | 1 | ✓ Committed |
| 42 | 2026-07-10 | `b7c1ff6` | docs(tracker): start M7 — REST API v1 (M6 complete) | `feat/milestone-7-api-v1` | 1 | ✓ Committed |
| 43 | 2026-07-10 | `8857c87` | feat(api): implement REST API v1 for all domains | `feat/milestone-7-api-v1` | 59 | ✓ Committed |
| 44 | 2026-07-10 | `b1947b5` | docs(tracker): finalize M7 — REST API v1 complete | `feat/milestone-7-api-v1` | 1 | ✓ Committed |
| 45 | 2026-07-10 | `7cdfb33` | docs(tracker): set M7 Last Commit and git history row 44 | `feat/milestone-7-api-v1` | 1 | ✓ Committed |
| 46 | 2026-07-10 | `2a19611` | docs(tracker): sync M7 Last Commit to HEAD | `feat/milestone-7-api-v1` | 1 | ✓ Committed |
| 47 | 2026-07-10 | `385da40` | refactor(sap): centralize SAP write transaction management | `feat/milestone-7-api-v1` | 13 | ✓ Committed |
| 48 | 2026-07-10 | `7693264` | feat(messaging): implement Celery tasks for SAP sync and PM scheduling | `feat/milestone-8-celery-tasks` | — | ✓ Committed |

---

## Decision Log

### ADR-001 — Domain-per-App Internal Layering

| Field        | Detail |
|--------------|--------|
| **Decision** | Each Django app (`apps/<domain>/`) contains its own `domain/`, `application/`, `infrastructure/`, and `interfaces/` sub-packages |
| **Reason**   | Self-contained domain modules. Django app = deployment unit, not architectural unit. Avoids cross-domain coupling. |
| **Impact**   | Each domain is independently testable. Migration files stay with the owning app via `Meta.app_label`. |
| **Date**     | 2026-07-09 |

---

### ADR-002 — Shared SAP Infrastructure at Project Level

| Field        | Detail |
|--------------|--------|
| **Decision** | `infrastructure/sap/` lives at the project root, not inside any single domain app |
| **Reason**   | SAP is cross-domain. Equipment → Vehicle, Fault Catalog → Fault, Materials → Procurement. It cannot belong to one app. |
| **Impact**   | All SAP clients, adapters, and transaction manager are shared and independently versioned. |
| **Date**     | 2026-07-09 |

---

### ADR-003 — Abstract Repository Interfaces in Domain Layer

| Field        | Detail |
|--------------|--------|
| **Decision** | Repository interfaces (ports) live in `apps/<domain>/domain/interfaces/` as pure Python ABCs |
| **Reason**   | Respects Dependency Inversion. Service layer depends on abstractions. Concrete ORM implementations are in infrastructure. |
| **Impact**   | All business logic is testable without a database. Services receive injected mock repositories in tests. |
| **Date**     | 2026-07-09 |

---

### ADR-004 — SAPTransactionManager as the Sole SAP Write Gateway

| Field        | Detail |
|--------------|--------|
| **Decision** | All SAP write operations must pass through `SAPTransactionManager` |
| **Reason**   | Single enforcement point for idempotency key check, `SAPTransaction` record creation, retry, and error mapping. Prevents duplicate SAP documents. |
| **Impact**   | Every SAP write is auditable, retryable, and idempotent by design. |
| **Date**     | 2026-07-09 |

---

### ADR-005 — Settings Split by Environment

| Field        | Detail |
|--------------|--------|
| **Decision** | `config/settings/` contains `base.py`, `development.py`, `staging.py`, `production.py`. Selected via `DJANGO_SETTINGS_MODULE` env var. |
| **Reason**   | Zero configuration hardcoding. Safe for CI/CD. Prevents production credentials leaking into development. |
| **Impact**   | All secrets and environment-specific values externalized via `django-environ` and `.env` files. |
| **Date**     | 2026-07-09 |

---

### ADR-006 — Soft Delete on All Business Records

| Field        | Detail |
|--------------|--------|
| **Decision** | `BaseModel` includes `is_deleted`, `deleted_at`, `deleted_by`. No physical DELETE on business records. |
| **Reason**   | Full auditability required. SAP integration records are audit evidence and must never be physically removed. |
| **Impact**   | All repository `delete()` methods perform soft delete. All list queries filter `is_deleted=False` by default. |
| **Date**     | 2026-07-09 |

---

### ADR-007 — SAPTransaction Uses Generic Relation (No FK to Domain Models)

| Field        | Detail |
|--------------|--------|
| **Decision** | `SAPTransactionModel` references domain objects via `business_object_type` (string) + `business_object_id` (string) — not Django FK |
| **Reason**   | `SAPTransaction` tracks all domains. A FK would couple the integration table to every domain model and block independent migration. |
| **Impact**   | Flexible, extensible integration tracking. New domains integrated without modifying `SAPTransactionModel`. Querying requires two fields instead of one FK. |
| **Date**     | 2026-07-09 |

---

### ADR-008 — SAP Port Interfaces Live in `core/sap/ports/` (Not Infrastructure)

| Field        | Detail |
|--------------|--------|
| **Decision** | Abstract SAP port interfaces (`ISAPEquipmentPort`, `ISAPPMOrderPort`, etc.) are defined in `core/sap/ports/`, not in `infrastructure/sap/interfaces/` |
| **Reason**   | Clean Architecture dependency rule: inner layers must not import from outer layers. If application services import from `infrastructure/`, the dependency direction is inverted — a direct DIP violation. `core/` is a neutral, shared package accessible to all layers. |
| **Impact**   | `infrastructure/sap/adapters/` imports from and implements `core/sap/ports/`. Application services import from `core/sap/ports/` only. No application code ever references `infrastructure/sap/` directly. |
| **Date**     | 2026-07-09 |

---

### ADR-009 — Custom User Model Before First Migration

| Field        | Detail |
|--------------|--------|
| **Decision** | A custom `FMMSUser` model (extending `AbstractBaseUser`) is created in `apps/authentication/` in Milestone 1, before any other migration runs. `AUTH_USER_MODEL = 'authentication.FMMSUser'` |
| **Reason**   | Django prohibits changing `AUTH_USER_MODEL` after the first migration. Deferring this would require destroying all migrations and the database — an unacceptable risk in an enterprise project. |
| **Impact**   | All models using `created_by`, `updated_by`, `deleted_by` FK in `BaseModel` correctly reference `settings.AUTH_USER_MODEL`. Role-based authorization is built on `FMMSUser.role`. |
| **Date**     | 2026-07-09 |

---

### ADR-010 — Reporting Domain Deferred to Phase 2

| Field        | Detail |
|--------------|--------|
| **Decision** | Reporting domain entities are defined as boundary placeholders in M2. No ORM model, no service, no API endpoint is implemented in Phase 1. |
| **Reason**   | Reporting requires data from all other domains to be stable first. Premature implementation creates tight coupling to unstable data structures. |
| **Impact**   | Phase 1 delivers 8 of 9 domains fully. Reporting is added in Phase 2 after the data model is stable. |
| **Date**     | 2026-07-09 |

---

### ADR-012 — Cross-Domain References via UUID, Not Django ForeignKey

| Field        | Detail |
|--------------|--------|
| **Decision** | Domain ORM models reference aggregates in other domains via `UUIDField`, not `ForeignKey`. E.g., `DriverModel.assigned_vehicle_id` is a `UUIDField`, not `FK(VehicleModel)`. |
| **Reason**   | Maintains aggregate boundary independence. Django FK creates a hidden coupling: deleting a vehicle would cascade or restrict driver deletion, violating domain isolation. UUID references keep each bounded context independently deployable and migratable. |
| **Impact**   | Cross-aggregate consistency is enforced at the Application Service level, not by DB constraints. Queries across aggregates require explicit UUID lookups. |
| **Date**     | 2026-07-09 |

---

### ADR-013 — `initiator_id` Column Naming to Avoid BaseModel FK Clash

| Field        | Detail |
|--------------|--------|
| **Decision** | ORM fields representing "who initiated/created a business object" are named `initiator_id` (RepairOrder) or `po_initiator_id` (PurchaseOrder) instead of `created_by_id`. |
| **Reason**   | Django auto-creates the attname `created_by_id` as the DB column for `BaseModel.created_by` (a ForeignKey). Declaring a second field with that name causes a `SystemCheckError`. |
| **Impact**   | Repository `_to_domain()` functions map `orm.initiator_id → entity.created_by_id`. Consistent approach across all affected models. |
| **Date**     | 2026-07-09 |

---

### ADR-014 — SQLite for Test Database (`config/settings/test.py`)

| Field        | Detail |
|--------------|--------|
| **Decision** | `pytest` uses `config.settings.test` which overrides the database to SQLite. PostgreSQL is used only in development (docker-compose) and production. |
| **Reason**   | The sandbox environment has PostgreSQL running but with authentication failures for the `fmms` user. SQLite allows integration tests to run without external services, making the test suite portable across CI environments without database provisioning. |
| **Impact**   | All 8 domain repositories are tested against SQLite. Production uses PostgreSQL exclusively. `ATOMIC_REQUESTS` is disabled in test settings for pytest-django transaction fixture compatibility. |
| **Date**     | 2026-07-09 |

---

### ADR-011 — `pyproject.toml` as Single Tool Configuration File

| Field        | Detail |
|--------------|--------|
| **Decision** | All tool configurations (`black`, `isort`, `ruff`, `mypy`, `pytest`, `coverage`) live in `pyproject.toml` |
| **Reason**   | Centralizes all developer tooling in one file. Avoids configuration drift across `setup.cfg`, `.flake8`, `mypy.ini`, `pytest.ini`. |
| **Impact**   | Every developer and CI pipeline uses identical settings. `make lint` is a single, reproducible command. |
| **Date**     | 2026-07-09 |

---

### ADR-015 — `ISAPClient` ABC Injected into Adapters (Strategy Pattern)

| Field        | Detail |
|--------------|--------|
| **Decision** | Every SAP adapter receives an `ISAPClient` instance by constructor injection. The concrete client (OData, BAPI, or Mock) is decided at composition root, not inside the adapter. |
| **Reason**   | Enables seamless swap between `MockSAPClient` (dev/test) and real clients (production) without any adapter code changes. Satisfies DIP and OCP. |
| **Impact**   | Adapters are fully testable without real SAP. `MockSAPClient` is the default in `SAP_USE_MOCK=True` environments. Production wiring deferred until SAP credentials are provided. |
| **Date**     | 2026-07-09 |

---

### ADR-016 — `SAPTransactionManager.execute()` Accepts `adapter_call: Callable`

| Field        | Detail |
|--------------|--------|
| **Decision** | `SAPTransactionManager` accepts an `adapter_call: Callable[[dict], tuple[dict, str]]` parameter rather than a direct adapter reference. |
| **Reason**   | Decouples the transaction manager from all concrete adapters. The manager orchestrates idempotency/retry lifecycle; the caller provides the SAP operation as a lambda. Avoids a dependency on 12 adapter classes in a single manager. |
| **Impact**   | Application services compose the adapter call and pass it to the manager. The manager remains a pure transaction state machine. |
| **Date**     | 2026-07-09 |

---

### ADR-017 — `SAP_USE_MOCK=True` Default; Production Requires Explicit Credentials

| Field        | Detail |
|--------------|--------|
| **Decision** | `SAPConfig.from_env()` defaults to `SAP_USE_MOCK=True`. When `False`, it raises `ImproperlyConfigured` if any required credential environment variable is missing. |
| **Reason**   | Prevents accidental production deployment without SAP credentials. Eliminates the risk of silent failures where an unconfigured client calls a real SAP system. |
| **Impact**   | Development and test environments work without any SAP configuration. Production deployment requires all 5 credential variables to be explicitly set. |
| **Date**     | 2026-07-09 |

---

### ADR-018 — `ISAPTransactionManager` Is the Sole SAP Write Gateway

| Field        | Detail |
|--------------|--------|
| **Decision** | All SAP WRITE operations go through `ISAPTransactionManager` (implemented by `SAPTransactionManager`). Application services depend on the port only and must not manage `SAPTransaction` lifecycle themselves. |
| **Reason**   | Unify idempotency, audit, and retry; prevent divergent write paths (e.g. hand-rolled lifecycle in services). |
| **Impact**   | `SubmitPRToSAPService`, `SyncRepairToSAPService`, and PM SAP notification writes use the manager. Celery SAP retries must call the manager/facade — never ORM. Flow: Application Service → Manager → SAP Port → Adapter. |
| **Date**     | 2026-07-10 |

---

### ADR-019 — Milestone 8 Reduced Async Scope

| Field        | Detail |
|--------------|--------|
| **Decision** | M8 implements only: SAP retry worker, PM trigger scheduler, and single-equipment SAP sync. Bulk catalog/material/equipment sync and maintenance notification jobs are deferred. |
| **Reason**   | Matching application services do not yet exist for bulk sync/notification jobs; keep M8 aligned with existing services and the write-gateway architecture. |
| **Impact**   | Tracker Beat schedule reduced; deferred jobs require new application services in a later milestone. |
| **Date**     | 2026-07-10 |

---

### ADR-020 — M9 Critical-Scenario Testing Over Coverage Expansion

| Field        | Detail |
|--------------|--------|
| **Decision** | M9 prioritizes P0/P1 production scenarios (security, JWT, SAP retry, API errors, Celery failures, workflow/transaction/soft-delete edges). Deferred adapter coverage is P2 only when Phase 1 requires it. |
| **Reason**   | Coverage was already ~87%; remaining risk was behavioural hardening, not line count. |
| **Impact**   | Defects found during M9 are locked by tests but production fixes require explicit approval. |
| **Date**     | 2026-07-10 |

---

### ADR-021 — Domain Exception Hierarchy and Service NotFound Translation

| Field        | Detail |
|--------------|--------|
| **Decision** | Introduce `DomainError` / `DomainNotFoundError` / `DomainStateError` in `core/domain`. Context exceptions inherit these. Application services translate not-found via `load_or_not_found` → `FMMSNotFoundError`. Handler maps `DomainStateError` → 422 by category only. |
| **Reason**   | Close DEFECT-M9-01/02 without domain-specific knowledge in the global handler and without changing repository contracts. |
| **Impact**   | Missing resources return 404; illegal state transitions return 422. Domain rules unchanged. |
| **Date**     | 2026-07-10 |

---

### ADR-022 — Discrete PostgreSQL Env Vars + Idempotent DB Bootstrap

| Field        | Detail |
|--------------|--------|
| **Decision** | Replace `DATABASE_URL` with `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_HOST` / `POSTGRES_PORT`. Bootstrap via `infrastructure/database/bootstrap.py` and `manage.py ensure_database` creates the DB if missing (never drops). Wired in Compose, Makefile migrate, WSGI/ASGI. |
| **Reason**   | Avoid embedded credentials in URLs; make DB initialization part of the backend deployment workflow. |
| **Impact**   | Local/prod config uses discrete env vars; startup is idempotent for missing databases. |
| **Date**     | 2026-07-10 |

---

### ADR-023 — Standalone Removable Demo Frontend

| Field        | Detail |
|--------------|--------|
| **Decision** | Ship a Vanilla HTML/CSS/JS + Bootstrap CDN demo under `demo-frontend/`. It is not part of the backend architecture and must remain deletable without backend changes. |
| **Reason**   | Stakeholder workflow demonstration without coupling a production SPA to Phase 1. |
| **Impact**   | No Python imports of demo-frontend; API base URL only in `demo-frontend/config/env.js`. |
| **Date**     | 2026-07-10 |

---

### ADR-024 — Bulk SAP Vehicle Sync + Local Inspection Templates

| Field        | Detail |
|--------------|--------|
| **Decision** | Add collection `POST /api/v1/vehicles/sync-sap/` (`SyncVehiclesFromSAPService`) that creates/updates FMMS vehicles from SAP equipment master by `sap_equipment_number`. Add `InspectionTemplate` local cache synced via `POST /api/v1/inspection-templates/sync-sap/` from `ISAPObjectPartCatalogPort`, readable at `GET /api/v1/inspection-templates/`. |
| **Reason**   | Demo/frontend must not hardcode vehicles or checklist items; SAP remains master data owner while FMMS stores synced local copies for offline-capable reads. |
| **Impact**   | Detail `POST /vehicles/{id}/sync-sap/` remains for single-equipment refresh. Deterministic plate/VIN generated on create when SAP lacks those fields. |
| **Date**     | 2026-07-10 |

---

### ADR-025 — Inspection FAIL Auto-Orchestrates Fault + Repair (Distribution Decides Availability)

| Field        | Detail |
|--------------|--------|
| **Decision** | `SubmitInspectionService` aggregates FAIL items into one Fault with FaultItems and one RepairOrder. Vehicle status stays unchanged (`ACTIVE`). Distribution supervisors close faults or call `POST /vehicles/{id}/deactivate/` when the vehicle is not usable. |
| **Reason**   | Drivers report inspection problems; operational availability is a supervisor decision, not a driver-side effect. |
| **Impact**   | `VehicleStatus.OUT_OF_SERVICE` remains available for future use; deactivate transitions to `INACTIVE`. |
| **Date**     | 2026-07-10 |

---

## Demo Backend Workflow Prep (2026-07-10)

| Field         | Value |
|---------------|-------|
| **Status**    | `Complete` |
| **Scope**     | Backend APIs only — `demo-frontend` not modified |

**Delivered:**
- [x] `POST /api/v1/vehicles/sync-sap/` — bulk SAP equipment → vehicle create/update (idempotent)
- [x] `POST /api/v1/inspection-templates/sync-sap/` — SAP object-part catalog → local templates
- [x] `GET /api/v1/inspection-templates/` — list active checklist templates
- [x] `POST /api/v1/inspections/` accepts optional `items` (template-driven checklist results)
- [x] `POST /api/v1/inspections/{id}/submit/` FAIL → one Fault (with items) + one RepairOrder; vehicle stays `ACTIVE`
- [x] PASS submit leaves vehicle `ACTIVE`
- [x] `POST /api/v1/repair-orders/{id}/approve/` — transport supervisor approval (`APPROVED`)
- [x] `POST /api/v1/repair-orders/{id}/assign-workshop/` — INTERNAL/EXTERNAL → `WORKSHOP_ASSIGNED`
- [x] Unit + integration tests (`test_demo_workflow_api.py`, `test_repair_approval_api.py`)
- [x] Migrations `inspection.0002_inspection_template`, `repair.0002_workshop_type_and_status_length`

**Validation:** 593 tests PASS; black/isort/ruff PASS; mypy on changed modules PASS.

---

*Last updated: 2026-07-10 | Updated by: Lead Backend Architect | Validation: demo backend workflow APIs complete; frontend deferred*
