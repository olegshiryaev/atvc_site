from django.shortcuts import redirect
from .models import City


class CityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Пропускаем статические файлы и админку
        if request.path.startswith(("/static/", "/media/", "/admin/")):
            return self.get_response(request)

        # Получаем slug из URL
        path_parts = [p for p in request.path.split("/") if p]
        city_slug = path_parts[0] if path_parts else None

        # Если город не указан — редирект на первый активный (если есть)
        if not city_slug:
            default_city = City.objects.filter(is_active=True).first()
            if default_city:
                return redirect(f"/{default_city.slug}/")
            else:
                # Если в базе нет городов — пропускаем дальше без редиректа
                request.city = None
                return self.get_response(request)

        try:
            request.city = City.objects.get(slug=city_slug, is_active=True)
        except City.DoesNotExist:
            default_city = City.objects.filter(is_active=True).first()
            if default_city:
                return redirect(f"/{default_city.slug}/")
            else:
                request.city = None

        return self.get_response(request)
