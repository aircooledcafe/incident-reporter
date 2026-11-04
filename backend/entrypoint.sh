#!/usr/bin/env sh
set -e

if [ -z "${DJANGO_SECRET_KEY}" ]; then
    echo "ERROR: DJANGO_SECRET_KEY environment variable is not set." >&2
    echo "Copy .env.example to .env and set DJANGO_SECRET_KEY before starting the containers." >&2
    exit 1
fi

# Ensure external/mapped volume directory exists for investigation artifacts
mkdir -p "${DJANGO_ARTIFACTS_ROOT:-/data/artifacts}"

if [ -n "${POSTGRES_DB}" ]; then
    echo "[Backend] Waiting for PostgreSQL database at ${POSTGRES_HOST:-postgres}:${POSTGRES_PORT:-5432}/${POSTGRES_DB}..."
    python - <<'EOF'
import sys
import time
import os
import psycopg

host = os.environ.get('POSTGRES_HOST', 'postgres')
port = os.environ.get('POSTGRES_PORT', '5432')
dbname = os.environ.get('POSTGRES_DB')
user = os.environ.get('POSTGRES_USER', 'postgres')
password = os.environ.get('POSTGRES_PASSWORD', '')

max_tries = 30
for i in range(1, max_tries + 1):
    try:
        conn = psycopg.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password,
            connect_timeout=3
        )
        conn.close()
        print(f"[Backend] Successfully connected to PostgreSQL on attempt {i}.")
        sys.exit(0)
    except Exception as e:
        print(f"[Backend] PostgreSQL not ready yet ({e}). Retrying in 1s ({i}/{max_tries})...")
        time.sleep(1)

print("[Backend] ERROR: Timed out waiting for PostgreSQL.", file=sys.stderr)
sys.exit(1)
EOF
    echo "[Backend] Running database migrations on PostgreSQL (${POSTGRES_DB})..."
else
    mkdir -p "$(dirname "${DJANGO_DB_PATH:-/data/db/db.sqlite3}")"
    echo "[Backend] Running database migrations on SQLite (${DJANGO_DB_PATH:-/data/db/db.sqlite3})..."
fi

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
