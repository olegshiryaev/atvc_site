import os
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
import json
import uuid
from django.db.models import Count, Q
from .models import ChatMessage, ChatSession
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)

def is_support(user):
    return user.is_authenticated and user.is_staff

def support_login(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('support_dashboard')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                if user.is_staff:
                    login(request, user)
                    logger.info(f"Специалист вошёл: username={username}")
                    return redirect('support_dashboard')
                else:
                    logger.warning(f"Попытка входа без прав специалиста: username={username}")
                    form.add_error(None, 'Требуются права специалиста')
            else:
                logger.warning(f"Неверные учетные данные: username={username}")
                form.add_error(None, 'Неверное имя пользователя или пароль')
        else:
            logger.warning(f"Ошибка валидации формы входа: errors={form.errors}")
    else:
        form = AuthenticationForm()

    return render(request, 'chat/support_login.html', {'form': form})

@login_required
@user_passes_test(is_support)
def support_dashboard(request):
    return render(request, 'chat/support_dashboard.html')

def support_logout(request):
    logout(request)
    logger.info(f"Специалист вышел: username={request.user.username}")
    return redirect('support_login')

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
                file_name = f"{uuid.uuid4()}_{file.name}"
                file_path = os.path.join('chat_attachments', file_name)
                saved_path = default_storage.save(file_path, file)
                file_url = f"{settings.MEDIA_URL}{saved_path}"
                file_size = file.size
                logger.info(f"Файл загружен: session_id={session_id}, file={file.name}, saved_path={saved_path}, file_url={file_url}, file_size={file_size}")
                return JsonResponse({'file_url': file_url, 'file_size': file_size}, status=201)
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
                'attachment': msg.attachment_url if msg.attachment_url else None,
                'file_size': msg.file_size,
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
        if not request.user.is_staff:
            logger.error(f"Попытка закрытия сессии без прав: session_id={session_id}, user={request.user.username}")
            return JsonResponse({'error': 'Требуются права специалиста'}, status=403)
        session.is_closed = True
        session.save()
        logger.info(f"Сессия закрыта: session_id={session_id}")
        return JsonResponse({'status': 'closed'})
    except ChatSession.DoesNotExist:
        logger.error(f"Сессия не найдена: session_id={session_id}")
        return JsonResponse({'error': 'Сессия не найдена'}, status=404)

def get_sessions(request):
    sessions = ChatSession.objects.filter(is_closed=False).select_related('operator').annotate(
        unread_count=Count('messages', filter=Q(messages__is_support=False, messages__is_read=False))
    ).order_by('-created_at')
    logger.info(f"Загружено сессий: count={sessions.count()}")
    return JsonResponse([
        {
            'id': session.id,
            'name': session.name,
            'contact': session.contact,
            'unread_count': session.unread_count
        } for session in sessions
    ], safe=False)