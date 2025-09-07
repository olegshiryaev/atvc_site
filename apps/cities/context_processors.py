from django.core.serializers.json import DjangoJSONEncoder
import json

from apps.cities.models import Locality


def locality_context(request):
    current_locality = getattr(request, "locality", None)
    
    # Безопасное получение населенных пунктов
    try:
        localities = Locality.objects.filter(is_active=True).select_related('district').values(
            "name", "slug", "district__name", "district__id", "name_prepositional"
        )
        localities_list = list(localities)
    except Exception as e:
        print(f"Error in locality_context: {e}")
        localities_list = []
    
    return {
        "current_locality": current_locality,
        "localities_json": json.dumps(localities_list, cls=DjangoJSONEncoder),
    }
