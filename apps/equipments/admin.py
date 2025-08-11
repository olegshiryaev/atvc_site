from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.contrib.humanize.templatetags.humanize import intcomma
from .models import *
    

class ProductItemInline(admin.TabularInline):
    model = ProductItem
    extra = 1
    fields = (
        'admin_image_preview', 'color', 'price', 'old_price', 'in_stock', 
        'article', 'slug', 'installment_badge'
    )
    readonly_fields = ('admin_image_preview', 'slug', 'installment_badge')
    autocomplete_fields = ('color',)
    show_change_link = True

    def admin_image_preview(self, obj):
        if obj.pk and obj.get_main_image():
            img = obj.get_main_image()
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 4px;">',
                img.image.url
            )
        return "—"
    admin_image_preview.short_description = "Фото"

    def installment_badge(self, obj):
        if not obj.installment_available:
            return format_html('<span style="color: #999;">—</span>')
        parts = []
        if obj.installment_12_months:
            parts.append(f"12м: {intcomma(obj.installment_12_months)}")
        if obj.installment_24_months:
            parts.append(f"24м: {intcomma(obj.installment_24_months)}")
        if obj.installment_48_months:
            parts.append(f"48м: {intcomma(obj.installment_48_months)}")
        return format_html('<br>'.join(parts))
    installment_badge.short_description = "Рассрочка"


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image_preview', 'image', 'is_main', 'order')
    readonly_fields = ('image_preview',)
    ordering = ('order',)

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 4px;">',
                obj.image.url
            )
        return "—"
    image_preview.short_description = "Превью"


class SmartSpeakerInline(admin.StackedInline):
    model = SmartSpeaker
    can_delete = False
    verbose_name = "Характеристики умной колонки"
    fieldsets = (
        ("Аудио", {
            "fields": (("max_power", "voice_assistant"), "frequency_range", "signal_noise_ratio")
        }),
        ("Подключение", {
            "fields": ("wireless_connection", "wifi_standard", "power_source")
        }),
        ("Физические параметры", {
            "fields": ("dimensions", "weight"),
            "classes": ("collapse",)
        }),
    )

class CameraInline(admin.StackedInline):
    model = Camera
    can_delete = False
    verbose_name = "Характеристики камеры"
    fieldsets = (
        ("Тип и стандарт", {
            "fields": (("camera_standard", "camera_type"),)
        }),
        ("Качество изображения", {
            "fields": (("resolution_mp", "resolution"), "frame_rate", "matrix_type", "focal_length", "viewing_angle")
        }),
        ("Рабочие условия", {
            "fields": ("operating_temperature",)
        }),
        ("Физические параметры", {
            "fields": ("dimensions", "weight"),
            "classes": ("collapse",)
        }),
    )

class RouterInline(admin.StackedInline):
    model = Router
    can_delete = False
    verbose_name = "Характеристики роутера"
    fieldsets = (
        ("Скорость и покрытие", {
            "fields": (("max_speed", "port_speed"), "coverage_area", "supports_devices")
        }),
        ("Wi-Fi", {
            "fields": (("bands", "frequency"), "wifi_standards", "supports_ipv6")
        }),
        ("Порты и память", {
            "fields": (("lan_ports", "antennas_count"), "ram", "encryption")
        }),
        ("Управление", {
            "fields": ("management", "vpn_support")
        }),
        ("Физические параметры", {
            "fields": ("dimensions", "weight"),
            "classes": ("collapse",)
        }),
    )

class TvBoxInline(admin.StackedInline):
    model = TvBox
    can_delete = False
    verbose_name = "Характеристики ТВ-приставки"
    fieldsets = (
        ("Подключение", {
            "fields": (("ethernet", "wifi"), "hdmi", "hdmi_version", "av_output", "usb_ports")
        }),
        ("Память", {
            "fields": (("os", "ram", "rom"),)
        }),
        ("Дополнительно", {
            "fields": (("sd_card", "usb_count"), "protocols")
        }),
    )


@admin.register(ProductItem)
class ProductItemAdmin(admin.ModelAdmin):
    list_display = (
        'product_link', 'color', 'price_display', 'old_price', 
        'in_stock', 'is_in_stock', 'images_count', 'installment_badge'
    )
    list_filter = ('color', 'in_stock', 'product__category', 'installment_available')
    search_fields = ('product__name', 'article', 'color__name')
    autocomplete_fields = ('product', 'color')
    readonly_fields = ('slug', 'get_main_image_preview')
    
    fieldsets = (
        (None, {
            'fields': ('product', 'color', 'price', 'old_price', 'in_stock', 'article', 'slug')
        }),
        ('Изображение', {
            'fields': ('get_main_image_preview',)
        }),
        ('Рассрочка', {
            'fields': (
                'installment_available',
                'installment_12_months',
                'installment_24_months',
                'installment_48_months',
            ),
            'classes': ('collapse',),
            'description': 'Условия рассрочки для этой товарной позиции. '
                           'Если рассрочка доступна — укажите хотя бы один срок.'
        }),
    )
    inlines = [ProductImageInline]

    def product_link(self, obj):
        url = reverse('admin:equipments_product_change', args=[obj.product.pk])
        return format_html('<a href="{}">{}</a>', url, obj.product.name)
    product_link.short_description = "Товар"

    def price_display(self, obj):
        return f"{intcomma(obj.price)} ₽"
    price_display.short_description = "Цена"

    def is_in_stock(self, obj):
        return obj.in_stock > 0
    is_in_stock.boolean = True
    is_in_stock.short_description = "В наличии"

    def images_count(self, obj):
        return obj.images.count()
    images_count.short_description = "Фото"

    def get_main_image_preview(self, obj):
        if obj.pk:
            img = obj.get_main_image()
            if img:
                return format_html(
                    '<img src="{}" style="width: 200px; border-radius: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.1);">',
                    img.image.url
                )
        return "Нет изображения"
    get_main_image_preview.short_description = "Основное изображение"
    get_main_image_preview.allow_tags = True

    # === НОВОЕ: Отображение рассрочки в списке ===
    def installment_badge(self, obj):
        if not obj.installment_available:
            return format_html('<span style="color: #999; font-size: 0.9em;">—</span>')

        parts = []
        if obj.installment_12_months:
            parts.append(f"12 мес: {intcomma(obj.installment_12_months)} ₽")
        if obj.installment_24_months:
            parts.append(f"24 мес: {intcomma(obj.installment_24_months)} ₽")
        if obj.installment_48_months:
            parts.append(f"48 мес: {intcomma(obj.installment_48_months)} ₽")

        return format_html(
            '<div style="font-size: 0.9em; color: #0066cc; font-weight: 500;">{}</div>',
            "<br>".join(parts)
        )
    installment_badge.short_description = "Рассрочка"
    installment_badge.allow_tags = True

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product', 'color')
    

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'admin_image', 'name', 'category', 'is_available', 'is_featured',
        'view_count', 'created_at', 'items_count'
    )
    list_filter = (
        'is_available', 'is_featured', 'category', 'created_at'
    )
    search_fields = ('name', 'slug', 'category__name')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at', 'view_count_link')
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'category', 'description')
        }),
        ('Дополнительно', {
            'fields': ('warranty', 'instruction', 'is_featured', 'is_available'),
            'classes': ('collapse',)
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    inlines = [ProductItemInline, SmartSpeakerInline, CameraInline, RouterInline, TvBoxInline]

    def admin_image(self, obj):
        main_image = obj.items.filter(in_stock__gt=0).first()
        if main_image:
            img = main_image.get_main_image()
            if img:
                return format_html(
                    '<img src="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 4px;">',
                    img.image.url
                )
        return format_html('<div style="width:50px; height:50px; background:#f0f0f0; text-align:center; line-height:50px; border-radius:4px;">нет</div>')

    admin_image.short_description = "Фото"

    def view_count(self, obj):
        count = ViewCount.objects.filter(item__product=obj).count()
        if count:
            url = reverse('admin:equipments_viewcount_changelist') + f'?item__product__id={obj.id}'
            return format_html('<a href="{}">{} просмотров</a>', url, intcomma(count))
        return "0"
    view_count.short_description = "Просмотры"

    def items_count(self, obj):
        count = obj.items.count()
        return format_html('<span style="color: #0066cc;">{} позиций</span>', count)
    items_count.short_description = "Позиции"

    def view_count_link(self, obj):
        count = ViewCount.objects.filter(item__product=obj).count()
        return intcomma(count)
    view_count_link.short_description = "Всего просмотров"

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('items__images')


@admin.register(ViewCount)
class ViewCountAdmin(admin.ModelAdmin):
    list_display = ('item_link', 'user', 'session_short', 'ip_address', 'viewed_on')
    list_filter = ('viewed_on', 'item__product__category')  # Фильтр по категории товара
    search_fields = (
        'item__product__name',
        'item__color__name',
        'user__username',
        'session_key',
        'ip_address'
    )
    readonly_fields = ('item_link_full', 'user', 'session_key', 'ip_address', 'viewed_on')

    def item_link(self, obj):
        url = reverse('admin:equipment_productitem_change', args=[obj.item.pk])
        return format_html('<a href="{}">{}</a>', url, str(obj.item))
    item_link.short_description = "Товарная позиция"
    item_link.allow_tags = True

    def item_link_full(self, obj):
        return self.item_link(obj)
    item_link_full.short_description = "Товарная позиция"
    item_link_full.allow_tags = True

    def session_short(self, obj):
        return obj.session_key[:8] if obj.session_key else "—"
    session_short.short_description = "Сессия"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return True
    

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'product_count', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}  # Авто-генерация slug при вводе name
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('name', 'slug')
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def product_count(self, obj):
        count = obj.products.count()
        url = reverse('admin:equipments_product_changelist') + f'?category__id={obj.id}'
        return format_html('<a href="{}">{}</a>', url, count)
    product_count.short_description = "Товары"
    product_count.admin_order_field = 'products__count'

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            products__count=models.Count('products')
        )


@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ('name', 'hex_code', 'color_preview', 'product_count')
    search_fields = ('name', 'hex_code')
    prepopulated_fields = {'slug': ('name',)}

    def color_preview(self, obj):
        if obj.hex_code:
            return format_html(
                '<div style="width: 30px; height: 30px; background: {}; border: 1px solid #ccc; border-radius: 4px;"></div>',
                obj.hex_code
            )
        return "—"
    color_preview.short_description = "Цвет"

    def product_count(self, obj):
        count = ProductItem.objects.filter(color=obj).count()
        return format_html('<span style="color: #0066cc;">{}</span>', count)
    product_count.short_description = "Товары"


# Кастомизация заголовка
admin.site.site_header = "Админка Оборудования"
admin.site.site_title = "Оборудование"
admin.site.index_title = "Добро пожаловать в админку"