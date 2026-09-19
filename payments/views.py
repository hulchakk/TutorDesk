import json

from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import ListView
from django.urls import reverse

from payments.models import Order, OrderStatus
from schedule.models import Student
from services.payments.monobank import MonobankService, verify_monobank_signature


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

    webhook_url = request.build_absolute_uri(reverse("payments:monobank-webhook"))

    checkout_session = MonobankService().create_checkout_session(
        order_id=str(order.id),
        amount=total_amount,
        redirect_url=redirect_url,
        web_hook_url=webhook_url,
    )

    order.invoice_id = checkout_session.invoice_id
    order.save(update_fields=["invoice_id"])

    return redirect(checkout_session.checkout_url)


@csrf_exempt
@require_POST
def monobank_webhook_view(request) -> HttpResponse:
    x_sign = request.headers.get("X-Sign")
    if not x_sign:
        return HttpResponseBadRequest("Missing X-Sign header")

    if not verify_monobank_signature(request.body, x_sign):
        return HttpResponseBadRequest("Invalid signature")

    try:
        data = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON")

    order_id = int(data.get("reference"))
    status = data.get("status")

    if not order_id or not status:
        return HttpResponseBadRequest("Missing required fields")

    try:
        order = Order.objects.get(pk=order_id)
    except Order.DoesNotExist:
        return HttpResponse("Order not found, ignored.", status=200)

    if status == "success":
        with transaction.atomic():
            if order.status != OrderStatus.COMPLETED:
                order.status = OrderStatus.COMPLETED
                order.paid_at = timezone.now()
                order.save(update_fields=["status"])

                student = order.student
                student.lessons_count += order.lessons_amount
                student.save(update_fields=["lessons_count"])

    elif status in ["failure", "reversed", "expired"]:
        order.status = OrderStatus.FAILED
        order.save(update_fields=["status"])

    return HttpResponse("OK", status=200)
