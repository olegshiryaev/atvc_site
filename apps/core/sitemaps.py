from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.utils import timezone

from apps.cities.models import Locality
from apps.core.models import Tariff, StaticPage


def _absolute_url(path, site, protocol):
    """
    Возвращает абсолютный URL (protocol://domain + path).
    site: объект Site (может быть None) — его передаёт sitemap view.
    protocol: 'http' или 'https'.
    """
    if path.startswith("http://") or path.startswith("https://"):
        return path
    domain = None
    if site is not None:
        domain = getattr(site, "domain", None)
    if not domain:
        domain = getattr(settings, "SITE_DOMAIN", None)
    if not domain:
        # fallback — не идеально, но чтобы не упасть. Заменить на реальный домен в settings!
        domain = "atvc.ru"
    proto = protocol or getattr(settings, "SITE_PROTOCOL", "https")
    if path.startswith("/"):
        return f"{proto}://{domain}{path}"
    return f"{proto}://{domain}/{path}"


class LocalitySitemap(Sitemap):
    priority = 0.9
    changefreq = "daily"

    def items(self):
        return Locality.objects.filter(is_active=True)

    def location(self, obj):
        # reverse возможен, но проще — корневая страница города
        return reverse("core:home", kwargs={"locality_slug": obj.slug})


class CoreStaticSitemap(Sitemap):
    """
    Статические view (about, contacts, company_detail, feedback_form),
    но каждую страницу нужно дублировать для каждого active locality,
    потому что у тебя локализация в URL.
    """
    priority = 0.7
    changefreq = "monthly"
    static_names = [
        ("core:about", {}),
        ("core:contacts", {}),
        ("core:company_detail", {}),
        ("core:feedback_form", {}),
        # Добавь другие simple views, если необходимо
    ]

    def items(self):
        # возвращаем имена — но реальную генерацию делаем в get_urls
        return self.static_names

    def get_urls(self, page=1, site=None, protocol=None):
        urls = []
        localities = Locality.objects.filter(is_active=True)
        for view_name, extra_kwargs in self.items():
            for locality in localities:
                try:
                    path = reverse(view_name, kwargs={"locality_slug": locality.slug, **extra_kwargs})
                except Exception:
                    # если reverse не сработал — пропускаем (не критично)
                    continue
                urls.append({
                    "location": _absolute_url(path, site, protocol),
                    "lastmod": None,
                    "changefreq": self.changefreq,
                    "priority": self.priority,
                })
        return urls


class StaticPagesSitemap(Sitemap):
    priority = 0.6
    changefreq = "monthly"

    def items(self):
        return StaticPage.objects.all()

    def get_urls(self, page=1, site=None, protocol=None):
        urls = []
        localities = Locality.objects.filter(is_active=True)
        for page_obj in self.items().iterator():
            for locality in localities:
                try:
                    path = reverse("core:static_page", kwargs={"locality_slug": locality.slug, "slug": page_obj.slug})
                except Exception:
                    continue
                urls.append({
                    "location": _absolute_url(path, site, protocol),
                    "lastmod": getattr(page_obj, "updated_at", None) or getattr(page_obj, "created_at", None),
                    "changefreq": self.changefreq,
                    "priority": self.priority,
                })
        return urls