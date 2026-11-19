#!/usr/bin/env python3
"""
God of War Themed SOC Investigation - Python Automation Script
Demonstrates:
  1. Connecting to customer domain (or local development)
  2. Customer setup & Investigation creation using human-readable IDs ('CUST-GOW-05', 'INV000005')
  3. Escalation contacts, related escalated incidents, and external research creation
  4. Single-item evidence ingestion (Item 1)
  5. High-performance bulk evidence ingestion (Items 2-12)
"""

import os
import sys
import requests

# Base URL: Use your deployed domain or local dev
# In production on soc.example.com, target https://soc.example.com/api (no port 8000)
API_BASE = os.environ.get("API_BASE", "https://soc.example.com/api")
API_TOKEN = os.environ.get("API_TOKEN", "YOUR_API_TOKEN_HERE")

CUSTOMER_CODE = "CUST-GOW-05"
INVESTIGATION_CODE = "INV000005"

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
    "name": "Midgard Realmworks Technologies",
    "customer_id": "CUST-GOW-05",
    "notes": "Enterprise client profile for Midgard Realmworks Technologies.",
}
cust_res = session.post(f"{API_BASE}/customers/", json=customer_payload)
if cust_res.status_code == 201:
    print(f"[+] Customer created with code: {CUSTOMER_CODE}")
else:
    print(f"[+] Customer '{CUSTOMER_CODE}' already registered and ready for use.")

# 1b. Register Customer Escalation Contacts
contacts_payload = [
    {
        "customer": "CUST-GOW-05",
        "name": "Atreus (Loki)",
        "escalation_tier": "PRIMARY",
        "notes": "Primary technical contact who first reported .RAGNAROK encrypted files across network shares.",
    },
    {
        "customer": "CUST-GOW-05",
        "name": "Brok & Sindri (Huldra Brothers)",
        "escalation_tier": "SECONDARY",
        "notes": "Supervising SAN storage isolation and verifying air-gapped tape backup sets.",
    },
    {
        "customer": "CUST-GOW-05",
        "name": "Freya",
        "escalation_tier": "TERTIARY",
        "notes": "Executive incident commander managing Board briefings and legal disclosures.",
    },
]
for contact in contacts_payload:
    c_res = session.post(f"{API_BASE}/customer-contacts/", json=contact)
    if c_res.status_code == 201:
        print(f"[+] Added contact: {contact['name']} ({contact['escalation_tier']})")

# 2. Create Investigation referencing customer by CUSTOMER_CODE
print(f"[*] Creating Investigation '{INVESTIGATION_CODE}'...")
investigation_payload = {
    "customer": "CUST-GOW-05",
    "investigation_id": "INV000005",
    "title": "Fimbulwinter Ransomware Deployment, Volume Shadow Deletion & Domain-Wide Encryption",
    "ticket_id": "SOC-2026-GOW77",
    "ticket_link": "https://soc.internal.example/tickets/SOC-2026-GOW77",
    "status": "INVESTIGATING",
    "lead_analyst": "Kratos of Sparta",
    "summary": "Threat actor (tracked as Fimbulwinter / Ragnarök Ransomware Cartel) gained initial access to Midgard Realmworks via exposed Citrix/RDP gateway GW-ASGARD-01 using compromised contractor credentials for MIDGARD\\a.spartan. The actor moved laterally to administrator workstation WRK-KRATOS-04, performed LSASS memory credential dumping with Mimikatz, and obtained Domain Admin privileges for MIDGARD\\adm_atreus. Operating from Domain Controller DC-YGGDRASIL-01, the adversary created backdoor account MIDGARD\\adm_fimbulwinter, executed Cobalt Strike beacons to c2.fimbulwinter-ops.net, terminated EDR and endpoint defense agents using BYOVD driver groot.sys, wiped all Volume Shadow Copies across file and database servers (FS-MIDGARD-01, DB-VALHALLA-01, HYPERV-NILFHEIM-01), stopped MSSQL and backup services, and deployed multi-threaded ransomware binary fimbulwinter.exe encrypting network shares and local disks, appending the .RAGNAROK extension, and dropping HOW_TO_RESTORE_MIDGARD_FILES.txt before containment.",
    "action_plan": "1. Maintain hard VLAN network isolation for all Midgard production subnets; ensure perimeter firewalls drop all outbound traffic to C2 IPs 194.26.29.112 and 185.196.8.24.\n2. Coordinate with designated incident response legal counsel and digital forensics partner regarding the Ragnarök ransomware extortion demand and onion leak site monitoring.\n3. Validate immutable, offline air-gapped tape backup catalogs for production database DB-VALHALLA-01 and file server FS-MIDGARD-01 prior to bare-metal restoration.\n4. Perform emergency double-reset of the KRBTGT Kerberos account across the MIDGARD Active Directory domain.\n5. Rebuild Domain Controller DC-YGGDRASIL-01 from verified clean golden media, revoke all compromised accounts, and enforce hardware FIDO2 MFA across all external Citrix/remote access gateways.",
    "key_customer_contacts": "24/7 Midgard Realm Emergency War Room: +1-555-REALM-99 (Bridge Code: 4048#)",
    "key_assets_affected": "GW-ASGARD-01 (10.30.1.10 - Perimeter Citrix Gateway)\nDC-YGGDRASIL-01 (10.30.0.5 - Primary Domain Controller)\nFS-MIDGARD-01 (10.30.4.15 - Enterprise File Server)\nDB-VALHALLA-01 (10.30.8.20 - Production SQL Server)\nHYPERV-NILFHEIM-01 (10.30.2.50 - Hyper-V Cluster Node)\nWRK-KRATOS-04 (10.30.100.82 - Compromised Admin Workstation)",
    "key_users_affected": "MIDGARD\\a.spartan (Compromised Contractor Account)\nMIDGARD\\adm_atreus (Compromised Domain Admin Account)\nMIDGARD\\svc_hyperv_backup (Compromised Service Account)\nMIDGARD\\adm_fimbulwinter (Attacker-Created Rogue Domain Admin)",
    "key_malicious_indicators": "194.26.29.112 (Cobalt Strike C2 Server)\n185.196.8.24 (Data Exfiltration Drop Server)\n109.236.81.45 (RDP Brute-Force Origin IP)\nc2.fimbulwinter-ops.net (Adversary C2 Domain)\nragnarok-leak-portal.onion (TOR Ransom Leak Site)\nfimbulwinter.exe (SHA256: e8b94109f2208a731d6e872c011985da33bc88219461df893bc4428019a3b612)\ngroot.sys (BYOVD Vulnerable Signed Driver)\nvssadmin.exe delete shadows /all /quiet\nwbadmin.exe delete catalog -quiet\nHOW_TO_RESTORE_MIDGARD_FILES.txt (Ransom Note)\n.RAGNAROK (Encrypted File Extension)",
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
        "title": "INC-2026-8801: CRITICAL ALERT: Mass Volume Shadow Copy Deletion Detected via vssadmin",
        "link": "https://soc.internal.example/escalations/INC-2026-8801",
        "analyst_name": "Mimir",
    },
    {
        "title": "INC-2026-8802: FIREWALL ALERT: High-Frequency Outbound Beaconing to Known Ransomware C2 194.26.29.112",
        "link": "https://soc.internal.example/escalations/INC-2026-8802",
        "analyst_name": "Kratos of Sparta",
    },
    {
        "title": "INC-2026-8803: EDR ALERT: Kernel Driver Exploit (BYOVD) Terminating Endpoint Protection on DB-VALHALLA-01",
        "link": "https://soc.internal.example/escalations/INC-2026-8803",
        "analyst_name": "Mimir",
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
        "link": "https://attack.mitre.org/techniques/T1486/",
        "summary": "MITRE ATT&CK T1486 - Data Encrypted for Impact: Fimbulwinter / Ragnarök Ransomware technical analysis.",
        "analyst_name": "Kratos of Sparta",
    },
    {
        "link": "https://attack.mitre.org/techniques/T1490/",
        "summary": "MITRE ATT&CK T1490 - Inhibit System Recovery: Volume Shadow Copy and backup catalog wiping techniques.",
        "analyst_name": "Mimir",
    },
    {
        "link": "https://attack.mitre.org/techniques/T1562/001/",
        "summary": "MITRE ATT&CK T1562.001 - Impair Defenses: Bring-Your-Own-Vulnerable-Driver (BYOVD) groot.sys kernel exploit.",
        "analyst_name": "Mimir",
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
    "analyst_name": "Kratos of Sparta",
    "timestamp": "2026-10-28T01:14:02Z",
    "end_timestamp": "2026-10-28T01:20:18Z",
    "summary": "External RDP password spraying against perimeter Citrix gateway GW-ASGARD-01 from 109.236.81.45 resulting in successful authentication for contractor account MIDGARD\\a.spartan.",
    "affected_asset": "GW-ASGARD-01 (10.30.1.10)",
    "affected_user": "MIDGARD\\a.spartan",
    "user_created_by_attacker": False,
    "malicious_hosts_ips": "109.236.81.45",
    "commands_run": "",
    "mitre_tactic": "Initial Access (TA0001); Credential Access (TA0006)",
    "mitre_technique": "T1110.003 - Password Spraying; T1133 - External Remote Services",
    "related_log_link": "https://siem.internal.example/events/citrix-auth-77192",
    "search_result_link": "https://siem.internal.example/app/discover#/view/citrix-rdp-spray",
    "search_query_link": "https://siem.internal.example/app/discover#/?_q=(source.ip:109.236.81.45%20AND%20event.category:authentication)",
    "is_key_evidence": True,
    "notes": "SIEM captured 248 failed logon attempts across 40 accounts prior to successful credential match on a.spartan.",
}
item_1["investigation"] = inv_id
res_single = session.post(f"{API_BASE}/evidence/", json=item_1)
res_single.raise_for_status()
print(f"[+] [1/12] Created single item ID: {res_single.json()['id']} on {inv_id}")

# 4. Ingest Remaining 11 Items in Bulk (Items 2-12) referencing inv_id
print(f"\n[*] [Bulk Ingest] Ingesting remaining 11 items into '{inv_id}' via POST /api/evidence/bulk_create/...")
bulk_items = [
    {
        "evidence_type": "ATOMIC",
        "analyst_name": "Mimir",
        "timestamp": "2026-10-28T01:31:10Z",
        "summary": "Adversary executed SharpHound / BloodHound collector to map Active Directory attack paths to Domain Admins.",
        "affected_asset": "GW-ASGARD-01 (10.30.1.10)",
        "affected_user": "MIDGARD\\a.spartan",
        "user_created_by_attacker": False,
        "malicious_hosts_ips": "sharphound.exe, 20261028_BloodHound.zip",
        "commands_run": "powershell.exe -ExecutionPolicy Bypass -Command Invoke-BloodHound -CollectionMethod All -Domain midgard.realm -ZipFileName C:\\Windows\\Temp\\20261028_BloodHound.zip",
        "mitre_tactic": "Discovery (TA0007)",
        "mitre_technique": "T1087.002 - Account Discovery: Domain Account; T1069.002 - Permission Groups Discovery: Domain Groups",
        "related_log_link": "https://edr.internal.example/alerts/ps-sharphound-3301",
        "is_key_evidence": True,
        "notes": "PowerShell process spawned SharpHound binary from C:\\Windows\\Temp\\sharphound.exe.",
    },
    {
        "evidence_type": "ATOMIC",
        "analyst_name": "Kratos of Sparta",
        "timestamp": "2026-10-28T01:46:25Z",
        "summary": "RDP connection initiated from gateway 10.30.1.10 to Tier-1 administrative workstation WRK-KRATOS-04.",
        "affected_asset": "WRK-KRATOS-04 (10.30.100.82)",
        "affected_user": "MIDGARD\\a.spartan",
        "user_created_by_attacker": False,
        "malicious_hosts_ips": "10.30.1.10, 10.30.100.82",
        "commands_run": "mstsc.exe /v:10.30.100.82",
        "mitre_tactic": "Lateral Movement (TA0008)",
        "mitre_technique": "T1021.001 - Remote Services: Remote Desktop Protocol",
        "related_log_link": "https://siem.internal.example/events/event-4624-rdp-kratos04",
        "is_key_evidence": False,
        "notes": "Windows Event ID 4624 (Logon Type 10) confirms lateral movement across internal subnets.",
    },
    {
        "evidence_type": "ATOMIC",
        "analyst_name": "Mimir",
        "timestamp": "2026-10-28T01:54:40Z",
        "summary": "LSASS credential harvesting via Mimikatz extracting cleartext NTLM hashes and credentials for Domain Admin MIDGARD\\adm_atreus.",
        "affected_asset": "WRK-KRATOS-04 (10.30.100.82)",
        "affected_user": "MIDGARD\\a.spartan",
        "user_created_by_attacker": False,
        "malicious_hosts_ips": "mimikatz.exe, sekurlsa::logonpasswords",
        "commands_run": "mimikatz.exe \"privilege::debug\" \"sekurlsa::logonpasswords\" \"exit\"",
        "mitre_tactic": "Credential Access (TA0006); Privilege Escalation (TA0004)",
        "mitre_technique": "T1003.001 - OS Credential Dumping: LSASS Memory",
        "related_log_link": "https://edr.internal.example/alerts/mimikatz-lsass-99401",
        "is_key_evidence": True,
        "notes": "Adversary elevated privileges using SeDebugPrivilege and dumped credentials from memory.",
    },
    {
        "evidence_type": "ATOMIC",
        "analyst_name": "Kratos of Sparta",
        "timestamp": "2026-10-28T02:10:15Z",
        "summary": "Compromised Domain Admin credentials used to establish interactive WinRM session on Primary Domain Controller DC-YGGDRASIL-01.",
        "affected_asset": "DC-YGGDRASIL-01 (10.30.0.5)",
        "affected_user": "MIDGARD\\adm_atreus",
        "user_created_by_attacker": False,
        "malicious_hosts_ips": "10.30.100.82, 10.30.0.5",
        "commands_run": "Enter-PSSession -ComputerName DC-YGGDRASIL-01 -Credential MIDGARD\\adm_atreus",
        "mitre_tactic": "Lateral Movement (TA0008)",
        "mitre_technique": "T1021.006 - Remote Services: Windows Remote Management",
        "related_log_link": "https://siem.internal.example/events/winrm-session-88210",
        "is_key_evidence": False,
        "notes": "Remote PowerShell management connection from 10.30.100.82.",
    },
    {
        "evidence_type": "ATOMIC",
        "analyst_name": "Mimir",
        "timestamp": "2026-10-28T02:21:05Z",
        "summary": "Rogue backdoor Domain Admin account created on Domain Controller: MIDGARD\\adm_fimbulwinter.",
        "affected_asset": "DC-YGGDRASIL-01 (10.30.0.5)",
        "affected_user": "MIDGARD\\adm_fimbulwinter",
        "user_created_by_attacker": True,
        "malicious_hosts_ips": "MIDGARD\\adm_fimbulwinter",
        "commands_run": "net user adm_fimbulwinter Ragnarok2026! /add /domain & net group \"Domain Admins\" adm_fimbulwinter /add /domain & net group \"Enterprise Admins\" adm_fimbulwinter /add /domain",
        "mitre_tactic": "Persistence (TA0003); Privilege Escalation (TA0004)",
        "mitre_technique": "T1136.002 - Create Account: Domain Account; T1098 - Account Manipulation",
        "related_log_link": "https://siem.internal.example/events/event-4720-user-created",
        "is_key_evidence": True,
        "notes": "User added directly to Domain Admins and Enterprise Admins security groups.",
    },
    {
        "evidence_type": "SEARCH",
        "analyst_name": "Kratos of Sparta",
        "timestamp": "2026-10-28T02:38:20Z",
        "end_timestamp": "2026-10-28T03:55:00Z",
        "summary": "Cobalt Strike HTTPS Beacon execution maintaining persistent encrypted command-and-control channel to 194.26.29.112.",
        "affected_asset": "DC-YGGDRASIL-01 (10.30.0.5)",
        "affected_user": "MIDGARD\\adm_fimbulwinter",
        "user_created_by_attacker": True,
        "malicious_hosts_ips": "194.26.29.112, c2.fimbulwinter-ops.net",
        "commands_run": "powershell.exe -nop -w hidden -enc JABzAD0ATgBlAHcALQBPAGIAagBlAGMAdAAgAEkATwAuAE0AZQBtAG8AcgB5AFMAdAByAGUAYQBt...",
        "mitre_tactic": "Command and Control (TA0011)",
        "mitre_technique": "T1071.001 - Application Layer Protocol: Web Protocols; T1059.001 - Command and Scripting Interpreter: PowerShell",
        "related_log_link": "https://fw.internal.example/traffic/c2-beacon-194-26-29-112",
        "search_result_link": "https://siem.internal.example/app/discover#/view/c2-beaconing-194-26",
        "search_query_link": "https://siem.internal.example/app/discover#/?_q=(destination.ip:194.26.29.112%20AND%20destination.port:443)",
        "is_key_evidence": True,
        "notes": "Beacon established jittered 5-second heartbeats to c2.fimbulwinter-ops.net.",
    },
    {
        "evidence_type": "ATOMIC",
        "analyst_name": "Mimir",
        "timestamp": "2026-10-28T03:06:50Z",
        "summary": "Defense Evasion via Bring-Your-Own-Vulnerable-Driver (BYOVD): vulnerable signed kernel driver groot.sys loaded to terminate EDR agents and Defender services.",
        "affected_asset": "DB-VALHALLA-01 (10.30.8.20)",
        "affected_user": "MIDGARD\\adm_fimbulwinter",
        "user_created_by_attacker": True,
        "malicious_hosts_ips": "groot.sys, terminate_edr.exe",
        "commands_run": "sc.exe create groot binPath= C:\\Windows\\Temp\\groot.sys type= kernel & sc.exe start groot & terminate_edr.exe --kill-all",
        "mitre_tactic": "Defense Evasion (TA0005)",
        "mitre_technique": "T1562.001 - Impair Defenses: Disable or Modify Tools; T1068 - Exploitation for Privilege Escalation",
        "related_log_link": "https://edr.internal.example/events/byovd-driver-loaded-8802",
        "is_key_evidence": True,
        "notes": "Adversary leveraged kernel-mode memory write primitives to strip EDR process callbacks and kill security monitoring.",
    },
    {
        "evidence_type": "ATOMIC",
        "analyst_name": "Kratos of Sparta",
        "timestamp": "2026-10-28T03:27:15Z",
        "summary": "System recovery destruction: Volume Shadow Copies deleted, backup catalogs purged, and boot recovery disabled via vssadmin and wbadmin.",
        "affected_asset": "FS-MIDGARD-01 (10.30.4.15)",
        "affected_user": "MIDGARD\\adm_fimbulwinter",
        "user_created_by_attacker": True,
        "malicious_hosts_ips": "vssadmin.exe, wbadmin.exe, bcdedit.exe",
        "commands_run": "vssadmin.exe delete shadows /all /quiet & wbadmin.exe delete catalog -quiet & bcdedit.exe /set {default} bootstatuspolicy ignoreallfailures & bcdedit.exe /set {default} recoveryenabled no",
        "mitre_tactic": "Impact (TA0040)",
        "mitre_technique": "T1490 - Inhibit System Recovery",
        "related_log_link": "https://siem.internal.example/events/vssadmin-deleted-9014",
        "is_key_evidence": True,
        "notes": "Ensured local shadow copies could not be used to recover encrypted files.",
    },
    {
        "evidence_type": "ATOMIC",
        "analyst_name": "Mimir",
        "timestamp": "2026-10-28T03:43:30Z",
        "summary": "Forceful service termination of production database engines and Veeam backup agents to unlock file handles before encryption.",
        "affected_asset": "DB-VALHALLA-01 (10.30.8.20)",
        "affected_user": "MIDGARD\\adm_fimbulwinter",
        "user_created_by_attacker": True,
        "malicious_hosts_ips": "MSSQLSERVER, VeeamBackupSvc",
        "commands_run": "net stop MSSQLSERVER /y & net stop VeeamBackupSvc /y & taskkill.exe /F /IM sqlservr.exe /IM veeam.exe",
        "mitre_tactic": "Impact (TA0040)",
        "mitre_technique": "T1489 - Service Stop",
        "related_log_link": "https://siem.internal.example/events/service-stop-mssql",
        "is_key_evidence": False,
        "notes": "Database files (.mdf, .ldf) unmounted and made accessible for encryption.",
    },
    {
        "evidence_type": "SEARCH",
        "analyst_name": "Kratos of Sparta",
        "timestamp": "2026-10-28T03:57:12Z",
        "end_timestamp": "2026-10-28T04:12:45Z",
        "summary": "Fimbulwinter Ransomware payload executed across 14 hosts and network shares, encrypting files and appending .RAGNAROK extension.",
        "affected_asset": "FS-MIDGARD-01, DB-VALHALLA-01, HYPERV-NILFHEIM-01 (14 Hosts)",
        "affected_user": "MIDGARD\\adm_fimbulwinter",
        "user_created_by_attacker": True,
        "malicious_hosts_ips": "fimbulwinter.exe, .RAGNAROK, HOW_TO_RESTORE_MIDGARD_FILES.txt",
        "commands_run": "fimbulwinter.exe --threads 16 --path \\\\*\\C$ --path \\\\*\\D$ --path \\\\*\\E$ --note HOW_TO_RESTORE_MIDGARD_FILES.txt",
        "mitre_tactic": "Impact (TA0040)",
        "mitre_technique": "T1486 - Data Encrypted for Impact",
        "related_log_link": "https://siem.internal.example/events/ransomware-mass-encrypt-01",
        "search_result_link": "https://siem.internal.example/app/discover#/view/ragnarok-mass-encryption",
        "search_query_link": "https://siem.internal.example/app/discover#/?_q=(file.extension:RAGNAROK%20OR%20file.name:HOW_TO_RESTORE_MIDGARD_FILES.txt)",
        "is_key_evidence": True,
        "notes": "Multi-threaded ransomware binary utilized ChaCha20 symmetric stream cipher and RSA-4096 master public key.",
    },
    {
        "evidence_type": "ATOMIC",
        "analyst_name": "Kratos of Sparta",
        "timestamp": "2026-10-28T04:15:00Z",
        "summary": "Emergency SOC containment: Core network switches severed, affected VLANs isolated, and C2 IPs blackholed at edge border firewalls.",
        "affected_asset": "PERIMETER-FIREWALL-01",
        "affected_user": "Kratos of Sparta",
        "user_created_by_attacker": False,
        "malicious_hosts_ips": "194.26.29.112, 185.196.8.24, 109.236.81.45",
        "commands_run": "panos-cli# set rule 'RANSOMWARE-EMERGENCY-DROP' action drop source any destination [194.26.29.112, 185.196.8.24]",
        "mitre_tactic": "Containment",
        "mitre_technique": "Network Isolation & Null-Route Containment",
        "related_log_link": "https://fw.internal.example/logs/emergency-drop-9921",
        "is_key_evidence": True,
        "notes": "Fimbulwinter ransomware propagation halted. Offline backup recovery and forensics triage initiated under Incident Commander Kratos.",
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

if total_timeline == 12:
    print(f"\n✅ Verification SUCCESS: 1 item ingested individually + 11 items ingested in bulk = 12 total items on '{inv_id}'!")
else:
    print(f"\n⚠️ Unexpected event count: expected 12, found {total_timeline}")
