from django.shortcuts import redirect
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from .models import City


def select_city(request):
    city_id = request.GET.get("city")
    if city_id:
        request.session["selected_city_id"] = city_id  # Сохраняем город в сессии
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", reverse("home")))


def get_cities(request):
    cities = list(City.objects.filter(is_active=True).values("name", "slug"))
    return JsonResponse({"cities": cities})
