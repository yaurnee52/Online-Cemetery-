from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .identity import (
    build_full_name,
    normalize_passport_number,
    normalize_passport_series,
    parse_bool,
)
from .models import UserProfile, UserRole

User = get_user_model()

IDENTITY_FIELDS = (
    "last_name",
    "first_name",
    "patronymic",
    "no_patronymic",
    "passport_series",
    "passport_number",
    "poa_city",
)


def validate_identity_fields(data: dict, *, required: bool = True) -> dict:
    last_name = (data.get("last_name") or "").strip()
    first_name = (data.get("first_name") or "").strip()
    patronymic = (data.get("patronymic") or "").strip()
    no_patronymic = parse_bool(data.get("no_patronymic"))
    passport_series_raw = (data.get("passport_series") or "").strip()
    passport_number_raw = (data.get("passport_number") or "").strip()
    poa_city = (data.get("poa_city") or "г. Москва").strip() or "г. Москва"

    errors = {}
    if required:
        if not last_name:
            errors["last_name"] = "Укажите фамилию."
        if not first_name:
            errors["first_name"] = "Укажите имя."
        if not no_patronymic and not patronymic:
            errors["patronymic"] = "Укажите отчество или отметьте «Нет отчества»."
        if not passport_series_raw:
            errors["passport_series"] = "Укажите серию паспорта."
        if not passport_number_raw:
            errors["passport_number"] = "Укажите номер паспорта."

    passport_series = ""
    passport_number = ""
    if passport_series_raw:
        try:
            passport_series = normalize_passport_series(passport_series_raw)
        except ValueError as exc:
            errors["passport_series"] = str(exc)
    if passport_number_raw:
        try:
            passport_number = normalize_passport_number(passport_number_raw)
        except ValueError as exc:
            errors["passport_number"] = str(exc)

    if errors:
        raise serializers.ValidationError(errors)

    return {
        "last_name": last_name,
        "first_name": first_name,
        "patronymic": patronymic if not no_patronymic else "",
        "no_patronymic": no_patronymic,
        "passport_series": passport_series,
        "passport_number": passport_number,
        "poa_city": poa_city,
        "full_name": build_full_name(
            last_name=last_name,
            first_name=first_name,
            patronymic=patronymic,
            no_patronymic=no_patronymic,
        ),
    }


class RegistrationSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=UserRole.choices, default=UserRole.CUSTOMER)
    display_name = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=64)
    first_name = serializers.CharField(max_length=64)
    patronymic = serializers.CharField(required=False, allow_blank=True, max_length=64)
    no_patronymic = serializers.BooleanField(required=False, default=False)
    passport_series = serializers.CharField(max_length=16)
    passport_number = serializers.CharField(max_length=12)
    poa_city = serializers.CharField(required=False, allow_blank=True, max_length=128)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Пользователь с таким username уже существует.")
        return value

    def validate(self, attrs):
        identity = validate_identity_fields(attrs, required=True)
        attrs["_identity"] = identity
        return attrs

    def create(self, validated_data):
        identity = validated_data.pop("_identity")
        role = validated_data.pop("role", UserRole.CUSTOMER)
        display_name = validated_data.pop("display_name", "") or identity["full_name"]
        phone = validated_data.pop("phone", "")
        validated_data.pop("last_name", None)
        validated_data.pop("first_name", None)
        validated_data.pop("patronymic", None)
        validated_data.pop("no_patronymic", None)
        validated_data.pop("passport_series", None)
        validated_data.pop("passport_number", None)
        validated_data.pop("poa_city", None)
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)
        profile = user.profile
        profile.role = role
        profile.display_name = display_name
        profile.phone = phone
        profile.last_name = identity["last_name"]
        profile.first_name = identity["first_name"]
        profile.patronymic = identity["patronymic"]
        profile.no_patronymic = identity["no_patronymic"]
        profile.passport_series = identity["passport_series"]
        profile.passport_number = identity["passport_number"]
        profile.poa_city = identity["poa_city"]
        profile.save(
            update_fields=[
                "role",
                "display_name",
                "phone",
                "last_name",
                "first_name",
                "patronymic",
                "no_patronymic",
                "passport_series",
                "passport_number",
                "poa_city",
                "updated_at",
            ]
        )
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username")
    email = serializers.EmailField(source="user.email", allow_blank=True, required=False)
    is_staff = serializers.BooleanField(source="user.is_staff", read_only=True)
    full_name = serializers.SerializerMethodField()
    passport_line = serializers.SerializerMethodField()

    def get_full_name(self, obj):
        return obj.full_name

    def get_passport_line(self, obj):
        return obj.passport_line

    class Meta:
        model = UserProfile
        fields = (
            "id",
            "username",
            "email",
            "role",
            "display_name",
            "full_name",
            "last_name",
            "first_name",
            "patronymic",
            "no_patronymic",
            "passport_series",
            "passport_number",
            "passport_line",
            "poa_city",
            "phone",
            "bio",
            "is_staff",
        )
        read_only_fields = ("role", "full_name", "passport_line")

    def validate(self, attrs):
        if self.instance and self.instance.user.is_staff:
            return attrs
        instance_data = {}
        if self.instance:
            instance_data = {
                "last_name": self.instance.last_name,
                "first_name": self.instance.first_name,
                "patronymic": self.instance.patronymic,
                "no_patronymic": self.instance.no_patronymic,
                "passport_series": self.instance.passport_series,
                "passport_number": self.instance.passport_number,
                "poa_city": self.instance.poa_city,
            }
        merged = {**instance_data, **attrs}
        if any(k in attrs for k in IDENTITY_FIELDS):
            identity = validate_identity_fields(merged, required=True)
            for key in IDENTITY_FIELDS:
                if key in identity:
                    attrs[key] = identity[key]
            if not attrs.get("display_name") and identity.get("full_name"):
                attrs["display_name"] = identity["full_name"]
        return attrs

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})
        user = instance.user
        username = user_data.get("username")
        email = user_data.get("email")
        if username and username != user.username:
            if User.objects.filter(username=username).exclude(pk=user.pk).exists():
                raise serializers.ValidationError({"username": "Пользователь с таким username уже существует."})
            user.username = username
        if email is not None:
            user.email = email
        if user_data:
            user.save(update_fields=["username", "email"])
        return super().update(instance, validated_data)


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
