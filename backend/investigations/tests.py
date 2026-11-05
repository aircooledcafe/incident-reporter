import csv
import io
import json
import os
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone as dt_timezone
from pathlib import Path
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient
from PIL import Image as PilImage

from .defang import defang_text
from .models import (
    Customer,
    CustomerContact,
    Investigation,
    EvidenceItem,
    Project,
    UserProfile,
    get_or_create_user_profile,
    sync_user_flags_for_role,
)

User = get_user_model()


def create_user_with_role(username: str, password: str, role: str, **extra):
    is_super = role == UserProfile.ROLE_SUPER_ADMIN
    user = User.objects.create_user(
        username=username,
        password=password,
        is_superuser=is_super,
        is_staff=is_super,
        **extra,
    )
    profile = get_or_create_user_profile(user)
    profile.role = role
    profile.save(update_fields=['role', 'updated_at'])
    sync_user_flags_for_role(user, role)
    user.refresh_from_db()
    return user


class IncidentReporterTests(TestCase):
    def setUp(self):
        self.temp_artifacts_dir = tempfile.mkdtemp()
        self.override = override_settings(
            ARTIFACTS_ROOT=Path(self.temp_artifacts_dir),
            MEDIA_ROOT=Path(self.temp_artifacts_dir),
        )
        self.override.enable()
        self.client = APIClient()
        self.factory = RequestFactory()

        # Default users for role-based tests
        self.super_admin = create_user_with_role(
            "superadmin", "Str0ngSuperPass!99", UserProfile.ROLE_SUPER_ADMIN,
            first_name="Chrisjen", last_name="Avasarala",
        )
        self.admin_user = create_user_with_role(
            "socadmin", "Str0ngAdminPass!99", UserProfile.ROLE_ADMIN,
            first_name="Camina", last_name="Drummer",
        )
        self.analyst_user = create_user_with_role(
            "analyst1", "Str0ngAnalystPass!99", UserProfile.ROLE_ANALYST,
            first_name="James", last_name="Holden",
        )
        self.exec_user = create_user_with_role(
            "executive1", "Str0ngExecPass!99", UserProfile.ROLE_EXECUTIVE,
            first_name="Sadavir", last_name="Errinwright",
        )

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

    def test_unauthenticated_blocked_and_initial_setup_flow(self):
        # Unauthenticated API calls are blocked
        unauth_res = self.client.get("/api/projects/")
        self.assertIn(unauth_res.status_code, (401, 403))

        # Clear users to test brand-new DB initial setup
        User.objects.all().delete()
        status_res = self.client.get("/api/auth/status/")
        self.assertEqual(status_res.status_code, 200)
        self.assertFalse(status_res.json()["authenticated"])
        self.assertTrue(status_res.json()["needs_initial_setup"])

        setup_res = self.client.post(
            "/api/auth/setup/",
            {
                "username": "first_root",
                "password": "InitSuperSecure!2026",
                "first_name": "Root",
                "last_name": "Operator",
                "email": "root@soc.example",
            },
            format="json",
        )
        self.assertEqual(setup_res.status_code, 201)
        self.assertEqual(setup_res.json()["user"]["role"], UserProfile.ROLE_SUPER_ADMIN)

        # Second call to setup must be forbidden
        second_setup = self.client.post(
            "/api/auth/setup/",
            {"username": "attacker", "password": "InitSuperSecure!2026"},
            format="json",
        )
        self.assertEqual(second_setup.status_code, 403)

    def test_login_logout_and_change_own_password(self):
        login_res = self.client.post(
            "/api/auth/login/",
            {"username": "analyst1", "password": "Str0ngAnalystPass!99"},
            format="json",
        )
        self.assertEqual(login_res.status_code, 200)
        self.assertEqual(login_res.json()["user"]["role"], UserProfile.ROLE_ANALYST)

        # Change own password
        pw_res = self.client.post(
            "/api/auth/change-password/",
            {
                "current_password": "Str0ngAnalystPass!99",
                "new_password": "Upd4tedAnalystPass!99",
            },
            format="json",
        )
        self.assertEqual(pw_res.status_code, 200)

        # Logout and log back in with new password
        self.assertEqual(self.client.post("/api/auth/logout/").status_code, 200)
        old_login = self.client.post(
            "/api/auth/login/",
            {"username": "analyst1", "password": "Str0ngAnalystPass!99"},
            format="json",
        )
        self.assertEqual(old_login.status_code, 401)
        new_login = self.client.post(
            "/api/auth/login/",
            {"username": "analyst1", "password": "Upd4tedAnalystPass!99"},
            format="json",
        )
        self.assertEqual(new_login.status_code, 200)

    def test_project_creation_creates_artifact_folder_without_raw_artifacts(self):
        self.client.force_authenticate(user=self.analyst_user)
        res = self.client.post(
            "/api/projects/",
            {"title": "Ransomware Triage Alpha", "customer_name": "Globex Corp"},
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertTrue(data["artifact_folder"].startswith("investigation_") or data["artifact_folder"].startswith("project_"))
        self.assertEqual(data["lead_analyst"], "James Holden")

        project_dir = Path(self.temp_artifacts_dir) / data["artifact_folder"]
        self.assertTrue(project_dir.exists())
        self.assertTrue((project_dir / "screenshots").exists())
        self.assertTrue((project_dir / "reports").exists())
        self.assertFalse((project_dir / "raw_artifacts").exists())
        self.assertTrue((project_dir / "archive_manifest.json").exists())

    def test_multi_analyst_timeline_mitre_reports_and_protected_artifacts(self):
        self.client.force_authenticate(user=self.analyst_user)
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

        EvidenceItem.objects.create(
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

        EvidenceItem.objects.create(
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
        image_url = shot_res.json()["image_url"]

        # Unauthenticated direct access to /artifacts/... must be rejected (401)
        anon_client = APIClient()
        self.assertEqual(anon_client.get(image_url).status_code, 401)

        # Authenticated session access to /artifacts/... succeeds (200)
        session_client = APIClient()
        session_client.login(username="executive1", password="Str0ngExecPass!99")
        shot_fetch = session_client.get(image_url)
        self.assertEqual(shot_fetch.status_code, 200)
        list(shot_fetch.streaming_content)

        # Verify Report 1: CSV Timeline Report & Filename Format (date_customer_id_ticket_investigation_id.csv)
        expected_date = project.created_at.astimezone(dt_timezone.utc).strftime("%Y-%m-%d")
        csv_res = self.client.get(f"/api/projects/{project.id}/report_csv/")
        self.assertEqual(csv_res.status_code, 200)
        self.assertEqual(
            csv_res["Content-Disposition"],
            f'attachment; filename="{expected_date}_CUST-100_INC-500_{project.id}.csv"',
        )
        rows = list(csv.reader(io.StringIO(csv_res.content.decode("utf-8"))))
        self.assertEqual(len(rows), 4)
        self.assertIn("192.168[.]1.1", rows[1][11])
        self.assertEqual(rows[1][15], "https://ids.example/alert/101")

        # Verify Report 2 (ODT) & Investigation wording + filename
        odt_res = self.client.get(f"/api/projects/{project.id}/report_odt/")
        self.assertEqual(odt_res.status_code, 200)
        self.assertEqual(
            odt_res["Content-Disposition"],
            f'attachment; filename="{expected_date}_CUST-100_INC-500_{project.id}.odt"',
        )
        with zipfile.ZipFile(io.BytesIO(odt_res.content), "r") as zf:
            xml_text = zf.read("content.xml").decode("utf-8")
            self.assertNotIn("[Key Evidence]", xml_text)
            self.assertIn("Summary of Investigation", xml_text)
            self.assertIn("Investigation Summary Tables", xml_text)
            self.assertIn("2026-10-17 01:00:00 UTC, WEB-01 (10.0[.]0.5), www-data:", xml_text)
            self.assertIn("192.168[.]1.1", xml_text)
            self.assertIn("https://ids.example/alert/101", xml_text)
            self.assertIn("KeyAssetsAffectedTable", xml_text)
            self.assertIn("KeyMaliciousIndicatorsTable", xml_text)
            self.assertIn("MitreTacticsTechniquesTable", xml_text)

        # Verify Report 2 (Markdown & ZIP) + filename
        md_res = self.client.get(f"/api/projects/{project.id}/report_md/")
        self.assertEqual(md_res.status_code, 200)
        self.assertEqual(
            md_res["Content-Disposition"],
            f'attachment; filename="{expected_date}_CUST-100_INC-500_{project.id}.md"',
        )
        md_text = md_res.content.decode("utf-8")
        self.assertNotIn("[Key Evidence]", md_text)
        self.assertIn("## Summary of Investigation", md_text)
        self.assertIn("### 2026-10-17 01:00:00 UTC, WEB-01 (10.0[.]0.5), www-data:", md_text)

        zip_res = self.client.get(f"/api/projects/{project.id}/report_md/?bundle=zip")
        self.assertEqual(zip_res.status_code, 200)
        self.assertEqual(
            zip_res["Content-Disposition"],
            f'attachment; filename="{expected_date}_CUST-100_INC-500_{project.id}.zip"',
        )

        # Verify filename omits ticket when no ticket is present on the investigation
        no_ticket_inv = Project.objects.create(
            title="Unticketed Threat Hunt",
            customer_name="Initech",
            customer_id="CUST-100",
            ticket_id="",
        )
        no_ticket_date = no_ticket_inv.created_at.astimezone(dt_timezone.utc).strftime("%Y-%m-%d")
        no_ticket_csv = self.client.get(f"/api/projects/{no_ticket_inv.id}/report_csv/")
        self.assertEqual(no_ticket_csv.status_code, 200)
        self.assertEqual(
            no_ticket_csv["Content-Disposition"],
            f'attachment; filename="{no_ticket_date}_CUST-100_{no_ticket_inv.id}.csv"',
        )

        # Verify screenshot deletion
        shot_id = shot_res.json()["id"]
        del_res = self.client.delete(f"/api/screenshots/{shot_id}/")
        self.assertEqual(del_res.status_code, 204)
        self.assertEqual(ev_earlier.screenshots.count(), 0)

    def test_seed_demo_super_admin_only_and_all_four_scenarios(self):
        # Executive, Analyst, and Admin MUST be denied access to sample incident seeding
        for non_super in (self.exec_user, self.analyst_user, self.admin_user):
            self.client.force_authenticate(user=non_super)
            self.assertEqual(self.client.get("/api/projects/demo_scenarios/").status_code, 403)
            self.assertEqual(self.client.post("/api/projects/seed_demo/").status_code, 403)

        # Super Admin CAN list and load all 5 themed sample scenarios
        self.client.force_authenticate(user=self.super_admin)
        cat_res = self.client.get("/api/projects/demo_scenarios/")
        self.assertEqual(cat_res.status_code, 200)
        scenario_ids = [s["id"] for s in cat_res.json()]
        self.assertEqual(scenario_ids, ["expanse", "star_trek", "matrix", "star_wars", "god_of_war"])

        # 1. Expanse scenario (default)
        expanse_res = self.client.post("/api/projects/seed_demo/", {"scenario": "expanse"}, format="json")
        self.assertEqual(expanse_res.status_code, 201)
        expanse_data = expanse_res.json()
        self.assertEqual(expanse_data["evidence_count"], 20)
        self.assertEqual(expanse_data["key_evidence_count"], 7)
        self.assertEqual(len(expanse_data["external_research_items"]), 3)
        self.assertGreaterEqual(len(expanse_data["customer_contacts"]), 2)
        self.assertGreaterEqual(len(expanse_data["related_incidents"]), 2)
        self.assertTrue(expanse_data["action_plan"])

        first_res_id = expanse_data["external_research_items"][0]["id"]
        self.assertEqual(self.client.delete(f"/api/external-research/{first_res_id}/").status_code, 204)

        # 2. Star Trek scenario (website compromise + web shells)
        trek_res = self.client.post("/api/projects/seed_demo/", {"scenario": "star_trek"}, format="json")
        self.assertEqual(trek_res.status_code, 201)
        self.assertIn("Web Shell", trek_res.json()["title"])
        self.assertGreaterEqual(trek_res.json()["key_evidence_count"], 4)

        # 3. Matrix scenario (ClickFix -> DC takeover)
        matrix_res = self.client.post("/api/projects/seed_demo/", {"scenario": "matrix"}, format="json")
        self.assertEqual(matrix_res.status_code, 201)
        self.assertIn("ClickFix", matrix_res.json()["title"])
        self.assertGreaterEqual(matrix_res.json()["key_evidence_count"], 4)

        # 4. Star Wars scenario (MitM phishing -> spam & multi-account takeover)
        sw_res = self.client.post("/api/projects/seed_demo/", {"scenario": "star_wars"}, format="json")
        self.assertEqual(sw_res.status_code, 201)
        self.assertIn("MitM", sw_res.json()["title"])
        self.assertGreaterEqual(sw_res.json()["key_evidence_count"], 4)

        # 5. God of War scenario (Fimbulwinter ransomware attack)
        gow_res = self.client.post("/api/projects/seed_demo/", {"scenario": "god_of_war"}, format="json")
        self.assertEqual(gow_res.status_code, 201)
        self.assertIn("Ransomware", gow_res.json()["title"])
        self.assertEqual(gow_res.json()["customer_name"], "Midgard Realmworks Technologies")
        self.assertGreaterEqual(gow_res.json()["key_evidence_count"], 4)
        self.assertEqual(len(gow_res.json()["related_incidents"]), 3)
        self.assertEqual(len(gow_res.json()["customer_contacts"]), 3)

    def test_profile_avatar_preferred_display_name_and_pronouns(self):
        self.client.force_authenticate(user=self.analyst_user)
        avatar_upload = SimpleUploadedFile(
            "holden_avatar.png",
            self._make_png_bytes(),
            content_type="image/png",
        )
        patch_res = self.client.patch(
            "/api/auth/profile/",
            {
                "preferred_display_name": "Capt. Jim Holden",
                "job_role": "Incident Commander",
                "pronouns": "he/him",
                "avatar": avatar_upload,
            },
            format="multipart",
        )
        self.assertEqual(patch_res.status_code, 200)
        profile_json = patch_res.json()
        self.assertEqual(profile_json["preferred_display_name"], "Capt. Jim Holden")
        self.assertEqual(profile_json["display_name"], "Capt. Jim Holden")
        self.assertEqual(profile_json["job_role"], "Incident Commander")
        self.assertEqual(profile_json["pronouns"], "he/him")
        self.assertTrue(profile_json["avatar_url"].startswith("/artifacts/avatars/"))

        # Avatar file exists inside external ARTIFACTS_ROOT
        rel_avatar = profile_json["avatar_url"].replace("/artifacts/", "", 1)
        avatar_disk_path = Path(self.temp_artifacts_dir) / rel_avatar
        self.assertTrue(avatar_disk_path.exists())

        # Remove avatar cleans up disk file and resets avatar_url
        rem_res = self.client.patch(
            "/api/auth/profile/",
            {"remove_avatar": "true"},
            format="multipart",
        )
        self.assertEqual(rem_res.status_code, 200)
        self.assertEqual(rem_res.json()["avatar_url"], "")
        self.assertFalse(avatar_disk_path.exists())

    def test_related_incidents_customer_contacts_action_plan_and_multi_mitre(self):
        self.client.force_authenticate(user=self.analyst_user)
        proj_res = self.client.post(
            "/api/projects/",
            {
                "title": "Escalated Web Intrusion",
                "customer_name": "Acme Orbital",
                "action_plan": "1. Isolate web tier\n2. Collect Nginx access logs",
                "key_customer_contacts": "24/7 Bridge: +1-555-0100",
            },
            format="json",
        )
        self.assertEqual(proj_res.status_code, 201)
        proj_id = proj_res.json()["id"]

        rel_res = self.client.post(
            "/api/related-incidents/",
            {
                "project": proj_id,
                "title": "SIEM-101: Initial WAF Alert",
                "link": "https://soc.example/tickets/SIEM-101",
            },
            format="json",
        )
        self.assertEqual(rel_res.status_code, 201)
        rel_id = rel_res.json()["id"]

        contact_res = self.client.post(
            "/api/customer-contacts/",
            {
                "project": proj_id,
                "name": "Ellen Ripley",
                "notes": "Primary incident commander",
            },
            format="json",
        )
        self.assertEqual(contact_res.status_code, 201)
        contact_id = contact_res.json()["id"]

        # Multi-select MITRE tactics and techniques on a single evidence item
        ev_res = self.client.post(
            "/api/evidence/",
            {
                "project": proj_id,
                "evidence_type": "ATOMIC",
                "summary": "Public exploit dropped web shell",
                "affected_asset": "WEB-01 (10.10.2.5)",
                "mitre_tactic": "Initial Access (TA0001); Persistence (TA0003)",
                "mitre_technique": (
                    "T1190 - Exploit Public-Facing Application; "
                    "T1505.003 - Server Software Component: Web Shell"
                ),
                "is_key_evidence": True,
            },
            format="json",
        )
        self.assertEqual(ev_res.status_code, 201)

        detail = self.client.get(f"/api/projects/{proj_id}/").json()
        self.assertIn("Isolate web tier", detail["action_plan"])
        self.assertEqual(len(detail["related_incidents"]), 1)
        self.assertEqual(len(detail["customer_contacts"]), 1)

        mitre_pairs = {(m["tactic"], m["technique"]) for m in detail["mitre_summary"]}
        self.assertIn(
            ("Initial Access (TA0001)", "T1190 - Exploit Public-Facing Application"),
            mitre_pairs,
        )
        self.assertIn(
            ("Persistence (TA0003)", "T1505.003 - Server Software Component: Web Shell"),
            mitre_pairs,
        )

        # Locking project blocks adding/removing related incidents and contacts
        self.client.force_authenticate(user=self.admin_user)
        self.assertEqual(self.client.post(f"/api/projects/{proj_id}/lock/").status_code, 200)

        self.client.force_authenticate(user=self.analyst_user)
        self.assertEqual(self.client.delete(f"/api/related-incidents/{rel_id}/").status_code, 403)
        self.assertEqual(self.client.delete(f"/api/customer-contacts/{contact_id}/").status_code, 403)

    def test_executive_role_read_only_and_report_export(self):
        project = Project.objects.create(title="Executive Review Case", ticket_id="SOC-1")
        ev = EvidenceItem.objects.create(project=project, summary="Initial event")

        self.client.force_authenticate(user=self.exec_user)

        # Executive CAN view projects, timeline, and export all reports
        self.assertEqual(self.client.get("/api/projects/").status_code, 200)
        self.assertEqual(self.client.get(f"/api/projects/{project.id}/").status_code, 200)
        self.assertEqual(self.client.get(f"/api/projects/{project.id}/timeline/").status_code, 200)
        self.assertEqual(self.client.get(f"/api/projects/{project.id}/report_csv/").status_code, 200)
        self.assertEqual(self.client.get(f"/api/projects/{project.id}/report_odt/").status_code, 200)
        self.assertEqual(self.client.get(f"/api/projects/{project.id}/report_md/").status_code, 200)

        # Executive CANNOT create/update/delete/lock projects or modify evidence/users
        self.assertEqual(
            self.client.post("/api/projects/", {"title": "Forbidden"}, format="json").status_code,
            403,
        )
        self.assertEqual(
            self.client.patch(f"/api/projects/{project.id}/", {"title": "Edit"}, format="json").status_code,
            403,
        )
        self.assertEqual(self.client.delete(f"/api/projects/{project.id}/").status_code, 403)
        self.assertEqual(self.client.post(f"/api/projects/{project.id}/lock/").status_code, 403)
        self.assertEqual(
            self.client.post("/api/evidence/", {"project": project.id, "summary": "Nope"}, format="json").status_code,
            403,
        )
        self.assertEqual(self.client.post(f"/api/evidence/{ev.id}/toggle_key/").status_code, 403)
        self.assertEqual(self.client.get("/api/auth/api-token/").status_code, 403)
        self.assertEqual(self.client.get("/api/users/").status_code, 403)

    def test_analyst_permissions_and_token_soc_ingest(self):
        self.client.force_authenticate(user=self.analyst_user)
        proj_res = self.client.post(
            "/api/projects/",
            {"title": "Analyst Case", "ticket_id": "SOC-777"},
            format="json",
        )
        self.assertEqual(proj_res.status_code, 201)
        proj_id = proj_res.json()["id"]

        # Analyst cannot lock/unlock or delete projects or manage users
        self.assertEqual(self.client.post(f"/api/projects/{proj_id}/lock/").status_code, 403)
        self.assertEqual(self.client.delete(f"/api/projects/{proj_id}/").status_code, 403)
        self.assertEqual(self.client.get("/api/users/").status_code, 403)

        # Analyst CAN obtain an API token and push via /api/soc/ingest/
        tok_res = self.client.get("/api/auth/api-token/")
        self.assertEqual(tok_res.status_code, 200)
        token_key = tok_res.json()["token"]

        token_client = APIClient()
        token_client.credentials(HTTP_AUTHORIZATION=f"Token {token_key}")
        ingest_res = token_client.post(
            "/api/soc/ingest/",
            {
                "ticket_id": "SOC-777",
                "evidence_type": "ATOMIC",
                "summary": "SIEM automated alert push",
                "is_key_evidence": True,
            },
            format="json",
        )
        self.assertEqual(ingest_res.status_code, 201)
        self.assertEqual(ingest_res.json()["analyst_name"], "James Holden")

    def test_admin_permissions_and_no_db_admin_access(self):
        # Verify Admin does NOT have Django /admin/ database access
        self.assertFalse(self.admin_user.is_staff)
        self.assertFalse(self.admin_user.is_superuser)
        req = self.factory.get("/admin/")
        req.user = self.admin_user
        self.assertFalse(admin.site.has_permission(req))

        self.client.force_authenticate(user=self.admin_user)

        # Admin CAN create Analyst & Executive users
        create_analyst = self.client.post(
            "/api/users/",
            {
                "username": "new_analyst",
                "password": "ValidPassword!2026",
                "role": UserProfile.ROLE_ANALYST,
            },
            format="json",
        )
        self.assertEqual(create_analyst.status_code, 201)
        new_uid = create_analyst.json()["id"]

        # Admin CAN assign roles between ANALYST and EXECUTIVE for lesser users
        role_upd = self.client.patch(
            f"/api/users/{new_uid}/",
            {"role": UserProfile.ROLE_EXECUTIVE},
            format="json",
        )
        self.assertEqual(role_upd.status_code, 200)
        self.assertEqual(role_upd.json()["role"], UserProfile.ROLE_EXECUTIVE)

        # Admin CAN reset passwords for lesser users (Analyst / Executive)
        pw_reset = self.client.post(
            f"/api/users/{new_uid}/reset_password/",
            {"new_password": "ResetByAdmin!2026"},
            format="json",
        )
        self.assertEqual(pw_reset.status_code, 200)

        # Admin CANNOT create ADMIN or SUPER_ADMIN users
        self.assertEqual(
            self.client.post(
                "/api/users/",
                {
                    "username": "rogue_admin",
                    "password": "ValidPassword!2026",
                    "role": UserProfile.ROLE_ADMIN,
                },
                format="json",
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(
                "/api/users/",
                {
                    "username": "rogue_super",
                    "password": "ValidPassword!2026",
                    "role": UserProfile.ROLE_SUPER_ADMIN,
                },
                format="json",
            ).status_code,
            403,
        )

        # Admin CANNOT promote a lesser user to ADMIN
        self.assertEqual(
            self.client.patch(
                f"/api/users/{new_uid}/",
                {"role": UserProfile.ROLE_ADMIN},
                format="json",
            ).status_code,
            403,
        )

        # Admin CANNOT reset password or delete Super Admin or another Admin
        other_admin = create_user_with_role("admin2", "Str0ngAdminPass!99", UserProfile.ROLE_ADMIN)
        self.assertEqual(
            self.client.post(
                f"/api/users/{other_admin.id}/reset_password/",
                {"new_password": "HackedPassword!2026"},
                format="json",
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(
                f"/api/users/{self.super_admin.id}/reset_password/",
                {"new_password": "HackedPassword!2026"},
                format="json",
            ).status_code,
            403,
        )
        self.assertEqual(self.client.delete(f"/api/users/{other_admin.id}/").status_code, 403)

        # Admin CAN delete lesser user
        self.assertEqual(self.client.delete(f"/api/users/{new_uid}/").status_code, 204)

    def test_super_admin_full_access_and_self_lockout_guard(self):
        # Super Admin HAS access to Django /admin/
        self.assertTrue(self.super_admin.is_staff)
        self.assertTrue(self.super_admin.is_superuser)
        req = self.factory.get("/admin/")
        req.user = self.super_admin
        self.assertTrue(admin.site.has_permission(req))

        self.client.force_authenticate(user=self.super_admin)

        # Super Admin CAN create, update, reset password, and delete Admin users
        res = self.client.post(
            "/api/users/",
            {
                "username": "managed_admin",
                "password": "C0rrectH0rseBattery!99",
                "role": UserProfile.ROLE_ADMIN,
            },
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        admin_id = res.json()["id"]

        self.assertEqual(
            self.client.post(
                f"/api/users/{admin_id}/reset_password/",
                {"new_password": "N3wQuantumVaultKey!88"},
                format="json",
            ).status_code,
            200,
        )
        self.assertEqual(self.client.delete(f"/api/users/{admin_id}/").status_code, 204)

        # Last active Super Admin cannot delete or demote themselves
        self.assertEqual(self.client.delete(f"/api/users/{self.super_admin.id}/").status_code, 403)
        self.assertEqual(
            self.client.patch(
                f"/api/users/{self.super_admin.id}/",
                {"role": UserProfile.ROLE_ADMIN},
                format="json",
            ).status_code,
            403,
        )

    def test_project_lock_unlock_and_deletion_cleanup(self):
        self.client.force_authenticate(user=self.admin_user)
        proj_res = self.client.post(
            "/api/projects/",
            {"title": "Lockable Investigation", "ticket_id": "LOCK-100"},
            format="json",
        )
        self.assertEqual(proj_res.status_code, 201)
        proj_id = proj_res.json()["id"]
        folder_name = proj_res.json()["artifact_folder"]
        project_dir = Path(self.temp_artifacts_dir) / folder_name
        self.assertTrue(project_dir.exists())

        ev_res = self.client.post(
            "/api/evidence/",
            {"project": proj_id, "summary": "Before lock"},
            format="json",
        )
        self.assertEqual(ev_res.status_code, 201)
        ev_id = ev_res.json()["id"]

        # Lock the project as Admin
        lock_res = self.client.post(f"/api/projects/{proj_id}/lock/")
        self.assertEqual(lock_res.status_code, 200)
        self.assertTrue(lock_res.json()["is_locked"])
        self.assertEqual(lock_res.json()["locked_by_username"], "socadmin")

        manifest = json.loads((project_dir / "archive_manifest.json").read_text(encoding="utf-8"))
        self.assertTrue(manifest["is_locked"])

        # While locked, modifications by Analyst AND Admin are blocked (read-only)
        self.client.force_authenticate(user=self.analyst_user)
        self.assertEqual(
            self.client.patch(f"/api/projects/{proj_id}/", {"title": "Blocked"}, format="json").status_code,
            403,
        )
        self.assertEqual(
            self.client.post("/api/evidence/", {"project": proj_id, "summary": "Blocked"}, format="json").status_code,
            403,
        )
        self.assertEqual(
            self.client.patch(f"/api/evidence/{ev_id}/", {"summary": "Blocked"}, format="json").status_code,
            403,
        )
        self.assertEqual(self.client.post(f"/api/evidence/{ev_id}/toggle_key/").status_code, 403)
        self.assertEqual(self.client.delete(f"/api/evidence/{ev_id}/").status_code, 403)
        self.assertEqual(
            self.client.post(
                "/api/external-research/",
                {"project": proj_id, "link": "https://example.com"},
                format="json",
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(
                "/api/soc/ingest/",
                {"ticket_id": "LOCK-100", "summary": "Blocked ingest"},
                format="json",
            ).status_code,
            403,
        )

        # Reading and exporting reports while locked STILL succeed
        self.assertEqual(self.client.get(f"/api/projects/{proj_id}/report_csv/").status_code, 200)
        self.assertEqual(self.client.get(f"/api/projects/{proj_id}/report_odt/").status_code, 200)

        # Deleting a locked project is blocked until unlocked
        self.client.force_authenticate(user=self.admin_user)
        self.assertEqual(self.client.delete(f"/api/projects/{proj_id}/").status_code, 403)

        # Unlock the project as Admin -> modifications and deletion work again
        unlock_res = self.client.post(f"/api/projects/{proj_id}/unlock/")
        self.assertEqual(unlock_res.status_code, 200)
        self.assertFalse(unlock_res.json()["is_locked"])

        self.assertEqual(
            self.client.patch(f"/api/projects/{proj_id}/", {"title": "Unlocked Edit"}, format="json").status_code,
            200,
        )

        # Delete unlocked project as Admin -> removes DB row and artifact folder
        del_proj = self.client.delete(f"/api/projects/{proj_id}/")
        self.assertEqual(del_proj.status_code, 204)
        self.assertFalse(Project.objects.filter(pk=proj_id).exists())
        self.assertFalse(project_dir.exists())

    def test_ensure_superuser_command_idempotent(self):
        with patch.dict(
            os.environ,
            {
                "DJANGO_SUPERUSER_USERNAME": "env_super",
                "DJANGO_SUPERUSER_PASSWORD": "EnvSuperSecret!2026",
                "DJANGO_SUPERUSER_EMAIL": "env_super@soc.example",
            },
        ):
            call_command("ensure_superuser")
            call_command("ensure_superuser")  # Idempotent second run

        created = User.objects.get(username="env_super")
        self.assertTrue(created.is_superuser)
        self.assertTrue(created.is_staff)
        self.assertEqual(created.profile.role, UserProfile.ROLE_SUPER_ADMIN)

    def test_timeline_item_deletion_restricted_to_creator_admin_or_super_admin(self):
        analyst_two = create_user_with_role(
            "analyst2", "Str0ngAnalyst2Pass!99", UserProfile.ROLE_ANALYST,
            first_name="Amos", last_name="Burton",
        )

        # Analyst 1 creates an investigation and 3 timeline items
        self.client.force_authenticate(user=self.analyst_user)
        proj_res = self.client.post(
            "/api/projects/",
            {"title": "Timeline Ownership Case", "customer_id": "CUST-55"},
            format="json",
        )
        self.assertEqual(proj_res.status_code, 201)
        proj_id = proj_res.json()["id"]

        item_a = self.client.post(
            "/api/evidence/",
            {"project": proj_id, "summary": "Created by Analyst 1 (for creator delete)"},
            format="json",
        ).json()
        item_b = self.client.post(
            "/api/evidence/",
            {"project": proj_id, "summary": "Created by Analyst 1 (for Admin delete)"},
            format="json",
        ).json()
        item_c = self.client.post(
            "/api/evidence/",
            {"project": proj_id, "summary": "Created by Analyst 1 (for Super Admin delete)"},
            format="json",
        ).json()

        self.assertEqual(item_a["created_by"], self.analyst_user.id)
        self.assertEqual(item_a["created_by_username"], "analyst1")
        self.assertTrue(item_a["can_actor_delete"])

        # Analyst 2 (did NOT create these items) sees can_actor_delete=False and CANNOT delete them (403)
        self.client.force_authenticate(user=analyst_two)
        proj_detail_a2 = self.client.get(f"/api/projects/{proj_id}/").json()
        for ev in proj_detail_a2["timeline_evidence"]:
            self.assertFalse(ev["can_actor_delete"])
        self.assertEqual(self.client.delete(f"/api/evidence/{item_a['id']}/").status_code, 403)

        # Executive also CANNOT delete timeline items
        self.client.force_authenticate(user=self.exec_user)
        self.assertEqual(self.client.delete(f"/api/evidence/{item_a['id']}/").status_code, 403)

        # Creator (Analyst 1) CAN delete their own timeline item
        self.client.force_authenticate(user=self.analyst_user)
        self.assertEqual(self.client.delete(f"/api/evidence/{item_a['id']}/").status_code, 204)

        # Admin CAN delete timeline items created by another user
        self.client.force_authenticate(user=self.admin_user)
        proj_detail_admin = self.client.get(f"/api/projects/{proj_id}/").json()
        self.assertTrue(proj_detail_admin["timeline_evidence"][0]["can_actor_delete"])
        self.assertEqual(self.client.delete(f"/api/evidence/{item_b['id']}/").status_code, 204)

        # Super Admin CAN delete timeline items created by another user
        self.client.force_authenticate(user=self.super_admin)
        self.assertEqual(self.client.delete(f"/api/evidence/{item_c['id']}/").status_code, 204)

    def test_screenshot_deletion_restricted_to_creator_admin_or_super_admin(self):
        analyst_two = create_user_with_role(
            "analyst2_shots", "Str0ngAnalyst2Pass!99", UserProfile.ROLE_ANALYST,
            first_name="Amos", last_name="Burton",
        )

        def make_png_upload(name: str) -> SimpleUploadedFile:
            buf = io.BytesIO()
            PilImage.new("RGB", (16, 16), color=(12, 34, 56)).save(buf, format="PNG")
            return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")

        # Analyst 1 creates an investigation, an evidence item, and 3 screenshots
        self.client.force_authenticate(user=self.analyst_user)
        proj_id = self.client.post(
            "/api/projects/",
            {"title": "Screenshot Ownership Case", "customer_id": "CUST-77"},
            format="json",
        ).json()["id"]

        ev_res = self.client.post(
            "/api/evidence/",
            {
                "project": proj_id,
                "summary": "Event with attached screenshots",
                "screenshots_upload": [
                    make_png_upload("shot_creator.png"),
                    make_png_upload("shot_admin.png"),
                    make_png_upload("shot_super.png"),
                ],
                "screenshot_captions": ["Creator Shot", "Admin Shot", "Super Shot"],
            },
            format="multipart",
        )
        self.assertEqual(ev_res.status_code, 201)
        shots = ev_res.json()["screenshots"]
        self.assertEqual(len(shots), 3)
        shot_a, shot_b, shot_c = shots
        self.assertEqual(shot_a["created_by"], self.analyst_user.id)
        self.assertEqual(shot_a["created_by_username"], "analyst1")
        self.assertTrue(shot_a["can_actor_delete"])

        # Analyst 2 (did NOT upload these screenshots) sees can_actor_delete=False and CANNOT delete (403)
        self.client.force_authenticate(user=analyst_two)
        proj_detail_a2 = self.client.get(f"/api/projects/{proj_id}/").json()
        for sh in proj_detail_a2["timeline_evidence"][0]["screenshots"]:
            self.assertFalse(sh["can_actor_delete"])
        self.assertEqual(self.client.delete(f"/api/screenshots/{shot_a['id']}/").status_code, 403)

        # Executive also CANNOT delete screenshots
        self.client.force_authenticate(user=self.exec_user)
        self.assertEqual(self.client.delete(f"/api/screenshots/{shot_a['id']}/").status_code, 403)

        # Uploader (Analyst 1) CAN delete their own screenshot
        self.client.force_authenticate(user=self.analyst_user)
        self.assertEqual(self.client.delete(f"/api/screenshots/{shot_a['id']}/").status_code, 204)

        # Admin CAN delete screenshots uploaded by another user
        self.client.force_authenticate(user=self.admin_user)
        proj_detail_admin = self.client.get(f"/api/projects/{proj_id}/").json()
        self.assertTrue(proj_detail_admin["timeline_evidence"][0]["screenshots"][0]["can_actor_delete"])
        self.assertEqual(self.client.delete(f"/api/screenshots/{shot_b['id']}/").status_code, 204)

        # Super Admin CAN delete screenshots uploaded by another user
        self.client.force_authenticate(user=self.super_admin)
        self.assertEqual(self.client.delete(f"/api/screenshots/{shot_c['id']}/").status_code, 204)

    def test_pcap_attachment_storage_in_artifacts_folder_reports_and_permissions(self):
        analyst_two = create_user_with_role(
            "analyst2_pcap", "Str0ngAnalyst2Pass!99", UserProfile.ROLE_ANALYST,
            first_name="Alex", last_name="Kamal",
        )

        # Minimal valid 24-byte libpcap global header
        pcap_bytes = bytes.fromhex("d4c3b2a1020004000000000000000000ffff000001000000")

        def make_pcap_upload(name: str) -> SimpleUploadedFile:
            return SimpleUploadedFile(name, pcap_bytes, content_type="application/vnd.tcpdump.pcap")

        self.client.force_authenticate(user=self.analyst_user)
        proj_res = self.client.post(
            "/api/projects/",
            {"title": "PCAP Capture Investigation", "customer_id": "CUST-909"},
            format="json",
        )
        self.assertEqual(proj_res.status_code, 201)
        proj_data = proj_res.json()
        proj_id = proj_data["id"]
        artifact_folder = proj_data["artifact_folder"]

        ev_res = self.client.post(
            "/api/evidence/",
            {
                "project": proj_id,
                "summary": "Outbound C2 beacon captured in PCAP",
                "is_key_evidence": "true",
                "pcaps_upload": [
                    make_pcap_upload("c2_beacon.pcap"),
                    make_pcap_upload("dns_tunnel.pcapng"),
                ],
                "pcap_descriptions": ["HTTPS C2 beacon on eth0", "DNS tunneling stream"],
            },
            format="multipart",
        )
        self.assertEqual(ev_res.status_code, 201)
        pcaps = ev_res.json()["pcaps"]
        self.assertEqual(len(pcaps), 2)
        pcap_a, pcap_b = pcaps
        self.assertEqual(pcap_a["created_by"], self.analyst_user.id)
        self.assertEqual(pcap_a["file_size"], len(pcap_bytes))
        self.assertTrue(pcap_a["can_actor_delete"])

        # Verify PCAPs are stored inside artifacts/<project_folder>/pcaps/ alongside screenshots & reports
        pcap_dir = Path(self.temp_artifacts_dir) / artifact_folder / "pcaps"
        self.assertTrue(pcap_dir.is_dir())
        stored_pcap_path = pcap_dir / pcap_a["filename"]
        self.assertTrue(stored_pcap_path.is_file())
        self.assertEqual(stored_pcap_path.read_bytes(), pcap_bytes)

        # Verify archive_manifest.json includes the attached PCAP paths
        manifest_path = Path(self.temp_artifacts_dir) / artifact_folder / "archive_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(len(manifest["evidence_timeline"][0]["pcaps"]), 2)

        # Unauthenticated download of PCAP must return 401; authenticated ?download=1 returns attachment
        anon_client = APIClient()
        self.assertEqual(anon_client.get(pcap_a["download_url"]).status_code, 401)

        session_client = APIClient()
        session_client.login(username="executive1", password="Str0ngExecPass!99")
        dl_res = session_client.get(pcap_a["download_url"])
        self.assertEqual(dl_res.status_code, 200)
        self.assertIn('attachment; filename="', dl_res["Content-Disposition"])
        self.assertEqual(b"".join(dl_res.streaming_content), pcap_bytes)

        # Verify CSV & Markdown ZIP bundle include PCAP references/files
        csv_res = self.client.get(f"/api/projects/{proj_id}/report_csv/")
        csv_rows = list(csv.reader(io.StringIO(csv_res.content.decode("utf-8"))))
        self.assertEqual(csv_rows[0][17], "PCAPs")
        self.assertIn(pcap_a["filename"], csv_rows[1][17])

        zip_res = self.client.get(f"/api/projects/{proj_id}/report_md/?bundle=zip")
        with zipfile.ZipFile(io.BytesIO(zip_res.content), "r") as zf:
            names = zf.namelist()
            self.assertTrue(any(pcap_a["filename"] in n for n in names))

        # Deletion permissions: non-creator Analyst & Executive denied (403); creator & Admin allowed (204)
        self.client.force_authenticate(user=analyst_two)
        self.assertEqual(self.client.delete(f"/api/pcaps/{pcap_a['id']}/").status_code, 403)

        self.client.force_authenticate(user=self.exec_user)
        self.assertEqual(self.client.delete(f"/api/pcaps/{pcap_a['id']}/").status_code, 403)

        self.client.force_authenticate(user=self.analyst_user)
        self.assertEqual(self.client.delete(f"/api/pcaps/{pcap_a['id']}/").status_code, 204)
        self.assertFalse(stored_pcap_path.exists())

        self.client.force_authenticate(user=self.admin_user)
        self.assertEqual(self.client.delete(f"/api/pcaps/{pcap_b['id']}/").status_code, 204)

    def test_customer_directory_and_investigation_document_model(self):
        """
        Tests the Customer directory, contact escalation tiers, investigation linking,
        lead analyst user selection, embedded timeline document model, and customer protection.
        """
        self.client.force_authenticate(user=self.analyst_user)

        # 1. Create a Customer
        cust_res = self.client.post(
            "/api/customers/",
            {
                "name": "Cyberdyne Systems",
                "customer_id": "CYBERDYNE-01",
                "notes": "Autonomous defense contractor.",
            },
            format="json",
        )
        self.assertEqual(cust_res.status_code, 201)
        cust_data = cust_res.json()
        cust_id = cust_data["id"]
        self.assertEqual(cust_data["name"], "Cyberdyne Systems")
        self.assertEqual(cust_data["customer_id"], "CYBERDYNE-01")

        # 2. Add Contacts across Primary, Secondary, Tertiary escalation tiers
        c1 = self.client.post(
            "/api/customer-contacts/",
            {
                "customer": cust_id,
                "name": "Miles Dyson",
                "escalation_tier": "PRIMARY",
                "notes": "24/7 Primary Emergency Lead",
            },
            format="json",
        )
        self.assertEqual(c1.status_code, 201)
        self.assertTrue(c1.json()["is_primary_escalation"])
        self.assertEqual(c1.json()["escalation_tier_display"], "Primary")

        c2 = self.client.post(
            "/api/customer-contacts/",
            {
                "customer": cust_id,
                "name": "Sarah Connor",
                "escalation_tier": "SECONDARY",
            },
            format="json",
        )
        self.assertEqual(c2.status_code, 201)
        self.assertFalse(c2.json()["is_primary_escalation"])

        # 3. Create an Investigation selecting the Customer & Lead Analyst user
        inv_res = self.client.post(
            "/api/investigations/",
            {
                "customer": cust_id,
                "title": "Neural Net Prototype Anomalous Outbound Traffic",
                "ticket_id": "CYBER-9921",
                "lead_analyst_user": self.analyst_user.id,
                "summary": "High-volume encrypted egress to unlisted cloud node.",
            },
            format="json",
        )
        self.assertEqual(inv_res.status_code, 201)
        inv_data = inv_res.json()
        inv_id = inv_data["id"]
        self.assertEqual(inv_data["customer_name"], "Cyberdyne Systems")
        self.assertEqual(inv_data["customer_code"], "CYBERDYNE-01")
        self.assertEqual(inv_data["lead_analyst"], "James Holden")
        self.assertEqual(len(inv_data["customer_contacts"]), 2)
        self.assertEqual(inv_data["timeline_events"], [])

        # 4. Add an Evidence Item and verify embedded document timeline_events is automatically updated
        ev_res = self.client.post(
            "/api/evidence/",
            {
                "investigation": inv_id,
                "evidence_type": "ATOMIC",
                "summary": "100GB exfiltration from R&D server",
                "affected_asset": "SRV-NEURAL-01 (10.0.1.10)",
                "affected_user": "svc_neural_mesh",
                "mitre_tactic": "Exfiltration (TA0010)",
                "mitre_technique": "T1048 - Exfiltration Over Alternative Protocol",
            },
            format="json",
        )
        self.assertEqual(ev_res.status_code, 201)

        # Refresh investigation detail and verify document timeline_events
        inv_detail = self.client.get(f"/api/investigations/{inv_id}/").json()
        self.assertEqual(len(inv_detail["timeline_events"]), 1)
        doc_event = inv_detail["timeline_events"][0]
        self.assertEqual(doc_event["summary"], "100GB exfiltration from R&D server")
        self.assertEqual(doc_event["affected_asset"], "SRV-NEURAL-01 (10.0.1.10)")

        # 5. Customer deletion protection: Cannot delete customer while an active investigation exists
        self.client.force_authenticate(user=self.admin_user)
        del_cust_blocked = self.client.delete(f"/api/customers/{cust_id}/")
        self.assertEqual(del_cust_blocked.status_code, 403)
        self.assertIn("associated investigation", del_cust_blocked.json()["detail"])

        # 6. Delete investigation, then deleting the customer succeeds (204)
        del_inv = self.client.delete(f"/api/investigations/{inv_id}/")
        self.assertEqual(del_inv.status_code, 204)

        del_cust_ok = self.client.delete(f"/api/customers/{cust_id}/")
        self.assertEqual(del_cust_ok.status_code, 204)

    def test_bulk_evidence_creation_and_timeline_sync(self):
        """
        Tests the bulk evidence creation endpoint (/api/evidence/bulk_create/ and
        /api/investigations/{id}/bulk-evidence/):
        1. Atomic multi-item ingestion with automatic timeline sync.
        2. Validation failure rollbacks.
        3. Project lock enforcement.
        4. Role permission checks (Executive forbidden).
        """
        # Create customer & investigation
        cust = Customer.objects.create(name="Allomancy Logistics", customer_id="CUST-ALLO-01")
        inv = Investigation.objects.create(
            title="House Venture Warehouse Breach",
            customer=cust,
            lead_analyst="Vin",
        )

        # 1. Analyst bulk-posts 3 items to /api/evidence/bulk_create/
        self.client.force_authenticate(user=self.analyst_user)
        payload = {
            "investigation": inv.id,
            "items": [
                {
                    "evidence_type": "ATOMIC",
                    "timestamp": "2026-10-31T08:00:00Z",
                    "summary": "Initial atium cache door compromise",
                    "affected_asset": "VAULT-GATE-01",
                    "mitre_tactic": "Initial Access (TA0001)",
                    "mitre_technique": "T1190 - Exploit Public-Facing Application",
                },
                {
                    "evidence_type": "ATOMIC",
                    "timestamp": "2026-10-31T08:30:00Z",
                    "summary": "Steelpush acoustic sensor tampering",
                    "affected_asset": "SENSOR-SRV-02",
                    "mitre_tactic": "Defense Evasion (TA0005)",
                    "mitre_technique": "T1562.001 - Disable or Modify Tools",
                },
                {
                    "evidence_type": "SEARCH",
                    "timestamp": "2026-10-31T09:00:00Z",
                    "end_timestamp": "2026-10-31T09:45:00Z",
                    "summary": "Continuous metal reserve exfiltration",
                    "affected_asset": "CARGO-DOCK-04",
                    "mitre_tactic": "Exfiltration (TA0010)",
                    "mitre_technique": "T1048 - Exfiltration Over Alternative Protocol",
                    "is_key_evidence": True,
                },
            ],
        }

        res = self.client.post("/api/evidence/bulk_create/", payload, format="json")
        self.assertEqual(res.status_code, 201)
        res_data = res.json()
        self.assertEqual(res_data["status"], "success")
        self.assertEqual(res_data["count"], 3)
        self.assertEqual(len(res_data["items"]), 3)

        # Verify investigation timeline was synchronized
        inv.refresh_from_db()
        self.assertEqual(len(inv.timeline_events), 3)
        self.assertEqual(inv.timeline_events[0]["summary"], "Initial atium cache door compromise")
        self.assertEqual(inv.timeline_events[2]["summary"], "Continuous metal reserve exfiltration")
        self.assertTrue(inv.timeline_events[2]["is_key_evidence"])

        # 2. Ingest via investigation action /api/investigations/{id}/bulk-evidence/
        sub_payload = [
            {
                "evidence_type": "ATOMIC",
                "timestamp": "2026-10-31T10:00:00Z",
                "summary": "Coppercloud trace wiped from perimeter logs",
                "affected_asset": "LOG-SRV-01",
            }
        ]
        res_sub = self.client.post(f"/api/investigations/{inv.id}/bulk-evidence/", sub_payload, format="json")
        self.assertEqual(res_sub.status_code, 201)
        self.assertEqual(res_sub.json()["count"], 1)

        inv.refresh_from_db()
        self.assertEqual(len(inv.timeline_events), 4)

        # 3. Validation failure: an invalid item must roll back everything atomically
        initial_ev_count = EvidenceItem.objects.filter(investigation=inv).count()
        bad_payload = {
            "investigation": inv.id,
            "items": [
                {
                    "evidence_type": "ATOMIC",
                    "summary": "Valid item before error",
                    "timestamp": "2026-10-31T11:00:00Z",
                },
                {
                    "evidence_type": "INVALID_TYPE_ENUM",
                    "summary": "Corrupted item",
                    "timestamp": "not-a-valid-date",
                },
            ],
        }
        bad_res = self.client.post("/api/evidence/bulk_create/", bad_payload, format="json")
        self.assertEqual(bad_res.status_code, 400)
        self.assertIn("error", bad_res.json())
        # Confirm no items were saved (atomic rollback)
        self.assertEqual(EvidenceItem.objects.filter(investigation=inv).count(), initial_ev_count)

        # 4. Project locked enforcement: lock the investigation and attempt bulk creation
        inv.is_locked = True
        inv.locked_by = self.admin_user
        inv.locked_at = timezone.now()
        inv.save()

        locked_res = self.client.post(
            "/api/evidence/bulk_create/",
            {"investigation": inv.id, "items": [{"summary": "Blocked on locked"}]},
            format="json",
        )
        self.assertEqual(locked_res.status_code, 400)
        self.assertIn("locked", str(locked_res.json()).lower())

        inv.is_locked = False
        inv.save()

        # 5. Executive role CANNOT create bulk evidence (read-only RBAC)
        self.client.force_authenticate(user=self.exec_user)
        exec_res = self.client.post(
            "/api/evidence/bulk_create/",
            {"investigation": inv.id, "items": [{"summary": "Exec attempt"}]},
            format="json",
        )
        self.assertEqual(exec_res.status_code, 403)

    def test_human_readable_customer_and_investigation_identifiers_api(self):
        """
        Tests human-readable identifiers across the entire API:
        1. Customer lookup via customer_id (e.g. /api/customers/CANTON-FIN-01/).
        2. Investigation creation referencing customer by customer_id string without numeric DB IDs.
        3. Automatic assignment of INV###### format investigation_id (e.g. INV000001).
        4. Detail, lock, unlock, and bulk-evidence access via /api/investigations/INV######/.
        5. Evidence item single and bulk ingestion referencing investigation by INV######.
        6. SOC ingest webhook matching by INV######.
        """
        import re

        # 1. Create a customer with a custom business customer_id code
        self.client.force_authenticate(user=self.admin_user)
        cust_res = self.client.post(
            "/api/customers/",
            {
                "name": "Canton of Resource & Finance",
                "customer_id": "CANTON-FIN-01",
                "notes": "Luthadel Treasury",
            },
            format="json",
        )
        self.assertEqual(cust_res.status_code, 201)

        # Lookup customer by customer_id string
        get_cust = self.client.get("/api/customers/CANTON-FIN-01/")
        self.assertEqual(get_cust.status_code, 200)
        self.assertEqual(get_cust.json()["customer_id"], "CANTON-FIN-01")

        # 2. Analyst creates investigation referencing customer by customer_id string (no DB PK needed!)
        self.client.force_authenticate(user=self.analyst_user)
        inv_payload = {
            "customer": "CANTON-FIN-01",
            "title": "Operation Tenth Metal Breach",
            "ticket_id": "CANTON-SEC-1024",
            "summary": "Perimeter breach testing allomantic ledgers",
        }
        create_inv_res = self.client.post("/api/investigations/", inv_payload, format="json")
        self.assertEqual(create_inv_res.status_code, 201)
        inv_data = create_inv_res.json()

        # 3. Verify format: INV followed by 6 digits (INV123456 format)
        inv_code = inv_data.get("investigation_id")
        self.assertIsNotNone(inv_code)
        self.assertTrue(bool(re.match(r"^INV\d{6}$", inv_code)), f"Expected INV######, got: {inv_code}")
        self.assertEqual(inv_data["customer_id"], "CANTON-FIN-01")

        # 4. Access investigation detail directly using the human-readable INV###### URL
        detail_res = self.client.get(f"/api/investigations/{inv_code}/")
        self.assertEqual(detail_res.status_code, 200)
        self.assertEqual(detail_res.json()["title"], "Operation Tenth Metal Breach")

        # Lock and unlock using the INV###### identifier
        self.client.force_authenticate(user=self.admin_user)
        lock_res = self.client.post(f"/api/investigations/{inv_code}/lock/")
        self.assertEqual(lock_res.status_code, 200)
        self.assertTrue(lock_res.json()["is_locked"])

        unlock_res = self.client.post(f"/api/investigations/{inv_code}/unlock/")
        self.assertEqual(unlock_res.status_code, 200)
        self.assertFalse(unlock_res.json()["is_locked"])

        # 5. Analyst creates single evidence item passing "investigation": "INV######" (no integer PK!)
        self.client.force_authenticate(user=self.analyst_user)
        ev_payload = {
            "investigation": inv_code,
            "evidence_type": "ATOMIC",
            "summary": "Spear-phishing attachment delivered",
            "affected_asset": "MAIL-LUTHADEL-01",
        }
        ev_res = self.client.post("/api/evidence/", ev_payload, format="json")
        self.assertEqual(ev_res.status_code, 201)
        self.assertEqual(ev_res.json()["investigation_id"], inv_code)

        # 6. Bulk evidence ingestion referencing investigation by string code
        bulk_payload = {
            "investigation": inv_code,
            "items": [
                {
                    "evidence_type": "ATOMIC",
                    "summary": "Mimikatz LSASS dump",
                    "affected_asset": "WRK-INQUISITOR-03",
                },
                {
                    "evidence_type": "SEARCH",
                    "summary": "18.4GB exfiltration of Atium manifests",
                    "affected_asset": "DB-CANTON-RESOURCE",
                    "is_key_evidence": True,
                },
            ],
        }
        bulk_res = self.client.post("/api/evidence/bulk_create/", bulk_payload, format="json")
        self.assertEqual(bulk_res.status_code, 201)
        self.assertEqual(bulk_res.json()["count"], 2)

        # Bulk evidence directly on the investigation URL using INV######
        bulk_sub = self.client.post(
            f"/api/investigations/{inv_code}/bulk-evidence/",
            [{"evidence_type": "ATOMIC", "summary": "Log purge via wevtutil"}],
            format="json",
        )
        self.assertEqual(bulk_sub.status_code, 201)
        self.assertEqual(bulk_sub.json()["count"], 1)

        # Verify all 4 evidence items appear on the investigation timeline
        inv_verify = self.client.get(f"/api/investigations/{inv_code}/").json()
        self.assertEqual(len(inv_verify["timeline_events"]), 4)

        # 7. Query evidence list filtered by ?investigation=INV######
        ev_list = self.client.get(f"/api/evidence/?investigation={inv_code}").json()
        self.assertEqual(len(ev_list), 4)

        # 8. SOC Ingest webhook using "investigation": "INV######"
        soc_res = self.client.post(
            "/api/soc/ingest/",
            {
                "investigation": inv_code,
                "evidence_type": "ATOMIC",
                "summary": "Outbound C2 alert from perimeter firewall",
                "affected_asset": "GW-PERIMETER-01",
            },
            format="json",
        )
        self.assertEqual(soc_res.status_code, 201)


