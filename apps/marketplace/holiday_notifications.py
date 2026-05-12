"""Создание персональных уведомлений о праздничных услугах."""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.users.models import UserRole

from .holidays import get_active_holiday_reminders
from .models import Notification


def sync_holiday_notifications_for_all_users(*, days_before: int = 15) -> dict[str, int]:
    """Создаёт уведомления заказчикам, если напоминание ещё не отправлялось."""
    User = get_user_model()
    reminders = get_active_holiday_reminders(days_before=days_before)
    if not reminders:
        return {"users": 0, "created": 0}

    customers = User.objects.filter(profile__role=UserRole.CUSTOMER, is_active=True)
    created = 0
    now = timezone.now()

    for user in customers:
        for reminder in reminders:
            exists = Notification.objects.filter(
                user=user,
                type=reminder.notification_type,
                payload__holiday_key=reminder.key,
            ).exists()
            if exists:
                continue
            when_label = (
                "сегодня" if reminder.days_until == 0 else f"через {reminder.days_until} дн."
            )
            Notification.objects.create(
                user=user,
                type=reminder.notification_type,
                title=f"{reminder.title} — {when_label}",
                body=(
                    f"{reminder.holiday_date_display}. {reminder.date_context}. {reminder.body}"
                ),
                payload={
                    "holiday_key": reminder.key,
                    "holiday_date": reminder.holiday_date.isoformat(),
                    "holiday_date_display": reminder.holiday_date_display,
                    "date_context": reminder.date_context,
                    "days_until": reminder.days_until,
                    "service_codes": list(reminder.service_codes),
                    "primary_service_code": reminder.primary_service_code,
                    "marketplace_url": reminder.marketplace_url,
                },
                scheduled_for=now,
                sent_at=now,
            )
            created += 1

    return {"users": customers.count(), "created": created}
