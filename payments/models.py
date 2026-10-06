from decimal import Decimal

from django.db import models

from schedule.models import Student
from subscriptions.models import TariffPlan


class OrderStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class Order(models.Model):
    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name="orders"
    )
    tariff = models.ForeignKey(
        TariffPlan, on_delete=models.CASCADE, related_name="orders"
    )

    price_per_lesson = models.DecimalField(max_digits=10, decimal_places=2)
    lessons_amount = models.PositiveIntegerField(default=1)

    status = models.CharField(
        choices=OrderStatus.choices, default=OrderStatus.PENDING, max_length=10
    )

    invoice_id = models.CharField(max_length=255, null=True)
    paid_at = models.DateTimeField(null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_amount(self) -> Decimal:
        return self.lessons_amount * self.price_per_lesson

    def __str__(self):
        return f"Order #{self.id}({self.student.name} - lessons: {self.lessons_amount}; total: {self.total_amount}; status: {self.status};)"
