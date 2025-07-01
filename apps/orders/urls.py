from django.urls import path
from . import views


app_name = "orders"

urlpatterns = [
    path("order/<slug:slug>/", views.order_create, name="order_create"),
    path('submit-order/', views.submit_order, name='submit_order'),
    path("cart/add/", views.add_to_cart, name="add_to_cart"),
    path("cart/", views.cart_view, name="cart"),
    path("cart/remove/", views.remove_from_cart, name="remove_from_cart"),
    path("checkout/", views.checkout, name="checkout"),
    path("order/<int:order_id>/success/", views.order_success, name="order_success"),
]