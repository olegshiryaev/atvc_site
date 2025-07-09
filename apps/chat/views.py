from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json
from .models import ChatMessage, ChatSession
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
import logging

logger = logging.getLogger(__name__)

def is_support(user):
    return user.is_authenticated and user.is_staff

@login_required
@user_passes_test(is_support)
def support_dashboard(request):
    if not request.user.is_staff:
        return JsonResponse({'error': 'Доступ запрещён'}, status=403)
    return render(request, 'chat/support_dashboard.html')


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
            allowed_extensions = ['jpg', 'jpeg', 'png', 'pdf']
            validator = FileExtensionValidator(allowed_extensions)
            try:
                validator(file)
            except ValidationError:
                logger.error(f"Недопустимый тип файла: session_id={session_id}, file={file.name}")
                return JsonResponse({'error': 'Недопустимый тип файла. Разрешены: jpg, jpeg, png, pdf'}, status=400)
            
            if file.size > 5 * 1024 * 1024:
                logger.error(f"Файл слишком большой: session_id={session_id}, file={file.name}")
                return JsonResponse({'error': 'Файл слишком большой (максимум 5 МБ)'}, status=400)
            
            try:
                session = ChatSession.objects.get(id=session_id)
                message = ChatMessage.objects.create(
                    session=session,
                    message='[Файл]',
                    is_support=request.user.is_staff,
                    sender='Специалист' if request.user.is_staff else 'Клиент',
                    attachment=file
                )
                logger.info(f"Файл загружен: session_id={session_id}, file={file.name}")
                return JsonResponse({'file_url': message.attachment.url}, status=201)
            except ChatSession.DoesNotExist:
                logger.error(f"Сессия не найдена: session_id={session_id}")
                return JsonResponse({'error': 'Сессия не найдена'}, status=404)
    logger.error(f"Недопустимый запрос: method={request.method}, session_id={session_id}")
    return JsonResponse({'error': 'Invalid request'}, status=400)

def get_chat_history(request, session_id):
    try:
        messages = ChatMessage.objects.filter(session_id=session_id).order_by('timestamp')
        logger.info(f"Загружена история: session_id={session_id}, messages_count={messages.count()}")
        return JsonResponse([
            {
                'message_id': str(msg.message_id),
                'message': msg.message,
                'timestamp': msg.timestamp.isoformat(),
                'is_support': msg.is_support,
                'sender': msg.sender,
                'attachment': msg.attachment.url if msg.attachment else None,
                'is_read': msg.is_read
            } for msg in messages
        ], safe=False)
    except ChatSession.DoesNotExist:
        logger.error(f"Сессия не найдена: session_id={session_id}")
        return JsonResponse({'error': 'Сессия не найдена'}, status=404)

@csrf_exempt
def get_unread_count(request):
    session_id = request.GET.get('session_id')
    if session_id:
        try:
            session = ChatSession.objects.get(id=session_id)
            if request.user.is_staff:
                unread = ChatMessage.objects.filter(
                    session=session, is_support=False, is_read=False
                ).count()
            else:
                unread = ChatMessage.objects.filter(
                    session=session, is_support=True, is_read=False
                ).count()
            logger.info(f"Непрочитанные сообщения: session_id={session_id}, is_staff={request.user.is_staff}, unread={unread}")
            return JsonResponse({'unread': unread})
        except ChatSession.DoesNotExist:
            logger.error(f"Сессия не найдена: session_id={session_id}")
            return JsonResponse({'unread': 0})
    else:
        unread = ChatMessage.objects.filter(is_support=False, is_read=False).count()
        logger.info(f"Непрочитанные для специалиста: unread={unread}")
        return JsonResponse({'unread': unread})

@csrf_exempt
def mark_messages_as_read(request, session_id):
    try:
        session = ChatSession.objects.get(id=session_id)
        if request.user.is_staff:
            unread_count = ChatMessage.objects.filter(session=session, is_support=False, is_read=False).count()
            ChatMessage.objects.filter(session=session, is_support=False, is_read=False).update(is_read=True)
        else:
            unread_count = ChatMessage.objects.filter(session=session, is_support=True, is_read=False).count()
            ChatMessage.objects.filter(session=session, is_support=True, is_read=False).update(is_read=True)
        logger.info(f"Сообщения помечены как прочитанные: session_id={session_id}, is_staff={request.user.is_staff}, unread_count={unread_count}")
        return JsonResponse({'status': 'success', 'unread_count': 0})
    except ChatSession.DoesNotExist:
        logger.error(f"Сессия не найдена: session_id={session_id}")
        return JsonResponse({'error': 'Сессия не найдена'}, status=404)

@csrf_exempt
def close_chat(request, session_id):
    try:
        session = ChatSession.objects.get(id=session_id)
        session.is_closed = True
        session.save()
        logger.info(f"Сессия закрыта: session_id={session_id}")
        return JsonResponse({'status': 'closed'})
    except ChatSession.DoesNotExist:
        logger.error(f"Сессия не найдена: session_id={session_id}")
        return JsonResponse({'error': 'Сессия не найдена'}, status=404)

def get_sessions(request):
    sessions = ChatSession.objects.filter(is_closed=False).order_by('-created_at')
    logger.info(f"Загружено сессий: count={sessions.count()}")
    return JsonResponse([
        {
            'id': session.id,
            'name': session.name,
            'contact': session.contact,
            'unread_count': ChatMessage.objects.filter(session=session, is_support=False, is_read=False).count()
        } for session in sessions
    ], safe=False)