from django.shortcuts import get_object_or_404, redirect, render
from django.urls import resolve, reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin
from django.http import JsonResponse
from django.views.generic import CreateView
from django.template.loader import render_to_string

from .forms import ApplicationForm, FeedbackCreateForm
from .models import Office, Tariff, Feedback
from ..cities.models import City
from ..services.utils import get_client_ip
from ..services.email import send_contact_email_message


def index(request, city_slug):
    active_filter = request.GET.get("type", "internet")

    tariffs = (
        Tariff.objects.filter(cities=request.city, is_active=True)
        .select_related()
        .prefetch_related("cities")
    )

    if active_filter == "combo":
        displayed_tariffs = tariffs.filter(tariff_type="combo")
    else:
        displayed_tariffs = tariffs.filter(tariff_type=active_filter)

    # Если запрос AJAX (от JavaScript), возвращаем JSON с HTML
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        tariffs_html = render_to_string(
            "core/partials/tariffs_list.html",  # Этот файл создадим на Шаге 2
            {"displayed_tariffs": displayed_tariffs.order_by("price")},
            request=request,
        )
        return JsonResponse({"html": tariffs_html})

    # Если обычный запрос (первая загрузка страницы)
    context = {
        "displayed_tariffs": displayed_tariffs.order_by("price"),
        "active_filter": active_filter,
    }
    return render(request, "core/index.html", context)


def submit_application(request, city_slug, tariff_id):
    tariff = get_object_or_404(Tariff, id=tariff_id, is_active=True)

    if request.method == "POST":
        form = ApplicationForm(request.POST)
        if form.is_valid():
            application = form.save(commit=False)
            application.tariff = tariff
            application.save()
            return JsonResponse({"success": True})
        else:
            return JsonResponse({"success": False, "errors": form.errors})
    return JsonResponse({"success": False, "error": "Неверный метод запроса"})


def office_list(request, city_slug):
    city = get_object_or_404(City, slug=city_slug, is_active=True)
    offices = Office.objects.filter(city=city)

    return render(
        request,
        "core/offices.html",
        {
            "city": city,  # Передаём объект города
            "offices": offices,
            "cities": City.objects.filter(is_active=True).exclude(
                id=city.id
            ),  # Все города кроме текущего
        },
    )


def get_items(request):
    items = ["Элемент 1", "Элемент 2", "Элемент 3"]
    return render(request, "core/items.html", {"items": items})


def about(request):
    return render(request, "core/about.html", {"title": "О нас"})


def contact(request):
    return render(request, "core/contact.html", {"title": "Контакты"})


class FeedbackCreateView(SuccessMessageMixin, CreateView):
    model = Feedback
    form_class = FeedbackCreateForm
    success_message = "Ваше письмо успешно отправлено администрации сайта"
    template_name = "system/feedback.html"
    extra_context = {"title": "Контактная форма"}
    success_url = reverse_lazy("home")

    def form_valid(self, form):
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.ip_address = get_client_ip(self.request)
            if self.request.user.is_authenticated:
                feedback.user = self.request.user
            send_contact_email_message(
                feedback.subject,
                feedback.email,
                feedback.content,
                feedback.ip_address,
                feedback.user_id,
            )
        return super().form_valid(form)
