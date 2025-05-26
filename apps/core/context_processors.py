from apps.cities.models import Locality
from .models import Service, Tariff


def available_services(request):
    # Инициализация словаря для возврата
    context = {"locality": None, "available_services": []}

    # Попытка получить locality_slug из URL
    try:
        locality_slug = request.resolver_match.kwargs.get("locality_slug") if request.resolver_match else None
    except AttributeError:
        locality_slug = None

    # Если locality_slug отсутствует, пробуем взять из сессии
    if not locality_slug:
        locality_slug = request.session.get("locality_slug", None)

    if locality_slug:
        # Получаем Locality, используем get() для точного соответствия
        locality = Locality.objects.filter(slug=locality_slug).first()
        if locality:
            # Оптимизированный запрос: фильтруем активные тарифы и услуги
            tariffs = Tariff.objects.filter(localities=locality, is_active=True).select_related("service")
            service_ids = tariffs.values_list("service_id", flat=True).distinct()
            services = Service.objects.filter(id__in=service_ids, is_active=True).order_by("name")
            context.update({"locality": locality, "available_services": services})

    return context
