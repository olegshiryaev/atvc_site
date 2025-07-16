from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.core.models import Feedback
from apps.core.email_tasks import send_feedback_notification

@receiver(post_save, sender=Feedback)
def trigger_feedback_notification(sender, instance, created, **kwargs):
    if created:
        send_feedback_notification.delay(instance.id)  # Запускаем задачу асинхронно