"""Все вьюхи проекта: HTML-страницы и REST API.

Слой намеренно тонкий: вся бизнес-логика — в `services.py`,
фильтрация — в `filters.py`, сериализация — в `serializers.py`.
"""
from __future__ import annotations

import json

from django.conf import settings
from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .filters import BurialFilter, BurialPersonFilter, CemeteryFilter
from .models import Burial, BurialPerson, Cemetery
from .serializers import (
    BurialPersonSerializer,
    BurialSerializer,
    CemeteryMarkerSerializer,
    CemeterySerializer,
)


APP_TITLE = "Онлайн-кладбище"


# ===========================================================================
# REST API
# ===========================================================================
class CemeteryViewSet(viewsets.ReadOnlyModelViewSet):
    """Кладбища: список, детальная карточка и связанные захоронения."""

    queryset = Cemetery.objects.all()
    serializer_class = CemeterySerializer
    filterset_class = CemeteryFilter
    search_fields = ("name",)
    ordering_fields = ("name", "burials_total", "people_total")
    ordering = ("name",)

    @action(detail=True, methods=["get"], url_path="burials")
    def burials(self, request, pk=None):
        """Захоронения внутри кладбища с фильтрами FIO и участка."""
        cemetery = self.get_object()
        fio = request.query_params.get("fio")
        sector = request.query_params.get("sector")
        limit = int(request.query_params.get("limit") or 200)

        items = services.search_person_hits(
            fio=fio,
            cemetery_id=cemetery.id,
            sector=sector,
            limit=limit,
            max_limit=2000,
        )
        total = services.count_person_hits(cemetery_id=cemetery.id, fio=fio, sector=sector)
        return Response({"items": items, "total": total})

    @action(detail=False, methods=["get"], url_path="markers")
    def markers(self, request):
        """Маркеры для карты — только кладбища с известными координатами."""
        qs = Cemetery.objects.filter(latitude__isnull=False, longitude__isnull=False)
        serializer = CemeteryMarkerSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="geocode")
    def geocode(self, request):
        """Запуск геокодинга для кладбищ без координат."""
        limit = request.data.get("limit") or request.query_params.get("limit")
        try:
            limit = int(limit) if limit not in (None, "") else None
        except (TypeError, ValueError):
            limit = None
        report = services.geocode_missing_cemeteries(limit=limit)
        return Response(report.to_dict())


class BurialViewSet(viewsets.ReadOnlyModelViewSet):
    """Захоронения: detail и публичный поиск по людям."""

    queryset = Burial.objects.select_related("cemetery").prefetch_related("people")
    serializer_class = BurialSerializer
    filterset_class = BurialFilter
    ordering_fields = ("id",)
    ordering = ("-id",)

    def get_queryset(self) -> QuerySet[Burial]:
        return super().get_queryset()

    @action(detail=False, methods=["get"], url_path="search")
    def search(self, request):
        """Плоский поиск по людям в захоронениях (для UI таблицы)."""
        params = request.query_params
        cemetery_id = params.get("cemetery_id")
        try:
            cemetery_id_int = int(cemetery_id) if cemetery_id else None
        except (TypeError, ValueError):
            cemetery_id_int = None

        items = services.search_person_hits(
            fio=params.get("fio"),
            cemetery_id=cemetery_id_int,
            cemetery_name=params.get("cemetery"),
            sector=params.get("sector"),
            limit=int(params.get("limit") or 100),
            max_limit=500,
        )
        return Response(items)

    @action(detail=True, methods=["get"], url_path="point")
    def point(self, request, pk=None):
        """Точка на карте конкретного захоронения (lat/lon)."""
        burial = self.get_object()
        point = burial.center_point
        if point is None:
            return Response({}, status=status.HTTP_200_OK)
        lat, lon = point
        return Response({"lat": lat, "lon": lon})


class BurialPersonViewSet(viewsets.ReadOnlyModelViewSet):
    """Люди: альтернативный точечный фильтруемый эндпоинт."""

    queryset = BurialPerson.objects.select_related("burial", "burial__cemetery")
    serializer_class = BurialPersonSerializer
    filterset_class = BurialPersonFilter
    search_fields = ("person_name",)
    ordering_fields = ("id", "birth_year", "death_year")
    ordering = ("-burial_id", "id")


# ---------------------------------------------------------------------------
# External proxy
# ---------------------------------------------------------------------------
class DGisSearchView(APIView):
    """Прокси для catalog.api.2gis.com (для проверки/кнопки на карте)."""

    permission_classes = [AllowAny]

    def get(self, request):
        query = request.query_params.get("q", "")
        code, payload = services.call_2gis_search(query)
        return Response(payload, status=code)


class MosRuPingView(APIView):
    """Проверка доступности набора 64023 на data.mos.ru."""

    permission_classes = [AllowAny]

    def get(self, request):
        code, payload = services.call_mosru_dataset()
        return Response(payload, status=code)


# ===========================================================================
# HTML pages (Server-side rendered)
# ===========================================================================
class IndexView(TemplateView):
    template_name = "index.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = APP_TITLE
        ctx["cemeteries"] = Cemetery.objects.all()
        return ctx


class MapView(TemplateView):
    template_name = "map.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        markers_qs = Cemetery.objects.filter(latitude__isnull=False, longitude__isnull=False)
        markers = [
            {"id": row.id, "name": row.name, "lat": row.latitude, "lon": row.longitude}
            for row in markers_qs
        ]

        focus_point = None
        burial_id = self.request.GET.get("burial_id")
        if burial_id and str(burial_id).isdigit():
            burial = Burial.objects.filter(id=int(burial_id)).first()
            if burial:
                point = burial.center_point
                if point is not None:
                    focus_point = {
                        "lat": point[0],
                        "lon": point[1],
                        "label": services.normalize_inscription_preview(burial.inscription),
                    }

        ctx.update(
            {
                "title": f"{APP_TITLE} — Карта",
                "dgis_api_key": settings.DGIS_API_KEY or settings.DGIS_FALLBACK_KEY,
                "markers_json": json.dumps(markers, ensure_ascii=False),
                "focus_point_json": json.dumps(focus_point, ensure_ascii=False),
            }
        )
        return ctx


class CemeteryDetailView(TemplateView):
    template_name = "cemetery.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        cemetery_id = int(kwargs["cemetery_id"])
        cemetery = Cemetery.objects.filter(id=cemetery_id).first()
        ctx.update(
            {
                "title": f"{APP_TITLE} — Кладбище",
                "cemetery": cemetery,
                "cemetery_id": cemetery_id,
            }
        )
        return ctx
