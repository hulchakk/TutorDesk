import base64
import logging

import httpx
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from django.conf import settings
from django.core.cache import cache

from services.payments.exeptions import PaymentError
from services.payments.interfaces import IPaymentsService, CheckoutSession

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
    ) -> CheckoutSession:
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

            return CheckoutSession(
                checkout_url=data["pageUrl"],
                invoice_id=data["invoiceId"],
            )
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


def get_monobank_public_key(force_refresh: bool = False) -> str:
    cache_key = "monobank_public_key"
    key = None if force_refresh else cache.get(cache_key)

    if not key:
        headers = {"X-Token": settings.MONOBANK_API_TOKEN}
        response = httpx.get(
            "https://api.monobank.ua/api/merchant/pubkey",
            headers=headers,
            timeout=10,
        )
        response.raise_for_status()
        key = response.json()["key"]

        cache.set(cache_key, key, timeout=60 * 60 * 24 * 7)

    return key


def _check_ecdsa(body: bytes, x_sign_base64: str, pub_key_pem: str) -> bool:
    try:
        public_key = load_pem_public_key(pub_key_pem.encode("utf-8"))
        signature = base64.b64decode(x_sign_base64)

        if not isinstance(public_key, ec.EllipticCurvePublicKey):
            return False

        public_key.verify(signature, body, ec.ECDSA(hashes.SHA256()))
        return True
    except (InvalidSignature, Exception):
        return False


def verify_monobank_signature(body: bytes, x_sign_base64: str) -> bool:
    pub_key_pem = get_monobank_public_key(force_refresh=False)
    if _check_ecdsa(body, x_sign_base64, pub_key_pem):
        return True

    fresh_pub_key_pem = get_monobank_public_key(force_refresh=True)
    return _check_ecdsa(body, x_sign_base64, fresh_pub_key_pem)
