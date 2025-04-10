from django.db import models
from django.urls import reverse
from django.utils.text import slugify

from ..cities.models import City


class News(models.Model):
    title = models.CharField(max_length=200, verbose_name="Заголовок")
    slug = models.SlugField(unique=True, verbose_name="URL")
    content = models.TextField(verbose_name="Содержание")
    image = models.ImageField(
        upload_to="news/", null=True, blank=True, verbose_name="Изображение"
    )
    is_published = models.BooleanField(default=True, verbose_name="Опубликовано")
    cities = models.ManyToManyField(City, related_name="news")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата публикации")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Новость / акция"
        verbose_name_plural = "Новости и акции"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        city = self.cities.filter(is_active=True).first() or self.cities.first()
        return reverse(
            "news:news_detail", kwargs={"city_slug": city.slug, "news_slug": self.slug}
        )
