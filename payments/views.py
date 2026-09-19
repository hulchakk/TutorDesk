from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.views.generic import ListView
from django.urls import reverse

from payments.models import Order
from schedule.models import Student
from services.payments.monobank import MonobankService


class StudentProfilesListView(ListView):
    template_name = "payments/student_profiles_list.html"
    context_object_name = "profiles"

    def get_queryset(self):
        return self.request.user.student_profiles.select_related(
            "teacher",
            "group",
        )


@require_POST
def buy_lessons_view(request, pk: int) -> HttpResponse:
    student = get_object_or_404(
        Student.active_objects,
        pk=pk,
        user=request.user,
    )

    lessons_amount = int(request.POST.get("lessons_amount", 1))

    order = Order.objects.create(
        student=student,
        price_per_lesson=student.lessons_price,
        lessons_amount=lessons_amount,
    )

    total_amount = int(order.price_per_lesson * lessons_amount * 100)

    redirect_url = request.build_absolute_uri(reverse("payments:student-profiles"))

    checkout_session = MonobankService().create_checkout_session(
        order_id=str(order.id),
        amount=total_amount,
        redirect_url=redirect_url,
        web_hook_url="",
    )

    order.invoice_id = checkout_session.invoice_id
    order.save(update_fields=["invoice_id"])

    return redirect(checkout_session.checkout_url)
