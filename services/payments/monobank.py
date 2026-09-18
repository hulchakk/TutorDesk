import logging

import httpx
from django.conf import settings

from services.payments.exeptions import PaymentError
from services.payments.interfaces import IPaymentsService

HEADERS = {
    "X-Token": settings.MONOBANK_TOKEN,
    "Content-Type": "application/json",
}

API_CREATE_INVOICE_URL = "https://api.monobank.ua/api/merchant/invoice/create"
API_SEND_RECEIPT_URL = "https://api.monobank.ua/api/merchant/invoice/receipt"


class MonobankService(IPaymentsService):
    def create_checkout_session(
        self,
        order_id: str,
        amount: int,
        redirect_url: str,
        web_hook_url: str,
        ccy: int = 980,
    ) -> str:
        try:
            response = httpx.post(
                API_CREATE_INVOICE_URL,
                headers=HEADERS,
                json={
                    "amount": amount,
                    "ccy": ccy,
                    "merchantPaymInfo": {
                        "reference": order_id,
                        "destination": f"Payment for order {order_id}.",
                    },
                    "redirectUrl": redirect_url,
                    "webHookUrl": web_hook_url,
                    "validity": 60 * 60 * 2,
                },
            )

            data = response.json()

            if response.status_code != 200:
                raise PaymentError(data)

            return data["pageUrl"]
        except httpx.RequestError:
            raise PaymentError("Something went wrong while creating payment.")


def send_receipt(
    invoice_id: str,
    customer_email: str,
):
    try:
        response = httpx.get(
            API_SEND_RECEIPT_URL,
            headers=HEADERS,
            params={
                "invoiceId": invoice_id,
                "email": customer_email,
            },
        )
        if response.status_code != 200:
            raise httpx.RequestError("Something went wrong while sending receipt.")
    except httpx.RequestError as e:
        logging.error(e)
