from django.urls import path

from schedule.views import (
    StudentsView,
    delete_student_view,
    StudentUpdateView,
    GroupsView,
    delete_group_view,
    GroupUpdateView,
    GroupStudentsView,
    LessonCreateView,
    LessonUpdateView,
    delete_lesson_view,
)

urlpatterns = [
    path("students/", StudentsView.as_view(), name="students"),
    path("students/<int:pk>/", StudentUpdateView.as_view(), name="student-update"),
    path("students/<int:pk>/delete/", delete_student_view, name="student-delete"),
    path("groups/", GroupsView.as_view(), name="groups"),
    path("groups/<int:pk>/", GroupUpdateView.as_view(), name="group-update"),
    path("groups/<int:pk>/delete/", delete_group_view, name="group-delete"),
    path(
        "groups/<int:pk>/students/", GroupStudentsView.as_view(), name="group-students"
    ),
    path("lessons/create/", LessonCreateView.as_view(), name="lesson-create"),
    path("lessons/<int:pk>/", LessonUpdateView.as_view(), name="lesson-update"),
    path("lessons/<int:pk>/delete/", delete_lesson_view, name="lesson-delete"),
]

app_name = "schedule"
