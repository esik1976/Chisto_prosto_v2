import logging
import smtplib
from email.message import EmailMessage

from .config import (
    NOTIFY_EMAIL_TO,
    SMTP_FROM,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USERNAME,
)

logger = logging.getLogger(__name__)


def send_order_created_email(order) -> None:
    if not NOTIFY_EMAIL_TO:
        logger.info("Email notifications are disabled: NOTIFY_EMAIL_TO is empty")
        return

    message = EmailMessage()
    message["Subject"] = f"Новый заказ #{order.id}"
    message["From"] = SMTP_FROM
    message["To"] = NOTIFY_EMAIL_TO
    message.set_content(
        "\n".join(
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
        )
    )

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as smtp:
        smtp.starttls()
        smtp.login(SMTP_USERNAME, SMTP_PASSWORD)
        smtp.send_message(message)
