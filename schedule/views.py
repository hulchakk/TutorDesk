from datetime import datetime, timedelta, time

from django.contrib import messages
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

from schedule.decorators import htmx_redirect_response
from schedule.forms import StudentForm, GroupForm, LessonForm, GroupLessonForm
from schedule.mixins import HTMXFormMixin
from schedule.models import Student, Group, Lesson, GroupLesson
from schedule.utils import get_week_str
from user.decorators import teacher_required
from user.mixins import TeacherRequiredMixin


class StudentsView(TeacherRequiredMixin, ListView):
    model = Student
    template_name = "schedule/students.html"
    context_object_name = "students"

    def get_queryset(self):
        return (
            Student.active_objects.filter(teacher=self.request.user)
            .prefetch_related("available_tariffs")
            .order_by("name")
        )


class StudentCreateView(TeacherRequiredMixin, HTMXFormMixin, CreateView):
    model = Student
    form_class = StudentForm
    template_name = "schedule/forms/student_create_form.html"
    success_url = reverse_lazy("schedule:students")
    success_message = "Student %(name)s added"

    def form_valid(self, form):
        form.instance.teacher = self.request.user
        return super().form_valid(form)


class StudentUpdateView(TeacherRequiredMixin, HTMXFormMixin, UpdateView):
    model = Student
    form_class = StudentForm
    template_name = "schedule/forms/student_update_form.html"
    context_object_name = "student"
    success_message = "Student %(name)s updated"

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


@teacher_required
@require_POST
@htmx_redirect_response
def delete_student_view(request: HttpRequest, pk: int) -> HttpResponse:
    student = get_object_or_404(
        Student.active_objects,
        Q(teacher=request.user) | Q(group__teacher=request.user),
        pk=pk,
    )
    student.is_active = False
    student.save()
    messages.success(request, f"Student {student.name} deleted")

    if student.group:
        return redirect("schedule:group-students", pk=student.group.pk)

    return redirect("schedule:students")


class GroupsView(TeacherRequiredMixin, ListView):
    model = Group
    template_name = "schedule/groups.html"
    context_object_name = "groups"

    def get_queryset(self):
        queryset = Group.active_objects

        queryset = queryset.filter(teacher=self.request.user)
        queryset = queryset.annotate(
            active_students_count=Count("students", filter=Q(students__is_active=True))
        )

        return queryset.order_by("name")


class GroupCreateView(TeacherRequiredMixin, HTMXFormMixin, CreateView):
    model = Group
    form_class = GroupForm
    template_name = "schedule/forms/group_create_form.html"
    success_url = reverse_lazy("schedule:groups")
    success_message = "Group %(name)s created"

    def form_valid(self, form):
        form.instance.teacher = self.request.user
        return super().form_valid(form)


class GroupUpdateView(TeacherRequiredMixin, HTMXFormMixin, UpdateView):
    model = Group
    form_class = GroupForm
    template_name = "schedule/forms/group_update_form.html"
    context_object_name = "group"
    success_url = reverse_lazy("schedule:groups")
    success_message = "Group %(name)s updated"

    def get_queryset(self):
        queryset = Group.active_objects
        return queryset.filter(teacher=self.request.user)


@teacher_required
@require_POST
@htmx_redirect_response
def delete_group_view(request: HttpRequest, pk: int) -> HttpResponse:
    group = get_object_or_404(Group.active_objects, pk=pk, teacher=request.user)
    group.is_active = False
    group.save()
    messages.success(request, f"Group {group.name} deleted")

    return redirect("schedule:groups")


class GroupStudentsView(TeacherRequiredMixin, DetailView):
    model = Group
    template_name = "schedule/group_students.html"
    context_object_name = "group"

    def get_queryset(self):
        queryset = Group.active_objects

        queryset = queryset.filter(teacher=self.request.user)

        queryset = queryset.prefetch_related(
            Prefetch(
                "students",
                queryset=Student.active_objects.prefetch_related(
                    "available_tariffs"
                ).order_by("name"),
            )
        )

        return queryset


class GroupStudentCreateView(TeacherRequiredMixin, HTMXFormMixin, CreateView):
    model = Student
    form_class = StudentForm
    template_name = "schedule/forms/group_student_create_form.html"
    success_message = "%(name)s added to the group"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["group"] = get_object_or_404(
            Group.active_objects, pk=self.kwargs["pk"], teacher=self.request.user
        )
        return context

    def form_valid(self, form):
        group = get_object_or_404(
            Group.active_objects, pk=self.kwargs["pk"], teacher=self.request.user
        )
        form.instance.group = group
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("schedule:group-students", kwargs={"pk": self.kwargs["pk"]})


def schedule_week_url(dt) -> str:
    return f"{reverse('schedule:teacher-schedule')}?week={get_week_str(dt)}"


class LessonFormMixin(HTMXFormMixin):
    """Shared behaviour of lesson create/update views."""

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        # Clicking a free slot in the schedule opens the form with ?start=YYYY-MM-DDTHH:MM
        if start := self.request.GET.get("start"):
            initial["start_datetime"] = start
        return initial

    def get_success_url(self):
        return schedule_week_url(self.object.start_datetime)


class LessonCreateView(TeacherRequiredMixin, LessonFormMixin, CreateView):
    model = Lesson
    form_class = LessonForm
    template_name = "schedule/forms/lesson_create_form.html"
    success_message = "Lesson added"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class LessonUpdateView(TeacherRequiredMixin, LessonFormMixin, UpdateView):
    model = Lesson
    form_class = LessonForm
    template_name = "schedule/forms/lesson_update_form.html"
    context_object_name = "lesson"
    success_message = "Lesson updated"


@teacher_required
@require_POST
@htmx_redirect_response
def delete_lesson_view(request: HttpRequest, pk: int) -> HttpResponse:
    lesson = get_object_or_404(
        Lesson,
        pk=pk,
        student__teacher=request.user,
    )
    lesson.delete()
    messages.success(request, "Lesson deleted")
    return redirect(schedule_week_url(lesson.start_datetime))


class GroupLessonCreateView(TeacherRequiredMixin, LessonFormMixin, CreateView):
    model = GroupLesson
    form_class = GroupLessonForm
    template_name = "schedule/forms/group_lesson_create_form.html"
    success_message = "Group lesson added"


class GroupLessonUpdateView(TeacherRequiredMixin, LessonFormMixin, UpdateView):
    model = GroupLesson
    form_class = GroupLessonForm
    template_name = "schedule/forms/group_lesson_update_form.html"
    context_object_name = "lesson"
    success_message = "Group lesson updated"


@teacher_required
@require_POST
@htmx_redirect_response
def delete_group_lesson_view(request: HttpRequest, pk: int) -> HttpResponse:
    lesson = get_object_or_404(
        GroupLesson,
        pk=pk,
        group__teacher=request.user,
    )
    lesson.delete()
    messages.success(request, "Lesson deleted")
    return redirect(schedule_week_url(lesson.start_datetime))


class TeacherScheduleView(TeacherRequiredMixin, TemplateView):
    template_name = "schedule/teacher_schedule.html"

    # Free slots ("windows") are shown inside working hours only.
    work_day_start = time(9)
    work_day_end = time(21)
    min_gap = timedelta(minutes=15)

    def _build_timeline(self, day_date, day_lessons) -> list[dict]:
        cursor = timezone.make_aware(datetime.combine(day_date, self.work_day_start))
        day_end = timezone.make_aware(datetime.combine(day_date, self.work_day_end))
        timeline = []

        def add_gap(start, end):
            if end - start >= self.min_gap:
                timeline.append(
                    {
                        "type": "GAP",
                        "start_datetime": start,
                        "end_datetime": end,
                        "start_param": timezone.localtime(start).strftime(
                            "%Y-%m-%dT%H:%M"
                        ),
                    }
                )

        for lesson in day_lessons:
            add_gap(cursor, lesson.start_datetime)
            # max() keeps overlapping lessons from moving the cursor backwards
            cursor = max(cursor, lesson.start_datetime + lesson.duration)

            is_individual = hasattr(lesson, "student")
            timeline.append(
                {
                    "type": "INDIVIDUAL" if is_individual else "GROUP",
                    "id": lesson.id,
                    "start_datetime": lesson.start_datetime,
                    "duration": int(lesson.duration.total_seconds() // 60),
                    "status": lesson.status,
                    "status_display": lesson.get_status_display(),
                    "name": lesson.student.name if is_individual else lesson.group.name,
                }
            )

        add_gap(cursor, day_end)
        return timeline

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

        today = timezone.localdate()
        schedule = []

        for day_id in range(7):
            day_date = (start_of_week + timedelta(days=day_id)).date()

            day_lessons = [
                lesson
                for lesson in [*lessons, *group_lessons]
                if timezone.localtime(lesson.start_datetime).date() == day_date
            ]
            day_lessons.sort(key=lambda x: x.start_datetime)

            schedule.append(
                {
                    "date": day_date,
                    "is_today": day_date == today,
                    "timeline": self._build_timeline(day_date, day_lessons),
                }
            )

        context["schedule"] = schedule

        prev_week = start_of_week - timedelta(days=7)
        next_week = start_of_week + timedelta(days=7)

        context["prev_week_str"] = prev_week.date().strftime("%G-W%V")
        context["next_week_str"] = next_week.date().strftime("%G-W%V")
        context["start_of_week"] = start_of_week.date()
        context["end_of_week"] = end_of_week.date() - timedelta(days=1)
        context["is_current_week"] = start_of_week.date() <= today < end_of_week.date()

        return context
