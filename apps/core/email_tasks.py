from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth.models import User
from apps.core.models import Feedback
import logging

logger = logging.getLogger(__name__)

@shared_task
def send_feedback_notification(feedback_id):
    try:
        feedback = Feedback.objects.get(id=feedback_id)
        subject = f'Новое сообщение обратной связи от {feedback.name or "Аноним"}'
        html_message = render_to_string('core/feedback_notification.html', {
            'name': feedback.name,
            'phone': feedback.phone,
            'content': feedback.content,
            'time_create': feedback.time_create,
            'ip_address': feedback.ip_address,
        })
        recipient_list = User.objects.filter(
            groups__name='SupportTeam',
            is_active=True
        ).values_list('email', flat=True).exclude(email__isnull=True).exclude(email='')
        if not recipient_list:
            logger.warning(f"Нет активных пользователей в группе SupportTeam с указанным email для feedback_id={feedback_id}")
            return
        send_mail(
            subject,
            'Новое сообщение поступило.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Уведомление отправлено {recipient_list} для feedback_id={feedback_id}")
    except Feedback.DoesNotExist:
        logger.error(f"Feedback с id={feedback_id} не найдена")