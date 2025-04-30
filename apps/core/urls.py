from django.urls import path
from .views import (
    TariffDetailView,
    company_detail,
    index,
    internet_tariffs,
    office_list,
    submit_application,
    FeedbackCreateView,
)

app_name = "core"

urlpatterns = [
    path("", index, name="home"),
    path("tariffs/<slug:slug>/", TariffDetailView.as_view(), name="tariff_detail"),
    path("offices/", office_list, name="office_list"),
    path("rekvizity-i-dokumenty/", company_detail, name="company_detail"),
    path("internet/", internet_tariffs, name="internet_tariffs"),
    path(
        "application/submit/",
        submit_application,
        name="submit_application",
    ),
    path("feedback/", FeedbackCreateView.as_view(), name="feedback"),
]
