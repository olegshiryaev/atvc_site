from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.cities.models import Locality
from apps.core.models import AdditionalService, TVChannel, TVChannelPackage, Tariff
from apps.equipments.models import Product, ProductVariant
from apps.orders.forms import OrderForm
from apps.orders.models import CartItem, Order, OrderProduct
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

    products = tariff.products.all().select_related('category')
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

            # Обработка продуктов
            equipment_ids = form.cleaned_data.get("selected_equipment_ids", [])
            payment_options = form.cleaned_data.get("equipment_payment_options", {})
            logger.debug(f"Обработка продуктов: equipment_ids={equipment_ids}, payment_options={payment_options}")
            for product_id in equipment_ids:
                product = get_object_or_404(Product, id=product_id)
                payment_type = payment_options.get(str(product_id), 'purchase')
                price = product.price  # Цена по умолчанию для покупки
                if payment_type == 'installment12' and product.installment_12_months:
                    price = int(product.installment_12_months)
                elif payment_type == 'installment24' and product.installment_24_months:
                    price = int(product.installment_24_months)
                elif payment_type == 'installment48' and product.installment_48_months:
                    price = int(product.installment_48_months)
                OrderProduct.objects.create(
                    order=order,
                    product=product,
                    price=price,
                    quantity=1,
                    payment_type=payment_type
                )

            # Обработка услуг
            service_slugs = form.cleaned_data.get("selected_service_slugs", [])
            if service_slugs:
                order.services.set(AdditionalService.objects.filter(slug__in=service_slugs))
                logger.debug(f"Добавлены услуги: {service_slugs}")

            # Обработка ТВ-пакетов
            tv_package_ids = form.cleaned_data.get("selected_tv_package_ids", [])
            if tv_package_ids:
                order.tv_packages.set(TVChannelPackage.objects.filter(id__in=tv_package_ids))

            # Логирование и уведомление
            logger.info(
                f"Заявка #{order.id} создана для {locality.name}, тариф: {tariff.name}"
            )
            try:
                admin_url = request.build_absolute_uri(f"/admin/orders/order/{order.id}/change/")
                send_order_notification.delay(order.id, admin_url)
                logger.info(f"Задача отправки уведомления о заявке #{order.id} поставлена в очередь")
            except Exception as e:
                logger.error(f"Ошибка постановки задачи уведомления о заявке #{order.id}: {str(e)}")

            # Если запрос AJAX, возвращаем JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    "success": True,
                    "message": "Заявка успешно отправлена! Мы свяжемся с вами в течение часа.",
                    "order_id": order.id,
                    "locality_slug": locality_slug
                })
            # Иначе редирект
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

        # Обработка продуктов
        equipment_ids = form.cleaned_data.get("selected_equipment_ids", [])
        payment_options = form.cleaned_data.get("equipment_payment_options", {})
        logger.debug(f"Обработка продуктов: equipment_ids={equipment_ids}, payment_options={payment_options}")

        for product_id in equipment_ids:
            product = get_object_or_404(Product, id=product_id)

            # === ОБРАБОТКА ВАРИАНТА (цвета) ===
            variant = None
            variant_id = request.POST.get(f"variant_id")
            if variant_id:
                try:
                    variant = ProductVariant.objects.get(id=variant_id, product=product)
                except ProductVariant.DoesNotExist:
                    logger.warning(f"Variant {variant_id} не найден для продукта {product_id}, используется базовая цена")
            
            # Определяем базовую цену (из варианта или продукта)
            base_price = variant.get_price() if variant else product.get_price()

            # Определяем тип оплаты
            payment_type = payment_options.get(str(product_id), 'purchase')

            # Рассчитываем итоговую цену в зависимости от типа оплаты
            if payment_type == 'installment12' and product.installment_12_months:
                total_price = product.get_total_installment_price(12)
            elif payment_type == 'installment24' and product.installment_24_months:
                total_price = product.get_total_installment_price(24)
            elif payment_type == 'installment48' and product.installment_48_months:
                total_price = product.get_total_installment_price(48)
            else:
                total_price = base_price  # Покупка — цена из варианта или продукта

            # Создаём запись в заказе
            OrderProduct.objects.create(
                order=order,
                product=product,
                variant=variant,
                price=total_price,
                quantity=1,
                payment_type=payment_type
            )

        # Обработка услуг
        service_slugs = form.cleaned_data.get("selected_service_slugs", [])
        if service_slugs:
            order.services.set(AdditionalService.objects.filter(slug__in=service_slugs))
            logger.debug(f"Добавлены услуги: {service_slugs}")

        # Обработка ТВ-пакетов
        tv_package_ids = form.cleaned_data.get("selected_tv_package_ids", [])
        if tv_package_ids:
            order.tv_packages.set(TVChannelPackage.objects.filter(id__in=tv_package_ids))
            logger.debug(f"Добавлены ТВ-пакеты: {tv_package_ids}")

        # Логирование и уведомление
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
    

# def add_to_cart(request, locality_slug):
#     if request.method == "POST":
#         cart = request.session.get("cart", {"products": {}, "tariff": None, "services": {}, "tv_packages": {}})
#         item_type = request.POST.get("item_type")  # product, tariff, service, tv_package
#         quantity = int(request.POST.get("quantity", 1))

#         if item_type == "product":
#             variant_id = request.POST.get("variant_id")
#             variant = get_object_or_404(ProductVariant, id=variant_id)
#             product = variant.product
#             price = variant.price if variant.price is not None else product.price or 0
#             cart_key = f"variant_{variant_id}"

#             # Проверка остатка на складе
#             if variant.stock < quantity:
#                 return JsonResponse({"success": False, "message": "Недостаточно товара на складе"}, status=400)

#             if cart_key in cart["products"]:
#                 cart["products"][cart_key]["quantity"] += quantity
#             else:
#                 cart["products"][cart_key] = {
#                     "product_id": product.id,
#                     "variant_id": variant_id,
#                     "quantity": quantity,
#                     "price": price,
#                     "name": product.name,
#                     "color": variant.get_color_display(),
#                 }

#         elif item_type == "tariff":
#             tariff_id = request.POST.get("tariff_id")
#             tariff = get_object_or_404(Tariff, id=tariff_id)
#             cart["tariff"] = {
#                 "id": tariff.id,
#                 "name": tariff.name,
#                 "price": tariff.price,
#             }

#         elif item_type == "service":
#             service_id = request.POST.get("service_id")
#             service = get_object_or_404(AdditionalService, id=service_id)
#             cart["services"][str(service_id)] = {
#                 "id": service.id,
#                 "name": service.name,
#                 "price": service.price,
#             }

#         elif item_type == "tv_package":
#             tv_package_id = request.POST.get("tv_package_id")
#             tv_package = get_object_or_404(TVChannelPackage, id=tv_package_id)
#             cart["tv_packages"][str(tv_package_id)] = {
#                 "id": tv_package.id,
#                 "name": tv_package.name,
#                 "price": tv_package.price,
#             }

#         request.session["cart"] = cart
#         request.session.modified = True
#         return JsonResponse({"success": True, "message": "Элемент добавлен в корзину"})

#     return JsonResponse({"success": False, "message": "Неверный запрос"}, status=400)

def cart_view(request, locality_slug):
    cart = request.session.get("cart", {"products": {}, "tariff": None, "services": {}, "tv_packages": {}})
    cart_items = {"products": [], "tariff": None, "services": [], "tv_packages": []}
    total_price = 0

    # Товары (основное внимание на ProductVariant)
    for key, item in cart["products"].items():
        variant = ProductVariant.objects.get(id=item["variant_id"])
        product = variant.product
        item_total = item["quantity"] * item["price"]
        cart_items["products"].append({
            "product": product,
            "variant": variant,
            "quantity": item["quantity"],
            "price": item["price"],
            "total": item_total,
        })
        total_price += item_total

    # Тариф
    if cart["tariff"]:
        cart_items["tariff"] = cart["tariff"]
        total_price += cart["tariff"]["price"]

    # Услуги
    for key, service in cart["services"].items():
        cart_items["services"].append(service)
        total_price += service["price"]

    # ТВ-пакеты
    for key, tv_package in cart["tv_packages"].items():
        cart_items["tv_packages"].append(tv_package)
        total_price += tv_package["price"]

    return render(request, "core/cart.html", {
        "cart_items": cart_items,
        "total_price": total_price,
        "locality_slug": locality_slug,
    })

def remove_from_cart(request, locality_slug):
    if request.method == "POST":
        item_type = request.POST.get("item_type")
        item_id = request.POST.get("item_id")
        cart = request.session.get("cart", {"products": {}, "tariff": None, "services": {}, "tv_packages": {}})

        if item_type == "product" and item_id in cart["products"]:
            del cart["products"][item_id]
        elif item_type == "tariff" and cart["tariff"]:
            cart["tariff"] = None
        elif item_type == "service" and item_id in cart["services"]:
            del cart["services"][item_id]
        elif item_type == "tv_package" and item_id in cart["tv_packages"]:
            del cart["tv_packages"][item_id]

        request.session["cart"] = cart
        request.session.modified = True
        return redirect("orders:cart", locality_slug=locality_slug)

    return JsonResponse({"success": False, "message": "Неверный запрос"}, status=400)

def checkout(request, locality_slug):
    if request.method == "POST":
        cart = request.session.get("cart", {"products": {}, "tariff": None, "services": {}, "tv_packages": {}})
        if not any([cart["products"], cart["tariff"], cart["services"], cart["tv_packages"]]):
            return redirect("orders:cart", locality_slug=locality_slug)

        # Создаем заказ
        locality = get_object_or_404(Locality, slug=locality_slug)
        order = Order.objects.create(
            full_name=request.POST.get("full_name", ""),
            phone=request.POST.get("phone"),
            email=request.POST.get("email"),
            street=request.POST.get("street"),
            house=request.POST.get("house"),
            apartment=request.POST.get("apartment"),
            comment=request.POST.get("comment"),
            locality=locality,
        )

        # Добавляем тариф
        if cart["tariff"]:
            tariff = Tariff.objects.get(id=cart["tariff"]["id"])
            order.tariff = tariff

        # Добавляем товары
        for key, item in cart["products"].items():
            OrderProduct.objects.create(
                order=order,
                product_id=item["product_id"],
                variant_id=item["variant_id"],
                quantity=item["quantity"],
                price=item["price"],
            )

        # Добавляем услуги
        if cart["services"]:
            order.services.set([AdditionalService.objects.get(id=s["id"]) for s in cart["services"].values()])

        # Добавляем ТВ-пакеты
        if cart["tv_packages"]:
            order.tv_packages.set([TVChannelPackage.objects.get(id=t["id"]) for t in cart["tv_packages"].values()])

        order.save()

        # Очищаем корзину
        request.session["cart"] = {"products": {}, "tariff": None, "services": {}, "tv_packages": {}}
        request.session.modified = True
        return redirect("orders:order_success", locality_slug=locality_slug, order_id=order.id)

    return render(request, "core/checkout.html", {"locality_slug": locality_slug})

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


@csrf_exempt
def debug_cart(request, locality_slug=None):  # Добавляем необязательный параметр
    cart_info = [
        f"Корзина ID: {request.cart.id}",
        f"Сессия: {request.session.session_key}",
        f"Товаров в корзине: {request.cart.items.count()}",
        f"Общая сумма: {request.cart.total_price()} руб.",
        f"Локация: {locality_slug}"  # Для проверки
    ]
    return HttpResponse("<br>".join(cart_info))



@require_POST
def add_to_cart(request, locality_slug):
    model_type = request.POST.get('model_type')  # 'product', 'tariff', 'tvpackage', 'service'
    object_id = request.POST.get('object_id')
    
    # Определяем модель по типу
    if model_type == 'product':
        from apps.equipments.models import Product
        model = Product
    elif model_type == 'tariff':
        from apps.core.models import Tariff
        model = Tariff
    elif model_type == 'tvpackage':
        from apps.core.models import TVChannelPackage
        model = TVChannelPackage
    elif model_type == 'service':
        from apps.core.models import AdditionalService
        model = AdditionalService
    else:
        return JsonResponse({'success': False, 'error': 'Invalid model type'})

    # Получаем объект
    obj = model.objects.get(pk=object_id)
    
    # Определяем цену
    if hasattr(obj, 'get_actual_price'):  # Для тарифов с акциями
        price = obj.get_actual_price()
    else:
        price = obj.price

    # Создаем запись в корзине
    content_type = ContentType.objects.get_for_model(model)
    cart_item, created = CartItem.objects.get_or_create(
        cart=request.cart,
        content_type=content_type,
        object_id=object_id,
        defaults={'price': price}
    )

    if not created:
        cart_item.quantity += 1
        cart_item.save()

    return JsonResponse({
        'success': True,
        'cart_total': request.cart.total_price(),
        'items_count': request.cart.items.count()
    })


def get_cart_count(request, locality_slug):
    return JsonResponse({
        'success': True,
        'items_count': request.cart.items.count()
    })


class CartView(TemplateView):
    template_name = 'orders/cart.html'

    def get(self, request, locality_slug):
        cart_items = request.cart.items.select_related('content_type').all()
        
        # Группируем товары по типам
        items_by_type = {}
        for item in cart_items:
            model_name = item.content_type.model
            if model_name not in items_by_type:
                items_by_type[model_name] = []
            item.content_object = item.content_object  # Преобразуем generic relation
            items_by_type[model_name].append(item)
        
        # Рассчитываем общую сумму
        total_price = sum(item.total_price() for item in cart_items)

        context = {
            'locality_slug': locality_slug,
            'items_by_type': items_by_type,
            'total_price': total_price,
            'cart_items_count': request.cart.items.count(),
        }
        return render(request, self.template_name, context)

    def post(self, request, locality_slug):
        action = request.POST.get('action')
        
        if action == 'update_quantity':
            item_id = request.POST.get('item_id')
            new_quantity = int(request.POST.get('quantity', 1))
            
            try:
                item = request.cart.items.get(id=item_id)
                if new_quantity > 0:
                    item.quantity = new_quantity
                    item.save()
                    messages.success(request, 'Количество обновлено')
                else:
                    item.delete()
                    messages.success(request, 'Товар удален из корзины')
            except CartItem.DoesNotExist:
                messages.error(request, 'Товар не найден в корзине')
        
        elif action == 'remove_item':
            item_id = request.POST.get('item_id')
            try:
                item = request.cart.items.get(id=item_id)
                item.delete()
                messages.success(request, 'Товар удален из корзины')
            except CartItem.DoesNotExist:
                messages.error(request, 'Товар не найден в корзине')
        
        elif action == 'clear_cart':
            request.cart.items.all().delete()
            messages.success(request, 'Корзина очищена')
        
        return redirect('orders:cart_view', locality_slug=locality_slug)
    

class EquipmentOrderView(TemplateView):
    template_name = 'orders/equipment_order.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = get_object_or_404(Product, pk=kwargs['product_id'])
        locality = get_object_or_404(Locality, slug=kwargs['locality_slug'], is_active=True)

        installment_12_total = product.get_total_installment_price(12) if product.installment_available else 0
        installment_24_total = product.get_total_installment_price(24) if product.installment_available else 0
        installment_48_total = product.get_total_installment_price(48) if product.installment_available else 0

        context.update({
            'product': product,
            'locality': locality,
            'tariff': None,
            'initial_equipment': [str(product.id)],
            'initial_payment_options': {str(product.id): 'purchase'},
            'installment_12_total': installment_12_total,
            'installment_24_total': installment_24_total,
            'installment_48_total': installment_48_total,
            'form': OrderForm(locality=locality)
        })
        return context

    def post(self, request, *args, **kwargs):
        locality = get_object_or_404(Locality, slug=kwargs['locality_slug'], is_active=True)
        product = get_object_or_404(Product, pk=kwargs['product_id'])

        form = OrderForm(request.POST, locality=locality)

        if form.is_valid():
            order = form.save(commit=False)
            order.locality = locality

            if not order.comment:
                order.comment = "Заказ оборудования"

            order.save()

            payment_options = json.loads(form.cleaned_data.get("equipment_payment_options", "{}"))
            payment_type = payment_options.get(str(product.id), 'purchase')

            # Сопоставление типа оплаты с полем цены
            if payment_type == 'installment_12' and product.installment_12_months:
                price = product.installment_12_months
            elif payment_type == 'installment_24' and product.installment_24_months:
                price = product.installment_24_months
            elif payment_type == 'installment_48' and product.installment_48_months:
                price = product.installment_48_months
            else:
                price = product.get_final_price()

            OrderProduct.objects.create(
                order=order,
                product=product,
                price=price,
                quantity=1,
                payment_type=payment_type
            )

            success_url = reverse('orders:order_success', kwargs={
                'order_id': order.id
            })

            # Ответ для AJAX
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'redirect_url': success_url
                })

            return redirect('orders:order_success', order_id=order.id)

        # Обработка ошибок (AJAX)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            errors = {field: [str(e) for e in error_list] for field, error_list in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors}, status=400)

        # Ошибки при обычном запросе
        context = self.get_context_data(**kwargs)
        context['form'] = form
        return self.render_to_response(context)