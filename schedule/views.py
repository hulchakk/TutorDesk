from datetime import datetime, timedelta, time

from django.contrib.auth.mixins import UserPassesTestMixin
from django.db.models import Count, Q, Prefetch
from django.http import HttpResponse, HttpRequest
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import (
    ListView,
    UpdateView,
    DetailView,
    CreateView,
    TemplateView,
)

from schedule.forms import StudentForm, GroupForm, LessonForm, GroupLessonForm
from schedule.mixins import HTMXFormMixin
from schedule.models import Student, Group, Lesson, GroupLesson
from schedule.utils import get_week_str


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


class StudentUpdateView(HTMXFormMixin, UpdateView):
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


class GroupUpdateView(HTMXFormMixin, UpdateView):
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


class LessonCreateView(HTMXFormMixin, CreateView):
    model = Lesson
    form_class = LessonForm
    template_name = "schedule/forms/lesson_create_form.html"
    success_url = reverse_lazy("schedule:teacher-schedule")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class LessonUpdateView(HTMXFormMixin, UpdateView):
    model = Lesson
    form_class = LessonForm
    template_name = "schedule/forms/lesson_update_form.html"
    context_object_name = "lesson"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_success_url(self):
        return f"{reverse('schedule:teacher-schedule')}?week={get_week_str(self.object.start_datetime)}"


@require_POST
def delete_lesson_view(request: HttpRequest, pk: int) -> HttpResponse:
    lesson = get_object_or_404(
        Lesson,
        pk=pk,
        student__teacher=request.user,
    )
    lesson.delete()
    return redirect("schedule:teacher-schedule")


class GroupLessonCreateView(HTMXFormMixin, CreateView):
    model = Lesson
    form_class = GroupLessonForm
    template_name = "schedule/forms/group_lesson_create_form.html"
    success_url = reverse_lazy("schedule:teacher-schedule")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class GroupLessonUpdateView(HTMXFormMixin, UpdateView):
    model = GroupLesson
    form_class = GroupLessonForm
    template_name = "schedule/forms/group_lesson_update_form.html"
    context_object_name = "lesson"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_success_url(self):
        return f"{reverse('schedule:teacher-schedule')}?week={get_week_str(self.object.start_datetime)}"


@require_POST
def delete_group_lesson_view(request: HttpRequest, pk: int) -> HttpResponse:
    lesson = get_object_or_404(
        GroupLesson,
        pk=pk,
        group__teacher=request.user,
    )
    lesson.delete()
    return redirect("schedule:teacher-schedule")


class TeacherScheduleView(UserPassesTestMixin, TemplateView):
    template_name = "schedule/teacher_schedule.html"

    def test_func(self):
        return self.request.user.is_teacher

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        week_str = self.request.GET.get("week")
        start_of_week = None

        if week_str:
            try:
                start_of_week = datetime.strptime(f"{week_str}-1", "%G-W%V-%u").date()
            except ValueError:
                start_of_week = None

        if not start_of_week:
            today = timezone.localdate()
            start_of_week = today - timedelta(days=today.weekday())

        start_of_week = timezone.make_aware(datetime.combine(start_of_week, time.min))

        end_of_week = start_of_week + timedelta(days=7)

        lessons = Lesson.objects.select_related("student").filter(
            student__teacher=self.request.user,
            start_datetime__gte=start_of_week,
            start_datetime__lt=end_of_week,
        )
        group_lessons = GroupLesson.objects.select_related("group").filter(
            group__teacher=self.request.user,
            start_datetime__gte=start_of_week,
            start_datetime__lt=end_of_week,
        )

        days = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]

        schedule = []

        for day_id in range(7):
            timeline = []
            day_date = start_of_week + timedelta(days=day_id)
            cursor = day_date

            day_lessons = [
                lesson
                for lesson in lessons
                if lesson.start_datetime.weekday() == day_id
            ] + [
                lesson
                for lesson in group_lessons
                if lesson.start_datetime.weekday() == day_id
            ]

            day_lessons.sort(key=lambda x: x.start_datetime)

            for lesson in day_lessons:
                if cursor < lesson.start_datetime:
                    timeline.append(
                        {
                            "type": "GAP",
                            "start_datetime": cursor,
                            "end_datetime": lesson.start_datetime,
                        }
                    )
                cursor = lesson.start_datetime + lesson.duration

                is_individual = hasattr(lesson, "student")

                timeline.append(
                    {
                        "type": "INDIVIDUAL" if is_individual else "GROUP",
                        "id": lesson.id,
                        "start_datetime": lesson.start_datetime,
                        "duration": int(lesson.duration.total_seconds() // 60),
                        "status": lesson.status,
                        "name": (
                            lesson.student.name if is_individual else lesson.group.name
                        ),
                    }
                )

            schedule.append(
                {
                    "name": days[day_id],
                    "date": day_date.date(),
                    "timeline": timeline,
                }
            )

        context["schedule"] = schedule

        prev_week = start_of_week - timedelta(days=7)
        next_week = start_of_week + timedelta(days=7)

        context["prev_week_str"] = prev_week.date().strftime("%G-W%V")
        context["next_week_str"] = next_week.date().strftime("%G-W%V")
        context["start_of_week"] = start_of_week.date()
        context["end_of_week"] = end_of_week.date() - timedelta(days=1)

        return context
