from dataclasses import dataclass
from uuid import uuid4

from .storage import Order


@dataclass
class PaymentSession:
    payment_id: str
    payment_url: str


def create_mock_payment(order: Order) -> PaymentSession:
    payment_id = f"mock-{order.id}-{uuid4().hex[:10]}"
    return PaymentSession(
        payment_id=payment_id,
        payment_url=f"/payments/mock/{payment_id}",
    )
