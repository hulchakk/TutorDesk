from django.http import HttpResponse, HttpRequest
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import ListView, UpdateView

from schedule.forms import StudentForm
from schedule.models import Student


class StudentsView(ListView):
    model = Student
    template_name = "schedule/students.html"
    context_object_name = "students"

    def get_queryset(self):
        queryset = Student.active_objects

        queryset = queryset.filter(teacher=self.request.user)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if "form" not in context:
            context["form"] = StudentForm()
        return context

    def post(self, request, *args, **kwargs):
        form = StudentForm(request.POST)
        if form.is_valid():
            student = form.save(commit=False)
            student.teacher = request.user
            student.save()
            return redirect("schedule:students")

        self.object_list = self.get_queryset()
        return render(
            request,
            self.template_name,
            self.get_context_data(form=form),
        )


class StudentUpdateView(UpdateView):
    model = Student
    form_class = StudentForm
    template_name = "schedule/forms/student_update.html"
    context_object_name = "student"
    success_url = reverse_lazy("schedule:students")

    def get_queryset(self):
        queryset = Student.active_objects
        return queryset.filter(teacher=self.request.user)


def delete_student_view(request: HttpRequest, pk: int) -> HttpResponse:
    if request.method == "POST":
        student = Student.objects.get(pk=pk)
        student.is_active = False
        student.save()
    return redirect("schedule:students")
