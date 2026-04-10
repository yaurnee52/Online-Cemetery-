"""Маршрутизация приложения cemeteries (REST + страницы)."""
from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views


router = DefaultRouter()
router.register(r"cemeteries", views.CemeteryViewSet, basename="cemetery")
router.register(r"burials", views.BurialViewSet, basename="burial")
router.register(r"persons", views.BurialPersonViewSet, basename="burial-person")


api_urlpatterns = [
    path("", include(router.urls)),
    path("2gis/search/", views.DGisSearchView.as_view(), name="api-2gis-search"),
    path("mosru/64023/", views.MosRuPingView.as_view(), name="api-mosru-64023"),
]


urlpatterns = [
    # HTML
    path("", views.IndexView.as_view(), name="index"),
    path("map/", views.MapView.as_view(), name="map"),
    path("cemetery/<int:cemetery_id>/", views.CemeteryDetailView.as_view(), name="cemetery-detail"),
    # REST
    path("api/", include(api_urlpatterns)),
]
