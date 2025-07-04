from django.urls import path
from . import views

urlpatterns = [
    path('', views.chat_view, name='chat'),
    path('api/start/', views.start_chat, name='start_chat'),
    path('support/', views.support_dashboard, name='support_dashboard'),
]