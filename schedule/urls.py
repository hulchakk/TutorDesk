from django.urls import path

from schedule.views import (
    StudentsView,
    delete_student_view,
    StudentUpdateView,
    GroupsView,
    delete_group_view,
)

urlpatterns = [
    path("students/", StudentsView.as_view(), name="students"),
    path("students/<int:pk>/", StudentUpdateView.as_view(), name="student-update"),
    path("students/<int:pk>/delete/", delete_student_view, name="student-delete"),
    path("groups/", GroupsView.as_view(), name="groups"),
    path("groups/<int:pk>/delete/", delete_group_view, name="group-delete"),
]

app_name = "schedule"
