from __future__ import annotations

from django.db.models import Q
from rest_framework import serializers

from .models import (
    BurialSubscription,
    CareSubscription,
    ChatMessage,
    Donation,
    ExecutorServiceOffer,
    Notification,
    Order,
    OrderPhoto,
    OrderReview,
    ServiceType,
)


class ServiceTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceType
        fields = "__all__"


class OrderPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderPhoto
        fields = ("id", "kind", "image", "uploaded_by", "created_at")
        read_only_fields = ("uploaded_by", "created_at")


class OrderReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderReview
        fields = ("rating", "comment", "created_at")
        read_only_fields = ("created_at",)


class OrderSerializer(serializers.ModelSerializer):
    photos = OrderPhotoSerializer(many=True, read_only=True)
    review = OrderReviewSerializer(read_only=True)
    service_type_name = serializers.CharField(source="service_type.name", read_only=True)
    burial_label = serializers.CharField(source="burial.grave_number", read_only=True)
    power_of_attorney = serializers.FileField(source="power_of_attorney.file", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    executor_name = serializers.CharField(source="executor.username", read_only=True)
    executor_bio = serializers.CharField(source="executor.profile.bio", read_only=True)
    customer_order_number = serializers.SerializerMethodField()

    def get_customer_order_number(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        if request.user.profile.role != "customer":
            return None
        if obj.customer_id != request.user.id:
            return None
        return (
            Order.objects.filter(customer_id=obj.customer_id)
            .filter(
                Q(created_at__lt=obj.created_at)
                | Q(created_at=obj.created_at, id__lte=obj.id)
            )
            .count()
        )

    class Meta:
        model = Order
        fields = (
            "id",
            "customer",
            "executor",
            "executor_name",
            "executor_bio",
            "customer_order_number",
            "burial",
            "burial_label",
            "service_type",
            "service_type_name",
            "status",
            "status_label",
            "description",
            "scheduled_at",
            "price",
            "created_at",
            "updated_at",
            "photos",
            "review",
            "power_of_attorney",
        )
        read_only_fields = ("customer", "created_at", "updated_at")


class ChatMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source="sender.username", read_only=True)

    class Meta:
        model = ChatMessage
        fields = ("id", "order", "sender", "sender_name", "message", "created_at", "is_read")
        read_only_fields = ("sender", "created_at")


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = "__all__"
        read_only_fields = ("user", "created_at", "sent_at")


class BurialSubscriptionSerializer(serializers.ModelSerializer):
    burial_label = serializers.CharField(source="burial.grave_number", read_only=True)
    cemetery_name = serializers.CharField(source="burial.cemetery.name", read_only=True)
    person_name = serializers.SerializerMethodField()

    def get_person_name(self, obj):
        person = obj.burial.people.order_by("id").first()
        if person and person.person_name:
            return person.person_name
        if obj.burial.inscription:
            return obj.burial.inscription
        return "Без подписи"

    class Meta:
        model = BurialSubscription
        fields = ("id", "burial", "burial_label", "cemetery_name", "person_name", "created_at")
        read_only_fields = ("created_at",)


class DonationSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Donation
        fields = (
            "id",
            "donor",
            "cemetery",
            "burial",
            "amount",
            "currency",
            "status",
            "status_label",
            "external_payment_id",
            "created_at",
        )
        read_only_fields = ("donor", "created_at")


class CareSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CareSubscription
        fields = "__all__"
        read_only_fields = ("customer", "created_at")


class ExecutorServiceOfferSerializer(serializers.ModelSerializer):
    executor_name = serializers.CharField(source="executor.username", read_only=True)
    executor_display_name = serializers.CharField(source="executor.profile.display_name", read_only=True)
    executor_bio = serializers.CharField(source="executor.profile.bio", read_only=True)
    service_type_name = serializers.CharField(source="service_type.name", read_only=True)

    class Meta:
        model = ExecutorServiceOffer
        fields = (
            "id",
            "executor",
            "executor_name",
            "executor_display_name",
            "executor_bio",
            "service_type",
            "service_type_name",
            "fixed_price",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("executor", "created_at", "updated_at")
