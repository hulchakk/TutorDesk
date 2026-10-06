from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone


class ActiveModelsManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class Student(models.Model):
    name = models.CharField(null=False, max_length=255)
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="students",
    )
    group = models.ForeignKey(
        "Group",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="students",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="student_profiles",
    )
    is_active = models.BooleanField(null=False, default=True)

    objects = models.Manager()
    active_objects = ActiveModelsManager()

    @property
    def total_lessons_count(self) -> int:
        now = timezone.now()
        result = self.subscriptions.filter(
            models.Q(lessons_left__lt=0)
            | (
                models.Q(lessons_left__gt=0)
                & (models.Q(expires_at__gte=now) | models.Q(expires_at__isnull=True))
            )
        ).aggregate(total=models.Sum("lessons_left"))

        return result["total"] or 0

    def consume_lessons(self, count: int = 1) -> int:
        if count <= 0:
            return 0

        now = timezone.now()

        with transaction.atomic():
            active_subscriptions = list(
                self.subscriptions.select_for_update()
                .filter(lessons_left__gt=0)
                .filter(
                    models.Q(expires_at__gte=now) | models.Q(expires_at__isnull=True)
                )
                .order_by(models.F("expires_at").asc(nulls_last=True), "created_at")
            )

            remaining_to_consume = count

            for subscription in active_subscriptions:
                if remaining_to_consume <= 0:
                    break

                if subscription.lessons_left >= remaining_to_consume:
                    subscription.lessons_left -= remaining_to_consume
                    subscription.save(update_fields=["lessons_left", "updated_at"])
                    remaining_to_consume = 0
                else:
                    remaining_to_consume -= subscription.lessons_left
                    subscription.lessons_left = 0
                    subscription.save(update_fields=["lessons_left", "updated_at"])

            if remaining_to_consume > 0:
                self.subscriptions.create(
                    lessons_left=-remaining_to_consume,
                    expires_at=None,
                )

            return count

    def refund_lessons(self, count: int = 1) -> int:
        if count <= 0:
            return 0

        with transaction.atomic():
            debts = list(
                self.subscriptions.select_for_update()
                .filter(lessons_left__lt=0)
                .order_by("-created_at")
            )

            remaining_to_refund = count

            for debt in debts:
                if remaining_to_refund <= 0:
                    break

                covered = min(-debt.lessons_left, remaining_to_refund)
                debt.lessons_left += covered
                debt.save(update_fields=["lessons_left", "updated_at"])
                remaining_to_refund -= covered

            if remaining_to_refund > 0:
                self.subscriptions.create(
                    lessons_left=remaining_to_refund,
                    expires_at=None,
                )

            return count

    def clean(self):
        super().clean()
        if self.teacher and not getattr(self.teacher, "is_teacher", False):
            raise ValidationError(
                {"teacher": "User should have is_teacher=True attribute."}
            )
        if self.user and not getattr(self.user, "is_student", False):
            raise ValidationError(
                {"user": "User should have is_student=True attribute."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    (models.Q(group__isnull=False) & models.Q(teacher__isnull=True))
                    | (models.Q(group__isnull=True) & models.Q(teacher__isnull=False))
                ),
                name="exactly_one_of_group_or_teacher",
            ),
            models.UniqueConstraint(
                fields=("group", "name"),
                condition=models.Q(is_active=True),
                name="unique_student_in_group",
            ),
            models.UniqueConstraint(
                fields=("teacher", "name"),
                condition=models.Q(is_active=True),
                name="unique_student_in_teacher",
            ),
        ]

    def __str__(self):
        return self.name


class Group(models.Model):
    name = models.CharField(null=False, max_length=255)
    teacher = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="tutoring_groups",
    )
    is_active = models.BooleanField(null=False, default=True)

    objects = models.Manager()
    active_objects = ActiveModelsManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("teacher", "name"),
                condition=models.Q(is_active=True),
                name="unique_group_in_teacher",
            )
        ]

    def __str__(self):
        return self.name


class LessonStatusEnum(models.TextChoices):
    PLANNED = "planned", "Planned"
    FINISHED = "finished", "Finished"
    CANCELED = "canceled", "Canceled"


class AttendanceStatusEnum(models.TextChoices):
    PRESENT = "present", "Present"
    ABSENT = "absent", "Absent"
    SKIPPED = "skipped", "Skipped"


class LessonAbstract(models.Model):
    start_datetime = models.DateTimeField(null=False)
    duration = models.DurationField(null=False, default=timedelta(minutes=60))
    status = models.CharField(
        null=False,
        max_length=10,
        choices=LessonStatusEnum.choices,
        default=LessonStatusEnum.PLANNED,
    )

    class Meta:
        abstract = True


class Lesson(LessonAbstract):
    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name="individual_lessons"
    )

    @property
    def teacher(self):
        return self.student.teacher

    def clean(self):
        super().clean()

        if not self.start_datetime or not self.duration or not self.student_id:
            return

        end_datetime = self.start_datetime + self.duration

        student = (
            Student.objects.select_related("teacher", "user")
            .only("teacher_id", "user_id")
            .get(pk=self.student_id)
        )
        teacher_id = student.teacher_id
        student_user_id = student.user_id

        if teacher_id:
            ind_conflicts = Lesson.objects.filter(
                student__teacher_id=teacher_id,
                status=LessonStatusEnum.PLANNED,
                start_datetime__lt=end_datetime,
            ).exclude(pk=self.pk)

            for l in ind_conflicts:
                if l.start_datetime + l.duration > self.start_datetime:
                    raise ValidationError(
                        {
                            "student": "Teacher already has an individual lesson at this time."
                        }
                    )

            grp_conflicts = GroupLesson.objects.filter(
                group__teacher_id=teacher_id,
                status=LessonStatusEnum.PLANNED,
                start_datetime__lt=end_datetime,
            )

            for l in grp_conflicts:
                if l.start_datetime + l.duration > self.start_datetime:
                    raise ValidationError(
                        {"student": "Teacher already has a group lesson at this time."}
                    )

        if student_user_id:
            ind_conflicts = Lesson.objects.filter(
                student__user_id=student_user_id,
                status=LessonStatusEnum.PLANNED,
                start_datetime__lt=end_datetime,
            ).exclude(pk=self.pk)

            for l in ind_conflicts:
                if l.start_datetime + l.duration > self.start_datetime:
                    raise ValidationError(
                        {
                            "student": "Student already has an individual lesson at this time."
                        }
                    )

            grp_conflicts = GroupLesson.objects.filter(
                group__students__user_id=student_user_id,
                status=LessonStatusEnum.PLANNED,
                start_datetime__lt=end_datetime,
            )

            for l in grp_conflicts:
                if l.start_datetime + l.duration > self.start_datetime:
                    raise ValidationError(
                        {"student": "Student already has a group lesson at this time."}
                    )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Lesson(student={str(self.student)}, status={str(self.status)}, start_datetime={str(self.start_datetime)})"


class GroupLesson(LessonAbstract):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="lessons")
    attendance_list = models.JSONField(null=False, blank=True, default=list)

    def clean(self):
        super().clean()

        if not isinstance(self.attendance_list, list):
            raise ValidationError(
                {"attendance_list": "Attendance must be a list of objects."}
            )

        valid_statuses = set(AttendanceStatusEnum.values)

        for record in self.attendance_list:
            if (
                not isinstance(record, dict)
                or "student_id" not in record
                or "status" not in record
            ):
                raise ValidationError(
                    {
                        "attendance_list": "Each item must contain 'student_id' and 'status'."
                    }
                )

            if record["status"] not in valid_statuses:
                raise ValidationError(
                    {
                        "attendance_list": f"Invalid status '{record['status']}'. Allowed: {valid_statuses}"
                    }
                )

        if not self.start_datetime or not self.duration or not self.group_id:
            return

        end_datetime = self.start_datetime + self.duration

        group = (
            Group.objects.prefetch_related("students")
            .only("teacher_id")
            .get(pk=self.group_id)
        )
        teacher_id = group.teacher_id
        student_user_ids = list(
            group.students.values_list("user_id", flat=True).distinct()
        )

        if teacher_id:
            ind_conflicts = Lesson.objects.filter(
                student__teacher_id=teacher_id,
                status=LessonStatusEnum.PLANNED,
                start_datetime__lt=end_datetime,
            )
            for l in ind_conflicts:
                if l.start_datetime + l.duration > self.start_datetime:
                    raise ValidationError(
                        {
                            "group": "Teacher already has an individual lesson at this time."
                        }
                    )

            grp_conflicts = GroupLesson.objects.filter(
                group__teacher_id=teacher_id,
                status=LessonStatusEnum.PLANNED,
                start_datetime__lt=end_datetime,
            ).exclude(pk=self.pk)

            for l in grp_conflicts:
                if l.start_datetime + l.duration > self.start_datetime:
                    raise ValidationError(
                        {
                            "group": "Teacher already has another group lesson at this time."
                        }
                    )

        if student_user_ids:
            ind_conflicts = Lesson.objects.filter(
                student__user_id__in=student_user_ids,
                status=LessonStatusEnum.PLANNED,
                start_datetime__lt=end_datetime,
            )
            for l in ind_conflicts:
                if l.start_datetime + l.duration > self.start_datetime:
                    raise ValidationError(
                        {
                            "group": f"One of group students (User ID: {l.student.user_id}) has an individual lesson at this time."
                        }
                    )

            grp_conflicts = GroupLesson.objects.filter(
                group__students__user_id__in=student_user_ids,
                status=LessonStatusEnum.PLANNED,
                start_datetime__lt=end_datetime,
            ).exclude(pk=self.pk)

            for l in grp_conflicts:
                if l.start_datetime + l.duration > self.start_datetime:
                    raise ValidationError(
                        {
                            "group": "One of group students has another group lesson at this time."
                        }
                    )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"GroupLesson(group={str(self.group)}, status={str(self.status)}, start_datetime={str(self.start_datetime)})"
