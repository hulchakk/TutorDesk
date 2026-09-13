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
