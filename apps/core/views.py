from django.shortcuts import get_object_or_404, redirect, render
from django.urls import resolve, reverse_lazy, reverse
from django.views.decorators.http import require_POST
from django.contrib.messages.views import SuccessMessageMixin
from django.http import JsonResponse, FileResponse
from django.views.generic import CreateView, DetailView
from django.template.loader import render_to_string
from collections import defaultdict
from django.db.models import Count, Q, Prefetch, F
from django.contrib import messages
import os
from urllib.parse import quote
import logging

from apps.equipments.models import Product
from apps.orders.forms import OrderForm

from .forms import (
    ApplicationForm,
    ContactForm,
    FeedbackForm,
)
from .models import (
    AdditionalService,
    Banner,
    Company,
    Document,
    Equipment,
    Office,
    Service,
    StaticPage,
    TVChannel,
    TVChannelPackage,
    Tariff,
    Feedback,
)
from ..cities.models import Locality
from ..news.models import News
from ..services.utils import get_client_ip
from ..services.email import send_contact_email_message
from django.core.mail import send_mail

# Определение логгера
logger = logging.getLogger(__name__)


def index(request, locality_slug):
    # Получаем населённый пункт
    locality = get_object_or_404(Locality, slug=locality_slug, is_active=True)

    # Все активные тарифы для этого населённого пункта
    tariffs = (
        Tariff.objects.filter(localities=locality, is_active=True)
        .select_related("service")
        .prefetch_related(
            Prefetch('included_channels', queryset=TVChannel.objects.all()),
            'localities',
            'tv_packages',
        )
    )

    # Собираем уникальные ТВ-пакеты, связанные с тарифами
    tv_package_ids = tariffs.values_list('tv_packages', flat=True).distinct()
    tv_packages = TVChannelPackage.objects.filter(id__in=tv_package_ids).prefetch_related('channels')

    # Группируем тарифы по типу услуги
    grouped_tariffs = defaultdict(list)
    for tariff in tariffs:
        grouped_tariffs[tariff.service].append(tariff)

    # Список доступных услуг
    available_services = (
        Service.objects.filter(id__in=tariffs.values_list("service_id", flat=True))
        .distinct()
        .order_by("name")
    )

    # Преобразуем defaultdict в обычный dict
    grouped_dict = dict(grouped_tariffs)

    # Первая услуга для активного таба
    first_service_slug = available_services[0].slug if available_services else ""

    # Новости и баннеры
    latest_news = News.objects.filter(is_published=True, localities=locality).order_by(
        "-created_at"
    )
    banners = Banner.objects.filter(is_active=True, localities=locality)

    # Популярные продукты
    popular_products = (
        Product.objects.filter(is_available=True)
        .annotate(view_count=Count("views"))
        .select_related("category")
        .prefetch_related("images")
        .order_by("-view_count")[:10]
    )

    # Инициализируем форму
    form = OrderForm()

    context = {
        "grouped_tariffs": dict(grouped_tariffs),
        "first_service_slug": first_service_slug,
        "CATEGORY_CHOICES": TVChannel.CATEGORY_CHOICES,
        "tv_packages": tv_packages,
        "locality": locality,
        "latest_news": latest_news,
        "banners": banners,
        "popular_products": popular_products,
        "form": form,
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


def office_list(request, locality_slug=None):
    localities = Locality.objects.filter(
        is_active=True,
        office__isnull=False
    ).distinct().prefetch_related('office_set', 'office_set__schedules')

    current_locality = None

    if locality_slug:
        current_locality = localities.filter(slug=locality_slug).first()

    if not current_locality:
        current_locality = localities.filter(name__icontains="Архангельск").first() or localities.first()

    # Обработка формы обратной связи
    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.ip_address = request.META.get('REMOTE_ADDR')
            feedback.save()
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True})
            messages.success(request, 'Ваше сообщение успешно отправлено!')
            return redirect(request.path)
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = FeedbackForm()

    context = {
        "localities": localities,
        "current_locality": current_locality,
        "title": "Контакты",
        "meta_title": f"Офисы обслуживания АТК {f'в {current_locality.name_prepositional}' if current_locality else ''}",
        "breadcrumbs": [
            {"title": "Главная", "url": "core:home"},
            {"title": "Контакты", "url": None},
        ],
        "form": form,
    }
    return render(request, "core/offices.html", context)


def get_items(request):
    items = ["Элемент 1", "Элемент 2", "Элемент 3"]
    return render(request, "core/items.html", {"items": items})


def about(request):
    return render(request, "core/about.html", {"title": "О нас"})


def contact(request):
    return render(request, "core/contact.html", {"title": "Контакты"})


# def internet_tariffs(request, locality_slug):
#     locality = get_object_or_404(Locality, slug=locality_slug)
#     service = get_object_or_404(Service, slug="internet")
#     tariffs = Tariff.objects.filter(
#         service=service, localities__slug=locality_slug, is_active=True
#     )
#     equipments = Equipment.objects.filter(service_types=service).distinct()
#     return render(
#         request,
#         "tariffs/internet.html",
#         {
#             "tariffs": tariffs,
#             "equipments": equipments,
#             "locality_slug": locality_slug,
#             "locality": locality,
#         },
#     )


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
        form = FeedbackCreateForm(request.POST)
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
        "form": form,
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


@require_POST
def feedback_form(request, locality_slug):
    form = FeedbackForm(request.POST)
    if form.is_valid():
        Feedback.objects.create(
            **form.cleaned_data,
            ip_address=request.META.get("REMOTE_ADDR")
        )
        if request.htmx:
            return render(request, "core/callback_success.html")
        return redirect("core:index")
    else:
        print(form.errors)  # Debug form errors
        return render(request, "core/callback_form.html", {"form": form})


def services(request, service_slug, locality_slug):
    locality = get_object_or_404(Locality, slug=locality_slug)
    service = get_object_or_404(Service, slug=service_slug)

    tariffs = (
        Tariff.objects.filter(service=service, localities=locality, is_active=True)
        .select_related("service")
        .prefetch_related("included_channels")
    )

    products = Product.objects.filter(
        is_available=True, services=service
    ).prefetch_related("images", "services")

    # Формируем breadcrumbs
    breadcrumbs = [
        {"title": "Главная", "url": "core:home"},
        {
            "title": f"Подключить {service.name.lower()} в {locality.name_prepositional}",
            "url": request.path,
        },
    ]

    title = f"Подключить {service.name.lower()} в {locality.name_prepositional}"

    context = {
        "service": service,
        "displayed_tariffs": tariffs,
        "locality": locality,
        "CATEGORY_CHOICES": TVChannel.CATEGORY_CHOICES,
        "products": products,
        "breadcrumbs": breadcrumbs,
        "title": title,
    }

    return render(request, "core/services.html", context)


def static_page_view(request, slug, locality_slug):
    locality = get_object_or_404(Locality, slug=locality_slug)
    page = get_object_or_404(StaticPage, slug=slug)

    context = {
        "page": page,
        "locality": locality,
        "title": page.title,
        "breadcrumbs": [
            {"title": "Главная", "url": "core:home"},
            {"title": page.title, "url": request.path},
        ],
    }

    return render(request, "core/static_page.html", context)