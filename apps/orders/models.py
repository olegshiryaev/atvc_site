from django.db import models
from django.conf import settings
from apps.equipments.models import Product, ProductVariant
from apps.core.models import Locality, Tariff, TVChannelPackage, AdditionalService

class OrderProduct(models.Model):
    """Промежуточная модель для товаров в заказе"""
    order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='order_products', verbose_name="Заявка")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Товар")
    variant = models.ForeignKey(
        ProductVariant, 
        on_delete=models.SET_NULL, 
        blank=True, 
        null=True, 
        verbose_name="Вариант товара"
    )
    quantity = models.PositiveIntegerField("Количество", default=1)
    price = models.PositiveIntegerField("Цена за единицу")
    payment_type = models.CharField(
        "Тип оплаты",
        max_length=20,
        choices=[
            ('purchase', 'Покупка'),
            ('installment12', 'Рассрочка на 12 месяцев'),
            ('installment24', 'Рассрочка на 24 месяцев'),
        ],
        default='purchase'
    )
    
    class Meta:
        verbose_name = "Товар в заявке"
        verbose_name_plural = "Товары в заявке"
    
    def __str__(self):
        variant_str = f" ({self.variant.get_color_display()})" if self.variant else ""
        return f"{self.product.name}{variant_str} x{self.quantity} в заявке #{self.order.id}"

    def get_price(self):
        """Возвращает сохранённую цену за единицу на момент добавления в заявку"""
        return self.price


class Order(models.Model):
    STATUS_CHOICES = [
        ("new", "Новая"),
        ("processed", "В обработке"),
        ("completed", "Выполнена"),
    ]

    # Связи с другими моделями
    locality = models.ForeignKey(
        Locality,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        verbose_name="Населенный пункт",
    )
    tariff = models.ForeignKey(
        Tariff, 
        on_delete=models.SET_NULL, 
        verbose_name="Тариф", 
        null=True, 
        blank=True
    )
    products = models.ManyToManyField(
        Product,
        through=OrderProduct,
        blank=True, 
        verbose_name="Оборудование"
    )
    services = models.ManyToManyField(
        AdditionalService, 
        blank=True, 
        verbose_name="Доп. услуги"
    )
    tv_packages = models.ManyToManyField(
        TVChannelPackage, 
        verbose_name="Пакеты ТВ-каналов", 
        blank=True
    )
    
    # Информация о клиенте
    full_name = models.CharField("ФИО", max_length=255)
    phone = models.CharField("Телефон", max_length=20)
    email = models.EmailField("Email", blank=True, null=True)
    
    # Адрес
    street = models.CharField("Улица", max_length=255, blank=True, null=True)
    house = models.CharField("Дом", max_length=20, blank=True, null=True)
    apartment = models.CharField("Квартира", max_length=10, blank=True, null=True)
    
    # Дополнительная информация
    comment = models.TextField("Комментарий", blank=True, null=True)
    status = models.CharField(
        "Статус", 
        max_length=20, 
        choices=STATUS_CHOICES, 
        default="new"
    )
    
    # Даты
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Дата обновления",
    )

    def get_products_with_details(self):
        """Возвращает продукты с их вариантами, типом оплаты и ценами рассрочки"""
        products = []
        for order_product in self.order_products.select_related('product', 'variant').all():
            product = order_product.product
            variant = order_product.variant
            details = {
                'quantity': order_product.quantity,
                'price': order_product.price,
                'payment_type': order_product.payment_type,
                'product': product,
                'variant': variant,
                'installment_12_months': product.installment_12_months if product.installment_available else None,
                'installment_24_months': product.installment_24_months if product.installment_available else None,
                'type': None,
                'specifics': None
            }
            
            # Проверяем тип продукта
            if hasattr(product, 'smart_speaker'):
                details.update({
                    'type': 'smart_speaker',
                    'specifics': product.smart_speaker
                })
            elif hasattr(product, 'camera'):
                details.update({
                    'type': 'camera',
                    'specifics': product.camera
                })
            elif hasattr(product, 'router'):
                details.update({
                    'type': 'router',
                    'specifics': product.router
                })
            elif hasattr(product, 'tvbox'):
                details.update({
                    'type': 'tvbox',
                    'specifics': product.tvbox
                })
                
            products.append(details)
        return products

    def total_products_cost(self):
        return sum(op.price * op.quantity for op in self.order_products.all())

    def total_services_cost(self):
        return sum(s.price for s in self.services.all())

    def total_cost(self):
        total = 0
        
        # Тариф
        if self.tariff:
            total += self.tariff.get_actual_price()
            total += self.tariff.connection_price  # Добавляем стоимость подключения
        
        # Оборудование
        total += self.total_products_cost()
        
        # Доп. услуги
        total += self.total_services_cost()
        
        # ТВ-пакеты
        total += sum(p.price for p in self.tv_packages.all())
        
        return total

    def mark_as_processed(self):
        self.status = "processed"
        self.save()

    def mark_as_completed(self):
        self.status = "completed"
        self.save()

    class Meta:
        verbose_name = "Заявка"
        verbose_name_plural = "Заявки"
        ordering = ['-created_at']

    def __str__(self):
        tariff_name = self.tariff.name if self.tariff else "не указан"
        return f"Заявка #{self.id} от {self.full_name} ({tariff_name})"