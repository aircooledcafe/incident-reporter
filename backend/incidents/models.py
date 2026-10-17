import json
import os
from pathlib import Path
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


def screenshot_upload_path(instance, filename):
    project = instance.evidence.project
    folder = project.get_or_create_artifact_folder()
    safe_name = os.path.basename(filename)
    return f"{folder}/screenshots/evidence_{instance.evidence.id}_{safe_name}"


class Project(models.Model):
    STATUS_CHOICES = [
        ('OPEN', 'Open / Triage'),
        ('INVESTIGATING', 'Investigating'),
        ('CONTAINED', 'Contained'),
        ('ARCHIVED', 'Archived / Closed'),
    ]

    # Overview fields (none are hard DB requirements)
    title = models.CharField(max_length=255, blank=True, default="")
    customer_name = models.CharField(max_length=255, blank=True, default="")
    customer_id = models.CharField(max_length=128, blank=True, default="")
    ticket_id = models.CharField(max_length=128, blank=True, default="")
    ticket_link = models.CharField(max_length=1024, blank=True, default="")
    summary = models.TextField(blank=True, default="")
    key_assets_affected = models.TextField(blank=True, default="")
    key_users_affected = models.TextField(blank=True, default="")
    key_malicious_indicators = models.TextField(blank=True, default="")

    # Primary inline external research fields (plus support for multiple via ExternalResearch model)
    external_research_link = models.CharField(max_length=1024, blank=True, default="")
    external_research_summary = models.TextField(blank=True, default="")

    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='INVESTIGATING')
    lead_analyst = models.CharField(max_length=150, blank=True, default="")
    artifact_folder = models.CharField(max_length=255, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title or f"Incident Project #{self.pk}"

    def get_or_create_artifact_folder(self) -> str:
        """
        Ensures a dedicated folder exists on disk for storing form-submitted evidence
        (screenshots and generated reports) during the investigation phase and for archive purposes.
        """
        if not self.artifact_folder and self.pk:
            slug = slugify(self.title or self.customer_name or "incident")[:40] or "incident"
            self.artifact_folder = f"project_{self.pk}_{slug}"
            Project.objects.filter(pk=self.pk).update(artifact_folder=self.artifact_folder)

        folder_name = self.artifact_folder or "project_unassigned"
        base_path = Path(settings.ARTIFACTS_ROOT) / folder_name
        (base_path / "screenshots").mkdir(parents=True, exist_ok=True)
        (base_path / "reports").mkdir(parents=True, exist_ok=True)
        return folder_name

    @property
    def artifact_folder_absolute_path(self) -> str:
        if not self.artifact_folder:
            return ""
        return str((Path(settings.ARTIFACTS_ROOT) / self.artifact_folder).resolve())

    def sync_archive_manifest(self):
        """
        Writes an up-to-date JSON manifest into the project's artifact directory
        containing only the evidence and metadata submitted via the forms.
        """
        folder_name = self.get_or_create_artifact_folder()
        manifest_path = Path(settings.ARTIFACTS_ROOT) / folder_name / "archive_manifest.json"
        research_list = [
            {
                "id": r.id,
                "link": r.link,
                "summary": r.summary,
                "analyst_name": r.analyst_name,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in self.external_research_items.all()
        ]
        evidence_list = [
            {
                "id": e.id,
                "evidence_type": e.evidence_type,
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                "end_timestamp": e.end_timestamp.isoformat() if e.end_timestamp else None,
                "summary": e.summary,
                "affected_asset": e.affected_asset,
                "affected_user": e.affected_user,
                "user_created_by_attacker": e.user_created_by_attacker,
                "malicious_hosts_ips": e.malicious_hosts_ips,
                "commands_run": e.commands_run,
                "mitre_tactic": e.mitre_tactic,
                "mitre_technique": e.mitre_technique,
                "related_log_link": e.related_log_link,
                "search_result_link": e.search_result_link,
                "search_query_link": e.search_query_link,
                "notes": e.notes,
                "is_key_evidence": e.is_key_evidence,
                "analyst_name": e.analyst_name,
                "screenshots": [s.image.name for s in e.screenshots.all()],
            }
            for e in self.get_timeline_evidence()
        ]
        manifest_data = {
            "project_id": self.pk,
            "title": self.title,
            "customer_name": self.customer_name,
            "customer_id": self.customer_id,
            "ticket_id": self.ticket_id,
            "ticket_link": self.ticket_link,
            "summary": self.summary,
            "key_assets_affected": self.key_assets_affected,
            "key_users_affected": self.key_users_affected,
            "key_malicious_indicators": self.key_malicious_indicators,
            "external_research_link": self.external_research_link,
            "external_research_summary": self.external_research_summary,
            "additional_external_research": research_list,
            "status": self.status,
            "lead_analyst": self.lead_analyst,
            "artifact_folder": folder_name,
            "updated_at": timezone.now().isoformat(),
            "evidence_timeline": evidence_list,
        }
        try:
            manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")
        except OSError:
            pass

    def save(self, *args, **kwargs):
        inline_link = (self.external_research_link or "").strip()
        inline_summary = (self.external_research_summary or "").strip()
        if inline_link or inline_summary:
            self.external_research_link = ""
            self.external_research_summary = ""
        super().save(*args, **kwargs)
        if inline_link or inline_summary:
            ExternalResearch.objects.create(
                project=self,
                link=inline_link,
                summary=inline_summary,
                analyst_name=self.lead_analyst or "Chrisjen Avasarala",
            )
        self.get_or_create_artifact_folder()
        self.sync_archive_manifest()

    def get_timeline_evidence(self):
        """
        Returns all evidence items ordered chronologically by timestamp (Start Timestamp for Search results,
        Timestamp for Atomic events). Items without a timestamp are placed at the end ordered by creation time.
        """
        return self.evidence_items.prefetch_related('screenshots').order_by(
            models.F('timestamp').asc(nulls_last=True),
            'created_at',
        )


class ExternalResearch(models.Model):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='external_research_items',
    )
    link = models.CharField(max_length=1024, blank=True, default="")
    summary = models.TextField(blank=True, default="")
    analyst_name = models.CharField(max_length=150, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Research for Project #{self.project_id}: {self.link}"


class EvidenceItem(models.Model):
    EVIDENCE_TYPE_ATOMIC = 'ATOMIC'
    EVIDENCE_TYPE_SEARCH = 'SEARCH'
    EVIDENCE_TYPE_CHOICES = [
        (EVIDENCE_TYPE_ATOMIC, 'Atomic Event (IDS / Log Event)'),
        (EVIDENCE_TYPE_SEARCH, 'Search Result (Activity Pattern Over Time)'),
    ]

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='evidence_items',
    )
    evidence_type = models.CharField(
        max_length=16,
        choices=EVIDENCE_TYPE_CHOICES,
        default=EVIDENCE_TYPE_ATOMIC,
    )
    analyst_name = models.CharField(max_length=150, blank=True, default="")

    # Timestamps:
    # For ATOMIC events: `timestamp` is the event Timestamp.
    # For SEARCH events: `timestamp` is the Start Timestamp (used for timeline ordering),
    # and `end_timestamp` is the End Timestamp.
    timestamp = models.DateTimeField(null=True, blank=True)
    end_timestamp = models.DateTimeField(null=True, blank=True)

    # Core Investigation Fields (none compulsory)
    summary = models.TextField(blank=True, default="")
    affected_asset = models.CharField(max_length=512, blank=True, default="")
    affected_user = models.CharField(max_length=255, blank=True, default="")
    user_created_by_attacker = models.BooleanField(default=False)
    malicious_hosts_ips = models.TextField(blank=True, default="")
    commands_run = models.TextField(blank=True, default="")

    # Optional MITRE ATT&CK Tactics and Techniques
    mitre_tactic = models.CharField(max_length=255, blank=True, default="")
    mitre_technique = models.CharField(max_length=255, blank=True, default="")

    # Links (Atomic uses related_log_link; Search uses search_result_link and search_query_link)
    related_log_link = models.CharField(max_length=1024, blank=True, default="")
    search_result_link = models.CharField(max_length=1024, blank=True, default="")
    search_query_link = models.CharField(max_length=1024, blank=True, default="")

    # Notes & Report Flag
    notes = models.TextField(blank=True, default="")
    is_key_evidence = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['timestamp', 'created_at']

    def __str__(self):
        return f"[{self.evidence_type}] {self.summary[:50] or 'Evidence #' + str(self.pk)}"


class EvidenceScreenshot(models.Model):
    evidence = models.ForeignKey(
        EvidenceItem,
        on_delete=models.CASCADE,
        related_name='screenshots',
    )
    image = models.FileField(upload_to=screenshot_upload_path)
    caption = models.CharField(max_length=512, blank=True, default="")
    analyst_name = models.CharField(max_length=150, blank=True, default="")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at']

    def delete(self, *args, **kwargs):
        storage = self.image.storage if self.image else None
        name = self.image.name if self.image else None
        super().delete(*args, **kwargs)
        if storage and name and storage.exists(name):
            storage.delete(name)

    def __str__(self):
        return f"Screenshot for Evidence #{self.evidence_id}"
