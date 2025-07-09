from django.urls import path
from . import views

urlpatterns = [
    path('', views.chat_view, name='chat'),
    path('api/start/', views.start_chat, name='start_chat'),
    path('api/upload/', views.upload_file, name='upload_file'),
    path('api/history/<int:session_id>/', views.get_chat_history, name='chat_history'),
    path('api/unread/', views.get_unread_count, name='unread_count'),
    path('api/close/<int:session_id>/', views.close_chat, name='close_chat'),
    path('api/sessions/', views.get_sessions, name='get_sessions'),
    path('support/', views.support_dashboard, name='support_dashboard'),
]