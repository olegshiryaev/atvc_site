from django.apps import AppConfig


class CitiesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.cities"
    verbose_name = "Населённые пункты"

    def ready(self):
        from django.db.models.signals import post_migrate
        from .signals import create_default_locality

        post_migrate.connect(create_default_locality, sender=self)
