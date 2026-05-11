from __future__ import annotations

from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserRole(models.TextChoices):
    CUSTOMER = "customer", "Заказчик"
    EXECUTOR = "executor", "Исполнитель"


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    role = models.CharField(max_length=16, choices=UserRole.choices, default=UserRole.CUSTOMER)
    display_name = models.CharField(max_length=255, blank=True)
    last_name = models.CharField(max_length=64, blank=True, verbose_name="Фамилия")
    first_name = models.CharField(max_length=64, blank=True, verbose_name="Имя")
    patronymic = models.CharField(max_length=64, blank=True, verbose_name="Отчество")
    no_patronymic = models.BooleanField(default=False, verbose_name="Нет отчества")
    passport_series = models.CharField(max_length=8, blank=True, verbose_name="Серия паспорта")
    passport_number = models.CharField(max_length=6, blank=True, verbose_name="Номер паспорта")
    poa_city = models.CharField(
        max_length=128,
        blank=True,
        default="г. Москва",
        verbose_name="Город для доверенности",
    )
    phone = models.CharField(max_length=32, blank=True)
    bio = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Профиль пользователя"
        verbose_name_plural = "Профили пользователей"

    def __str__(self) -> str:
        return f"{self.user.username} ({self.role})"

    @property
    def full_name(self) -> str:
        from .identity import build_full_name

        if self.last_name or self.first_name:
            return build_full_name(
                last_name=self.last_name,
                first_name=self.first_name,
                patronymic=self.patronymic,
                no_patronymic=self.no_patronymic,
            )
        return self.display_name or self.user.username

    @property
    def passport_line(self) -> str:
        from .identity import passport_display

        if self.passport_series and self.passport_number:
            return passport_display(self.passport_series, self.passport_number)
        return ""

    def has_identity_for_poa(self) -> bool:
        return bool(
            self.last_name
            and self.first_name
            and self.passport_series
            and self.passport_number
            and (self.no_patronymic or self.patronymic)
        )


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    else:
        UserProfile.objects.get_or_create(user=instance)
