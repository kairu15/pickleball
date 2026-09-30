#!/bin/sh
set -e

# Wait for the database to accept connections before migrating.
# Uses DB_ENGINE to know which driver to probe (default: postgres).
DB_ENGINE="${DB_ENGINE:-django.db.backends.postgresql}"

case "$DB_ENGINE" in
    *postgres*)
        DB_HOST_DEFAULT="db"
        DB_PORT_DEFAULT="5432"
        ;;
    *mysql*)
        DB_HOST_DEFAULT="db"
        DB_PORT_DEFAULT="3306"
        ;;
    *sqlite*)
        DB_HOST_DEFAULT=""
        DB_PORT_DEFAULT=""
        ;;
    *)
        echo "Unknown DB_ENGINE '$DB_ENGINE'; assuming postgres-style probe."
        DB_HOST_DEFAULT="db"
        DB_PORT_DEFAULT="5432"
        ;;
esac

DB_HOST="${DB_HOST:-$DB_HOST_DEFAULT}"
DB_PORT="${DB_PORT:-$DB_PORT_DEFAULT}"

if [ -n "$DB_HOST" ]; then
    echo "Waiting for database at $DB_HOST:$DB_PORT..."
    until python - <<PY
import socket, sys
s = socket.socket()
s.settimeout(2)
try:
    s.connect(("$DB_HOST", int("$DB_PORT")))
except OSError:
    sys.exit(1)
finally:
    s.close()
PY
    do
        sleep 1
    done
    echo "Database is up."
fi

# Only the web service runs migrations/collectstatic (RUN_MIGRATIONS=1 in
# docker-compose.yml) so Celery worker/beat containers never race it.
if [ "${RUN_MIGRATIONS:-}" = "1" ]; then
    echo "Applying database migrations..."
    python manage.py migrate --noinput

    echo "Collecting static files..."
    python manage.py collectstatic --noinput
else
    echo "RUN_MIGRATIONS not set; skipping migrate/collectstatic."
fi

# Optional convenience: create a superuser when credentials are provided.
# Never set these in real deployments - use createsuperuser one-off instead.
if [ -n "$DJANGO_SUPERUSER_EMAIL" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
    python manage.py createsuperuser --noinput --email "$DJANGO_SUPERUSER_EMAIL" 2>/dev/null \
        || echo "Superuser already exists or creation skipped."
fi

exec "$@"
