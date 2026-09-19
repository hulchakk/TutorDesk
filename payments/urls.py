from django.urls import path

from payments.views import StudentProfilesListView, buy_lessons_view

urlpatterns = [
    path("my_profiles/", StudentProfilesListView.as_view(), name="student-profiles"),
    path("student/<int:pk>/buy_lessons/", buy_lessons_view, name="buy_lessons"),
]

app_name = "payments"
