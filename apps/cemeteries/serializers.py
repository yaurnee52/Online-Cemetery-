"""Сериалайзеры DRF для всех публичных моделей."""
from __future__ import annotations

from rest_framework import serializers

from .models import Burial, BurialPerson, Cemetery


class CemeterySerializer(serializers.ModelSerializer):
    has_coordinates = serializers.BooleanField(read_only=True)

    class Meta:
        model = Cemetery
        fields = (
            "id",
            "name",
            "burials_signed",
            "burials_unsigned",
            "burials_total",
            "people_signed",
            "people_unsigned",
            "people_total",
            "latitude",
            "longitude",
            "has_coordinates",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at", "has_coordinates")


class CemeteryShortSerializer(serializers.ModelSerializer):
    """Лёгкий сериалайзер для выпадающих списков."""

    class Meta:
        model = Cemetery
        fields = ("id", "name")


class CemeteryMarkerSerializer(serializers.ModelSerializer):
    """Маркер для карты."""

    lat = serializers.FloatField(source="latitude")
    lon = serializers.FloatField(source="longitude")

    class Meta:
        model = Cemetery
        fields = ("id", "name", "lat", "lon")


class BurialPersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = BurialPerson
        fields = (
            "id",
            "burial",
            "person_name",
            "birth_date",
            "death_date",
            "birth_year",
            "death_year",
        )


class BurialSerializer(serializers.ModelSerializer):
    cemetery_name = serializers.CharField(source="cemetery.name", read_only=True)
    people = BurialPersonSerializer(many=True, read_only=True)

    class Meta:
        model = Burial
        fields = (
            "id",
            "cemetery",
            "cemetery_name",
            "grave_number",
            "has_tombstone",
            "inscription",
            "global_id",
            "geo_data",
            "geo_data_center",
            "people",
            "created_at",
        )
        read_only_fields = ("created_at",)


class BurialPointSerializer(serializers.Serializer):
    lat = serializers.FloatField()
    lon = serializers.FloatField()
