import os
import re
from django.db import models
from django.conf import settings
from django.forms import ValidationError
from django.core.validators import MinValueValidator
from django.core.validators import RegexValidator
from django.utils import timezone
from pytils.translit import slugify
from ckeditor.fields import RichTextField
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from imagekit.models import ProcessedImageField
from imagekit.processors import ResizeToFit
from django.utils.html import strip_tags
from pilkit.processors import Transpose
import uuid


class BaseModel(models.Model):
    slug = models.SlugField("URL", blank=True, max_length=100)
    created_at = models.DateTimeField("Дата создания", auto_now_add=True, null=True)
    updated_at = models.DateTimeField("Дата обновления", auto_now=True, null=True)

    def generate_unique_slug(self, base_field_value):
        """
        Генерирует уникальный slug на основе значения поля.
        """
        base_slug = slugify(base_field_value)
        if len(base_slug) > 90:
            base_slug = base_slug[:90]
        slug = base_slug
        counter = 1
        while self.__class__.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            # Учитываем длину суффикса
            max_base_len = 100 - len(str(counter)) - 1  # -1 для дефиса
            slug = f"{base_slug[:max_base_len]}-{counter}"
            counter += 1
        return slug

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.generate_unique_slug(self.name)
        super().save(*args, **kwargs)

    class Meta:
        abstract = True


# Модель цвета
class Color(BaseModel):
    name = models.CharField("Название цвета", max_length=100, unique=True)
    hex_code = models.CharField(
        "HEX-код цвета",
        max_length=7,
        blank=True,
        null=True,
        validators=[
            RegexValidator(
                regex=r'^#[0-9A-Fa-f]{6}$',
                message="HEX-код должен быть в формате #rrggbb, например #ffffff."
            )
        ],
        help_text="Например, #ffffff для белого"
    )

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.hex_code:
            self.hex_code = self.hex_code.lower()

    def save(self, *args, **kwargs):
        if self.hex_code:
            self.hex_code = self.hex_code.lower()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Цвет"
        verbose_name_plural = "Цвета"
        indexes = [
            models.Index(fields=['slug']),
        ]

# Модель категории
class Category(BaseModel):
    name = models.CharField("Название", max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        indexes = [
            models.Index(fields=['slug']),
        ]


# Модель товара
class Product(BaseModel):
    name = models.CharField("Название", max_length=255)
    description = RichTextField("Описание", blank=True, null=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        related_name="products",
        blank=True,
        null=True,
        verbose_name="Категория"
    )
    services = models.ManyToManyField(
        "core.Service",
        related_name="products",
        verbose_name="Услуги",
        blank=True
    )
    warranty = models.PositiveIntegerField(
        "Гарантия (месяцев)",
        blank=True,
        null=True,
        default=12,
        help_text="Срок гарантии в месяцах"
    )
    instruction = models.FileField(
        "Инструкция", upload_to='instructions/', blank=True, null=True,
        help_text="PDF-файл с инструкцией к товару"
    )
    is_featured = models.BooleanField(
        "Рекомендуемый товар", default=False,
        help_text="Отображать товар в разделе рекомендуемых"
    )
    is_available = models.BooleanField(
        "Отображать в каталоге", default=True,
        help_text="Если выключено, товар не отображается в списке товаров"
    )

    def __str__(self):
        return self.name or "Товар без названия"
    
    def get_display_type(self):
        if hasattr(self, 'smart_speaker'):
            return "Умная колонка"
        elif hasattr(self, 'camera'):
            return "IP-камера"
        elif hasattr(self, 'router'):
            return "Роутер"
        elif hasattr(self, 'tvbox'):
            return "ТВ-приставка"
        return None
    
    def has_description(self):
        return bool(self.description and strip_tags(self.description).strip())
    
    def clean(self):
        if self.instruction:
            ext = os.path.splitext(self.instruction.name)[1].lower()
            if ext != '.pdf':
                raise ValidationError({"instruction": "Можно загружать только PDF-файлы."})
        super().clean()

    def is_in_stock(self):
        """
        Проверяет, есть ли товар в наличии на основе остатков товарных позиций.
        """
        return self.items.filter(in_stock__gt=0).exists()

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_available']),
            models.Index(fields=['created_at']),
        ]


# Модель товарной позиции
class ProductItem(BaseModel):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Товар",
    )
    display_name = models.CharField(
        "Отображаемое название",
        max_length=300,
        default="",  # временный дефолт, будет пересчитан в миграции
        blank=False,
        null=False,
        help_text="Название, под которым товарная позиция отображается на сайте. Можно редактировать."
    )
    color = models.ForeignKey(
        Color,
        on_delete=models.SET_NULL,
        related_name="items",
        blank=True,
        null=True,
        verbose_name="Цвет",
    )
    price = models.PositiveIntegerField(
        "Цена",
        validators=[MinValueValidator(0)],
        help_text="Цена в рублях"
    )
    old_price = models.PositiveIntegerField(
        "Старая цена",
        blank=True,
        null=True,
        validators=[MinValueValidator(0)],
        help_text="Цена до скидки"
    )
    in_stock = models.PositiveIntegerField(
        "В наличии",
        default=0,
        help_text="Количество товара на складе"
    )
    article = models.CharField(
        "Артикул",
        max_length=50,
        blank=True,
        null=True,
        unique=True,
        help_text="Уникальный код товара"
    )
    installment_available = models.BooleanField("Доступна рассрочка", default=False)
    prefer_installment = models.BooleanField(
        default=False,
        verbose_name="Предпочитать рассрочку",
        help_text="Если включено, по умолчанию для этого оборудования выбирается рассрочка."
    )
    installment_12_months = models.PositiveIntegerField(
        "Ежемесячный платёж на 12 месяцев", blank=True, null=True
    )
    installment_24_months = models.PositiveIntegerField(
        "Ежемесячный платёж на 24 месяца", blank=True, null=True
    )
    installment_48_months = models.PositiveIntegerField(
        "Ежемесячный платёж на 48 месяцев", blank=True, null=True
    )

    def save(self, *args, **kwargs):
        if not self.slug and self.display_name:
            self.slug = self.generate_unique_slug(self.display_name)
        super().save(*args, **kwargs)

    def get_display_name(self):
        return self.display_name

    def __str__(self):
        return self.display_name

    def get_final_price(self):
        """
        Возвращает актуальную цену (с учётом скидки, если нужно).
        """
        return self.price

    def get_installment_price(self, months):
        if not self.installment_available:
            return None
        installment_fields = {
            12: self.installment_12_months,
            24: self.installment_24_months,
            48: self.installment_48_months,
        }
        return installment_fields.get(months)

    def get_total_installment_price(self, months):
        """
        Возвращает общую сумму выплат по рассрочке для указанного количества месяцев.
        Если рассрочка недоступна или платеж не указан, возвращает полную цену.
        """
        installment_price = self.get_installment_price(months)
        if installment_price:
            return installment_price * months
        return self.get_final_price()
    
    def get_price_display(self):
        """Возвращает строку: '1 299 ₽'"""
        return f"{self.price:,.0f} ₽".replace(',', ' ')

    def is_in_stock(self):
        """
        Проверяет наличие позиции на складе.
        """
        return self.in_stock > 0
    
    def get_main_image(self):
        """
        Возвращает основное изображение позиции.
        """
        main_image = self.images.filter(is_main=True).first()
        return main_image if main_image else self.images.first()
    
    def has_images(self):
        return self.images.exists()

    def clean(self):
        if not self.price:
            raise ValidationError("Цена обязательна для товарной позиции")

        if self.installment_available:
            if not any([
                self.installment_12_months,
                self.installment_24_months,
                self.installment_48_months,
            ]):
                raise ValidationError(
                    "Укажите хотя бы один вариант ежемесячного платежа (12, 24 или 48 месяцев), "
                    "если рассрочка доступна."
                )

        super().clean()

    class Meta:
        verbose_name = "Товарная позиция"
        verbose_name_plural = "Товарные позиции"
        ordering = ["product", "color"]
        constraints = [
            models.UniqueConstraint(fields=["product", "color"], name="unique_product_color")
        ]
        indexes = [
            models.Index(fields=['color']),
            models.Index(fields=['in_stock']),
            models.Index(fields=['slug']),
        ]

# Модель изображения
class ProductImage(models.Model):
    item = models.ForeignKey(
        ProductItem, on_delete=models.CASCADE, related_name="images", verbose_name="Товарная позиция",
        null=True
    )
    image = ProcessedImageField(
        upload_to='product_images',
        processors=[Transpose(), ResizeToFit(800, 800)],
        format='WEBP',
        options={'quality': 90},
        blank=True,
        null=True,
        verbose_name="Изображение"
    )
    is_main = models.BooleanField("Основное изображение", default=False)
    order = models.PositiveIntegerField("Порядок", default=0)

    def __str__(self):
        return f"Изображение для {self.item}"

    def save(self, *args, **kwargs):
        """
        Обновляет основное изображение и генерирует уникальное имя файла.
        """
        if self.is_main:
            self.item.images.exclude(pk=self.pk).filter(is_main=True).update(is_main=False)
        if self.image and not self.pk:
            self.image.name = self.generate_filename()
        super().save(*args, **kwargs)

    def generate_filename(self):
        """
        Генерирует уникальное имя файла в формате: product_slug-uuid.webp
        """
        ext = '.webp'
        base_name = slugify(self.item.product.slug or self.item.product.name or 'product')
        unique_id = str(uuid.uuid4())[:8]
        return f"{base_name}-{unique_id}{ext}"

    class Meta:
        ordering = ["order"]
        verbose_name = "Изображение товарной позиции"
        verbose_name_plural = "Изображения товарных позиций"
        constraints = [
            models.UniqueConstraint(
                fields=["item"],
                condition=models.Q(is_main=True),
                name="unique_main_image_per_item"
            )
        ]


class SmartSpeaker(models.Model):
    product = models.OneToOneField(
        Product,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="smart_speaker",
        verbose_name="Товар"
    )
    
    max_power = models.CharField(
        "Максимальная мощность",
        max_length=20,
        blank=True,
        null=True,
        help_text="Например: 30 Вт"
    )
    
    voice_assistant = models.CharField(
        "Голосовой помощник",
        max_length=100,
        blank=True,
        null=True,
        help_text="Например: Маруся, Алиса, Google Assistant"
    )
    
    wireless_connection = models.CharField(
        "Беспроводное соединение",
        max_length=100,
        blank=True,
        null=True,
        help_text="Например: Bluetooth, Wi-Fi"
    )
    
    power_source = models.CharField(
        "Питание",
        max_length=100,
        blank=True,
        null=True,
        help_text="Например: от сети, от батареи"
    )
    
    frequency_range = models.CharField(
        "Диапазон частот",
        max_length=100,
        blank=True,
        null=True,
        help_text="Например: 50 - 20000 Гц"
    )
    
    wifi_standard = models.CharField(
        "Стандарт Wi-Fi",
        max_length=100,
        blank=True,
        null=True,
        help_text="Например: 802.11 a/b/g/n/ac"
    )
    
    signal_noise_ratio = models.CharField(
        "Соотношение сигнал/шум",
        max_length=20,
        blank=True,
        null=True,
        help_text="Например: 80 дБ"
    )
    
    dimensions = models.CharField(
        "Размер (ШхДхВ)", 
        max_length=50, 
        blank=True, 
        null=True
    )
    
    weight = models.PositiveIntegerField(
        "Вес (г)", 
        blank=True, 
        null=True
    )

    def __str__(self):
        return f"Умная колонка: {self.product.name}"

    class Meta:
        verbose_name = "Умная колонка"
        verbose_name_plural = "Умные колонки"


class Camera(models.Model):
    product = models.OneToOneField(
        Product, on_delete=models.CASCADE, primary_key=True, related_name="camera",
        verbose_name="Товар"
    )

    # ==== Характеристики камеры ====
    STANDARD_CHOICES = [
        ("ip", "IP"),
        ("analog", "Аналоговая"),
        ("other", "Другая"),
    ]
    camera_standard = models.CharField(
        "Стандарт видеокамеры",
        max_length=10,
        choices=STANDARD_CHOICES,
        blank=True,
        null=True,
    )

    TYPE_CHOICES = [
        ("dome", "Купольная"),
        ("bullet", "Цилиндрическая"),
        ("ptz", "Поворотная"),
        ("hidden", "Скрытая"),
        ("other", "Другой тип"),
    ]
    camera_type = models.CharField(
        "Тип видеокамеры", max_length=20, choices=TYPE_CHOICES, blank=True, null=True
    )

    resolution_mp = models.FloatField("Количество мегапикселей", blank=True, null=True)
    frame_rate = models.IntegerField("Частота кадров (кадров/с)", blank=True, null=True)
    operating_temperature = models.CharField(
        "Рабочая температура", max_length=50, blank=True, null=True
    )
    dimensions = models.CharField(
        "Размер (ШхДхВ)", max_length=50, blank=True, null=True
    )
    weight = models.PositiveIntegerField("Вес (г)", blank=True, null=True)
    focal_length = models.CharField(
        "Фокусное расстояние", max_length=20, blank=True, null=True
    )
    resolution = models.CharField("Разрешение", max_length=20, blank=True, null=True)
    matrix_type = models.CharField("Тип матрицы", max_length=50, blank=True, null=True)
    viewing_angle = models.CharField(
        "Угол обзора", max_length=20, blank=True, null=True
    )

    def __str__(self):
        return f"Камера: {self.product.name}"

    class Meta:
        verbose_name = "IP-камера"
        verbose_name_plural = "IP-камеры"


class Router(models.Model):
    """
    Модель для хранения характеристик роутеров.
    Содержит информацию о скорости Wi-Fi, диапазонах, проводной скорости и стандарте Wi-Fi.
    Связана с моделью Product через OneToOneField.
    """
    product = models.OneToOneField(
        Product, on_delete=models.CASCADE, primary_key=True, related_name="router",
        verbose_name="Товар"
    )

    max_wifi_speed_2_4 = models.PositiveIntegerField(
        "Максимальная скорость Wi-Fi на частоте 2.4 ГГц (Мбит/с)",
        blank=True,
        null=True,
        validators=[MinValueValidator(1, "Скорость должна быть не менее 1 Мбит/с")]
    )
    max_wifi_speed_5 = models.PositiveIntegerField(
        "Максимальная скорость Wi-Fi на частоте 5 ГГц (Мбит/с)",
        blank=True,
        null=True,
        validators=[MinValueValidator(1, "Скорость должна быть не менее 1 Мбит/с")]
    )
    wifi_bands = models.CharField(
        "Диапазоны Wi-Fi",
        max_length=20,
        choices=[
            ("2_4", "2.4 ГГц"),
            ("5", "5 ГГц"),
            ("2_4_and_5", "2.4 и 5 ГГц"),
        ],
        blank=True,
        null=True
    )
    wired_speed = models.PositiveIntegerField(
        "Скорость передачи по проводному подключению (Мбит/с)",
        blank=True,
        null=True,
        validators=[MinValueValidator(1, "Скорость должна быть не менее 1 Мбит/с")]
    )
    wifi_standard = models.CharField(
        "Стандарт Wi-Fi",
        max_length=50,
        help_text="Например: 4 (802.11n), 5 (802.11ac), 6 (802.11ax)",
        blank=True,
        null=True
    )

    def __str__(self):
        return f"Роутер: {self.product.name}"

    class Meta:
        verbose_name = "Роутер"
        verbose_name_plural = "Роутеры"
        indexes = [
            models.Index(fields=['wifi_bands'], name='equipments_router_bands_idx'),
            models.Index(fields=['wifi_standard'], name='equipments_router_standard_idx'),
        ]


class TvBox(models.Model):
    """
    Модель для хранения характеристик ТВ-приставок.
    Содержит информацию об операционной системе, разрешении, памяти, беспроводных соединениях и интерфейсах.
    Связана с моделью Product через OneToOneField.
    """

    product = models.OneToOneField(
        Product, on_delete=models.CASCADE, primary_key=True, related_name="tvbox",
        verbose_name="Товар"
    )
    os = models.CharField(
        "Операционная система",
        max_length=100,
        default="Не указано"
    )
    max_resolution = models.CharField(
        "Максимальное разрешение",
        max_length=100,
        default="Не указано"
    )

    # Характеристики памяти
    storage_size = models.PositiveIntegerField(
        "Встроенная память (ГБ)",
        blank=True,
        null=True,
        validators=[MinValueValidator(8, "Встроенная память должна быть не менее 8 ГБ")]
    )
    ram_size = models.PositiveIntegerField(
        "Оперативная память (ГБ)",
        blank=True,
        null=True,
        validators=[MinValueValidator(1, "Оперативная память должна быть не менее 1 ГБ")]
    )

    # Беспроводное соединение
    wireless_interfaces = models.CharField(
        "Беспроводные интерфейсы",
        max_length=255,
        blank=True,
        null=True
    )
    bluetooth_version = models.CharField(
        "Версия Bluetooth",
        max_length=10,
        blank=True,
        null=True
    )
    wifi_standard = models.CharField(
        "Стандарт Wi-Fi",
        max_length=50,
        blank=True,
        null=True
    )

    # Интерфейсы и разъемы
    interfaces = models.CharField(
        "Интерфейсы",
        max_length=255,
        blank=True,
        null=True
    )
    hdmi_count = models.PositiveIntegerField(
        "Количество HDMI-разъемов",
        blank=True,
        null=True,
        validators=[MinValueValidator(1, "Количество HDMI-разъемов должно быть не менее 1")]
    )

    def __str__(self):
        return f"{self.product.name} ({self.os}, {self.max_resolution})"

    class Meta:
        verbose_name = "ТВ-приставка"
        verbose_name_plural = "ТВ-приставки"
        indexes = [
            models.Index(fields=['os']),
            models.Index(fields=['max_resolution']),
        ]


class ViewCount(models.Model):
    item = models.ForeignKey(
        "ProductItem", on_delete=models.CASCADE, related_name="views",
        verbose_name="Товарная позиция"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name="Пользователь"
    )
    session_key = models.CharField("Ключ сессии", max_length=40, blank=True, null=True)
    ip_address = models.GenericIPAddressField(verbose_name="IP адрес")
    viewed_on = models.DateTimeField(auto_now_add=True, verbose_name="Дата просмотра")

    def __str__(self):
        return f"Просмотр {self.item}"

    class Meta:
        ordering = ("-viewed_on",)
        verbose_name = "Просмотр"
        verbose_name_plural = "Просмотры"
        indexes = [
            models.Index(fields=['item']),
            models.Index(fields=['user']),
            models.Index(fields=['session_key']),
            models.Index(fields=['ip_address']),
            models.Index(fields=['viewed_on']),
        ]
