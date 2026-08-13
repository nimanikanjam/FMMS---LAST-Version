# FMMS — Fleet Maintenance Management System

> Enterprise-grade backend for fleet maintenance operations.
> Acts as an operational layer between users and SAP.

---

## Overview

FMMS is a Django-based backend system that manages the full lifecycle of fleet
maintenance — from vehicle inspection and fault reporting through repair execution,
preventive maintenance scheduling, and procurement. All operational data flows
through FMMS while SAP remains the system of record for master data.

---

## Architecture

FMMS follows **Clean Architecture** with strict layer separation:

```
┌─────────────────────────────────┐
│        Interface Layer          │  REST API (DRF), Serializers
├─────────────────────────────────┤
│      Application Layer          │  Services, Use Cases, DTOs
├─────────────────────────────────┤
│        Domain Layer             │  Entities, Value Objects, Rules
├─────────────────────────────────┤
│     Infrastructure Layer        │  ORM, SAP Adapters, Redis, Celery
└─────────────────────────────────┘
```

### SAP Integration Flow

```
Application Service
    → core/sap/ports/          (abstract interface)
    → infrastructure/sap/adapters/    (concrete adapter)
    → infrastructure/sap/client/      (HTTP / RFC client)
    → SAP (OData / BAPI / RFC)
```

All SAP writes are gated through `SAPTransactionManager` — providing idempotency,
retry, and full audit trail via `SAPTransaction` records.

---

## Core Domains

| Domain                  | Responsibility                                       |
|-------------------------|------------------------------------------------------|
| Vehicle Management      | Vehicle registry, SAP equipment sync                 |
| Driver Management       | Driver profiles, vehicle assignments                 |
| Inspection              | Pre/post-trip inspections, checklist management      |
| Fault Management        | Fault reporting, severity classification, lifecycle  |
| Repair Management       | Repair orders, workshop workflow, external invoices  |
| Material Requests       | Parts requests, stock issue, PR handoff              |
| Vehicle Handover        | Driver accept/reject after repair completion         |
| Preventive Maintenance  | PM plans, scheduled work orders, overdue triggers    |
| Procurement             | Purchase requisitions, orders, goods receipt/issue   |
| Integration             | SAP transaction tracking, sync status, retry logs    |

---

## Technology Stack

| Component       | Technology                          |
|-----------------|-------------------------------------|
| Language        | Python 3.12                         |
| Framework       | Django 5.x + Django REST Framework  |
| Database        | PostgreSQL 16                       |
| Cache / Broker  | Redis 7                             |
| Task Queue      | Celery + Celery Beat                |
| SAP Integration | OData (requests/httpx) + BAPI (pyrfc) |
| Auth            | JWT (djangorestframework-simplejwt) |
| API Docs        | drf-spectacular (OpenAPI 3.0)       |
| Code Quality    | black, isort, ruff, mypy            |
| Testing         | pytest, pytest-django, factory-boy  |
| Containerization| Docker + docker-compose             |

---

## Project Structure

```
FMMS/
├── config/                  # Django project settings (base, dev, staging, prod)
├── core/                    # Cross-cutting: logging, exceptions, middleware, SAP ports
│   ├── logging/
│   ├── exceptions/
│   ├── middleware/
│   ├── pagination/
│   ├── permissions/
│   └── sap/
│       └── ports/           # Abstract SAP port interfaces (ISAPEquipmentPort, etc.)
├── apps/                    # One Django app per domain
│   ├── authentication/      # Custom FMMSUser model, roles
│   ├── vehicle/
│   ├── driver/
│   ├── inspection/
│   ├── fault/
│   ├── repair/
│   ├── material/
│   ├── handover/
│   ├── preventive_maintenance/
│   ├── procurement/
│   ├── integration/
│   └── reporting/           # Phase 2
├── infrastructure/          # Shared infrastructure
│   ├── database/            # Shared Django ORM primitives (plain package)
│   ├── operations/          # Project-wide Django management commands
│   ├── sap/                 # SAP clients + adapters + transaction manager
│   └── messaging/           # Celery app + tasks
├── interfaces/              # REST API (DRF views, serializers, URLs)
│   └── api/
│       └── v1/
├── frontend/                # Frontend application
├── tests/                   # All tests
│   ├── unit/
│   ├── integration/
│   └── factories/
├── docs/                    # Architecture and planning documents
└── docs/prototypes/         # Exploratory code (not production)
```

Each domain app has its own internal Clean Architecture:
```
apps/<domain>/
    domain/          # Entities, value objects, exceptions, repository interfaces
    application/     # Services, DTOs
    infrastructure/  # ORM models, repository implementations, migrations
    interfaces/      # (thin — views handled in top-level interfaces/)
```

---

## Quick Start

### Prerequisites

- Docker and docker-compose
- Python 3.12 (for local development without Docker)
- An externally provisioned PostgreSQL database
- `make`

### 1. Clone and configure

```bash
git clone <repo-url>
cd FMMS
cp .env.example .env
# Edit .env with your local values
```

Docker Compose does not create or manage PostgreSQL. Set `POSTGRES_*` in `.env`
to an existing database before continuing.

### 2. Apply migrations

```bash
# Local Python environment
make migrate

# Or through the application image
docker compose run --rm app python manage.py migrate
```

Migrations are an explicit deployment step and are not run by web or Celery
process startup.

### 3. Start with Docker

```bash
make run
```

This starts Redis and the Django development server. PostgreSQL remains an
external dependency in both development and production.

### 4. Run tests

```bash
make test
```

### 5. Run code quality checks

```bash
make lint
```

---

## Make Targets

| Target               | Description                                      |
|----------------------|--------------------------------------------------|
| `make run`           | Start all services via docker-compose            |
| `make test`          | Run full pytest suite with coverage              |
| `make lint`          | black + isort + ruff + mypy checks               |
| `make format`        | Auto-format with black + isort                   |
| `make migrate`       | Run Django database migrations                   |
| `make shell`         | Open Django shell                                |
| `make worker`        | Start Celery worker                              |
| `make beat`          | Start Celery beat scheduler                      |
| `make createsuperuser` | Create an admin user                           |

---

## API Documentation

Once running, the interactive API documentation is available at:

| URL                              | Description        |
|----------------------------------|--------------------|
| `/api/schema/swagger-ui/`        | Swagger UI         |
| `/api/schema/redoc/`             | Redoc              |
| `/api/schema/`                   | Raw OpenAPI JSON   |

---

## Environment Variables

See `.env.example` for the full list of required variables with descriptions.

Key variables:

```env
DJANGO_SETTINGS_MODULE=config.settings.development
SECRET_KEY=<django-secret-key>
POSTGRES_DB=fmms
POSTGRES_USER=fmms
POSTGRES_PASSWORD=fmms
POSTGRES_HOST=localhost
POSTGRES_DOCKER_HOST=host.docker.internal
POSTGRES_PORT=5432
REDIS_URL=redis://localhost:6379/0
SAP_USE_MOCK=True
```

The database itself must already exist. Django manages only its schema:

```bash
python manage.py migrate
```

Run migrations once as a separate development/deployment step before starting
web and Celery processes.

### Development data reset (DEBUG only)

When local workflow/demo data becomes inconsistent after schema or workflow
changes, wipe operational records while keeping master data:

```bash
# Preview counts (no writes)
python manage.py reset_workflow_data --dry-run

# Confirm interactively (type RESET) or skip prompt
python manage.py reset_workflow_data
python manage.py reset_workflow_data --yes
```

| Kept | Deleted | Vehicle status reset |
|------|---------|----------------------|
| Vehicles, inspection checklist templates, users | Inspections, faults, repairs (+ events/invoices), materials, handovers, procurement, SAP transactions, odometer readings, drivers, PM plans/work orders | `UNDER_REPAIR` and `WAITING_DRIVER_CONFIRMATION` → `ACTIVE` |

The command refuses to run when `DEBUG=False` (staging/production/tests).

---

## Git Workflow

### Branch Strategy

| Branch          | Purpose                                      |
|-----------------|----------------------------------------------|
| `main`          | Production-ready code only                   |
| `develop`       | Integration branch — all features merge here |
| `feat/*`        | Feature / milestone branches                 |
| `fix/*`         | Bug fix branches                             |
| `hotfix/*`      | Emergency production fixes                   |

See `docs/DEVELOPMENT_GUIDE.md` for the current branching and development rules.

### Commit Format

```
type(scope): description

Types:  feat | fix | docs | chore | test | refactor | perf
Scope:  core | domain | vehicle | driver | inspection | fault |
        repair | pm | procurement | sap | api | auth | infra | repo

Examples:
  feat(vehicle): implement create vehicle service
  feat(sap): add PM order BAPI adapter
  fix(repair): handle invalid state transition error
  test(vehicle): add unit tests for create vehicle service
  docs(api): update API contract documentation
  chore(repo): initialize FMMS repository
```

---

## Development Roadmap

The initial milestone history is archived. Current scope and implemented domains are
documented in `docs/PROJECT_OVERVIEW.md`; active defects and production-readiness work
are tracked only in `docs/ENGINEERING_BACKLOG.md`.

---

## Documentation

| Document | Description |
|---|---|
| `docs/index.md` | Documentation entry point and source-of-truth policy |
| `docs/PROJECT_OVERVIEW.md` | Business scope, roles, domains, and workflows |
| `docs/TECHNICAL_ARCHITECTURE.md` | Django architecture, data, API, security, and deployment |
| `docs/SAP_INTEGRATION_GUIDE.md` | SAP concepts and current OData/BAPI implementation |
| `docs/ENGINEERING_BACKLOG.md` | Canonical defects, decisions, priorities, and acceptance criteria |
| `docs/DEVELOPMENT_GUIDE.md` | Setup, Git, testing, CI, and documentation rules |

---

## Code Quality Standards

- **Architecture:** Clean Architecture — zero business logic in controllers
- **Style:** PEP8, enforced by `black` and `isort`
- **Linting:** `ruff` — no warnings tolerated
- **Types:** `mypy` strict mode — every function must have type hints
- **Docs:** Google Style Docstrings on every public class, method, and function
- **Logging:** Structured JSON logging — `print()` is forbidden
- **Tests:** Minimum 80% coverage — domain logic testable without database

---

*FMMS — Built for long-term enterprise maintainability.*
