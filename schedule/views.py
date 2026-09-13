from django.views.generic import ListView

from schedule.models import Student


class StudentsView(ListView):
    model = Student
    template_name = "schedule/students.html"
    context_object_name = "students"

    def get_queryset(self):
        queryset = Student.active_objects

        queryset = queryset.filter(teacher=self.request.user)

        return queryset
