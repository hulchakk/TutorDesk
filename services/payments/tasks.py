import logging

from celery import shared_task

from services.payments.monobank import MonobankService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_receipt_task(self, order_id: int, email: str) -> None:
    from payments.models import Order

    try:
        order = Order.objects.get(pk=order_id)
        service = MonobankService()

        service.send_receipt(
            order_id=str(order.id),
            email=email,
            amount=int(order.total_amount * 100),
            order_details={
                "student": order.student.name,
                "tariff": order.tariff.name,
                "lessons": order.lessons_amount,
                "price_per_lesson": str(order.price_per_lesson),
                "total": str(order.total_amount),
            },
        )
    except Order.DoesNotExist:
        logger.error("Order %s not found for receipt", order_id)
    except Exception as exc:
        logger.exception("Failed to send receipt for order %s", order_id)
        self.retry(exc=exc, countdown=300)
