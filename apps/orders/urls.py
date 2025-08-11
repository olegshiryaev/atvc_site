from django.urls import path
from . import views
from . import views_cart

app_name = "orders"

urlpatterns = [
    path("order/<slug:slug>/", views.order_create, name="order_create"),
    path('order-equipment/<int:product_item_id>/',
        views.EquipmentOrderView.as_view(),
        name='equipment_order'),
    path("submit-order/", views.submit_order, name="submit_order"),
    path('cart/', views.CartView.as_view(), name='cart_view'),
    # path("cart/add/", views.add_to_cart, name="add_to_cart"),
    path('get-cart-count/', views.get_cart_count, name='get_cart_count'),
    path("cart/remove/", views.remove_from_cart, name="remove_from_cart"),
    path('debug-cart/', views.debug_cart, name='debug_cart'),
    path('add-to-cart/', views.add_to_cart, name='add_to_cart'),
    path("order-success/<int:order_id>/", views.order_success, name="order_success"),
    path("cart/add-tariff/<int:tariff_id>/", views_cart.add_tariff_to_cart, name="add_tariff_to_cart"),
    path("cart/add-product/<int:product_id>/", views_cart.add_product_to_cart, name="add_product_to_cart"),
    path("cart/add-service/<int:service_id>/", views_cart.add_service_to_cart, name="add_service_to_cart"),
    path("cart/add-tv-package/<int:package_id>/", views_cart.add_tv_package_to_cart, name="add_tv_package_to_cart"),
    path("cart/", views_cart.cart_view, name="cart_view"),
    path('checkout/', views_cart.checkout_view, name='checkout_view'),
]