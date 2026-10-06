import logging

from celery import shared_task

from services.payments.exeptions import PaymentError
from services.payments.monobank import MonobankService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_receipt_task(self, order_id: int) -> None:
    from payments.models import Order

    order = (
        Order.objects.select_related("student__user")
        .filter(pk=order_id, invoice_id__isnull=False)
        .first()
    )

    if not order or not order.student.user:
        logger.warning(
            "Order %s has no invoice or student account for receipt", order_id
        )
        return

    try:
        MonobankService().send_receipt(order.invoice_id, order.student.user.email)
    except PaymentError as exc:
        logger.warning("Failed to send receipt for order %s: %s", order_id, exc)
        raise self.retry(exc=exc, countdown=300)
