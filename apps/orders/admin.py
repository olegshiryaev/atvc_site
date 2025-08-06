from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import Order, OrderProduct

class OrderProductInline(admin.TabularInline):
    model = OrderProduct
    extra = 0
    fields = ('product', 'quantity', 'price', 'payment_type', 'display_price')
    readonly_fields = ('product', 'payment_type', 'display_price')

    def display_price(self, obj):
        """Отображение цены с учётом типа оплаты."""
        if obj.payment_type == 'installment12' and obj.product.installment_12_months:
            return f"{obj.product.installment_12_months} руб./мес. (12 месяцев)"
        elif obj.payment_type == 'installment24' and obj.product.installment_24_months:
            return f"{obj.product.installment_24_months} руб./мес. (24 месяца)"
        elif obj.payment_type == 'installment48' and obj.product.installment_48_months:
            return f"{obj.product.installment_48_months} руб./мес. (48 месяца)"
        return f"{obj.price} руб."
    display_price.short_description = 'Цена'

    def get_queryset(self, request):
        """Оптимизация запроса для включения данных о продукте."""
        return super().get_queryset(request).select_related('product')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    inlines = [OrderProductInline]
    list_display = (
        'id', 'full_name', 'phone', 'locality_link', 'tariff_link',
        'status', 'total_cost', 'created_at', 'products_count'
    )
    list_filter = ('status', 'created_at', 'locality', 'tariff')
    search_fields = (
        'full_name', 'phone', 'email',
        'order_products__product__name'  # Поиск по именам продуктов
    )
    date_hierarchy = 'created_at'
    actions = ['mark_as_processed', 'mark_as_completed']

    def locality_link(self, obj):
        """Отображение ссылки на страницу админки населённого пункта."""
        if obj.locality:
            url = reverse('admin:cities_locality_change', args=[obj.locality.id])
            return format_html('<a href="{}">{}</a>', url, obj.locality.name)
        return '-'
    locality_link.short_description = 'Населенный пункт'

    def tariff_link(self, obj):
        """Отображение ссылки на страницу админки тарифа."""
        if obj.tariff:
            url = reverse('admin:core_tariff_change', args=[obj.tariff.id])
            return format_html('<a href="{}">{}</a>', url, obj.tariff.name)
        return '-'
    tariff_link.short_description = 'Тариф'

    def products_count(self, obj):
        """Отображение количества продуктов в заказе."""
        return obj.order_products.count()
    products_count.short_description = 'Кол-во продуктов'

    def mark_as_processed(self, request, queryset):
        """Действие для массовой пометки заказов как 'в обработке'."""
        updated = queryset.update(status='processed')
        self.message_user(request, f"{updated} заявок отмечено как 'В обработке'.")
    mark_as_processed.short_description = 'Отметить как в обработке'

    def mark_as_completed(self, request, queryset):
        """Действие для массовой пометки заказов как 'выполнено'."""
        updated = queryset.update(status='completed')
        self.message_user(request, f"{updated} заявок отмечено как 'Выполнена'.")
    mark_as_completed.short_description = 'Отметить как выполненные'

    def get_queryset(self, request):
        """Оптимизация запроса для включения связанных данных."""
        return super().get_queryset(request).select_related('locality', 'tariff').prefetch_related('order_products__product')

@admin.register(OrderProduct)
class OrderProductAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'product_name', 'quantity', 'price', 'payment_type', 'display_price')
    list_filter = ('payment_type', 'order__status')
    search_fields = ('product__name', 'order__full_name', 'order__phone')
    readonly_fields = ('order', 'product', 'price', 'quantity', 'payment_type')

    def order_id(self, obj):
        """Отображение ID заказа со ссылкой на заказ."""
        url = reverse('admin:orders_order_change', args=[obj.order.id])
        return format_html('<a href="{}">#{}</a>', url, obj.order.id)
    order_id.short_description = 'Заявка'

    def product_name(self, obj):
        """Отображение имени продукта."""
        return obj.product.name
    product_name.short_description = 'Продукт'

    def display_price(self, obj):
        """Отображение цены с учётом типа оплаты."""
        if obj.payment_type == 'installment12' and obj.product.installment_12_months:
            return f"{obj.product.installment_12_months} руб./мес. (12 месяцев)"
        elif obj.payment_type == 'installment24' and obj.product.installment_24_months:
            return f"{obj.product.installment_24_months} руб./мес. (24 месяца)"
        elif obj.payment_type == 'installment48' and obj.product.installment_48_months:
            return f"{obj.product.installment_48_months} руб./мес. (48 месяцев)"
        return f"{obj.price} руб."
    display_price.short_description = 'Цена'

    def get_queryset(self, request):
        """Оптимизация запроса для включения связанных данных."""
        return super().get_queryset(request).select_related('order', 'product')