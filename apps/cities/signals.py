from django.db.utils import OperationalError
from .models import Locality, Region


def create_default_locality(sender, **kwargs):
    try:
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
    except OperationalError:
        pass
