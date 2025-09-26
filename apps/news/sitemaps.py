from django.contrib.sitemaps import Sitemap
from .models import News

class NewsSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return News.objects.published().prefetch_related('localities')

    def lastmod(self, obj):
        return obj.created_at

    def location(self, obj):
        try:
            return obj.get_absolute_url()
        except ValueError:
            return None