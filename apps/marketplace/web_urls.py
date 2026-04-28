from __future__ import annotations

from django.urls import path

from .views import CabinetPageView, MarketplaceServicesPageView, OrderDetailPageView

urlpatterns = [
    path("marketplace/", MarketplaceServicesPageView.as_view(), name="marketplace-services-page"),
    path("cabinet/", CabinetPageView.as_view(), name="cabinet-page"),
    path("orders/<int:order_id>/", OrderDetailPageView.as_view(), name="order-detail-page"),
]
