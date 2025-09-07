from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db import models
from .models import ArticlePDF, HelpTopic, HelpArticle, ArticleFeedback, FAQ


@admin.register(ArticlePDF)
class ArticlePDFAdmin(admin.ModelAdmin):
    list_display = ('display_title', 'article', 'topic', 'display_description', 'order', 'created_at')
    list_filter = ('article', 'topic', 'created_at')
    search_fields = ('title', 'description', 'article__title', 'topic__title')
    list_editable = ('order',)
    readonly_fields = ('created_at',)
    fields = ('article', 'topic', 'pdf_file', 'title', 'description', 'order', 'created_at')
    autocomplete_fields = ('article', 'topic')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('article', 'topic')

class ArticlePDFTopicInline(admin.TabularInline):
    model = ArticlePDF
    extra = 1
    fields = ['pdf_file', 'title', 'description', 'order', 'pdf_preview']
    readonly_fields = ['pdf_preview']
    ordering = ['-order']
    verbose_name = "PDF-инструкция"
    verbose_name_plural = "PDF-инструкции"

    def pdf_preview(self, obj):
        if obj.pdf_file:
            return format_html('<a href="{}" target="_blank">Открыть PDF</a>', obj.pdf_file.url)
        return format_html('<span style="color: #999;">—</span>')
    pdf_preview.short_description = "Предпросмотр PDF"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'article':
            kwargs['queryset'] = HelpArticle.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(HelpTopic)
class HelpTopicAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'slug',
        'icon_preview',
        'is_single_topic',
        'content_preview',
        'is_popular',
        'view_count',
        'article_count',
        'pdf_count',
        'order',
        'created_at',
    )
    list_editable = ('order', 'is_single_topic', 'is_popular')
    list_filter = ('service', 'created_at', 'is_single_topic', 'is_popular')
    search_fields = ('title', 'description', 'content')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('created_at', 'updated_at')
    inlines = [ArticlePDFTopicInline]
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'icon_image', 'description', 'order', 'is_single_topic', 'is_popular', 'view_count'),
            'description': 'Загрузите изображение (рекомендуется 50×50 px, PNG или JPG).'
        }),
        ('Содержимое одиночного топика', {
            'fields': ('content',),
            'classes': ('collapse',),
            'description': 'Поле «Содержание» используется только для одиночных топиков.'
        }),
        ('Услуги', {
            'fields': ('service',),
            'description': 'Выберите услугу, с которой связана эта тема.'
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    autocomplete_fields = ('service',)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('service').prefetch_related('articles', 'pdfs')

    def article_count(self, obj):
        if obj.is_single_topic:
            return format_html('<span style="color: #888;">Одиночный топик</span>')
        count = obj.articles.count()
        url = reverse('admin:support_helparticle_changelist') + f'?topic__id={obj.id}'
        return format_html('<a href="{}">{} статей</a>', url, count)
    article_count.short_description = "Статей"

    def pdf_count(self, obj):
        count = obj.pdfs.count()
        if count > 0:
            url = reverse('admin:support_articlepdf_changelist') + f'?topic__id={obj.id}'
            return format_html('<a href="{}">{} PDF</a>', url, count)
        return format_html('<span style="color: #999;">—</span>')
    pdf_count.short_description = "PDF-файлы"

    def content_preview(self, obj):
        if obj.is_single_topic:
            return format_html(
                '<span style="color: #2ecc71;">Заполнено</span>' if obj.content
                else '<span style="color: #e74c3c;">Пусто</span>'
            )
        return format_html('<span style="color: #888;">—</span>')
    content_preview.short_description = "Содержание"

    def icon_preview(self, obj):
        if obj.icon_image:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; object-fit: contain; '
                'background: #f8fafc; border: 1px solid #e2e8f0; padding: 8px; display: block;">',
                obj.icon_image.url
            )
        return format_html(
            '<div style="width:50px; height:50px; background:#f0f0f0; display:flex; '
            'align-items:center; justify-content:center; border:1px solid #ddd; font-size:12px; color:#999;">Нет</div>'
        )
    icon_preview.short_description = "Иконка"
    icon_preview.allow_tags = True

    def save_model(self, request, obj, form, change):
        obj.clean()
        super().save_model(request, obj, form, change)


class ArticlePDFInline(admin.TabularInline):
    model = ArticlePDF
    extra = 1
    fields = ['pdf_file', 'title', 'description', 'order', 'pdf_preview']
    readonly_fields = ['pdf_preview']
    ordering = ['-order']
    verbose_name = "PDF-инструкция"
    verbose_name_plural = "PDF-инструкции"

    def pdf_preview(self, obj):
        if obj.pdf_file:
            return format_html('<a href="{}" target="_blank">Открыть PDF</a>', obj.pdf_file.url)
        return format_html('<span style="color: #999;">—</span>')
    pdf_preview.short_description = "Предпросмотр PDF"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'topic':
            kwargs['queryset'] = HelpTopic.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(HelpArticle)
class HelpArticleAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'topic',
        'status',
        'author',
        'view_count',
        'is_popular',
        'has_image_badge',
        'pdf_count',
        'order',
        'created_at',
    )
    list_filter = ('status', 'is_popular', 'topic', 'created_at', 'author')
    search_fields = ('title', 'content', 'search_keywords')
    list_editable = ('status', 'is_popular', 'order')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('created_at', 'updated_at', 'view_count', 'has_image_preview')
    autocomplete_fields = ('topic', 'author')
    inlines = [ArticlePDFInline]
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'topic', 'content', 'image')
        }),
        ('Миниатюра', {
            'fields': ('has_image_preview',),
            'classes': ('collapse',),
            'description': 'Предпросмотр загруженной миниатюры.'
        }),
        ('Публикация', {
            'fields': ('status', 'author', 'is_popular', 'order'),
        }),
        ('Мета-информация', {
            'fields': ('search_keywords',),
            'classes': ('collapse',),
            'description': 'Ключевые слова для поиска (через запятую или пробел).'
        }),
        ('Статистика', {
            'fields': ('view_count', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('topic', 'author').prefetch_related('pdfs')

    def has_image_preview(self, obj):
        if obj.image:
            return format_html(
                '<div style="margin: 10px 0;"><img src="{}" style="max-height: 200px; max-width: 100%; border-radius: 8px;" /></div>',
                obj.image.url
            )
        return format_html('<p>Нет изображения</p>')
    has_image_preview.short_description = "Предпросмотр миниатюры"

    def has_image_badge(self, obj):
        if obj.image:
            return format_html('<span style="color: green;">✅ Есть</span>')
        return format_html('<span style="color: #999;">—</span>')
    has_image_badge.short_description = "Изображение"

    def pdf_count(self, obj):
        count = obj.pdfs.count()
        if count > 0:
            url = reverse('admin:support_articlepdf_changelist') + f'?article__id={obj.id}'
            return format_html('<a href="{}">{} PDF</a>', url, count)
        return format_html('<span style="color: #999;">—</span>')
    pdf_count.short_description = "PDF-файлы"

    def save_model(self, request, obj, form, change):
        if not obj.author and request.user.has_perm('support.add_helparticle'):
            obj.author = request.user
        super().save_model(request, obj, form, change)


@admin.register(ArticleFeedback)
class ArticleFeedbackAdmin(admin.ModelAdmin):
    list_display = (
        'article_title',
        'helped',
        'session_id_preview',
        'created_at'
    )

    list_filter = (
        'helped',
        'created_at',
        'article__topic__service',
        'article__topic',
    )

    search_fields = (
        'article__title',
        'session_id',
        'article__topic__title',
        'article__topic__service__name'
    )

    readonly_fields = (
        'article',
        'helped',
        'session_id',
        'created_at'
    )

    fieldsets = (
        ('Статья', {
            'fields': ('article',)
        }),
        ('Оценка', {
            'fields': ('helped',)
        }),
        ('Анонимная сессия', {
            'fields': ('session_id',),
            'description': 'Идентификатор браузера. Используется для предотвращения повторных голосов.'
        }),
        ('Дата', {
            'fields': ('created_at',)
        }),
    )

    ordering = ['-created_at']

    def has_add_permission(self, request):
        return False  # Только чтение

    def has_delete_permission(self, request, obj=None):
        return True  # Можно удалять при необходимости

    def article_title(self, obj):
        return obj.article.title

    article_title.short_description = "Статья"
    article_title.admin_order_field = 'article__title'

    def session_id_preview(self, obj):
        truncated = obj.session_id[:15] + "..." if len(obj.session_id) > 15 else obj.session_id
        return format_html(
            '<span title="{}" style="font-family: monospace; font-size: 0.9em;">{}</span>',
            obj.session_id,
            truncated
        )

    session_id_preview.short_description = "Session ID"
    session_id_preview.admin_order_field = 'session_id'


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = (
        'question_short',
        'service',
        'category_display',
        'order',
        'is_featured',
        'created_at'
    )
    list_filter = (
        'service',
        'is_featured',
        'category'
    )
    search_fields = ('question', 'answer')
    list_editable = ('order', 'is_featured')
    autocomplete_fields = ('service',)
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (None, {
            'fields': ('question', 'answer', 'service'),
            'description': 'Основная информация о вопросе и ответе.'
        }),
        ('Категоризация', {
            'fields': ('category', 'order'),
            'description': 'Выберите раздел и укажите порядок отображения.'
        }),
        ('Отображение', {
            'fields': ('is_featured',),
            'description': 'Отметьте, чтобы вопрос отображался в блоке "Популярные вопросы" на главной странице поддержки.'
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def category_display(self, obj):
        return dict(FAQ.CATEGORY_CHOICES).get(obj.category, obj.category)

    category_display.short_description = "Раздел"
    category_display.admin_order_field = 'category'

    def question_short(self, obj):
        return obj.question[:70] + "..." if len(obj.question) > 70 else obj.question

    question_short.short_description = "Вопрос"