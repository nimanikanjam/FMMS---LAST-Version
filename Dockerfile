# ──────────────────────────────────────────────────────────────────────────────
# FMMS — Dockerfile
# Python 3.12 slim, non-root user, production-grade layers.
# ──────────────────────────────────────────────────────────────────────────────

FROM python:3.12-slim AS base

# Prevents Python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE=1
# Prevents Python from buffering stdout/stderr
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# System dependencies (psycopg2 build deps)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ── Development Stage ─────────────────────────────────────────────────────────
FROM base AS development

COPY requirements/ ./requirements/
RUN pip install --no-cache-dir -r requirements/development.txt

COPY . .

# Non-root user for development
RUN useradd --create-home --shell /bin/bash fmms
USER fmms

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# ── Production Stage ──────────────────────────────────────────────────────────
FROM base AS production

# Create non-root user before installing packages
RUN useradd --create-home --shell /bin/bash --uid 1001 fmms

COPY requirements/ ./requirements/
RUN pip install --no-cache-dir -r requirements/production.txt

COPY --chown=fmms:fmms . .

USER fmms

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl --fail --silent --show-error http://localhost:8000/api/health/live/ || exit 1

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120"]
