from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json
from .models import ChatSession
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render

def is_support(user):
    return user.is_authenticated and user.is_staff  # или своя логика для специалистов

@login_required
@user_passes_test(is_support)
def support_dashboard(request):
    sessions = ChatSession.objects.filter(is_closed=False).order_by('-created_at')
    return render(request, 'chat/support_dashboard.html', {'sessions': sessions})

@login_required
def chat_view(request, locality_slug=None):
    context = {
        'user': request.user,
        'locality_slug': locality_slug or request.session.get('active_locality')
    }
    return render(request, 'chat/index.html', context)


@csrf_exempt
def start_chat(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            name = data.get('name')
            contact = data.get('contact')
            if not name or not contact:
                return JsonResponse({'error': 'Имя и контакт обязательны'}, status=400)
            session = ChatSession.objects.create(name=name, contact=contact)
            return JsonResponse({'session_id': session.id})
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Недействительный JSON'}, status=400)
    return JsonResponse({'error': 'Метод не поддерживается'}, status=405)