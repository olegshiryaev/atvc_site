from django.forms import ValidationError
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
from django.db import transaction
import logging

from apps.services.utils import is_business_hours




# Определение логгера
logger = logging.getLogger('orders')


def process_order_data(order, form_data, logger):
    with transaction.atomic():
        # Обработка тарифов
        tariff_ids = list(set(
            ([form_data.get("tariff_id")] if form_data.get("tariff_id") else []) +
            (form_data.get("tariff_ids", []) or [])
        ))
        tariffs = Tariff.objects.filter(id__in=tariff_ids, is_active=True).select_related('service')
        if tariffs.exists():
            order.tariffs.set(tariffs)
            logger.debug(f"Добавлены тарифы: {list(tariffs.values_list('name', flat=True))}")
        else:
            logger.debug("Ни один тариф не был добавлен (не найдены или неактивны)")

        # --- 🔥 КЛЮЧЕВОЕ ИЗМЕНЕНИЕ: Проверяем наличие оборудования ---
        equipment_ids = form_data.get("selected_equipment_ids") or []
        if not isinstance(equipment_ids, list):
            logger.warning(f"Поле selected_equipment_ids не является списком: {equipment_ids}")
            equipment_ids = []

        # Получаем payment_options ТОЛЬКО если есть оборудование
        payment_options = {}
        if equipment_ids:
            payment_options = form_data.get("equipment_payment_options", {})
            if not isinstance(payment_options, dict):
                logger.warning(f"Поле equipment_payment_options не является словарем: {payment_options}")
                payment_options = {}

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
                payment_type=payment_type
            )

        # Обработка дополнительных услуг
        service_slugs = form_data.get("selected_service_slugs", [])
        if service_slugs:
            services = AdditionalService.objects.filter(slug__in=service_slugs)
            order.services.set(services)
            logger.debug(f"Добавлены услуги: {list(services.values_list('name', flat=True))}")

        # Обработка ТВ-пакетов
        tv_package_ids = form_data.get("selected_tv_package_ids", [])
        if tv_package_ids:
            tv_packages = TVChannelPackage.objects.filter(id__in=tv_package_ids)
            order.tv_packages.set(tv_packages)
            logger.debug(f"Добавлены ТВ-пакеты: {list(tv_packages.values_list('name', flat=True))}")

        return tariffs

def order_create(request, locality_slug, slug):
    logger.debug(f"Получен запрос: {request.method}, URL: {request.path}, POST: {dict(request.POST)}")
    
    locality = get_object_or_404(Locality, slug=locality_slug, is_active=True)
    tariff = get_object_or_404(Tariff, slug=slug, is_active=True)

    is_internet_tariff = tariff.service.slug == "internet"
    is_tv_tariff = tariff.service.slug == "tv"

    tv_tariffs = Tariff.objects.none()
    tv_packages = TVChannelPackage.objects.none()

    if is_internet_tariff:
        tv_tariffs = Tariff.objects.filter(
            service__slug="tv",
            is_active=True,
            localities=locality
        ).prefetch_related('products', 'included_channels')
        tv_packages = TVChannelPackage.objects.filter(
            tariffs__in=tv_tariffs
        ).prefetch_related('channels', 'tariffs').distinct()
    elif is_tv_tariff:
        tv_tariffs = Tariff.objects.filter(id=tariff.id)
        tv_packages = tariff.tv_packages.all().prefetch_related('channels', 'tariffs')
        if not tv_packages.exists():
            logger.info(f"Для ТВ-тарифа {tariff.slug} нет связанных пакетов")
    else:
        logger.warning(f"Неизвестный тип услуги для тарифа {tariff.slug}")

    logger.debug(f"Количество ТВ-тарифов: {tv_tariffs.count()}, ТВ-пакетов: {tv_packages.count()}")

    products = tariff.products.all().select_related('product__category')
    services = AdditionalService.objects.filter(service_types=tariff.service).distinct()

    if request.method == "POST":
        form = OrderForm(request.POST, locality=locality)
        if form.is_valid():
            logger.debug(f"Очищенные данные формы: {form.cleaned_data}")

            order = form.save(commit=False)
            order.locality = locality
            order.save()

            selected_tariffs = process_order_data(order, form.cleaned_data, logger)

            service_ids = list(selected_tariffs.values_list('service__id', flat=True))
            if len(service_ids) != len(set(service_ids)):
                form.add_error(None, "Нельзя выбрать более одного тарифа на одну услугу.")
                return render(request, "orders/order_create.html", {
                    "form": form,
                    "tariff": tariff,
                    "tv_tariffs": tv_tariffs,
                    "products": products,
                    "services": services,
                    "tv_packages": tv_packages,
                    "locality": locality,
                    "is_tv_tariff": is_tv_tariff,
                    "is_internet_tariff": is_internet_tariff,
                    "no_tv_packages": not tv_packages.exists(),
                    "submit_order_url": reverse("orders:submit_order", kwargs={"locality_slug": locality_slug}),
                })

            try:
                send_order_notification.delay(order.id)
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
            return redirect("orders:order_success", pk=order.id, locality_slug=locality_slug)

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
        "orders/order_create.html",
        {
            "title": "Заявка на подключение",
            "breadcrumbs": [
                {"title": "Главная", "url": "core:home"},
                {"title": tariff.service.name, "url": None},
                {"title": "Заявка на подключение", "url": None},
            ],
            "tariff": tariff,
            "tv_tariffs": tv_tariffs,
            "products": products,
            "services": services,
            "tv_packages": tv_packages,
            "CATEGORY_CHOICES": TVChannel.CATEGORY_CHOICES,
            "form": form,
            "locality": locality,
            "is_tv_tariff": is_tv_tariff,
            "is_internet_tariff": is_internet_tariff,
            "no_tv_packages": not tv_packages.exists(),
            "submit_order_url": reverse("orders:submit_order", kwargs={"locality_slug": locality_slug}),
        },
    )

def submit_order(request, locality_slug):
    logger.debug(f"Полученные данные формы: {request.POST}")
    locality = get_object_or_404(Locality, slug=locality_slug, is_active=True)
    form = OrderForm(request.POST, locality=locality)

    if form.is_valid():
        logger.debug(f"Очищенные данные: {form.cleaned_data}")
        order = form.save(commit=False)
        order.locality = locality
        order.save()
        process_order_data(order, form.cleaned_data, logger)

        tariff_names = ", ".join(t.name for t in order.tariffs.all())
        logger.info(f"Заявка #{order.id} создана для {locality.name}, тарифы: {tariff_names}")

        try:
            send_order_notification.delay(order.id)
            logger.info(f"Задача отправки уведомления о заявке #{order.id} поставлена в очередь")
        except Exception as e:
            logger.error(f"Ошибка постановки задачи уведомления о заявке #{order.id}: {str(e)}")

        # --- 🔥 Определяем тип формы по скрытому полю ---
        form_type = request.POST.get('form_type', '')

        if request.headers.get('HX-Request'):  # Это htmx-запрос
            if form_type == 'address_check':
                # --- 🔥 Определяем сообщение в зависимости от времени ---
                if is_business_hours():
                    message_text = "Мы свяжемся с вами в течение часа для уточнения деталей."
                else:
                    message_text = "Ваша заявка принята. Мы свяжемся с вами в рабочее время (с 8:00 до 21:00)."
                # Возвращаем HTML для модального окна
                return HttpResponse(f"""
                    <div class="address-check__modal-content">
                        <span class="address-check__modal-close" role="button" aria-label="Закрыть модальное окно" 
                            hx-delete="" hx-target="#address-check-modal" hx-swap="delete">×</span>
                        <h3 class="address-check__modal-title" id="address-check-modal-title">Заявка отправлена!</h3>
                        <p class="address-check__modal-text">{message_text}</p>
                        <button class="address-check__modal-btn" 
                                hx-delete="" hx-target="#address-check-modal" hx-swap="delete">Закрыть</button>
                    </div>
                """)
            else:
                # Возвращаем HTML-фрагмент с редиректом для основной формы
                redirect_url = reverse("orders:order_success", kwargs={
                    "locality_slug": locality_slug,
                    "order_id": order.id
                })
                return HttpResponse(f"""
                    <div hx-trigger="load" hx-get="{redirect_url}" hx-target="body" hx-swap="outerHTML">
                        <!-- Редирект на страницу успеха -->
                    </div>
                """)
        else:
            # Если это обычный запрос, делаем стандартный редирект
            return redirect("orders:order_success", locality_slug=locality_slug, order_id=order.id)

    else:
        logger.warning(f"Ошибка валидации формы: {form.errors}")
        # --- Воссоздаем контекст и возвращаем форму с ошибками ---

        # Получаем текущий тариф (как в order_create)
        tariff_id = request.POST.get('tariff_id')
        if not tariff_id:
            tariff_ids = request.POST.getlist('tariff_ids')
            tariff_id = tariff_ids[0] if tariff_ids else None
        tariff = get_object_or_404(Tariff, id=tariff_id) if tariff_id else None

        is_internet_tariff = tariff.service.slug == "internet" if tariff else False
        is_tv_tariff = tariff.service.slug == "tv" if tariff else False

        # Получаем ТВ-тарифы (как в order_create)
        tv_tariffs = Tariff.objects.none()
        tv_packages = TVChannelPackage.objects.none()
        if is_internet_tariff and tariff:
            tv_tariffs = Tariff.objects.filter(
                service__slug="tv",
                is_active=True,
                localities=locality
            ).prefetch_related('products', 'included_channels')
            tv_packages = TVChannelPackage.objects.filter(
                tariffs__in=tv_tariffs
            ).prefetch_related('channels', 'tariffs').distinct()
        elif is_tv_tariff and tariff:
            tv_tariffs = Tariff.objects.filter(id=tariff.id)
            tv_packages = tariff.tv_packages.all().prefetch_related('channels', 'tariffs')

        # Получаем оборудование и услуги (как в order_create)
        products = tariff.products.all().select_related('product__category') if tariff else ProductItem.objects.none()
        services = AdditionalService.objects.filter(service_types=tariff.service).distinct() if tariff else AdditionalService.objects.none()

        # Рендерим всю страницу с формой и ошибками
        return render(
            request,
            "orders/order_create.html",
            {
                "form": form,  # форма с ошибками
                "tariff": tariff,
                "tv_tariffs": tv_tariffs,
                "products": products,
                "services": services,
                "tv_packages": tv_packages,
                "locality": locality,
                "is_tv_tariff": is_tv_tariff,
                "is_internet_tariff": is_internet_tariff,
                "no_tv_packages": not tv_packages.exists(),
                "submit_order_url": reverse("orders:submit_order", kwargs={"locality_slug": locality_slug}),
            },
        )
    

def order_success(request, locality_slug, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, "orders/order_success.html", {"order": order, "locality_slug": locality_slug})

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
            product_item = get_object_or_404(
                ProductItem,
                pk=kwargs['product_item_id'],
                in_stock__gt=0
            )
        except ProductItem.DoesNotExist:
            logger.error(f"Товарная позиция ID={kwargs['product_item_id']} недоступна или нет на складе")
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
                    payment_type=payment_type
                )
                logger.info(f"Создан заказ #{order.id} для {product_item.get_display_name()} (пользователь: {order.full_name})")
                # --- Отправка уведомления ---
                try:
                    send_order_notification.delay(order.id)
                    logger.info(f"Задача отправки уведомления добавлена для заказа #{order.id}")
                except Exception as e:
                    logger.error(f"Ошибка при отправке уведомления для заказа #{order.id}: {str(e)}")
                # ----------------------------
                success_url = reverse('orders:order_success', kwargs={
                    'locality_slug': locality.slug,
                    'order_id': order.id
                })

                # --- КЛЮЧЕВОЕ ИЗМЕНЕНИЕ: Возвращаем HTML-фрагмент с редиректом ---
                if request.headers.get('HX-Request'):  # Это htmx-запрос
                    return HttpResponse(f"""
                        <div hx-trigger="load" hx-get="{success_url}" hx-target="body" hx-swap="outerHTML">
                            <!-- Редирект на страницу успеха -->
                        </div>
                    """)
                else:
                    return redirect('orders:order_success', locality_slug=locality.slug, order_id=order.id)

            except Exception as e:
                logger.error(f"Ошибка создания заказа для product_item_id={kwargs['product_item_id']}: {str(e)}")
                raise
        else:
            logger.warning(f"Ошибка валидации формы заказа: {form.errors}")

        # --- КЛЮЧЕВОЕ ИЗМЕНЕНИЕ: Возвращаем HTML с формой и ошибками ---
        context = self.get_context_data(**kwargs)
        context['form'] = form
        return self.render_to_response(context)