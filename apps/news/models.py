from django.db import models
from django.urls import reverse
from django.utils.text import slugify
import html
from django.utils.html import strip_tags
from django.utils.text import Truncator
from ckeditor.fields import RichTextField
from django.core.validators import FileExtensionValidator

from ..cities.models import Locality


class News(models.Model):
    CATEGORY_CHOICES = (
        ("news", "Новости"),
        ("promotions", "Акции"),
    )
    
    title = models.CharField(max_length=200, verbose_name="Заголовок")
    slug = models.SlugField(unique=True, verbose_name="URL")
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default="news",
        verbose_name="Категория",
        help_text="Выберите тип записи: новость или акция",
    )
    content = RichTextField(verbose_name="Содержание")
    image = models.ImageField(
        upload_to="news/",
        null=True,
        blank=True,
        verbose_name="Изображение",
        validators=[FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "gif"])],
        help_text="Загрузите изображение в формате JPG, PNG или GIF",
    )
    is_published = models.BooleanField(default=True, verbose_name="Опубликовано")
    localities = models.ManyToManyField(
        Locality,
        related_name="news",
        verbose_name="Населённые пункты",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата публикации")
    views_count = models.PositiveIntegerField(default=0, verbose_name="Количество просмотров")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Новость / акция"
        verbose_name_plural = "Новости и акции"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while News.objects.filter(slug=slug).exclude(id=self.id).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

        
    @property
    def preview_text(self):
        text = html.unescape(strip_tags(self.content))
        return Truncator(text).words(20, truncate='...')

    def get_absolute_url(self):
        locality = self.localities.filter(is_active=True).first()
        if not locality:
            locality = self.localities.first()
        return reverse(
            "news:news_detail",
            kwargs={"locality_slug": locality.slug, "news_slug": self.slug},
        )
