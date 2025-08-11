from django.urls import path
from . import views

app_name = "orders"

urlpatterns = [
    path("order/<slug:slug>/", views.order_create, name="order_create"),
    path('order-equipment/<int:product_item_id>/',
        views.EquipmentOrderView.as_view(),
        name='equipment_order'),
    path("submit-order/", views.submit_order, name="submit_order"),
    path("order-success/<int:order_id>/", views.order_success, name="order_success"),
]