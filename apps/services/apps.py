from django.apps import AppConfig


class ServicesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.services'
    path = '/app/apps/services'
    verbose_name = 'Сервисы'
