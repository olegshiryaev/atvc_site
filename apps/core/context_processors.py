from apps.cities.models import Locality
from .models import Service, Tariff


def available_services(request):
    # Получаем текущий locality_slug из URL (если есть)
    locality_slug = (
        request.resolver_match.kwargs.get("locality_slug")
        if request.resolver_match
        else None
    )

    if locality_slug:
        locality = Locality.objects.filter(slug=locality_slug).first()
        if locality:
            tariffs = Tariff.objects.filter(localities=locality, is_active=True)
            service_ids = tariffs.values_list("service_id", flat=True).distinct()
            services = Service.objects.filter(id__in=service_ids)

            return {"locality": locality, "available_services": services}

    return {}
