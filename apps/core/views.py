from django.shortcuts import get_object_or_404, redirect, render
from django.urls import resolve, reverse_lazy, reverse
from django.views.decorators.http import require_POST
from django.contrib.messages.views import SuccessMessageMixin
from django.http import JsonResponse
from django.views.generic import CreateView, DetailView
from django.template.loader import render_to_string
from collections import defaultdict
from django.db.models import Count
from django.contrib import messages
import logging

from apps.core.tasks import send_order_notification
from apps.equipments.models import Product

from .forms import (
    ApplicationForm,
    ContactForm,
    FeedbackCreateForm,
    FeedbackForm,
    OrderForm,
)
from .models import (
    AdditionalService,
    Banner,
    Company,
    Equipment,
    Office,
    Service,
    StaticPage,
    TVChannel,
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
        .prefetch_related("localities", "included_channels")
    )

    # Группируем тарифы по типу услугиMore actions
    grouped_tariffs = defaultdict(list)
    for tariff in tariffs:
        grouped_tariffs[tariff.service].append(tariff)

    # Список доступных услуг (сортированный)
    available_services = (
        Service.objects.filter(id__in=tariffs.values_list("service_id", flat=True))
        .distinct()
        .order_by("name")
    )

    # Преобразуем defaultdict в обычный dict
    grouped_dict = dict(grouped_tariffs)

    # Определяем первую услугу для установки активного таба
    first_service_slug = available_services[0].slug if available_services else ""

    latest_news = News.objects.filter(is_published=True, localities=locality).order_by(
        "-created_at"
    )
    banners = Banner.objects.filter(is_active=True, localities=locality)

    # Получаем 10 самых популярных товаров на основе количества просмотров
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


def order_create(request, locality_slug, slug):
    locality = get_object_or_404(Locality, slug=locality_slug)
    tariff = get_object_or_404(Tariff, slug=slug)

    equipments = Equipment.objects.filter(service_types=tariff.service)
    services = AdditionalService.objects.filter(service_types=tariff.service)
    tv_packages = tariff.tv_packages.all()

    if request.method == "POST":
        form = OrderForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.tariff = tariff
            order.locality = locality
            order.save()

            # Получаем ID из формы
            equipment_ids = request.POST.getlist("selected_equipment_ids")
            service_slugs = request.POST.getlist("selected_service_slugs")
            tv_package_ids = request.POST.getlist("selected_tv_package_ids")

            # Сохраняем ManyToMany связи
            if equipment_ids:
                order.equipment.set(equipment_ids)
            if service_slugs:
                order.services.set(
                    AdditionalService.objects.filter(slug__in=service_slugs)
                )
            if tv_package_ids:
                order.tv_packages.set(tv_package_ids)

            return redirect("order_success", pk=order.pk)

    else:
        form = OrderForm()

    return render(
        request,
        "core/tariffs/order_create.html",
        {
            "title": f"Заявка на подключение",
            "breadcrumbs": [
                {"title": "Главная", "url": "core:home"},
                {"title": tariff.service.name, "url": None},
                {"title": "Заявка на подключение", "url": None},
            ],
            "tariff": tariff,
            "equipments": equipments,
            "services": services,
            "tv_packages": tv_packages,
            "CATEGORY_CHOICES": TVChannel.CATEGORY_CHOICES,
            "form": form,
            "locality": locality,
        },
    )


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
            {"title": "Главная", "url": f"/{locality.slug}/"},
            {"title": page.title, "url": request.path},
        ],
    }

    return render(request, "core/static_page.html", context)


@require_POST
def submit_order(request, locality_slug):
    locality = get_object_or_404(Locality, slug=locality_slug, is_active=True)
    form = OrderForm(request.POST, locality=locality)
    if form.is_valid():
        order = form.save(commit=False)
        order.locality = locality
        tariff_id = form.cleaned_data.get("tariff_id")
        if tariff_id:
            order.tariff = Tariff.objects.get(id=tariff_id, is_active=True)
        order.save()
        logger.info(
            f"Заявка #{order.id} создана для {locality.name}, тариф: {order.tariff.name if order.tariff else 'не указан'}"
        )

        # Асинхронная отправка уведомления
        try:
            admin_url = request.build_absolute_uri(
                f"/admin/core/order/{order.id}/change/"
            )
            send_order_notification.delay(order.id, admin_url)
            logger.info(
                f"Задача отправки уведомления о заявке #{order.id} поставлена в очередь"
            )
        except Exception as e:
            logger.error(
                f"Ошибка постановки задачи уведомления о заявке #{order.id}: {str(e)}"
            )

        return JsonResponse(
            {
                "success": True,
                "message": "Заявка успешно отправлена! Мы свяжемся с вами в течение часа.",
            }
        )
    else:
        errors = {
            field: [str(e) for e in errors] for field, errors in form.errors.items()
        }
        non_field_errors = [str(error) for error in form.non_field_errors()]
        logger.warning(f"Ошибка валидации формы: {form.errors}")
        return JsonResponse(
            {
                "success": False,
                "errors": errors,
                "non_field_errors": non_field_errors,
            },
            status=400,
        )
