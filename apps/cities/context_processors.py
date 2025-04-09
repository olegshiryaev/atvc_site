from django.core.serializers.json import DjangoJSONEncoder
import json

from apps.cities.models import City


def city_context(request):
    current_city = getattr(request, "city", None)
    cities = City.objects.filter(is_active=True).values(
        "name", "slug"
    )  # Преобразуем в QuerySet словарей
    return {
        "current_city": current_city,
        "cities_json": json.dumps(
            list(cities), cls=DjangoJSONEncoder
        ),  # Сериализуем в JSON
    }
