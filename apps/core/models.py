import logging
from django.db import models
from ckeditor.fields import RichTextField
from django.core.validators import MinValueValidator
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
from django.contrib import messages

from apps.cities.models import Locality
from django.contrib.auth.models import User

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
        max_length=20, verbose_name="Телефон технической поддержки", blank=True, null=True
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
    slug = models.SlugField("Код", unique=True)
    name = models.CharField("Название услуги", max_length=100)
    description = models.TextField("Описание", blank=True, null=True)
    localities = models.ManyToManyField(
        Locality, related_name="services", verbose_name="Населённые пункты", blank=True
    )
    is_active = models.BooleanField("Активна", default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Услуга"
        verbose_name_plural = "Услуги"

    def __str__(self):
        return self.name


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
    ]

    name = models.CharField("Название канала", max_length=100)
    description = models.TextField("Описание", null=True, blank=True)
    category = models.CharField(
        "Категория",
        max_length=20,
        choices=CATEGORY_CHOICES,
        blank=True,
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
    )
    speed = models.IntegerField(
        "Скорость (Мбит/с)", null=True, blank=True, validators=[MinValueValidator(0)]
    )
    channels = models.IntegerField(
        "Количество каналов", null=True, blank=True, validators=[MinValueValidator(0)]
    )
    hd_channels = models.IntegerField(
        "Количество HD каналов",
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
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
    description = RichTextField("Описание", blank=True, null=True)
    localities = models.ManyToManyField(
        Locality,
        blank=True,
        verbose_name="Населённые пункты",
        related_name="tariffs",
    )
    slug = models.SlugField("Слаг", max_length=120, blank=True)
    is_active = models.BooleanField("Активен", default=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = pytils_slugify(self.name)
            # Ensure slug is unique
            base_slug = self.slug
            counter = 1
            while Tariff.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Тариф"
        verbose_name_plural = "Тарифы"
        ordering = ["name", "price"]


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

    name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Имя")
    phone = models.CharField(
        max_length=20, blank=True, null=True, verbose_name="Номер телефона"
    )
    content = models.TextField(verbose_name="Сообщение")
    time_create = models.DateTimeField(auto_now_add=True, verbose_name="Дата отправки")
    ip_address = models.GenericIPAddressField(
        verbose_name="IP отправителя", blank=True, null=True
    )
    user = models.ForeignKey(
        User,
        verbose_name="Пользователь",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Обратная связь"
        verbose_name_plural = "Обратная связь"
        ordering = ["-time_create"]
        db_table = "app_feedback"

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
    title = models.CharField("Заголовок", max_length=255)
    description = models.TextField("Описание", blank=True)
    background_image = models.ImageField(
        "Фоновое изображение", upload_to="banners/backgrounds/", blank=True, null=True
    )
    button_text = models.CharField(
        "Текст кнопки", blank=True, null=True, max_length=100
    )
    link = models.URLField("Ссылка", blank=True, null=True)
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
        return self.title

    class Meta:
        ordering = ["order"]
        verbose_name = "Баннер"
        verbose_name_plural = "Баннеры"

    def get_badge(self):
        """Возвращает текст бейджа или None"""
        return self.badge.strip() if self.badge else None

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
    slug = models.SlugField("Слаг", blank=True, null=True)

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

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Пакет ТВ-каналов"
        verbose_name_plural = "Пакеты ТВ-каналов"

    def get_channel_stats(self):
        channels = self.channels.all()
        hd_channels = channels.filter(is_hd=True).count()
        sd_channels = channels.count() - hd_channels
        return {"sd": sd_channels, "hd": hd_channels}

    def channel_count_display(self):
        stats = self.get_channel_stats()
        if stats["hd"] > 0:
            return f"{stats['sd']} SD + {stats['hd']} HD"
        return f"{stats['sd']} каналов"

    def has_hd_channels(self):
        return self.channels.filter(is_hd=True).exists()

    def is_only_hd(self):
        return self.channels.filter(is_hd=True).count() == self.channels.count()

    def total_channels(self):
        return self.channels.count()

    def price_display(self):
        return f"{self.price} ₽/мес."


class Order(models.Model):
    STATUS_CHOICES = [
        ("new", "Новая"),
        ("processed", "В обработке"),
        ("completed", "Выполнена"),
    ]

    locality = models.ForeignKey(
        Locality,
        on_delete=models.CASCADE,
        verbose_name="Населенный пункт",
        null=True,
    )
    tariff = models.ForeignKey(Tariff, on_delete=models.CASCADE, verbose_name="Тариф")
    equipment = models.ManyToManyField(
        "Equipment", blank=True, verbose_name="Оборудование"
    )
    services = models.ManyToManyField(
        AdditionalService, blank=True, verbose_name="Доп. услуги"
    )
    tv_packages = models.ManyToManyField(
        "TVChannelPackage", verbose_name="Пакеты ТВ-каналов", blank=True
    )
    full_name = models.CharField("ФИО", max_length=255)
    phone = models.CharField("Телефон", max_length=20)
    email = models.EmailField(blank=True, null=True)
    street = models.CharField("Улица", max_length=255)
    house = models.CharField("Дом", max_length=20)
    apartment = models.CharField("Квартира", max_length=10, blank=True, null=True)
    comment = models.TextField("Комментарий", blank=True, null=True)
    status = models.CharField(
        "Статус", max_length=20, choices=STATUS_CHOICES, default="new"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def total_equipment_cost(self):
        return sum(eq.price for eq in self.equipment.all())

    def total_services_cost(self):
        return sum(s.price for s in self.services.all())

    def total_cost(self):
        equipment_cost = sum(eq.price for eq in self.equipment.all())
        services_cost = sum(s.price for s in self.services.all())
        tariff_price = self.tariff.price if self.tariff else 0
        return equipment_cost + services_cost + tariff_price

    def mark_as_processed(self):
        self.status = "processed"
        self.save()

    def mark_as_completed(self):
        self.status = "completed"
        self.save()

    class Meta:
        verbose_name = "Заявка"
        verbose_name_plural = "Заявки"

    def __str__(self):
        return f"Заявка от {self.full_name} на тариф {self.tariff.name}"


class StaticPage(models.Model):
    title = models.CharField("Заголовок", max_length=200)
    slug = models.SlugField("URL-адрес", unique=True)
    content = RichTextField("Содержимое")

    class Meta:
        verbose_name = "Статическая страница"
        verbose_name_plural = "Статические страницы"

    def __str__(self):
        return self.title


