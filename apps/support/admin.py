from django.contrib import admin
from .models import HelpCategory, HelpArticle, FAQ

@admin.register(HelpCategory)
class HelpCategoryAdmin(admin.ModelAdmin):
    list_display = ['title', 'service', 'icon', 'order', 'slug']
    list_editable = ['order', 'icon']
    list_filter = ['service', 'icon']
    search_fields = ['title', 'description']
    readonly_fields = ['slug']  # Делаем slug только для чтения в админке
    
    # Поля для формы редактирования
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'service', 'icon', 'order')
        }),
        ('Описание', {
            'fields': ('description',),
            'classes': ('collapse',)
        }),
    )
    
    # Автозаполнение slug при создании через админку
    prepopulated_fields = {'slug': ('title',)}
    
    def get_prepopulated_fields(self, request, obj=None):
        # Для существующих объектов не используем автозаполнение
        if obj:
            return {}
        return {'slug': ('title',)}

@admin.register(HelpArticle)
class HelpArticleAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'status', 'is_popular', 'order', 'view_count']
    list_editable = ['status', 'is_popular', 'order']
    list_filter = ['status', 'category', 'is_popular']
    search_fields = ['title', 'content']
    prepopulated_fields = {'slug': ('title',)}
    
    def get_prepopulated_fields(self, request, obj=None):
        if obj:
            return {}
        return {'slug': ('title',)}

@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ['question', 'category', 'is_featured']
    list_editable = ['is_featured']
    list_filter = ['is_featured', 'category']
    search_fields = ['question', 'answer']