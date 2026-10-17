# SOC Incident Response Evidence & Timeline Reporter

A full-stack incident response evidence recording, chronological timeline construction, and reporting application designed to integrate into existing SOC environments.

---

## Technology Stack & Pinned Versions

- **Backend**: Python (`>=3.10`) + **Django `5.1.14`** + Django REST Framework (`3.17.2`) + `django-cors-headers` (`4.9.0`) + `odfpy` (`1.4.1`) + `Pillow` (`13.0.0`)
- **Frontend**: **React `19.2.6`** (`react-dom@19.2.6`) + **`react-bootstrap@2.10.10`** + **`@restart/hooks@0.4.16`** + Vite (`6.x`)

---

## Key Features

1. **Incident Project Overview & Archive Folder Provisioning**
   - Supports **Title**, **Customer Name**, **Customer ID**, **Ticket ID**, **Ticket Link**, **Summary of Incident**, **Key Assets Affected**, **Key Users Affected**, **Key Malicious Indicators**, and **External Research** links & summaries (each individually removable).
   - Automatically provisions a dedicated investigation folder (`artifacts/project_<id>_<slug>/`) containing `screenshots/`, `reports/`, and a live-synced `archive_manifest.json`.
   - Investigation status management (`Open / Triage`, `Investigating`, `Contained`, `Archived / Closed`) with a header status picker, confirmation warning when closing/archiving, and a sidebar toggle to show/hide archived investigations.

2. **Multi-Analyst Evidence Collection & Chronological Timeline**
   - Multiple analysts (e.g., *Chrisjen Avasarala* and *James Holden*) can contribute evidence concurrently.
   - **Atomic Events (`ATOMIC`)**: Linked to a single IDS or log event (Timestamp, Summary, Affected Asset, Affected User, Malicious Hosts/IPs, Commands Run, MITRE Tactic & Technique, Related Log/IDS Link, Freeform Notes, Screenshots, and Key Evidence flag).
   - **Search Result Evidence (`SEARCH`)**: Pattern of activity over a time window (Start Timestamp used for timeline ordering, End Timestamp, Summary, Affected Asset, Affected User with **Created by Attacker** flag, Malicious Hosts/IPs, Commands Run, MITRE Tactic & Technique, Search Result Link, Search Query Link, Freeform Notes, Screenshots, and Key Evidence flag).
   - **Scoped Defanging**: Automatically defangs affected or malicious assets, hostnames, domains, files, IPs, and URLs (`192.168[.]1.1`, `domain[.]com`, `hxxps[:]//`, `payload[.]exe`) while keeping analyst-provided links to logs, searches, and external threat intelligence intact and clickable.

3. **Two Incident Report Outputs**
   - **Report 1 — Evidence Timeline Report (`.csv`)**: Time-ordered CSV export of **all** recorded evidence items, including MITRE ATT&CK Tactics and Techniques.
   - **Report 2 — Key Evidence Formatted Report (`.odt` OpenDocument Text & `.md` Markdown)**:
     - Includes **only items flagged as Key Evidence**, ordered chronologically.
     - Structured with **Title**, **Summary of Incident**, **Key Evidence Timeline** (`TIMESTAMP, ASSET, USER:` followed by Analyst notes, Key malicious indicators, embedded Screenshots, and Links), and three **Summary Tables at the bottom** (*Key Assets Affected*, *Key Malicious Indicators*, and *MITRE Tactics and Techniques*).
     - The Markdown export automatically creates a dedicated `key_evidence_screenshots_project_<id>/` folder alongside the `.md` report and links to the images there (also downloadable as a `.zip` bundle).

---

## Local Deployment Guide

### Prerequisites
- **Python** `3.10+` (or [`uv`](https://docs.astral.sh/uv/))
- **Node.js** `18+` and **npm**

---

### 1. Clone the Repository
```bash
git clone <YOUR_GITHUB_REPO_URL> incident-reporter
cd incident-reporter
```

### 2. Backend Setup (Django 5.1.14)
Create a virtual environment in `backend/.venv`, install dependencies, and run database migrations:

```bash
cd backend

# Option A: Using standard python3 venv + pip
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Option B: Using uv (optional, faster)
# uv venv .venv
# uv pip install --python .venv/bin/python -r requirements.txt

# Apply database migrations
.venv/bin/python manage.py migrate
cd ..
```

### 3. Frontend Setup (React 19.2.6 + React-Bootstrap 2.10.10)
Install the Node dependencies using `--legacy-peer-deps` (ensuring `react-bootstrap@2.10.10` and `@restart/hooks@0.4.16` install cleanly alongside `react@19.2.6`):

```bash
cd frontend
npm install --legacy-peer-deps
cd ..
```

---

### 4. Running the Application Locally

#### Quick Start (Single Command)
From the project root directory, run:
```bash
./start.sh
```
This starts:
- **Django Backend API**: `http://0.0.0.0:8000`
- **React Frontend UI**: `http://localhost:5173` (or `http://<SERVER_LAN_IP>:5173` from another host on the internal network)

*(In the web UI, click **"Load Sample Incident"** in the top navigation bar to populate the 20-event / 7-key-event demo investigation with sample analysts **Chrisjen Avasarala** and **James Holden**.)*

#### Starting Backend & Frontend Separately (Manual)
1. **Terminal 1 — Django Backend**:
   ```bash
   cd backend
   .venv/bin/python manage.py runserver 0.0.0.0:8000
   ```
2. **Terminal 2 — React Frontend**:
   ```bash
   cd frontend
   npm run dev -- --host 0.0.0.0
   ```

---

### 5. Running Automated Tests
To run the Django backend test suite (covering project folder creation, defanging, chronological ordering, CSV/ODT/Markdown report generation, screenshot deletion, and the 20-event demo seed):

```bash
cd backend
.venv/bin/python manage.py test incidents
```

---

## SOC Tool Programmatic Ingestion API

External Python/Django SIEM, SOAR, or IDS scripts can push evidence into an active project via `POST /api/soc/ingest/`:

```bash
curl -X POST http://127.0.0.1:8000/api/soc/ingest/ \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_id": "SOC-2026-9041",
    "evidence_type": "ATOMIC",
    "analyst_name": "James Holden",
    "timestamp": "2026-10-17T03:15:00Z",
    "summary": "Outbound C2 beacon blocked at perimeter firewall",
    "affected_asset": "DC-PROD-01 (10.20.0.10)",
    "malicious_hosts_ips": "45.155.205.109, c2.ceres-telemetry.net",
    "mitre_tactic": "Command and Control (TA0011)",
    "mitre_technique": "T1071.001 - Web Protocols",
    "related_log_link": "https://siem.internal.example/events/fw-99201",
    "is_key_evidence": true
  }'
```
