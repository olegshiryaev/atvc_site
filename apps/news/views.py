from django.shortcuts import render, get_object_or_404
from django.template.loader import render_to_string
from django.http import HttpResponse, JsonResponse
from django.core.paginator import Paginator, EmptyPage
from django.db.models import F
from ..cities.models import Locality
from .models import News
import re


def news_list(request, locality_slug):
    locality = get_object_or_404(Locality, slug=locality_slug)
    news_list = News.objects.filter(localities=locality, is_published=True).order_by(
        "-created_at"
    )
    paginator = Paginator(news_list, 6)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    return render(
        request,
        "news/news_list.html",
        {
            "news_list": page_obj,
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
    if request.headers.get("X-Requested-With") != "XMLHttpRequest":
        return JsonResponse({"error": "Invalid request"}, status=400)

    locality = get_object_or_404(Locality, slug=locality_slug)
    page = int(request.GET.get("page", 2))
    news_per_page = 3

    news_list = News.objects.filter(localities=locality, is_published=True).order_by(
        "-created_at"
    )

    paginator = Paginator(news_list, news_per_page)

    try:
        page_obj = paginator.page(page)
    except EmptyPage:
        return JsonResponse({"has_more_news": False, "html": ""})

    # Рендерим список карточек новостей
    html = render_to_string(
        "news/partials/news_card_list.html",
        {"news_list": page_obj, "locality": locality},
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

    return render(
        request,
        "news/news_detail.html",
        {
            "locality": locality,
            "news": news_item,
            "title": news_item.title,
            "breadcrumbs": [
                {"title": "Главная", "url": "core:home"},
                {"title": "Новости", "url": "news:news_list"},
                {"title": news_item.title, "url": None},
            ],
        },
    )


def news_widget(request, locality_slug):
    locality = get_object_or_404(Locality, slug=locality_slug, is_active=True)
    latest_news = News.objects.filter(is_published=True, localiies=locality).order_by(
        "-created_at"
    )
    return render(
        request,
        "news/partials/news_widget.html",
        {
            "latest_news": latest_news,
            "locality": locality,
        },
    )
