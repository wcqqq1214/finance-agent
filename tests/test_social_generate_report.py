from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import app.social.generate_report as social_generate_report


def test_generate_report_includes_markdown_report(tmp_path, monkeypatch):
    monkeypatch.setattr(
        social_generate_report,
        "get_reddit_discussion",
        SimpleNamespace(invoke=lambda payload: "reddit corpus"),
    )
    monkeypatch.setattr(
        social_generate_report,
        "_extract_ingest_meta_from_text",
        lambda text: {
            "source": "json",
            "window": "24h",
            "subreddits": ["stocks", "wallstreetbets"],
            "post_count": 42,
            "comment_count": 512,
        },
    )
    monkeypatch.setattr(
        social_generate_report,
        "analyze_reddit_text",
        SimpleNamespace(
            invoke=lambda payload: {
                "sentiment": "bullish",
                "keywords": ["AI", "earnings", "momentum"],
                "summary": "Retail sentiment remains constructive.",
            }
        ),
    )
    monkeypatch.setattr(
        social_generate_report,
        "build_social_report",
        SimpleNamespace(
            invoke=lambda payload: {
                "asset": payload["asset"],
                "meta": payload["meta"],
                "sentiment": payload["nlp_result"]["sentiment"],
                "keywords": payload["nlp_result"]["keywords"],
                "summary": payload["nlp_result"]["summary"],
            }
        ),
    )

    report = social_generate_report.generate_report("NVDA", str(tmp_path))

    assert report["sentiment"] == "bullish"
    assert "# Social Retail Sentiment Report" in report["markdown_report"]
    assert "`AI`" in report["markdown_report"]
    assert "`stocks`" in report["markdown_report"]

    saved = json.loads(Path(tmp_path, "social.json").read_text(encoding="utf-8"))
    assert saved["markdown_report"] == report["markdown_report"]
