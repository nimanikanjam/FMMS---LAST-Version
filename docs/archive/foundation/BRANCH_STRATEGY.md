# FMMS Branch Strategy

> Git branching model for the FMMS project.
> All engineers must follow this strategy without exception.

---

## Branch Model

FMMS uses a **trunk-based development model with milestone feature branches**.

```
main  ────────────────────────────────────────────────────────► (production)
  ▲                  ▲                  ▲
  │   merge          │   merge          │   merge
  │                  │                  │
develop  ────────────────────────────────────────────────────►
  ▲        ▲         ▲        ▲         ▲
  │        │         │        │         │
feat/    feat/     fix/     feat/     hotfix/
m1-...   m2-...   ...      m3-...    ...
```

---

## Branch Types

### `main`
- **Purpose:** Production-ready code only.
- **Merges from:** `develop` (via PR) or `hotfix/*`
- **Protection rules:**
  - No direct pushes.
  - Requires PR with at least one review.
  - All CI checks must pass before merge.
  - Tagged on every merge: `vX.Y.Z`

### `develop`
- **Purpose:** Integration branch. All completed milestone branches merge here.
- **Merges from:** `feat/*`, `fix/*`
- **Protection rules:**
  - No direct pushes.
  - Requires PR.
  - All CI checks must pass.

### `feat/milestone-N-<name>`
- **Purpose:** One branch per milestone, as defined in `IMPLEMENTATION_TRACKER.md`.
- **Created from:** `develop`
- **Merges into:** `develop`
- **Naming examples:**
  - `feat/milestone-1-foundation`
  - `feat/milestone-2-domain`
  - `feat/milestone-4-sap-integration`
- **Rules:**
  - One milestone = one branch.
  - Never mix milestone work on a single branch.
  - Must pass all quality checks before PR.

### `feat/<scope>-<short-description>`
- **Purpose:** Sub-feature branches for larger milestones, if a milestone needs to be split.
- **Created from:** `develop` or the milestone branch.
- **Naming examples:**
  - `feat/vehicle-sap-sync`
  - `feat/repair-state-machine`
- **Rules:**
  - Keep short-lived — merge within the same sprint.

### `fix/<scope>-<short-description>`
- **Purpose:** Bug fixes discovered during development (non-production).
- **Created from:** `develop`
- **Merges into:** `develop`
- **Naming examples:**
  - `fix/sap-retry-failure`
  - `fix/vehicle-not-found-error`

### `hotfix/<scope>-<short-description>`
- **Purpose:** Emergency fixes for production issues only.
- **Created from:** `main`
- **Merges into:** `main` AND `develop` (to keep them in sync)
- **Naming examples:**
  - `hotfix/sap-transaction-deadlock`
  - `hotfix/auth-token-expiry`

---

## Commit Format

Every commit must follow the **Conventional Commits** specification.

### Format

```
type(scope): description

[optional body]

[optional footer]
```

### Types

| Type | When to Use |
|---|---|
| `feat` | New feature or capability |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `chore` | Build, tooling, repository setup |
| `test` | Adding or fixing tests |
| `refactor` | Code restructuring without behavior change |
| `perf` | Performance improvement |

### Scopes

| Scope | Domain |
|---|---|
| `repo` | Repository structure, git, CI |
| `core` | Cross-cutting concerns (logging, exceptions, middleware) |
| `domain` | Domain layer changes |
| `infra` | Infrastructure layer |
| `auth` | Authentication / User model |
| `vehicle` | Vehicle domain |
| `driver` | Driver domain |
| `inspection` | Inspection domain |
| `fault` | Fault domain |
| `repair` | Repair domain |
| `pm` | Preventive maintenance domain |
| `procurement` | Procurement domain |
| `sap` | SAP integration layer |
| `api` | Interface / REST API layer |
| `celery` | Background task changes |
| `config` | Settings / configuration |

### Examples

```bash
chore(repo): initialize FMMS repository
feat(core): initialize project foundation and configuration
feat(domain): define domain entities and repository interfaces
feat(infra): create ORM models and repositories for all domains
feat(sap): implement SAP integration layer with transaction management
feat(vehicle): implement create vehicle service
feat(api): implement REST API v1 for all domains
fix(sap): handle retry failure on BAPI connection timeout
test(repair): add unit tests for repair order state machine
docs(api): update API contract documentation
```

---

## Milestone Workflow

For every milestone in `IMPLEMENTATION_TRACKER.md`:

```
1. Create branch from develop
   git checkout develop
   git checkout -b feat/milestone-N-<name>

2. Implement milestone tasks (one logical change per commit)

3. Before committing:
   make lint        # black + isort + ruff + mypy — zero violations
   make test        # pytest — all pass

4. Commit with prescribed message
   git commit -m "feat(scope): description"

5. Update IMPLEMENTATION_TRACKER.md
   git commit -m "docs(repo): update tracker for milestone N completion"

6. Open PR into develop
   - Title: same as commit message
   - Description: link to tracker milestone, list changed files
   - Request review

7. After PR merged: start next milestone
```

---

## Tagging Strategy

| Tag Format | When | Example |
|---|---|---|
| `vX.Y.Z` | Production release | `v1.0.0` |
| `vX.Y.Z-phase1-foundation` | Phase milestone | `v0.1.0-phase1-foundation` |
| `vX.Y.Z-rcN` | Release candidate | `v1.0.0-rc1` |

### Semantic Versioning Rules

- **Major (X):** Breaking API or database change
- **Minor (Y):** New feature, backward compatible
- **Patch (Z):** Bug fix, no new features

---

## CI/CD Enforcement

Every push to any branch must pass:

```
[ ] black --check .
[ ] isort --check .
[ ] ruff check .
[ ] mypy .
[ ] pytest --cov --cov-fail-under=80
[ ] python manage.py check
```

No branch may be merged if any CI check fails.

---

## Forbidden Practices

| Practice | Reason |
|---|---|
| `git push --force` to `main` or `develop` | Risk of losing shared history |
| Committing `.env` files | Security — secrets must never be committed |
| Committing `config.ini` from prototypes | Contains SAP credentials |
| Huge monolithic commits | Violates single logical change rule |
| Merging without tests passing | Breaks CI pipeline |
| Direct commits to `main` or `develop` | Bypasses review and CI |
| Committing debug code (`print()`, `breakpoint()`) | Code quality |

---

*Last updated: 2026-07-09*
