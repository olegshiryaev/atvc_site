from django.urls import path
from . import views

app_name = 'support'

urlpatterns = [
    # Главная страница поддержки
    path('', views.SupportHomeView.as_view(), name='home'),

    # Поиск
    path('search/', views.search_results_view, name='search_results'),
    path('search/suggestions/', views.search_suggestions, name='search_suggestions'),

    # Помощь по услуге
    path('<slug:service_slug>/', views.ServiceHelpView.as_view(), name='service_help'),

    # Страница со всеми FAQ
    path('<str:service_slug>/faq/', 
         views.service_faq_view, 
         name='service_faq'),

    path(
        '<str:service_slug>/<str:topic_slug>/<str:article_slug>/feedback/',
        views.submit_feedback,
        name='submit_feedback'
    ),

    # Тема в контексте услуги
    path(
        '<slug:service_slug>/<slug:topic_slug>/',
        views.TopicDetailView.as_view(),
        name='topic_detail'
    ),
    
    # Статья в контексте услуги и темы
    path(
        '<slug:service_slug>/<slug:topic_slug>/<slug:article_slug>/',
        views.ArticleDetailView.as_view(),
        name='article_detail'
    ),
    
    # Популярные статьи
    path('popular/', views.PopularArticlesView.as_view(), name='popular_articles'),
    
    # AJAX endpoint для фидбека
    path('article/<int:article_id>/feedback/', views.article_feedback, name='article_feedback'),
    
    # Автодополнение поиска
    path('search/autocomplete/', views.search_autocomplete, name='search_autocomplete'),
]