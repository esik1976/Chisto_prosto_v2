import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import EMAIL_FROM, NOTIFY_EMAIL_TO, RESEND_API_KEY

logger = logging.getLogger(__name__)


def send_order_created_email(order) -> None:
    if not NOTIFY_EMAIL_TO:
        logger.info("Email notifications are disabled: NOTIFY_EMAIL_TO is empty")
        return
    if not RESEND_API_KEY or not EMAIL_FROM:
        logger.warning(
            "Email notifications are misconfigured: RESEND_API_KEY/EMAIL_FROM must be set"
        )
        return

    payload = {
        "from": EMAIL_FROM,
        "to": [NOTIFY_EMAIL_TO],
        "subject": f"Новый заказ #{order.id}",
        "text": "\n".join(
            [
                f"Создан новый заказ #{order.id}",
                "",
                f"Адрес: {order.address}",
                f"Описание: {order.description or '-'}",
                f"Цена: {order.price}",
                (
                    f"Координаты: {order.latitude}, {order.longitude}"
                    if order.latitude is not None and order.longitude is not None
                    else "Координаты: не указаны"
                ),
            ]
        ),
    }

    request = Request(
        "https://api.resend.com/emails",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8")
            logger.info(
                "Order created email sent for order_id=%s to=%s response=%s",
                order.id,
                NOTIFY_EMAIL_TO,
                body,
            )
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        logger.warning("Resend HTTP error for order_id=%s: %s %s", order.id, exc, details)
        raise
    except URLError as exc:
        logger.warning("Resend network error for order_id=%s: %s", order.id, exc)
        raise
