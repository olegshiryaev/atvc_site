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
                message="HEX-код должен быть в формате #RRGGBB, например #FFFFFF."
            )
        ],
        help_text="Например, #FFFFFF для белого"
    )

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()

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
        help_text="Уникальный код товара"
    )
    installment_available = models.BooleanField("Доступна рассрочка", default=False)
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
        if not self.slug:
            # Генерируем slug на основе товара + цвета
            base_value = f"{self.product.name} {self.color.name}" if self.color else self.product.name
            self.slug = self.generate_unique_slug(base_value)
        super().save(*args, **kwargs)

    def get_display_name(self):
        base_name = self.product.name
        product_type = self.product.get_display_type()

        if product_type:
            full_name = f"{product_type} {base_name}"
        else:
            full_name = base_name

        if self.color:
            color_name = self.color.name.strip()
            color_name_lower = color_name[0].lower() + color_name[1:] if color_name else ""
            full_name += f", {color_name_lower}"

        return full_name

    def __str__(self):
        return self.get_display_name()

    def get_final_price(self):
        """
        Возвращает актуальную цену (с учётом скидки, если нужно).
        """
        return self.price

    def get_installment_price(self, months):
        """
        Возвращает ежемесячный платёж для указанного количества месяцев.
        """
        if not self.installment_available:
            return None
        if months == 12:
            return self.installment_12_months
        if months == 24:
            return self.installment_24_months
        if months == 48:
            return self.installment_48_months
        return None

    def get_total_installment_price(self, months):
        """
        Возвращает общую сумму выплат по рассрочке.
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
    product = models.OneToOneField(
        Product, on_delete=models.CASCADE, primary_key=True, related_name="router",
        verbose_name="Товар"
    )

    # ==== Основные параметры ====
    max_speed = models.PositiveIntegerField(
        "Максимальная скорость (Мбит/с)", blank=True, null=True
    )
    supports_devices = models.PositiveIntegerField(
        "Поддерживает устройств", blank=True, null=True
    )
    coverage_area = models.PositiveIntegerField(
        "Площадь покрытия (кв. м)", blank=True, null=True
    )

    BAND_CHOICES = [
        ("dual", "Двухдиапазонный"),
        ("single", "Однодиапазонный"),
        ("tri", "Трехдиапазонный"),
    ]
    bands = models.CharField(
        "Количество диапазонов",
        max_length=10,
        choices=BAND_CHOICES,
        blank=True,
        null=True,
    )

    FREQUENCY_CHOICES = [
        ("2_4", "2.4 ГГц"),
        ("5", "5 ГГц"),
        ("2_4_and_5", "2.4 и 5 ГГц"),
    ]
    frequency = models.CharField(
        "Частоты", max_length=10, choices=FREQUENCY_CHOICES, blank=True, null=True
    )

    dimensions = models.CharField(
        "Размер (ШхДхВ)", max_length=50, blank=True, null=True
    )
    weight = models.PositiveIntegerField("Вес (г)", blank=True, null=True)
    antennas_count = models.PositiveIntegerField("Антенны, шт", blank=True, null=True)
    lan_ports = models.PositiveIntegerField("LAN порты", blank=True, null=True)
    ram = models.PositiveIntegerField(
        "Объем оперативной памяти (МБ)", blank=True, null=True
    )
    supports_ipv6 = models.BooleanField("Поддержка IPv6", default=False)
    encryption = models.CharField("Шифрование", max_length=100, blank=True, null=True)

    port_speed = models.PositiveIntegerField(
        "Скорость портов (Мбит/с)", blank=True, null=True
    )

    # ==== Поля со свободным вводом ====
    management = models.CharField(
        "Управление",
        max_length=255,
        help_text="Например: Web-интерфейс, TR-069",
        blank=True,
        null=True,
    )
    vpn_support = models.CharField(
        "Поддержка VPN",
        max_length=255,
        help_text="Например: L2TP, OpenVPN клиент",
        blank=True,
        null=True,
    )
    wifi_standards = models.CharField(
        "Стандарты Wi-Fi",
        max_length=255,
        help_text="Например: a (Wi-Fi 2), ac (Wi-Fi 5)",
        blank=True,
        null=True,
    )

    def __str__(self):
        return f"Роутер: {self.product.name}"

    class Meta:
        verbose_name = "Роутер"
        verbose_name_plural = "Роутеры"


class TvBox(models.Model):
    product = models.OneToOneField(
        Product, on_delete=models.CASCADE, primary_key=True, related_name="tvbox",
        verbose_name="Товар"
    )
    ethernet = models.CharField("Ethernet", max_length=50, blank=True, null=True)
    usb_count = models.PositiveIntegerField(
        "Количество USB-портов", blank=True, null=True
    )
    os = models.CharField("Операционная система", max_length=50, blank=True, null=True)
    hdmi = models.BooleanField("HDMI", default=True)
    usb_ports = models.IntegerField("USB порты", blank=True, null=True)
    hdmi_version = models.CharField("HDMI выход", max_length=50, blank=True, null=True)
    av_output = models.BooleanField("AV выход", default=False)
    sd_card = models.BooleanField("micro SD", default=False)
    ram = models.CharField("ОЗУ", max_length=50, blank=True, null=True)
    rom = models.CharField("ПЗУ", max_length=50, blank=True, null=True)
    wifi = models.CharField("Wi-Fi", max_length=255, blank=True, null=True)
    protocols = models.TextField("Поддержка протоколов", blank=True, null=True)

    def __str__(self):
        return f"ТВ-приставка: {self.product.name}"

    class Meta:
        verbose_name = "ТВ-приставка"
        verbose_name_plural = "ТВ-приставки"


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
