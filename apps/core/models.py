import logging
from django.db import models
from ckeditor.fields import RichTextField
from django.core.validators import MinValueValidator
from pytils.translit import slugify as pytils_slugify
import os
from django.core.exceptions import ValidationError
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
        max_length=20, verbose_name="Телефон", blank=True, null=True
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
        Locality,
        related_name='services',
        verbose_name="Населённые пункты",
        blank=True
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
    description = models.TextField("Описание", blank=True)
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
    description = RichTextField("Описание", blank=True)
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
        return f"{self.name} ({', '.join(loc.name for loc in self.localities.all())})"

    class Meta:
        verbose_name = "Тариф"
        verbose_name_plural = "Тарифы"
        ordering = ["name", "price"]


class Device(models.Model):
    DEVICE_TYPE_CHOICES = [
        ("router", "Роутер"),
        ("camera", "Видеокамера"),
        ("tv_box", "ТВ-приставка"),
        ("other", "Другое"),
    ]

    device_type = models.CharField(
        verbose_name="Тип устройства", max_length=20, choices=DEVICE_TYPE_CHOICES
    )
    name = models.CharField(verbose_name="Название", max_length=255)
    description = models.TextField(verbose_name="Описание", blank=True)
    price = models.IntegerField(verbose_name="Цена")
    image = models.ImageField(
        verbose_name="Изображение", upload_to="devices/", blank=True, null=True
    )
    service_types = models.ManyToManyField(
        "Service", verbose_name="Типы услуги", related_name="devices", blank=True
    )

    class Meta:
        verbose_name = "Оборудование"
        verbose_name_plural = "Оборудование"
        ordering = ["name"]

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
    BANNER_TYPES = (
        ('', 'Не выбрано'),
        ('promo', 'Акция'),
        ('new', 'Новинка'),
        ('service', 'Услуга'),
        ('offer', 'Предложение'),
    )
    title = models.CharField("Заголовок", max_length=255)
    description = models.TextField("Описание", blank=True)
    background_image = models.ImageField(
        "Фоновое изображение", upload_to="banners/backgrounds/", blank=True, null=True
    )
    button_text = models.CharField("Текст кнопки", max_length=100, default="Подробнее")
    link = models.URLField("Ссылка", blank=True)
    banner_type = models.CharField(
        "Тип баннера",
        max_length=50,
        choices=BANNER_TYPES,
        default='',
        blank=True,
        null=True
    )
    is_active = models.BooleanField("Активен", default=True)
    localities = models.ManyToManyField(
        Locality, verbose_name="Населённые пункты", related_name="banners"
    )
    order = models.PositiveIntegerField("Порядок показа", default=0)
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлён", auto_now=True)

    class Meta:
        ordering = ["order"]
        verbose_name = "Баннер"
        verbose_name_plural = "Баннеры"

    def get_banner_type_display(self):
        if self.banner_type:
            return dict(self.BANNER_TYPES).get(self.banner_type, '')
        return ''

    def get_banner_type_color(self):
        colors = {
            'promo': 'danger',
            'new': 'success',
            'service': 'primary',
            'offer': 'info',
        }
        return colors.get(self.banner_type, 'secondary')


class Document(models.Model):
    company = models.ForeignKey(
        Company,
        related_name="documents",
        on_delete=models.CASCADE,
        verbose_name="Компания",
    )
    title = models.CharField(max_length=255, verbose_name="Название документа")
    file = models.FileField(upload_to="company_documents/", verbose_name="Файл")
    thumbnail = ProcessedImageField(
        upload_to="company_documents/thumbnails/",
        processors=[ResizeToFit(300, 400)],
        format="JPEG",
        options={"quality": 80},
        blank=True,
        null=True,
        verbose_name="Превью документа",
    )
    uploaded_at = models.DateField(auto_now_add=True, verbose_name="Дата загрузки")

    class Meta:
        verbose_name = "Документ"
        verbose_name_plural = "Документы"

    def __str__(self):
        return self.title

    @property
    def extension(self):
        """Возвращает расширение файла в верхнем регистре, например PDF, DOCX."""
        return os.path.splitext(self.file.name)[1][1:].upper()

    def clean(self):
        """Валидация загружаемого файла."""
        if self.file:
            # Ограничение размера файла (10 МБ)
            if self.file.size > 10 * 1024 * 1024:
                raise ValidationError("Размер файла не должен превышать 10 МБ.")
            # Ограничение типов файлов
            allowed_extensions = (".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx")
            if not self.file.name.lower().endswith(allowed_extensions):
                raise ValidationError("Разрешены только файлы PDF, JPG и PNG.")

    def generate_thumbnail(self, request=None):
        """Генерация миниатюры для PDF и изображений."""
        try:
            if self.extension == "PDF":
                # Генерация миниатюры из первой страницы PDF
                self.file.seek(0)  # Сбрасываем указатель файла
                pages = convert_from_bytes(
                    self.file.read(), dpi=150, first_page=1, last_page=1
                )
                buffer = BytesIO()
                pages[0].save(buffer, format="JPEG")
                self.thumbnail.save(
                    f"{self.pk}_thumb.jpg", ContentFile(buffer.getvalue()), save=False
                )
            elif self.extension in ("JPG", "JPEG", "PNG"):
                # Генерация миниатюры из изображения
                self.file.seek(0)  # Сбрасываем указатель файла
                image = Image.open(self.file)
                image.thumbnail((300, 400))
                buffer = BytesIO()
                image.save(buffer, format="JPEG")
                self.thumbnail.save(
                    f"{self.pk}_thumb.jpg", ContentFile(buffer.getvalue()), save=False
                )
            elif self.extension in ("DOC", "DOCX"):
                pass
        except Exception as e:
            logger.error(f"Не удалось создать миниатюру для {self.file.name}: {e}")
            if request:
                messages.error(
                    request,
                    f"Не удалось создать миниатюру для {self.file.name}. Проверьте файл.",
                )

    def save(self, *args, request=None, **kwargs):
        """Пользовательский метод сохранения с генерацией миниатюры."""
        needs_thumbnail = (
            self.file
            and self.extension in ("PDF", "JPG", "JPEG", "PNG")
            and (not self.thumbnail or self.file != self._original_file)
        )

        super().save(*args, **kwargs)

        if needs_thumbnail:
            self.generate_thumbnail(request=request)
            super().save(*args, **kwargs)

        self._original_file = self.file
