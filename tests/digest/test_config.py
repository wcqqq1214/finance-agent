from app.digest.config import DEFAULT_MACRO_QUERY, build_daily_digest_trigger, load_daily_digest_config


def test_load_daily_digest_config_defaults(monkeypatch):
    for key in (
        "DAILY_DIGEST_ENABLED",
        "DAILY_DIGEST_TIME",
        "DAILY_DIGEST_TIMEZONE",
        "DAILY_DIGEST_RECIPIENTS",
        "DAILY_DIGEST_FROM",
        "DAILY_DIGEST_TICKERS",
        "DAILY_DIGEST_MACRO_QUERY",
        "SMTP_HOST",
        "SMTP_PORT",
        "SMTP_USERNAME",
        "SMTP_PASSWORD",
        "SMTP_USE_STARTTLS",
        "SMTP_USE_SSL",
    ):
        monkeypatch.delenv(key, raising=False)
    cfg = load_daily_digest_config()
    assert cfg["enabled"] is False
    assert cfg["time"] == "08:00"
    assert cfg["timezone"] == "Asia/Shanghai"
    assert cfg["macro_query"] == DEFAULT_MACRO_QUERY
    assert cfg["tickers"] == ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BTC", "ETH"]


def test_build_daily_digest_trigger_rejects_invalid_time(monkeypatch):
    monkeypatch.setenv("DAILY_DIGEST_ENABLED", "true")
    monkeypatch.setenv("DAILY_DIGEST_TIME", "25:61")
    cfg = load_daily_digest_config()
    assert build_daily_digest_trigger(cfg) is None


def test_build_daily_digest_trigger_rejects_invalid_timezone(monkeypatch):
    monkeypatch.setenv("DAILY_DIGEST_ENABLED", "true")
    monkeypatch.setenv("DAILY_DIGEST_TIMEZONE", "Asia/Invalid")
    cfg = load_daily_digest_config()
    assert build_daily_digest_trigger(cfg) is None


def test_load_daily_digest_config_filters_bad_recipients(monkeypatch):
    monkeypatch.setenv("DAILY_DIGEST_RECIPIENTS", "ok@example.com,not-an-email")
    cfg = load_daily_digest_config()
    assert cfg["recipients"] == ["ok@example.com"]


def test_load_daily_digest_config_falls_back_to_default_tickers(monkeypatch):
    monkeypatch.setenv("DAILY_DIGEST_TICKERS", " , , ")
    cfg = load_daily_digest_config()
    assert cfg["tickers"] == ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BTC", "ETH"]


def test_load_daily_digest_config_uses_smtp_username_as_sender(monkeypatch):
    monkeypatch.delenv("DAILY_DIGEST_FROM", raising=False)
    monkeypatch.setenv("SMTP_USERNAME", "digest@example.com")
    cfg = load_daily_digest_config()
    assert cfg["sender"] == "digest@example.com"


def test_load_daily_digest_config_falls_back_when_smtp_port_is_invalid(monkeypatch):
    monkeypatch.setenv("SMTP_PORT", "not-a-number")
    cfg = load_daily_digest_config()
    assert cfg["smtp_port"] == 587


def test_load_daily_digest_config_logs_ticker_fallback_and_dropped_recipients(monkeypatch, caplog):
    monkeypatch.setenv("DAILY_DIGEST_TICKERS", " , , ")
    monkeypatch.setenv("DAILY_DIGEST_RECIPIENTS", "ok@example.com,not-an-email")
    cfg = load_daily_digest_config()
    assert cfg["tickers"][0] == "AAPL"
    assert cfg["recipients"] == ["ok@example.com"]
    assert "falling back to default tickers" in caplog.text
    assert "dropped " in caplog.text
    assert "invalid recipient" in caplog.text
