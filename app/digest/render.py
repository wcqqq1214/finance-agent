"""Render structured daily digest payloads into email-ready content."""

from __future__ import annotations

from html import escape

from app.digest.models import DailyDigestPayload, EmailContent


def _render_text(payload: DailyDigestPayload) -> str:
    meta = payload["meta"]
    subject = f"Daily Market Digest | {meta['digest_date']}"
    lines = [
        subject,
        f"Schedule: {meta['scheduled_time']} {meta['timezone']}",
        "",
        "Technical Snapshot",
    ]

    for section in payload.get("technical_sections", []):
        ticker = section.get("ticker", "UNKNOWN")
        asset_type = section.get("asset_type", "unknown")
        trend = section.get("trend", "neutral")
        summary = section.get("summary", "No summary available.")
        lines.append(f"- {ticker} ({asset_type}, {trend}): {summary}")

    lines.extend(["", "Macro News"])
    macro_news = payload.get("macro_news", {})
    summary_points = macro_news.get("summary_points", [])
    if macro_news.get("status") == "ok" and summary_points:
        lines.extend(f"- {point}" for point in summary_points)
    else:
        lines.append(f"Unavailable: {macro_news.get('error') or 'macro news unavailable'}")

    lines.extend(["", "CIO Summary"])
    cio_summary = payload.get("cio_summary", {})
    if cio_summary.get("status") == "ok" and cio_summary.get("text"):
        lines.append(str(cio_summary["text"]))
    else:
        lines.append(f"Unavailable: {cio_summary.get('error') or 'cio summary unavailable'}")

    return "\n".join(lines)


def _render_html(payload: DailyDigestPayload) -> str:
    meta = payload["meta"]
    subject = f"Daily Market Digest | {meta['digest_date']}"
    technical_items = []
    for section in payload.get("technical_sections", []):
        technical_items.append(
            "<li>"
            f"<b>{escape(str(section.get('ticker', 'UNKNOWN')))}</b> "
            f"<span>({escape(str(section.get('asset_type', 'unknown')))}, {escape(str(section.get('trend', 'neutral')))})</span>: "
            f"{escape(str(section.get('summary', 'No summary available.')))}"
            "</li>"
        )

    macro_news = payload.get("macro_news", {})
    summary_points = macro_news.get("summary_points", [])
    if macro_news.get("status") == "ok" and summary_points:
        macro_html = "".join(f"<li>{escape(str(point))}</li>" for point in summary_points)
    else:
        macro_html = f"<li>Unavailable: {escape(str(macro_news.get('error') or 'macro news unavailable'))}</li>"

    cio_summary = payload.get("cio_summary", {})
    if cio_summary.get("status") == "ok" and cio_summary.get("text"):
        cio_html = escape(str(cio_summary["text"]))
    else:
        cio_html = (
            f"Unavailable: {escape(str(cio_summary.get('error') or 'cio summary unavailable'))}"
        )

    technical_html = "".join(technical_items) or "<li>No technical sections available.</li>"
    return (
        "<html><body>"
        f"<h1>{escape(subject)}</h1>"
        f"<p>Schedule: {escape(str(meta['scheduled_time']))} {escape(str(meta['timezone']))}</p>"
        "<h2>Technical Snapshot</h2>"
        f"<ul>{technical_html}</ul>"
        "<h2>Macro News</h2>"
        f"<ul>{macro_html}</ul>"
        "<h2>CIO Summary</h2>"
        f"<p>{cio_html}</p>"
        "</body></html>"
    )


def render_digest_email(payload: DailyDigestPayload) -> EmailContent:
    """Render digest payload into text and HTML email bodies.

    Args:
        payload: Persisted digest payload containing run metadata and sections.

    Returns:
        EmailContent: Subject plus text and HTML bodies for multipart delivery.
    """

    digest_date = str(payload["meta"]["digest_date"])
    subject = f"Daily Market Digest | {digest_date}"
    return {
        "subject": subject,
        "text_body": _render_text(payload),
        "html_body": _render_html(payload),
    }
