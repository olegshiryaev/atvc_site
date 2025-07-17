from django.db import models
from django.conf import settings
from django.utils import timezone
from pytils.translit import slugify
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType

from apps.core.models import Service


COLOR_CHOICES = [
    ("white", "Белый"),
    ("black", "Чёрный"),
    ("gray", "Серый"),
    ("other", "Другой"),
]

class Category(models.Model):
    name = models.CharField("Название категории", max_length=100)
    slug = models.SlugField("URL", unique=True, blank=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while self.__class__.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"


class Product(models.Model):
    name = models.CharField("Название", max_length=255)
    slug = models.SlugField("URL", unique=True, blank=True)
    short_description = models.CharField(
        "Краткое описание", max_length=255, blank=True, null=True
    )
    description = models.TextField("Описание", blank=True, null=True)
    price = models.PositiveIntegerField("Цена", blank=True, null=True)
    is_available = models.BooleanField("В наличии", default=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        related_name="products",
        blank=True,
        null=True,
    )
    services = models.ManyToManyField(
        Service, related_name="products", verbose_name="Услуги", blank=True
    )

    def __str__(self):
        return self.name or "Товар без названия"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while self.__class__.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_main_image(self):
        return self.images.filter(is_main=True).first()
    
    def get_price(self):
        return self.price

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images", verbose_name="Товар"
    )
    image = models.ImageField("Изображение", upload_to="product_images/")
    is_main = models.BooleanField("Основное изображение", default=False)
    color = models.CharField(
        "Цвет", max_length=10, choices=COLOR_CHOICES, blank=True, null=True
    )
    order = models.PositiveIntegerField("Порядок", default=0)

    def __str__(self):
        return f"Изображение для {self.product.name}"
    
    def save(self, *args, **kwargs):
        if self.is_main:
            self.product.images.exclude(pk=self.pk).filter(is_main=True).update(is_main=False)

    class Meta:
        ordering = ["order"]
        verbose_name = "Изображение товара"
        verbose_name_plural = "Изображения товаров"
        constraints = [
            models.UniqueConstraint(
                fields=["product"],
                condition=models.Q(is_main=True),
                name="unique_main_image_per_product"
            )
        ]


class ProductVariant(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="variants", verbose_name="Товар"
    )
    color = models.CharField("Цвет", max_length=10, choices=COLOR_CHOICES)
    sku = models.CharField("Артикул", max_length=50, blank=True, null=True)
    stock = models.PositiveIntegerField("Остаток на складе", default=0)
    price = models.PositiveIntegerField(
        "Цена", blank=True, null=True,
        help_text="Если не указано, используется цена из Product"
    )

    def __str__(self):
        return f"{self.product.name} ({self.get_color_display()})"
    
    def get_price(self):
        return self.price if self.price is not None else self.product.get_price()
    
    def save(self, *args, **kwargs):
        if self.price is None:
            self.price = self.product.price
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Вариант товара"
        verbose_name_plural = "Варианты товаров"
        constraints = [
            models.UniqueConstraint(
                fields=["product", "color"],
                name="unique_product_color"
            )
        ]


class SmartSpeaker(models.Model):
    product = models.OneToOneField(
        Product,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="smart_speaker",
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
        Product, on_delete=models.CASCADE, primary_key=True, related_name="camera"
    )

    # ==== Характеристики камеры ====
    color = models.CharField(
        "Цвет", max_length=10, choices=COLOR_CHOICES, blank=True, null=True
    )

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
        Product, on_delete=models.CASCADE, primary_key=True, related_name="router"
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

    color = models.CharField(
        "Цвет", max_length=10, choices=COLOR_CHOICES, blank=True, null=True
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
        Product, on_delete=models.CASCADE, primary_key=True, related_name="tvbox"
    )
    color = models.CharField(
        "Цвет", max_length=10, choices=COLOR_CHOICES, blank=True, null=True
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
    product = models.ForeignKey(
        "Product", on_delete=models.CASCADE, related_name="views"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True
    )
    session_key = models.CharField("Ключ сессии", max_length=40, blank=True, null=True)
    ip_address = models.GenericIPAddressField(verbose_name="IP адрес")
    viewed_on = models.DateTimeField(auto_now_add=True, verbose_name="Дата просмотра")

    def __str__(self):
        return f"Просмотр {self.product.name}"

    class Meta:
        ordering = ("-viewed_on",)
        verbose_name = "Просмотр"
        verbose_name_plural = "Просмотры"
