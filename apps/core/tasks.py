from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task(autoretry_for=(Exception,), retry_kwargs={"max_retries": 3})
def generate_thumbnail_async(document_id):
    try:
        # Ленивый импорт внутри задачи
        from apps.core.models import Document

        document = Document.objects.get(pk=document_id)
        document.generate_thumbnail()
        document.save(update_fields=["thumbnail"])
        logger.info(f"Миниатюра успешно создана для документа #{document_id}")
    except Document.DoesNotExist:
        logger.warning(f"Документ #{document_id} не найден")
    except Exception as e:
        logger.error(
            f"Ошибка при генерации миниатюры для документа #{document_id}: {e}",
            exc_info=True,
        )
        raise
