from django.contrib import admin
from .models import Order, OrderProduct

class OrderProductInline(admin.TabularInline):
    model = OrderProduct
    extra = 0

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    inlines = [OrderProductInline]
    list_display = ('id', 'full_name', 'phone', 'status', 'total_cost')
    list_filter = ('status', 'created_at')
    search_fields = ('full_name', 'phone', 'email')