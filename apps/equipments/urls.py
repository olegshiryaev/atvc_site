from django.urls import path
from .views import equipment_list, product_detail

app_name = "equipments"

urlpatterns = [
    path("oborudovanie/", equipment_list, name="equipment_list"),
    path("product/<slug:slug>/", product_detail, name="product_detail"),
]
