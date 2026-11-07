#!/usr/bin/env zsh
set -e

export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ -f "$ROOT_DIR/.env" ]; then
  set -a
  source "$ROOT_DIR/.env"
  set +a
fi

if [ -z "${DJANGO_SECRET_KEY}" ]; then
  echo "ERROR: DJANGO_SECRET_KEY is not set." >&2
  echo "Run: cp .env.example .env && set DJANGO_SECRET_KEY in .env (e.g. openssl rand -base64 48)" >&2
  exit 1
fi

# Verify PostgreSQL is configured and reachable
if [ -z "${POSTGRES_DB}" ]; then
  echo "ERROR: POSTGRES_DB is not set in .env." >&2
  exit 1
fi

PG_CHECK_HOST="${POSTGRES_HOST:-localhost}"
if [ "$PG_CHECK_HOST" = "postgres" ]; then
  PG_CHECK_HOST="localhost"
  export POSTGRES_HOST="localhost"
fi
if ! nc -z "$PG_CHECK_HOST" "${POSTGRES_PORT:-5432}" 2>/dev/null; then
  echo "ERROR: PostgreSQL is not reachable at $PG_CHECK_HOST:${POSTGRES_PORT:-5432}." >&2
  echo "Start PostgreSQL or launch the full stack with: docker compose up --build -d" >&2
  exit 1
fi

echo "Applying Django migrations & checking optional initial Super Admin..."
"$ROOT_DIR/backend/.venv/bin/python" "$ROOT_DIR/backend/manage.py" migrate --noinput
"$ROOT_DIR/backend/.venv/bin/python" "$ROOT_DIR/backend/manage.py" ensure_superuser

echo "Starting Django 5.1.14 backend on http://0.0.0.0:8000 ..."
"$ROOT_DIR/backend/.venv/bin/python" "$ROOT_DIR/backend/manage.py" runserver 0.0.0.0:8000 &
BACKEND_PID=$!

trap "kill $BACKEND_PID 2>/dev/null || true" EXIT

echo "Starting React 19.2.6 (react-bootstrap 2.10.10) frontend on http://0.0.0.0:5173 ..."
cd "$ROOT_DIR/frontend"
npm run dev -- --host 0.0.0.0
