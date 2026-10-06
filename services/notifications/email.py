import logging
from smtplib import SMTPException

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from payments.models import Order
from services.notifications.exceptions import NotificationError
from services.notifications.interfaces import INotificationsService

logger = logging.getLogger(__name__)


class EmailNotificationsService(INotificationsService):
    template_dir = "notifications/email"

    def _send_email(
        self, recipient: str, subject: str, template_name: str, context: dict
    ) -> None:
        html_content = render_to_string(
            f"{self.template_dir}/{template_name}", {"subject": subject, **context}
        )

        message = EmailMultiAlternatives(
            subject=subject,
            body=strip_tags(html_content),
            to=[recipient],
        )
        message.attach_alternative(html_content, "text/html")

        try:
            message.send()
        except (SMTPException, OSError) as error:
            logger.exception("Failed to send '%s' email to %s", subject, recipient)
            raise NotificationError(f"Failed to send email to {recipient}") from error

    def send_activation_email(
        self, email: str, name: str, activation_link: str
    ) -> None:
        self._send_email(
            email,
            "Activate your account",
            "activation.html",
            {
                "name": name,
                "action_url": activation_link,
                "action_label": "Activate account",
            },
        )

    def send_password_reset_email(self, email: str, name: str, reset_link: str) -> None:
        self._send_email(
            email,
            "Reset your password",
            "password_reset.html",
            {
                "name": name,
                "action_url": reset_link,
                "action_label": "Reset password",
            },
        )

    def send_password_changed_email(
        self, email: str, name: str, reset_request_link: str
    ) -> None:
        self._send_email(
            email,
            "Your password was changed",
            "password_changed.html",
            {
                "name": name,
                "action_url": reset_request_link,
                "action_label": "Reset password",
            },
        )

    def send_payment_success_email(
        self, email: str, order: Order, profiles_link: str
    ) -> None:
        self._send_email(
            email,
            f"Payment received · Order #{order.pk}",
            "payment_success.html",
            {
                "order": order,
                "action_url": profiles_link,
                "action_label": "View my lessons",
            },
        )
