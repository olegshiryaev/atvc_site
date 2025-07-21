from django.shortcuts import redirect, get_object_or_404, render
from django.views.decorators.http import require_POST
from django.contrib import messages
import json

from apps.core.models import AdditionalService, TVChannelPackage, Tariff
from apps.equipments.models import Product, ProductVariant
from apps.orders.cart import Cart
from apps.orders.models import Order, OrderProduct

@require_POST
def add_tariff_to_cart(request, tariff_id):
    cart = Cart(request)
    tariff = get_object_or_404(Tariff, pk=tariff_id, is_active=True)
    cart.set_tariff(tariff.id)
    return redirect('cart_view')  # Название URL корзины


@require_POST
def add_product_to_cart(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, pk=product_id, is_available=True)

    variant_id = request.POST.get("variant_id") or None
    quantity = int(request.POST.get("quantity", 1))

    variant = None
    price = product.get_price()

    if variant_id and variant_id != 'null':
        variant = get_object_or_404(ProductVariant, pk=variant_id, product=product)
        price = variant.get_price()

    cart.add_product(product.id, variant.id if variant else None, quantity, price)

    return redirect("cart_view")


@require_POST
def add_service_to_cart(request, service_id):
    cart = Cart(request)
    service = get_object_or_404(AdditionalService, pk=service_id)
    cart.add_service(service.id)
    return redirect("cart_view")


@require_POST
def add_tv_package_to_cart(request, package_id):
    cart = Cart(request)
    package = get_object_or_404(TVChannelPackage, pk=package_id)
    cart.add_tv_package(package.id)
    return redirect("cart_view")


def cart_view(request, locality_slug):
    cart = Cart(request)

    # Тариф
    tariff = Tariff.objects.filter(pk=cart.cart["tariff"]).first()

    # Оборудование
    products_data = []
    for key, item in cart.cart["products"].items():
        product_id, variant_id = key.split(":")
        product = Product.objects.filter(pk=product_id).first()
        variant = (
            ProductVariant.objects.filter(pk=variant_id).first()
            if variant_id != "null"
            else None
        )
        products_data.append({
            "product": product,
            "variant": variant,
            "quantity": item["quantity"],
            "price": item["price"],
            "total": item["quantity"] * item["price"],
        })

    # Услуги
    services = AdditionalService.objects.filter(pk__in=cart.cart["services"])

    # ТВ-пакеты
    tv_packages = TVChannelPackage.objects.filter(pk__in=cart.cart["tv_packages"])

    # Подсчёт общей стоимости
    total_price = 0
    if tariff:
        total_price += tariff.get_actual_price()
    total_price += sum(item["total"] for item in products_data)
    total_price += sum(s.price for s in services)
    total_price += sum(p.price for p in tv_packages)

    context = {
        "tariff": tariff,
        "products": products_data,
        "services": services,
        "tv_packages": tv_packages,
        "total_price": total_price,
        "locality_slug": locality_slug,
    }
    return render(request, "orders/cart.html", context)



def checkout_view(request, locality_slug):
    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        street = request.POST.get('street')
        house = request.POST.get('house')
        apartment = request.POST.get('apartment')
        comment = request.POST.get('comment')
        locality_id = request.POST.get('locality_id')
        cart_json = request.POST.get('cart_data')

        if not full_name or not phone:
            messages.error(request, "Пожалуйста, заполните имя и телефон.")
            return render(request, 'checkout.html')

        try:
            cart = json.loads(cart_json)
        except Exception:
            cart = {}

        order = Order.objects.create(
            full_name=full_name,
            phone=phone,
            email=email or None,
            street=street or None,
            house=house or None,
            apartment=apartment or None,
            comment=comment or None,
            locality_id=locality_id or None,
        )

        # Добавляем тариф
        tariff_slug = cart.get('tariff')
        if tariff_slug:
            try:
                tariff = Tariff.objects.get(slug=tariff_slug)
                order.tariff = tariff
                order.save()
            except Tariff.DoesNotExist:
                pass

        # Добавляем оборудование (products)
        equipment = cart.get('equipment', {})
        for slug, item in equipment.items():
            try:
                product = Product.objects.get(slug=slug)
                # Сохраняем цену из корзины, количество - 1 (можно потом расширить)
                OrderProduct.objects.create(
                    order=order,
                    product=product,
                    quantity=item.get('quantity', 1),
                    price=item['price']
                )
            except Product.DoesNotExist:
                continue

        # Добавляем доп. услуги
        services = cart.get('services', {})
        for slug in services.keys():
            try:
                service = AdditionalService.objects.get(slug=slug)
                order.services.add(service)
            except AdditionalService.DoesNotExist:
                continue

        # Добавляем ТВ-пакеты
        tv_packages = cart.get('tv_packages', {})
        for slug in tv_packages.keys():
            try:
                tv_package = TVChannelPackage.objects.get(slug=slug)
                order.tv_packages.add(tv_package)
            except TVChannelPackage.DoesNotExist:
                continue

        messages.success(request, "Спасибо! Ваша заявка принята.")
        return redirect('checkout_success')

    # GET-запрос: показать форму
    return render(request, 'orders/checkout.html')