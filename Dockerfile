FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Build dependencies for mysqlclient (pulled in by requirements.txt). The same
# layer installs the Python packages so the toolchain stays cacheable; a
# multi-stage runtime split can trim the image later if needed.
RUN apt-get update && apt-get install -y --no-install-recommends \
        default-libmysqlclient-dev \
        pkg-config \
        gcc \
        libpq5 \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt requirements-prod.txt ./
RUN pip install -r requirements-prod.txt

COPY . .

# Non-root runtime user; owns the dirs the app writes to (media, staticfiles).
RUN addgroup --system picklesphere \
    && adduser --system --ingroup picklesphere picklesphere \
    && mkdir -p /app/media /app/staticfiles \
    && chown -R picklesphere:picklesphere /app
USER picklesphere

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/health/ || exit 1

# Entrypoint waits for the database, applies migrations, collects static
# files, then execs the container command (ASGI server or a one-off task).
ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "picklesphere.asgi:application"]
