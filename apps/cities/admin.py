from django.contrib import admin
from .models import District, Locality, Region


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ("name", "region")
    list_filter = ("region",)
    search_fields = ("name",)


@admin.register(Locality)
class LocalityAdmin(admin.ModelAdmin):
    list_display = ("name", "locality_type", "district", "is_active")
    list_filter = ("locality_type", "is_active", "district__region")
    search_fields = ("name", "name_prepositional")
    prepopulated_fields = {"slug": ("name",)}
