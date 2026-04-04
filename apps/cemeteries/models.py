"""Доменные модели проекта Online Cemetery.

Структура полностью повторяет открытые данные mos.ru, но приведена
к чистым Django-конвенциям: связи через ForeignKey, geoData в JSONField,
HasTombstone — BooleanField (nullable), числовые идентификаторы — BigIntegerField.
"""
from __future__ import annotations

import re
from typing import Optional

from django.db import models


# ---------------------------------------------------------------------------
# Cemetery
# ---------------------------------------------------------------------------
class Cemetery(models.Model):
    """Кладбище. Агрегированная статистика + точка на карте."""

    name = models.CharField(
        verbose_name="Название",
        max_length=255,
        unique=True,
    )

    burials_signed = models.IntegerField(
        verbose_name="Подписанных захоронений", null=True, blank=True
    )
    burials_unsigned = models.IntegerField(
        verbose_name="Неподписанных захоронений", null=True, blank=True
    )
    burials_total = models.IntegerField(
        verbose_name="Всего захоронений", null=True, blank=True
    )

    people_signed = models.IntegerField(
        verbose_name="Подписанных людей", null=True, blank=True
    )
    people_unsigned = models.IntegerField(
        verbose_name="Неподписанных людей", null=True, blank=True
    )
    people_total = models.IntegerField(
        verbose_name="Всего людей", null=True, blank=True
    )

    latitude = models.FloatField(
        verbose_name="Широта", null=True, blank=True
    )
    longitude = models.FloatField(
        verbose_name="Долгота", null=True, blank=True
    )

    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    class Meta:
        verbose_name = "Кладбище"
        verbose_name_plural = "Кладбища"
        ordering = ("name",)
        indexes = [
            models.Index(fields=["name"], name="cem_name_idx"),
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def has_coordinates(self) -> bool:
        return self.latitude is not None and self.longitude is not None


# ---------------------------------------------------------------------------
# Burial
# ---------------------------------------------------------------------------
class Burial(models.Model):
    """Захоронение (одна могила). Может содержать одного или нескольких людей."""

    cemetery = models.ForeignKey(
        Cemetery,
        verbose_name="Кладбище",
        on_delete=models.PROTECT,
        related_name="burials",
    )

    grave_number = models.CharField(
        verbose_name="Номер участка",
        max_length=128,
        blank=True,
        db_index=True,
    )
    has_tombstone = models.BooleanField(
        verbose_name="Памятник установлен",
        null=True,
        blank=True,
    )
    inscription = models.TextField(
        verbose_name="Надпись на памятнике",
        blank=True,
    )
    global_id = models.BigIntegerField(
        verbose_name="Глобальный ID (mos.ru)",
        null=True,
        blank=True,
        unique=True,
    )

    geo_data = models.JSONField(
        verbose_name="Геометрия захоронения",
        null=True,
        blank=True,
        help_text="GeoJSON-структура: тип геометрии и координаты (Point/Polygon/MultiPolygon).",
    )
    geo_data_center = models.JSONField(
        verbose_name="Центральная точка",
        null=True,
        blank=True,
        help_text="GeoJSON Point с центром для отображения маркера на карте.",
    )

    created_at = models.DateTimeField("Создано", auto_now_add=True)

    class Meta:
        verbose_name = "Захоронение"
        verbose_name_plural = "Захоронения"
        ordering = ("-id",)
        indexes = [
            models.Index(fields=["grave_number"], name="bur_grave_idx"),
            models.Index(fields=["cemetery"], name="bur_cem_idx"),
        ]

    def __str__(self) -> str:
        return f"#{self.pk} · {self.grave_number or '—'}"

    @property
    def center_point(self) -> Optional[tuple[float, float]]:
        """Возвращает (lat, lon) если центр известен."""
        return _extract_lat_lon(self.geo_data_center) or _extract_lat_lon(self.geo_data)


# ---------------------------------------------------------------------------
# BurialPerson
# ---------------------------------------------------------------------------
class BurialPerson(models.Model):
    """Один человек в захоронении (1 захоронение = 1..N людей)."""

    burial = models.ForeignKey(
        Burial,
        verbose_name="Захоронение",
        on_delete=models.CASCADE,
        related_name="people",
    )

    person_name = models.TextField(
        verbose_name="ФИО / подпись",
    )
    birth_date = models.CharField(
        verbose_name="Дата рождения",
        max_length=32,
        blank=True,
        help_text="Сырая строка ДД.ММ.ГГГГ или год — данные из источника не унифицированы.",
    )
    death_date = models.CharField(
        verbose_name="Дата смерти",
        max_length=32,
        blank=True,
    )
    birth_year = models.IntegerField(
        verbose_name="Год рождения", null=True, blank=True, db_index=True
    )
    death_year = models.IntegerField(
        verbose_name="Год смерти", null=True, blank=True, db_index=True
    )

    class Meta:
        verbose_name = "Человек в захоронении"
        verbose_name_plural = "Люди в захоронениях"
        ordering = ("burial_id", "id")
        indexes = [
            models.Index(fields=["burial"], name="bp_burial_idx"),
            models.Index(fields=["birth_year"], name="bp_birth_year_idx"),
            models.Index(fields=["death_year"], name="bp_death_year_idx"),
        ]

    def __str__(self) -> str:
        return self.person_name[:80]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
_NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")


def _extract_lat_lon(geo: object) -> Optional[tuple[float, float]]:
    """Достаёт (lat, lon) из произвольного geo-объекта или строки."""
    if geo is None:
        return None
    coords: object = geo
    if isinstance(geo, dict):
        coords = geo.get("coordinates", geo)
    if isinstance(coords, (list, tuple)):
        flat: list[float] = []

        def _walk(node: object) -> None:
            if isinstance(node, (list, tuple)):
                for child in node:
                    _walk(child)
            elif isinstance(node, (int, float)):
                flat.append(float(node))

        _walk(coords)
        if len(flat) >= 2:
            lon, lat = flat[0], flat[1]
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return (lat, lon)
    if isinstance(geo, str):
        nums = [float(n) for n in _NUMBER_RE.findall(geo)]
        if len(nums) >= 2:
            lon, lat = nums[0], nums[1]
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return (lat, lon)
    return None
