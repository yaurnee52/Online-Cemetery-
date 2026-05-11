from django.db.models.signals import post_migrate
from django.dispatch import receiver

from .models import ServiceType
from .service_catalog import SERVICE_CATALOG


@receiver(post_migrate)
def seed_service_types(sender, **kwargs):
    if getattr(sender, "label", None) != "marketplace":
        return
    for code, name, description, is_active in SERVICE_CATALOG:
        ServiceType.objects.update_or_create(
            code=code,
            defaults={"name": name, "description": description, "is_active": is_active},
        )
