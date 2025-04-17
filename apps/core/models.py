from django.db import models
from django.core.validators import MinValueValidator
from pytils.translit import slugify as pytils_slugify
import os

from apps.cities.models import City
from django.contrib.auth.models import User


class Office(models.Model):
    image = models.ImageField(upload_to="office_images/", verbose_name="Изображение")
    city = models.ForeignKey(
        City, on_delete=models.CASCADE, related_name="offices", verbose_name="Город"
    )
    address = models.CharField(max_length=200, verbose_name="Адрес")
    phone = models.CharField(
        max_length=20, verbose_name="Телефон", blank=True, null=True
    )
    longitude = models.CharField(
        max_length=50, verbose_name="Долгота", blank=True, null=True
    )
    latitude = models.CharField(
        max_length=50, verbose_name="Широта", blank=True, null=True
    )

    def __str__(self):
        return f"{self.city} - {self.address}"

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

    class Meta:
        verbose_name = "Тип услуги"
        verbose_name_plural = "Типы услуг"

    def __str__(self):
        return self.name
    

def channel_logo_upload_to(instance, filename):
    ext = os.path.splitext(filename)[1]
    filename = f"{pytils_slugify(instance.name)}{ext}"
    return os.path.join("channel_logos", filename)

class TVChannel(models.Model):
    CATEGORY_CHOICES = [
        ('broadcast', 'Эфирные'),
        ('education', 'Познавательные'),
        ('entertainment', 'Развлекательные'),
        ('kids', 'Детям'),
        ('movie', 'Кино'),
        ('music', 'Музыка'),
        ('news', 'Бизнес, новости'),
        ('sport', 'Спорт'),
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
    SERVICE_CHOICES = [
        ("internet", "Интернет"),
        ("tv", "Телевидение"),
        ("combo", "Комбо"),
    ]

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
    speed = models.IntegerField("Скорость (Мбит/с)", null=True, blank=True, validators=[MinValueValidator(0)])
    channels = models.IntegerField("Количество каналов", null=True, blank=True, validators=[MinValueValidator(0)])
    included_channels = models.ManyToManyField(
        TVChannel,
        verbose_name="Включённые ТВ каналы",
        related_name="tariffs",
        blank=True,
    )
    price = models.IntegerField("Цена (руб/мес)", validators=[MinValueValidator(0)])
    description = models.TextField("Описание", blank=True)
    cities = models.ManyToManyField(City, verbose_name="Города", related_name="tariffs")
    is_active = models.BooleanField("Активен", default=True)

    def __str__(self):
        return f"{self.name} ({', '.join(city.name for city in self.cities.all())})"
    
    class Meta:
        verbose_name = "Тариф"
        verbose_name_plural = "Тарифы"
        ordering = ["name", "price"]


class Device(models.Model):
    name = models.CharField(verbose_name="Название", max_length=255)
    description = models.TextField(verbose_name="Описание")
    price = models.DecimalField(verbose_name="Цена", max_digits=6, decimal_places=2)
    image = models.ImageField(verbose_name="Изображение", upload_to="devices/")
    service_types = models.ManyToManyField(
        "Service", verbose_name="Типы услуги", related_name="devices"
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

    city = models.ForeignKey(
        City, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Город"
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
        city_name = self.city.name if self.city else "без города"
        return f"Заявка #{self.id} от {self.name} ({city_name})"

    class Meta:
        verbose_name = "Заявка"
        verbose_name_plural = "Заявки"


class Feedback(models.Model):
    """
    Модель обратной связи
    """

    subject = models.CharField(max_length=255, verbose_name="Тема письма")
    email = models.EmailField(max_length=255, verbose_name="Электронный адрес (email)")
    content = models.TextField(verbose_name="Содержимое письма")
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
        return f"Вам письмо от {self.email}"


class Company(models.Model):
    # Основные наименования
    full_name = models.CharField(max_length=255, verbose_name="Полное наименование")
    short_name = models.CharField(
        max_length=100, verbose_name="Сокращенное наименование"
    )

    # Идентификационные номера
    inn = models.CharField(max_length=12, verbose_name="ИНН")
    kpp = models.CharField(max_length=9, verbose_name="КПП")
    okved = models.CharField(max_length=100, verbose_name="ОКВЭД")
    okpo = models.CharField(max_length=10, verbose_name="ОКПО")
    ogrn = models.CharField(max_length=13, verbose_name="ОГРН")
    ogrn_date = models.DateField(verbose_name="Дата ОГРН", null=True, blank=True)
    okfs = models.CharField(max_length=10, verbose_name="ОКФС")
    okogu = models.CharField(max_length=10, verbose_name="ОКОГУ")
    okopf = models.CharField(max_length=10, verbose_name="ОКОПФ")
    oktmo = models.CharField(max_length=10, verbose_name="ОКТМО")

    # Адреса
    legal_address = models.CharField(max_length=255, verbose_name="Юридический адрес")
    postal_address = models.CharField(
        max_length=255, verbose_name="Фактический (почтовый) адрес"
    )

    # Контакты
    phone_fax = models.CharField(max_length=100, verbose_name="Телефон-факс")
    email = models.EmailField(verbose_name="E-mail")

    # Банковские реквизиты
    bank_account = models.CharField(max_length=20, verbose_name="Расчетный счет")
    bank_name = models.CharField(max_length=255, verbose_name="Наименование банка")
    correspondent_account = models.CharField(max_length=20, verbose_name="Кор/счет")
    bik = models.CharField(max_length=9, verbose_name="БИК")

    # Руководитель
    director_name = models.CharField(
        max_length=255, verbose_name="Генеральный директор"
    )
    director_basis = models.CharField(
        max_length=255, verbose_name="Действует на основании"
    )

    def __str__(self):
        return self.short_name

    class Meta:
        verbose_name = "Компания"
        verbose_name_plural = "Компании"


class Banner(models.Model):
    title = models.CharField("Заголовок", max_length=255)
    description = models.TextField("Описание", blank=True)
    image = models.ImageField(
        "Изображение", upload_to="banners/", blank=True, null=True
    )
    background_image = models.ImageField(
        "Фоновое изображение", upload_to="banners/backgrounds/", blank=True, null=True
    )
    button_text = models.CharField("Текст кнопки", max_length=100, default="Подробнее")
    link = models.URLField("Ссылка", blank=True)
    is_active = models.BooleanField("Активен", default=True)
    cities = models.ManyToManyField(City, verbose_name="Города", related_name="banners")
    order = models.PositiveIntegerField("Порядок показа", default=0)

    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлён", auto_now=True)

    class Meta:
        ordering = ["order"]
        verbose_name = "Баннер"
        verbose_name_plural = "Баннеры"

    def __str__(self):
        return self.title
