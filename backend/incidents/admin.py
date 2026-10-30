from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import (
    UserProfile,
    Project,
    RelatedIncident,
    CustomerContact,
    ExternalResearch,
    EvidenceItem,
    EvidenceScreenshot,
)
from .permissions import is_super_admin

User = get_user_model()


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
admin.site.site_header = "Incident Reporter — Super Admin Database Administration"
admin.site.site_title = "Incident Reporter Super Admin"


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

    @admin.display(description='Role')
    def get_role(self, obj):
        if hasattr(obj, 'profile'):
            return obj.profile.get_role_display()
        return 'Super Admin' if obj.is_superuser else 'Analyst'


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'preferred_display_name', 'pronouns', 'updated_at')
    list_filter = ('role',)
    search_fields = ('user__username', 'user__email', 'preferred_display_name')


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'customer_name', 'ticket_id', 'status', 'is_locked', 'lead_analyst', 'created_at')
    list_filter = ('status', 'is_locked')
    search_fields = ('title', 'customer_name', 'customer_id', 'ticket_id')


admin.site.register(RelatedIncident)
admin.site.register(CustomerContact)
admin.site.register(ExternalResearch)
admin.site.register(EvidenceItem)
admin.site.register(EvidenceScreenshot)
