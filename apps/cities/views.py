from django.shortcuts import redirect
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_GET
from .models import Locality


@require_GET
def select_locality(request):
    locality_id = request.GET.get("locality")
    if locality_id:
        try:
            # Проверяем существование населенного пункта
            locality = Locality.objects.get(id=locality_id, is_active=True)
            request.session["selected_locality_id"] = locality_id
        except (Locality.DoesNotExist, ValueError):
            # Обработка неверного ID
            pass
    
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", reverse("home")))


@require_GET
def get_localities(request):
    try:
        localities = list(
            Locality.objects.filter(is_active=True)
            .select_related('district')
            .order_by("name")
            .values("name", "slug", "district__name", "district__id", "name_prepositional")
        )
        return JsonResponse({"localities": localities, "status": "success"})
    except Exception as e:
        return JsonResponse({"localities": [], "status": "error", "message": str(e)})
