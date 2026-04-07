"""Tests for daily digest email rendering."""

from app.digest.render import render_digest_email


def test_render_digest_email_returns_subject_text_and_html():
    """Renderer should build deterministic subject, text, and HTML bodies."""
    payload = {
        "meta": {
            "timezone": "Asia/Shanghai",
            "scheduled_time": "08:00",
            "digest_date": "2026-04-07",
        },
        "tickers": ["AAPL", "BTC"],
        "technical_sections": [
            {
                "ticker": "AAPL",
                "asset_type": "equity",
                "status": "ok",
                "summary": "AAPL trend improving.",
                "trend": "bullish",
                "error": None,
            },
            {
                "ticker": "BTC",
                "asset_type": "crypto",
                "status": "error",
                "summary": "Technical snapshot unavailable for this run.",
                "trend": "neutral",
                "error": "timeout",
            },
        ],
        "macro_news": {
            "status": "ok",
            "window_start": "2026-04-06T08:00:00+08:00",
            "window_end": "2026-04-07T08:00:00+08:00",
            "summary_points": ["Fed watch remains the top macro risk."],
            "error": None,
        },
        "cio_summary": {
            "status": "ok",
            "text": "Risk appetite is mixed.",
            "error": None,
        },
    }

    email = render_digest_email(payload)

    assert email["subject"] == "Daily Market Digest | 2026-04-07"
    assert "Daily Market Digest | 2026-04-07" in email["text_body"]
    assert "Schedule: 08:00 Asia/Shanghai" in email["text_body"]
    assert "AAPL (equity, bullish): AAPL trend improving." in email["text_body"]
    assert (
        "BTC (crypto, neutral): Technical snapshot unavailable for this run." in email["text_body"]
    )
    assert "Fed watch remains the top macro risk." in email["text_body"]
    assert "CIO Summary" in email["text_body"]
    assert "Risk appetite is mixed." in email["text_body"]
    assert "<html" in email["html_body"].lower()
    assert (
        "<li><b>AAPL</b> <span>(equity, bullish)</span>: AAPL trend improving.</li>"
        in email["html_body"]
    )
    assert "Fed watch remains the top macro risk." in email["html_body"]
    assert "Risk appetite is mixed." in email["html_body"]


def test_render_digest_email_handles_error_sections_compactly():
    """Renderer should keep degraded sections readable and compact."""
    payload = {
        "meta": {
            "timezone": "UTC",
            "scheduled_time": "06:30",
            "digest_date": "2026-04-08",
        },
        "tickers": ["ETH"],
        "technical_sections": [
            {
                "ticker": "ETH",
                "asset_type": "crypto",
                "status": "error",
                "summary": "Technical snapshot unavailable for this run.",
                "trend": "neutral",
                "error": "source timeout",
            }
        ],
        "macro_news": {
            "status": "error",
            "window_start": "2026-04-07T06:30:00+00:00",
            "window_end": "2026-04-08T06:30:00+00:00",
            "summary_points": [],
            "error": "news search unavailable",
        },
        "cio_summary": {
            "status": "error",
            "text": "",
            "error": "llm unavailable",
        },
    }

    email = render_digest_email(payload)

    assert email["subject"] == "Daily Market Digest | 2026-04-08"
    assert "Macro News" in email["text_body"]
    assert "Unavailable: news search unavailable" in email["text_body"]
    assert "Unavailable: llm unavailable" in email["text_body"]
    assert "source timeout" not in email["text_body"]
    assert "news search unavailable" in email["html_body"]
    assert "llm unavailable" in email["html_body"]
