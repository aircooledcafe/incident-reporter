#!/usr/bin/env python3
"""
Star Trek Themed SOC Investigation - Python Automation Script
Demonstrates:
  1. Connecting to customer domain (or local development)
  2. Customer setup & Investigation creation using human-readable IDs ('CUST-47170', 'INV000002')
  3. Escalation contacts, related escalated incidents, and external research creation
  4. Single-item evidence ingestion (Item 1)
  5. High-performance bulk evidence ingestion (Items 2-7)
"""

import os
import sys
import requests

# Base URL: Use your deployed domain or local dev
# In production on soc.example.com, target https://soc.example.com/api (no port 8000)
API_BASE = os.environ.get("API_BASE", "https://soc.example.com/api")
API_TOKEN = os.environ.get("API_TOKEN", "YOUR_API_TOKEN_HERE")

CUSTOMER_CODE = "CUST-47170"
INVESTIGATION_CODE = "INV000002"

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
    "name": "Daystrom Institute & Utopia Planitia Yards",
    "customer_id": "CUST-47170",
    "notes": "Enterprise client profile for Daystrom Institute & Utopia Planitia Yards.",
}
cust_res = session.post(f"{API_BASE}/customers/", json=customer_payload)
if cust_res.status_code == 201:
    print(f"[+] Customer created with code: {CUSTOMER_CODE}")
else:
    print(f"[+] Customer '{CUSTOMER_CODE}' already registered and ready for use.")

# 1b. Register Customer Escalation Contacts
contacts_payload = [
    {
        "customer": "CUST-47170",
        "name": "Geordi La Forge",
        "escalation_tier": "PRIMARY",
        "notes": "Owns WEB-LCARS-01 reverse proxy and IIS-UTOPIA-02 application servers.",
    },
    {
        "customer": "CUST-47170",
        "name": "Bruce Maddox",
        "escalation_tier": "SECONDARY",
        "notes": "Application owner reviewing uploaded research attachments and database schema sensitivity.",
    },
]
for contact in contacts_payload:
    c_res = session.post(f"{API_BASE}/customer-contacts/", json=contact)
    if c_res.status_code == 201:
        print(f"[+] Added contact: {contact['name']} ({contact['escalation_tier']})")

# 2. Create Investigation referencing customer by CUSTOMER_CODE
print(f"[*] Creating Investigation '{INVESTIGATION_CODE}'...")
investigation_payload = {
    "customer": "CUST-47170",
    "investigation_id": "INV000002",
    "title": "Subspace Research Portal Compromise, Web Shell Deployment & Database Credential Theft",
    "ticket_id": "SOC-2026-4701",
    "ticket_link": "https://soc.internal.example/tickets/SOC-2026-4701",
    "status": "INVESTIGATING",
    "lead_analyst": "Jean-Luc Picard",
    "summary": "An external threat actor exploited an unauthenticated multipart file-upload bypass on the public-facing Subspace Research Portal (WEB-LCARS-01) to drop an obfuscated PHP web shell (eps_conduit.php), executed OS commands under www-data, harvested database credentials from .env configuration files, pivoted to internal Warp Telemetry IIS host (IIS-UTOPIA-02) to plant a secondary ASPX web shell (tachyon_relay.aspx), queried warp-core schematics from PGSQL-DAYSTROM-01, and installed a cron persistence job before WAF virtual patching and host isolation.",
    "action_plan": "1. Rotate PostgreSQL role `svc_lcars_portal` and Utopia Planitia API signing keys immediately.\n2. Validate WAF virtual patch rules blocking `.php`, `.phtml`, and `.aspx` execution inside `/uploads/`.\n3. Obtain confirmation from Daystrom Cybernetics Lead (Dr. Maddox) on whether warp-field simulation tables contain classified Starfleet specs.\n4. Rebuild WEB-LCARS-01 from golden container image after forensic memory preservation.",
    "key_customer_contacts": "Starfleet Cyber Command Duty Officer: subspace-soc@daystrom-institute.example",
    "key_assets_affected": "WEB-LCARS-01 (172.16.47.10 / portal.daystrom-institute.example)\nIIS-UTOPIA-02 (10.47.20.15)\nPGSQL-DAYSTROM-01 (10.47.30.50)",
    "key_users_affected": "www-data (WEB-LCARS-01)\nUTOPIA\\iis_apphost\nsvc_lcars_portal (PostgreSQL Role)\nsys_romulan_maint (Created by Attacker)",
    "key_malicious_indicators": "198.51.100.214\n203.0.113.77\ntal-shiar-telemetry.org\neps_conduit.php\ntachyon_relay.aspx\n/var/www/lcars/uploads/avatars/eps_conduit.php\n/tmp/.subspace_sync.sh",
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
        "title": "WAF-2026-1192: Anomalous Multipart Double-Extension Upload on portal.daystrom-institute.example",
        "link": "https://soc.internal.example/escalations/WAF-2026-1192",
        "analyst_name": "Seven of Nine",
    },
    {
        "title": "EDR-2026-3308: Linux www-data Spawning Interactive /bin/sh & curl",
        "link": "https://soc.internal.example/escalations/EDR-2026-3308",
        "analyst_name": "Jean-Luc Picard",
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
        "link": "https://attack.mitre.org/techniques/T1505/003/",
        "summary": "MITRE ATT&CK T1505.003 - Server Software Component: Web Shell persistence & remote command execution.",
        "analyst_name": "Seven of Nine",
    },
    {
        "link": "https://attack.mitre.org/techniques/T1190/",
        "summary": "MITRE ATT&CK T1190 - Exploit Public-Facing Application via unrestricted multipart upload.",
        "analyst_name": "Jean-Luc Picard",
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
    "evidence_type": "SEARCH",
    "analyst_name": "Seven of Nine",
    "timestamp": "2026-10-21T08:12:00Z",
    "end_timestamp": "2026-10-21T08:19:45Z",
    "summary": "Automated directory & endpoint fuzzing (1,840 HTTP requests) from 198.51.100.214 against /api/v2/research/upload.",
    "affected_asset": "WEB-LCARS-01 (172.16.47.10)",
    "affected_user": "",
    "user_created_by_attacker": False,
    "malicious_hosts_ips": "198.51.100.214",
    "commands_run": "",
    "mitre_tactic": "Reconnaissance (TA0043)",
    "mitre_technique": "T1595.002 - Active Scanning: Vulnerability Scanning",
    "search_result_link": "https://siem.internal.example/app/discover#/view/lcars-waf-fuzzing",
    "search_query_link": "https://siem.internal.example/app/discover#/?_q=(host.name:WEB-LCARS-01%20AND%20source.ip:198.51.100.214)",
    "is_key_evidence": False,
    "notes": "Scanner enumerated MIME filter validation behavior on portal.daystrom-institute.example.",
}
item_1["investigation"] = inv_id
res_single = session.post(f"{API_BASE}/evidence/", json=item_1)
res_single.raise_for_status()
print(f"[+] [1/7] Created single item ID: {res_single.json()['id']} on {inv_id}")

# 4. Ingest Remaining 6 Items in Bulk (Items 2-7) referencing inv_id
print(f"\n[*] [Bulk Ingest] Ingesting remaining 6 items into '{inv_id}' via POST /api/evidence/bulk_create/...")
bulk_items = [
    {
        "evidence_type": "ATOMIC",
        "analyst_name": "Jean-Luc Picard",
        "timestamp": "2026-10-21T08:22:14Z",
        "summary": "Unauthenticated multipart POST exploited magic-byte bypass (GIF89a header) to write web shell /var/www/lcars/uploads/avatars/eps_conduit.php.",
        "affected_asset": "WEB-LCARS-01 (172.16.47.10)",
        "affected_user": "www-data",
        "user_created_by_attacker": False,
        "malicious_hosts_ips": "198.51.100.214, eps_conduit.php, /var/www/lcars/uploads/avatars/eps_conduit.php",
        "commands_run": "POST /api/v2/research/upload HTTP/1.1 [filename=\"diagram.gif.php\" -> eps_conduit.php]",
        "mitre_tactic": "Initial Access (TA0001); Persistence (TA0003)",
        "mitre_technique": "T1190 - Exploit Public-Facing Application; T1505.003 - Server Software Component: Web Shell",
        "related_log_link": "https://siem.internal.example/events/nginx-access-774102",
        "is_key_evidence": True,
        "notes": "HTTP 201 Created returned; file written with executable PHP handler permissions.",
    },
    {
        "evidence_type": "SEARCH",
        "analyst_name": "Seven of Nine",
        "timestamp": "2026-10-21T08:24:30Z",
        "end_timestamp": "2026-10-21T08:28:12Z",
        "summary": "19 HTTP POST requests to /uploads/avatars/eps_conduit.php spawned /bin/sh child processes from php-fpm8.2 executing host discovery.",
        "affected_asset": "WEB-LCARS-01 (172.16.47.10)",
        "affected_user": "www-data",
        "user_created_by_attacker": False,
        "malicious_hosts_ips": "198.51.100.214, eps_conduit.php",
        "commands_run": "id; uname -a; ip route; cat /etc/passwd; env",
        "mitre_tactic": "Execution (TA0002); Discovery (TA0007)",
        "mitre_technique": "T1059.004 - Command and Scripting Interpreter: Unix Shell; T1082 - System Information Discovery",
        "search_result_link": "https://edr.internal.example/app/LinuxExec#/web-lcars-01-webshell",
        "search_query_link": "https://edr.internal.example/app/LinuxExec#/?_q=(parent.executable:*php-fpm*%20AND%20process.name:sh)",
        "is_key_evidence": True,
        "notes": "Linux auditd EXECVE telemetry confirmed base64-encoded command payloads inside POST body.",
    },
    {
        "evidence_type": "ATOMIC",
        "analyst_name": "Geordi La Forge",
        "timestamp": "2026-10-21T08:29:50Z",
        "summary": "Attacker read /var/www/lcars/.env and /etc/lcars/partner_sync.conf, harvesting PostgreSQL credentials and Utopia Planitia API deploy key.",
        "affected_asset": "WEB-LCARS-01 (172.16.47.10)",
        "affected_user": "www-data",
        "user_created_by_attacker": False,
        "malicious_hosts_ips": "/var/www/lcars/.env",
        "commands_run": "cat /var/www/lcars/.env /etc/lcars/partner_sync.conf",
        "mitre_tactic": "Credential Access (TA0006)",
        "mitre_technique": "T1552.001 - Unsecured Credentials: Credentials In Files",
        "related_log_link": "https://edr.internal.example/events/auditd-991204",
        "is_key_evidence": True,
        "notes": "Extracted DB password for svc_lcars_portal and internal WebDAV publishing credentials for IIS-UTOPIA-02.",
    },
    {
        "evidence_type": "ATOMIC",
        "analyst_name": "Geordi La Forge",
        "timestamp": "2026-10-21T08:35:18Z",
        "summary": "Secondary ASPX web shell tachyon_relay.aspx uploaded to IIS-UTOPIA-02 via stolen internal WebDAV deployment credentials.",
        "affected_asset": "IIS-UTOPIA-02 (10.47.20.15)",
        "affected_user": "UTOPIA\\iis_apphost",
        "user_created_by_attacker": False,
        "malicious_hosts_ips": "172.16.47.10, 10.47.20.15, tachyon_relay.aspx",
        "commands_run": "curl -u iis_apphost:*** -T /tmp/tachyon_relay.aspx http://10.47.20.15/ diagnostics/tachyon_relay.aspx",
        "mitre_tactic": "Lateral Movement (TA0008); Persistence (TA0003)",
        "mitre_technique": "T1021.006 - Remote Services: Windows Remote Management; T1505.003 - Server Software Component: Web Shell",
        "related_log_link": "https://siem.internal.example/events/iis-w3wp-448210",
        "is_key_evidence": True,
        "notes": "w3wp.exe subsequently spawned cmd.exe /c whoami /priv on IIS-UTOPIA-02.",
    },
    {
        "evidence_type": "SEARCH",
        "analyst_name": "Seven of Nine",
        "timestamp": "2026-10-21T08:41:00Z",
        "end_timestamp": "2026-10-21T08:46:22Z",
        "summary": "psql client invoked from WEB-LCARS-01 dumped subspace_transceiver_specs and researcher_directory tables to /tmp/daystrom_dump.sql.gz.",
        "affected_asset": "PGSQL-DAYSTROM-01 (10.47.30.50)",
        "affected_user": "svc_lcars_portal",
        "user_created_by_attacker": False,
        "malicious_hosts_ips": "10.47.30.50, /tmp/daystrom_dump.sql.gz",
        "commands_run": "PGPASSWORD=*** pg_dump -h 10.47.30.50 -U svc_lcars_portal -t subspace_transceiver_specs lcars_prod | gzip > /tmp/daystrom_dump.sql.gz",
        "mitre_tactic": "Collection (TA0009)",
        "mitre_technique": "T1005 - Data from Local System; T1560.001 - Archive Collected Data: Archive via Utility",
        "search_result_link": "https://siem.internal.example/app/discover#/view/pgsql-audit-copy",
        "search_query_link": "https://siem.internal.example/app/discover#/?_q=(host.name:PGSQL-DAYSTROM-01%20AND%20db.user:svc_lcars_portal)",
        "is_key_evidence": True,
        "notes": "PostgreSQL audit logs recorded COPY TO STDOUT for 6,410 rows.",
    },
    {
        "evidence_type": "ATOMIC",
        "analyst_name": "Jean-Luc Picard",
        "timestamp": "2026-10-21T08:49:05Z",
        "summary": "User crontab persistence added for www-data calling /tmp/.subspace_sync.sh to beacon to tal-shiar-telemetry.org (203.0.113.77).",
        "affected_asset": "WEB-LCARS-01 (172.16.47.10)",
        "affected_user": "sys_romulan_maint",
        "user_created_by_attacker": True,
        "malicious_hosts_ips": "203.0.113.77, tal-shiar-telemetry.org, /tmp/.subspace_sync.sh",
        "commands_run": "(crontab -l; echo '*/10 * * * * /bin/sh /tmp/.subspace_sync.sh') | crontab -",
        "mitre_tactic": "Persistence (TA0003); Command and Control (TA0011)",
        "mitre_technique": "T1053.003 - Scheduled Task/Job: Cron; T1071.001 - Application Layer Protocol: Web Protocols",
        "related_log_link": "https://edr.internal.example/events/auditd-991890",
        "is_key_evidence": False,
        "notes": "Outbound curl callback blocked by egress DNS sinkhole; web shells quarantined and hosts isolated.",
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

if total_timeline == 7:
    print(f"\n✅ Verification SUCCESS: 1 item ingested individually + 6 items ingested in bulk = 7 total items on '{inv_id}'!")
else:
    print(f"\n⚠️ Unexpected event count: expected 7, found {total_timeline}")
