from django.db import models


class City(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название города")
    name_prepositional = models.CharField(
        max_length=100, verbose_name="Название в предложном падеже"
    )
    slug = models.SlugField(unique=True, verbose_name="URL")
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    class Meta:
        ordering = ["name"]
        verbose_name = "Город"
        verbose_name_plural = "Города"

    def __str__(self):
        return self.name
