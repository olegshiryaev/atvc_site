from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.cities.models import Locality
from apps.core.models import AdditionalService, TVChannel, TVChannelPackage, Tariff
from apps.equipments.models import Product, ProductItem
from apps.orders.forms import OrderForm
from apps.orders.models import Order, OrderProduct
from django.views.generic import TemplateView
from apps.orders.tasks import send_order_notification
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages

from django.views.decorators.http import require_POST
import json
import logging




# Определение логгера
logger = logging.getLogger('orders')

def order_create(request, locality_slug, slug):
    logger.debug(f"Получен запрос: {request.method}, URL: {request.path}, POST: {dict(request.POST)}")
    locality = get_object_or_404(Locality, slug=locality_slug, is_active=True)
    tariff = get_object_or_404(Tariff, slug=slug, is_active=True)

    products = tariff.products.all().select_related('product__category')  # Изменено на products (ProductItem)
    services = AdditionalService.objects.filter(service_types=tariff.service)
    tv_packages = tariff.tv_packages.all().prefetch_related('channels')

    if request.method == "POST":
        form = OrderForm(request.POST, locality=locality)
        logger.debug(f"Полученные данные формы: {dict(request.POST)}")
        if form.is_valid():
            logger.debug(f"Очищенные данные: {form.cleaned_data}")
            order = form.save(commit=False)
            order.tariff = tariff
            order.locality = locality
            order.save()

            equipment_ids = form.cleaned_data.get("selected_equipment_ids", [])
            payment_options = form.cleaned_data.get("equipment_payment_options", {})
            logger.debug(f"Обработка продуктов: equipment_ids={equipment_ids}, payment_options={payment_options}")
            for product_id in equipment_ids:
                product_item = get_object_or_404(ProductItem, id=product_id)
                payment_type = payment_options.get(str(product_id), 'purchase')
                price = product_item.get_final_price()  # Цена по умолчанию для покупки
                if payment_type == 'installment12' and product_item.installment_12_months:
                    price = product_item.installment_12_months
                elif payment_type == 'installment24' and product_item.installment_24_months:
                    price = product_item.installment_24_months
                elif payment_type == 'installment48' and product_item.installment_48_months:
                    price = product_item.installment_48_months
                OrderProduct.objects.create(
                    order=order,
                    product=product_item.product,  # Сохраняем связь с Product
                    variant=product_item,  # Сохраняем конкретную товарную позицию
                    price=price,
                    quantity=1,
                    payment_type=payment_type
                )

            service_slugs = form.cleaned_data.get("selected_service_slugs", [])
            if service_slugs:
                order.services.set(AdditionalService.objects.filter(slug__in=service_slugs))
                logger.debug(f"Добавлены услуги: {service_slugs}")

            tv_package_ids = form.cleaned_data.get("selected_tv_package_ids", [])
            if tv_package_ids:
                order.tv_packages.set(TVChannelPackage.objects.filter(id__in=tv_package_ids))

            logger.info(f"Заявка #{order.id} создана для {locality.name}, тариф: {tariff.name}")
            try:
                admin_url = request.build_absolute_uri(f"/admin/orders/order/{order.id}/change/")
                send_order_notification.delay(order.id, admin_url)
                logger.info(f"Задача отправки уведомления о заявке #{order.id} поставлена в очередь")
            except Exception as e:
                logger.error(f"Ошибка постановки задачи уведомления о заявке #{order.id}: {str(e)}")

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    "success": True,
                    "message": "Заявка успешно отправлена! Мы свяжемся с вами в течение часа.",
                    "order_id": order.id,
                    "locality_slug": locality_slug
                })
            return redirect("orders:order_success", pk=order.id)
        else:
            logger.warning(f"Ошибка валидации формы: {form.errors}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                errors = {field: [str(e) for e in errors] for field, errors in form.errors.items()}
                non_field_errors = [str(error) for error in form.non_field_errors()]
                return JsonResponse({
                    "success": False,
                    "errors": errors,
                    "non_field_errors": non_field_errors
                }, status=400)

    else:
        form = OrderForm(locality=locality)

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
    logger.debug(f"Полученные данные формы: {request.POST}")
    locality = get_object_or_404(Locality, slug=locality_slug, is_active=True)
    form = OrderForm(request.POST, locality=locality)

    if form.is_valid():
        logger.debug(f"Очищенные данные: {form.cleaned_data}")
        order = form.save(commit=False)
        order.locality = locality
        tariff_id = form.cleaned_data.get("tariff_id")
        if tariff_id:
            order.tariff = get_object_or_404(Tariff, id=tariff_id, is_active=True)
        order.save()

        equipment_ids = form.cleaned_data.get("selected_equipment_ids", [])
        payment_options = form.cleaned_data.get("equipment_payment_options", {})
        logger.debug(f"Обработка продуктов: equipment_ids={equipment_ids}, payment_options={payment_options}")

        for product_id in equipment_ids:
            product_item = get_object_or_404(ProductItem, id=product_id)
            payment_type = payment_options.get(str(product_id), 'purchase')
            price = product_item.get_final_price()
            if payment_type == 'installment12' and product_item.installment_12_months:
                price = product_item.installment_12_months
            elif payment_type == 'installment24' and product_item.installment_24_months:
                price = product_item.installment_24_months
            elif payment_type == 'installment48' and product_item.installment_48_months:
                price = product_item.installment_48_months
            OrderProduct.objects.create(
                order=order,
                product_item=product_item,
                price=price,
                quantity=1,
                payment_type=payment_type
            )

        service_slugs = form.cleaned_data.get("selected_service_slugs", [])
        if service_slugs:
            order.services.set(AdditionalService.objects.filter(slug__in=service_slugs))
            logger.debug(f"Добавлены услуги: {service_slugs}")

        tv_package_ids = form.cleaned_data.get("selected_tv_package_ids", [])
        if tv_package_ids:
            order.tv_packages.set(TVChannelPackage.objects.filter(id__in=tv_package_ids))
            logger.debug(f"Добавлены ТВ-пакеты: {tv_package_ids}")

        logger.info(
            f"Заявка #{order.id} создана для {locality.name}, тариф: {order.tariff.name if order.tariff else 'не указан'}"
        )
        try:
            admin_url = request.build_absolute_uri(f"/admin/orders/order/{order.id}/change/")
            send_order_notification.delay(order.id, admin_url)
            logger.info(f"Задача отправки уведомления о заявке #{order.id} поставлена в очередь")
        except Exception as e:
            logger.error(f"Ошибка постановки задачи уведомления о заявке #{order.id}: {str(e)}")

        return JsonResponse({
            "success": True,
            "message": "Заявка успешно отправлена! Мы свяжемся с вами в течение часа.",
            "order_id": order.id,
            "locality_slug": locality_slug
        })
    else:
        errors = {field: [str(e) for e in errors] for field, errors in form.errors.items()}
        non_field_errors = [str(error) for error in form.non_field_errors()]
        logger.warning(f"Ошибка валидации формы: {form.errors}")
        return JsonResponse({
            "success": False,
            "errors": errors,
            "non_field_errors": non_field_errors
        }, status=400)
    

def order_success(request, locality_slug, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, "core/order_success.html", {"order": order, "locality_slug": locality_slug})

def tariff_detail(request, locality_slug, tariff_id):
    tariff = get_object_or_404(Tariff, id=tariff_id)
    return render(request, "tariff_detail.html", {
        "tariff": tariff,
        "locality_slug": locality_slug,
    })

def service_detail(request, locality_slug, service_id):
    service = get_object_or_404(AdditionalService, id=service_id)
    return render(request, "service_detail.html", {
        "service": service,
        "locality_slug": locality_slug,
    })
    

class EquipmentOrderView(TemplateView):
    template_name = 'orders/equipment_order.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            product_item = get_object_or_404(ProductItem, pk=kwargs['product_item_id'], in_stock__gt=0)
        except ProductItem.DoesNotExist:
            logger.error(f"Товарная позиция ID={kwargs['product_item_id']} недоступна или отсутствует на складе")
            return redirect('equipments:product_list', locality_slug=kwargs['locality_slug'])

        locality = get_object_or_404(Locality, slug=kwargs['locality_slug'], is_active=True)
        payment_type = self.request.GET.get('payment_type', 'purchase')

        valid_payment_types = ['purchase']
        if product_item.installment_available:
            if product_item.installment_12_months:
                valid_payment_types.append('installment12')
            if product_item.installment_24_months:
                valid_payment_types.append('installment24')
            if product_item.installment_48_months:
                valid_payment_types.append('installment48')
        if payment_type not in valid_payment_types:
            payment_type = 'purchase'

        context.update({
            'product_item': product_item,
            'product': product_item.product,
            'locality': locality,
            'installment_12_total': product_item.get_total_installment_price(12) if product_item.installment_available else 0,
            'installment_24_total': product_item.get_total_installment_price(24) if product_item.installment_available else 0,
            'installment_48_total': product_item.get_total_installment_price(48) if product_item.installment_available else 0,
            'form': OrderForm(locality=locality, initial={
                'product_item_id': product_item.id,
                'payment_type': payment_type
            }),
            'selected_payment_type': payment_type,
        })
        return context

    def post(self, request, *args, **kwargs):
        locality = get_object_or_404(Locality, slug=kwargs['locality_slug'], is_active=True)
        product_item = get_object_or_404(ProductItem, pk=kwargs['product_item_id'], in_stock__gt=0)
        form = OrderForm(request.POST, locality=locality)

        if form.is_valid():
            try:
                order = form.save(commit=False)
                order.locality = locality
                if not order.comment:
                    order.comment = f"Заказ оборудования: {product_item.get_display_name()}"
                order.save()

                price = product_item.get_final_price()
                payment_type = form.cleaned_data['payment_type']
                if payment_type.startswith('installment'):
                    months = int(payment_type.replace('installment', ''))
                    installment_price = product_item.get_installment_price(months)
                    price = installment_price if installment_price else price

                OrderProduct.objects.create(
                    order=order,
                    product_item=product_item,
                    price=price,
                    quantity=1,
                    payment_type=payment_type
                )

                logger.info(f"Создан заказ #{order.id} для {product_item.get_display_name()} (пользователь: {order.full_name})")
                success_url = reverse('orders:order_success', kwargs={
                    'locality_slug': locality.slug,
                    'order_id': order.id
                })

                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'redirect_url': success_url
                    })

                return redirect('orders:order_success', locality_slug=locality.slug, order_id=order.id)
            except Exception as e:
                logger.error(f"Ошибка создания заказа для product_item_id={kwargs['product_item_id']}: {str(e)}")
                raise
        else:
            logger.warning(f"Ошибка валидации формы заказа: {form.errors}")

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            errors = {field: [str(e) for e in error_list] for field, error_list in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors}, status=400)

        context = self.get_context_data(**kwargs)
        context['form'] = form
        return self.render_to_response(context)