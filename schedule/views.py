from django.db.models import Count, Q, Prefetch
from django.http import HttpResponse, HttpRequest
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.decorators.http import require_POST
from django.views.generic import (
    ListView,
    UpdateView,
    DetailView,
    CreateView,
    DeleteView,
)

from schedule.forms import StudentForm, GroupForm, LessonForm, GroupLessonForm
from schedule.models import Student, Group, Lesson, GroupLesson


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
        return self.render_to_response(self.get_context_data(form=form))


class StudentUpdateView(UpdateView):
    model = Student
    form_class = StudentForm
    template_name = "schedule/forms/student_update.html"
    context_object_name = "student"

    def get_queryset(self):
        queryset = Student.active_objects

        queryset = queryset.filter(
            Q(teacher=self.request.user) | Q(group__teacher=self.request.user)
        )

        return queryset

    def get_success_url(self):
        if self.object.group_id:
            return reverse(
                "schedule:group-students", kwargs={"pk": self.object.group_id}
            )

        return reverse("schedule:students")


@require_POST
def delete_student_view(request: HttpRequest, pk: int) -> HttpResponse:
    student = get_object_or_404(
        Student.active_objects,
        Q(teacher=request.user) | Q(group__teacher=request.user),
        pk=pk,
    )
    student.is_active = False
    student.save()

    if student.group:
        return redirect("schedule:group-students", pk=student.group.pk)

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
        return self.render_to_response(self.get_context_data(form=form))


class GroupUpdateView(UpdateView):
    model = Group
    form_class = GroupForm
    template_name = "schedule/forms/group_update.html"
    context_object_name = "group"
    success_url = reverse_lazy("schedule:groups")

    def get_queryset(self):
        queryset = Group.active_objects
        return queryset.filter(teacher=self.request.user)


@require_POST
def delete_group_view(request: HttpRequest, pk: int) -> HttpResponse:
    group = get_object_or_404(Group.active_objects, pk=pk, teacher=request.user)
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


class LessonCreateView(CreateView):
    model = Lesson
    form_class = LessonForm
    template_name = "schedule/forms/lesson_create_form.html"
    success_url = reverse_lazy("schedule:lesson-create")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class LessonUpdateView(UpdateView):
    model = Lesson
    form_class = LessonForm
    template_name = "schedule/forms/lesson_update_form.html"
    context_object_name = "lesson"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse("schedule:lesson-update", kwargs={"pk": self.object.pk})


@require_POST
def delete_lesson_view(request: HttpRequest, pk: int) -> HttpResponse:
    lesson = get_object_or_404(
        Lesson,
        pk=pk,
        student__teacher=request.user,
    )
    lesson.delete()
    return redirect("schedule:lesson-create")


class GroupLessonCreateView(CreateView):
    model = Lesson
    form_class = GroupLessonForm
    template_name = "schedule/forms/group_lesson_create_form.html"
    success_url = reverse_lazy("schedule:group-lesson-create")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class GroupLessonUpdateView(UpdateView):
    model = GroupLesson
    form_class = GroupLessonForm
    template_name = "schedule/forms/group_lesson_update_form.html"
    context_object_name = "lesson"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse("schedule:group-lesson-update", kwargs={"pk": self.object.pk})
