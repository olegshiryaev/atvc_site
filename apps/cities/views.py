from django.shortcuts import redirect
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from .models import Locality


def select_locality(request):
    locality_id = request.GET.get("locality")
    if locality_id:
        request.session["selected_locality_id"] = (
            locality_id  # Сохраняем город в сессии
        )
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", reverse("home")))


def get_localities(request):
    localities = list(
        Locality.objects.filter(is_active=True).order_by("name").values("name", "slug")
    )
    return JsonResponse({"localities": localities})
