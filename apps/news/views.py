from django.shortcuts import render, get_object_or_404
from django.http import Http404
from django.urls import reverse
from django.template.loader import render_to_string
from django.http import HttpResponse, JsonResponse
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from django.contrib import messages
from apps.services.utils import get_client_ip
from django.core.paginator import Paginator, EmptyPage
from django.db.models import F
from ..cities.models import Locality
from .models import News
import re
import logging

logger = logging.getLogger(__name__)


def news_list(request, locality_slug):
    """Отображает список новостей для указанного населённого пункта."""
    locality = get_object_or_404(Locality, slug=locality_slug, is_active=True)
    news_qs = News.objects.published().filter(localities=locality).order_by("-created_at").select_related('image').prefetch_related('localities')
    paginator = Paginator(news_qs, 6)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    return render(
        request,
        "news/news_list.html",
        {
            "page_obj": page_obj,  # Унифицировано название
            "locality": locality,
            "has_more_news": page_obj.has_next(),
            "title": "Новости",
            "breadcrumbs": [
                {"title": "Главная", "url": "core:home"},
                {"title": "Новости", "url": None},
            ],
        },
    )


def load_more_news(request, locality_slug):
    """Загружает дополнительные новости через AJAX."""
    if not request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"error": "Требуется AJAX-запрос"}, status=400)

    locality = get_object_or_404(Locality, slug=locality_slug, is_active=True)
    page = int(request.GET.get("page", 2))
    news_per_page = 6  # Унифицировано с news_list

    news_qs = News.objects.published().filter(localities=locality).order_by("-created_at").select_related('image').prefetch_related('localities')
    paginator = Paginator(news_qs, news_per_page)

    try:
        page_obj = paginator.page(page)
    except EmptyPage:
        return JsonResponse({"has_more_news": False, "html": ""})

    html = render_to_string(
        "news/partials/news_card_list.html",
        {"page_obj": page_obj, "locality": locality},
        request=request,
    )

    return JsonResponse({"html": html, "has_more_news": page_obj.has_next()})


def news_detail(request, locality_slug, news_slug):
    locality = get_object_or_404(Locality, slug=locality_slug, is_active=True)
    news_item = get_object_or_404(
        News, slug=news_slug, localities=locality, is_published=True
    )

    # Увеличиваем счётчик просмотров
    News.objects.filter(pk=news_item.pk).update(views_count=F("views_count") + 1)

    # Получаем другие новости из той же локальности
    other_news = News.objects.filter(
        localities=locality,
        is_published=True
    ).exclude(
        id=news_item.id
    ).order_by('-created_at')[:3]

    return render(
        request,
        "news/news_detail.html",
        {
            "locality": locality,
            "news": news_item,
            "other_news": other_news,
            "title": news_item.title,
            "breadcrumbs": [
                {"title": "Главная", "url": "core:home"},
                {"title": "Новости", "url": "news:news_list"},
                {"title": news_item.title, "url": None},
            ],
        },
    )


def news_widget(request, locality_slug):
    """Отображает виджет последних новостей."""
    locality = get_object_or_404(Locality, slug=locality_slug, is_active=True)
    latest_news = News.objects.published().filter(localities=locality).order_by(
        "-created_at"
    ).select_related('image').prefetch_related('localities')[:3]  # Ограничение для виджета

    return render(
        request,
        "news/partials/news_widget.html",
        {
            "latest_news": latest_news,
            "locality": locality,
        },
    )