import json
from datetime import timedelta

from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView

from payments.models import Order, OrderStatus
from schedule.models import Student
from services.payments.interfaces import CheckoutSession, IPaymentsService
from services.payments.monobank import MonobankService, verify_monobank_signature
from subscriptions.models import StudentSubscription, TariffType


class StudentProfilesListView(ListView):
    template_name = "payments/student_profiles_list.html"
    context_object_name = "profiles"

    def get_queryset(self):
        return self.request.user.student_profiles.select_related("teacher", "group")


class AvailableTariffsView(DetailView):
    template_name = "payments/buy_lessons.html"
    context_object_name = "profile"

    def get_queryset(self):
        return Student.active_objects.filter(user=self.request.user).prefetch_related(
            "available_tariffs"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tariff_type"] = TariffType
        return context


class BuyLessonsView(View):
    def post(self, request, pk, tariff_pk):
        student = get_object_or_404(
            Student.active_objects.filter(user=request.user).prefetch_related(
                "available_tariffs"
            ),
            pk=pk,
        )
        tariff = get_object_or_404(student.available_tariffs, pk=tariff_pk)

        if tariff.tariff_type == TariffType.PER_LESSON:
            try:
                lessons_amount = int(request.POST.get("lessons_amount", 1))
                if lessons_amount <= 0:
                    lessons_amount = 1
            except (ValueError, TypeError):
                lessons_amount = 1
        elif tariff.tariff_type == TariffType.PACKAGE:
            lessons_amount = tariff.default_lessons_amount
        else:
            lessons_amount = 1

        total_amount = lessons_amount * int(tariff.price_per_lesson) * 100

        order = Order.objects.create(
            student=student,
            tariff=tariff,
            price_per_lesson=tariff.price_per_lesson,
            lessons_amount=lessons_amount,
        )

        payment_service: IPaymentsService = MonobankService()
        web_hook_url = request.build_absolute_uri(reverse("payments:monobank-webhook"))
        redirect_url = request.build_absolute_uri(reverse("payments:student-profiles"))

        checkout_session: CheckoutSession = payment_service.create_checkout_session(
            order_id=str(order.id),
            amount=total_amount,
            redirect_url=redirect_url,
            web_hook_url=web_hook_url,
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

    reference = data.get("reference")
    status = data.get("status")

    if not reference or not status:
        return HttpResponseBadRequest("Missing required fields")

    try:
        order_id = int(reference)
    except (ValueError, TypeError):
        return HttpResponseBadRequest("Invalid reference format")

    try:
        order = Order.objects.select_related("tariff", "student").get(pk=order_id)
    except Order.DoesNotExist:
        return HttpResponse("Order not found, ignored.", status=200)

    if status == "success":
        with transaction.atomic():
            if order.status != OrderStatus.COMPLETED:
                order.status = OrderStatus.COMPLETED
                order.paid_at = timezone.now()
                order.save(update_fields=["status", "paid_at"])

                student = order.student
                StudentSubscription.objects.create(
                    student=student,
                    tariff_plan=order.tariff,
                    lessons_left=order.lessons_amount,
                    expires_at=timezone.now()
                    + timedelta(days=order.tariff.duration_days),
                )

    elif status in ["failure", "reversed", "expired"]:
        order.status = OrderStatus.FAILED
        order.save(update_fields=["status"])

    return HttpResponse("OK", status=200)
