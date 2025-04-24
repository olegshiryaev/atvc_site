from django.shortcuts import redirect
from .models import Locality


class LocalityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith(("/static/", "/media/", "/admin/")):
            return self.get_response(request)

        path_parts = [p for p in request.path.split("/") if p]
        locality_slug = path_parts[0] if path_parts else None

        if not locality_slug:
            default_locality = Locality.objects.filter(is_active=True).first()
            if default_locality:
                return redirect(f"/{default_locality.slug}/")
            else:
                request.locality = None
                return self.get_response(request)

        try:
            request.locality = Locality.objects.get(slug=locality_slug, is_active=True)
        except Locality.DoesNotExist:
            default_locality = Locality.objects.filter(is_active=True).first()
            if default_locality:
                return redirect(f"/{default_locality.slug}/")
            else:
                request.locality = None

        return self.get_response(request)
