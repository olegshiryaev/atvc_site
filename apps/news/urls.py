from django.urls import path
from . import views

app_name = "news"

urlpatterns = [
    path("", views.news_list, name="news_list"),
    path('load-more/', views.load_more_news, name='load_more_news'),
    path("widget/", views.news_widget, name="news_widget"),
    path("<slug:news_slug>/", views.news_detail, name="news_detail"),
]
