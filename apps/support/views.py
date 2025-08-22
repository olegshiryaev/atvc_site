from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.views.generic import ListView, DetailView, TemplateView
from django.db.models import Q, Count
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.core.cache import cache
from django.views.decorators.cache import cache_page

from apps.cities.models import Locality
from apps.core.models import Service
from .models import HelpCategory, HelpArticle, FAQ
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator


class SupportBaseView:
    """Базовый класс для всех view поддержки, который добавляет locality"""
    
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        # Сохраняем locality как атрибут объекта
        locality_slug = self.kwargs.get('locality_slug')
        if locality_slug:
            self.locality = get_object_or_404(Locality, slug=locality_slug, is_active=True)
        else:
            self.locality = None
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['locality'] = self.locality
        return context

class SupportHomeView(SupportBaseView, TemplateView):
    template_name = 'support/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Получаем услуги для текущего населенного пункта
        services = Service.objects.filter(
            is_active=True,
            localities=self.locality  # Фильтруем по текущему населенному пункту
        ).prefetch_related('help_categories')
        
        # Популярные статьи (топ-6 по просмотрам)
        popular_articles = HelpArticle.objects.filter(
            status=HelpArticle.STATUS_PUBLISHED
        ).select_related('category').order_by('-view_count')[:6]
        
        # Избранные FAQ
        featured_faqs = FAQ.objects.filter(is_featured=True).select_related('category')[:8]
        
        context['services'] = services
        context['popular_articles'] = popular_articles
        context['featured_faqs'] = featured_faqs
        
        return context
    

class ServiceHelpView(SupportBaseView, TemplateView):
    """Страница помощи по конкретной услуге"""
    template_name = 'support/service_help.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Получаем услугу по slug
        service_slug = self.kwargs.get('service_slug')
        service = get_object_or_404(
            Service, 
            slug=service_slug, 
            is_active=True,
            localities=self.locality  # Проверяем, что услуга доступна в этом населенном пункте
        )
        
        # Категории помощи для этой услуги
        categories = HelpCategory.objects.filter(
            service=service,
            articles__status=HelpArticle.STATUS_PUBLISHED
        ).annotate(
            article_count=Count('articles', filter=Q(articles__status=HelpArticle.STATUS_PUBLISHED))
        ).filter(article_count__gt=0).distinct().order_by('-order', 'title')
        
        # Популярные статьи для этой услуги
        popular_articles = HelpArticle.objects.filter(
            category__service=service,
            status=HelpArticle.STATUS_PUBLISHED,
            is_popular=True
        ).select_related('category')[:6]
        
        context['service'] = service
        context['categories'] = categories
        context['popular_articles'] = popular_articles
        
        return context


class CategoryDetailView(SupportBaseView, ListView):
    """
    Страница категории со списком статей и FAQ этой категории.
    """
    template_name = 'support/category_detail.html'
    context_object_name = 'articles'
    paginate_by = 12

    def get_queryset(self):
        self.category = get_object_or_404(
            HelpCategory, 
            slug=self.kwargs['category_slug']
        )
        return HelpArticle.objects.filter(
            category=self.category,
            status=HelpArticle.STATUS_PUBLISHED
        ).select_related('category').order_by('-order', '-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        context['category_faqs'] = FAQ.objects.filter(
            category=self.category
        )[:10]  # Показываем первые 10 FAQ категории
        return context


class ArticleDetailView(SupportBaseView, DetailView):
    """
    Детальная страница статьи.
    """
    model = HelpArticle
    template_name = 'support/article_detail.html'
    context_object_name = 'article'

    def get_queryset(self):
        # Показываем только опубликованные статьи
        return HelpArticle.objects.filter(status=HelpArticle.STATUS_PUBLISHED)

    def get_object(self, queryset=None):
        # Получаем объект и увеличиваем счетчик просмотров
        obj = super().get_object(queryset)
        obj.increment_view_count()
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        article = self.object
        
        # Похожие статьи (из той же категории)
        context['related_articles'] = HelpArticle.objects.filter(
            category=article.category,
            status=HelpArticle.STATUS_PUBLISHED
        ).exclude(pk=article.pk).order_by('-view_count', '-created_at')[:4]
        
        return context


class FAQListView(SupportBaseView, ListView):
    """
    Страница со списком всех часто задаваемых вопросов.
    """
    model = FAQ
    template_name = 'support/faq_list.html'
    context_object_name = 'faqs'

    def get_queryset(self):
        return FAQ.objects.all().select_related('category').order_by('category__order', 'category__title', 'question')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Группируем FAQ по категориям для удобного отображения в шаблоне
        faqs_by_category = {}
        for faq in context['faqs']:
            if faq.category not in faqs_by_category:
                faqs_by_category[faq.category] = []
            faqs_by_category[faq.category].append(faq)
        
        context['faqs_by_category'] = faqs_by_category
        return context


class SearchResultsView(SupportBaseView, ListView):
    """
    Страница результатов поиска.
    Ищет по заголовку и содержанию статей, а также по вопросам и ответам FAQ.
    """
    template_name = 'support/search_results.html'
    context_object_name = 'results'
    paginate_by = 10

    def get_queryset(self):
        query = self.request.GET.get('q', '').strip()
        
        if not query:
            return HelpArticle.objects.none()

        # Ищем в опубликованных статьях
        article_results = HelpArticle.objects.filter(
            status=HelpArticle.STATUS_PUBLISHED
        ).filter(
            Q(title__icontains=query) | 
            Q(content__icontains=query)
        ).select_related('category').order_by('-view_count', '-created_at')

        # Ищем в FAQ
        faq_results = FAQ.objects.filter(
            Q(question__icontains=query) | 
            Q(answer__icontains=query)
        ).select_related('category').order_by('-is_featured', 'category__title')

        # Объединяем результаты
        # В реальном проекте можно использовать search engine (Elasticsearch, PostgreSQL Search)
        return list(article_results) + list(faq_results)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        context['results_count'] = len(self.get_queryset())
        return context


class PopularArticlesView(SupportBaseView, ListView):
    """
    Страница с самыми популярными статьями.
    """
    template_name = 'support/popular_articles.html'
    context_object_name = 'articles'
    paginate_by = 15

    def get_queryset(self):
        return HelpArticle.objects.filter(
            status=HelpArticle.STATUS_PUBLISHED
        ).select_related('category').order_by('-view_count', '-created_at')


@method_decorator(csrf_exempt, name='dispatch')
def article_feedback(request, article_id):
    """
    AJAX view для обработки фидбека по статье (полезно/не полезно).
    """
    if request.method == 'POST' and request.is_ajax():
        article = get_object_or_404(HelpArticle, id=article_id)
        is_helpful = request.POST.get('is_helpful')
        
        # Здесь можно сохранять фидбек в базу или отправлять в аналитику
        # Пока просто возвращаем успешный статус
        
        return JsonResponse({'status': 'success', 'message': 'Спасибо за ваш отзыв!'})
    
    return JsonResponse({'status': 'error', 'message': 'Неверный запрос'}, status=400)


def search_autocomplete(request, locality_slug):
    query = request.GET.get('q', '')
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    # Ищем в заголовках статей и вопросах FAQ
    articles = HelpArticle.objects.filter(
        Q(title__icontains=query),
        status=HelpArticle.STATUS_PUBLISHED
    )[:5]
    
    faqs = FAQ.objects.filter(
        Q(question__icontains=query)
    )[:5]
    
    results = []
    for article in articles:
        results.append({
            'type': 'article',
            'title': article.title,
            'url': article.get_absolute_url(),
            'category': article.category.title
        })
    
    for faq in faqs:
        results.append({
            'type': 'faq',
            'title': faq.question,
            'url': f"{reverse('support:faq_list')}#faq-{faq.id}",
            'category': faq.category.title
        })
    
    return JsonResponse({'results': results})


class FAQListView(SupportBaseView, ListView):
    """Страница со списком всех часто задаваемых вопросов."""
    model = FAQ
    template_name = 'support/faq_list.html'
    context_object_name = 'faqs'

    def get_queryset(self):
        return FAQ.objects.all().select_related('category').order_by('category__order', 'category__title', 'question')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Группируем FAQ по категориям
        faqs_by_category = {}
        for faq in context['faqs']:
            if faq.category not in faqs_by_category:
                faqs_by_category[faq.category] = []
            faqs_by_category[faq.category].append(faq)
        
        context['faqs_by_category'] = faqs_by_category
        return context