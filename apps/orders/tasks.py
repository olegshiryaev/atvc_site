from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth.models import User, Group
from django.apps import apps
import logging

from apps.orders.models import Order

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, retry_backoff=True)
def send_order_notification(self, order_id, admin_url):
    logger.info(f"Начало выполнения задачи для заявки #{order_id}")
    try:
        order = Order.objects.get(id=order_id)
        logger.info(f"Заявка #{order_id} найдена: {order}")

        dispatchers_group = Group.objects.get(name="Dispatchers")
        dispatchers_emails = User.objects.filter(
            groups=dispatchers_group, is_active=True
        ).values_list("email", flat=True)
        logger.debug(f"Диспетчеры: {list(dispatchers_emails)}")

        if dispatchers_emails:
            context = {
                "order": order,
                "admin_url": admin_url,
            }
            subject = f"Новая заявка #{order.id}"
            text_message = render_to_string(
                "emails/new_order_notification.txt", context
            )
            html_message = render_to_string(
                "emails/new_order_notification.html", context
            )
            logger.debug(f"Содержимое текстового письма: {text_message}")
            logger.debug(f"Содержимое HTML письма: {html_message}")
            logger.debug(f"Настройки почты: HOST={settings.EMAIL_HOST}, PORT={settings.EMAIL_PORT}, TLS={settings.EMAIL_USE_TLS}, SSL={settings.EMAIL_USE_SSL}")

            send_mail(
                subject=subject,
                message=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=list(dispatchers_emails),
                html_message=html_message,
                fail_silently=False,
            )
            logger.info(
                f"Уведомление о заявке #{order.id} отправлено: {', '.join(dispatchers_emails)}"
            )
            return f"Уведомление о заявке #{order.id} отправлено: {', '.join(dispatchers_emails)}"
        else:
            logger.warning(f"Нет активных диспетчеров для заявки #{order.id}")
            return f"Нет активных диспетчеров для заявки #{order.id}"
    except Order.DoesNotExist:
        logger.error(f"Заявка #{order_id} не найдена")
        return f"Заявка #{order_id} не найдена"
    except Group.DoesNotExist:
        logger.error(f"Группа Dispatchers не найдена для заявки #{order_id}")
        return f"Группа Dispatchers не найдена для заявки #{order_id}"
    except Exception as e:
        logger.error(
            f"Ошибка при отправке уведомления для заявки #{order_id}: {str(e)}"
        )
        self.retry(countdown=60, exc=e)
        return f"Ошибка отправки уведомления о заявке #{order_id}: {str(e)}"