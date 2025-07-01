from django.shortcuts import get_object_or_404, redirect, render

from apps.cities.models import Locality
from apps.core.models import AdditionalService, TVChannel, TVChannelPackage, Tariff
from apps.equipments.models import Product, ProductVariant
from apps.orders.forms import OrderForm
from apps.orders.models import Order, OrderProduct
from apps.orders.tasks import send_order_notification
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages

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
    

def add_to_cart(request, locality_slug):
    if request.method == "POST":
        cart = request.session.get("cart", {"products": {}, "tariff": None, "services": {}, "tv_packages": {}})
        item_type = request.POST.get("item_type")  # product, tariff, service, tv_package
        quantity = int(request.POST.get("quantity", 1))

        if item_type == "product":
            variant_id = request.POST.get("variant_id")
            variant = get_object_or_404(ProductVariant, id=variant_id)
            product = variant.product
            price = variant.price if variant.price is not None else product.price or 0
            cart_key = f"variant_{variant_id}"

            # Проверка остатка на складе
            if variant.stock < quantity:
                return JsonResponse({"success": False, "message": "Недостаточно товара на складе"}, status=400)

            if cart_key in cart["products"]:
                cart["products"][cart_key]["quantity"] += quantity
            else:
                cart["products"][cart_key] = {
                    "product_id": product.id,
                    "variant_id": variant_id,
                    "quantity": quantity,
                    "price": price,
                    "name": product.name,
                    "color": variant.get_color_display(),
                }

        elif item_type == "tariff":
            tariff_id = request.POST.get("tariff_id")
            tariff = get_object_or_404(Tariff, id=tariff_id)
            cart["tariff"] = {
                "id": tariff.id,
                "name": tariff.name,
                "price": tariff.price,
            }

        elif item_type == "service":
            service_id = request.POST.get("service_id")
            service = get_object_or_404(AdditionalService, id=service_id)
            cart["services"][str(service_id)] = {
                "id": service.id,
                "name": service.name,
                "price": service.price,
            }

        elif item_type == "tv_package":
            tv_package_id = request.POST.get("tv_package_id")
            tv_package = get_object_or_404(TVChannelPackage, id=tv_package_id)
            cart["tv_packages"][str(tv_package_id)] = {
                "id": tv_package.id,
                "name": tv_package.name,
                "price": tv_package.price,
            }

        request.session["cart"] = cart
        request.session.modified = True
        return JsonResponse({"success": True, "message": "Элемент добавлен в корзину"})

    return JsonResponse({"success": False, "message": "Неверный запрос"}, status=400)

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