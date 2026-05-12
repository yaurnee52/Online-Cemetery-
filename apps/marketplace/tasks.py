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
from .holiday_notifications import sync_holiday_notifications_for_all_users
from .services import create_order_from_subscription


@shared_task
def holiday_service_reminders_task():
    return sync_holiday_notifications_for_all_users(days_before=15)


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
    """Напоминание о дне памяти (годовщине) за 15 дней до даты."""
    from .memorial_dates import memorial_reminder_for_person

    today = timezone.localdate()
    created = 0
    for sub in BurialSubscription.objects.select_related("burial", "user").prefetch_related(
        "burial__people"
    ):
        person = sub.burial.people.order_by("id").first()
        if not person:
            continue
        reminder = memorial_reminder_for_person(person.death_date, person.death_year, today=today)
        if not reminder:
            continue
        exists = Notification.objects.filter(
            user=sub.user,
            type=NotificationType.ANNIVERSARY,
            created_at__date=today,
            payload__burial_id=sub.burial_id,
        ).exists()
        if exists:
            continue
        Notification.objects.create(
            user=sub.user,
            type=NotificationType.ANNIVERSARY,
            title=reminder["label"],
            body=(
                f"{reminder['next_date_display']} · {reminder['when_short']}. "
                f"Захоронение: {sub.burial.grave_number or 'участок не указан'}."
            ),
            payload={
                "burial_id": sub.burial_id,
                "memorial_date": reminder["next_date"],
                "days_until": reminder["days_until"],
            },
        )
        created += 1
    return {"created_notifications": created}
