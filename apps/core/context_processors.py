from django.conf import settings
from apps.cities.models import Locality
from .models import Service


def yandex_metrika(request):
    return {
        'YANDEX_METRIKA_ID': settings.YANDEX_METRIKA_ID if hasattr(settings, 'YANDEX_METRIKA_ID') else None
    }


def available_services(request):
    context = {
        "locality": None,
        "available_services": [],
    }

    # Получаем slug населённого пункта из URL или из сессии
    try:
        locality_slug = (
            request.resolver_match.kwargs.get("locality_slug")
            if request.resolver_match
            else None
        )
    except AttributeError:
        locality_slug = None

    if not locality_slug:
        locality_slug = request.session.get("locality_slug")

    # Если есть slug, получаем населённый пункт
    if locality_slug:
        locality = Locality.objects.filter(slug=locality_slug, is_active=True).first()
        if locality:
            # Фильтруем услуги, в которых выбран этот населённый пункт
            services = Service.objects.filter(
                localities=locality, is_active=True
            ).order_by("name")

            context.update(
                {
                    "locality": locality,
                    "available_services": services,
                }
            )

    return context
