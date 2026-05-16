from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Order

PLATFORM_FEE_PERCENT = 10
PLATFORM_FEE_RATE = Decimal("0.10")


def quantize_rub(amount: Decimal) -> Decimal:
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def resolve_executor_price(order: Order) -> Decimal | None:
    """Цена исполнителя: из заказа или из активного предложения исполнителя."""
    if order.price is not None:
        return order.price
    if not order.executor_id:
        return None
    from .models import ExecutorServiceOffer

    offer = (
        ExecutorServiceOffer.objects.filter(
            executor_id=order.executor_id,
            service_type_id=order.service_type_id,
            is_active=True,
        )
        .order_by("-updated_at")
        .first()
    )
    if offer:
        return offer.fixed_price
    return None


def ensure_order_price(order: Order) -> Decimal | None:
    """Сохраняет цену в заказе, если исполнитель назначен, а price пустой."""
    resolved = resolve_executor_price(order)
    if resolved is not None and order.price is None:
        order.price = resolved
        order.save(update_fields=["price", "updated_at"])
    return resolved


def customer_pricing_from_executor_price(executor_price: Decimal | None) -> dict | None:
    """
    Цена исполнителя + сервисный сбор платформы (10%) = сумма к оплате заказчиком.
    """
    if executor_price is None:
        return None
    fee = quantize_rub(Decimal(executor_price) * PLATFORM_FEE_RATE)
    total = quantize_rub(Decimal(executor_price) + fee)
    return {
        "executor_price": str(quantize_rub(Decimal(executor_price))),
        "platform_fee": str(fee),
        "platform_fee_percent": PLATFORM_FEE_PERCENT,
        "customer_total": str(total),
    }
