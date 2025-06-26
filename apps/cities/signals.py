from django.db.utils import OperationalError
from .models import Locality


def create_default_locality(sender, **kwargs):
    try:
        if not Locality.objects.exists():
            Locality.objects.create(
                name="Архангельск",
                name_prepositional="Архангельске",
                slug="arkhangelsk",
                locality_type="city",
                is_active=True
            )
    except OperationalError:
        pass
