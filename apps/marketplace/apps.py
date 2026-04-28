from django.apps import AppConfig


class MarketplaceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.marketplace"
    label = "marketplace"
    verbose_name = "Маркетплейс услуг"

    def ready(self):
        from . import signals  # noqa: F401
