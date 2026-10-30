from django.contrib.auth import get_user_model
from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied

from .models import UserProfile, get_user_role

User = get_user_model()

ROLE_RANK = {
    UserProfile.ROLE_EXECUTIVE: 10,
    UserProfile.ROLE_ANALYST: 20,
    UserProfile.ROLE_ADMIN: 30,
    UserProfile.ROLE_SUPER_ADMIN: 40,
}

LESSER_ROLES_FOR_ADMIN = {
    UserProfile.ROLE_ANALYST,
    UserProfile.ROLE_EXECUTIVE,
}


def is_super_admin(user) -> bool:
    return get_user_role(user) == UserProfile.ROLE_SUPER_ADMIN


def is_admin_or_super(user) -> bool:
    return get_user_role(user) in (
        UserProfile.ROLE_ADMIN,
        UserProfile.ROLE_SUPER_ADMIN,
    )


def can_write_investigations(user) -> bool:
    return get_user_role(user) in (
        UserProfile.ROLE_ANALYST,
        UserProfile.ROLE_ADMIN,
        UserProfile.ROLE_SUPER_ADMIN,
    )


def build_user_permissions_summary(user) -> dict:
    role = get_user_role(user)
    return {
        "can_edit": role in (
            UserProfile.ROLE_ANALYST,
            UserProfile.ROLE_ADMIN,
            UserProfile.ROLE_SUPER_ADMIN,
        ),
        "can_lock_projects": role in (
            UserProfile.ROLE_ADMIN,
            UserProfile.ROLE_SUPER_ADMIN,
        ),
        "can_delete_projects": role in (
            UserProfile.ROLE_ADMIN,
            UserProfile.ROLE_SUPER_ADMIN,
        ),
        "can_manage_users": role in (
            UserProfile.ROLE_ADMIN,
            UserProfile.ROLE_SUPER_ADMIN,
        ),
        "can_manage_admins": role == UserProfile.ROLE_SUPER_ADMIN,
        "can_access_db_admin": role == UserProfile.ROLE_SUPER_ADMIN,
        "can_seed_demo": role == UserProfile.ROLE_SUPER_ADMIN,
    }


def can_actor_modify_user(actor, target_user) -> bool:
    actor_role = get_user_role(actor)
    if not actor_role:
        return False
    target_role = (
        target_user.profile.role
        if hasattr(target_user, 'profile')
        else (
            UserProfile.ROLE_SUPER_ADMIN
            if target_user.is_superuser
            else UserProfile.ROLE_ANALYST
        )
    )
    if actor_role == UserProfile.ROLE_SUPER_ADMIN:
        return True
    if actor_role == UserProfile.ROLE_ADMIN:
        return target_role in LESSER_ROLES_FOR_ADMIN
    return False


def validate_user_management_action(
    actor,
    target_user=None,
    requested_role: str | None = None,
    requested_is_active: bool | None = None,
    is_delete: bool = False,
) -> None:
    actor_role = get_user_role(actor)
    if actor_role not in (UserProfile.ROLE_ADMIN, UserProfile.ROLE_SUPER_ADMIN):
        raise PermissionDenied("Only Admin and Super Admin users can manage accounts.")

    if actor_role == UserProfile.ROLE_ADMIN:
        if requested_role is not None and requested_role not in LESSER_ROLES_FOR_ADMIN:
            raise PermissionDenied(
                "Admins can only create or assign Analyst and Executive roles."
            )
        if target_user is not None:
            if target_user.pk == actor.pk:
                raise PermissionDenied(
                    "Admins cannot modify their own role or delete their own account here; use Profile & Account Settings."
                )
            if not can_actor_modify_user(actor, target_user):
                raise PermissionDenied(
                    "Admins can only manage Analyst and Executive users."
                )
        return

    # Actor is SUPER_ADMIN
    if target_user is not None and target_user.pk == actor.pk:
        if is_delete:
            raise PermissionDenied("You cannot delete your own active Super Admin account.")
        demoting = (
            requested_role is not None
            and requested_role != UserProfile.ROLE_SUPER_ADMIN
        )
        deactivating = requested_is_active is False
        if demoting or deactivating:
            other_active_supers = User.objects.filter(
                is_active=True,
                profile__role=UserProfile.ROLE_SUPER_ADMIN,
            ).exclude(pk=actor.pk)
            if not other_active_supers.exists():
                raise PermissionDenied(
                    "Cannot demote or deactivate the last active Super Admin account."
                )


def assert_project_unlocked(project) -> None:
    if project and project.is_locked:
        raise PermissionDenied(
            "This investigation is locked (read-only). An Admin or Super Admin must unlock it before changes can be made."
        )


class ProjectAccessPermission(permissions.BasePermission):
    """
    - demo_scenarios / seed_demo: SUPER_ADMIN only.
    - Safe methods (GET/HEAD/OPTIONS, including timeline & report exports): all authenticated users.
    - lock / unlock / destroy: ADMIN and SUPER_ADMIN only.
    - create / update / partial_update: ANALYST, ADMIN, and SUPER_ADMIN.
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated or not user.is_active:
            return False

        action_name = getattr(view, 'action', None)
        if action_name in ('seed_demo', 'demo_scenarios'):
            if not is_super_admin(user):
                raise PermissionDenied(
                    "Only Super Admin users can load sample demonstration investigations."
                )
            return True

        if request.method in permissions.SAFE_METHODS:
            return bool(get_user_role(user))

        if action_name in ('destroy', 'lock', 'unlock') or request.method == 'DELETE':
            if not is_admin_or_super(user):
                raise PermissionDenied(
                    "Only Admin and Super Admin users can lock, unlock, or delete investigations."
                )
            return True

        if not can_write_investigations(user):
            raise PermissionDenied(
                "Executive accounts are read-only and cannot create or modify investigations."
            )
        return True


class InvestigationItemPermission(permissions.BasePermission):
    """
    - Safe methods: all authenticated users (Executive, Analyst, Admin, Super Admin).
    - Unsafe methods (create, edit, delete, toggle_key, ingest): Analyst, Admin, Super Admin.
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated or not user.is_active:
            return False

        if request.method in permissions.SAFE_METHODS:
            return bool(get_user_role(user))

        if not can_write_investigations(user):
            raise PermissionDenied(
                "Executive accounts are read-only and cannot create or modify investigation items."
            )
        return True


class UserManagementPermission(permissions.BasePermission):
    """
    Restricts /api/users/ endpoints to ADMIN and SUPER_ADMIN.
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated or not user.is_active:
            return False
        if not is_admin_or_super(user):
            raise PermissionDenied(
                "Only Admin and Super Admin users have access to user management."
            )
        return True
