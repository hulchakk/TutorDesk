from django.db.models import Count, Q, Prefetch
from django.http import HttpResponse, HttpRequest
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import ListView, UpdateView, DetailView

from schedule.forms import StudentForm, GroupForm
from schedule.models import Student, Group


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


class GroupsView(ListView):
    model = Group
    template_name = "schedule/groups.html"
    context_object_name = "groups"

    def get_queryset(self):
        queryset = Group.active_objects

        queryset = queryset.filter(teacher=self.request.user)
        queryset = queryset.annotate(
            active_students_count=Count("students", filter=Q(students__is_active=True))
        )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if "form" not in context:
            context["form"] = GroupForm()
        return context

    def post(self, request, *args, **kwargs):
        form = GroupForm(request.POST)
        if form.is_valid():
            group = form.save(commit=False)
            group.teacher = request.user
            group.save()
            return redirect("schedule:groups")

        self.object_list = self.get_queryset()
        return render(
            request,
            self.template_name,
            self.get_context_data(form=form),
        )


class GroupUpdateView(UpdateView):
    model = Group
    form_class = GroupForm
    template_name = "schedule/forms/group_update.html"
    context_object_name = "group"
    success_url = reverse_lazy("schedule:groups")

    def get_queryset(self):
        queryset = Group.active_objects
        return queryset.filter(teacher=self.request.user)


def delete_group_view(request: HttpRequest, pk: int) -> HttpResponse:
    if request.method == "POST":
        group = Group.objects.get(pk=pk)
        group.is_active = False
        group.save()
    return redirect("schedule:groups")


class GroupStudentsView(DetailView):
    model = Group
    template_name = "schedule/group_students.html"
    context_object_name = "group"

    def get_queryset(self):
        queryset = Group.active_objects

        queryset = queryset.filter(teacher=self.request.user)

        queryset = queryset.prefetch_related(
            Prefetch("students", queryset=Student.active_objects.all())
        )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if "form" not in context:
            context["form"] = StudentForm()
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = StudentForm(request.POST)

        if form.is_valid():
            student = form.save(commit=False)
            student.group = self.object
            student.save()
            return redirect("schedule:group-students", pk=self.object.pk)

        return self.render_to_response(self.get_context_data(form=form))
