from django.db import models


class Region(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Регион")

    class Meta:
        ordering = ["name"]
        verbose_name = "Регион"
        verbose_name_plural = "Регионы"

    def __str__(self):
        return self.name


class District(models.Model):
    name = models.CharField(max_length=100, verbose_name="Район")
    region = models.ForeignKey(
        Region, on_delete=models.CASCADE, related_name="districts"
    )

    class Meta:
        ordering = ["name"]
        unique_together = ("name", "region")
        verbose_name = "Район"
        verbose_name_plural = "Районы"

    def __str__(self):
        return f"{self.name}, {self.region.name}"


class Locality(models.Model):
    LOCALITY_TYPES = [
        ("city", "Город"),
        ("village", "Деревня"),
        ("town", "Посёлок"),
        ("selo", "Село"),
        ("work-town", "Рабочий посёлок"),
    ]

    name = models.CharField(max_length=100, verbose_name="Населённый пункт")
    name_prepositional = models.CharField(
        max_length=100, verbose_name="Название в предложном падеже"
    )
    slug = models.SlugField(unique=True, verbose_name="URL-адрес")
    locality_type = models.CharField(
        max_length=20, choices=LOCALITY_TYPES, verbose_name="Тип"
    )
    region = models.ForeignKey(
        Region,
        on_delete=models.CASCADE,
        related_name="localities",
        verbose_name="Регион",
        null=True,
        blank=True,
    )
    district = models.ForeignKey(
        District,
        on_delete=models.SET_NULL,
        related_name="localities",
        null=True,
        blank=True,
        verbose_name="Район",
    )
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    class Meta:
        indexes = [
            models.Index(fields=["slug", "is_active"]),
        ]
        ordering = ["name"]
        unique_together = ("name", "region")
        verbose_name = "Населённый пункт"
        verbose_name_plural = "Населённые пункты"

    def __str__(self):
        return self.name
