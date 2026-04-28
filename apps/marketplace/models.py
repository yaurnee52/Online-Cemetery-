from __future__ import annotations

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.cemeteries.models import Burial, Cemetery


class ServiceCode(models.TextChoices):
    CLEANING = "cleaning", "Уборка участка"
    FENCE_PAINTING = "fence_painting", "Покраска ограждений"
    INSPECTION = "inspection", "Проверка состояния"
    RADONITSA_REMOTE = "radonitsa_remote", "Дистанционная Радоница"


class ServiceType(models.Model):
    code = models.CharField(max_length=32, choices=ServiceCode.choices, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Тип услуги"
        verbose_name_plural = "Типы услуг"

    def __str__(self):
        return self.name


class OrderStatus(models.TextChoices):
    CREATED = "created", "Создан"
    IN_PROGRESS = "in_progress", "В работе"
    DONE = "done", "Завершен"
    CONFIRMED = "confirmed", "Подтвержден"
    CANCELLED = "cancelled", "Отменен"


class Order(models.Model):
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="customer_orders"
    )
    executor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="executor_orders",
    )
    burial = models.ForeignKey(Burial, on_delete=models.PROTECT, related_name="orders")
    service_type = models.ForeignKey(ServiceType, on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(max_length=16, choices=OrderStatus.choices, default=OrderStatus.CREATED)
    description = models.TextField(blank=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        ordering = ("-created_at",)

    def __str__(self):
        return f"Order #{self.id} ({self.get_status_display()})"


class PhotoKind(models.TextChoices):
    BEFORE = "before", "До"
    AFTER = "after", "После"


class OrderPhoto(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="photos")
    kind = models.CharField(max_length=16, choices=PhotoKind.choices)
    image = models.ImageField(upload_to="order_photos/%Y/%m/%d/")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Фото отчета"
        verbose_name_plural = "Фото отчеты"
        ordering = ("-created_at",)


class OrderReview(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="review")
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Отзыв по заказу"
        verbose_name_plural = "Отзывы по заказам"


class PowerOfAttorneyDocument(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="power_of_attorney")
    file = models.FileField(upload_to="documents/power_of_attorney/%Y/%m/%d/")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Доверенность"
        verbose_name_plural = "Доверенности"


class ChatMessage(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages")
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Сообщение чата"
        verbose_name_plural = "Сообщения чата"
        ordering = ("created_at",)


class NotificationType(models.TextChoices):
    ANNIVERSARY = "anniversary", "Годовщина"
    PASCHA = "pascha", "Пасха / Радоница"
    CARE_REMINDER = "care_reminder", "Напоминание об уходе"
    ORDER_EVENT = "order_event", "Событие заказа"


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    type = models.CharField(max_length=32, choices=NotificationType.choices)
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True)
    payload = models.JSONField(default=dict, blank=True)
    is_read = models.BooleanField(default=False)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Уведомление"
        verbose_name_plural = "Уведомления"
        ordering = ("-created_at",)


class BurialSubscription(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="burial_subscriptions")
    burial = models.ForeignKey(Burial, on_delete=models.CASCADE, related_name="subscribers")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Подписка на захоронение"
        verbose_name_plural = "Подписки на захоронения"
        unique_together = ("user", "burial")


class DonationStatus(models.TextChoices):
    PENDING = "pending", "Ожидает оплаты"
    PAID = "paid", "Оплачен"
    FAILED = "failed", "Ошибка оплаты"


class Donation(models.Model):
    donor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="donations"
    )
    cemetery = models.ForeignKey(Cemetery, on_delete=models.SET_NULL, null=True, blank=True, related_name="donations")
    burial = models.ForeignKey(Burial, on_delete=models.SET_NULL, null=True, blank=True, related_name="donations")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=8, default="RUB")
    status = models.CharField(max_length=16, choices=DonationStatus.choices, default=DonationStatus.PENDING)
    external_payment_id = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Пожертвование"
        verbose_name_plural = "Пожертвования"


class SubscriptionPeriod(models.TextChoices):
    MONTHLY = "monthly", "Ежемесячно"
    QUARTERLY = "quarterly", "Ежеквартально"


class CareSubscription(models.Model):
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="care_subscriptions"
    )
    burial = models.ForeignKey(Burial, on_delete=models.CASCADE, related_name="care_subscriptions")
    service_type = models.ForeignKey(ServiceType, on_delete=models.PROTECT, related_name="care_subscriptions")
    period = models.CharField(max_length=16, choices=SubscriptionPeriod.choices, default=SubscriptionPeriod.MONTHLY)
    next_run_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Подписка на уход"
        verbose_name_plural = "Подписки на уход"


class ExecutorServiceOffer(models.Model):
    executor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="service_offers",
    )
    service_type = models.ForeignKey(ServiceType, on_delete=models.CASCADE, related_name="executor_offers")
    fixed_price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Предложение исполнителя"
        verbose_name_plural = "Предложения исполнителей"
        unique_together = ("executor", "service_type")
        ordering = ("service_type__name", "executor__username")

    def __str__(self):
        return f"{self.executor.username}: {self.service_type.name} ({self.fixed_price})"
