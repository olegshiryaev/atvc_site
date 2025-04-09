from django.db.utils import OperationalError
from .models import City


def create_default_city(sender, **kwargs):
    try:
        if not City.objects.exists():
            City.objects.create(name="Архангельск", slug="arkhangelsk", is_active=True)
    except OperationalError:
        pass
