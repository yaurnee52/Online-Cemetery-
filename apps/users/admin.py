from django.contrib import admin

from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "role", "display_name", "phone")
    list_filter = ("role",)
    search_fields = ("user__username", "display_name", "phone")
