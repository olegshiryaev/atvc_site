from django.shortcuts import get_object_or_404, redirect, render
from django.urls import resolve, reverse_lazy
from django.views.decorators.http import require_POST
from django.contrib.messages.views import SuccessMessageMixin
from django.http import JsonResponse
from django.views.generic import CreateView
from django.template.loader import render_to_string

from .forms import ApplicationForm, FeedbackCreateForm
from .models import Banner, Device, Office, Service, Tariff, Feedback
from ..cities.models import City
from ..news.models import News
from ..services.utils import get_client_ip
from ..services.email import send_contact_email_message


def index(request, city_slug):
    city = get_object_or_404(City, slug=city_slug, is_active=True)
    active_filter = request.GET.get("type", "internet")

    tariffs = (
        Tariff.objects.filter(cities=city, is_active=True)
        .select_related()
        .prefetch_related("cities")
    )

    if active_filter == "kombo":
        displayed_tariffs = tariffs.filter(service__slug="kombo")
    else:
        displayed_tariffs = tariffs.filter(service__slug=active_filter)

    # Если запрос AJAX (от JavaScript / HTMX), возвращаем JSON с HTML
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        tariffs_html = render_to_string(
            "core/partials/tariffs_list.html",
            {"displayed_tariffs": displayed_tariffs.order_by("price")},
            request=request,
        )
        return JsonResponse({"html": tariffs_html})

    # Получаем последние 3 новости для текущего города
    latest_news = News.objects.filter(is_published=True, cities=city).order_by(
        "-created_at"
    )

    banners = Banner.objects.filter(is_active=True, cities=city)

    context = {
        "displayed_tariffs": displayed_tariffs.order_by("price"),
        "active_filter": active_filter,
        "city": city,
        "latest_news": latest_news,
        "banners": banners,
    }

    return render(request, "core/index.html", context)


@require_POST
def submit_application(request, city_slug):
    if request.headers.get("X-Requested-With") != "XMLHttpRequest":
        return JsonResponse(
            {"success": False, "error": "Недопустимый запрос"}, status=400
        )

    form = ApplicationForm(request.POST)
    if form.is_valid():
        application = form.save(commit=False)
        if hasattr(request, "city") and request.city:
            application.city = request.city
        application.save()
        return JsonResponse({"success": True})
    else:
        errors = {}
        for field, error_list in form.errors.items():
            errors[field] = [str(error) for error in error_list]
        return JsonResponse({"success": False, "errors": errors}, status=400)


def office_list(request, city_slug):
    city = get_object_or_404(City, slug=city_slug, is_active=True)
    offices = Office.objects.filter(city=city)

    return render(
        request,
        "core/offices.html",
        {
            "city": city,
            "offices": offices,
            "cities": City.objects.filter(is_active=True).exclude(id=city.id),
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


def internet_tariffs(request, city_slug):
    city = get_object_or_404(City, slug=city_slug)
    service = get_object_or_404(Service, slug="internet")
    tariffs = Tariff.objects.filter(
        service=service, cities__slug=city_slug, is_active=True
    )
    devices = Device.objects.filter(service_types=service).distinct()
    return render(
        request,
        "tariffs/internet.html",
        {
            "tariffs": tariffs,
            "devices": devices,
            "city_slug": city_slug,
            "city": city,
        },
    )
