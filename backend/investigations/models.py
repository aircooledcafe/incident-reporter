import json
import os
import shutil
from pathlib import Path
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.text import slugify


User = get_user_model()


def _user_display_str(self) -> str:
    full_name = f"{self.first_name} {self.last_name}".strip()
    if full_name:
        return f"{self.username} ({full_name})"
    return self.username


# Make user representations throughout selection boxes display username as well as first name and last name
User.__str__ = _user_display_str


def avatar_upload_path(instance, filename):
    safe_name = os.path.basename(filename)
    uid = instance.user_id or "user"
    return f"avatars/user_{uid}_{safe_name}"


class UserProfile(models.Model):
    ROLE_SUPER_ADMIN = 'SUPER_ADMIN'
    ROLE_ADMIN = 'ADMIN'
    ROLE_ANALYST = 'ANALYST'
    ROLE_EXECUTIVE = 'EXECUTIVE'

    ROLE_CHOICES = [
        (ROLE_SUPER_ADMIN, 'Super Admin'),
        (ROLE_ADMIN, 'Admin'),
        (ROLE_ANALYST, 'Analyst'),
        (ROLE_EXECUTIVE, 'Executive'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    role = models.CharField(
        max_length=24,
        choices=ROLE_CHOICES,
        default=ROLE_ANALYST,
    )
    preferred_display_name = models.CharField(max_length=150, blank=True, default="")
    job_role = models.CharField(max_length=120, blank=True, default="")
    pronouns = models.CharField(max_length=64, blank=True, default="")
    avatar = models.FileField(upload_to=avatar_upload_path, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['user__username']

    def delete_avatar_file(self):
        if self.avatar:
            storage = self.avatar.storage
            name = self.avatar.name
            self.avatar = None
            if storage and name and storage.exists(name):
                storage.delete(name)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"


def sync_user_flags_for_role(user, role: str) -> None:
    """
    Synchronizes Django's built-in `is_superuser` and `is_staff` flags with the application role.
    Only SUPER_ADMIN receives `is_staff=True` and `is_superuser=True` (granting Django /admin/ DB access).
    ADMIN, ANALYST, and EXECUTIVE never have raw database admin access.
    """
    should_be_super = role == UserProfile.ROLE_SUPER_ADMIN
    changed_fields = []
    if user.is_superuser != should_be_super:
        user.is_superuser = should_be_super
        changed_fields.append('is_superuser')
    if user.is_staff != should_be_super:
        user.is_staff = should_be_super
        changed_fields.append('is_staff')
    if changed_fields and user.pk:
        type(user).objects.filter(pk=user.pk).update(
            is_superuser=should_be_super,
            is_staff=should_be_super,
        )


def get_or_create_user_profile(user) -> UserProfile:
    profile, created = UserProfile.objects.get_or_create(
        user=user,
        defaults={
            'role': (
                UserProfile.ROLE_SUPER_ADMIN
                if user.is_superuser
                else UserProfile.ROLE_ANALYST
            ),
        },
    )
    if not created and user.is_superuser and profile.role != UserProfile.ROLE_SUPER_ADMIN:
        profile.role = UserProfile.ROLE_SUPER_ADMIN
        profile.save(update_fields=['role', 'updated_at'])
    sync_user_flags_for_role(user, profile.role)
    return profile


def get_user_role(user) -> str:
    if not user or not user.is_authenticated or not user.is_active:
        return ""
    return get_or_create_user_profile(user).role


def get_user_display_name(user) -> str:
    if not user or not user.is_authenticated:
        return ""
    profile = getattr(user, 'profile', None)
    if profile is None and user.pk:
        profile = get_or_create_user_profile(user)
    if profile and (profile.preferred_display_name or "").strip():
        return profile.preferred_display_name.strip()
    full = f"{user.first_name or ''} {user.last_name or ''}".strip()
    return full or user.username


@receiver(post_save, sender=get_user_model())
def _ensure_user_profile_on_save(sender, instance, created, **kwargs):
    if created:
        default_role = (
            UserProfile.ROLE_SUPER_ADMIN
            if instance.is_superuser
            else UserProfile.ROLE_ANALYST
        )
        UserProfile.objects.get_or_create(
            user=instance,
            defaults={'role': default_role},
        )
        sync_user_flags_for_role(instance, default_role)


class Customer(models.Model):
    name = models.CharField(max_length=255, unique=True)
    customer_id = models.CharField(max_length=64, unique=True)  # e.g. "ACME-CORP"
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.customer_id})"


class CustomerContact(models.Model):
    ESCALATION_PRIMARY = 'PRIMARY'
    ESCALATION_SECONDARY = 'SECONDARY'
    ESCALATION_TERTIARY = 'TERTIARY'
    ESCALATION_CHOICES = [
        (ESCALATION_PRIMARY, 'Primary'),
        (ESCALATION_SECONDARY, 'Secondary'),
        (ESCALATION_TERTIARY, 'Tertiary'),
    ]

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='contacts',
    )
    name = models.CharField(max_length=255)
    escalation_tier = models.CharField(
        max_length=16,
        choices=ESCALATION_CHOICES,
        default=ESCALATION_PRIMARY,
    )
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['escalation_tier', 'created_at']

    @property
    def is_primary_escalation(self) -> bool:
        return self.escalation_tier == self.ESCALATION_PRIMARY

    def __str__(self):
        return f"Contact for {self.customer.name}: {self.name} ({self.get_escalation_tier_display()})"


def screenshot_upload_path(instance, filename):
    inv = instance.evidence.investigation
    folder = inv.get_or_create_artifact_folder()
    safe_name = os.path.basename(filename)
    return f"{folder}/screenshots/evidence_{instance.evidence.id}_{safe_name}"


def pcap_upload_path(instance, filename):
    inv = instance.evidence.investigation
    folder = inv.get_or_create_artifact_folder()
    safe_name = os.path.basename(filename)
    return f"{folder}/pcaps/evidence_{instance.evidence.id}_{safe_name}"


class InvestigationManager(models.Manager):
    def create(self, **kwargs):
        customer = kwargs.get('customer')
        cust_name = kwargs.pop('customer_name', None)
        raw_cust_id = kwargs.pop('customer_id', None)

        if not customer:
            if isinstance(raw_cust_id, Customer):
                kwargs['customer'] = raw_cust_id
            elif isinstance(raw_cust_id, int):
                kwargs['customer_id'] = raw_cust_id
            else:
                name = (cust_name or '').strip()
                code = (raw_cust_id or '').strip()
                if not name and not code:
                    name = "Default Organization"
                    code = "DEFAULT-ORG"
                else:
                    name = name or f"Customer {code}"
                    code = code or f"CUST-{name[:20]}"

                customer, _ = Customer.objects.get_or_create(
                    name=name,
                    defaults={'customer_id': code},
                )
                kwargs['customer'] = customer
        return super().create(**kwargs)


def generate_next_investigation_id() -> str:
    """
    Generates a unique human-friendly investigation ID in format INV###### (e.g. INV000001, INV000009).
    Finds the highest existing INV###### number starting from 0 and increments it,
    starting from INV000001.
    """
    import re

    existing_ids = Investigation.objects.filter(
        investigation_id__startswith='INV'
    ).values_list('investigation_id', flat=True)

    max_num = 0
    for iid in existing_ids:
        match = re.search(r'^INV(\d{6})$', str(iid).upper())
        if match:
            num = int(match.group(1))
            # Standard auto-generated IDs start from 0 (e.g. INV000001 to INV099999).
            # Avoid letting custom high IDs (e.g. INV123456) or legacy 100000+ skew the counter.
            if num < 100000 and num > max_num:
                max_num = num

    candidate = f"INV{max_num + 1:06d}"
    while Investigation.objects.filter(investigation_id=candidate).exists():
        max_num += 1
        candidate = f"INV{max_num + 1:06d}"
    return candidate


class Investigation(models.Model):
    STATUS_CHOICES = [
        ('OPEN', 'Triage'),
        ('INVESTIGATING', 'Investigating'),
        ('AWAITING_CUSTOMER', 'Awaiting Customer'),
        ('CONTAINED', 'Contained'),
        ('ARCHIVED', 'Closed'),
    ]

    objects = InvestigationManager()

    investigation_id = models.CharField(
        max_length=32,
        unique=True,
        blank=True,
        help_text="Human-usable ID in format INV123456",
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name='investigations',
    )
    title = models.CharField(max_length=255, blank=True, default="")
    ticket_id = models.CharField(max_length=128, blank=True, default="")
    ticket_link = models.CharField(max_length=1024, blank=True, default="")
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='INVESTIGATING')

    # Lead analyst selection from tool users
    lead_analyst = models.CharField(max_length=150, blank=True, default="")
    lead_analyst_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='led_investigations',
    )

    summary = models.TextField(blank=True, default="")
    action_plan = models.TextField(blank=True, default="")
    key_customer_contacts = models.TextField(blank=True, default="")
    key_assets_affected = models.TextField(blank=True, default="")
    key_users_affected = models.TextField(blank=True, default="")
    key_malicious_indicators = models.TextField(blank=True, default="")

    external_research_link = models.CharField(max_length=1024, blank=True, default="")
    external_research_summary = models.TextField(blank=True, default="")

    artifact_folder = models.CharField(max_length=255, blank=True, default="")

    # Document-style embedded timeline (JSONB in PostgreSQL / JSON in SQLite)
    # Stored as an array of event objects: [{ id, timestamp, summary, mitre: [...], pcaps: [...], screenshots: [...] }]
    timeline_events = models.JSONField(default=list, blank=True)

    # Read-only investigation lock managed by Admin / Super Admin
    is_locked = models.BooleanField(default=False)
    locked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='locked_investigations',
    )
    locked_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        code = self.investigation_id or f"#{self.pk}"
        return f"[{code}] {self.title or 'Untitled Investigation'}"

    @property
    def customer_name(self) -> str:
        return self.customer.name if self.customer_id and self.customer else ""

    @property
    def customer_code(self) -> str:
        return self.customer.customer_id if self.customer_id and self.customer else ""

    def get_or_create_artifact_folder(self) -> str:
        """
        Ensures a dedicated folder exists on disk for storing form-submitted evidence
        (screenshots, pcaps, generated reports) during the investigation phase and for archive purposes.
        """
        if not self.artifact_folder and self.pk:
            cust_slug = slugify(self.customer.name if self.customer_id and self.customer else "incident")[:25]
            title_slug = slugify(self.title or "investigation")[:30]
            self.artifact_folder = f"investigation_{self.pk}_{cust_slug}_{title_slug}".strip('_')
            Investigation.objects.filter(pk=self.pk).update(artifact_folder=self.artifact_folder)

        folder_name = self.artifact_folder or "investigation_unassigned"
        base_path = Path(settings.ARTIFACTS_ROOT) / folder_name
        (base_path / "screenshots").mkdir(parents=True, exist_ok=True)
        (base_path / "pcaps").mkdir(parents=True, exist_ok=True)
        (base_path / "reports").mkdir(parents=True, exist_ok=True)
        return folder_name

    @property
    def artifact_folder_absolute_path(self) -> str:
        if not self.artifact_folder:
            return ""
        return str((Path(settings.ARTIFACTS_ROOT) / self.artifact_folder).resolve())

    def get_timeline_evidence(self):
        return (
            self.evidence_items.select_related('created_by')
            .prefetch_related('screenshots__created_by', 'pcaps__created_by')
            .order_by(
                models.F('timestamp').asc(nulls_last=True),
                'created_at',
            )
        )

    def sync_timeline_events(self):
        """
        Serializes the full evidence timeline into the investigation's embedded JSON column
        (document model), and updates the archive manifest on disk.
        """
        events = [
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
                "created_by": e.created_by.username if e.created_by_id and e.created_by else None,
                "screenshots": [
                    {
                        "id": s.id,
                        "image": s.image.name,
                        "caption": s.caption,
                        "analyst_name": s.analyst_name,
                    }
                    for s in e.screenshots.all()
                ],
                "pcaps": [
                    {
                        "id": p.id,
                        "file": p.file.name,
                        "description": p.description,
                        "analyst_name": p.analyst_name,
                    }
                    for p in e.pcaps.all()
                ],
            }
            for e in self.get_timeline_evidence()
        ]
        self.timeline_events = events
        if self.pk:
            Investigation.objects.filter(pk=self.pk).update(timeline_events=events)
        self.sync_archive_manifest()

    def sync_archive_manifest(self):
        """
        Writes an up-to-date JSON manifest into the investigation's artifact directory.
        """
        if not self.pk:
            return
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
        related_incidents_list = [
            {
                "id": ri.id,
                "title": ri.title,
                "link": ri.link,
                "analyst_name": ri.analyst_name,
                "created_at": ri.created_at.isoformat() if ri.created_at else None,
            }
            for ri in self.related_incidents.all()
        ]
        contacts_list = [
            {
                "id": c.id,
                "name": c.name,
                "escalation_tier": c.escalation_tier,
                "escalation_tier_display": c.get_escalation_tier_display(),
                "notes": c.notes,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in (self.customer.contacts.all() if self.customer_id and self.customer else [])
        ]
        manifest_data = {
            "investigation_id": self.pk,
            "title": self.title,
            "customer_name": self.customer.name if self.customer_id and self.customer else "",
            "customer_id": self.customer.customer_id if self.customer_id and self.customer else "",
            "ticket_id": self.ticket_id,
            "ticket_link": self.ticket_link,
            "summary": self.summary,
            "action_plan": self.action_plan,
            "key_customer_contacts": self.key_customer_contacts,
            "customer_contacts": contacts_list,
            "related_escalated_incidents": related_incidents_list,
            "key_assets_affected": self.key_assets_affected,
            "key_users_affected": self.key_users_affected,
            "key_malicious_indicators": self.key_malicious_indicators,
            "external_research_link": self.external_research_link,
            "external_research_summary": self.external_research_summary,
            "additional_external_research": research_list,
            "status": self.status,
            "is_locked": self.is_locked,
            "locked_by": self.locked_by.username if self.locked_by_id and self.locked_by else None,
            "locked_at": self.locked_at.isoformat() if self.locked_at else None,
            "lead_analyst": self.lead_analyst,
            "artifact_folder": folder_name,
            "updated_at": timezone.now().isoformat(),
            "evidence_timeline": self.timeline_events,
        }
        try:
            manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")
        except OSError:
            pass

    def save(self, *args, **kwargs):
        if not self.investigation_id:
            self.investigation_id = generate_next_investigation_id()
        else:
            self.investigation_id = str(self.investigation_id).strip().upper()

        if not self.customer_id:
            default_cust, _ = Customer.objects.get_or_create(
                name="Default Organization",
                defaults={"customer_id": "DEFAULT-ORG"},
            )
            self.customer = default_cust

        if self.lead_analyst_user and not self.lead_analyst:
            self.lead_analyst = get_user_display_name(self.lead_analyst_user)

        inline_link = (self.external_research_link or "").strip()
        inline_summary = (self.external_research_summary or "").strip()
        if inline_link or inline_summary:
            self.external_research_link = ""
            self.external_research_summary = ""
        super().save(*args, **kwargs)
        if inline_link or inline_summary:
            ExternalResearch.objects.create(
                investigation=self,
                link=inline_link,
                summary=inline_summary,
                analyst_name=self.lead_analyst or "Analyst",
            )
        self.get_or_create_artifact_folder()
        self.sync_archive_manifest()

    def delete(self, *args, **kwargs):
        folder_name = (self.artifact_folder or "").strip()
        result = super().delete(*args, **kwargs)
        if folder_name:
            artifacts_root = Path(settings.ARTIFACTS_ROOT).resolve()
            target_dir = (artifacts_root / folder_name).resolve()
            if target_dir.parent == artifacts_root and target_dir.exists():
                shutil.rmtree(target_dir, ignore_errors=True)
        return result


# Project alias for backward compatibility
Project = Investigation


class RelatedIncident(models.Model):
    investigation = models.ForeignKey(
        Investigation,
        on_delete=models.CASCADE,
        related_name='related_incidents',
    )
    title = models.CharField(max_length=255)
    link = models.CharField(max_length=1024, blank=True, default="")
    analyst_name = models.CharField(max_length=150, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    @property
    def project(self):
        return self.investigation

    @project.setter
    def project(self, value):
        self.investigation = value

    @property
    def project_id(self):
        return self.investigation_id

    def __str__(self):
        return f"Related Incident for Investigation #{self.investigation_id}: {self.title}"


class ExternalResearch(models.Model):
    investigation = models.ForeignKey(
        Investigation,
        on_delete=models.CASCADE,
        related_name='external_research_items',
    )
    link = models.CharField(max_length=1024, blank=True, default="")
    summary = models.TextField(blank=True, default="")
    analyst_name = models.CharField(max_length=150, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    @property
    def project(self):
        return self.investigation

    @project.setter
    def project(self, value):
        self.investigation = value

    @property
    def project_id(self):
        return self.investigation_id

    def __str__(self):
        return f"Research for Investigation #{self.investigation_id}: {self.link}"


class EvidenceItem(models.Model):
    EVIDENCE_TYPE_ATOMIC = 'ATOMIC'
    EVIDENCE_TYPE_SEARCH = 'SEARCH'
    EVIDENCE_TYPE_CHOICES = [
        (EVIDENCE_TYPE_ATOMIC, 'Atomic Event'),
        (EVIDENCE_TYPE_SEARCH, 'Search Result (Activity Pattern Over Time)'),
    ]

    investigation = models.ForeignKey(
        Investigation,
        on_delete=models.CASCADE,
        related_name='evidence_items',
    )
    evidence_type = models.CharField(
        max_length=16,
        choices=EVIDENCE_TYPE_CHOICES,
        default=EVIDENCE_TYPE_ATOMIC,
    )
    analyst_name = models.CharField(max_length=150, blank=True, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_evidence_items',
    )

    timestamp = models.DateTimeField(null=True, blank=True)
    end_timestamp = models.DateTimeField(null=True, blank=True)

    summary = models.TextField(blank=True, default="")
    affected_asset = models.CharField(max_length=512, blank=True, default="")
    affected_user = models.CharField(max_length=255, blank=True, default="")
    user_created_by_attacker = models.BooleanField(default=False)
    malicious_hosts_ips = models.TextField(blank=True, default="")
    commands_run = models.TextField(blank=True, default="")

    mitre_tactic = models.TextField(blank=True, default="")
    mitre_technique = models.TextField(blank=True, default="")

    related_log_link = models.CharField(max_length=1024, blank=True, default="")
    search_result_link = models.CharField(max_length=1024, blank=True, default="")
    search_query_link = models.CharField(max_length=1024, blank=True, default="")

    notes = models.TextField(blank=True, default="")
    is_key_evidence = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['timestamp', 'created_at']

    @property
    def project(self):
        return self.investigation

    @project.setter
    def project(self, value):
        self.investigation = value

    @property
    def project_id(self):
        return self.investigation_id

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
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_evidence_screenshots',
    )
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


class EvidencePcap(models.Model):
    evidence = models.ForeignKey(
        EvidenceItem,
        on_delete=models.CASCADE,
        related_name='pcaps',
    )
    file = models.FileField(upload_to=pcap_upload_path)
    description = models.CharField(max_length=512, blank=True, default="")
    analyst_name = models.CharField(max_length=150, blank=True, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_evidence_pcaps',
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at']

    def delete(self, *args, **kwargs):
        storage = self.file.storage if self.file else None
        name = self.file.name if self.file else None
        super().delete(*args, **kwargs)
        if storage and name and storage.exists(name):
            storage.delete(name)

    def __str__(self):
        return f"PCAP for Evidence #{self.evidence_id}"


# Signals to keep Investigation.timeline_events in sync with Evidence items
@receiver(post_save, sender=EvidenceItem)
@receiver(post_delete, sender=EvidenceItem)
def _on_evidence_item_changed(sender, instance, **kwargs):
    if instance.investigation_id:
        instance.investigation.sync_timeline_events()


@receiver(post_save, sender=EvidenceScreenshot)
@receiver(post_delete, sender=EvidenceScreenshot)
def _on_screenshot_changed(sender, instance, **kwargs):
    if instance.evidence_id and instance.evidence and instance.evidence.investigation_id:
        instance.evidence.investigation.sync_timeline_events()


@receiver(post_save, sender=EvidencePcap)
@receiver(post_delete, sender=EvidencePcap)
def _on_pcap_changed(sender, instance, **kwargs):
    if instance.evidence_id and instance.evidence and instance.evidence.investigation_id:
        instance.evidence.investigation.sync_timeline_events()
