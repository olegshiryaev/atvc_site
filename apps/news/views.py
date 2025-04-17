from django.shortcuts import render, get_object_or_404
from django.template.loader import render_to_string
from django.http import HttpResponse, JsonResponse
from django.core.paginator import Paginator
from ..cities.models import City
from .models import News


def news_list(request, city_slug):
    city = get_object_or_404(City, slug=city_slug)
    news_list = News.objects.filter(cities=city, is_published=True).order_by('-created_at')
    paginator = Paginator(news_list, 6)  # Первые 6 новостей
    page_obj = paginator.get_page(1)
    
    # Проверяем, есть ли ещё новости
    has_more_news = paginator.count > 6
    
    return render(request, 'news/news_list.html', {
        'news_list': page_obj,
        'city': city,
        'has_more_news': has_more_news
    })

def load_more_news(request, city_slug):
    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return JsonResponse({'error': 'Invalid request'}, status=400)
    
    city = get_object_or_404(City, slug=city_slug)
    page = int(request.GET.get('page', 2))
    news_per_page = 3
    news_list = News.objects.filter(cities=city, is_published=True).order_by('-created_at')
    paginator = Paginator(news_list, news_per_page)
    
    try:
        page_obj = paginator.page(page)
    except:
        return JsonResponse({'has_more_news': False, 'news': []})
    
    news_data = [{
        'title': news.title,
        'slug': news.slug,
        'date': news.created_at.strftime('%d.%m.%Y'),
        'content': (news.content[:100] + '...' if len(news.content) > 100 else news.content) if news.content else '',
        'image': news.image.url if news.image else ''
    } for news in page_obj]
    
    return JsonResponse({
        'news': news_data,
        'has_more_news': page_obj.has_next()
    })


def news_detail(request, city_slug, news_slug):
    city = get_object_or_404(City, slug=city_slug, is_active=True)
    news_item = get_object_or_404(News, slug=news_slug, cities=city)

    return render(request, "news/news_detail.html", {"city": city, "news": news_item})


def news_widget(request, city_slug):
    city = get_object_or_404(City, slug=city_slug, is_active=True)
    latest_news = News.objects.filter(is_published=True, cities=city).order_by(
        "-created_at"
    )
    return render(
        request,
        "news/partials/news_widget.html",
        {
            "latest_news": latest_news,
            "city": city,
        },
    )
