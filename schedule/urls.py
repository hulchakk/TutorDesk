from django.urls import path

from schedule.views import StudentsView, delete_student_view, StudentUpdateView

urlpatterns = [
    path("students/", StudentsView.as_view(), name="students"),
    path("students/<int:pk>/", StudentUpdateView.as_view(), name="student-update"),
    path("students/<int:pk>/delete/", delete_student_view, name="student-delete"),
]

app_name = "schedule"
