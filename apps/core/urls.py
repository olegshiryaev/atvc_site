from django.urls import path
from .views import (
    TariffDetailView,
    about_company,
    b2b_internet_view,
    company_detail,
    feedback_form,
    index,
    office_list,
    services,
    static_page_view,
    submit_application,
)

app_name = "core"

urlpatterns = [
    path("", index, name="home"),
    path("tariffs/<slug:slug>/", TariffDetailView.as_view(), name="tariff_detail"),
    path("about/", about_company, name="about"),
    path("contacts/", office_list, name="contacts"),
    path("rekvizity-i-dokumenty/", company_detail, name="company_detail"),
    path("page/<slug:slug>/", static_page_view, name="static_page"),
    path("home/<slug:service_slug>/", services, name="services"),
    path(
        "application/submit/",
        submit_application,
        name="submit_application",
    ),
    path("feedback/", feedback_form, name="feedback_form"),
    path("b2b/internet/", b2b_internet_view, name="b2b_internet"),
]
