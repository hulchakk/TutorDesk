from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class TariffType(models.TextChoices):
    PER_LESSON = "per_lesson", "Per Lesson (Flexible)"
    PACKAGE = "package", "Fixed Package / Subscription"


class TariffPlan(models.Model):
    name = models.CharField(max_length=255)
    tariff_type = models.CharField(
        max_length=20, choices=TariffType.choices, default=TariffType.PACKAGE
    )

    price_per_lesson = models.DecimalField(max_digits=10, decimal_places=2)

    default_lessons_amount = models.PositiveIntegerField(default=1)
    duration_days = models.PositiveIntegerField(null=True, blank=True)

    teachers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="tariffs",
        limit_choices_to={"is_teacher": True},
    )
    students = models.ManyToManyField(
        "schedule.Student",
        blank=True,
        related_name="available_tariffs",
    )

    is_active = models.BooleanField(default=True)

    def clean(self):
        super().clean()
        if self.tariff_type == TariffType.PACKAGE and not self.duration_days:
            raise ValidationError(
                {"duration_days": "Fixed package tariff must have duration_days set."}
            )

    @property
    def total_package_price(self):
        return self.price_per_lesson * self.default_lessons_amount

    def __str__(self):
        return f"{self.name} ({self.get_tariff_type_display()}) - {self.price_per_lesson} price/lesson"
