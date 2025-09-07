from django.contrib import admin
import os
from django.conf import settings
from django.core.files import File
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.safestring import mark_safe
from import_export.admin import ImportExportModelAdmin
from import_export import resources, fields
from import_export import widgets
from import_export.widgets import ManyToManyWidget, ForeignKeyWidget
import csv
from django.http import HttpResponse
from django.utils.html import format_html
from import_export.widgets import BooleanWidget

from apps.cities.models import Locality
from pytils.translit import slugify as pytils_slugify
from django.db.models import Count, Q
from apps.core.forms import DocumentForm
from apps.equipments.models import ProductItem
from .models import (
    AdditionalService,
    Application,
    Banner,
    Company,
    Equipment,
    Document,
    Feedback,
    Office,
    Service,
    StaticPage,
    TVChannel,
    TVChannelPackage,
    Tariff,
    WorkSchedule,
)
import logging

logger = logging.getLogger(__name__)

# Кастомизация заголовка админки
admin.site.site_header = "Админ-панель управления сайтом"
admin.site.site_title = "Пенль управления сайтом"
admin.site.index_title = "Добро пожаловать в панель управления сайтом"

class CustomBooleanWidget(widgets.BooleanWidget):
    TRUE_VALUES = ("1", "true", "yes", "on", "Истина", "ИСТИНА", "истина")
    FALSE_VALUES = ("0", "false", "no", "off", "Ложь", "ЛОЖЬ", "ложь")

    def clean(self, value, row=None, **kwargs):
        if value is None or value == '' or value is False:
            return False

        value = str(value).strip().replace('\u00A0', ' ').lower()

        # Проверяем, есть ли значение в списке истинных (в нижнем регистре)
        if value in [v.lower() for v in self.TRUE_VALUES]:
            return True
        elif value in [v.lower() for v in self.FALSE_VALUES]:
            return False

        # Можно добавить поддержку булевых значений Python
        if isinstance(value, bool):
            return value

        raise ValidationError(f"Неизвестное значение для булевого поля: {value}")


class WorkScheduleInline(admin.TabularInline):
    model = WorkSchedule
    extra = 1


@admin.register(Office)
class OfficeAdmin(admin.ModelAdmin):
    inlines = [WorkScheduleInline]


class LocalityFilter(admin.SimpleListFilter):
    title = "Город"
    parameter_name = "locality"

    def lookups(self, request, model_admin):
        localities = Locality.objects.filter(is_active=True)
        return [(locality.id, locality.name) for locality in localities]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(localities__id=self.value())
        return queryset


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    filter_horizontal = ("localities",)
    list_display = ("name", "slug", "is_active")
    search_fields = ('name', 'description')
    prepopulated_fields = {"slug": ("name",)}
    list_filter = ('is_active', 'localities')
    fields = ('name', 'description', 'icon_image', 'background_image', 'localities', 'slug', 'is_active')
    readonly_fields = ('created_at', 'updated_at')


class CategoryWidget(widgets.Widget):
    mapping = {
        "Эфирные": "broadcast",
        "Познавательные": "education",
        "Развлекательные": "entertainment",
        "Детям": "kids",
        "Кино": "movie",
        "Музыка": "music",
        "Бизнес, новости": "news",
        "Спорт": "sport",
        "Другое": "other",
    }

    def clean(self, value, row=None, *args, **kwargs):
        if not value:
            return ""
        value = value.strip()
        if value not in self.mapping:
            raise ValueError(f"Неверная категория: {value}")
        return self.mapping[value]

    def render(self, value, obj=None, *args, **kwargs):
        reverse_mapping = {v: k for k, v in self.mapping.items()}
        return reverse_mapping.get(value, "")


class TVChannelResource(resources.ModelResource):
    name = fields.Field(column_name="Название канала", attribute="name")
    description = fields.Field(column_name="Описание", attribute="description")
    category = fields.Field(
        column_name="Категория",
        attribute="category",
        widget=CategoryWidget(),
    )
    is_hd = fields.Field(
        column_name="HD качество",
        attribute="is_hd",
        widget=CustomBooleanWidget(),
    )
    logo = fields.Field(column_name="Логотип", attribute="logo")

    def dehydrate_category_display(self, obj):
        return obj.get_category_display()

    def dehydrate_logo(self, obj):
        if obj.logo:
            # Возвращаем только имя файла без пути
            return os.path.basename(obj.logo.name)
        return ""

    class Meta:
        model = TVChannel
        fields = ("name", "description", "category", "is_hd", "logo")
        export_order = ("name", "description", "category", "is_hd", "logo")
        import_id_fields = ("name",)
        skip_unchanged = True
        report_skipped = True

    def before_save_instance(self, instance, row, **kwargs):
        logo_filename = getattr(instance, "logo", None)
        if logo_filename:
            logo_filename = str(logo_filename).strip()
            # Если имя файла уже с префиксом 'channel_logos/', используем как есть,
            # иначе добавляем префикс, чтобы проверить файл
            if not logo_filename.startswith("channel_logos/"):
                logo_filename = os.path.join("channel_logos", logo_filename)

            logo_path = os.path.join(settings.MEDIA_ROOT, logo_filename)

            if os.path.exists(logo_path):
                with open(logo_path, "rb") as f:
                    # сохраняем файл с оригинальным именем (без изменений)
                    instance.logo.save(
                        os.path.basename(logo_filename), File(f), save=False
                    )

        return super().before_save_instance(instance, row, **kwargs)


@admin.register(TVChannel)
class TVChannelAdmin(ImportExportModelAdmin):
    resource_class = TVChannelResource
    list_display = ["name", "category", "is_hd", "logo_preview"]
    list_filter = ["category", "is_hd"]
    search_fields = ["name"]
    fields = ["name", "category", "is_hd", "description", "logo"]

    def logo_preview(self, obj):
        if obj.logo:
            return mark_safe(f'<img src="{obj.logo.url}" width="50" />')
        return "-"

    logo_preview.short_description = "Логотип"


class TariffResource(resources.ModelResource):
    name = fields.Field(
        column_name="Название",
        attribute="name"
    )
    
    service = fields.Field(
        column_name="Тип услуги",
        attribute="service",
        widget=ForeignKeyWidget(Service, 'name')
    )
    
    technology = fields.Field(
        column_name="Технология подключения",
        attribute="technology"
    )
    
    speed = fields.Field(
        column_name="Скорость (Мбит/с)",
        attribute="speed"
    )
    
    included_channels = fields.Field(
        column_name="Включённые ТВ каналы",
        attribute="included_channels",
        widget=ManyToManyWidget(TVChannel, field='name', separator=',')
    )
    
    price = fields.Field(
        column_name="Цена (руб/мес)",
        attribute="price"
    )
    
    connection_price = fields.Field(
        column_name="Стоимость подключения (₽)",
        attribute="connection_price"
    )
    
    is_featured = fields.Field(
        column_name="Хит",
        attribute="is_featured"
    )
    
    is_promo = fields.Field(
        column_name="Акция",
        attribute="is_promo"
    )
    
    promo_price = fields.Field(
        column_name="Промо-цена (₽)",
        attribute="promo_price"
    )
    
    promo_months = fields.Field(
        column_name="Месяцев по акции",
        attribute="promo_months"
    )
    
    description = fields.Field(
        column_name="Описание",
        attribute="description"
    )
    
    is_active = fields.Field(
        column_name="Активен",
        attribute="is_active"
    )
    
    slug = fields.Field(
        column_name="Слаг",
        attribute="slug",
        readonly=True
    )
    
    products = fields.Field(
        column_name="Оборудование",
        attribute="products",
        widget=ManyToManyWidget(ProductItem, field='article', separator=',')
    )

    class Meta:
        model = Tariff
        fields = (
            'name',
            'service',
            'technology',
            'speed',
            'included_channels',
            'price',
            'connection_price',
            'is_featured',
            'is_promo',
            'promo_price',
            'promo_months',
            'description',
            'slug',
            'is_active',
            'products'
        )
        export_order = (
            'name',
            'service',
            'technology',
            'speed',
            'included_channels',
            'price',
            'connection_price',
            'is_featured',
            'is_promo',
            'promo_price',
            'promo_months',
            'description',
            'is_active',
            'products'
        )
        import_id_fields = ('slug',)
        skip_unchanged = True
        report_skipped = True

    def before_import_row(self, row, **kwargs):
        """Генерируем уникальный slug и валидируем оборудование перед импортом"""
        if 'Название' in row:
            name = row['Название'].strip()
            if name:
                base_slug = pytils_slugify(name)
                row['slug'] = base_slug
                counter = 1
                while Tariff.objects.filter(slug=row['slug']).exists() or self.is_slug_in_import(row['slug'], kwargs):
                    row['slug'] = f"{base_slug}-{counter}"
                    counter += 1

        if 'Оборудование' in row:
            articles = row['Оборудование'].split(',')
            for article in articles:
                article = article.strip()
                if article and not ProductItem.objects.filter(article=article).exists():
                    logger.warning(f"Товар с артикулом {article} не найден при импорте тарифа {row.get('Название', '')}")
                    raise ValueError(f"Товар с артикулом {article} не найден")

    def is_slug_in_import(self, slug, kwargs):
        """Проверяет, используется ли slug в других строках текущего импорта"""
        existing_rows = kwargs.get('existing_rows', [])
        return any(r.get('slug') == slug for r in existing_rows)

@admin.register(Tariff)
class TariffAdmin(ImportExportModelAdmin):
    resource_class = TariffResource

    list_display = (
        'name',
        'service',
        'display_price',
        'priority',
        'is_active',
        'is_featured',
        'is_promo',
        'get_channels_count',
        'get_hd_channels_count',
        'get_products_count',
        'technology_display',
        'localities_count',
        'slug',
    )

    list_filter = (
        'is_active',
        'is_featured',
        'is_promo',
        'service',
        'technology',
        'priority',
    )

    search_fields = ('name', 'description', 'slug')
    filter_horizontal = ('included_channels', 'localities', 'products')
    readonly_fields = (
        'slug',
        'get_channels_count_display',
        'get_hd_channels_count_display',
    )
    list_per_page = 30

    fieldsets = (
        ('Основная информация', {
            'fields': (
                'name',
                'slug',
                'priority',
                'service',
                'description',
                'is_active',
            )
        }),
        ('Цены', {
            'fields': (
                'price',
                'connection_price',
                'is_promo',
                'promo_price',
                'promo_months',
                'is_featured',
            )
        }),
        ('Характеристики', {
            'fields': (
                'technology',
                'speed',
                'get_channels_count_display',
                'get_hd_channels_count_display',
            )
        }),
        ('Связи', {
            'fields': (
                'included_channels',
                'localities',
                'products',
            )
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            _channels_count=Count('included_channels'),
            _hd_channels_count=Count(
                'included_channels',
                filter=Q(included_channels__is_hd=True)
            ),
            _products_count=Count('products')
        ).prefetch_related(
            'included_channels',
            'localities',
            'products__product'
        )

    # --- Методы для list_display и fieldsets ---

    def display_price(self, obj):
        """Отображение цены с акцией (в списке)"""
        if obj.is_promo and obj.promo_price:
            return format_html(
                '<span style="color: red; text-decoration: line-through;">{}₽</span> → '
                '<strong style="color: green;">{}₽</strong>',
                obj.price,
                obj.promo_price
            )
        return f"{obj.price}₽"
    display_price.short_description = 'Цена'
    display_price.admin_order_field = 'price'  # Сортируем по реальной цене

    def get_channels_count(self, obj):
        return obj._channels_count
    get_channels_count.short_description = 'Всего каналов'
    get_channels_count.admin_order_field = '_channels_count'

    def get_hd_channels_count(self, obj):
        return obj._hd_channels_count
    get_hd_channels_count.short_description = 'HD каналов'
    get_hd_channels_count.admin_order_field = '_hd_channels_count'

    def get_products_count(self, obj):
        count = obj.products.count()
        if count:
            return format_html(
                '<a href="{}?tariffs__id__exact={}">{}</a>',
                reverse('admin:equipments_productitem_changelist'),
                obj.id,
                count
            )
        return count
    get_products_count.short_description = 'Оборудование'
    get_products_count.admin_order_field = '_products_count'

    def technology_display(self, obj):
        return obj.get_technology_display()
    technology_display.short_description = 'Технология'

    def localities_count(self, obj):
        return obj.localities.count()
    localities_count.short_description = 'Локации'

    # --- Методы для формы редактирования (fieldsets) ---

    def get_channels_count_display(self, obj):
        if obj is None:
            return "-"
        return obj._channels_count
    get_channels_count_display.short_description = 'Всего каналов'
    get_channels_count_display.admin_order_field = '_channels_count'

    def get_hd_channels_count_display(self, obj):
        if obj is None:
            return "-"
        return obj._hd_channels_count
    get_hd_channels_count_display.short_description = 'HD каналов'
    get_hd_channels_count_display.admin_order_field = '_hd_channels_count'

    # --- Дополнительные действия ---

    def activate_tariffs(self, request, queryset):
        queryset.update(is_active=True)
        logger.info(f"Активировано тарифов: {queryset.count()}")
    activate_tariffs.short_description = "Активировать выбранные тарифы"

    def deactivate_tariffs(self, request, queryset):
        queryset.update(is_active=False)
        logger.info(f"Деактивировано тарифов: {queryset.count()}")
    deactivate_tariffs.short_description = "Деактивировать выбранные тарифы"

    # --- Сохранение ---

    def save_model(self, request, obj, form, change):
        logger.info(f"Сохранение тарифа: {obj.name}, slug: {obj.slug}, изменен: {change}")
        if not obj.slug:
            obj.slug = pytils_slugify(obj.name)
        super().save_model(request, obj, form, change)

    # --- Экспорт в CSV ---

    def export_as_csv(self, request, queryset):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="tariffs.csv"'
        writer = csv.writer(response)
        writer.writerow([
            "Название", "URL-адрес", "Тип", "Цена", "Скорость", 
            "Каналы", "HD Каналы", "Города", "Оборудование"
        ])

        for tariff in queryset:
            localities = ", ".join([loc.name for loc in tariff.localities.all()])
            products = ", ".join([pi.get_display_name() for pi in tariff.products.all()])
            writer.writerow([
                tariff.name,
                tariff.slug,
                tariff.get_service_display(),
                tariff.get_actual_price(),
                tariff.speed or "-",
                tariff.included_channels.count(),
                tariff.included_channels.filter(is_hd=True).count(),
                localities,
                products,
            ])
        logger.info(f"Экспортировано тарифов: {queryset.count()}")
        return response

    export_as_csv.short_description = "Экспорт в CSV"

    # --- Media ---

    class Media:
        css = {
            "all": ("fontawesome/css/all.min.css",)
        }

@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = (
        "image_thumb",
        "name",
        "equipment_type",
        "price",
        "get_service_types",
    )
    list_filter = ("equipment_type", "service_types")
    search_fields = ("name", "description")
    autocomplete_fields = ("service_types",)
    filter_horizontal = ("service_types",)
    readonly_fields = ("image_preview",)
    fieldsets = (
        (None, {"fields": ("name", "equipment_type", "price", "description")}),
        ("Изображение", {"fields": ("image", "image_preview")}),
        ("Услуги", {"fields": ("service_types",)}),
    )

    def get_service_types(self, obj):
        return ", ".join([s.name for s in obj.service_types.all()])

    get_service_types.short_description = "Типы услуги"

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 200px;" />', obj.image.url
            )
        return "Нет изображения"

    image_preview.short_description = "Превью изображения"

    def image_thumb(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height: 50px;" />', obj.image.url)
        return "—"

    image_thumb.short_description = "Фото"


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "phone",
        "locality",
        "status",
        "created_at",
        "updated_at",
    )
    list_filter = ("status", "locality", "created_at")
    search_fields = ("name", "phone", "street", "house_number", "comment")
    list_editable = ("status",)
    date_hierarchy = "created_at"
    readonly_fields = ("created_at", "updated_at")
    list_per_page = 25
    fieldsets = (
        (None, {"fields": ("name", "phone", "status")}),
        ("Адрес", {"fields": ("locality", "street", "house_number")}),
        ("Дополнительно", {"fields": ("comment",)}),
        ("Даты", {"fields": ("created_at", "updated_at")}),
    )
    ordering = ("-created_at",)
    actions = ["mark_as_in_progress", "mark_as_completed"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("locality")

    # Кастомное действие: "Пометить как в обработке"
    @admin.action(description="Пометить выбранные заявки как 'В обработке'")
    def mark_as_in_progress(self, request, queryset):
        queryset.update(status="in_progress")

    # Кастомное действие: "Пометить как завершенные"
    @admin.action(description="Пометить выбранные заявки как 'Завершена'")
    def mark_as_completed(self, request, queryset):
        queryset.update(status="completed")


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "phone",
        "short_content",
        "time_create",
        "ip_address",
    )
    list_filter = ("time_create",)
    search_fields = ("name", "phone", "content", "ip_address")
    readonly_fields = ("time_create", "ip_address")

    def short_content(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content

    short_content.short_description = "Сообщение"


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "badge",
        "badge_color",
        "is_active",
        "order",
        "localities_count",
        "updated_at",
    )
    list_editable = ("order", "is_active", "badge", "badge_color")
    list_filter = ("is_active", "badge_color")
    search_fields = ("title", "description", "badge")
    filter_horizontal = ("localities",)
    fieldsets = (
        (
            "Основная информация",
            {"fields": ("title", "description", "badge", "badge_color")},
        ),
        (
            "Кнопка и ссылка",
            {"fields": ("button_text", "link"), "classes": ("collapse",)},
        ),
        ("Изображение", {"fields": ("background_image", "mobile_image", "background_image_alt",)}),
        ("Настройки отображения", {"fields": ("is_active", "order", "localities")}),
    )
    readonly_fields = ("created_at", "updated_at")

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.prefetch_related("localities")

    @admin.display(description="Кол-во локаций")
    def localities_count(self, obj):
        return obj.localities.count()

    @admin.display(description="Цвет")
    def get_badge_color_display(self, obj):
        color_map = dict(Banner.BADGE_COLOR_CHOICES)
        return color_map.get(obj.badge_color, "—")


class DocumentInline(admin.TabularInline):
    model = Document
    fields = ("title", "file", "thumbnail_preview")
    readonly_fields = ("thumbnail_preview",)

    def thumbnail_preview(self, obj):
        if obj.thumbnail:
            return format_html(
                '<img src="{}" style="max-height:100px;" />', obj.thumbnail.url
            )
        return "-"

    thumbnail_preview.short_description = "Превью"


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("short_name", "full_name", "inn", "kpp", "email")
    search_fields = ("short_name", "full_name", "inn")
    inlines = [DocumentInline]


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "company",
        "file_link",
        "file_type",
        "uploaded_at",
        "thumbnail_preview",
    )
    list_filter = ("company", "uploaded_at")
    search_fields = ("title", "company__name")
    readonly_fields = ("thumbnail_preview", "uploaded_at", "extension")

    def file_type(self, obj):
        return obj.extension

    file_type.short_description = "Тип файла"

    def file_link(self, obj):
        if obj.file:
            return format_html('<a href="{}" target="_blank">Скачать</a>', obj.file.url)
        return "-"

    file_link.short_description = "Файл"

    def thumbnail_preview(self, obj):
        if obj.thumbnail:
            return format_html(
                '<img src="{}" style="max-height: 100px; max-width: 80px; object-fit: contain;">',
                obj.thumbnail.url,
            )
        elif obj.extension in ("PDF", "JPG", "JPEG", "PNG"):
            return format_html('<span class="text-muted">В обработке...</span>')
        else:
            return "-"

    thumbnail_preview.short_description = "Миниатюра"


@admin.register(AdditionalService)
class AdditionalServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "service_types_short")
    search_fields = ("name",)
    filter_horizontal = ("service_types",)
    fieldsets = (
        (None, {"fields": ("name", "price")}),
        ("Связь с услугами", {"fields": ("service_types",)}),
        ("Описание", {"fields": ("description",)}),
    )

    def service_types_short(self, obj):
        return ", ".join([s.name for s in obj.service_types.all()])

    service_types_short.short_description = "Типы услуг"


@admin.register(TVChannelPackage)
class TVChannelPackageAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "tariff_list", "image_tag", "slug")
    search_fields = ("name", "slug")
    filter_horizontal = ("channels", "tariffs")
    readonly_fields = ("image_tag",)
    fieldsets = (
        (None, {"fields": ("name", "price", "description", "image", "image_tag", "slug")}),
        ("Связь", {"fields": ("channels", "tariffs")}),
    )

    def image_tag(self, obj):
        """Отображает миниатюру изображения пакета."""
        if obj.image:
            return format_html(
                '<img src="{}" width="132" height="72" />'.format(obj.image.url)
            )
        return "-"

    image_tag.short_description = "Изображение"
    image_tag.allow_tags = True

    def tariff_list(self, obj):
        """Возвращает список связанных тарифов."""
        return ", ".join([t.name for t in obj.tariffs.all()])

    tariff_list.short_description = "Тарифы"


@admin.register(StaticPage)
class StaticPageAdmin(admin.ModelAdmin):
    list_display = ("title", "slug")
    prepopulated_fields = {"slug": ("title",)}
