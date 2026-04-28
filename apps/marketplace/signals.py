from django.db.models.signals import post_migrate
from django.dispatch import receiver

from .models import ServiceCode, ServiceType


@receiver(post_migrate)
def seed_service_types(sender, **kwargs):
    if getattr(sender, "label", None) != "marketplace":
        return
    defaults = [
        (ServiceCode.CLEANING, "Уборка участка"),
        (ServiceCode.FENCE_PAINTING, "Покраска ограждений"),
        (ServiceCode.INSPECTION, "Проверка состояния"),
        (ServiceCode.RADONITSA_REMOTE, "Дистанционная Радоница"),
    ]
    for code, name in defaults:
        ServiceType.objects.get_or_create(code=code, defaults={"name": name})
