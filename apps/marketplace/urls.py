from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    BurialSubscriptionViewSet,
    CareSubscriptionViewSet,
    ChatMessageViewSet,
    DonationViewSet,
    ExecutorServiceOfferViewSet,
    HolidayReminderAPIView,
    NotificationViewSet,
    OrderViewSet,
    ServiceTypeViewSet,
)

router = DefaultRouter()
router.register("services", ServiceTypeViewSet, basename="service-type")
router.register("orders", OrderViewSet, basename="order")
router.register("chat", ChatMessageViewSet, basename="chat")
router.register("notifications", NotificationViewSet, basename="notification")
router.register("burial-subscriptions", BurialSubscriptionViewSet, basename="burial-subscription")
router.register("donations", DonationViewSet, basename="donation")
router.register("care-subscriptions", CareSubscriptionViewSet, basename="care-subscription")
router.register("executor-offers", ExecutorServiceOfferViewSet, basename="executor-offer")

urlpatterns = [
    path("holiday-reminders/", HolidayReminderAPIView.as_view(), name="holiday-reminders"),
    path("", include(router.urls)),
]
