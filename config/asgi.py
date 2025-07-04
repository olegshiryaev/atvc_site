"""
ASGI config for atvc_site project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application

# Важно: сначала устанавливаем переменную окружения
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Инициализируем Django приложение до импорта anything else
django_asgi_app = get_asgi_application()

# Только после этого импортируем компоненты Channels
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from apps.chat import routing

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            routing.websocket_urlpatterns
        )
    ),
})