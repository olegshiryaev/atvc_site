from django.core.serializers.json import DjangoJSONEncoder
import json

from apps.cities.models import Locality


def locality_context(request):
    current_locality = getattr(request, "locality", None)
    localities = Locality.objects.filter(is_active=True).values("name", "slug")
    return {
        "current_locality": current_locality,
        "localities_json": json.dumps(list(localities), cls=DjangoJSONEncoder),
    }
