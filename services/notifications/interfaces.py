from abc import ABC, abstractmethod

from payments.models import Order


class INotificationsService(ABC):
    @abstractmethod
    def send_activation_email(self, email: str, name: str, activation_link: str) -> None:
        pass

    @abstractmethod
    def send_password_reset_email(self, email: str, name: str, reset_link: str) -> None:
        pass

    @abstractmethod
    def send_password_changed_email(
        self, email: str, name: str, reset_request_link: str
    ) -> None:
        pass

    @abstractmethod
    def send_payment_success_email(
        self, email: str, order: Order, profiles_link: str
    ) -> None:
        pass
