# Incident Reporter REST API Specification

This document provides a comprehensive reference and usage guide for the **Incident Reporter REST API**. It details authentication, RBAC boundaries, object schemas, query parameters, error formats, and all available endpoints—including single and bulk evidence ingestion, SIEM/SOAR webhook automation, customer directory management, and report exports.

---

## 1. Architecture & Protocol Overview

- **Base URL**:
  - **Deployed / Customer Domain**: `https://soc-demo.aircooledcafe.com/api` (Standard HTTPS on port 443. The reverse proxy / Nginx routes `/api/` traffic directly to the backend. **Do not target port 8000 on a deployed domain**).
  - **Local Development**: `http://localhost:8000/api` (direct backend) or `http://localhost:5173/api` (Vite dev proxy).
- **Data Exchange Format**: `application/json` (UTF-8 encoded) for all endpoints, except file uploads (`multipart/form-data`) and exported reports (`text/csv`, `text/markdown`, `application/zip`, `application/vnd.oasis.opendocument.text`).
- **Defanging & Sanitization**: Any IP addresses, hostnames, and URLs submitted via the API or web interface are automatically defanged when rendered in timeline summaries and reports (e.g. `10[.]10[.]10[.]10`, `hxxp://...`).
- **Embedded Document Sync**: When evidence items are created, updated, or bulk-ingested, the parent investigation's embedded JSON `timeline_events` column and its disk archive manifest (`archive_manifest.json`) are automatically synchronized.

---

## 2. Authentication & Authorization (RBAC)

The API supports **Token Authentication** (`rest_framework.authentication.TokenAuthentication`) for programmatic clients, scripts, and SIEM/SOAR platforms, alongside standard Django session authentication for the browser web UI.

### 2.1 Generating / Retrieving Your API Token

Each user account has a dedicated API token. Analysts, Admins, and Super Admins can obtain or regenerate their token via the web UI (**Account Menu -> Account, Avatar & Preferences -> Password & API Token**) or programmatically:

#### `GET /api/auth/api-token/`
Retrieves the active user's persistent API token.
```bash
curl -s -X GET http://127.0.0.1:8000/api/auth/api-token/ \
  -H "Cookie: sessionid=<SESSION_COOKIE>"
```

**Response (200 OK):**
```json
{
  "token": "7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b",
  "created_at": "2026-11-04T12:00:00Z"
}
```

#### `POST /api/auth/api-token/`
Regenerates and rotates the user's API token. Any previous token is immediately invalidated.

### 2.2 Using the Token in API Calls
Pass the token in the `Authorization` HTTP header on all subsequent requests:
```http
Authorization: Token 7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b
```

### 2.3 Role-Based Access Control (RBAC) Boundaries

| Role | Read Access | Create/Edit Investigations | Bulk Evidence Ingest | Lock / Unlock | Delete Investigations | User Administration | Direct DB (`/admin/`) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`EXECUTIVE`** | Yes | No (Read-only) | No (HTTP 403) | No | No | No | No |
| **`ANALYST`** | Yes | Yes (Unlocked only) | Yes (Unlocked only) | No | No | No | No |
| **`ADMIN`** | Yes | Yes (Unlocked only) | Yes (Unlocked only) | **Yes** | **Yes** (Unlocked) | Yes (Analyst/Exec) | No |
| **`SUPER_ADMIN`**| Yes | Yes (Unlocked only) | Yes (Unlocked only) | **Yes** | **Yes** (Unlocked) | **Yes** (All Roles) | **Yes** |

---

## 3. Customer Directory & Escalation Contacts

Investigations are associated with a customer organization. Customers and their multi-tier escalation contacts can be queried and managed programmatically using their business **Customer ID** (e.g. `SCAD-01`, `CANTON-FIN-01`).

### 3.1 Customer Endpoints

#### `GET /api/customers/`
Lists all registered customer organizations.

#### `GET /api/customers/{customer_id}/`
Retrieves a customer organization directly by its `customer_id` code (e.g. `/api/customers/SCAD-01/`) or numeric PK.

```bash
curl -X GET https://soc-demo.aircooledcafe.com/api/customers/SCAD-01/ \
  -H "Authorization: Token <TOKEN>"
```

**Response (200 OK):**
```json
{
  "id": 1,
  "name": "Scadrial Metallurgy Syndicate",
  "customer_id": "SCAD-01",
  "notes": "Primary metal refineries & logistics network",
  "contacts": [
    {
      "id": 4,
      "customer": 1,
      "name": "Breeze Ladrian",
      "role_title": "Head of Corporate Communications",
      "email": "breeze@scadrial-metals.corp",
      "phone": "+1-555-0192",
      "escalation_tier": "PRIMARY",
      "is_primary_escalation": true,
      "notes": "24/7 incident response bridge contact"
    }
  ],
  "investigations_count": 2,
  "created_at": "2026-11-04T10:00:00Z",
  "updated_at": "2026-11-04T10:00:00Z"
}
```

#### `POST /api/customers/`
Creates a new customer organization.
```bash
curl -X POST https://soc-demo.aircooledcafe.com/api/customers/ \
  -H "Authorization: Token <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Luthadel Security Ops",
    "customer_id": "LUTH-SEC-01",
    "notes": "Central garrison infrastructure monitoring"
  }'
```

#### `DELETE /api/customers/{customer_id}/`
Deletes a customer organization (referenced by its `customer_id` or PK).
> [!IMPORTANT]
> A customer **cannot** be deleted if active or archived investigations are linked to it (HTTP 403 Forbidden). You must delete or reassign all linked investigations before deleting the customer.

### 3.2 Escalation Contact Endpoints

#### `POST /api/customer-contacts/`
Adds an escalation contact to a customer organization. The `customer` field accepts the business `customer_id` code:
```bash
curl -X POST https://soc-demo.aircooledcafe.com/api/customer-contacts/ \
  -H "Authorization: Token <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "customer": "SCAD-01",
    "name": "Elend Venture",
    "role_title": "Chief Information Security Officer",
    "email": "elend@scadrial-metals.corp",
    "phone": "+1-555-0144",
    "escalation_tier": "PRIMARY",
    "notes": "Authorized for incident declaration & shutdown approvals"
  }'
```

Valid `escalation_tier` choices: `"PRIMARY"`, `"SECONDARY"`, `"TERTIARY"`.

---

## 4. Investigations (Projects) API

The `/api/investigations/` (aliased to `/api/projects/`) endpoint manages root investigation records.

All investigation endpoints accept human-usable **Investigation IDs in format `INV123456`** (e.g. `/api/investigations/INV000001/`, `/api/investigations/INV000009/`, or `/api/investigations/INV123456/`).

### 4.1 Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/investigations/` | List investigations. Filter by `?status=OPEN`, `?customer=SCAD-01`, `?is_locked=true`. |
| `POST` | `/api/investigations/` | Create investigation. Accepts `"customer": "SCAD-01"`. Returns assigned `investigation_id` (`INV######`). |
| `GET` | `/api/investigations/{INV123456}/` | Retrieve investigation detail using its `INV######` ID. |
| `PATCH` | `/api/investigations/{INV123456}/` | Update investigation metadata, overview, status, or action plans (unlocked only). |
| `DELETE` | `/api/investigations/{INV123456}/` | Delete investigation and purge associated artifacts (Admin / Super Admin only; unlocked only). |
| `POST` | `/api/investigations/{INV123456}/lock/` | Lock investigation to read-only state (Admin / Super Admin only). |
| `POST` | `/api/investigations/{INV123456}/unlock/` | Unlock investigation for edits (Admin / Super Admin only). |
| `POST` | `/api/investigations/seed_demo/` | Seed sample scenario: `{"scenario": "expanse" \| "matrix" \| "god_of_war" \| "all"}` (Super Admin only). |
| `GET` | `/api/investigations/{INV123456}/export_csv/` | Export CSV timeline attachment. |
| `GET` | `/api/investigations/{INV123456}/report_md/` | Export Markdown report attachment (`?bundle=true` downloads full ZIP bundle with images). |
| `GET` | `/api/investigations/{INV123456}/report_odt/` | Export LibreOffice / Word `.odt` report document. |

### 4.2 Investigation Schema
```json
{
  "investigation_id": "INV123456",
  "customer": "SCAD-01",
  "title": "Operation Mistborn: Steel Ministry Perimeter Breach",
  "status": "INVESTIGATING",
  "ticket_id": "INC-2026-8801",
  "ticket_link": "https://jira.internal.corp/browse/INC-2026-8801",
  "lead_analyst": "Vin of Luthadel",
  "summary": "Sophisticated multi-stage compromise targeting allomantic metal inventory databases.",
  "scope": "Perimeter firewalls, SCADA telemetry sensors, and corporate Active Directory.",
  "impact": "Exfiltration of high-value metallurgy formulas and disruption of sensor monitoring.",
  "immediate_actions": "Isolated compromised vault subnets; revoked compromised administrative credentials.",
  "long_term_actions": "Deploy multi-factor authentication across all engineering workstations; re-key certificates."
}
```

Status choices: `"OPEN"`, `"INVESTIGATING"`, `"CONTAINED"`, `"ARCHIVED"`.

---

## 5. Bulk Evidence Creation API

When ingesting multiple forensic artifacts, log extracts, or timeline events from external tools, scripts, or SIEM systems, the **Bulk Evidence Ingestion API** provides maximum throughput, single-transaction atomic consistency, and timeline optimization.

### 5.1 Endpoints

- **`POST /api/evidence/bulk_create/`** (or `/api/evidence/bulk/`, `/api/evidence-items/bulk_create/`)
- **`POST /api/investigations/{id}/bulk-evidence/`** (or `/api/investigations/{id}/bulk_evidence/`)

### 5.2 Performance & Design Advantages
1. **Single Network Round-Trip**: Ingests dozens or hundreds of items in a single HTTP request instead of issuing individual calls.
2. **Atomic Consistency (`transaction.atomic`)**: If any single item fails validation (e.g. invalid date format or malformed enum), the entire transaction rolls back cleanly with HTTP 400. No partial or corrupted state is saved.
3. **Single Timeline Sync**: Recalculates and sorts the parent investigation's embedded `timeline_events` document column and updates the disk archive manifest **once** at the end of the batch, rather than rebuilding the timeline N consecutive times.
4. **Automatic Default Analyst**: If `analyst_name` is omitted on individual items, it defaults automatically to the authenticated API user's display name.

### 5.3 Request Formats

#### Option A: Top-Level Investigation Container (Recommended)
Pass the target `investigation` ID at the root level alongside an `items` array:

```bash
curl -X POST http://127.0.0.1:8000/api/evidence/bulk_create/ \
  -H "Authorization: Token <YOUR_API_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "investigation": 12,
    "items": [
      {
        "evidence_type": "ATOMIC",
        "timestamp": "2026-10-31T08:00:00Z",
        "summary": "Spearphishing email delivered to logistics supervisor",
        "affected_asset": "WS-LOGISTICS-04 (10.10.4.15)",
        "affected_user": "dock_manager",
        "malicious_hosts_ips": "phish.evil-infiltrator.net",
        "mitre_tactic": "Initial Access (TA0001)",
        "mitre_technique": "T1566.002 - Spearphishing Link",
        "related_log_link": "https://siem.internal/events/phish-441"
      },
      {
        "evidence_type": "ATOMIC",
        "timestamp": "2026-10-31T08:35:00Z",
        "summary": "Mimikatz LSASS memory dump executed via stolen administrator credentials",
        "affected_asset": "DC-PROD-01 (10.10.0.10)",
        "affected_user": "domain_admin_svc",
        "commands_run": "mimikatz.exe \"privilege::debug\" \"sekurlsa::logonpasswords\" exit",
        "mitre_tactic": "Credential Access (TA0006)",
        "mitre_technique": "T1003.001 - LSASS Memory",
        "is_key_evidence": true
      },
      {
        "evidence_type": "SEARCH",
        "timestamp": "2026-10-31T09:00:00Z",
        "end_timestamp": "2026-10-31T09:45:00Z",
        "summary": "Sustained encrypted exfiltration over HTTPS to external VPS",
        "affected_asset": "VAULT-SRV-02 (10.10.2.20)",
        "malicious_hosts_ips": "185.220.101.55, c2.steel-ministry.org",
        "mitre_tactic": "Exfiltration (TA0010)",
        "mitre_technique": "T1048 - Exfiltration Over Alternative Protocol",
        "search_query_link": "index=firewall bytes_out > 1000000000 dest_ip=185.220.101.55",
        "is_key_evidence": true
      }
    ]
  }'
```

#### Option B: Direct Array Ingestion
Post an array of item objects directly. Each item specifies its `investigation` (or inherits target from URL):

```bash
curl -X POST http://127.0.0.1:8000/api/investigations/12/bulk-evidence/ \
  -H "Authorization: Token <YOUR_API_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '[
    {
      "evidence_type": "ATOMIC",
      "timestamp": "2026-10-31T10:00:00Z",
      "summary": "Ransom note dropped in all public network shares",
      "affected_asset": "FS-PROD-01",
      "mitre_tactic": "Impact (TA0040)",
      "mitre_technique": "T1486 - Data Encrypted for Impact",
      "is_key_evidence": true
    }
  ]'
```

### 5.4 Bulk Ingestion Success Response (HTTP 201 Created)
```json
{
  "status": "success",
  "count": 3,
  "items": [
    {
      "id": 101,
      "investigation": 12,
      "project": 12,
      "evidence_type": "ATOMIC",
      "evidence_type_display": "Atomic Event",
      "analyst_name": "Vin of Luthadel",
      "created_by": 2,
      "created_by_username": "vin_analyst",
      "can_actor_delete": true,
      "timestamp": "2026-10-31T08:00:00Z",
      "end_timestamp": null,
      "summary": "Spearphishing email delivered to logistics supervisor",
      "affected_asset": "WS-LOGISTICS-04 (10.10.4.15)",
      "affected_user": "dock_manager",
      "user_created_by_attacker": false,
      "malicious_hosts_ips": "phish[.]evil-infiltrator[.]net",
      "commands_run": "",
      "mitre_tactic": "Initial Access (TA0001)",
      "mitre_technique": "T1566.002 - Spearphishing Link",
      "related_log_link": "https://siem.internal/events/phish-441",
      "search_result_link": "",
      "search_query_link": "",
      "notes": "",
      "is_key_evidence": false,
      "screenshots": [],
      "pcaps": [],
      "created_at": "2026-11-04T12:30:00Z",
      "updated_at": "2026-11-04T12:30:00Z"
    }
  ]
}
```

### 5.5 Bulk Ingestion Validation Failure Response (HTTP 400 Bad Request)
When validation fails, no records are saved to the database:
```json
{
  "error": "Validation failed for one or more evidence items. No items were saved.",
  "details": [
    {
      "index": 1,
      "errors": {
        "evidence_type": ["\"INVALID\" is not a valid choice."],
        "timestamp": ["Datetime has wrong format. Use one of these formats instead: YYYY-MM-DDThh:mm[:ss[.uuuuuu]][+HH:MM|-HH:MM|Z]."]
      }
    }
  ]
}
```

---

## 6. Single Evidence Items & Attachments

### 6.1 Individual Evidence Item Management
- **`POST /api/evidence/`**: Ingest a single evidence item.
- **`GET /api/evidence/{id}/`**: Retrieve evidence item detail.
- **`PATCH /api/evidence/{id}/`**: Modify evidence item (unlocked investigation only).
- **`DELETE /api/evidence/{id}/`**: Delete evidence item (only creator, Admin, or Super Admin; unlocked only).
- **`POST /api/evidence/{id}/toggle_key/`**: Toggles whether this item is flagged as Key Evidence for the executive summary and ODT report.

### 6.2 Evidence Fields Specification

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `investigation` | Integer | Yes | Foreign key ID of the target investigation (alias: `project`). |
| `evidence_type` | String | No | `"ATOMIC"` (point-in-time event, default) or `"SEARCH"` (activity over duration). |
| `timestamp` | ISO-8601 String | No | Event start/observation time (e.g. `2026-10-31T08:15:00Z`). |
| `end_timestamp` | ISO-8601 String | No | Event end time (used when `evidence_type` is `"SEARCH"`). |
| `summary` | String | Yes | Concise description of the finding or observed attacker behavior. |
| `affected_asset` | String | No | Hostname, IP address, VM name, or cloud instance identifier. |
| `affected_user` | String | No | Compromised or targeted user/service account name. |
| `user_created_by_attacker` | Boolean | No | `true` if this account was created as a persistence backdoor. |
| `malicious_hosts_ips` | String | No | Attacker C2 IP addresses, domains, or infrastructure (auto-defanged). |
| `commands_run` | String | No | PowerShell, bash, or CLI commands executed by the attacker. |
| `mitre_tactic` | String | No | MITRE ATT&CK tactic name & ID (e.g. `Initial Access (TA0001)`). |
| `mitre_technique` | String | No | MITRE ATT&CK technique name & ID (e.g. `T1190 - Exploit Public-Facing Application`). |
| `related_log_link` | URL String | No | Direct permalink into SIEM, EDR, or log search platform. |
| `search_result_link` | URL String | No | Direct permalink to saved search or dashboard. |
| `search_query_link` | String | No | Raw SPL, KQL, Lucene, or SQL query used to uncover the artifact. |
| `notes` | String | No | Internal analyst notes, caveats, or investigative hypotheses. |
| `is_key_evidence` | Boolean | No | Flags item for highlight badges and key evidence summary sections. |
| `analyst_name` | String | No | Submitting analyst name (defaults to authenticated user). |

### 6.3 Screenshot & PCAP Attachments

Screenshots and network packet captures (PCAP) are linked to specific evidence items.

#### Uploading a Screenshot (`POST /api/screenshots/`)
```bash
curl -X POST http://127.0.0.1:8000/api/screenshots/ \
  -H "Authorization: Token <TOKEN>" \
  -F "evidence=101" \
  -F "image=@/path/to/mimikatz_dump.png" \
  -F "caption=Terminal capture of LSASS injection memory dump"
```

#### Uploading a PCAP (`POST /api/pcaps/`)
```bash
curl -X POST http://127.0.0.1:8000/api/pcaps/ \
  -H "Authorization: Token <TOKEN>" \
  -F "evidence=101" \
  -F "file=@/path/to/c2_beacon.pcap" \
  -F "description=Wireshark capture of TLS C2 beaconing on port 8443"
```

---

## 7. SIEM & SOAR Programmatic Ingest Endpoint

For security tools, SOAR playbooks (e.g. Splunk SOAR, Cortex XSOAR, Tines, Shuffle), and IDS sensors that need a lightweight ingestion webhook matching an open ticket ID:

#### `POST /api/soc/ingest/`

```bash
curl -X POST http://127.0.0.1:8000/api/soc/ingest/ \
  -H "Authorization: Token <YOUR_API_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_id": "INC-2026-8801",
    "evidence_type": "ATOMIC",
    "timestamp": "2026-10-31T08:15:00Z",
    "summary": "Outbound Cobalt Strike beacon blocked by perimeter firewall",
    "affected_asset": "DC-PROD-01 (10.10.0.10)",
    "malicious_hosts_ips": "45.155.205.109, c2.ceres-telemetry.net",
    "mitre_tactic": "Command and Control (TA0011)",
    "mitre_technique": "T1071.001 - Web Protocols",
    "related_log_link": "https://siem.corp/events/fw-99201",
    "is_key_evidence": true
  }'
```

**Ingestion Resolution:**
- Resolves the investigation by matching `ticket_id` against active unlocked investigations.
- If multiple investigations share the ticket ID, selects the most recently updated.
- Verifies that the target investigation is not locked.
- Automatically defangs indicators, records the creating analyst, and synchronizes the investigation timeline.

---

## 8. Related Escalations & External Threat Research

### 8.1 Related Escalated Incidents (`/api/related-incidents/`)
Tracks external tickets or prior incidents linked to the current investigation:
```bash
curl -X POST http://127.0.0.1:8000/api/related-incidents/ \
  -H "Authorization: Token <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "investigation": 12,
    "incident_id": "INC-PREV-2025-4100",
    "ticket_link": "https://jira.corp/browse/INC-PREV-2025-4100",
    "summary": "Previous reconnaissance probe against the same VPN gateway",
    "analyst_notes": "Observed identical user-agent string and SSL fingerprint."
  }'
```

### 8.2 External Threat Intelligence Research (`/api/external-research/`)
Records OSINT, CISA alerts, or threat actor dossiers:
```bash
curl -X POST http://127.0.0.1:8000/api/external-research/ \
  -H "Authorization: Token <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "investigation": 12,
    "link": "https://attack.mitre.org/groups/G0016/",
    "notes": "Apt29 / Cozy Bear infrastructure profile and TTP mappings."
  }'
```

---

## 9. MITRE ATT&CK Catalog API

#### `GET /api/mitre-catalog/`
Returns the standardized enterprise MITRE ATT&CK enterprise catalog bundled in the application, including tactics, technique IDs, sub-technique IDs, and official descriptions.
```bash
curl -X GET http://127.0.0.1:8000/api/mitre-catalog/ \
  -H "Authorization: Token <TOKEN>"
```

---

## 10. Complete Python Automation Client

The following Python script illustrates authenticating, registering a customer, creating an investigation, and executing a high-performance **bulk evidence ingestion** of forensic artifacts:

```python
#!/usr/bin/env python3
"""
Automated Incident Reporter Bulk Evidence Ingestion Script.
Demonstrates customer setup, investigation creation, and atomic bulk evidence ingest.
"""

import os
import sys
import requests

# Base URL: In production, target the HTTPS domain (e.g. https://soc-demo.aircooledcafe.com/api)
# For local dev without reverse proxy: http://localhost:8000/api
API_BASE = os.environ.get("API_BASE", "https://soc-demo.aircooledcafe.com/api")
API_TOKEN = os.environ.get("API_TOKEN", "7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b")

HEADERS = {
    "Authorization": f"Token {API_TOKEN}",
    "Content-Type": "application/json",
}

def main():
    session = requests.Session()
    session.headers.update(HEADERS)

    # 1. Ensure Customer exists
    print("[*] Creating / fetching Customer...")
    cust_res = session.post(f"{API_BASE}/customers/", json={
        "name": "Kredik Shaw Operations",
        "customer_id": "CUST-KREDIK-01",
        "notes": "Lord Ruler administrative infrastructure & vault networks",
    })
    if cust_res.status_code == 201:
        customer_id = cust_res.json()["id"]
        print(f"[+] Created customer ID: {customer_id}")
    else:
        # Fallback to search if already exists
        list_res = session.get(f"{API_BASE}/customers/").json()
        customer_id = list_res[0]["id"]
        print(f"[+] Reusing existing customer ID: {customer_id}")

    # 2. Create Investigation
    print("[*] Creating Investigation...")
    inv_res = session.post(f"{API_BASE}/investigations/", json={
        "title": "Operation Eleventh Metal: High Vault Intrusions",
        "status": "INVESTIGATING",
        "customer": customer_id,
        "ticket_id": "SEC-MISTBORN-2026",
        "lead_analyst": "Vin of Luthadel",
        "summary": "Coordinated allomantic breach targeting central treasury records and logs.",
        "scope": "Vault boundary firewalls, active directory domain controller, and sensor telemetry.",
    })
    inv_res.raise_for_status()
    inv_id = inv_res.json()["id"]
    print(f"[+] Created Investigation #{inv_id}: {inv_res.json()['title']}")

    # 3. Bulk Ingest Forensic Evidence
    print(f"[*] Bulk ingesting evidence items into Investigation #{inv_id}...")
    bulk_payload = {
        "investigation": inv_id,
        "items": [
            {
                "evidence_type": "ATOMIC",
                "timestamp": "2026-10-31T07:15:00Z",
                "summary": "External IP address spray targeting public steel gate telemetry port 8443",
                "affected_asset": "GW-PERIMETER-01 (192.168.1.1)",
                "malicious_hosts_ips": "185.190.140.22",
                "mitre_tactic": "Reconnaissance (TA0043)",
                "mitre_technique": "T1595.002 - Vulnerability Scanning",
                "is_key_evidence": False,
            },
            {
                "evidence_type": "ATOMIC",
                "timestamp": "2026-10-31T07:42:00Z",
                "summary": "VPN compromise via leaked credentials of junior guard cadet",
                "affected_asset": "VPN-CONC-01",
                "affected_user": "cadet_demoux",
                "mitre_tactic": "Initial Access (TA0001)",
                "mitre_technique": "T1078.002 - Domain Accounts",
                "is_key_evidence": True,
            },
            {
                "evidence_type": "ATOMIC",
                "timestamp": "2026-10-31T08:05:00Z",
                "summary": "PowerShell BloodHound execution mapping Domain Admins & ACLs",
                "affected_asset": "WS-GUARD-12",
                "commands_run": "powershell.exe -ExecutionPolicy Bypass -File SharpHound.exe -c All",
                "mitre_tactic": "Discovery (TA0007)",
                "mitre_technique": "T1069.002 - Domain Groups",
                "is_key_evidence": False,
            },
            {
                "evidence_type": "ATOMIC",
                "timestamp": "2026-10-31T08:30:00Z",
                "summary": "Mimikatz LSASS memory dump extracting cleartext Kerberos tickets",
                "affected_asset": "DC-MINISTRY-01 (10.10.0.5)",
                "affected_user": "svc_inquisitor",
                "commands_run": "mimikatz.exe \"privilege::debug\" \"sekurlsa::logonpasswords\" exit",
                "mitre_tactic": "Credential Access (TA0006)",
                "mitre_technique": "T1003.001 - LSASS Memory",
                "is_key_evidence": True,
            },
            {
                "evidence_type": "SEARCH",
                "timestamp": "2026-10-31T09:00:00Z",
                "end_timestamp": "2026-10-31T09:50:00Z",
                "summary": "120 GB exfiltration of metal reserve databases over encrypted HTTPS tunnel",
                "affected_asset": "DB-ALLOMANCY-01",
                "malicious_hosts_ips": "91.240.118.80, c2.luthadel-rebel.net",
                "mitre_tactic": "Exfiltration (TA0010)",
                "mitre_technique": "T1048 - Exfiltration Over Alternative Protocol",
                "search_query_link": "index=firewall bytes_out > 500000000 dst_ip=91.240.118.80",
                "is_key_evidence": True,
            },
        ],
    }

    bulk_res = session.post(f"{API_BASE}/evidence/bulk_create/", json=bulk_payload)
    if bulk_res.status_code != 201:
        print(f"[-] Bulk ingest failed: {bulk_res.status_code} {bulk_res.text}")
        sys.exit(1)

    result = bulk_res.json()
    print(f"[+] Successfully bulk-ingested {result['count']} items in 1 atomic transaction!")

    # 4. Verify Investigation Timeline
    inv_detail = session.get(f"{API_BASE}/investigations/{inv_id}/").json()
    print(f"[+] Total timeline events synchronized in investigation: {len(inv_detail['timeline_events'])}")

if __name__ == "__main__":
    main()
```
