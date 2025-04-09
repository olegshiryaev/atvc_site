from django.db import models

from apps.cities.models import City
from django.contrib.auth.models import User


class Office(models.Model):
    title = models.CharField(max_length=100, default="Офис обслуживания")
    image = models.ImageField(upload_to="office_images/")
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="offices")
    address = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    longitude = models.FloatField()
    latitude = models.FloatField()

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


class Tariff(models.Model):
    TARIFF_TYPES = [
        ("internet", "Интернет"),
        ("tv", "Телевидение"),
        ("combo", "Комбо"),
    ]

    TECHNOLOGY_CHOICES = [
        ("fttx", "FTTx"),
        ("pon", "PON"),
    ]

    name = models.CharField("Название", max_length=100)
    tariff_type = models.CharField("Тип", max_length=20, choices=TARIFF_TYPES)
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
