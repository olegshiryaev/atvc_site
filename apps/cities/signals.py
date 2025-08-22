from django.apps import apps
from .models import Locality, Region
from django.db.utils import ProgrammingError

def create_default_locality(sender, **kwargs):
    if sender.name != 'apps.cities':
        return

    try:
        # Убедимся, что модель доступна
        if not apps.is_installed('apps.cities'):
            return

        if not Locality.objects.exists():
            region, created = Region.objects.get_or_create(
                name="Архангельская область"
            )
            Locality.objects.create(
                name="Архангельск",
                name_prepositional="Архангельске",
                slug="arkhangelsk",
                locality_type="city",
                region=region,
                is_active=True
            )
    except ProgrammingError:
        pass