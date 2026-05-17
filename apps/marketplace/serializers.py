from __future__ import annotations

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
    holiday_timing = serializers.SerializerMethodField()

    def get_holiday_timing(self, obj):
        from .holidays import get_next_holiday_for_service

        return get_next_holiday_for_service(obj.code)

    class Meta:
        model = ServiceType
        fields = ("id", "code", "name", "description", "base_price", "is_active", "holiday_timing")


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
    payment_status_label = serializers.CharField(source="get_payment_status_display", read_only=True)
    executor_name = serializers.CharField(source="executor.username", read_only=True)
    executor_bio = serializers.CharField(source="executor.profile.bio", read_only=True)
    customer_order_number = serializers.SerializerMethodField()
    customer_pricing = serializers.SerializerMethodField()

    def get_customer_order_number(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        profile = getattr(request.user, "profile", None)
        if not profile or profile.role != "customer":
            return None
        if obj.customer_id != request.user.id:
            return None
        return obj.customer_sequence_number()

    def get_customer_pricing(self, obj):
        from apps.users.models import UserRole

        from .pricing import customer_pricing_from_executor_price, ensure_order_price, resolve_executor_price

        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        profile = getattr(request.user, "profile", None)
        if not profile or profile.role != UserRole.CUSTOMER:
            return None
        if obj.customer_id != request.user.id:
            return None
        price = resolve_executor_price(obj)
        if price is not None and obj.price is None:
            ensure_order_price(obj)
        return customer_pricing_from_executor_price(price)

    def to_representation(self, instance):
        from .pricing import resolve_executor_price

        data = super().to_representation(instance)
        resolved = resolve_executor_price(instance)
        if resolved is not None:
            data["price"] = str(resolved)
        return data

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
            "payment_status",
            "payment_status_label",
            "paid_at",
            "customer_pricing",
            "created_at",
            "updated_at",
            "photos",
            "review",
            "power_of_attorney",
        )
        read_only_fields = ("customer", "payment_status", "paid_at", "created_at", "updated_at")


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
    death_date = serializers.SerializerMethodField()
    memorial_info = serializers.SerializerMethodField()
    memorial_reminder = serializers.SerializerMethodField()

    def get_person_name(self, obj):
        person = obj.burial.people.order_by("id").first()
        if person and person.person_name:
            return person.person_name
        if obj.burial.inscription:
            return obj.burial.inscription
        return "Без подписи"

    def get_death_date(self, obj):
        person = obj.burial.people.order_by("id").first()
        if not person:
            return ""
        return person.death_date or (str(person.death_year) if person.death_year else "")

    def _first_person(self, obj):
        return obj.burial.people.order_by("id").first()

    def get_memorial_info(self, obj):
        from .memorial_dates import memorial_info_for_person

        person = self._first_person(obj)
        if not person:
            return None
        return memorial_info_for_person(person.death_date, person.death_year)

    def get_memorial_reminder(self, obj):
        info = self.get_memorial_info(obj)
        if info and info.get("is_reminder_active"):
            return info
        return None

    class Meta:
        model = BurialSubscription
        fields = (
            "id",
            "burial",
            "burial_label",
            "cemetery_name",
            "person_name",
            "death_date",
            "memorial_info",
            "memorial_reminder",
            "created_at",
        )
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
