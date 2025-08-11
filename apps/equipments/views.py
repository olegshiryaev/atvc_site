from django.http import FileResponse, HttpRequest, HttpResponseRedirect
from django.urls import reverse
import random
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import Count, Q, Prefetch, F

from apps.cities.models import Locality
from apps.services.utils import get_client_ip
from .models import Product, Category, ProductItem, ViewCount
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


def equipment_list(request, locality_slug):
    locality = get_object_or_404(Locality, slug=locality_slug)

    # Все категории
    categories = Category.objects.all()

    # Популярные товарные позиции (топ-10 по просмотрам)
    popular_items = (
        ProductItem.objects.filter(
            product__is_available=True,
            in_stock__gt=0
        )
        .annotate(view_count=Count("views"))
        .order_by("-view_count")[:10]
    )

    # Выбираем 4 случайных из топ-10
    popular_item_ids = list(popular_items.values_list('id', flat=True))
    random_ids = random.sample(popular_item_ids, min(4, len(popular_item_ids)))

    # Получаем объекты с нужными связями
    popular_items = (
        ProductItem.objects.filter(id__in=random_ids)
        .select_related("product__category", "color", "product")
        .prefetch_related("images")
    )

    # Все доступные товарные позиции
    product_items = ProductItem.objects.filter(
        product__is_available=True,
        in_stock__gt=0
    ).select_related("product__category", "color", "product").prefetch_related("images")

    # Фильтрация по категории
    category_id = request.GET.get("category")
    if category_id:
        product_items = product_items.filter(product__category_id=category_id)

    # Поиск
    query = request.GET.get("q", "")
    if query:
        product_items = product_items.filter(
            Q(product__name__icontains=query) |
            Q(product__description__icontains=query) |
            Q(color__name__icontains=query)
        )

    # Сортировка
    sort_by = request.GET.get("sort_by")
    product_items = product_items.annotate(view_count=Count("views"))

    if sort_by == "price_asc":
        product_items = product_items.order_by("price", "-view_count")
    elif sort_by == "price_desc":
        product_items = product_items.order_by("-price", "-view_count")
    elif sort_by == "discount":
        product_items = product_items.filter(old_price__gt=0).order_by(
            F("old_price") - F("price"), "-view_count"
        )
    else:  # по популярности
        product_items = product_items.order_by("-view_count", "price")

    # Пагинация
    paginator = Paginator(product_items, 12)
    page_number = request.GET.get("page")
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    # Хлебные крошки
    breadcrumbs = [
        {"title": "Главная", "url": "core:home"},
        {"title": "Оборудование", "url": ""},
    ]

    context = {
        "locality": locality,
        "categories": categories,
        "popular_products": popular_items,
        "products": page_obj,
        "selected_category": category_id,
        "search_query": query,
        "sort_by": sort_by,
        "breadcrumbs": breadcrumbs,
        "title": "Оборудование",
    }

    return render(request, "equipments/equipment_list.html", context)


def product_detail(request: HttpRequest, slug: str, locality_slug: str = None):
    # Получаем текущий ProductItem по slug
    current_item = get_object_or_404(
        ProductItem.objects.select_related(
            'product__category',
            'color',
            'product__smart_speaker',
            'product__camera',
            'product__router',
            'product__tvbox'
        ).prefetch_related(
            'images',  # ← изображения текущего ProductItem
            'product__items',  # ← если нужно для переключения цветов (опционально)
        ),
        slug=slug,
        product__is_available=True,
        in_stock__gt=0
    )

    # Все товарные позиции этого товара (разные цвета, в наличии)
    items = ProductItem.objects.filter(
        product=current_item.product,
        in_stock__gt=0
    ).select_related('color', 'product').prefetch_related('images')

    # Увеличение счётчика просмотров
    ip_address = get_client_ip(request)
    session_key = request.session.session_key or "anonymous"
    user = request.user if request.user.is_authenticated else None
    now = timezone.now()
    last_24_hours = now - timezone.timedelta(hours=24)

    viewed_recently = ViewCount.objects.filter(
        item=current_item,
        ip_address=ip_address,
        session_key=session_key,
        viewed_on__gte=last_24_hours,
    ).exists()

    if not viewed_recently:
        ViewCount.objects.create(
            item=current_item,
            ip_address=ip_address,
            session_key=session_key,
            user=user,
        )

    # Хлебные крошки
    breadcrumbs = [
        {"title": "Оборудование", "url": "equipments:equipment_list"},
    ]
    if current_item.product.category:
        breadcrumbs.append({
            "title": current_item.product.category.name,
            "url": "equipments:equipment_list",
            "query": f"?category={current_item.product.category.id}",
        })
    breadcrumbs.append({"title": str(current_item), "url": None})

    # Недавно просмотренные
    viewed_items = []
    if user:
        viewed_items = ViewCount.objects.filter(user=user).values_list('item_id', flat=True)
    elif session_key != "anonymous":
        viewed_items = ViewCount.objects.filter(session_key=session_key).values_list('item_id', flat=True)
    else:
        viewed_items = ViewCount.objects.filter(ip_address=ip_address).values_list('item_id', flat=True)

    recently_viewed = (
        ProductItem.objects.filter(id__in=viewed_items, in_stock__gt=0)
        .exclude(id=current_item.id)
        .select_related('product', 'color')
        .prefetch_related('images')[:5]
    )

    context = {
        "current_item": current_item,
        "items": items,
        "recently_viewed": recently_viewed,
        "locality_slug": locality_slug or "arhangelsk",
        "title": str(current_item),
        "breadcrumbs": breadcrumbs,
    }

    return render(request, "equipments/product_detail.html", context)


def variant_slug_detail(request, slug, locality_slug=None):
    variant = get_object_or_404(
        ProductItem.objects.select_related("product__category", "color", "product")
        .prefetch_related("images"),
        slug=slug,
        product__is_available=True,
        stock__gt=0,
    )
    product = variant.product

    # Счётчик просмотров
    ip_address = get_client_ip(request)
    session_key = request.session.session_key
    user = request.user if request.user.is_authenticated else None
    now = timezone.now()
    last_24_hours = now - timedelta(hours=24)

    viewed_recently = ViewCount.objects.filter(
        product=product,
        variant=variant,
        ip_address=ip_address,
        session_key=session_key,
        viewed_on__gte=last_24_hours,
    ).exists()

    if not viewed_recently:
        ViewCount.objects.create(
            product=product,
            variant=variant,
            ip_address=ip_address,
            session_key=session_key,
            user=user,
        )

    # Breadcrumbs
    breadcrumbs = [
        {"title": "Оборудование", "url": "equipments:equipment_list"},
    ]
    if product.category:
        breadcrumbs.append(
            {
                "title": product.category.name,
                "url": "equipments:equipment_list",
                "query": f"?category={product.category.id}",
            }
        )
    breadcrumbs.append({"title": f"{product.name} ({variant.color.name if variant.color else 'Без цвета'})", "url": None})

    # Недавно просмотренные
    viewed_products = []
    if request.user.is_authenticated:
        viewed_products = ViewCount.objects.filter(user=request.user).values_list("product_id", flat=True)
    elif session_key:
        viewed_products = ViewCount.objects.filter(session_key=session_key).values_list("product_id", flat=True)
    else:
        viewed_products = ViewCount.objects.filter(ip_address=ip_address).values_list("product_id", flat=True)

    recently_viewed = (
        Product.objects.filter(id__in=viewed_products)
        .exclude(id=product.id)
        .distinct()[:5]
    )

    context = {
        "product": product,
        "variant": variant,
        "recently_viewed": recently_viewed,
        "locality_slug": locality_slug or "arhangelsk",
        "title": f"{product.name} — {variant.color.name}" if variant.color else product.name,
        "breadcrumbs": breadcrumbs,
    }

    return render(request, "equipments/product_detail.html", context)


def download_instruction(request, locality_slug, slug):
    locality = get_object_or_404(Locality, slug=locality_slug)
    product = get_object_or_404(Product, slug=slug)
    # Предполагается, что у продукта есть поле, например, `instruction`, с файлом инструкции
    if hasattr(product, 'instruction') and product.instruction:
        return FileResponse(product.instruction.open('rb'), as_attachment=True, filename=f"{product.name}_instruction.pdf")
    return HttpResponseRedirect('equipments:product_detail', locality_slug=locality.slug, slug=product.slug)