from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.marketplace.holiday_notifications import sync_holiday_notifications_for_all_users


class Command(BaseCommand):
    help = "Создать уведомления заказчикам об услугах к приближающимся праздникам."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days-before",
            type=int,
            default=15,
            help="За сколько дней до праздника показывать напоминание (по умолчанию 15).",
        )

    def handle(self, *args, **options):
        stats = sync_holiday_notifications_for_all_users(days_before=options["days_before"])
        self.stdout.write(
            self.style.SUCCESS(
                f"Готово: пользователей-заказчиков {stats['users']}, создано уведомлений {stats['created']}."
            )
        )
