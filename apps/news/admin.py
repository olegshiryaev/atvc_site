from django.contrib import admin
from .models import News


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "category",
        "is_published",
        "created_at",
        "views_count",
        "get_localities",
    )
    list_filter = (
        "is_published",
        "category",
        "localities",
        "created_at",
    )
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ("title", "content")
    filter_horizontal = ("localities",)
    readonly_fields = ("views_count",)
    date_hierarchy = "created_at"
    ordering = ("-created_at",)

    def get_localities(self, obj):
        return ", ".join([l.name for l in obj.localities.all()])
    get_localities.short_description = "Населённые пункты"
