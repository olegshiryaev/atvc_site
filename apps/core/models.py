import logging
from django.db import models
from ckeditor.fields import RichTextField
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.validators import RegexValidator
from pytils.translit import slugify as pytils_slugify
import os
from django.core.exceptions import ValidationError
from django.utils.functional import cached_property
from apps.core.tasks import generate_thumbnail_async
from imagekit.models import ProcessedImageField
from imagekit.processors import ResizeToFit
from pdf2image import convert_from_bytes
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile
from django.core.validators import URLValidator
from django.core.validators import FileExtensionValidator
from django.contrib import messages

from apps.cities.models import Locality
from django.contrib.auth.models import User

from apps.equipments.models import Product

logger = logging.getLogger(__name__)


class Office(models.Model):
    image = models.ImageField(upload_to="office_images/", verbose_name="Изображение")
    locality = models.ForeignKey(
        Locality,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Населённый пункт",
    )
    address = models.CharField(max_length=200, verbose_name="Адрес")
    phone = models.CharField(
        max_length=20, verbose_name="Основной телефон", blank=True, null=True
    )
    connection_phone = models.CharField(
        max_length=20, verbose_name="Телефон для подключения", blank=True, null=True
    )
    tech_support_phone = models.CharField(
        max_length=20,
        verbose_name="Телефон технической поддержки",
        blank=True,
        null=True,
    )
    tech_support_email = models.EmailField(
        verbose_name="Email технической поддержки", blank=True, null=True
    )
    latitude = models.CharField(
        max_length=50, verbose_name="Широта", blank=True, null=True
    )
    longitude = models.CharField(
        max_length=50, verbose_name="Долгота", blank=True, null=True
    )

    def __str__(self):
        return f"{self.locality} - {self.address}"

    class Meta:
        verbose_name = "Офис"
        verbose_name_plural = "Офисы"


class WorkSchedule(models.Model):
    DAYS_CHOICES = (
        ("Пн", "Понедельник"),
        ("Вт", "Вторник"),
        ("Ср", "Среда"),
        ("Чт", "Четверг"),
        ("Пт", "Пятница"),
        ("Сб", "Суббота"),
        ("Вс", "Воскресенье"),
        ("Сб-Вс", "Сб-Вс"),
        ("Пн-Чт", "Пн-Чт"),
        ("Пн-Пт", "Пн-Пт"),
    )

    office = models.ForeignKey(
        Office, on_delete=models.CASCADE, related_name="schedules"
    )
    days = models.CharField(max_length=50, choices=DAYS_CHOICES)
    start_time = models.TimeField(null=True, blank=True)  # Время начала работы
    end_time = models.TimeField(null=True, blank=True)  # Время окончания работы
    is_closed = models.BooleanField(default=False)  # Флаг выходного дня

    def __str__(self):
        if self.is_closed:
            return f"{self.days}: выходной"
        return f"{self.days}: {self.start_time} - {self.end_time}"

    class Meta:
        verbose_name = "Расписание работы"
        verbose_name_plural = "Расписания работы"


class Service(models.Model):
    name = models.CharField("Название услуги", max_length=100)
    description = models.TextField("Описание", blank=True, null=True)
    localities = models.ManyToManyField(
        Locality, related_name="services", verbose_name="Населённые пункты", blank=True
    )
    background_image = models.ImageField(
        "Изображение", upload_to="services/", blank=True, null=True
    )
    slug = models.SlugField("URL-адрес", unique=True)
    is_active = models.BooleanField("Активна", default=True)
    created_at = models.DateTimeField("Дата создания", auto_now_add=True, null=True)
    updated_at = models.DateTimeField("Дата обновления", auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Услуга"
        verbose_name_plural = "Услуги"

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = pytils_slugify(self.name)
        super().save(*args, **kwargs)


def channel_logo_upload_to(instance, filename):
    ext = os.path.splitext(filename)[1]
    filename = f"{pytils_slugify(instance.name)}{ext}"
    return os.path.join("channel_logos", filename)


def tv_package_image_upload_to(instance, filename):
    ext = os.path.splitext(filename)[1]
    filename = f"{pytils_slugify(instance.name)}{ext}"
    return os.path.join("tv_packages", filename)


class TVChannel(models.Model):
    CATEGORY_CHOICES = [
        ("broadcast", "Эфирные"),
        ("education", "Познавательные"),
        ("entertainment", "Развлекательные"),
        ("kids", "Детям"),
        ("movie", "Кино"),
        ("music", "Музыка"),
        ("news", "Бизнес, новости"),
        ("sport", "Спорт"),
        ("other", "Другое"),
    ]

    name = models.CharField("Название канала", max_length=100)
    description = models.TextField("Описание", null=True, blank=True)
    category = models.CharField(
        "Категория",
        max_length=20,
        choices=CATEGORY_CHOICES,
        default="other",
    )
    is_hd = models.BooleanField("HD качество", default=False)
    logo = models.ImageField(
        "Логотип канала",
        upload_to=channel_logo_upload_to,
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "ТВ канал"
        verbose_name_plural = "ТВ каналы"
        ordering = ["name"]


class Tariff(models.Model):
    """Модель для хранения информации о тарифах"""
    TECHNOLOGY_CHOICES = [
        ("fttx", "FTTx"),
        ("pon", "PON"),
    ]

    name = models.CharField("Название", max_length=100)
    service = models.ForeignKey(
        "Service",
        on_delete=models.CASCADE,
        verbose_name="Тип услуги",
        related_name="tariffs",
    )
    technology = models.CharField(
        "Технология подключения",
        max_length=20,
        choices=TECHNOLOGY_CHOICES,
        blank=True,
        null=True
    )
    speed = models.IntegerField(
        "Скорость (Мбит/с)", null=True, blank=True, validators=[MinValueValidator(0)]
    )
    included_channels = models.ManyToManyField(
        TVChannel,
        verbose_name="Включённые ТВ каналы",
        related_name="tariffs",
        blank=True,
    )
    price = models.IntegerField("Цена (руб/мес)", validators=[MinValueValidator(0)])
    connection_price = models.PositiveIntegerField(
        "Стоимость подключения (₽)", default=200
    )
    is_featured = models.BooleanField("Хит", default=False)
    is_promo = models.BooleanField("Акция", default=False)
    promo_price = models.PositiveIntegerField("Промо-цена (₽)", null=True, blank=True)
    promo_months = models.PositiveSmallIntegerField(
        "Месяцев по акции", null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(24)]
    )
    description = RichTextField("Описание", null=True, blank=True)
    localities = models.ManyToManyField(
        Locality,
        blank=True,
        verbose_name="Населённые пункты",
        related_name="tariffs",
    )
    products = models.ManyToManyField(
        Product,
        verbose_name="Оборудование для тарифа",
        related_name="tariffs",
        blank=True
    )
    slug = models.SlugField("URL-адрес", max_length=120, blank=True, unique=True)
    priority = models.PositiveSmallIntegerField(
        "Приоритет отображения", 
        default=0,
        help_text="Чем выше число, тем выше тариф в списке"
    )
    is_active = models.BooleanField("Активен", default=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = pytils_slugify(self.name)
            self.slug = base_slug
            
            # Проверяем уникальность и добавляем суффикс если нужно
            counter = 1
            while Tariff.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1
        else:
            # Если slug задан вручную, тоже проверяем уникальность
            base_slug = self.slug
            counter = 1
            while Tariff.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1
                
        super().save(*args, **kwargs)

    def get_actual_price(self):
        """Текущая цена с учётом акции"""
        if self.is_promo and self.promo_price and self.promo_months:
            return self.promo_price
        return self.price
    
    def get_discount_percent(self):
        if self.is_promo and self.promo_price and self.price > 0:
            return ((self.price - self.promo_price) / self.price) * 100
        return 0
    
    @property
    def total_channels(self):
        """Общее количество каналов"""
        return self.included_channels.count()

    @property
    def total_hd_channels(self):
        """Количество HD-каналов"""
        return self.included_channels.filter(is_hd=True).count()

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Тариф"
        verbose_name_plural = "Тарифы"
        ordering = ["-priority", "name", "price"]


def equipment_image_upload_to(instance, filename):
    return f"devices/{instance.equipment_type}/{filename}"


class Equipment(models.Model):
    EQUIPMENT_TYPE_CHOICES = [
        ("router", "Роутер"),
        ("camera", "Видеокамера"),
        ("tv_box", "ТВ-приставка"),
        ("other", "Другое"),
    ]

    equipment_type = models.CharField(
        verbose_name="Тип устройства", max_length=20, choices=EQUIPMENT_TYPE_CHOICES
    )
    name = models.CharField(verbose_name="Название", max_length=255)
    description = RichTextField(verbose_name="Описание", blank=True, null=True)
    price = models.IntegerField(verbose_name="Цена")
    image = models.ImageField(
        verbose_name="Изображение",
        upload_to=equipment_image_upload_to,
        blank=True,
        null=True,
    )
    service_types = models.ManyToManyField(
        "Service", verbose_name="Типы услуги", related_name="devices", blank=True
    )

    class Meta:
        verbose_name = "Оборудование"
        verbose_name_plural = "Оборудование"
        ordering = ["name"]
        unique_together = ["equipment_type", "name"]

    def __str__(self):
        return self.name


class Application(models.Model):
    STATUSES = (
        ("new", "Новая"),
        ("in_progress", "В обработке"),
        ("completed", "Завершена"),
    )

    locality = models.ForeignKey(
        Locality,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Населённый пункт",
    )
    name = models.CharField(max_length=100, verbose_name="Имя")
    phone = models.CharField(max_length=20, verbose_name="Телефон")
    street = models.CharField(max_length=200, blank=True, verbose_name="Улица")
    house_number = models.CharField(
        max_length=50, blank=True, verbose_name="Номер дома"
    )
    comment = models.TextField(blank=True, verbose_name="Комментарий")
    status = models.CharField(
        max_length=20, choices=STATUSES, default="new", verbose_name="Статус заявки"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    def __str__(self):
        locality_name = (
            self.locality.name if self.locality else "без населённого пункта"
        )
        return f"Заявка #{self.id} от {self.name} ({locality_name})"

    class Meta:
        verbose_name = "Заявка"
        verbose_name_plural = "Заявки"


class Feedback(models.Model):
    """
    Модель обратной связи
    """
    STATUS_CHOICES = (
        ('new', 'Новая'),
        ('in_progress', 'В обработке'),
        ('resolved', 'Решена'),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new', verbose_name="Статус")
    name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Имя")
    phone = models.CharField(
        max_length=20, blank=True, null=True,
        verbose_name="Номер телефона",
    )
    content = models.TextField(verbose_name="Сообщение", blank=True, null=True)
    time_create = models.DateTimeField(auto_now_add=True, verbose_name="Дата отправки")
    ip_address = models.GenericIPAddressField(
        verbose_name="IP отправителя", blank=True, null=True
    )

    class Meta:
        verbose_name = "Обратная связь"
        verbose_name_plural = "Обратная связь"
        ordering = ["-time_create"]
        indexes = [
            models.Index(fields=['time_create']),
            models.Index(fields=['phone']),
        ]

    def __str__(self):
        return f"Сообщение от {self.phone}"


class Company(models.Model):
    # Основные наименования
    full_name = models.CharField(
        max_length=255, verbose_name="Полное наименование", blank=True, null=True
    )
    short_name = models.CharField(
        max_length=100, verbose_name="Сокращенное наименование", blank=True, null=True
    )

    # Идентификационные номера
    inn = models.CharField(max_length=12, verbose_name="ИНН", blank=True, null=True)
    kpp = models.CharField(max_length=9, verbose_name="КПП", blank=True, null=True)
    okved = models.CharField(
        max_length=100, verbose_name="ОКВЭД", blank=True, null=True
    )
    okpo = models.CharField(max_length=10, verbose_name="ОКПО", blank=True, null=True)
    ogrn = models.CharField(max_length=13, verbose_name="ОГРН", blank=True, null=True)
    ogrn_date = models.DateField(verbose_name="Дата ОГРН", blank=True, null=True)
    okfs = models.CharField(max_length=10, verbose_name="ОКФС", blank=True, null=True)
    okogu = models.CharField(max_length=10, verbose_name="ОКОГУ", blank=True, null=True)
    okopf = models.CharField(max_length=10, verbose_name="ОКОПФ", blank=True, null=True)
    oktmo = models.CharField(max_length=10, verbose_name="ОКТМО", blank=True, null=True)

    # Адреса
    legal_address = models.CharField(
        max_length=255, verbose_name="Юридический адрес", blank=True, null=True
    )
    postal_address = models.CharField(
        max_length=255,
        verbose_name="Фактический (почтовый) адрес",
        blank=True,
        null=True,
    )

    # Контакты
    phone_fax = models.CharField(
        max_length=100, verbose_name="Телефон-факс", blank=True, null=True
    )
    email = models.EmailField(verbose_name="E-mail", blank=True, null=True)

    # Банковские реквизиты
    bank_account = models.CharField(
        max_length=20, verbose_name="Расчетный счет", blank=True, null=True
    )
    bank_name = models.CharField(
        max_length=255, verbose_name="Наименование банка", blank=True, null=True
    )
    correspondent_account = models.CharField(
        max_length=20, verbose_name="Кор/счет", blank=True, null=True
    )
    bik = models.CharField(max_length=9, verbose_name="БИК", blank=True, null=True)

    # Руководитель
    director_name = models.CharField(
        max_length=255, verbose_name="Генеральный директор", blank=True, null=True
    )
    director_basis = models.CharField(
        max_length=255, verbose_name="Действует на основании", blank=True, null=True
    )

    def __str__(self):
        return self.short_name or "Компания"

    class Meta:
        verbose_name = "Компания"
        verbose_name_plural = "Компании"


class Banner(models.Model):
    BADGE_COLOR_CHOICES = (
        ("primary", "Синий"),
        ("secondary", "Серый"),
        ("success", "Зелёный"),
        ("danger", "Красный"),
        ("warning", "Жёлтый"),
        ("info", "Голубой"),
        ("dark", "Чёрный"),
    )
    title = models.CharField("Заголовок", max_length=255, blank=True, null=True)
    description = models.TextField("Описание", blank=True)
    background_image = models.ImageField(
        "Изображение для десктопа",
        upload_to="banners/",
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])],
    )
    background_image_alt = models.CharField(
        "Альтернативный текст для изображения",
        max_length=255,
        blank=True,
        null=True,
    )
    mobile_image = models.ImageField("Изображение для мобильных", upload_to="banners/mobile/", blank=True, null=True)
    button_text = models.CharField(
        "Текст кнопки", blank=True, null=True, max_length=100
    )
    link = models.URLField(
        "Ссылка",
        blank=True,
        null=True,
        validators=[URLValidator(message="Введите корректный URL")],
    )
    badge = models.CharField("Бейдж", max_length=50, blank=True, null=True)
    badge_color = models.CharField(
        "Цвет бейджa",
        max_length=50,
        choices=BADGE_COLOR_CHOICES,
        default="primary",
        blank=True,
        null=True,
    )
    is_active = models.BooleanField("Активен", default=True)
    localities = models.ManyToManyField(
        Locality, verbose_name="Населённые пункты", related_name="banners"
    )
    order = models.PositiveIntegerField("Порядок показа", default=0)
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлён", auto_now=True)

    def __str__(self):
        return self.title if self.title else f"Баннер #{self.id}"

    class Meta:
        ordering = ["order"]
        verbose_name = "Баннер"
        verbose_name_plural = "Баннеры"

    def get_badge(self):
        """Возвращает текст бейджа или None"""
        return self.badge if self.badge else None

    def get_badge_color_display_ru(self):
        """Возвращает название цвета на русском"""
        return dict(self.BADGE_COLOR_CHOICES).get(self.badge_color, "Неизвестный цвет")

    def get_badge_color(self):
        """Возвращает CSS-класс цвета бейджа"""
        return self.badge_color if self.badge_color else "secondary"


class Document(models.Model):
    company = models.ForeignKey(
        "Company",
        related_name="documents",
        on_delete=models.CASCADE,
        verbose_name="Компания",
    )
    title = models.CharField(max_length=255, verbose_name="Название документа")
    file = models.FileField(upload_to="company_documents/", verbose_name="Файл")
    thumbnail = models.ImageField(
        upload_to="company_documents/thumbnails/",
        blank=True,
        null=True,
        verbose_name="Превью документа",
    )
    uploaded_at = models.DateField(auto_now_add=True, verbose_name="Дата загрузки")

    class Meta:
        verbose_name = "Документ"
        verbose_name_plural = "Документы"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_file = self.file

    def __str__(self):
        return self.title

    @cached_property
    def extension(self):
        return os.path.splitext(self.file.name)[1][1:].upper()

    def clean(self):
        if self.file:
            if self.file.size > 10 * 1024 * 1024:
                raise ValidationError("Размер файла не должен превышать 10 МБ.")

            # Допустимые расширения
            allowed_extensions = {
                ".pdf",
                ".jpg",
                ".jpeg",
                ".png",
                ".doc",
                ".docx",
                ".xls",
                ".xlsx",
                ".ppt",
                ".pptx",
            }
            ext = os.path.splitext(self.file.name)[1].lower()
            if ext not in allowed_extensions:
                raise ValidationError(
                    "Разрешены только файлы: PDF, JPG, PNG, DOC(X), XLS(X), PPT(X)."
                )

    def generate_thumbnail(self):
        """Генерация миниатюры для изображений и PDF"""
        try:
            if self.extension == "PDF":
                self.file.seek(0)
                pages = convert_from_bytes(
                    self.file.read(), dpi=150, first_page=1, last_page=1
                )
                image = pages[0]

            elif self.extension in ("JPG", "JPEG", "PNG"):
                self.file.seek(0)
                image = Image.open(self.file)
                image.load()
                image.thumbnail((300, 400))

            else:
                logger.warning(
                    f"Миниатюра не поддерживается для файла: {self.extension}"
                )
                return

            buffer = BytesIO()
            image.convert("RGB").save(buffer, format="JPEG", quality=80)
            thumb_name = f"{self.pk}_thumb.jpg"
            self.thumbnail.save(thumb_name, ContentFile(buffer.getvalue()), save=False)

        except Exception as e:
            logger.error(
                f"Ошибка генерации миниатюры для документа #{self.id}: {e}",
                exc_info=True,
            )

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)

        needs_thumbnail = (
            self.file
            and self.extension in ("PDF", "JPG", "JPEG", "PNG")
            and (
                not self.thumbnail
                or self.file.name != getattr(self._original_file, "name", None)
            )
        )

        if needs_thumbnail:
            # Отправляем задачу в Celery
            generate_thumbnail_async.delay(self.pk)

        self._original_file = self.file


class AdditionalService(models.Model):
    service_types = models.ManyToManyField(
        "Service",
        verbose_name="Типы услуг",
        related_name="additional_services",
        help_text="К каким базовым услугам относится эта доп. услуга",
    )
    name = models.CharField("Название услуги", max_length=200)
    price = models.PositiveIntegerField("Цена в месяц (₽)")
    description = RichTextField(verbose_name="Описание", blank=True, null=True)
    slug = models.SlugField("URL-адрес", blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = pytils_slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Дополнительная услуга"
        verbose_name_plural = "Дополнительные услуги"


class TVChannelPackage(models.Model):
    name = models.CharField("Название пакета", max_length=100)
    description = RichTextField(verbose_name="Описание", blank=True, null=True)
    price = models.PositiveIntegerField("Цена в месяц (₽)")
    image = models.ImageField(
        "Изображение",
        upload_to=tv_package_image_upload_to,
        blank=True,
        null=True,
    )
    channels = models.ManyToManyField("TVChannel", verbose_name="Каналы")
    tariffs = models.ManyToManyField(
        "Tariff", verbose_name="Тарифы", related_name="tv_packages", blank=True
    )
    slug = models.SlugField("URL-адрес", max_length=120, blank=True)

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        """Автоматически генерирует уникальный slug на основе имени пакета."""
        if not self.slug:
            base_slug = pytils_slugify(self.name)
            self.slug = base_slug
            
            # Проверяем уникальность и добавляем суффикс, если нужно
            counter = 1
            while TVChannelPackage.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1
        else:
            # Если slug задан вручную, тоже проверяем уникальность
            base_slug = self.slug
            counter = 1
            while TVChannelPackage.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1
                
        super().save(*args, **kwargs)

    def get_channel_stats(self):
        channels = self.channels.all()
        hd_channels = channels.filter(is_hd=True).count()
        sd_channels = channels.count() - hd_channels
        return {"sd": sd_channels, "hd": hd_channels}

    def channel_count_display(self):
        stats = self.get_channel_stats()
        total = stats['sd'] + stats['hd']
        
        # Логика склонения слова "канал"
        if total % 10 == 1 and total % 100 != 11:
            channel_word = "канал"
        elif total % 10 in [2, 3, 4] and total % 100 not in [12, 13, 14]:
            channel_word = "канала"
        else:
            channel_word = "каналов"
        
        return f"{total} {channel_word}"

    def has_hd_channels(self):
        return self.channels.filter(is_hd=True).exists()

    def is_only_hd(self):
        return self.channels.filter(is_hd=True).count() == self.channels.count()

    def total_channels(self):
        return self.channels.count()

    def price_display(self):
        return f"{self.price} ₽/мес"
    
    def has_category(self, category):
        return self.channels.filter(category=category).exists()
    
    def total_price_with_tariff(self, tariff):
        return tariff.get_actual_price() + self.price
    
    class Meta:
        verbose_name = "Пакет ТВ-каналов"
        verbose_name_plural = "Пакеты ТВ-каналов"
        ordering = ["name"]


class StaticPage(models.Model):
    title = models.CharField("Заголовок", max_length=200)
    slug = models.SlugField("URL-адрес", unique=True)
    content = RichTextField("Содержимое")

    class Meta:
        verbose_name = "Статическая страница"
        verbose_name_plural = "Статические страницы"

    def __str__(self):
        return self.title
