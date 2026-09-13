from django.urls import path

from schedule.views import StudentsView

urlpatterns = [
    path("students/", StudentsView.as_view(), name="students"),
]

app_name = "schedule"
