from django.apps import AppConfig


class InvestigationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'investigations'
    verbose_name = 'Investigations'

    def ready(self):
        from django.contrib.auth import get_user_model
        from .models import format_user_label

        User = get_user_model()
        User.__str__ = format_user_label


