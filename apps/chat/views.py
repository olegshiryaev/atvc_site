from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json
from .models import ChatMessage, ChatSession
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
import logging

logger = logging.getLogger(__name__)

def is_support(user):
    return user.is_authenticated and user.is_staff  # или своя логика для специалистов

@login_required
@user_passes_test(is_support)
def support_dashboard(request):
    if not request.user.is_staff:
        return JsonResponse({'error': 'Доступ запрещён'}, status=403)
    return render(request, 'chat/support_dashboard.html')


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


@csrf_exempt
def upload_file(request):
    if request.method == 'POST':
        file = request.FILES.get('file')
        session_id = request.POST.get('session_id')
        if file and session_id:
            if file.size > 5 * 1024 * 1024:
                return JsonResponse({'error': 'Файл слишком большой (максимум 5 МБ)'}, status=400)
            message = ChatMessage.objects.create(
                session_id=session_id,
                message='[Файл]',
                is_support=False,
                sender='Клиент',
                attachment=file
            )
            return JsonResponse({'file_url': message.attachment.url}, status=201)
    return JsonResponse({'error': 'Invalid request'}, status=400)

def get_chat_history(request, session_id):
    messages = ChatMessage.objects.filter(session_id=session_id).order_by('timestamp')
    return JsonResponse([
        {
            'message_id': str(msg.message_id),
            'message': msg.message,
            'timestamp': msg.timestamp.isoformat(),
            'is_support': msg.is_support,
            'sender': msg.sender,
            'attachment': msg.attachment.url if msg.attachment else None
        } for msg in messages
    ], safe=False)

def get_unread_count(request):
    session_id = request.GET.get('session_id')
    if session_id:
        # Для клиента: считаем непрочитанные сообщения от специалиста в текущей сессии
        try:
            session = ChatSession.objects.get(id=session_id)
            unread = ChatMessage.objects.filter(
                session=session, is_support=True, is_read=False
            ).count()
            logger.info(f"Непрочитанные для клиента: session_id={session_id}, unread={unread}")
            return JsonResponse({'unread': unread})
        except ChatSession.DoesNotExist:
            logger.error(f"Сессия не найдена: session_id={session_id}")
            return JsonResponse({'unread': 0})
    else:
        # Для специалиста: считаем непрочитанные сообщения от клиентов по всем сессиям
        unread = ChatMessage.objects.filter(is_support=False, is_read=False).count()
        logger.info(f"Непрочитанные для специалиста: unread={unread}")
        return JsonResponse({'unread': unread})

@csrf_exempt
def close_chat(request, session_id):
    try:
        session = ChatSession.objects.get(id=session_id)
        session.is_closed = True
        session.save()
        return JsonResponse({'status': 'closed'})
    except ChatSession.DoesNotExist:
        return JsonResponse({'error': 'Сессия не найдена'}, status=404)

def get_sessions(request):
    sessions = ChatSession.objects.filter(is_closed=False).order_by('-created_at')
    return JsonResponse([
        {
            'id': session.id,
            'name': session.name,
            'contact': session.contact,
            'unread_count': ChatMessage.objects.filter(session=session, is_support=False, is_read=False).count()
        } for session in sessions
    ], safe=False)