from django.apps import AppConfig


class InvestigationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'investigations'
    verbose_name = 'Investigations'

    def ready(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()

        def _user_display_name_with_username_and_full_name(self) -> str:
            full_name = f"{self.first_name} {self.last_name}".strip()
            if not full_name and hasattr(self, 'profile') and getattr(self.profile, 'preferred_display_name', None):
                full_name = self.profile.preferred_display_name.strip()
            if full_name:
                return f"{self.username} ({full_name})"
            return self.username

        User.__str__ = _user_display_name_with_username_and_full_name

