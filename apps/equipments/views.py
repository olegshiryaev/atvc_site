from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import get_object_or_404, render
from django.db.models import Count, Q

from apps.cities.models import Locality
from apps.services.utils import get_client_ip
from .models import Product, Category, ViewCount
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


def equipment_list(request, locality_slug):
    # Получаем регион
    locality = get_object_or_404(Locality, slug=locality_slug)

    # Все категории
    categories = Category.objects.all()

    # Популярные товары (топ-4)
    popular_products = (
        Product.objects.filter(is_available=True)
        .annotate(view_count=Count("views"))
        .order_by("-view_count")[:4]
    )

    # Все доступные товары
    products = Product.objects.filter(is_available=True)

    # Фильтрация по категории
    category_id = request.GET.get("category")
    if category_id:
        products = products.filter(category_id=category_id)

    # Поиск
    query = request.GET.get("q", "")
    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(short_description__icontains=query)
        )

    # Сортировка
    sort_by = request.GET.get("sort_by")
    products = products.annotate(view_count=Count("views"))
    if sort_by == "price_asc":
        products = products.order_by("price", "-view_count")
    elif sort_by == "price_desc":
        products = products.order_by("-price", "-view_count")
    else:  # по популярности
        products = products.order_by("-view_count", "-price")

    # Пагинация
    paginator = Paginator(products, 12)
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
        "popular_products": popular_products,
        "products": page_obj,
        "selected_category": category_id,
        "search_query": query,
        "sort_by": sort_by,
        "breadcrumbs": breadcrumbs,
        "title": "Оборудование",
    }

    return render(request, "equipments/equipment_list.html", context)


def product_detail(request, slug, locality_slug=None):
    # Получаем продукт с предзагрузкой связанных данных
    product = get_object_or_404(
        Product.objects.select_related("category").prefetch_related("images"),
        slug=slug,
        is_available=True,
    )

    # Увеличиваем счётчик просмотров
    ip_address = get_client_ip(request)
    session_key = request.session.session_key
    user = request.user if request.user.is_authenticated else None
    now = timezone.now()
    last_24_hours = now - timedelta(hours=24)

    viewed_recently = ViewCount.objects.filter(
        product=product,
        ip_address=ip_address,
        session_key=session_key,
        viewed_on__gte=last_24_hours,
    ).exists()

    if not viewed_recently:
        ViewCount.objects.create(
            product=product,
            ip_address=ip_address,
            session_key=session_key,
            user=user,
        )

    # Формируем breadcrumbs
    breadcrumbs = [
        {
            "title": "Оборудование",
            "url": "equipments:equipment_list",  # 👈 имя маршрута, не путь
        }
    ]

    if product.category:
        breadcrumbs.append(
            {
                "title": product.category.name,
                "url": "equipments:equipment_list",  # тот же маршрут
                "query": f"?category={product.category.id}",  # 👈 передадим query отдельно
            }
        )

    breadcrumbs.append({"title": product.name, "url": None})

    # Получаем список просмотренных товаров
    viewed_products = []
    if request.user.is_authenticated:
        viewed_products = ViewCount.objects.filter(user=request.user).values_list(
            "product_id", flat=True
        )
    elif session_key:
        viewed_products = ViewCount.objects.filter(session_key=session_key).values_list(
            "product_id", flat=True
        )
    else:
        viewed_products = ViewCount.objects.filter(ip_address=ip_address).values_list(
            "product_id", flat=True
        )

    recently_viewed = (
        Product.objects.filter(id__in=viewed_products)
        .exclude(id=product.id)
        .distinct()[:5]
    )

    # Добавляем title и breadcrumbs в контекст
    context = {
        "product": product,
        "recently_viewed": recently_viewed,
        "locality_slug": locality_slug or "arhangelsk",
        "title": product.name,
        "breadcrumbs": breadcrumbs,
    }

    return render(
        request,
        "equipments/product_detail.html",
        context,
    )
