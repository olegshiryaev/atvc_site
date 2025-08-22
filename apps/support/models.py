from django.db import models
from django.contrib.auth import get_user_model
from django.urls import reverse
from pytils.translit import slugify
from ckeditor.fields import RichTextField

from apps.core.models import Service

# Получаем модель пользователя
User = get_user_model()


class HelpCategory(models.Model):
    title = models.CharField(
        max_length=200,
        verbose_name="Название категории"
    )
    slug = models.SlugField(
        max_length=200,
        unique=True,
        verbose_name="URL-адрес",
        blank=True
    )
    icon = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Иконка",
        help_text="Название иконки из FontAwesome (например: wifi, tv, phone)"
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="Краткое описание"
    )
    service = models.ForeignKey(
        'core.Service',  # Укажите правильный путь
        on_delete=models.CASCADE,
        related_name='help_categories',
        verbose_name="Услуга",
        null=True,
        blank=True
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name="Порядок сортировки"
    )

    class Meta:
        verbose_name = "Категория справки"
        verbose_name_plural = "Категории справки"
        ordering = ['service', '-order', 'title']
        indexes = [
            models.Index(fields=['service', '-order', 'title']),
            models.Index(fields=['slug']),
        ]

    def __str__(self):
        return f"{self.service.name} - {self.title}" if self.service else self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.generate_unique_slug()
        super().save(*args, **kwargs)
    
    def generate_unique_slug(self):
        """Генерирует уникальный slug на основе названия категории"""
        base_slug = slugify(self.title, allow_unicode=False)
        slug = base_slug
        counter = 1
        
        # Проверяем уникальность slug
        while HelpCategory.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        return slug

    def get_absolute_url(self):
        if self.service:
            return reverse('support:category_detail', kwargs={
                'locality_slug': 'default',
                'category_slug': self.slug
            })
        return '#'


class HelpArticle(models.Model):
    """
    Модель для справочных статей.
    """
    # Статусы публикации
    STATUS_DRAFT = 'draft'
    STATUS_PUBLISHED = 'published'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Черновик'),
        (STATUS_PUBLISHED, 'Опубликовано'),
    ]

    title = models.CharField(
        max_length=300,
        verbose_name="Заголовок статьи"
    )
    slug = models.SlugField(
        max_length=300,
        unique=True,
        verbose_name="URL-адрес"
    )
    category = models.ForeignKey(
        HelpCategory,
        on_delete=models.CASCADE,
        related_name='articles',
        verbose_name="Категория"
    )
    content = RichTextField(
        verbose_name="Содержание",
        help_text="Полное содержание статьи. Используйте инструменты форматирования для оформления."
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
        verbose_name="Статус"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Дата обновления"
    )
    author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Автор"
    )
    search_keywords = models.TextField(
        blank=True,
        verbose_name="Ключевые слова",
        help_text="Через запятую: интернет, Wi-Fi, подключение, роутер"
    )
    view_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Количество просмотров"
    )
    is_popular = models.BooleanField(
        default=False,
        verbose_name="Популярная статья?",
        help_text="Отметьте, чтобы показать эту статью в блоке 'Популярные вопросы' на главной."
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name="Порядок сортировки"
    )

    class Meta:
        verbose_name = "Справочная статья"
        verbose_name_plural = "Справочные статьи"
        ordering = ['-order', '-created_at']
        indexes = [
            models.Index(fields=['-order', '-created_at']),
            models.Index(fields=['slug']),
            models.Index(fields=['is_popular']),
            models.Index(fields=['view_count']),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
            # Проверка на уникальность
            base_slug = self.slug
            counter = 1
            while HelpArticle.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

    @property
    def service(self):
        return self.category.service

    def get_absolute_url(self):
        return reverse('support:article_detail', kwargs={
            'category_slug': self.category.slug,
            'article_slug': self.slug
        })

    def increment_view_count(self):
        """Увеличивает счетчик просмотров на 1."""
        self.view_count += 1
        self.save(update_fields=['view_count'])


class ArticleFeedback(models.Model):
    article = models.ForeignKey(HelpArticle, on_delete=models.CASCADE, related_name='feedback')
    helped = models.BooleanField()  # True — помогло, False — нет
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class FAQ(models.Model):
    """
    Модель для Часто Задаваемых Вопросов (FAQ).
    """
    question = models.CharField(
        max_length=500,
        verbose_name="Вопрос"
    )
    answer = RichTextField(
        verbose_name="Ответ"
    )
    category = models.ForeignKey(
        HelpCategory,
        on_delete=models.CASCADE,
        related_name='faqs',
        verbose_name="Категория"
    )
    is_featured = models.BooleanField(
        default=False,
        verbose_name="Показывать на главной?",
        help_text="Отметьте, чтобы этот FAQ отображался в блоке 'Частые вопросы' на главной странице поддержки."
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания"
    )

    class Meta:
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"
        ordering = ['-is_featured', 'category', 'question']
        indexes = [
            models.Index(fields=['-is_featured', 'category', 'question']),
        ]

    def __str__(self):
        return self.question