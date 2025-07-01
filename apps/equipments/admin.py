from django.contrib import admin
from .models import Category, Product, ProductImage, ProductVariant, SmartSpeaker, Camera, Router, TvBox, ViewCount


# Inline классы для связанных моделей
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image', 'color', 'is_main', 'order')
    ordering = ('order',)


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ('color', 'sku', 'stock', 'price')


class SmartSpeakerInline(admin.StackedInline):
    model = SmartSpeaker
    extra = 0
    max_num = 1
    fields = (
        'max_power', 'voice_assistant', 'wireless_connection',
        'power_source', 'frequency_range', 'wifi_standard',
        'signal_noise_ratio', 'dimensions', 'weight'
    )


class CameraInline(admin.StackedInline):
    model = Camera
    extra = 0
    max_num = 1
    fields = (
        'color', 'camera_standard', 'camera_type', 'resolution_mp',
        'frame_rate', 'operating_temperature', 'dimensions', 'weight',
        'focal_length', 'resolution', 'matrix_type', 'viewing_angle'
    )


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


class TvBoxInline(admin.StackedInline):
    model = TvBox
    extra = 0
    max_num = 1
    fields = (
        'color', 'ethernet', 'usb_count', 'os', 'hdmi', 'usb_ports',
        'hdmi_version', 'av_output', 'sd_card', 'ram', 'rom', 'wifi',
        'protocols'
    )


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    list_filter = ('name',)
    
    fieldsets = (
        (None, {
            'fields': ('name', 'slug')
        }),
    )


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'price', 'is_available', 'category', 'get_services')
    search_fields = ('name', 'description', 'short_description')
    list_filter = ('is_available', 'category', 'services')
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ('price', 'is_available')
    inlines = [ProductImageInline, ProductVariantInline, SmartSpeakerInline, CameraInline, RouterInline, TvBoxInline]
    
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'category', 'price', 'is_available')
        }),
        ('Descriptions', {
            'fields': ('short_description', 'description')
        }),
        ('Services', {
            'fields': ('services',)
        }),
    )

    def get_services(self, obj):
        return ", ".join([service.name for service in obj.services.all()])
    get_services.short_description = 'Услуги'


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('product', 'image', 'color', 'is_main', 'order')
    list_filter = ('product', 'color', 'is_main')
    search_fields = ('product__name',)
    list_editable = ('is_main', 'order', 'color')
    
    fieldsets = (
        (None, {
            'fields': ('product', 'image', 'color', 'is_main', 'order')
        }),
    )


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ('product', 'color', 'sku', 'stock', 'price')
    list_filter = ('color', 'product')
    search_fields = ('product__name', 'sku')
    list_editable = ('stock', 'price', 'color')
    
    fieldsets = (
        (None, {
            'fields': ('product', 'color', 'sku', 'stock', 'price')
        }),
    )


@admin.register(SmartSpeaker)
class SmartSpeakerAdmin(admin.ModelAdmin):
    list_display = ('product', 'voice_assistant', 'max_power', 'wireless_connection')
    search_fields = ('product__name', 'voice_assistant', 'wireless_connection')
    list_filter = ('voice_assistant', 'wireless_connection')
    
    fieldsets = (
        (None, {
            'fields': ('product',)
        }),
        ('Technical Specifications', {
            'fields': (
                'max_power', 'voice_assistant', 'wireless_connection', 
                'power_source', 'frequency_range', 'wifi_standard', 
                'signal_noise_ratio', 'dimensions', 'weight'
            )
        }),
    )


@admin.register(Camera)
class CameraAdmin(admin.ModelAdmin):
    list_display = ('product', 'camera_type', 'resolution', 'color')
    search_fields = ('product__name', 'camera_type', 'resolution', 'matrix_type')
    list_filter = ('camera_type', 'camera_standard', 'color')
    
    fieldsets = (
        (None, {
            'fields': ('product', 'color')
        }),
        ('Technical Specifications', {
            'fields': (
                'camera_standard', 'camera_type', 'resolution_mp', 'frame_rate',
                'operating_temperature', 'dimensions', 'weight', 'focal_length',
                'resolution', 'matrix_type', 'viewing_angle'
            )
        }),
    )


@admin.register(Router)
class RouterAdmin(admin.ModelAdmin):
    list_display = ('product', 'max_speed', 'bands', 'frequency', 'color')
    search_fields = ('product__name', 'wifi_standards', 'management')
    list_filter = ('bands', 'frequency', 'color', 'supports_ipv6')
    
    fieldsets = (
        (None, {
            'fields': ('product', 'color')
        }),
        ('Network Specifications', {
            'fields': (
                'max_speed', 'supports_devices', 'coverage_area', 
                'bands', 'frequency', 'wifi_standards', 'supports_ipv6', 
                'encryption', 'management', 'vpn_support'
            )
        }),
        ('Hardware', {
            'fields': ('antennas_count', 'lan_ports', 'port_speed', 'ram', 'dimensions', 'weight')
        }),
    )


@admin.register(TvBox)
class TvBoxAdmin(admin.ModelAdmin):
    list_display = ('product', 'os', 'color', 'hdmi')
    search_fields = ('product__name', 'os', 'wifi')
    list_filter = ('color', 'os', 'hdmi', 'av_output', 'sd_card')
    
    fieldsets = (
        (None, {
            'fields': ('product', 'color')
        }),
        ('Technical Specifications', {
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
    
    fieldsets = (
        (None, {
            'fields': ('product', 'user', 'session_key', 'ip_address', 'viewed_on')
        }),
    )
    
    def has_add_permission(self, request):
        return False  # Views are typically recorded automatically, not added manually
    
    def has_change_permission(self, request, obj=None):
        return False  # Views shouldn't be editable