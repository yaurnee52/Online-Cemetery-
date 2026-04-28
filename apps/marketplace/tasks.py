from __future__ import annotations

from celery import shared_task
from django.db.models import Q
from django.utils import timezone

from .models import (
    BurialSubscription,
    CareSubscription,
    Notification,
    NotificationType,
)
from .services import create_order_from_subscription


@shared_task
def create_periodic_orders_task():
    now = timezone.now()
    subs = CareSubscription.objects.filter(is_active=True, next_run_at__lte=now)
    created = 0
    for sub in subs:
        create_order_from_subscription(sub)
        created += 1
    return {"created_orders": created}


@shared_task
def burial_reminders_task():
    # Упрощенная реализация: если есть подписка на захоронение — отправляем напоминание раз в день.
    today = timezone.localdate()
    created = 0
    for sub in BurialSubscription.objects.select_related("burial", "user"):
        Notification.objects.create(
            user=sub.user,
            type=NotificationType.CARE_REMINDER,
            title="Напоминание об уходе за захоронением",
            body=f"Проверьте состояние захоронения: {sub.burial.grave_number or 'участок не указан'}",
            payload={"burial_id": sub.burial_id, "date": str(today)},
        )
        created += 1
    return {"created_notifications": created}
