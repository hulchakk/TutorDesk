from abc import ABC, abstractmethod


class IPaymentsService(ABC):
    @abstractmethod
    def create_checkout_session(
        self,
        order_id: str,
        amount: int,
        redirect_url: str,
        web_hook_url: str,
        ccy: int = 980,
    ) -> str:
        pass
