from django.apps import AppConfig


class CemeteriesConfig(AppConfig):
    """Главное приложение проекта: кладбища, захоронения и люди."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.cemeteries"
    label = "cemeteries"
    verbose_name = "Кладбища и захоронения"
