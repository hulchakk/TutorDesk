from django.urls import path

from payments.views import (
    StudentProfilesListView,
    buy_lessons_view,
    monobank_webhook_view,
)

urlpatterns = [
    path("my_profiles/", StudentProfilesListView.as_view(), name="student-profiles"),
    path("student/<int:pk>/buy_lessons/", buy_lessons_view, name="buy-lessons"),
    path("webhook/monobank/", monobank_webhook_view, name="monobank-webhook"),
]

app_name = "payments"
