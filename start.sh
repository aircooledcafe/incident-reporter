#!/usr/bin/env zsh
set -e

export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Starting Django 5.1.14 backend on http://0.0.0.0:8000 ..."
"$ROOT_DIR/backend/.venv/bin/python" "$ROOT_DIR/backend/manage.py" runserver 0.0.0.0:8000 &
BACKEND_PID=$!

trap "kill $BACKEND_PID 2>/dev/null || true" EXIT

echo "Starting React 19.2.6 (react-bootstrap 2.10.10) frontend on http://0.0.0.0:5173 ..."
cd "$ROOT_DIR/frontend"
npm run dev -- --host 0.0.0.0
