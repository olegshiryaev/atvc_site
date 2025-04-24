from django.shortcuts import render, get_object_or_404
from django.template.loader import render_to_string
from django.http import HttpResponse, JsonResponse
from django.core.paginator import Paginator
from ..cities.models import Locality
from .models import News
import re


def news_list(request, locality_slug):
    locality = get_object_or_404(Locality, slug=locality_slug)
    news_list = News.objects.filter(localities=locality, is_published=True).order_by(
        "-created_at"
    )
    paginator = Paginator(news_list, 6)  # Первые 6 новостей
    page_obj = paginator.get_page(1)

    # Проверяем, есть ли ещё новости
    has_more_news = paginator.count > 6

    return render(
        request,
        "news/news_list.html",
        {"news_list": page_obj, "locality": locality, "has_more_news": has_more_news},
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
    except:
        return JsonResponse({"has_more_news": False, "news": []})

    news_data = [
        {
            "title": news.title,
            "slug": news.slug,
            "date": news.created_at.strftime("%d.%m.%Y"),
            "content": (
                (
                    news.content[:100] + "..."
                    if len(news.content) > 100
                    else news.content
                )
                if news.content
                else ""
            ),
            "image": news.image.url if news.image else "",
        }
        for news in page_obj
    ]

    return JsonResponse({"news": news_data, "has_more_news": page_obj.has_next()})


def news_detail(request, locality_slug, news_slug):
    locality = get_object_or_404(Locality, slug=locality_slug, is_active=True)
    news_item = get_object_or_404(
        News, slug=news_slug, localiies=locality, is_published=True
    )

    return render(
        request,
        "news/news_detail.html",
        {
            "locality": locality,
            "news": news_item,
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
