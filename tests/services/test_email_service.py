"""Tests for SMTP-backed daily digest delivery."""

from email import message_from_string
from unittest.mock import MagicMock

from app.services.email_service import send_digest_email


def _base_config() -> dict[str, object]:
    return {
        "recipients": ["alice@example.com"],
        "sender": "digest@example.com",
        "smtp_host": "smtp.example.com",
        "smtp_port": 587,
        "smtp_username": "digest@example.com",
        "smtp_password": "secret",
        "smtp_use_starttls": True,
        "smtp_use_ssl": False,
    }


def test_send_digest_email_sends_multipart_message(monkeypatch):
    """Service should send a multipart/alternative message via SMTP."""
    config = _base_config()
    smtp = MagicMock()
    smtp_cm = MagicMock()
    smtp_cm.__enter__.return_value = smtp
    smtp_cm.__exit__.return_value = False
    smtp_cls = MagicMock(return_value=smtp_cm)
    monkeypatch.setattr("app.services.email_service.smtplib.SMTP", smtp_cls)

    result = send_digest_email(
        "Daily Market Digest | 2026-04-07",
        "plain body",
        "<html><body>html body</body></html>",
        config,
    )

    assert result == {
        "status": "sent",
        "subject": "Daily Market Digest | 2026-04-07",
        "recipients": ["alice@example.com"],
        "error": None,
    }
    smtp_cls.assert_called_once_with("smtp.example.com", 587)
    smtp.starttls.assert_called_once()
    smtp.login.assert_called_once_with("digest@example.com", "secret")
    smtp.send_message.assert_called_once()

    sent_message = smtp.send_message.call_args.args[0]
    assert sent_message.get_content_type() == "multipart/alternative"
    parsed = message_from_string(sent_message.as_string())
    assert parsed.get_payload(0).get_content_type() == "text/plain"
    assert parsed.get_payload(1).get_content_type() == "text/html"


def test_send_digest_email_skips_when_recipients_missing(caplog):
    """Service should skip sending when no recipients are configured."""
    result = send_digest_email(
        "Subject", "plain", "<html></html>", {**_base_config(), "recipients": []}
    )

    assert result == {
        "status": "skipped",
        "subject": "Subject",
        "recipients": [],
        "error": "missing recipients or sender",
    }
    assert "recipients or sender are missing" in caplog.text


def test_send_digest_email_skips_when_sender_missing(caplog):
    """Service should skip sending when sender is unavailable."""
    result = send_digest_email(
        "Subject", "plain", "<html></html>", {**_base_config(), "sender": None}
    )

    assert result["status"] == "skipped"
    assert result["error"] == "missing recipients or sender"
    assert "recipients or sender are missing" in caplog.text


def test_send_digest_email_skips_conflicting_tls_modes(caplog):
    """Service should refuse invalid STARTTLS and SSL combinations."""
    result = send_digest_email(
        "Subject",
        "plain",
        "<html></html>",
        {**_base_config(), "smtp_use_starttls": True, "smtp_use_ssl": True},
    )

    assert result["status"] == "skipped"
    assert result["error"] == "conflicting smtp tls settings"
    assert "SMTP TLS settings conflict" in caplog.text


def test_send_digest_email_skips_when_smtp_host_missing(caplog):
    """Service should skip sending when SMTP host is missing."""
    result = send_digest_email(
        "Subject", "plain", "<html></html>", {**_base_config(), "smtp_host": None}
    )

    assert result["status"] == "skipped"
    assert result["error"] == "missing smtp host"
    assert "SMTP host is missing" in caplog.text


def test_send_digest_email_returns_error_when_send_fails(monkeypatch):
    """Service should convert SMTP exceptions into structured error metadata."""
    config = {
        **_base_config(),
        "smtp_port": 465,
        "smtp_username": None,
        "smtp_password": None,
        "smtp_use_starttls": False,
        "smtp_use_ssl": True,
    }
    smtp = MagicMock()
    smtp.send_message.side_effect = RuntimeError("boom")
    smtp_cm = MagicMock()
    smtp_cm.__enter__.return_value = smtp
    smtp_cm.__exit__.return_value = False
    smtp_ssl_cls = MagicMock(return_value=smtp_cm)
    monkeypatch.setattr("app.services.email_service.smtplib.SMTP_SSL", smtp_ssl_cls)

    result = send_digest_email("Subject", "plain", "<html></html>", config)

    assert result["status"] == "error"
    assert result["subject"] == "Subject"
    assert result["recipients"] == ["alice@example.com"]
    assert "RuntimeError: boom" == result["error"]
    smtp_ssl_cls.assert_called_once_with("smtp.example.com", 465)
