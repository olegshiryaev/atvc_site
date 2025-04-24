from django.urls import path
from . import views


urlpatterns = [
    path("select_locality/", views.select_locality, name="select_locality"),
    path("get_localities/", views.get_localities, name="get_localities"),
]
