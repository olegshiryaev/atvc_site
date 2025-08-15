from django.db import models
from django.conf import settings
from django.contrib.sessions.models import Session
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.forms import ValidationError
from apps.equipments.models import Product, ProductItem
from django.core.validators import MinValueValidator
from apps.core.models import Locality, Tariff, TVChannelPackage, AdditionalService

class OrderProduct(models.Model):
    order = models.ForeignKey(
        'Order',
        on_delete=models.CASCADE,
        related_name='order_products',
        verbose_name="Заявка"
    )
    product_item = models.ForeignKey(
        ProductItem,
        on_delete=models.CASCADE,
        verbose_name="Товарная позиция"
    )
    quantity = models.PositiveIntegerField(
        "Количество",
        default=1,
        validators=[MinValueValidator(1)]
    )
    price = models.PositiveIntegerField(
        "Цена за единицу",
        validators=[MinValueValidator(0)]
    )
    payment_type = models.CharField(
        "Тип оплаты",
        max_length=20,
        choices=[
            ('purchase', 'Покупка'),
            ('installment12', 'Рассрочка на 12 месяцев'),
            ('installment24', 'Рассрочка на 24 месяцев'),
            ('installment48', 'Рассрочка на 48 месяцев'),
        ],
        default='purchase'
    )

    class Meta:
        verbose_name = "Товар в заявке"
        verbose_name_plural = "Товары в заявке"
        constraints = [
            models.UniqueConstraint(
                fields=['order', 'product_item'],
                name='unique_order_product_item'
            )
        ]

    def __str__(self):
        return f"{self.product_item.get_display_name()} x{self.quantity} в заявке #{self.order.id}"

    def get_price(self):
        """Возвращает сохранённую цену за единицу на момент добавления в заявку"""
        return self.price

    def get_total_price(self):
        """Возвращает общую стоимость с учётом количества и типа оплаты"""
        if self.payment_type.startswith('installment'):
            months = int(self.payment_type.replace('installment', ''))
            installment_price = self.product_item.get_installment_price(months)
            return installment_price * self.quantity * months if installment_price else self.price * self.quantity
        return self.price * self.quantity

    def clean(self):
        """Валидация типа оплаты относительно доступности рассрочки"""
        if self.payment_type != 'purchase' and not self.product_item.installment_available:
            raise ValidationError(f"Рассрочка недоступна для {self.product_item.get_display_name()}")
        months = {'installment12': 12, 'installment24': 24, 'installment48': 48}
        if self.payment_type in months:
            installment_price = self.product_item.get_installment_price(months[self.payment_type])
            if not installment_price:
                raise ValidationError(f"Рассрочка на {months[self.payment_type]} месяцев не настроена")
        super().clean()


class Order(models.Model):
    STATUS_CHOICES = [
        ("new", "Новая"),
        ("processed", "В обработке"),
        ("completed", "Выполнена"),
    ]

    locality = models.ForeignKey(
        Locality,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        verbose_name="Населенный пункт",
    )
    tariffs = models.ManyToManyField(
        Tariff,
        verbose_name="Тарифы",
        related_name="orders",
        blank=True
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

    full_name = models.CharField("ФИО", max_length=255)
    phone = models.CharField("Телефон", max_length=20)
    email = models.EmailField("Email", blank=True, null=True)
    street = models.CharField("Улица", max_length=255, blank=True, null=True)
    house = models.CharField("Дом", max_length=20, blank=True, null=True)
    apartment = models.CharField("Квартира", max_length=10, blank=True, null=True)
    comment = models.TextField("Комментарий", blank=True, null=True)
    status = models.CharField(
        "Статус", 
        max_length=20, 
        choices=STATUS_CHOICES, 
        default="new"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    def get_products_with_details(self):
        """Возвращает товары с их позициями, типом оплаты и ценами рассрочки"""
        products = []
        for order_product in self.order_products.select_related('product_item__product', 'product_item__color').all():
            product_item = order_product.product_item
            product = product_item.product
            details = {
                'quantity': order_product.quantity,
                'price': order_product.price,
                'payment_type': order_product.payment_type,
                'product': product,
                'product_item': product_item,
                'installment_12_months': product_item.installment_12_months if product_item.installment_available else None,
                'installment_24_months': product_item.installment_24_months if product_item.installment_available else None,
                'installment_48_months': product_item.installment_48_months if product_item.installment_available else None,
                'type': None,
                'specifics': None
            }

            if hasattr(product, 'smart_speaker'):
                details.update({'type': 'smart_speaker', 'specifics': product.smart_speaker})
            elif hasattr(product, 'camera'):
                details.update({'type': 'camera', 'specifics': product.camera})
            elif hasattr(product, 'router'):
                details.update({'type': 'router', 'specifics': product.router})
            elif hasattr(product, 'tvbox'):
                details.update({'type': 'tvbox', 'specifics': product.tvbox})

            products.append(details)
        return products
    
    def get_tariff_display(self):
        """
        Возвращает строку с названиями тарифов через ' + '
        Пример: "Интернет 100 Мбит + ТВ Премиум"
        """
        names = self.tariffs.values_list('name', flat=True)
        return " + ".join(names) if names else "не указаны"

    def total_products_cost(self):
        """Возвращает общую стоимость товаров с учётом рассрочки"""
        return sum(op.get_total_price() for op in self.order_products.all())

    def total_services_cost(self):
        return sum(s.price for s in self.services.all())

    def total_cost(self):
        """
        Возвращает общую стоимость заявки: 
        сумма абонплаты и подключения по всем тарифам + оборудование + услуги + ТВ-пакеты.
        """
        total = 0

        # Суммируем по всем выбранным тарифам
        for tariff in self.tariffs.all():
            total += tariff.get_actual_price()     # абонентская плата
            total += tariff.connection_price       # подключение

        # Добавляем стоимость оборудования
        total += self.total_products_cost()

        # Добавляем стоимость дополнительных услуг
        total += self.total_services_cost()

        # Добавляем стоимость ТВ-пакетов
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
        tariff_names = ", ".join(t.name for t in self.tariffs.all()[:2])
        if self.tariffs.count() > 2:
            tariff_names += f" + {self.tariffs.count() - 2} др."
        if not tariff_names:
            tariff_names = "не указаны"
        return f"Заявка #{self.id} от {self.full_name} ({tariff_names})"