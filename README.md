# SOC Incident Response Evidence & Timeline Reporter

A web-based incident response investigation tool designed for SOC teams to record evidence, build chronological event timelines with MITRE ATT&CK mappings, and generate formatted reports.

---

## Quick Start (Docker Compose)

### 1. Clone & Configure
```bash
git clone git@github.com:aircooledcafe/incident-reporter.git incident-reporter
cd incident-reporter

cp .env.example .env
```

Generate a secure key using `openssl` and paste it into `.env` as `DJANGO_SECRET_KEY`:
```bash
openssl rand -base64 48
```

### 2. Build & Launch
```bash
docker compose up -d --build
```

- **Web Application**: `http://localhost:5173`
- **Backend API**: `http://localhost:8000/api/`
- **Django Database Admin**: `http://localhost:5173/admin/` *(Super Admin only)*

On first launch, opening `http://localhost:5173` automatically prompts you to create the initial **Super Admin** account.

---

## Core Features

- **Investigation Management**: Customer-centric investigations with status tracking (`Triage`, `Investigating`, `Awaiting Customer`, `Contained`, `Closed`), actionable next steps, escalation contacts, and read-only investigation locking.
- **Evidence Timeline**: Record **Atomic Events** and **Search Patterns** with analyst attribution, scoped defanging (assets, IPs, domains, hashes), and MITRE ATT&CK tactic/technique tagging.
- **Artifacts & Attachments**: Dedicated per-investigation disk folders for screenshots, PCAPs, and exported reports, with automatic filesystem cleanup when items or investigations are removed.
- **Report Generation**: Export full timeline `.csv` files and formatted Key Evidence reports in `.odt` (OpenDocument Text) and `.md` (Markdown with screenshot `.zip` bundle).
- **Four-Tier RBAC**: Built-in Django authentication supporting `Super Admin`, `Admin`, `Analyst`, and `Executive` roles with custom profile avatars and granular permissions.
- **REST API**: Comprehensive token-authenticated API for SIEM/SOAR integrations and programmatic ingestion.

---

## Configuration (`.env`)

| Variable | Required | Default | Description |
| :--- | :---: | :--- | :--- |
| `DJANGO_SECRET_KEY` | **Yes** | *(None)* | Cryptographic signing key. Generate with `openssl rand -base64 48`. |
| `DJANGO_DEBUG` | No | `False` | Debug mode. Keep `False` in production. |
| `DJANGO_ALLOWED_HOSTS` | No | `*` | Comma-separated allowed hostnames or IPs. |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | No | *(Empty)* | Trusted origins when running behind HTTPS reverse proxies. |
| `HOST_DB_DIR` | No | `./data` | Host directory mounted to `/data/db` for the SQLite database. |
| `HOST_ARTIFACTS_DIR` | No | `./artifacts` | Host directory mounted to `/data/artifacts` for evidence files and reports. |
| `DJANGO_SUPERUSER_USERNAME` | No | *(Empty)* | Optional username for automated Super Admin creation on startup. |
| `DJANGO_SUPERUSER_PASSWORD` | No | *(Empty)* | Optional password for automated Super Admin creation on startup. |
| `DJANGO_SUPERUSER_EMAIL` | No | *(Empty)* | Optional email for automated Super Admin creation on startup. |
| `APP_PORT` | No | `5173` | Host port for the frontend Nginx web server. |
| `BACKEND_PORT` | No | `8000` | Host port for the backend API. |
| `GUNICORN_WORKERS` | No | `3` | Gunicorn worker process count. |

---

## Persistent Storage & Backups

All state is externalized to the host filesystem:

- **`HOST_DB_DIR` (`./data`)**: Stores `db.sqlite3` with Write-Ahead Logging (`WAL`) enabled for fast, concurrent reads and writes.
- **`HOST_ARTIFACTS_DIR` (`./artifacts`)**: Stores evidence screenshots, PCAPs, user avatars, and exported reports.

### Online Database Backup
Create a consistent, safe backup while the application is actively running:
```bash
docker compose exec backend python -c "import sqlite3; s=sqlite3.connect('/data/db/db.sqlite3'); d=sqlite3.connect('/data/db/backup.sqlite3'); s.backup(d); d.close()"
```
Copy `data/backup.sqlite3` together with `./artifacts/` for a complete backup.

### Fresh Instance Reset
To wipe existing data and start completely fresh:
```bash
docker compose down
rm -f ./data/db.sqlite3*
rm -rf ./artifacts/*
docker compose up -d --build
```

---

## Local Development (Without Docker)

### Prerequisites
- Python 3.10+
- Node.js 18+ and npm

### 1. Setup Backend
```bash
cp .env.example .env
# Set DJANGO_SECRET_KEY in .env (generate with openssl rand -base64 48)

cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
cd ..
```

### 2. Setup Frontend
```bash
cd frontend
npm install --legacy-peer-deps
cd ..
```

### 3. Run Application
```bash
./start.sh
```

### 4. Run Test Suite
```bash
cd backend
.venv/bin/python manage.py test investigations
```

---

## Documentation & Reference

- 📄 **[AWS Production Deployment Guide (`DEPLOYMENT_AWS.md`)](DEPLOYMENT_AWS.md)** — Step-by-step EC2 setup, EBS persistence, and Cloudflare Tunnel guide.
- 📄 **[REST API Specification (`API_SPECIFICATION.md`)](API_SPECIFICATION.md)** — Full endpoint schemas and ingestion scripts.
- 📄 **[Software Bill of Materials (`BOM.md`)](BOM.md)** — Component inventory and license compliance.
- 📄 **[Theme & Color System (`theme.md`)](theme.md)** — LevelBlue design tokens, status badges, and UI palette.
- 📄 **[Sample Investigation API Demos (`demo/`)](demo/)** — Standalone API walkthroughs and Python ingestion scripts for sample scenarios.
