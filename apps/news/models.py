from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from ckeditor.fields import RichTextField

from ..cities.models import Locality


class News(models.Model):
    title = models.CharField(max_length=200, verbose_name="Заголовок")
    slug = models.SlugField(unique=True, verbose_name="URL")
    content = RichTextField(verbose_name="Содержание")
    image = models.ImageField(
        upload_to="news/", null=True, blank=True, verbose_name="Изображение"
    )
    is_published = models.BooleanField(default=True, verbose_name="Опубликовано")
    localities = models.ManyToManyField(Locality, related_name="news")
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
        locality = (
            self.localities.filter(is_active=True).first() or self.localities.first()
        )
        return reverse(
            "news:news_detail",
            kwargs={"locality_slug": locality.slug, "news_slug": self.slug},
        )
