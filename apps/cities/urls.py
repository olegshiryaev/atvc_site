from django.urls import path
from . import views


urlpatterns = [
    path("select_city/", views.select_city, name="select_city"),
    path("get_cities/", views.get_cities, name="get_cities"),
]
