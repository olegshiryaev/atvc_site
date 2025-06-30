from django.contrib import admin
from django.utils.safestring import mark_safe
from .models import (
    Category,
    Product,
    ProductVariant,
    SmartSpeaker,
    Camera,
    Router,
    TvBox,
    ProductImage,
)


# === Вспомогательные классы для инлайнов ===


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ("image", "color", "is_main", "order")
    verbose_name = "Изображение"
    verbose_name_plural = "Изображения"

    def image_preview(self, obj):
        if obj.image:
            return mark_safe(f'<img src="{obj.image.url}" width="100" height="100" />')
        return "Нет изображения"
    image_preview.short_description = "Превью"


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ("color", "sku", "stock", "price")
    verbose_name = "Вариант товара"
    verbose_name_plural = "Варианты товаров"
    

class SmartSpeakerInline(admin.StackedInline):
    model = SmartSpeaker
    can_delete = False
    verbose_name = "Характеристики умной колонки"
    verbose_name_plural = "Характеристики умной колонки"
    fieldsets = (
        ('Основные', {
            'fields': ('voice_assistant', 'power_source')
        }),
        ('Беспроводное соединение', {
            'fields': ('wireless_connection', 'wifi_standard')
        }),
        ('Аудио', {
            'fields': ('max_power', 'frequency_range', 'signal_noise_ratio')
        }),
        ('Физические характеристики', {
            'fields': ('dimensions', 'weight')
        }),
    )


class CameraInline(admin.StackedInline):
    model = Camera
    can_delete = False
    verbose_name = "Характеристики камеры"
    verbose_name_plural = "Характеристики камеры"


class RouterInline(admin.StackedInline):
    model = Router
    can_delete = False
    verbose_name = "Характеристики роутера"
    verbose_name_plural = "Характеристики роутера"


class TvBoxInline(admin.StackedInline):
    model = TvBox
    can_delete = False
    verbose_name = "Характеристики ТВ-приставки"
    verbose_name_plural = "Характеристики ТВ-приставки"


# === Админка: Product ===


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "price", "category", "is_available", "variant_count"]
    search_fields = ["name", "slug", "short_description"]
    list_filter = ["category", "is_available", "services"]
    prepopulated_fields = {"slug": ("name",)}
    inlines = [
        ProductImageInline,
        ProductVariantInline,
        SmartSpeakerInline,
        CameraInline,
        RouterInline,
        TvBoxInline,
    ]

    fieldsets = (
        (
            "Основная информация",
            {"fields": ("name", "slug", "short_description", "description")},
        ),
        ("Цена и наличие", {"fields": ("price", "is_available")}),
        ("Категория", {"fields": ("category",)}),
        ("Услуги", {"fields": ("services",)}),
    )

    def variant_count(self, obj):
        """Отображает количество вариантов товара."""
        return obj.variants.count()
    variant_count.short_description = "Варианты"

    def get_inline_instances(self, request, obj=None):
        """Показывать только релевантные инлайны в зависимости от типа товара."""
        inlines = [ProductImageInline, ProductVariantInline]
        if obj:
            if hasattr(obj, 'smart_speaker'):
                inlines.append(SmartSpeakerInline)
            elif hasattr(obj, 'camera'):
                inlines.append(CameraInline)
            elif hasattr(obj, 'router'):
                inlines.append(RouterInline)
            elif hasattr(obj, 'tvbox'):
                inlines.append(TvBoxInline)
        return [inline(self.model, self.admin_site) for inline in inlines]


# === Админка: Category ===


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}


# === Админка: ProductImage ===


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ["product", "is_main", "order"]
    list_filter = ["product"]
    search_fields = ["product__name"]


# === Админка: ProductVariant ===

@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ["product", "color", "sku", "stock", "price"]
    list_filter = ["color"]
    search_fields = ["product__name", "sku"]
    list_editable = ["stock", "price"]


# === Админка: SmartSpeaker ===


@admin.register(SmartSpeaker)
class SmartSpeakerAdmin(admin.ModelAdmin):
    list_display = ('product', 'voice_assistant', 'power_source', 'wireless_connection', 'max_power')
    list_filter = ('voice_assistant', 'power_source', 'wireless_connection')
    search_fields = ('product__name', 'voice_assistant')
    fieldsets = (
        ('Основные', {
            'fields': ('product', 'voice_assistant', 'power_source')
        }),
        ('Беспроводное соединение', {
            'fields': ('wireless_connection', 'wifi_standard')
        }),
        ('Аудио', {
            'fields': ('max_power', 'frequency_range', 'signal_noise_ratio')
        }),
        ('Физические характеристики', {
            'fields': ('dimensions', 'weight')
        }),
    )
    readonly_fields = ('product',)


# === Админка: Camera ===


@admin.register(Camera)
class CameraAdmin(admin.ModelAdmin):
    list_display = [
        "product",
        "color",
        "camera_standard",
        "camera_type",
        "resolution_mp",
        "frame_rate",
    ]
    search_fields = ["product__name"]
    list_filter = ["color", "camera_standard", "camera_type"]


# === Админка: Router ===


@admin.register(Router)
class RouterAdmin(admin.ModelAdmin):
    list_display = [
        "product",
        "max_speed",
        "supports_devices",
        "coverage_area",
        "bands",
        "wifi_standards",
    ]
    search_fields = ["product__name"]
    list_filter = ["bands", "supports_ipv6"]


# === Админка: TvBox ===


@admin.register(TvBox)
class TvBoxAdmin(admin.ModelAdmin):
    list_display = ["product", "os", "hdmi", "usb_ports"]
    search_fields = ["product__name"]
