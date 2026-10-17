#!/usr/bin/env sh
set -e

# Ensure mapped volume directories exist
mkdir -p "$(dirname "${DJANGO_DB_PATH:-/data/db/db.sqlite3}")"
mkdir -p "${DJANGO_ARTIFACTS_ROOT:-/data/artifacts}"

echo "[Backend] Running database migrations on ${DJANGO_DB_PATH:-/data/db/db.sqlite3}..."
python manage.py migrate --noinput

echo "[Backend] Starting server on 0.0.0.0:8000..."
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "${GUNICORN_WORKERS:-3}" \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
