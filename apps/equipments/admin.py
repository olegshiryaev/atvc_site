from django.contrib import admin
from django.utils.safestring import mark_safe
from .models import Category, Product, ProductImage, ProductVariant, SmartSpeaker, Camera, Router, TvBox, ViewCount
from django.db.models import Count


# Inline классы для связанных моделей
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0
    max_num = 10
    fields = ('image', 'color', 'is_main', 'order')
    ordering = ('order',)
    verbose_name = "Изображение товара"
    verbose_name_plural = "Изображения товаров"


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0
    fields = ('color', 'sku', 'stock', 'price')
    verbose_name = "Вариант товара"
    verbose_name_plural = "Варианты товаров"


class SmartSpeakerInline(admin.StackedInline):
    model = SmartSpeaker
    extra = 0
    max_num = 1
    fields = (
        'max_power', 'voice_assistant', 'wireless_connection',
        'power_source', 'frequency_range', 'wifi_standard',
        'signal_noise_ratio', 'dimensions', 'weight'
    )
    verbose_name = "Умная колонка"
    verbose_name_plural = "Умные колонки"


class CameraInline(admin.StackedInline):
    model = Camera
    extra = 0
    max_num = 1
    fields = (
        'color', 'camera_standard', 'camera_type', 'resolution_mp',
        'frame_rate', 'operating_temperature', 'dimensions', 'weight',
        'focal_length', 'resolution', 'matrix_type', 'viewing_angle'
    )
    verbose_name = "IP-камера"
    verbose_name_plural = "IP-камеры"


class RouterInline(admin.StackedInline):
    model = Router
    extra = 0
    max_num = 1
    fields = (
        'max_speed', 'supports_devices', 'coverage_area', 'bands',
        'frequency', 'color', 'dimensions', 'weight', 'antennas_count',
        'lan_ports', 'ram', 'supports_ipv6', 'encryption', 'management',
        'vpn_support', 'port_speed'
    )
    verbose_name = "Роутер"
    verbose_name_plural = "Роутеры"


class TvBoxInline(admin.StackedInline):
    model = TvBox
    extra = 0
    max_num = 1
    fields = (
        'color', 'ethernet', 'usb_count', 'os', 'hdmi', 'usb_ports',
        'hdmi_version', 'av_output', 'sd_card', 'ram', 'rom', 'wifi',
        'protocols'
    )
    verbose_name = "ТВ-приставка"
    verbose_name_plural = "ТВ-приставки"


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    list_filter = ('name',)
    
    fieldsets = (
        (None, {
            'fields': ('name', 'slug'),
            'description': "Основные параметры категории"
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).order_by('name')

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'price', 'installment_available', 'is_available', 'category', 'get_services', 'get_main_image')
    search_fields = ('name', 'description', 'short_description')
    list_filter = ('is_available', 'category', 'services')
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ('price', 'is_available')
    autocomplete_fields = ['category', 'services']
    inlines = [ProductImageInline, ProductVariantInline, SmartSpeakerInline, CameraInline, RouterInline, TvBoxInline]
    
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'category', 'price', 'installment_available', 'installment_12_months', 'installment_24_months', 'is_available'),
            'description': "Основные параметры товара"
        }),
        ('Описание товара', {
            'fields': ('short_description', 'description')
        }),
        ('Услуги', {
            'fields': ('services',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('category').prefetch_related('services', 'images')
    
    def get_inlines(self, request, obj):
        inlines = [ProductImageInline, ProductVariantInline]
        if obj and obj.category:
            if obj.category.name == "Умные колонки":
                inlines.append(SmartSpeakerInline)
            elif obj.category.name == "Камеры":
                inlines.append(CameraInline)
            elif obj.category.name == "Роутеры":
                inlines.append(RouterInline)
            elif obj.category.name == "ТВ-приставки":
                inlines.append(TvBoxInline)
        return inlines

    def get_services(self, obj):
        return ", ".join([service.name for service in obj.services.all()])
    get_services.short_description = 'Услуги'

    def get_main_image(self, obj):
        main_image = obj.get_main_image()
        if main_image and main_image.image:
            return mark_safe(f'<img src="{main_image.image.url}" style="max-height: 50px;"/>')
        return "Нет изображения"
    get_main_image.short_description = "Основное изображение"


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('product', 'image_preview', 'color', 'is_main', 'order')
    list_filter = ('product', 'color', 'is_main', 'image')
    search_fields = ('product__name',)
    list_editable = ('is_main', 'order', 'color')
    readonly_fields = ('image_preview',)
    
    fieldsets = (
        (None, {
            'fields': ('product', 'image', 'image_preview', 'color', 'is_main', 'order'),
            'description': "Параметры изображения товара"
        }),
    )

    def image_preview(self, obj):
        if obj.image:
            return mark_safe(f'<img src="{obj.image.url}" style="max-height: 200px;"/>')
        return "Нет изображения"
    image_preview.short_description = "Превью"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product')


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ('product', 'color', 'sku', 'stock', 'price')
    list_filter = ('color', 'product')
    search_fields = ('product__name', 'sku')
    list_editable = ('stock', 'price', 'color')
    
    fieldsets = (
        (None, {
            'fields': ('product', 'color', 'sku', 'stock', 'price'),
            'description': "Параметры варианта товара"
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product')


@admin.register(SmartSpeaker)
class SmartSpeakerAdmin(admin.ModelAdmin):
    list_display = ('product', 'voice_assistant', 'max_power', 'wireless_connection')
    search_fields = ('product__name', 'voice_assistant', 'wireless_connection')
    list_filter = ('voice_assistant', 'wireless_connection')
    
    fieldsets = (
        (None, {
            'fields': ('product',),
            'description': "Основные параметры умной колонки"
        }),
        ('Технические характеристики', {
            'fields': (
                'max_power', 'voice_assistant', 'wireless_connection', 
                'power_source', 'frequency_range', 'wifi_standard', 
                'signal_noise_ratio', 'dimensions', 'weight'
            )
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product')


@admin.register(Camera)
class CameraAdmin(admin.ModelAdmin):
    list_display = ('product', 'camera_type', 'resolution', 'color')
    search_fields = ('product__name', 'camera_type', 'resolution', 'matrix_type')
    list_filter = ('camera_type', 'camera_standard', 'color')
    
    fieldsets = (
        (None, {
            'fields': ('product', 'color'),
            'description': "Основные параметры камеры"
        }),
        ('Технические характеристики', {
            'fields': (
                'camera_standard', 'camera_type', 'resolution_mp', 'frame_rate',
                'operating_temperature', 'dimensions', 'weight', 'focal_length',
                'resolution', 'matrix_type', 'viewing_angle'
            )
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product')


@admin.register(Router)
class RouterAdmin(admin.ModelAdmin):
    list_display = ('product', 'max_speed', 'bands', 'frequency', 'color')
    search_fields = ('product__name', 'wifi_standards', 'management')
    list_filter = ('bands', 'frequency', 'color', 'supports_ipv6')
    
    fieldsets = (
        (None, {
            'fields': ('product', 'color'),
            'description': "Основные параметры роутера"
        }),
        ("Сетевые характеристики", {
            'fields': (
                'max_speed', 'supports_devices', 'coverage_area', 
                'bands', 'frequency', 'wifi_standards', 'supports_ipv6', 
                'encryption', 'management', 'vpn_support'
            )
        }),
        ("Аппаратное обеспечение", {
            'fields': ('antennas_count', 'lan_ports', 'port_speed', 'ram', 'dimensions', 'weight')
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product')


@admin.register(TvBox)
class TvBoxAdmin(admin.ModelAdmin):
    list_display = ('product', 'os', 'color', 'hdmi')
    search_fields = ('product__name', 'os', 'wifi')
    list_filter = ('color', 'os', 'hdmi', 'av_output', 'sd_card')
    
    fieldsets = (
        (None, {
            'fields': ('product', 'color'),
            'description': "Основные параметры ТВ-приставки"
        }),
        ('Технические характеристики', {
            'fields': (
                'ethernet', 'usb_count', 'os', 'hdmi', 'usb_ports', 
                'hdmi_version', 'av_output', 'sd_card', 'ram', 'rom', 
                'wifi', 'protocols'
            )
        }),
    )


@admin.register(ViewCount)
class ViewCountAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'ip_address', 'viewed_on')
    search_fields = ('product__name', 'ip_address', 'user__username')
    list_filter = ('viewed_on', 'product')
    date_hierarchy = 'viewed_on'
    actions = ['show_view_stats']
    
    fieldsets = (
        (None, {
            'fields': ('product', 'user', 'session_key', 'ip_address', 'viewed_on'),
            'description': "Данные о просмотре товара"
        }),
    )
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def show_view_stats(self, request, queryset):
        stats = queryset.values('product__name').annotate(total_views=Count('id')).order_by('-total_views')
        message = "\n".join([f"{stat['product__name']}: {stat['total_views']} просмотров" for stat in stats])
        self.message_user(request, "Статистика просмотров:\n" + message)
    show_view_stats.short_description = "Показать статистику просмотров"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product', 'user')