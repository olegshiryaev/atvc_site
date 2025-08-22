from django.urls import path
from . import views

app_name = 'support'

urlpatterns = [
    # Главная страница поддержки
    path('', views.SupportHomeView.as_view(), name='home'),
    
    # Страница категории
    path('category/<slug:category_slug>/', views.CategoryDetailView.as_view(), name='category_detail'),
    
    # Детальная страница статьи
    path('article/<slug:category_slug>/<slug:article_slug>/', views.ArticleDetailView.as_view(), name='article_detail'),
    
    # Страница со всеми FAQ
    path('faq/', views.FAQListView.as_view(), name='faq_list'),
    
    # Поиск
    path('search/', views.SearchResultsView.as_view(), name='search'),
    
    # Популярные статьи
    path('popular/', views.PopularArticlesView.as_view(), name='popular_articles'),
    
    # AJAX endpoint для фидбека
    path('article/<int:article_id>/feedback/', views.article_feedback, name='article_feedback'),
    
    # Автодополнение поиска
    path('search/autocomplete/', views.search_autocomplete, name='search_autocomplete'),

    path('service/<slug:service_slug>/', views.ServiceHelpView.as_view(), name='service_help'),
]