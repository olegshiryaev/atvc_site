from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from datetime import datetime
import html
from django.utils.html import strip_tags
from django.utils.text import Truncator
from ckeditor.fields import RichTextField
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError
from django.utils import timezone

from ..cities.models import Locality

def news_image_upload_to(instance, filename):
    created_at = instance.created_at or datetime.now()
    return f"news/{created_at.year}/{created_at.month}/{filename}"

def validate_image_size(value):
    max_size_mb = 5
    if value.size > max_size_mb * 1024 * 1024:
        raise ValidationError(f"Размер файла не должен превышать {max_size_mb} МБ.")


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
        upload_to=news_image_upload_to,
        null=True,
        blank=True,
        verbose_name="Изображение",
        validators=[
            FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "gif"]),
            validate_image_size,
        ],
        help_text="Загрузите изображение в формате JPG, PNG или GIF (макс. 5 МБ)",
    )
    meta_title = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Meta title",
        help_text="Если пусто, будет использован заголовок новости"
    )
    meta_description = models.TextField(
        blank=True,
        verbose_name="Meta description",
        help_text="Краткое описание для поисковых систем"
    )
    is_published = models.BooleanField(default=False, verbose_name="Опубликовано")
    publish_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Дата и время публикации",
        help_text="Новость будет опубликована в указанное время"
    )
    localities = models.ManyToManyField(
        Locality,
        related_name="news",
        verbose_name="Населённые пункты",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
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