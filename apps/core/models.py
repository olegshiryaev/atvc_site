from django.db import models

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
        null=True,
    )
    technology = models.CharField(
        "Технология подключения",
        max_length=20,
        choices=TECHNOLOGY_CHOICES,
        default="fttx",
        blank=True,
    )
    speed = models.IntegerField("Скорость (Мбит/с)", null=True, blank=True)
    channels = models.IntegerField("Количество каналов", null=True, blank=True)
    price = models.IntegerField("Цена (руб/мес)")
    description = models.TextField("Описание", blank=True)
    cities = models.ManyToManyField(City, verbose_name="Города", related_name="tariffs")
    is_active = models.BooleanField("Активен", default=True)

    def __str__(self):
        return f"{self.name} ({', '.join(city.name for city in self.cities.all())})"


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

    tariff = models.ForeignKey(Tariff, on_delete=models.CASCADE, verbose_name="Тариф")
    name = models.CharField(max_length=100, verbose_name="Имя")
    phone = models.CharField(max_length=20, verbose_name="Телефон")
    address = models.TextField(verbose_name="Адрес")
    status = models.CharField(
        max_length=20, choices=STATUSES, default="new", verbose_name="Статус заявки"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    def __str__(self):
        return f"Заявка #{self.id} от {self.name} на {self.tariff.name}"


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
