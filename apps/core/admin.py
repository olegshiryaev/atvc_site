from django.contrib import admin
from django.utils.safestring import mark_safe
import csv
from django.http import HttpResponse
from django.utils.html import format_html

from apps.cities.models import Locality
from apps.core.forms import DocumentForm
from .models import (
    AdditionalService,
    Application,
    Banner,
    Company,
    Equipment,
    Document,
    Feedback,
    Office,
    Order,
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


class LocalityFilter(admin.SimpleListFilter):
    title = "Город"
    parameter_name = "locality"

    def lookups(self, request, model_admin):
        localities = Locality.objects.filter(is_active=True)
        return [(locality.id, locality.name) for locality in localities]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(localities__id=self.value())
        return queryset


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    filter_horizontal = ("localities",)
    list_display = ("name", "slug", "is_active")
    search_fields = ("name",)
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
        "slug",
        "get_localities",
    )
    list_editable = ("price", "is_active")
    list_filter = (LocalityFilter, "service")
    filter_horizontal = ["localities", "included_channels"]
    search_fields = ["name", "slug", "description"]
    readonly_fields = ("slug",)
    actions = ["export_as_csv"]

    fieldsets = (
        ("Основное", {"fields": ("name", "slug", "service", "price", "is_active")}),
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
        ("Привязка к городам", {"fields": ("localities",)}),
        ("ТВ каналы", {"fields": ("included_channels",)}),
    )

    def get_localities(self, obj):
        return ", ".join(obj.localities.values_list("name", flat=True))

    get_localities.short_description = "Города"

    def export_as_csv(self, request, queryset):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="tariffs.csv"'

        writer = csv.writer(response)
        writer.writerow(["Название", "Слаг", "Тип", "Цена", "Скорость", "Города"])

        for tariff in queryset:
            localities = ", ".join(
                [locality.name for locality in tariff.localities.all()]
            )
            writer.writerow(
                [
                    tariff.name,
                    tariff.slug,
                    tariff.get_service_display(),
                    tariff.price,
                    tariff.speed or "-",
                    localities,
                ]
            )
        return response

    export_as_csv.short_description = "Экспорт в CSV"

    class Media:
        css = {"all": ("fontawesome/css/all.min.css",)}


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ("image_thumb", "name", "equipment_type", "price", "get_service_types")
    list_filter = ("equipment_type", "service_types")
    search_fields = ("name", "description")
    autocomplete_fields = ("service_types",)
    filter_horizontal = ("service_types",)
    readonly_fields = ("image_preview",)
    fieldsets = (
        (None, {"fields": ("name", "equipment_type", "price", "description")}),
        ("Изображение", {"fields": ("image", "image_preview")}),
        ("Услуги", {"fields": ("service_types",)}),
    )

    def get_service_types(self, obj):
        return ", ".join([s.name for s in obj.service_types.all()])

    get_service_types.short_description = "Типы услуги"

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 200px;" />', obj.image.url
            )
        return "Нет изображения"

    image_preview.short_description = "Превью изображения"

    def image_thumb(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height: 50px;" />', obj.image.url)
        return "—"

    image_thumb.short_description = "Фото"


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "phone",
        "locality",
        "status",
        "created_at",
        "updated_at",
    )
    list_filter = ("status", "locality", "created_at")
    search_fields = ("name", "phone", "street", "house_number", "comment")
    list_editable = ("status",)
    date_hierarchy = "created_at"
    readonly_fields = ("created_at", "updated_at")
    list_per_page = 25
    fieldsets = (
        (None, {"fields": ("name", "phone", "status")}),
        ("Адрес", {"fields": ("locality", "street", "house_number")}),
        ("Дополнительно", {"fields": ("comment",)}),
        ("Даты", {"fields": ("created_at", "updated_at")}),
    )
    ordering = ("-created_at",)
    actions = ["mark_as_in_progress", "mark_as_completed"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("locality")

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
    list_display = (
        "name",
        "phone",
        "short_content",
        "time_create",
        "ip_address",
        "user",
    )
    list_filter = ("time_create", "user")
    search_fields = ("name", "phone", "content", "ip_address")
    readonly_fields = ("time_create", "ip_address", "user")

    def short_content(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content

    short_content.short_description = "Сообщение"


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ["title", "banner_type", "is_active", "order"]
    list_filter = ["banner_type", "is_active"]
    search_fields = ["title", "description"]
    ordering = ["order"]
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "title",
                    "description",
                    "background_image",
                    "button_text",
                    "link",
                )
            },
        ),
        (
            "Тип и настройки",
            {"fields": ("banner_type", "is_active", "localities", "order")},
        ),
    )


class DocumentInline(admin.TabularInline):
    model = Document
    fields = ("title", "file", "thumbnail_preview")
    readonly_fields = ("thumbnail_preview",)

    def thumbnail_preview(self, obj):
        if obj.thumbnail:
            return format_html(
                '<img src="{}" style="max-height:100px;" />', obj.thumbnail.url
            )
        return "-"

    thumbnail_preview.short_description = "Превью"


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("short_name", "full_name", "inn", "kpp", "email")
    search_fields = ("short_name", "full_name", "inn")
    inlines = [DocumentInline]


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "company",
        "file_link",
        "file_type",
        "uploaded_at",
        "thumbnail_preview",
    )
    list_filter = ("company", "uploaded_at")
    search_fields = ("title", "company__name")
    readonly_fields = ("thumbnail_preview", "uploaded_at", "extension")

    def file_type(self, obj):
        return obj.extension

    file_type.short_description = "Тип файла"

    def file_link(self, obj):
        if obj.file:
            return format_html('<a href="{}" target="_blank">Скачать</a>', obj.file.url)
        return "-"

    file_link.short_description = "Файл"

    def thumbnail_preview(self, obj):
        if obj.thumbnail:
            return format_html(
                '<img src="{}" style="max-height: 100px; max-width: 80px; object-fit: contain;">',
                obj.thumbnail.url,
            )
        elif obj.extension in ("PDF", "JPG", "JPEG", "PNG"):
            return format_html('<span class="text-muted">В обработке...</span>')
        else:
            return "-"

    thumbnail_preview.short_description = "Миниатюра"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone', 'tariff', 'equipment_summary', 'total_services', 'total_cost', 'created_at')
    list_filter = ('tariff', 'equipment', 'created_at')
    search_fields = ('full_name', 'phone', 'street', 'house')
    readonly_fields = ('created_at',)
    fieldsets = (
        ('Информация о клиенте', {
            'fields': ('full_name', 'phone')
        }),
        ('Адрес', {
            'fields': ('street', 'house')
        }),
        ('Тариф и оборудование', {
            'fields': ('tariff', 'equipment')
        }),
        ('Дополнительные услуги', {
            'fields': ('services',)
        }),
        ('Комментарий и дата', {
            'fields': ('comment', 'created_at')
        }),
    )

    def equipment_summary(self, obj):
        return obj.equipment.name if obj.equipment else '-'
    equipment_summary.short_description = 'Оборудование'

    def total_services(self, obj):
        return ", ".join(service.name for service in obj.services.all()) or '-'
    total_services.short_description = 'Услуги'

    def total_cost(self, obj):
        return f"{obj.total_cost()} ₽"
    total_cost.short_description = 'Сумма к оплате'


@admin.register(AdditionalService)
class AdditionalServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'description_short')
    search_fields = ('name',)

    def description_short(self, obj):
        return obj.description[:50] + '...' if obj.description and len(obj.description) > 50 else obj.description
    description_short.short_description = 'Описание'