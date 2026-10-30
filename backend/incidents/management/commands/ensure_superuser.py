import os
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from incidents.models import (
    UserProfile,
    get_or_create_user_profile,
    sync_user_flags_for_role,
)


class Command(BaseCommand):
    help = (
        "Idempotently creates or promotes an initial Super Admin account when "
        "DJANGO_SUPERUSER_USERNAME and DJANGO_SUPERUSER_PASSWORD environment variables are set."
    )

    def handle(self, *args, **options):
        username = (os.environ.get('DJANGO_SUPERUSER_USERNAME') or '').strip()
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD') or ''
        email = (os.environ.get('DJANGO_SUPERUSER_EMAIL') or '').strip()

        if not username or not password:
            return

        User = get_user_model()
        existing = User.objects.filter(username=username).first()
        if existing:
            profile = get_or_create_user_profile(existing)
            if profile.role != UserProfile.ROLE_SUPER_ADMIN:
                profile.role = UserProfile.ROLE_SUPER_ADMIN
                profile.save(update_fields=['role', 'updated_at'])
            sync_user_flags_for_role(existing, UserProfile.ROLE_SUPER_ADMIN)
            self.stdout.write(
                self.style.SUCCESS(
                    f"[Auth] Super Admin user '{username}' already exists."
                )
            )
            return

        user = User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
        )
        profile = get_or_create_user_profile(user)
        profile.role = UserProfile.ROLE_SUPER_ADMIN
        profile.save(update_fields=['role', 'updated_at'])
        sync_user_flags_for_role(user, UserProfile.ROLE_SUPER_ADMIN)
        self.stdout.write(
            self.style.SUCCESS(
                f"[Auth] Created initial Super Admin account '{username}'."
            )
        )
