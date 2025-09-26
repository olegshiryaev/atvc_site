"""
URL configuration for atvc_site project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings
from django.shortcuts import redirect
from django.views.generic import TemplateView
from apps.cities.models import Locality
from django.contrib.sitemaps.views import sitemap
from apps.core.sitemaps import CoreStaticSitemap, StaticPagesSitemap
from apps.news.sitemaps import NewsSitemap
from apps.core.views import getstatus


sitemaps = {
    "news": NewsSitemap,
    "static_core": CoreStaticSitemap,
    "static_pages": StaticPagesSitemap,
}

def redirect_to_active_locality(request):
    locality = Locality.objects.filter(is_active=True).first()
    if locality:
        return redirect(f"/{locality.slug}/")
    return redirect("/")


urlpatterns = [
    path("wfhlthch/getstatus/", getstatus, name="getstatus"),
    path("a9f8s7d6/", admin.site.urls),
    path("ckeditor/", include("ckeditor_uploader.urls")),
    path("chat/", include("apps.chat.urls")),
    path(
        "robots.txt",
        TemplateView.as_view(template_name="robots.txt", content_type="text/plain"),
    ),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}),
    # Корневой путь редиректит на первую активную локализацию
    path("", redirect_to_active_locality),
    # Пути без slug (например, список всех населённых пунктов)
    path("", include("apps.cities.urls")),
    # Пути с <locality_slug>/news/
    path("<slug:locality_slug>/news/", include("apps.news.urls", namespace="news")),
    # Общие маршруты по <locality_slug>/
    path("<slug:locality_slug>/", include("apps.core.urls")),
    path("<slug:locality_slug>/", include("apps.equipments.urls")),
    path("<slug:locality_slug>/", include("apps.orders.urls")),
    path('<slug:locality_slug>/support/', include("apps.support.urls", namespace='support')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
