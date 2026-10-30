#!/usr/bin/env sh
set -e

if [ -z "${DJANGO_SECRET_KEY}" ]; then
    echo "ERROR: DJANGO_SECRET_KEY environment variable is not set." >&2
    echo "Copy .env.example to .env and set DJANGO_SECRET_KEY before starting the containers." >&2
    exit 1
fi

# Ensure external/mapped volume directories exist for database (users, sessions, projects) and artifacts
mkdir -p "$(dirname "${DJANGO_DB_PATH:-/data/db/db.sqlite3}")"
mkdir -p "${DJANGO_ARTIFACTS_ROOT:-/data/artifacts}"

echo "[Backend] Running database migrations on ${DJANGO_DB_PATH:-/data/db/db.sqlite3}..."
python manage.py migrate --noinput

echo "[Backend] Checking optional initial Super Admin bootstrap..."
python manage.py ensure_superuser

echo "[Backend] Starting server on 0.0.0.0:8000..."
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "${GUNICORN_WORKERS:-3}" \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
