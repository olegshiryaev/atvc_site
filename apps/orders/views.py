from django.shortcuts import get_object_or_404, redirect, render

from apps.cities.models import Locality
from apps.core.models import AdditionalService, TVChannel, Tariff
from apps.equipments.models import Product
from apps.orders.forms import OrderForm
from apps.orders.tasks import send_order_notification
from django.http import JsonResponse

from django.views.decorators.http import require_POST
import logging




# Определение логгера
logger = logging.getLogger(__name__)

def order_create(request, locality_slug, slug):
    locality = get_object_or_404(Locality, slug=locality_slug)
    tariff = get_object_or_404(Tariff, slug=slug)

    products = Product.objects.filter(services__in=[tariff.service]).distinct()
    services = AdditionalService.objects.filter(service_types=tariff.service)
    tv_packages = tariff.tv_packages.all()

    if request.method == "POST":
        form = OrderForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.tariff = tariff
            order.locality = locality
            order.save()

            # Получаем ID продуктов из формы
            product_ids = request.POST.getlist("selected_product_ids")
            service_slugs = request.POST.getlist("selected_service_slugs")
            tv_package_ids = request.POST.getlist("selected_tv_package_ids")

            # Сохраняем ManyToMany связи
            if product_ids:
                order.products.set(product_ids)
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
            "products": products,
            "services": services,
            "tv_packages": tv_packages,
            "CATEGORY_CHOICES": TVChannel.CATEGORY_CHOICES,
            "form": form,
            "locality": locality,
        },
    )


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