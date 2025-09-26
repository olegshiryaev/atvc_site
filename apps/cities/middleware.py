from django.shortcuts import redirect
from django.conf import settings
from .models import Locality


class LocalityMiddleware:
    """
    Middleware для автоматического определения населённого пункта по URL.
    Исключает служебные урлы, AJAX-запросы и API.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        # Пути, которые не должны проверяться на slug города
        self.excluded_paths = getattr(settings, "LOCALITY_MIDDLEWARE_EXCLUDED_PATHS", [])

    def __call__(self, request):
        path = request.path

        # 1. Исключаем служебные пути (robots.txt, sitemap.xml, админка и т.п.)
        if any(path.startswith(p) for p in self.excluded_paths):
            return self.get_response(request)

        # 2. Исключаем AJAX-запросы
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return self.get_response(request)

        # 3. Извлекаем slug населённого пункта из первого сегмента URL
        path_parts = [p for p in path.split("/") if p]
        locality_slug = path_parts[0] if path_parts else None

        if not locality_slug:
            # Если slug отсутствует → редиректим на дефолтный город
            default_locality = Locality.objects.filter(is_active=True).first()
            if default_locality:
                return redirect(f"/{default_locality.slug}/")
            else:
                request.locality = None
                return self.get_response(request)

        try:
            request.locality = Locality.objects.get(slug=locality_slug, is_active=True)
        except Locality.DoesNotExist:
            # Если slug неправильный → редиректим на дефолтный город
            default_locality = Locality.objects.filter(is_active=True).first()
            if default_locality:
                return redirect(f"/{default_locality.slug}/")
            else:
                request.locality = None
        except Exception as e:
            # На всякий случай логируем любые ошибки
            print(f"[LocalityMiddleware] Ошибка: {e}")
            request.locality = None

        return self.get_response(request)
