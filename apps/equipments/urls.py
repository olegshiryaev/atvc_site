from django.urls import path
from .views import download_instruction, equipment_list, product_detail

app_name = "equipments"

urlpatterns = [
    path("oborudovanie/", equipment_list, name="equipment_list"),
    path("product/<slug:slug>/", product_detail, name="product_detail"),
    path('product/<slug:slug>/instruction/', download_instruction, name='download_instruction'),
]
