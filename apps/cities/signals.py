from django.db.utils import OperationalError
from .models import Locality


def create_default_locality(sender, **kwargs):
    try:
        if not Locality.objects.exists():
            Locality.objects.create(
                name="Архангельск", slug="arkhangelsk", is_active=True
            )
    except OperationalError:
        pass
