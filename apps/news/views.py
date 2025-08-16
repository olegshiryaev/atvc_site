from django.shortcuts import render, get_object_or_404
from django.template.loader import render_to_string
from django.http import HttpResponse, JsonResponse
from django.core.paginator import Paginator, EmptyPage
from django.db.models import F
from ..cities.models import Locality
from .models import News
import re


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
    """Отображает детальную страницу новости."""
    locality = get_object_or_404(Locality, slug=locality_slug, is_active=True)
    news_item = get_object_or_404(
        News.objects.published().filter(localities=locality, slug=news_slug).select_related('image').prefetch_related('localities')
    )

    # Увеличиваем счётчик просмотров через метод модели
    news_item.increment_views()

    # Получаем другие новости
    other_news = News.objects.published().filter(
        localities=locality
    ).exclude(id=news_item.id).order_by('-created_at')[:3].select_related('image').prefetch_related('localities')

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
                {"title": "Новости", "url": reverse("news:news_list", kwargs={"locality_slug": locality_slug})},
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