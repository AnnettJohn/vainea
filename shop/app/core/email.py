import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from starlette.concurrency import run_in_threadpool

from app.core.config import get_settings
from app.core.templates import templates
from app.models.order import Order

settings = get_settings()
logger = logging.getLogger(__name__)


def _send_email_sync(to: str, subject: str, html_body: str, text_body: str) -> None:
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    message["To"] = to
    message.attach(MIMEText(text_body, "plain"))
    message.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as client:
        if settings.smtp_use_tls:
            client.starttls()
        if settings.smtp_user:
            client.login(settings.smtp_user, settings.smtp_password)
        client.sendmail(settings.smtp_from_email, [to], message.as_string())


async def send_email(to: str, subject: str, html_body: str, text_body: str) -> None:
    """smtplib ist synchron - Versand im Threadpool, um den Event-Loop nicht
    zu blockieren (analog zur Mollie-Integration in app/core/mollie.py)."""
    await run_in_threadpool(_send_email_sync, to, subject, html_body, text_body)


async def send_order_confirmation_email(order: Order) -> None:
    """Wird aufgerufen, sobald der Mollie-Webhook eine Zahlung als "paid"
    bestätigt (siehe apply_payment_status) - erwartet order.items bereits
    geladen (selectinload)."""
    context = {"order": order}
    html_body = templates.get_template("email/order_confirmation.html").render(context)
    text_body = templates.get_template("email/order_confirmation.txt").render(context)

    await send_email(
        to=order.guest_email,
        subject=f"Deine VAINEA-Bestellung {order.order_number}",
        html_body=html_body,
        text_body=text_body,
    )
