from django.shortcuts import get_object_or_404, redirect, render
from django.urls import resolve, reverse_lazy
from django.views.decorators.http import require_POST
from django.contrib.messages.views import SuccessMessageMixin
from django.http import JsonResponse
from django.views.generic import CreateView, DetailView
from django.template.loader import render_to_string

from .forms import ApplicationForm, ContactForm, FeedbackCreateForm, FeedbackForm
from .models import Banner, Company, Device, Office, Service, Tariff, Feedback
from ..cities.models import Locality
from ..news.models import News
from ..services.utils import get_client_ip
from ..services.email import send_contact_email_message
from django.core.mail import send_mail


def index(request, locality_slug):
    locality = get_object_or_404(Locality, slug=locality_slug, is_active=True)
    active_filter = request.GET.get("type", "internet")

    tariffs = (
        Tariff.objects.filter(localities=locality, is_active=True)
        .select_related("service")
        .prefetch_related("localities")
    )

    if active_filter == "kombo":
        displayed_tariffs = tariffs.filter(service__slug="kombo")
    else:
        displayed_tariffs = tariffs.filter(service__slug=active_filter)

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        tariffs_html = render_to_string(
            "core/partials/tariffs_list.html",
            {
                "displayed_tariffs": displayed_tariffs.order_by("price"),
                "locality": locality,
            },
            request=request,
        )
        return JsonResponse({"html": tariffs_html})

    latest_news = News.objects.filter(is_published=True, localities=locality).order_by(
        "-created_at"
    )

    banners = Banner.objects.filter(is_active=True, localities=locality)

    context = {
        "displayed_tariffs": displayed_tariffs.order_by("price"),
        "active_filter": active_filter,
        "locality": locality,
        "latest_news": latest_news,
        "banners": banners,
    }

    return render(request, "core/index.html", context)


@require_POST
def submit_application(request, locality_slug):
    if request.headers.get("X-Requested-With") != "XMLHttpRequest":
        return JsonResponse(
            {"success": False, "error": "Недопустимый запрос"}, status=400
        )

    form = ApplicationForm(request.POST)
    if form.is_valid():
        application = form.save(commit=False)
        if hasattr(request, "locality") and request.locality:
            application.locality = request.locality
        application.save()
        return JsonResponse({"success": True})
    else:
        errors = {}
        for field, error_list in form.errors.items():
            errors[field] = [str(error) for error in error_list]
        return JsonResponse({"success": False, "errors": errors}, status=400)


def office_list(request, locality_slug):
    locality = get_object_or_404(Locality, slug=locality_slug, is_active=True)
    offices = Office.objects.filter(locality=locality).prefetch_related("schedules")

    context = {
        "locality": locality,
        "offices": offices,
        "title": f"Офис обслуживания в {locality.name_prepositional}",
        "meta_title": f"Офисы обслуживания АТК в {locality.name_prepositional}",
        "meta_description": f"Контакты и адреса офисов обслуживания АТК в {locality.name_prepositional}. Узнайте расписание работы и как связаться с нами.",
        "breadcrumbs": [
            {"title": "Главная", "url": "core:home"},
            {"title": "Офисы обслуживания", "url": None},
        ],
    }

    return render(request, "core/offices.html", context)


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


def internet_tariffs(request, locality_slug):
    locality = get_object_or_404(Locality, slug=locality_slug)
    service = get_object_or_404(Service, slug="internet")
    tariffs = Tariff.objects.filter(
        service=service, localities__slug=locality_slug, is_active=True
    )
    devices = Device.objects.filter(service_types=service).distinct()
    return render(
        request,
        "tariffs/internet.html",
        {
            "tariffs": tariffs,
            "devices": devices,
            "locality_slug": locality_slug,
            "locality": locality,
        },
    )


def company_detail(request, locality_slug):
    locality = get_object_or_404(Locality, slug=locality_slug, is_active=True)
    company = get_object_or_404(Company)
    context = {
        "locality": locality,
        "company": company,
        "meta_title": f"{company.short_name} — реквизиты и документы",
        "meta_description": f"Узнайте реквизиты, контактные данные и документы компании {company.short_name}.",
        "title": "Реквизиты и документы",
        "documents": company.documents.order_by("-uploaded_at"),
        "breadcrumbs": [
            {"title": "Главная", "url": "core:home"},
            {"title": "Реквизиты и документы", "url": None},
        ],
    }

    return render(request, "core/company_detail.html", context)


class TariffDetailView(DetailView):
    model = Tariff
    template_name = "core/tariffs/tariff_detail.html"
    context_object_name = "tariff"

    def get_queryset(self):
        locality_slug = self.kwargs["locality_slug"]
        locality = get_object_or_404(Locality, slug=locality_slug, is_active=True)
        return Tariff.objects.filter(localities=locality, is_active=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["locality"] = get_object_or_404(
            Locality, slug=self.kwargs["locality_slug"], is_active=True
        )
        return context


def about_company(request, locality_slug):
    locality = get_object_or_404(Locality, slug=locality_slug, is_active=True)

    if request.method == "POST":
        form = FeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.ip_address = request.META.get("REMOTE_ADDR")
            feedback.save()
            return render(request, "includes/feedback_thanks.html")
    else:
        form = FeedbackForm()

    context = {
        "locality": locality,
        "title": "О компании",
        "breadcrumbs": [
            {"title": "Главная", "url": "core:home"},
            {"title": "О компании", "url": None},
        ],
        "form": form,  # Передаем форму в контекст
    }

    return render(request, "core/about/company.html", context)


def b2b_internet_view(request, locality_slug):
    locality = get_object_or_404(Locality, slug=locality_slug, is_active=True)
    success = False
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data["name"]
            email = form.cleaned_data["email"]
            message = form.cleaned_data["message"]
            # Отправка письма
            send_mail(
                subject=f"Заявка с сайта от {name}",
                message=f"Имя: {name}\nEmail: {email}\nСообщение:\n{message}",
                from_email="site@atvc.ru",
                recipient_list=["дежурный@atvc.ru"],
                fail_silently=False,
            )
            success = True
            form = ContactForm()
    else:
        form = ContactForm()

    return render(
        request,
        "core/b2b_internet.html",
        {"form": form, "success": success, "locality": locality},
    )


def feedback_form(request, locality_slug):
    locality = get_object_or_404(Locality, slug=locality_slug, is_active=True)

    if request.method == "POST":
        form = FeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.ip_address = request.META.get("REMOTE_ADDR")
            feedback.save()
            return render(
                request, "includes/feedback_thanks.html", {"locality": locality}
            )
        return render(
            request, "includes/feedback_form.html", {"form": form, "locality": locality}
        )
    else:
        form = FeedbackForm()
        return render(
            request, "includes/feedback_form.html", {"form": form, "locality": locality}
        )
