"""SMTP delivery helpers for daily digest emails."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.digest.models import DailyDigestConfig, EmailDelivery

logger = logging.getLogger(__name__)


def _skip_delivery(
    subject: str, recipients: list[str], reason: str, log_message: str
) -> EmailDelivery:
    logger.warning(log_message)
    return {
        "status": "skipped",
        "subject": subject,
        "recipients": recipients,
        "error": reason,
    }


def send_digest_email(
    subject: str,
    text_body: str,
    html_body: str,
    config: DailyDigestConfig,
) -> EmailDelivery:
    """Send the rendered daily digest via SMTP.

    Args:
        subject: Final email subject line.
        text_body: Plain-text variant for mail clients.
        html_body: Minimal HTML variant for richer clients.
        config: Normalized digest and SMTP configuration.

    Returns:
        EmailDelivery: Structured status metadata describing sent, skipped, or
        error outcomes without raising transport failures to the caller.
    """

    recipients = list(config["recipients"])
    sender = config["sender"]

    if not recipients or not sender:
        return _skip_delivery(
            subject,
            recipients,
            "missing recipients or sender",
            "Skipping daily digest email because recipients or sender are missing",
        )
    if not config["smtp_host"]:
        return _skip_delivery(
            subject,
            recipients,
            "missing smtp host",
            "Skipping daily digest email because SMTP host is missing",
        )
    if config["smtp_use_starttls"] and config["smtp_use_ssl"]:
        return _skip_delivery(
            subject,
            recipients,
            "conflicting smtp tls settings",
            "Skipping daily digest email because SMTP TLS settings conflict",
        )

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = ", ".join(recipients)
    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")

    client_cls = smtplib.SMTP_SSL if config["smtp_use_ssl"] else smtplib.SMTP
    try:
        with client_cls(config["smtp_host"], config["smtp_port"]) as client:
            if config["smtp_use_starttls"]:
                client.starttls()
            if config["smtp_username"] and config["smtp_password"]:
                client.login(config["smtp_username"], config["smtp_password"])
            client.send_message(message)
    except Exception as exc:
        logger.exception("Failed to send daily digest email")
        return {
            "status": "error",
            "subject": subject,
            "recipients": recipients,
            "error": f"{type(exc).__name__}: {exc}",
        }

    logger.info("Sent daily digest email to %d recipient(s)", len(recipients))
    return {
        "status": "sent",
        "subject": subject,
        "recipients": recipients,
        "error": None,
    }
