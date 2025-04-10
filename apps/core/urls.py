from django.urls import path
from .views import index, internet_tariffs, office_list, submit_application, FeedbackCreateView

app_name = "core"

urlpatterns = [
    path("", index, name="home"),
    path("offices/", office_list, name="office_list"),
    path("internet/", internet_tariffs, name="internet_tariffs"),
    path(
        "application/submit/<int:tariff_id>/",
        submit_application,
        name="submit_application",
    ),
    path("feedback/", FeedbackCreateView.as_view(), name="feedback"),
]
