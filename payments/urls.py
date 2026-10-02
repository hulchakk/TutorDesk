from django.urls import path

from payments.views import (
    StudentProfilesListView,
    AvailableTariffsView,
    monobank_webhook_view,
    BuyLessonsView,
)

urlpatterns = [
    path("my_profiles/", StudentProfilesListView.as_view(), name="student-profiles"),
    path(
        "student/<int:pk>/available_tariffs/",
        AvailableTariffsView.as_view(),
        name="available-tariffs",
    ),
    path(
        "student/<int:pk>/tariff/<int:tariff_pk>/",
        BuyLessonsView.as_view(),
        name="buy-lessons",
    ),
    path("webhook/monobank/", monobank_webhook_view, name="monobank-webhook"),
]

app_name = "payments"
