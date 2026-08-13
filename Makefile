# ──────────────────────────────────────────────────────────────────────────────
# FMMS Makefile
# ──────────────────────────────────────────────────────────────────────────────

.PHONY: help run stop build test lint format migrate shell \
        worker beat createsuperuser logs clean check

PYTHON := python3
PIP    := pip3
VENV   := .venv
MANAGE := $(PYTHON) manage.py

# Default: show help
help:
	@echo ""
	@echo "  FMMS — Fleet Maintenance Management System"
	@echo ""
	@echo "  Usage: make <target>"
	@echo ""
	@echo "  Docker:"
	@echo "    make run          Start all services (db, redis, app)"
	@echo "    make stop         Stop all services"
	@echo "    make build        Rebuild Docker images"
	@echo "    make logs         Tail application logs"
	@echo ""
	@echo "  Development:"
	@echo "    make install      Install development dependencies"
	@echo "    make migrate      Run Django database migrations"
	@echo "    make shell        Open Django shell"
	@echo "    make createsuperuser  Create an admin user"
	@echo ""
	@echo "  Celery:"
	@echo "    make worker       Start Celery worker"
	@echo "    make beat         Start Celery beat scheduler"
	@echo ""
	@echo "  Quality:"
	@echo "    make test         Run full test suite with coverage"
	@echo "    make lint         Run black + isort + ruff + mypy checks"
	@echo "    make format       Auto-format code (black + isort)"
	@echo "    make check        Run Django system check"
	@echo ""
	@echo "  Cleanup:"
	@echo "    make clean        Remove cache, coverage, and .pyc files"
	@echo ""

# ── Docker ────────────────────────────────────────────────────────────────────

run:
	docker compose up --remove-orphans

run-d:
	docker compose up -d --remove-orphans

stop:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f app

# ── Local Development ─────────────────────────────────────────────────────────

install:
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip
	$(VENV)/bin/pip install -r requirements/development.txt
	@echo ""
	@echo "  Virtual environment ready. Activate with:"
	@echo "    source $(VENV)/bin/activate"
	@echo ""

migrate:
	$(MANAGE) migrate

makemigrations:
	$(MANAGE) makemigrations

shell:
	$(MANAGE) shell

createsuperuser:
	$(MANAGE) createsuperuser

check:
	$(MANAGE) check

# ── Celery ────────────────────────────────────────────────────────────────────

worker:
	celery -A infrastructure.messaging.celery_app worker --loglevel=info

beat:
	celery -A infrastructure.messaging.celery_app beat --loglevel=info

# ── Code Quality ──────────────────────────────────────────────────────────────

lint:
	@echo "── black ───────────────────────────────────────"
	black --check .
	@echo "── isort ───────────────────────────────────────"
	isort --check .
	@echo "── ruff ────────────────────────────────────────"
	ruff check .
	@echo "── mypy ────────────────────────────────────────"
	mypy .
	@echo ""
	@echo "  All checks passed."

format:
	@echo "── black ───────────────────────────────────────"
	black .
	@echo "── isort ───────────────────────────────────────"
	isort .
	@echo ""
	@echo "  Formatting complete."

# ── Tests ─────────────────────────────────────────────────────────────────────

test:
	pytest --cov --cov-report=term-missing --cov-report=html

test-fast:
	pytest -x --no-cov

test-unit:
	pytest tests/unit/ --no-cov

test-integration:
	pytest tests/integration/

# ── Cleanup ───────────────────────────────────────────────────────────────────

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	rm -f .coverage coverage.xml
	@echo "  Cleaned."
