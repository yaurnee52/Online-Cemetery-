from django.contrib import admin

from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "role",
        "last_name",
        "first_name",
        "passport_series",
        "passport_number",
        "phone",
    )
    list_filter = ("role",)
    search_fields = (
        "user__username",
        "display_name",
        "last_name",
        "first_name",
        "passport_number",
        "phone",
    )
