from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import UserProfile, UserRole

User = get_user_model()


class RegistrationSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=UserRole.choices, default=UserRole.CUSTOMER)
    display_name = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Пользователь с таким username уже существует.")
        return value

    def create(self, validated_data):
        role = validated_data.pop("role", UserRole.CUSTOMER)
        display_name = validated_data.pop("display_name", "")
        phone = validated_data.pop("phone", "")
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)
        profile = user.profile
        profile.role = role
        profile.display_name = display_name
        profile.phone = phone
        profile.save(update_fields=["role", "display_name", "phone", "updated_at"])
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username")
    email = serializers.EmailField(source="user.email", allow_blank=True, required=False)
    is_staff = serializers.BooleanField(source="user.is_staff", read_only=True)

    class Meta:
        model = UserProfile
        fields = ("username", "email", "role", "display_name", "phone", "bio", "is_staff")
        read_only_fields = ("role",)

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
