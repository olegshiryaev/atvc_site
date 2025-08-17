from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import Order, OrderProduct

class OrderProductInline(admin.TabularInline):
    model = OrderProduct
    extra = 0
    fields = ('product_item', 'price', 'payment_type', 'display_price')
    readonly_fields = ('product_item', 'payment_type', 'display_price')

    def display_price(self, obj):
        """Отображение цены с учётом типа оплаты."""
        return obj.get_display_price()
    display_price.short_description = 'Цена'

    def get_queryset(self, request):
        """Оптимизация запроса для включения данных о товарной позиции."""
        return super().get_queryset(request).select_related('product_item__product', 'product_item__color')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    inlines = [OrderProductInline]
    list_display = (
        'number',
        'full_name',
        'phone',
        'locality_link',
        'tariffs_display',
        'status',
        'total_cost_display',
        'created_at',
        'products_count'
    )
    list_filter = ('status', 'created_at', 'locality', 'tariffs')
    search_fields = (
        'full_name', 'phone', 'email',
        'order_products__product_item__product__name',
        'order_products__product_item__color__name'
    )
    date_hierarchy = 'created_at'
    actions = ['mark_as_processed', 'mark_as_completed']

    # --- Кастомные отображения ---
    def number(self, obj):
        return obj.id
    number.short_description = '№'
    number.admin_order_field = 'id'

    def total_cost_display(self, obj):
        cost = obj.total_cost()
        return f"{cost:,.0f} ₽".replace(',', ' ')
    total_cost_display.short_description = 'Итого'

    def locality_link(self, obj):
        if obj.locality:
            url = reverse('admin:cities_locality_change', args=[obj.locality.id])
            return format_html('<a href="{}">{}</a>', url, obj.locality.name)
        return '-'
    locality_link.short_description = 'Населенный пункт'

    def tariffs_display(self, obj):
        if obj.tariffs.exists():
            tariff_links = [
                format_html('<a href="{}">{}</a>', 
                            reverse('admin:core_tariff_change', args=[tariff.id]), 
                            tariff.name)
                for tariff in obj.tariffs.all()
            ]
            return format_html(', '.join(tariff_links))
        return '-'
    tariffs_display.short_description = 'Тарифы'

    def products_count(self, obj):
        return obj.order_products.count()
    products_count.short_description = 'Кол-во позиций'

    def mark_as_processed(self, request, queryset):
        updated = queryset.update(status='processed')
        self.message_user(request, f"{updated} заявок отмечено как 'В обработке'.")
    mark_as_processed.short_description = 'Отметить как в обработке'

    def mark_as_completed(self, request, queryset):
        updated = queryset.update(status='completed')
        self.message_user(request, f"{updated} заявок отмечено как 'Выполнена'.")
    mark_as_completed.short_description = 'Отметить как выполненные'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('locality').prefetch_related(
            'tariffs', 
            'order_products__product_item__product', 
            'order_products__product_item__color'
        )

@admin.register(OrderProduct)
class OrderProductAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'product_item_name', 'price', 'payment_type', 'display_price')
    list_filter = ('payment_type', 'order__status')
    search_fields = ('product_item__product__name', 'product_item__color__name', 'order__full_name', 'order__phone')
    readonly_fields = ('order', 'product_item', 'price', 'payment_type')

    def order_id(self, obj):
        """Отображение ID заказа со ссылкой на заказ."""
        url = reverse('admin:orders_order_change', args=[obj.order.id])
        return format_html('<a href="{}">#{}</a>', url, obj.order.id)
    order_id.short_description = 'Заявка'

    def product_item_name(self, obj):
        """Отображение имени товарной позиции."""
        return obj.product_item.get_display_name()
    product_item_name.short_description = 'Товарная позиция'

    def display_price(self, obj):
        """Отображение цены с учётом типа оплаты."""
        return obj.get_display_price()
    display_price.short_description = 'Цена'

    def get_queryset(self, request):
        """Оптимизация запроса для включения связанных данных."""
        return super().get_queryset(request).select_related('order', 'product_item__product', 'product_item__color')