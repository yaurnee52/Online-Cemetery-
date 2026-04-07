"""DRF/django-filter фильтры для ViewSet'ов."""
from __future__ import annotations

import django_filters as df

from .models import Burial, BurialPerson, Cemetery


class CemeteryFilter(df.FilterSet):
    name = df.CharFilter(field_name="name", lookup_expr="icontains")

    class Meta:
        model = Cemetery
        fields = ("name",)


class BurialFilter(df.FilterSet):
    cemetery = df.NumberFilter(field_name="cemetery_id")
    grave_number = df.CharFilter(field_name="grave_number", lookup_expr="icontains")
    has_tombstone = df.BooleanFilter(field_name="has_tombstone")

    class Meta:
        model = Burial
        fields = ("cemetery", "grave_number", "has_tombstone")


class BurialPersonFilter(df.FilterSet):
    fio = df.CharFilter(field_name="person_name", lookup_expr="icontains")
    cemetery = df.NumberFilter(field_name="burial__cemetery_id")
    cemetery_name = df.CharFilter(field_name="burial__cemetery__name", lookup_expr="icontains")
    sector = df.CharFilter(field_name="burial__grave_number", lookup_expr="icontains")
    birth_year = df.NumberFilter(field_name="birth_year")
    birth_year_gte = df.NumberFilter(field_name="birth_year", lookup_expr="gte")
    birth_year_lte = df.NumberFilter(field_name="birth_year", lookup_expr="lte")
    death_year = df.NumberFilter(field_name="death_year")
    death_year_gte = df.NumberFilter(field_name="death_year", lookup_expr="gte")
    death_year_lte = df.NumberFilter(field_name="death_year", lookup_expr="lte")

    class Meta:
        model = BurialPerson
        fields = (
            "fio",
            "cemetery",
            "cemetery_name",
            "sector",
            "birth_year",
            "birth_year_gte",
            "birth_year_lte",
            "death_year",
            "death_year_gte",
            "death_year_lte",
        )
