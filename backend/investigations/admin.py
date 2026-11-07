from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils import timezone
from django.utils.html import format_html
from django.urls import reverse

from .models import (
    Customer,
    CustomerContact,
    Investigation,
    UserProfile,
    RelatedIncident,
    ExternalResearch,
    EvidenceItem,
    EvidenceScreenshot,
    EvidencePcap,
    format_user_label,
    get_user_display_name,
)
from .permissions import is_super_admin

User = get_user_model()


class UserLabelForeignKeyMixin:
    """
    Ensures all dropdown selection boxes that reference User in the Django admin
    display both username and first name + last name (e.g. 'jsmith (John Smith)').
    """
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        formfield = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if formfield and hasattr(db_field, 'remote_field') and db_field.remote_field:
            if db_field.remote_field.model == User:
                formfield.label_from_instance = format_user_label
        return formfield


def _super_admin_only_permission(request) -> bool:
    """
    Restricts the Django /admin/ raw database interface strictly to active Super Admin accounts.
    Admin, Analyst, and Executive users cannot make direct database changes here.
    """
    user = getattr(request, 'user', None)
    return bool(
        user
        and user.is_authenticated
        and user.is_active
        and user.is_superuser
        and is_super_admin(user)
    )


admin.site.has_permission = _super_admin_only_permission
admin.site.site_header = "SOC Investigations — Super Admin Database Administration"
admin.site.site_title = "SOC Investigations Super Admin"
admin.site.index_title = "Database Entity Management & SOC Investigations Hierarchy"


# ==============================================================================
# Users & Roles Administration
# ==============================================================================

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = "Application Role Profile"


try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass


@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_role', 'is_active', 'is_superuser')
    search_fields = ('username', 'email', 'first_name', 'last_name')

    @admin.display(description='Role')
    def get_role(self, obj):
        if hasattr(obj, 'profile'):
            return obj.profile.get_role_display()
        return 'Super Admin' if obj.is_superuser else 'Analyst'


@admin.register(UserProfile)
class UserProfileAdmin(UserLabelForeignKeyMixin, admin.ModelAdmin):
    list_display = ('user', 'role', 'job_role', 'preferred_display_name', 'pronouns', 'updated_at')
    list_filter = ('role',)
    search_fields = ('user__username', 'user__email', 'preferred_display_name', 'job_role')


# ==============================================================================
# Customer & Contacts Administration
# ==============================================================================

class CustomerContactInline(admin.TabularInline):
    model = CustomerContact
    extra = 0
    fields = ('name', 'escalation_tier', 'notes')
    show_change_link = True


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'customer_id', 'contact_count_display', 'investigation_count_display', 'created_at')
    search_fields = ('name', 'customer_id')
    inlines = [CustomerContactInline]

    @admin.display(description='Contacts')
    def contact_count_display(self, obj):
        return obj.contacts.count()

    @admin.display(description='Investigations')
    def investigation_count_display(self, obj):
        count = obj.investigations.count()
        if count == 0:
            return "0"
        url = reverse('admin:investigations_investigation_changelist') + f"?customer__id__exact={obj.id}"
        return format_html('<a href="{}"><strong>{} investigation(s)</strong></a>', url, count)


@admin.register(CustomerContact)
class CustomerContactAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'customer_link', 'escalation_tier', 'notes', 'created_at')
    list_filter = ('escalation_tier', 'customer')
    search_fields = ('name', 'customer__name', 'notes')

    @admin.display(description='Customer')
    def customer_link(self, obj):
        if obj.customer:
            url = reverse('admin:investigations_customer_change', args=[obj.customer.id])
            return format_html('<a href="{}">{}</a>', url, obj.customer.name)
        return "-"


# ==============================================================================
# Evidence Attachments & Evidence Items
# ==============================================================================

class EvidenceScreenshotInline(UserLabelForeignKeyMixin, admin.TabularInline):
    model = EvidenceScreenshot
    extra = 0
    fields = ('image', 'caption', 'created_by', 'uploaded_at')
    readonly_fields = ('uploaded_at',)
    show_change_link = True


class EvidencePcapInline(UserLabelForeignKeyMixin, admin.TabularInline):
    model = EvidencePcap
    extra = 0
    fields = ('file', 'description', 'created_by', 'uploaded_at')
    readonly_fields = ('uploaded_at',)
    show_change_link = True


class EvidenceItemInline(UserLabelForeignKeyMixin, admin.StackedInline):
    """
    Inlines evidence items directly inside the parent Investigation object.
    """
    model = EvidenceItem
    extra = 0
    fields = (
        ('summary', 'evidence_type', 'timestamp'),
        ('created_by', 'analyst_name'),
        ('affected_asset', 'affected_user', 'user_created_by_attacker'),
        ('mitre_tactic', 'mitre_technique'),
        ('commands_run', 'malicious_hosts_ips'),
    )
    show_change_link = True
    classes = ('collapse',)


class RelatedIncidentInline(admin.TabularInline):
    """
    Inlines escalated incidents related to this full investigation.
    """
    model = RelatedIncident
    extra = 0
    fields = ('title', 'link', 'analyst_name', 'created_at')
    readonly_fields = ('created_at',)
    show_change_link = True


class ExternalResearchInline(admin.TabularInline):
    """
    Inlines threat intelligence and OSINT research related to this investigation.
    """
    model = ExternalResearch
    extra = 0
    fields = ('link', 'summary', 'analyst_name', 'created_at')
    readonly_fields = ('created_at',)
    show_change_link = True


@admin.register(EvidenceScreenshot)
class EvidenceScreenshotAdmin(UserLabelForeignKeyMixin, admin.ModelAdmin):
    list_display = ('id', 'evidence', 'caption', 'created_by', 'uploaded_at')
    list_filter = ('created_by',)
    search_fields = ('caption', 'analyst_name', 'evidence__summary')
    readonly_fields = ('uploaded_at',)


@admin.register(EvidencePcap)
class EvidencePcapAdmin(UserLabelForeignKeyMixin, admin.ModelAdmin):
    list_display = ('id', 'evidence', 'description', 'created_by', 'uploaded_at')
    list_filter = ('created_by',)
    search_fields = ('description', 'analyst_name', 'evidence__summary')
    readonly_fields = ('uploaded_at',)


@admin.register(EvidenceItem)
class EvidenceItemAdmin(UserLabelForeignKeyMixin, admin.ModelAdmin):
    list_display = (
        'id',
        'investigation_link',
        'customer_name',
        'summary_preview',
        'evidence_type',
        'timestamp',
        'created_by_display',
        'attachments_display',
    )
    list_filter = (
        'evidence_type',
        'investigation__customer',
        'investigation',
        'created_by',
    )
    search_fields = (
        'summary',
        'affected_asset',
        'affected_user',
        'investigation__title',
        'investigation__investigation_id',
        'investigation__customer__name',
        'commands_run',
        'malicious_hosts_ips',
    )
    inlines = [EvidenceScreenshotInline, EvidencePcapInline]
    actions = ('action_set_atomic', 'action_set_search')

    @admin.display(description='Investigation')
    def investigation_link(self, obj):
        if obj.investigation:
            url = reverse('admin:investigations_investigation_change', args=[obj.investigation.id])
            return format_html('<a href="{}"><strong>{}</strong></a>', url, obj.investigation.title or f"Investigation #{obj.investigation.id}")
        return "-"

    @admin.display(description='Customer')
    def customer_name(self, obj):
        if obj.investigation and obj.investigation.customer:
            return obj.investigation.customer.name
        return "-"

    @admin.display(description='Summary')
    def summary_preview(self, obj):
        text = obj.summary or ""
        return (text[:90] + "...") if len(text) > 90 else text

    @admin.display(description='Added / Created By')
    def created_by_display(self, obj):
        if obj.created_by:
            return format_user_label(obj.created_by)
        return obj.analyst_name or "-"

    @admin.display(description='Attachments')
    def attachments_display(self, obj):
        screenshots = obj.screenshots.count()
        pcaps = obj.pcaps.count()
        badges = []
        if screenshots > 0:
            badges.append(f"{screenshots} screenshot(s)")
        if pcaps > 0:
            badges.append(f"{pcaps} PCAP(s)")
        return ", ".join(badges) if badges else "None"

    # Bulk Mass Actions for Evidence Items
    @admin.action(description="Set Evidence Type: Atomic Event")
    def action_set_atomic(self, request, queryset):
        count = queryset.update(evidence_type=EvidenceItem.EVIDENCE_TYPE_ATOMIC)
        self.message_user(request, f"Updated {count} evidence item(s) to Atomic Event.")

    @admin.action(description="Set Evidence Type: Search Result Pattern")
    def action_set_search(self, request, queryset):
        count = queryset.update(evidence_type=EvidenceItem.EVIDENCE_TYPE_SEARCH)
        self.message_user(request, f"Updated {count} evidence item(s) to Search Result.")

    def get_actions(self, request):
        actions = super().get_actions(request)
        # Dynamically inject mass assignment actions for active users
        active_users = User.objects.filter(is_active=True).order_by('username')[:20]
        for user in active_users:
            display_name = format_user_label(user)
            action_name = f'mass_assign_evidence_to_user_{user.id}'

            def make_assign_action(target_user, label):
                def assign_action(modeladmin, req, queryset):
                    count = queryset.update(
                        created_by=target_user,
                        analyst_name=get_user_display_name(target_user),
                    )
                    modeladmin.message_user(req, f"Mass-assigned {count} evidence item(s) to {label}.")
                assign_action.__name__ = f'assign_{target_user.id}'
                return assign_action

            actions[action_name] = (
                make_assign_action(user, display_name),
                action_name,
                f"Mass Assign 'Added By' to: {display_name}"
            )
        return actions


# ==============================================================================
# Investigation Administration (Document / Object Level)
# ==============================================================================

@admin.register(Investigation)
class InvestigationAdmin(UserLabelForeignKeyMixin, admin.ModelAdmin):
    list_display = (
        'id',
        'investigation_id',
        'title',
        'customer_link',
        'ticket_id',
        'status_badge',
        'lead_analyst_display',
        'evidence_count_display',
        'is_locked',
        'created_at',
    )
    list_filter = (
        'status',
        'is_locked',
        'customer',
        'lead_analyst_user',
    )
    search_fields = (
        'investigation_id',
        'title',
        'ticket_id',
        'customer__name',
        'customer__customer_id',
        'summary',
        'action_plan',
    )
    fieldsets = (
        ('Investigation Overview', {
            'fields': (
                ('investigation_id', 'title'),
                'customer',
                ('ticket_id', 'ticket_link'),
                ('status', 'is_locked'),
                ('locked_by', 'locked_at'),
                ('lead_analyst_user', 'lead_analyst'),
            )
        }),
        ('Executive Brief & Key Indicators', {
            'fields': (
                'summary',
                'action_plan',
                'key_assets_affected',
                'key_users_affected',
                'key_malicious_indicators',
                'key_customer_contacts',
            )
        }),
        ('Embedded Timeline Document (JSON Events)', {
            'classes': ('collapse',),
            'fields': ('timeline_events',),
            'description': 'Document-style embedded event timeline synchronized with evidence records.',
        }),
        ('Storage Artifacts & Research', {
            'classes': ('collapse',),
            'fields': ('artifact_folder', 'external_research_link', 'external_research_summary'),
        }),
    )
    inlines = [
        EvidenceItemInline,
        RelatedIncidentInline,
        ExternalResearchInline,
    ]
    actions = (
        'action_lock_investigations',
        'action_unlock_investigations',
        'action_status_triage',
        'action_status_investigating',
        'action_status_awaiting_customer',
        'action_status_contained',
        'action_status_closed',
    )

    @admin.display(description='Customer')
    def customer_link(self, obj):
        if obj.customer:
            url = reverse('admin:investigations_customer_change', args=[obj.customer.id])
            return format_html('<a href="{}">{}</a>', url, obj.customer.name)
        return "-"

    @admin.display(description='Status')
    def status_badge(self, obj):
        color = {
            'OPEN': '#0096b3',
            'INVESTIGATING': '#198754',
            'AWAITING_CUSTOMER': '#0096b3',
            'CONTAINED': '#ffc107',
            'ARCHIVED': '#6c757d',
        }.get(obj.status, '#495057')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 11px;">{}</span>',
            color,
            obj.get_status_display()
        )

    @admin.display(description='Lead Analyst')
    def lead_analyst_display(self, obj):
        if obj.lead_analyst_user:
            return format_user_label(obj.lead_analyst_user)
        return obj.lead_analyst or "-"

    @admin.display(description='Evidence Items')
    def evidence_count_display(self, obj):
        count = obj.evidence_items.count()
        if count == 0:
            return "0"
        url = reverse('admin:investigations_evidenceitem_changelist') + f"?investigation__id__exact={obj.id}"
        return format_html('<a href="{}"><strong>{} item(s)</strong></a>', url, count)

    # Bulk Mass Actions for Investigations
    @admin.action(description="Lock selected investigations (Audit Protection)")
    def action_lock_investigations(self, request, queryset):
        count = queryset.update(
            is_locked=True,
            locked_by=request.user,
            locked_at=timezone.now(),
        )
        self.message_user(request, f"Locked {count} investigation(s) for audit protection.")

    @admin.action(description="Unlock selected investigations")
    def action_unlock_investigations(self, request, queryset):
        count = queryset.update(
            is_locked=False,
            locked_by=None,
            locked_at=None,
        )
        self.message_user(request, f"Unlocked {count} investigation(s).")

    @admin.action(description="Set Status: Triage")
    def action_status_triage(self, request, queryset):
        count = queryset.update(status='OPEN')
        self.message_user(request, f"Updated {count} investigation(s) to 'Triage'.")

    @admin.action(description="Set Status: Investigating")
    def action_status_investigating(self, request, queryset):
        count = queryset.update(status='INVESTIGATING')
        self.message_user(request, f"Updated {count} investigation(s) to 'Investigating'.")

    @admin.action(description="Set Status: Awaiting Customer")
    def action_status_awaiting_customer(self, request, queryset):
        count = queryset.update(status='AWAITING_CUSTOMER')
        self.message_user(request, f"Updated {count} investigation(s) to 'Awaiting Customer'.")

    @admin.action(description="Set Status: Contained")
    def action_status_contained(self, request, queryset):
        count = queryset.update(status='CONTAINED')
        self.message_user(request, f"Updated {count} investigation(s) to 'Contained'.")

    @admin.action(description="Set Status: Closed")
    def action_status_closed(self, request, queryset):
        count = queryset.update(status='ARCHIVED')
        self.message_user(request, f"Updated {count} investigation(s) to 'Closed'.")

    def get_actions(self, request):
        actions = super().get_actions(request)
        # Dynamically inject mass assignment actions for active users
        active_users = User.objects.filter(is_active=True).order_by('username')[:20]
        for user in active_users:
            display_name = format_user_label(user)
            action_name = f'mass_assign_lead_to_{user.id}'

            def make_assign_lead_action(target_user, label):
                def assign_lead(modeladmin, req, queryset):
                    count = queryset.update(
                        lead_analyst_user=target_user,
                        lead_analyst=get_user_display_name(target_user),
                    )
                    modeladmin.message_user(req, f"Mass-assigned {count} investigation(s) to Lead Analyst: {label}.")
                assign_lead.__name__ = f'assign_lead_{target_user.id}'
                return assign_lead

            actions[action_name] = (
                make_assign_lead_action(user, display_name),
                action_name,
                f"Mass Assign Lead Analyst to: {display_name}"
            )
        return actions


# ==============================================================================
# Related Incidents & External Threat Research
# ==============================================================================

@admin.register(RelatedIncident)
class RelatedIncidentAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'investigation_link', 'link', 'analyst_name', 'created_at')
    list_filter = ('investigation',)
    search_fields = ('title', 'link', 'analyst_name', 'investigation__title')

    @admin.display(description='Investigation')
    def investigation_link(self, obj):
        if obj.investigation:
            url = reverse('admin:investigations_investigation_change', args=[obj.investigation.id])
            return format_html('<a href="{}">{}</a>', url, obj.investigation.title or f"#{obj.investigation.id}")
        return "-"


@admin.register(ExternalResearch)
class ExternalResearchAdmin(admin.ModelAdmin):
    list_display = ('id', 'investigation_link', 'link', 'summary_preview', 'analyst_name', 'created_at')
    list_filter = ('investigation',)
    search_fields = ('link', 'summary', 'analyst_name', 'investigation__title')

    @admin.display(description='Investigation')
    def investigation_link(self, obj):
        if obj.investigation:
            url = reverse('admin:investigations_investigation_change', args=[obj.investigation.id])
            return format_html('<a href="{}">{}</a>', url, obj.investigation.title or f"#{obj.investigation.id}")
        return "-"

    @admin.display(description='Summary')
    def summary_preview(self, obj):
        text = obj.summary or ""
        return (text[:80] + "...") if len(text) > 80 else text
