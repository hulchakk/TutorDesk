from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True)
class CheckoutSession:
    checkout_url: str
    invoice_id: str


class IPaymentsService(ABC):
    @abstractmethod
    def create_checkout_session(
        self,
        order_id: str,
        amount: int,
        redirect_url: str,
        web_hook_url: str,
        ccy: int = 980,
    ) -> CheckoutSession:
        pass
