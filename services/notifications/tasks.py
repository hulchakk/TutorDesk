from celery import shared_task

from services.notifications.email import EmailNotificationsService
from services.notifications.exceptions import NotificationError


@shared_task(bind=True, max_retries=3)
def send_activation_email_task(
    self, email: str, name: str, activation_link: str
) -> None:
    try:
        EmailNotificationsService().send_activation_email(email, name, activation_link)
    except NotificationError as exc:
        self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_password_reset_email_task(
    self, email: str, name: str, reset_link: str
) -> None:
    try:
        EmailNotificationsService().send_password_reset_email(email, name, reset_link)
    except NotificationError as exc:
        self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_password_changed_email_task(
    self, email: str, name: str, reset_request_link: str
) -> None:
    try:
        EmailNotificationsService().send_password_changed_email(
            email, name, reset_request_link
        )
    except NotificationError as exc:
        self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_payment_success_email_task(
    self, email: str, order_id: int, profiles_link: str
) -> None:
    from payments.models import Order

    try:
        order = Order.objects.select_related("student", "tariff").get(pk=order_id)
        EmailNotificationsService().send_payment_success_email(
            email, order, profiles_link
        )
    except (Order.DoesNotExist, NotificationError) as exc:
        if isinstance(exc, NotificationError):
            self.retry(exc=exc, countdown=60)
