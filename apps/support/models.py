from django.db import models
from django.contrib.auth import get_user_model
from django.urls import reverse
from pytils.translit import slugify
from django.utils import timezone
from django.db.models import F
from ckeditor.fields import RichTextField
from ckeditor_uploader.fields import RichTextUploadingField
from django.core.validators import FileExtensionValidator
import os

from apps.core.models import Service

# Получаем модель пользователя
User = get_user_model()


class ArticlePDF(models.Model):
    article = models.ForeignKey(
        'HelpArticle',
        on_delete=models.CASCADE,
        related_name='pdfs',
        verbose_name="Статья",
        null=True,
        blank=True,
        help_text="Статья, к которой прикреплен PDF"
    )
    topic = models.ForeignKey(
        'HelpTopic',
        on_delete=models.CASCADE,
        related_name='pdfs',
        null=True,
        blank=True,
        verbose_name="Тема",
        help_text="Тема, к которой прикреплен PDF (если применимо)"
    )
    pdf_file = models.FileField(
        upload_to='support/pdfs/%Y/%m/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])],
        verbose_name="PDF-файл",
        help_text="Загрузите PDF-инструкцию"
    )
    title = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Название PDF",
        help_text="Например: «Инструкция для ZyXel Keenetic»"
    )
    description = models.CharField(
        max_length=300,
        blank=True,
        verbose_name="Описание PDF",
        help_text="Например: «PDF, 2.1 МБ, 12 страниц»"
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name="Порядок сортировки",
        help_text="Чем выше число, тем выше PDF в списке"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания"
    )

    class Meta:
        verbose_name = "PDF-инструкция"
        verbose_name_plural = "PDF-инструкции"
        ordering = ['-order', 'title']
        indexes = [
            models.Index(fields=['article', '-order']),
            models.Index(fields=['topic', '-order']),
        ]
        constraints = [
            models.CheckConstraint(
                check=(models.Q(article__isnull=False, topic__isnull=True) |
                       models.Q(article__isnull=True, topic__isnull=False)),
                name='article_or_topic_required'
            )
        ]

    def __str__(self):
        if self.article:
            return self.title or f"PDF для статьи {self.article.title}"
        return self.title or f"PDF для темы {self.topic.title}"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        if self.article and self.topic:
            raise ValidationError("PDF может быть привязан только к статье или к теме, но не к обоим.")
        if not self.article and not self.topic:
            raise ValidationError("PDF должен быть привязан либо к статье, либо к теме.")
        if self.topic and self.topic.is_single_topic and self.article:
            raise ValidationError("Одиночный топик не может иметь PDF, привязанный через статью.")
        super().clean()

    @property
    def display_title(self):
        """Возвращает название PDF или дефолтное значение"""
        if self.title:
            return self.title
        if self.article:
            return f"Инструкция ({self.article.title})"
        return f"Инструкция ({self.topic.title})"

    @property
    def display_description(self):
        """Возвращает описание PDF или вычисляет размер файла"""
        if self.description:
            return self.description
        if self.pdf_file:
            from django.template.defaultfilters import filesizeformat
            try:
                return f"PDF, {filesizeformat(self.pdf_file.size)}"
            except:
                return "PDF"
        return ""


def help_topic_icon_upload_to(instance, filename):
    # Генерируем путь: media/help_topic_icons/service_slug/topic_slug/icon.jpg
    service_slug = instance.service.slug
    topic_slug = instance.slug or slugify(instance.title)
    ext = filename.split('.')[-1]
    filename = f"icon.{ext}"
    return f"help_topic_icons/{service_slug}/{topic_slug}/{filename}"

class HelpTopic(models.Model):
    title = models.CharField(
        max_length=200,
        verbose_name="Название темы"
    )
    slug = models.SlugField(
        max_length=200,
        unique=True,
        verbose_name="URL-адрес",
        blank=True
    )

    icon_image = models.ImageField(
        upload_to=help_topic_icon_upload_to,
        blank=True,
        null=True,
        verbose_name="Иконка",
        help_text="Загрузите изображение в формате PNG или JPG (рекомендуемый размер: 50x50 px)"
    )

    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="Краткое описание"
    )

    service = models.ForeignKey(
        'core.Service',
        on_delete=models.PROTECT,
        related_name='help_topics',
        verbose_name="Услуга"
    )

    order = models.PositiveIntegerField(
        default=0,
        verbose_name="Порядок сортировки",
        help_text="Чем выше значение, тем выше элемент в списке (по убыванию)"
    )

    is_single_topic = models.BooleanField(
        default=False,
        verbose_name="Одиночный топик?",
        help_text="Если включено — в топике будет только текст (без статей)"
    )

    content = RichTextUploadingField(
        blank=True,
        null=True,
        verbose_name="Содержание",
        help_text="Используется только если топик одиночный"
    )

    view_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Количество просмотров"
    )
    is_popular = models.BooleanField(
        default=False,
        verbose_name="Популярный топик?"
    )

    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name="Дата создания"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Дата обновления"
    )

    class Meta:
        verbose_name = "Тема справки"
        verbose_name_plural = "Темы справки"
        ordering = ['-order', 'title']
        indexes = [
            models.Index(fields=['-order', 'title']),
            models.Index(fields=['slug']),
            models.Index(fields=['service']),
        ]

    def __str__(self):
        return f"{self.title} ({self.service.name})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.generate_unique_slug()
        super().save(*args, **kwargs)

    def generate_unique_slug(self):
        base_slug = slugify(self.title)
        slug = base_slug
        counter = 1
        while HelpTopic.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        return slug

    def get_absolute_url(self, locality_slug):
        if self.is_single_topic:
            return reverse('support:topic_detail', kwargs={
                'locality_slug': locality_slug,
                'service_slug': self.service.slug,
                'topic_slug': self.slug,
            })
        return reverse('support:topic_detail', kwargs={
            'locality_slug': locality_slug,
            'service_slug': self.service.slug,
            'topic_slug': self.slug,
        })

    @property
    def get_icon_url(self):
        if self.icon_image:
            return self.icon_image.url
        return None

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.is_single_topic:
            if self.articles.exists():
                raise ValidationError("Одиночный топик не может содержать статьи.")
            if not self.content:
                raise ValidationError("У одиночного топика должно быть заполнено поле «Содержание».")
        else:
            if self.content:
                raise ValidationError("Поле «Содержание» используется только для одиночных топиков.")

    def update_view_count(self):
        HelpTopic.objects.filter(pk=self.pk).update(view_count=F('view_count') + 1)
        self.refresh_from_db(fields=["view_count"])


class HelpArticle(models.Model):
    STATUS_DRAFT = 'draft'
    STATUS_PUBLISHED = 'published'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Черновик'),
        (STATUS_PUBLISHED, 'Опубликовано'),
    ]

    title = models.CharField(max_length=300, verbose_name="Заголовок статьи")
    slug = models.SlugField(
        max_length=300,
        unique=True,
        verbose_name="URL-адрес",
        blank=True
    )
    topic = models.ForeignKey(
        HelpTopic,
        on_delete=models.PROTECT,
        related_name='articles',
        verbose_name="Тема"
    )
    content = RichTextUploadingField(verbose_name="Содержание")
    image = models.ImageField(
        upload_to='support/article_thumbnails/%Y/%m/',
        blank=True,
        null=True,
        verbose_name="Миниатюра",
        help_text="Изображение для превью статьи (например, скриншот или иконка)"
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
        verbose_name="Статус",
        help_text="Опубликовано — видно пользователям, Черновик — только в админке"
    )
    author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Автор",
        related_name='help_articles'
    )
    search_keywords = models.TextField(blank=True, verbose_name="Ключевые слова")
    view_count = models.PositiveIntegerField(default=0, verbose_name="Количество просмотров")
    is_popular = models.BooleanField(default=False, verbose_name="Популярная статья?")
    order = models.PositiveIntegerField(
        default=0,
        verbose_name="Порядок сортировки",
        help_text="Чем выше число, тем выше элемент в списке (по убыванию)"
    )
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Справочная статья"
        verbose_name_plural = "Справочные статьи"
        ordering = ['-order', '-created_at']
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["topic"]),
            models.Index(fields=["is_popular"]),
        ]

    def __str__(self):
        if self.status == self.STATUS_DRAFT:
            return f"{self.title} (Черновик)"
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.generate_unique_slug()
        super().save(*args, **kwargs)

    def generate_unique_slug(self):
        base_slug = slugify(self.title)
        slug = base_slug
        counter = 1
        while HelpArticle.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        return slug

    @property
    def service(self):
        """Возвращает услугу, связанную с темой статьи"""
        return self.topic.service

    def get_absolute_url(self, locality_slug):
        return reverse('support:article_detail', kwargs={
            'locality_slug': locality_slug,
            'service_slug': self.topic.service.slug,
            'topic_slug': self.topic.slug,
            'article_slug': self.slug
        })

    def update_view_count(self):
        HelpArticle.objects.filter(pk=self.pk).update(view_count=F('view_count') + 1)
        self.refresh_from_db(fields=["view_count"])

class ArticleFeedback(models.Model):
    article = models.ForeignKey(HelpArticle, on_delete=models.CASCADE, related_name='feedback')
    helped = models.BooleanField()
    session_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('article', 'session_id')
        indexes = [
            models.Index(fields=['session_id']),
            models.Index(fields=['created_at']),
        ]
        verbose_name = "Отзыв по статье"
        verbose_name_plural = "Отзывы по статьям"

    def __str__(self):
        return f"{self.article.title} — {'Помогло' if self.helped else 'Не помогло'}"


class FAQ(models.Model):
    """
    Модель для вопросов и ответов (FAQ).
    """

    CATEGORY_CHOICES = [
        ('connection', 'Подключение'),
        ('internet_access', 'Доступ в интернет'),
        ('traffic', 'Сетевой трафик'),
        ('email', 'Электронная почта'),
        ('general', 'Общие вопросы'),
    ]

    question = models.CharField(
        max_length=500,
        verbose_name="Вопрос"
    )
    answer = RichTextUploadingField(
        verbose_name="Ответ"
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name='faqs',
        verbose_name="Услуга"
    )
    category = models.CharField(
        max_length=20,
        verbose_name="Раздел",
        choices=CATEGORY_CHOICES,
        default='general'
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name="Порядок сортировки",
        help_text="Чем меньше значение, тем выше вопрос в списке"
    )
    is_featured = models.BooleanField(
        default=False,
        verbose_name="Показывать на главной?",
        help_text="Отметьте, чтобы этот FAQ отображался в блоке 'Популярные вопросы'."
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name="Дата создания"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Дата обновления"
    )

    class Meta:
        verbose_name = "Вопрос"
        verbose_name_plural = "Вопросы"
        ordering = ['service', 'category', 'order']
        indexes = [
            models.Index(fields=['service', 'category', 'order']),
            models.Index(fields=['is_featured']),
        ]

    def __str__(self):
        return f"[{self.get_category_display()}] {self.question[:60]}"