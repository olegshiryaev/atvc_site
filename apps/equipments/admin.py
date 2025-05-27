from django.contrib import admin
from .models import (
    Category,
    Product,
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
    fields = ("image", "is_main", "order")
    verbose_name = "Изображение"
    verbose_name_plural = "Изображения"


class SmartSpeakerInline(admin.StackedInline):
    model = SmartSpeaker
    can_delete = False
    verbose_name = "Характеристики умной колонки"
    verbose_name_plural = "Характеристики умной колонки"


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
    list_display = ["name", "price", "category", "is_available"]
    search_fields = ["name", "slug", "short_description"]
    list_filter = ["category", "is_available"]
    prepopulated_fields = {"slug": ("name",)}
    inlines = [
        ProductImageInline,
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
    )


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


# === Админка: SmartSpeaker ===


@admin.register(SmartSpeaker)
class SmartSpeakerAdmin(admin.ModelAdmin):
    list_display = ["product", "voice_assistant", "bluetooth", "battery_life"]
    search_fields = ["product__name"]


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
