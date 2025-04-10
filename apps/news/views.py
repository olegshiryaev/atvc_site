from django.shortcuts import render, get_object_or_404
from django.template.loader import render_to_string
from django.http import HttpResponse
from ..cities.models import City
from .models import News


def news_list(request, city_slug):
    city = get_object_or_404(City, slug=city_slug, is_active=True)
    news_list = News.objects.filter(cities=city)

    return render(
        request, "news/news_list.html", {"city": city, "news_list": news_list}
    )


def news_detail(request, city_slug, news_slug):
    city = get_object_or_404(City, slug=city_slug, is_active=True)
    news_item = get_object_or_404(News, slug=news_slug, cities=city)

    return render(request, "news/news_detail.html", {"city": city, "news": news_item})


def news_widget(request, city_slug):
    city = get_object_or_404(City, slug=city_slug, is_active=True)
    latest_news = News.objects.filter(is_published=True, cities=city).order_by(
        "-created_at"
    )[:3]
    return render(
        request,
        "news/partials/news_widget.html",
        {
            "latest_news": latest_news,
            "city": city,
        },
    )
