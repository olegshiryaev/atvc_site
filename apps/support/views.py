from django.db import models
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse
from collections import defaultdict
from django.views.generic import ListView, DetailView, TemplateView
from django.db.models import Q, Count
from django.db.models import F
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.core.cache import cache
from django.views.decorators.cache import cache_page

from apps.cities.models import Locality
from apps.core.forms import FeedbackForm
from apps.core.models import Service
from .models import ArticleFeedback, ArticlePDF, HelpTopic, HelpArticle, FAQ
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from django.utils.html import strip_tags
from django.utils.text import Truncator
import json
import logging


logger = logging.getLogger(__name__)


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
    

def create_breadcrumbs(locality_slug, *items):
    """
    Создаёт хлебные крошки.
    Каждый элемент: (url_name, title, optional_kwargs)
    Пример: ('support:topic_detail', 'Интернет', {'topic_slug': 'internet'})
    """
    breadcrumbs = []
    for item in items:
        if isinstance(item, tuple) and len(item) == 3:
            url_name, title, extra_kwargs = item
            kwargs = {'locality_slug': locality_slug, **extra_kwargs}
            try:
                url = reverse(url_name, kwargs=kwargs)
                breadcrumbs.append({'url': url, 'title': title})
            except Exception:
                breadcrumbs.append({'url': None, 'title': title})
        elif isinstance(item, tuple) and len(item) == 2:
            url_name, title = item
            if url_name:
                try:
                    url = reverse(url_name, kwargs={'locality_slug': locality_slug})
                    breadcrumbs.append({'url': url, 'title': title})
                except Exception:
                    breadcrumbs.append({'url': None, 'title': title})
            else:
                breadcrumbs.append({'url': None, 'title': title})
        else:
            breadcrumbs.append({'url': None, 'title': 'Ошибка'})
    return breadcrumbs


class SupportHomeView(SupportBaseView, TemplateView):
    template_name = 'support/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Услуги, доступные в этом населённом пункте
        services = Service.objects.filter(
            is_active=True,
            localities=self.locality
        ).prefetch_related('help_topics').order_by('name')

        # Популярные статьи — только для активных услуг и этой локации
        popular_articles = HelpArticle.objects.filter(
            status=HelpArticle.STATUS_PUBLISHED,
            topic__service__is_active=True,
            topic__service__localities=self.locality
        ).select_related('topic__service').order_by('-view_count')[:6]

        # Темы помощи — только для активных услуг и этой локации
        help_topics = HelpTopic.objects.filter(
            service__is_active=True,
            service__localities=self.locality
        ).distinct().order_by('title')

        # Хлебные крошки
        context['breadcrumbs'] = [
            {'url': 'core:home', 'title': 'Главная'},
            {'url': None, 'title': 'Справочный портал'},
        ]

        # Заголовок
        context['title'] = 'Справочный портал'

        # Данные
        context['services'] = services
        context['popular_articles'] = popular_articles
        context['help_topics'] = help_topics
        context['locality'] = self.locality

        # Форма (если вы хотите использовать Django-валидацию)
        context['feedback_form'] = FeedbackForm()

        return context

    def post(self, request, *args, **kwargs):
        """Обработка POST-запроса от формы обратной связи"""
        form = FeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.locality = self.locality
            feedback.source = 'support_home'  # опционально: откуда пришёл запрос
            feedback.save()

            # Можно добавить сообщение
            from django.contrib import messages
            messages.success(request, "Спасибо за обращение! Мы свяжемся с вами.")

            # Перенаправляем, чтобы избежать повторной отправки
            return self.get(request, *args, **kwargs)
        else:
            # Если ошибка — возвращаем форму с ошибками
            context = self.get_context_data()
            context['feedback_form'] = form
            return render(request, self.template_name, context)
    

class ServiceHelpView(SupportBaseView, TemplateView):
    template_name = 'support/service_help.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        service_slug = self.kwargs.get('service_slug')
        service = get_object_or_404(
            Service,
            slug=service_slug,
            is_active=True,
            localities=self.locality
        )

        # Темы справки (включая одиночные топики без статей)
        topics = HelpTopic.objects.filter(
            service=service
        ).select_related('service').prefetch_related('articles').order_by('-order', 'title')

        # Популярные вопросы из FAQ
        featured_faqs = FAQ.objects.filter(
            service=service,
            is_featured=True
        ).order_by('order', 'question')[:6]

        # Хлебные крошки
        context['breadcrumbs'] = [
            {'url': 'core:home', 'title': 'Главная'},
            {'url': 'support:home', 'title': 'Справочный портал'},
            {'url': None, 'title': service.name},
        ]

        context['title'] = service.name
        context['service'] = service
        context['topics'] = topics
        context['featured_faqs'] = featured_faqs

        return context


class TopicDetailView(SupportBaseView, ListView):
    template_name = 'support/topic_detail.html'
    context_object_name = 'articles'
    paginate_by = 12

    def dispatch(self, request, *args, **kwargs):
        self.service = get_object_or_404(
            Service,
            slug=self.kwargs['service_slug'],
            localities=self.locality,
            is_active=True
        )
        self.topic = get_object_or_404(
            HelpTopic,
            slug=self.kwargs['topic_slug'],
            service=self.service
        )

        # 🟢 Если одиночный топик — подменяем "article" и рендерим article_detail.html
        if self.topic.is_single_topic:
            context = self.get_single_article_context()
            return render(request, "support/article_detail.html", context)

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return HelpArticle.objects.filter(
            topic=self.topic,
            status=HelpArticle.STATUS_PUBLISHED
        ).select_related("topic").order_by("-order", "-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            {"url": "core:home", "title": "Главная"},
            {"url": "support:home", "title": "Справочный портал"},
            {
                "url": "support:service_help",
                "title": self.topic.service.name,
                "service_slug": self.topic.service.slug,
            },
            {"url": None, "title": self.topic.title},
        ]
        context["title"] = self.topic.title
        context["topic"] = self.topic
        context["service"] = self.service
        return context

    def get_single_article_context(self):
        """Формируем контекст для одиночного топика (как будто это статья)"""
        self.topic.update_view_count()

        class FakeArticle:
            def __init__(self, topic):
                self.id = topic.id
                self.pk = topic.id
                self.title = topic.title
                self.content = topic.content
                self.view_count = topic.view_count
                self.created_at = topic.created_at
                self.updated_at = topic.updated_at
                self.slug = topic.slug
                self.topic = topic

        return {
            "breadcrumbs": [
                {"url": "core:home", "title": "Главная"},
                {"url": "support:home", "title": "Справочный портал"},
                {
                    "url": "support:service_help",
                    "title": self.topic.service.name,
                    "service_slug": self.topic.service.slug,
                },
                {"url": None, "title": self.topic.title},
            ],
            "title": self.topic.title,
            "article": FakeArticle(self.topic),
            "related_articles": HelpArticle.objects.filter(
                topic__service=self.service,
                status=HelpArticle.STATUS_PUBLISHED
            ).exclude(topic=self.topic).select_related("topic")[:6],
            "service": self.service,
            "topic": self.topic,
            "locality": self.locality,
            "hide_feedback": True,
            "pdf_instructions": ArticlePDF.objects.filter(
                topic=self.topic
            ).order_by('-order', 'title'),
        }


class ArticleDetailView(SupportBaseView, DetailView):
    model = HelpArticle
    template_name = 'support/article_detail.html'
    context_object_name = 'article'
    slug_field = 'slug'
    slug_url_kwarg = 'article_slug'

    def get_queryset(self):
        return HelpArticle.objects.filter(
            status=HelpArticle.STATUS_PUBLISHED,
            topic__service__slug=self.kwargs['service_slug'],
            topic__service__localities=self.locality,
            topic__service__is_active=True,
            topic__slug=self.kwargs['topic_slug']
        ).select_related('topic__service')

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        HelpArticle.objects.filter(pk=obj.pk).update(view_count=F('view_count') + 1)
        obj.refresh_from_db(fields=['view_count'])
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        article = self.object

        breadcrumbs_cache_key = f'breadcrumbs_article_{article.id}'
        breadcrumbs = cache.get(breadcrumbs_cache_key)
        if breadcrumbs is None:
            breadcrumbs = [
                {'url': 'core:home', 'title': 'Главная'},
                {'url': 'support:home', 'title': 'Справочный портал'},
                {
                    'url': 'support:service_help',
                    'title': article.topic.service.name,
                    'service_slug': article.topic.service.slug,
                },
                {
                    'url': 'support:topic_detail',
                    'title': article.topic.title,
                    'service_slug': article.topic.service.slug,
                    'topic_slug': article.topic.slug,
                },
                {
                    'url': None,
                    'title': article.title,
                },
            ]
            cache.set(breadcrumbs_cache_key, breadcrumbs, 60 * 15)

        context['title'] = article.title
        context['service'] = article.topic.service
        context['breadcrumbs'] = breadcrumbs

        context['pdf_instructions'] = ArticlePDF.objects.filter(
            article=article
        ).order_by('-order', 'title')

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
            Q(title__icontains=query) | Q(content__icontains=query)
        ).select_related('topic').order_by('-view_count', '-created_at')

        # Ищем в FAQ
        faq_results = FAQ.objects.filter(
            Q(question__icontains=query) | 
            Q(answer__icontains=query)
        ).select_related('topic').order_by('-is_featured', 'topic__title')

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
        ).select_related('topic').order_by('-view_count', '-created_at')


@method_decorator(csrf_exempt, name='dispatch')
def article_feedback(request, article_id):
    """
    AJAX view для обработки фидбека по статье (полезно/не полезно).
    """
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
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
            'topic': article.topic.title
        })
    
    for faq in faqs:
        results.append({
            'type': 'faq',
            'title': faq.question,
            'url': f"{reverse('support:faq_list')}#faq-{faq.id}",
            'topic': faq.topic.title
        })
    
    return JsonResponse({'results': results})


class FAQListView(SupportBaseView, ListView):
    """
    Страница со списком всех часто задаваемых вопросов.
    """
    model = FAQ
    template_name = 'support/faq_list.html'
    context_object_name = 'faqs'

    def get_queryset(self):
        return FAQ.objects.select_related('topic').order_by('topic__order', 'topic__title', 'question')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Группировка FAQ по темам
        faqs_by_topic = {}
        for faq in context['faqs']:
            if faq.topic not in faqs_by_topic:
                faqs_by_topic[faq.topic] = []
            faqs_by_topic[faq.topic].append(faq)
        context['faqs_by_topic'] = faqs_by_topic
        
        # Хлебные крошки: Главная / Справочный портал / Частые вопросы
        context['breadcrumbs'] = create_breadcrumbs(
            self.locality.slug,
            ('support:home', 'Главная'),
            ('support:home', 'Справочный портал'),
            (None, 'Частые вопросы')
        )
        
        # Заголовок
        context['title'] = 'Частые вопросы'
        
        return context
    


def service_faq_view(request, locality_slug, service_slug):
    service = get_object_or_404(Service, slug=service_slug, is_active=True, localities__slug=locality_slug)

    # Получаем все FAQ для этой услуги
    faqs = service.faqs.all()

    # Группируем по категориям
    faqs_by_category = defaultdict(list)
    category_display = dict(faqs.model.CATEGORY_CHOICES)

    for faq in faqs:
        key = faq.category
        display_name = category_display.get(key, "Общие вопросы")
        faqs_by_category[display_name].append(faq)

    # Сортируем категории в нужном порядке
    order_map = {
        'Доступ в интернет': 1,
        'Сетевой трафик': 2,
        'Электронная почта': 3,
        'Общие вопросы': 4,
    }

    sorted_categories = sorted(
        faqs_by_category.items(),
        key=lambda x: order_map.get(x[0], 99)
    )

    # --- Формируем хлебные крошки ---
    breadcrumbs_cache_key = f'breadcrumbs_faq_{service.slug}_{locality_slug}'
    breadcrumbs = cache.get(breadcrumbs_cache_key)

    if breadcrumbs is None:
        breadcrumbs = [
            {'url': 'core:home', 'title': 'Главная'},
            {'url': 'support:home', 'title': 'Справочный портал'},
            {
                'url': 'support:service_help',
                'title': service.name,
                'service_slug': service.slug,
            },
            {
                'url': None,
                'title': 'Вопросы и ответы',
            },
        ]
        cache.set(breadcrumbs_cache_key, breadcrumbs, 60 * 15)

    context = {
        'service': service,
        'faqs_by_category': sorted_categories,
        'title': f"Вопросы и ответы",
        'locality_slug': locality_slug,
        'breadcrumbs': breadcrumbs,
    }
    return render(request, 'support/faq_service.html', context)


@require_GET
def search_suggestions(request, locality_slug):

    query = request.GET.get('q', '').strip()
    results = []

    if query:
        # Поиск по статьям
        articles = HelpArticle.objects.filter(
            status=HelpArticle.STATUS_PUBLISHED
        ).filter(
            models.Q(title__icontains=query) |
            models.Q(content__icontains=query)
        ).select_related('topic')[:5]

        # Поиск по FAQ
        faqs = FAQ.objects.filter(
            models.Q(question__icontains=query) |
            models.Q(answer__icontains=query)
        )[:5]

        for article in articles:
            content_clean = strip_tags(article.content)
            results.append({
                'type': 'article',
                'title': article.title,
                'url': article.get_absolute_url(locality_slug),  # Передаём slug
                'desc': Truncator(content_clean).chars(120)
            })

        for faq in faqs:
            answer_clean = strip_tags(faq.answer)
            results.append({
                'type': 'faq',
                'title': faq.question,
                'url': reverse('support:service_faq', kwargs={
                    'locality_slug': locality_slug,
                    'service_slug': faq.service.slug
                }) + f'#faq-{faq.pk}',
                'desc': Truncator(answer_clean).chars(120)
            })

    return JsonResponse({'results': results})


def search_results_view(request, locality_slug):
    query = request.GET.get('q', '').strip()
    articles = []
    faqs = []

    if query:
        articles = HelpArticle.objects.filter(
            status=HelpArticle.STATUS_PUBLISHED
        ).filter(
            Q(title__icontains=query) |
            Q(content__icontains=query)
        ).select_related('topic', 'topic__service')[:10]

        faqs = FAQ.objects.filter(
            Q(question__icontains=query) |
            Q(answer__icontains=query)
        ).select_related('service')[:10]

    return render(request, 'support/search_results.html', {
        'query': query,
        'articles': articles,
        'faqs': faqs,
        'locality_slug': locality_slug,
        'title': f'Результаты поиска: {query}'
    })


@require_http_methods(["POST"])
@csrf_protect
def submit_feedback(request, locality_slug, service_slug, topic_slug, article_slug):
    article = get_object_or_404(
        HelpArticle,
        slug=article_slug,
        topic__slug=topic_slug,
        topic__service__slug=service_slug,
        status=HelpArticle.STATUS_PUBLISHED
    )

    try:
        data = json.loads(request.body)
        helped = data.get('helped')
        session_id = data.get('session_id')

        if not session_id:
            return JsonResponse({
                'success': False,
                'error': 'Нет идентификатора сессии'
            }, status=400)

        # Проверка на дубль
        if ArticleFeedback.objects.filter(article=article, session_id=session_id).exists():
            return JsonResponse({
                'success': False,
                'error': 'Вы уже оценили эту статью'
            }, status=400)

        # Сохраняем анонимный отзыв
        ArticleFeedback.objects.create(
            article=article,
            helped=helped,
            session_id=session_id
        )

        return JsonResponse({
            'success': True,
            'message': 'Спасибо за ваш отзыв!'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': 'Ошибка при сохранении'
        }, status=500)