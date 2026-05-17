from __future__ import annotations

from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from django.db.models import Q
from django.utils import timezone
from django.views.generic import TemplateView
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.models import UserRole

from .holidays import get_active_holiday_reminders
from .models import (
    BurialSubscription,
    CareSubscription,
    ChatMessage,
    Donation,
    ExecutorServiceOffer,
    Order,
    OrderPhoto,
    OrderReview,
    OrderPaymentStatus,
    OrderStatus,
    ServiceType,
)
from .serializers import (
    BurialSubscriptionSerializer,
    CareSubscriptionSerializer,
    ChatMessageSerializer,
    DonationSerializer,
    ExecutorServiceOfferSerializer,
    NotificationSerializer,
    OrderPhotoSerializer,
    OrderReviewSerializer,
    OrderSerializer,
    ServiceTypeSerializer,
)
from .services import generate_power_of_attorney, transition_order


class IsAuthenticated(permissions.IsAuthenticated):
    pass


class ServiceTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ServiceType.objects.filter(is_active=True).order_by("name")
    serializer_class = ServiceTypeSerializer
    permission_classes = [permissions.AllowAny]


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        role = getattr(user.profile, "role", UserRole.CUSTOMER)
        visibility_filter = Q(customer=user) | Q(executor=user)
        if role == UserRole.EXECUTOR:
            visibility_filter = visibility_filter | Q(status=OrderStatus.CREATED, executor__isnull=True)
        qs = (
            Order.objects.select_related("customer", "executor", "burial", "service_type", "burial__cemetery")
            .filter(visibility_filter)
            .order_by("-created_at")
        )
        burial_id = self.request.query_params.get("burial")
        if burial_id:
            qs = qs.filter(burial_id=burial_id)
        return qs

    def perform_create(self, serializer):
        if self.request.user.profile.role != UserRole.CUSTOMER:
            raise permissions.PermissionDenied("Создавать заказ может только заказчик.")
        executor = serializer.validated_data.get("executor")
        service_type = serializer.validated_data.get("service_type")
        extra_fields = {"customer": self.request.user}
        if executor:
            if executor.profile.role != UserRole.EXECUTOR:
                raise permissions.PermissionDenied("Назначить можно только пользователя с ролью исполнителя.")
            offer = ExecutorServiceOffer.objects.filter(
                executor=executor,
                service_type=service_type,
                is_active=True,
            ).first()
            if not offer:
                raise permissions.PermissionDenied("У выбранного исполнителя нет активного предложения на эту услугу.")
            extra_fields["price"] = offer.fixed_price
        serializer.save(**extra_fields)

    @action(detail=True, methods=["post"])
    def take(self, request, pk=None):
        order = self.get_object()
        profile = request.user.profile
        if profile.role != UserRole.EXECUTOR:
            return Response({"detail": "Только исполнитель может взять заказ."}, status=403)
        if order.status != OrderStatus.CREATED:
            return Response({"detail": "Взять можно только заказ со статусом 'Создан'."}, status=400)
        if order.executor_id and order.executor_id != request.user.id:
            return Response({"detail": "Заказ уже закреплен за другим исполнителем."}, status=400)
        order.executor = request.user
        update_fields = ["executor", "updated_at"]
        if not order.price:
            offer = ExecutorServiceOffer.objects.filter(
                executor=request.user,
                service_type=order.service_type,
                is_active=True,
            ).first()
            if offer:
                order.price = offer.fixed_price
                update_fields.append("price")
        order.save(update_fields=update_fields)
        try:
            order = transition_order(order, target_status=OrderStatus.IN_PROGRESS, actor_id=request.user.id)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(OrderSerializer(order, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def done(self, request, pk=None):
        order = self.get_object()
        if order.executor_id != request.user.id:
            return Response({"detail": "Только назначенный исполнитель может завершить заказ."}, status=403)
        try:
            order = transition_order(order, target_status=OrderStatus.DONE, actor_id=request.user.id)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(OrderSerializer(order, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        order = self.get_object()
        if order.customer_id != request.user.id:
            return Response({"detail": "Только заказчик может подтвердить заказ."}, status=403)
        try:
            order = transition_order(order, target_status=OrderStatus.CONFIRMED, actor_id=request.user.id)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(OrderSerializer(order, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def add_photo(self, request, pk=None):
        order = self.get_object()
        if order.executor_id != request.user.id:
            return Response({"detail": "Только исполнитель по заказу может добавлять фото."}, status=403)
        serializer = OrderPhotoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(order=order, uploaded_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def review(self, request, pk=None):
        order = self.get_object()
        if order.customer_id != request.user.id:
            return Response({"detail": "Только заказчик может оставить отзыв."}, status=403)
        serializer = OrderReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review, _ = OrderReview.objects.update_or_create(
            order=order,
            defaults=serializer.validated_data,
        )
        return Response(OrderReviewSerializer(review).data)

    @action(detail=True, methods=["post"], url_path="mock-pay")
    def mock_pay(self, request, pk=None):
        """Демо-оплата без платёжного шлюза (только заказчик)."""
        order = self.get_object()
        if order.customer_id != request.user.id:
            return Response({"detail": "Оплатить заказ может только заказчик."}, status=403)
        from .pricing import ensure_order_price, resolve_executor_price

        if resolve_executor_price(order) is None:
            return Response(
                {"detail": "Цена заказа ещё не определена. Дождитесь назначения исполнителя."},
                status=400,
            )
        ensure_order_price(order)
        if order.payment_status == OrderPaymentStatus.PAID:
            return Response({"detail": "Заказ уже оплачен."}, status=400)
        order.payment_status = OrderPaymentStatus.PAID
        order.paid_at = timezone.now()
        order.save(update_fields=["payment_status", "paid_at", "updated_at"])
        return Response(OrderSerializer(order, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def generate_power_of_attorney(self, request, pk=None):
        order = self.get_object()
        if order.customer_id != request.user.id:
            return Response({"detail": "Только заказчик может формировать доверенность."}, status=403)
        try:
            doc = generate_power_of_attorney(order)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response({"ok": True, "file": doc.file.url})


class ChatMessageViewSet(viewsets.ModelViewSet):
    serializer_class = ChatMessageSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        qs = ChatMessage.objects.select_related("order", "sender").filter(
            Q(order__customer=user) | Q(order__executor=user)
        )
        order_id = self.request.query_params.get("order_id")
        if order_id:
            qs = qs.filter(order_id=order_id)
        return qs.order_by("created_at")

    def perform_create(self, serializer):
        order = serializer.validated_data["order"]
        user = self.request.user
        if user.id not in {order.customer_id, order.executor_id}:
            raise permissions.PermissionDenied("Можно писать только в чат своих заказов.")
        serializer.save(sender=user)


class HolidayReminderAPIView(APIView):
    """Публичный список напоминаний об услугах к ближайшим праздникам (для баннера на сайте)."""

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        days_before = request.query_params.get("days_before", "15")
        try:
            days_before_int = max(1, min(60, int(days_before)))
        except (TypeError, ValueError):
            days_before_int = 15
        items = [
            {
                "key": r.key,
                "title": r.title,
                "body": r.body,
                "holiday_date": r.holiday_date.isoformat(),
                "holiday_date_display": r.holiday_date_display,
                "date_context": r.date_context,
                "days_until": r.days_until,
                "service_codes": list(r.service_codes),
                "primary_service_code": r.primary_service_code,
                "marketplace_url": r.marketplace_url,
            }
            for r in get_active_holiday_reminders(days_before=days_before_int)
        ]
        return Response({"items": items})


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.request.user.notifications.order_by("-created_at")

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        n = self.get_object()
        n.is_read = True
        n.sent_at = n.sent_at or timezone.now()
        n.save(update_fields=["is_read", "sent_at"])
        return Response({"ok": True})


class BurialSubscriptionViewSet(viewsets.ModelViewSet):
    serializer_class = BurialSubscriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            BurialSubscription.objects.filter(user=self.request.user)
            .select_related("burial", "burial__cemetery")
            .prefetch_related("burial__people")
            .order_by("-created_at")
        )

    def perform_create(self, serializer):
        if self.request.user.profile.role != UserRole.CUSTOMER:
            raise permissions.PermissionDenied("Избранное доступно только заказчику.")
        serializer.save(user=self.request.user)


class DonationViewSet(viewsets.ModelViewSet):
    serializer_class = DonationSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        return Donation.objects.filter(donor=self.request.user).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(donor=self.request.user)


class CareSubscriptionViewSet(viewsets.ModelViewSet):
    serializer_class = CareSubscriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CareSubscription.objects.filter(customer=self.request.user).order_by("-created_at")

    def perform_create(self, serializer):
        if self.request.user.profile.role != UserRole.CUSTOMER:
            raise permissions.PermissionDenied("Подписки на уход доступны только заказчику.")
        serializer.save(customer=self.request.user)


class ExecutorServiceOfferViewSet(viewsets.ModelViewSet):
    serializer_class = ExecutorServiceOfferSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = ExecutorServiceOffer.objects.select_related("executor", "executor__profile", "service_type")
        service_type_id = self.request.query_params.get("service_type")
        if service_type_id:
            qs = qs.filter(service_type_id=service_type_id)
        if user.profile.role == UserRole.EXECUTOR:
            return qs.filter(executor=user).order_by("service_type__name")
        return qs.filter(is_active=True).order_by("service_type__name", "fixed_price")

    def perform_create(self, serializer):
        if self.request.user.profile.role != UserRole.EXECUTOR:
            raise permissions.PermissionDenied("Создавать предложения услуг может только исполнитель.")
        service_type = serializer.validated_data["service_type"]
        defaults = {
            "fixed_price": serializer.validated_data["fixed_price"],
            "is_active": serializer.validated_data.get("is_active", True),
        }
        offer, _ = ExecutorServiceOffer.objects.update_or_create(
            executor=self.request.user,
            service_type=service_type,
            defaults=defaults,
        )
        serializer.instance = offer

    @action(detail=False, methods=["get"])
    def catalog(self, request):
        User = get_user_model()
        service_type_id = request.query_params.get("service_type")
        executors = User.objects.filter(profile__role=UserRole.EXECUTOR).select_related("profile").order_by("username")
        offers_qs = ExecutorServiceOffer.objects.filter(executor__in=executors, is_active=True).select_related("service_type")
        if service_type_id:
            offers_qs = offers_qs.filter(service_type_id=service_type_id)
        offers_by_executor = {offer.executor_id: offer for offer in offers_qs}
        result = []
        for executor in executors:
            offer = offers_by_executor.get(executor.id)
            result.append(
                {
                    "executor": executor.id,
                    "executor_name": executor.username,
                    "executor_display_name": executor.profile.display_name,
                    "executor_bio": executor.profile.bio,
                    "service_type": offer.service_type_id if offer else None,
                    "service_type_name": offer.service_type.name if offer else None,
                    "fixed_price": str(offer.fixed_price) if offer else None,
                    "is_available": bool(offer),
                }
            )
        return Response(result)


class MarketplaceServicesPageView(TemplateView):
    template_name = "marketplace/services.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and getattr(request.user.profile, "role", None) == UserRole.EXECUTOR:
            return redirect("cabinet-page")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "Маркетплейс услуг — Онлайн-кладбище"
        return ctx


class CabinetPageView(TemplateView):
    template_name = "marketplace/cabinet.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = "Личный кабинет — Онлайн-кладбище"
        ctx["new_burial"] = self.request.GET.get("new_burial", "")
        return ctx


class OrderDetailPageView(TemplateView):
    template_name = "marketplace/order_detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        order_id = int(kwargs["order_id"])
        ctx["title"] = f"Заказ #{order_id} — Онлайн-кладбище"
        ctx["order_id"] = order_id
        return ctx
