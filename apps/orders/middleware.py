from django.contrib.sessions.models import Session
from .models import Cart

class CartMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. Убедимся, что у запроса есть сессия
        if not request.session.session_key:
            request.session.create()

        # 2. Получаем или создаем корзину
        session = Session.objects.get(session_key=request.session.session_key)
        cart, created = Cart.objects.get_or_create(session=session)
        
        # 3. Добавляем корзину в объект запроса
        request.cart = cart

        response = self.get_response(request)
        return response