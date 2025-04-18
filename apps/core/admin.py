from django.contrib import admin
from django.utils.safestring import mark_safe
import csv
from django.http import HttpResponse

from apps.cities.models import City
from .models import (
    Application,
    Banner,
    Device,
    Feedback,
    Office,
    Service,
    TVChannel,
    Tariff,
    WorkSchedule,
)


class WorkScheduleInline(admin.TabularInline):
    model = WorkSchedule
    extra = 1


@admin.register(Office)
class OfficeAdmin(admin.ModelAdmin):
    inlines = [WorkScheduleInline]


class CityFilter(admin.SimpleListFilter):
    title = "Город"
    parameter_name = "city"

    def lookups(self, request, model_admin):
        cities = City.objects.filter(is_active=True)
        return [(city.id, city.name) for city in cities]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(cities__id=self.value())
        return queryset


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(TVChannel)
class TVChannelAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "is_hd", "logo_preview"]
    list_filter = ["category", "is_hd"]
    search_fields = ["name"]
    fields = ["name", "category", "is_hd", "description", "logo"]

    def logo_preview(self, obj):
        if obj.logo:
            return mark_safe(f'<img src="{obj.logo.url}" width="50" />')
        return "-"

    logo_preview.short_description = "Логотип"


@admin.register(Tariff)
class TariffAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "service",
        "technology",
        "speed",
        "price",
        "is_active",
        "get_cities",
    )
    list_editable = ("price", "is_active")
    list_filter = (CityFilter, "service")
    filter_horizontal = ["cities", "included_channels"]
    search_fields = ["name", "description"]
    actions = ["export_as_csv"]

    fieldsets = (
        ("Основное", {"fields": ("name", "service", "price", "is_active")}),
        (
            "Характеристики",
            {
                "fields": (
                    "technology",
                    "speed",
                    "channels",
                    "hd_channels",
                    "description",
                ),
                "classes": ("collapse",),
            },
        ),
        ("Привязка к городам", {"fields": ("cities",)}),
        ("ТВ каналы", {"fields": ("included_channels",)}),
    )

    def get_cities(self, obj):
        return ", ".join(obj.cities.values_list("name", flat=True))

    get_cities.short_description = "Города"

    def export_as_csv(self, request, queryset):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="tariffs.csv"'

        writer = csv.writer(response)
        writer.writerow(["Название", "Тип", "Цена", "Скорость", "Города"])

        for tariff in queryset:
            cities = ", ".join([city.name for city in tariff.cities.all()])
            writer.writerow(
                [
                    tariff.name,
                    tariff.get_service_display(),
                    tariff.price,
                    tariff.speed or "-",
                    cities,
                ]
            )
        return response

    export_as_csv.short_description = "Экспорт в CSV"

    class Media:
        css = {"all": ("fontawesome/css/all.min.css",)}


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ("name", "get_service_types", "price")
    list_filter = ("service_types",)
    search_fields = ("name",)

    def get_service_types(self, obj):
        return ", ".join([s.name for s in obj.service_types.all()])

    get_service_types.short_description = "Типы услуги"


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "phone",
        "city",
        "status",
        "created_at",
        "updated_at",
    )
    list_filter = ("status", "city", "created_at")
    search_fields = ("name", "phone", "street", "house_number", "comment")
    list_editable = ("status",)
    date_hierarchy = "created_at"
    readonly_fields = ("created_at", "updated_at")
    list_per_page = 25
    fieldsets = (
        (None, {"fields": ("name", "phone", "status")}),
        ("Адрес", {"fields": ("city", "street", "house_number")}),
        ("Дополнительно", {"fields": ("comment",)}),
        ("Даты", {"fields": ("created_at", "updated_at")}),
    )
    ordering = ("-created_at",)
    actions = ["mark_as_in_progress", "mark_as_completed"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("city")

    # Кастомное действие: "Пометить как в обработке"
    @admin.action(description="Пометить выбранные заявки как 'В обработке'")
    def mark_as_in_progress(self, request, queryset):
        queryset.update(status="in_progress")

    # Кастомное действие: "Пометить как завершенные"
    @admin.action(description="Пометить выбранные заявки как 'Завершена'")
    def mark_as_completed(self, request, queryset):
        queryset.update(status="completed")


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    """
    Админ-панель модели профиля
    """

    list_display = ("email", "ip_address", "user")
    list_display_links = ("email", "ip_address")


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ("title", "is_active", "order")
    list_editable = ("is_active", "order")
