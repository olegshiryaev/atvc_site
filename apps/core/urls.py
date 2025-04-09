from django.urls import path
from .views import index, office_list, submit_application, FeedbackCreateView

app_name = "core"

urlpatterns = [
    path("", index, name="home"),
    path("offices/", office_list, name="office_list"),
    path(
        "application/submit/<int:tariff_id>/",
        submit_application,
        name="submit_application",
    ),
    path("feedback/", FeedbackCreateView.as_view(), name="feedback"),
]
