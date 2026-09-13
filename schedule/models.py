from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth import get_user_model


class ActiveModelsManager(models.Manager):
    def get_queryset(self):
        return super(ActiveModelsManager, self).get_queryset().filter(is_active=True)


class Student(models.Model):
    name = models.CharField(null=False, max_length=255)
    teacher = models.ForeignKey(
        get_user_model(),
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

    lessons_count = models.IntegerField(null=False, default=0)

    user = models.ForeignKey(
        get_user_model(),
        null=False,
        on_delete=models.CASCADE,
        related_name="student_profiles",
    )
    is_active = models.BooleanField(null=False, default=True)

    objects = models.Manager()
    active_objects = ActiveModelsManager()

    def clean(self):
        super().clean()
        if self.teacher and not self.teacher.is_teacher:
            raise ValidationError(
                {"teacher": "User should have is_teacher=True attribute."}
            )
        if not self.user.is_student:
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
            )
        ]


class Group(models.Model):
    name = models.CharField(null=False, max_length=255)

    is_active = models.BooleanField(null=False, default=True)

    objects = models.Manager()
    active_objects = ActiveModelsManager()


class LessonStatusEnum(models.TextChoices):
    PLANNED = "planned"
    FINISHED = "finished"
    CANCELED = "canceled"


class Lesson(models.Model):
    start_datetime = models.DateTimeField(null=False)
    duration = models.DurationField(null=False, default=60)
    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name="individual_lessons"
    )
    status = models.CharField(
        null=False,
        max_length=8,
        choices=LessonStatusEnum,
        default=LessonStatusEnum.PLANNED,
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
            teacher_conflicts = Lesson.objects.filter(
                student__teacher_id=teacher_id,
                status=LessonStatusEnum.PLANNED,
                start_datetime__lt=end_datetime,
            ).exclude(pk=self.pk)

            for lesson in teacher_conflicts:
                if lesson.start_datetime + lesson.duration > self.start_datetime:
                    raise ValidationError(
                        {"student": "Teacher already has lesson at this time."}
                    )

        if student_user_id:
            student_conflicts = Lesson.objects.filter(
                student__user_id=student_user_id,
                status=LessonStatusEnum.PLANNED,
                start_datetime__lt=end_datetime,
            ).exclude(pk=self.pk)

            for lesson in student_conflicts:
                if lesson.start_datetime + lesson.duration > self.start_datetime:
                    raise ValidationError(
                        {"student": "Student already has lesson at this time."}
                    )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
