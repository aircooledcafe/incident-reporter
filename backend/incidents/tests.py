import csv
import io
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone as dt_timezone
from pathlib import Path
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from PIL import Image as PilImage

from .models import Project, EvidenceItem
from .defang import defang_text


class IncidentReporterTests(TestCase):
    def setUp(self):
        self.temp_artifacts_dir = tempfile.mkdtemp()
        self.override = override_settings(
            ARTIFACTS_ROOT=Path(self.temp_artifacts_dir),
            MEDIA_ROOT=Path(self.temp_artifacts_dir),
        )
        self.override.enable()
        self.client = APIClient()

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.temp_artifacts_dir, ignore_errors=True)

    def _make_png_bytes(self) -> bytes:
        buf = io.BytesIO()
        img = PilImage.new("RGB", (200, 100), color=(40, 40, 40))
        img.save(buf, format="PNG")
        return buf.getvalue()

    def test_defang_text(self):
        sample = "https://evil.domain.com/payload.exe 192.168.1.1 http://test.org"
        defanged = defang_text(sample)
        self.assertIn("hxxps[:]//", defanged)
        self.assertIn("hxxp[:]//", defanged)
        self.assertIn("192.168[.]1.1", defanged)
        self.assertIn("domain[.]com", defanged)
        self.assertIn("payload[.]exe", defanged)

    def test_project_creation_creates_artifact_folder_without_raw_artifacts(self):
        res = self.client.post(
            "/api/projects/",
            {"title": "Ransomware Triage Alpha", "customer_name": "Globex Corp"},
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertTrue(data["artifact_folder"].startswith("project_"))

        project_dir = Path(self.temp_artifacts_dir) / data["artifact_folder"]
        self.assertTrue(project_dir.exists())
        self.assertTrue((project_dir / "screenshots").exists())
        self.assertTrue((project_dir / "reports").exists())
        self.assertFalse((project_dir / "raw_artifacts").exists())
        self.assertTrue((project_dir / "archive_manifest.json").exists())

    def test_multi_analyst_timeline_mitre_and_reports(self):
        project = Project.objects.create(
            title="APT Intrusion Case",
            customer_name="Initech",
            customer_id="CUST-100",
            ticket_id="INC-500",
            ticket_link="https://tickets.example/INC-500",
            summary="Compromised edge server followed by lateral movement.",
            key_assets_affected="WEB-01 (10.0.0.5), DB-01",
            key_users_affected="www-data, backdoor_adm",
            key_malicious_indicators="192.168.1.1, evil.com",
        )

        # Later event (03:00 UTC) - Search Result with attacker-created user & MITRE
        ev_later = EvidenceItem.objects.create(
            project=project,
            evidence_type=EvidenceItem.EVIDENCE_TYPE_SEARCH,
            analyst_name="Analyst Bob",
            timestamp=datetime(2026, 10, 17, 3, 0, 0, tzinfo=dt_timezone.utc),
            end_timestamp=datetime(2026, 10, 17, 3, 30, 0, tzinfo=dt_timezone.utc),
            summary="Persistence account backdoor_adm created.",
            affected_asset="DB-01",
            affected_user="backdoor_adm",
            user_created_by_attacker=True,
            malicious_hosts_ips="192.168.1.1, evil.com",
            commands_run="net user backdoor_adm Pass123! /add",
            mitre_tactic="Persistence (TA0003)",
            mitre_technique="T1136.002 - Create Account: Domain Account",
            search_result_link="https://siem.example/results/99",
            search_query_link="https://siem.example/query/99",
            notes="Confirmed created by threat actor.",
            is_key_evidence=True,
        )

        # Earlier event (01:00 UTC) - Atomic Event (Key Evidence)
        ev_earlier = EvidenceItem.objects.create(
            project=project,
            evidence_type=EvidenceItem.EVIDENCE_TYPE_ATOMIC,
            analyst_name="Analyst Alice",
            timestamp=datetime(2026, 10, 17, 1, 0, 0, tzinfo=dt_timezone.utc),
            summary="Initial web shell execution alert from IDS.",
            affected_asset="WEB-01 (10.0.0.5)",
            affected_user="www-data",
            malicious_hosts_ips="192.168.1.1",
            commands_run="whoami && shell.exe",
            mitre_tactic="Execution (TA0002)",
            mitre_technique="T1059 - Command and Scripting Interpreter",
            related_log_link="https://ids.example/alert/101",
            notes="Initial foothold.",
            is_key_evidence=True,
        )

        # Middle event (02:00 UTC) - NOT flagged as key evidence
        ev_middle = EvidenceItem.objects.create(
            project=project,
            evidence_type=EvidenceItem.EVIDENCE_TYPE_ATOMIC,
            analyst_name="Analyst Charlie",
            timestamp=datetime(2026, 10, 17, 2, 0, 0, tzinfo=dt_timezone.utc),
            summary="Routine port scan noise on internal interface.",
            affected_asset="WEB-01 (10.0.0.5)",
            affected_user="www-data",
            is_key_evidence=False,
        )

        upload = SimpleUploadedFile(
            "webshell_alert.png",
            self._make_png_bytes(),
            content_type="image/png",
        )
        shot_res = self.client.post(
            "/api/screenshots/",
            {
                "evidence": ev_earlier.id,
                "image": upload,
                "caption": "IDS Webshell Alert Screenshot",
                "analyst_name": "Analyst Alice",
            },
            format="multipart",
        )
        self.assertEqual(shot_res.status_code, 201)

        # Verify Report 1: CSV Timeline Report
        csv_res = self.client.get(f"/api/projects/{project.id}/report_csv/")
        self.assertEqual(csv_res.status_code, 200)
        rows = list(csv.reader(io.StringIO(csv_res.content.decode("utf-8"))))
        self.assertEqual(len(rows), 4)
        self.assertIn("192.168[.]1.1", rows[1][11])
        # Analyst log link is NOT defanged
        self.assertEqual(rows[1][15], "https://ids.example/alert/101")

        # Verify Report 2 (ODT): Starts with Timestamp (no [Key Evidence]), tables at bottom, links not defanged
        odt_res = self.client.get(f"/api/projects/{project.id}/report_odt/")
        self.assertEqual(odt_res.status_code, 200)
        with zipfile.ZipFile(io.BytesIO(odt_res.content), "r") as zf:
            xml_text = zf.read("content.xml").decode("utf-8")
            self.assertNotIn("[Key Evidence]", xml_text)
            self.assertIn("2026-10-17 01:00:00 UTC, WEB-01 (10.0[.]0.5), www-data:", xml_text)
            self.assertIn("192.168[.]1.1", xml_text)
            self.assertIn("https://ids.example/alert/101", xml_text)
            self.assertIn("KeyAssetsAffectedTable", xml_text)
            self.assertIn("KeyMaliciousIndicatorsTable", xml_text)
            self.assertIn("MitreTacticsTechniquesTable", xml_text)

        # Verify Report 2 (Markdown): Starts with Timestamp, tables at bottom, links not defanged
        md_res = self.client.get(f"/api/projects/{project.id}/report_md/")
        self.assertEqual(md_res.status_code, 200)
        md_text = md_res.content.decode("utf-8")
        self.assertNotIn("[Key Evidence]", md_text)
        self.assertIn("### 2026-10-17 01:00:00 UTC, WEB-01 (10.0[.]0.5), www-data:", md_text)
        self.assertIn("- https://ids.example/alert/101", md_text)
        self.assertIn("| Key Assets Affected |", md_text)
        self.assertIn("| Key Malicious Indicators |", md_text)
        self.assertIn("| MITRE Tactic | MITRE Technique | Affected Assets |", md_text)

        # Verify screenshot deletion
        shot_id = shot_res.json()["id"]
        del_res = self.client.delete(f"/api/screenshots/{shot_id}/")
        self.assertEqual(del_res.status_code, 204)
        self.assertEqual(ev_earlier.screenshots.count(), 0)

    def test_seed_demo_creates_20_events_7_key_and_removable_research(self):
        res = self.client.post("/api/projects/seed_demo/")
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["evidence_count"], 20)
        self.assertEqual(data["key_evidence_count"], 7)
        key_events = [e for e in data["timeline_evidence"] if e["is_key_evidence"]]
        key_without_screenshots = [e for e in key_events if len(e["screenshots"]) == 0]
        key_with_screenshots = [e for e in key_events if len(e["screenshots"]) > 0]
        self.assertEqual(len(key_without_screenshots), 2)
        self.assertEqual(len(key_with_screenshots), 5)
        self.assertEqual(
            set(data["analysts_contributing"]),
            {"Chrisjen Avasarala", "James Holden"},
        )
        # All external research items are stored in external_research_items and individually removable
        self.assertEqual(data["external_research_link"], "")
        self.assertEqual(len(data["external_research_items"]), 3)
        first_res_id = data["external_research_items"][0]["id"]
        del_res = self.client.delete(f"/api/external-research/{first_res_id}/")
        self.assertEqual(del_res.status_code, 204)

