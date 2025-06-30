from django.urls import path
from . import views


app_name = "orders"

urlpatterns = [
    path("order/<slug:slug>/", views.order_create, name="order_create"),
    path('submit-order/', views.submit_order, name='submit_order'),
]