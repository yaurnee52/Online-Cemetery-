"""Регистрация моделей в Django Admin."""
from django.contrib import admin

from .models import Burial, BurialPerson, Cemetery


@admin.register(Cemetery)
class CemeteryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "burials_total",
        "people_total",
        "latitude",
        "longitude",
    )
    list_display_links = ("id", "name")
    search_fields = ("name",)
    ordering = ("name",)
    list_per_page = 50


class BurialPersonInline(admin.TabularInline):
    model = BurialPerson
    extra = 0
    fields = ("person_name", "birth_date", "death_date", "birth_year", "death_year")
    readonly_fields = ()
    show_change_link = True


@admin.register(Burial)
class BurialAdmin(admin.ModelAdmin):
    list_display = ("id", "cemetery", "grave_number", "has_tombstone", "global_id")
    list_filter = ("has_tombstone", "cemetery")
    search_fields = ("grave_number", "inscription", "global_id")
    raw_id_fields = ("cemetery",)
    list_select_related = ("cemetery",)
    inlines = (BurialPersonInline,)
    list_per_page = 50


@admin.register(BurialPerson)
class BurialPersonAdmin(admin.ModelAdmin):
    list_display = ("id", "person_name", "burial", "birth_year", "death_year")
    search_fields = ("person_name",)
    raw_id_fields = ("burial",)
    list_select_related = ("burial",)
    list_per_page = 50
