"""Tests for model registry module with multi-model orchestration."""

import numpy as np
import pandas as pd
import pytest

from app.ml.dl_config import DLConfig
import app.ml.model_registry as model_registry
from app.ml.model_registry import (
    format_predictions_for_agent,
    predict_proba_latest_dl,
    train_all_models,
)


def _create_mock_features(n_samples: int = 1000) -> tuple[pd.DataFrame, pd.Series]:
    """Create mock feature matrix and target for testing."""
    np.random.seed(42)
    columns = [
        "ret_1d", "ret_3d", "ret_5d", "ret_10d",
        "volatility_5d", "volatility_10d", "volume_ratio_5d",
        "gap", "ma5_vs_ma20", "rsi_14",
        "n_articles", "n_relevant", "n_positive", "n_negative",
        "news_count_3d", "news_count_5d", "news_count_10d",
        "day_of_week", "has_news", "n_neutral",
        "sentiment_score", "relevance_ratio", "positive_ratio", "negative_ratio",
        "sentiment_score_3d", "sentiment_score_5d", "sentiment_score_10d",
        "sentiment_momentum_3d",
    ]
    X = pd.DataFrame(np.random.randn(n_samples, len(columns)), columns=columns)
    y = pd.Series(np.random.randint(0, 2, n_samples))
    return X, y


def test_train_all_models_returns_multiple_models():
    """Test train_all_models returns results for multiple models"""
    X, y = _create_mock_features(n_samples=1000)

    config = DLConfig(max_epochs=3, n_splits=2)

    # Test with both LightGBM and GRU
    results = train_all_models(
        X=X,
        y=y,
        model_types=["lightgbm", "gru"],
        dl_config=config,
    )

    # Check that results contain both models
    assert "lightgbm" in results
    assert "gru" in results

    # Check structure of each result
    for model_name, result in results.items():
        assert "model" in result
        assert "metrics" in result
        assert "prediction" in result

        # Check metrics format
        metrics = result["metrics"]
        assert "mean_auc" in metrics
        assert "mean_accuracy" in metrics

        # Check prediction is a float between 0 and 1
        pred = result["prediction"]
        assert isinstance(pred, float)
        assert 0.0 <= pred <= 1.0

        # DL models should have scaler
        if model_name in ["gru", "lstm"]:
            assert "scaler" in result


def test_train_all_models_lightgbm_only():
    """Test train_all_models with only LightGBM"""
    X, y = _create_mock_features(n_samples=1000)

    config = DLConfig(max_epochs=3, n_splits=2)

    results = train_all_models(
        X=X,
        y=y,
        model_types=["lightgbm"],
        dl_config=config,
    )

    assert "lightgbm" in results
    assert "gru" not in results
    assert "lstm" not in results


def test_train_all_models_gru_only():
    """Test train_all_models with only GRU"""
    X, y = _create_mock_features(n_samples=1000)

    config = DLConfig(max_epochs=3, n_splits=2)

    results = train_all_models(
        X=X,
        y=y,
        model_types=["gru"],
        dl_config=config,
    )

    assert "gru" in results
    assert "lightgbm" not in results


def test_train_all_models_default_models():
    """Test train_all_models uses default models when not specified"""
    X, y = _create_mock_features(n_samples=1000)

    config = DLConfig(max_epochs=3, n_splits=2)

    results = train_all_models(
        X=X,
        y=y,
        model_types=None,  # Should default to ["lightgbm", "gru"]
        dl_config=config,
    )

    # Default should include both
    assert "lightgbm" in results or "gru" in results


def test_predict_proba_latest_dl_with_scaler():
    """Test predict_proba_latest_dl uses provided scaler correctly"""
    X, y = _create_mock_features(n_samples=1000)

    config = DLConfig(max_epochs=3, n_splits=2)

    # Train to get model and scaler
    results = train_all_models(
        X=X,
        y=y,
        model_types=["gru"],
        dl_config=config,
    )

    gru_result = results["gru"]
    model = gru_result["model"]
    scaler = gru_result["scaler"]

    # Make prediction with scaler
    pred = predict_proba_latest_dl(model, X, config, scaler)

    assert isinstance(pred, float)
    assert 0.0 <= pred <= 1.0


def test_predict_proba_latest_dl_insufficient_data():
    """Test predict_proba_latest_dl raises error on insufficient data"""
    from sklearn.preprocessing import RobustScaler

    X = pd.DataFrame(np.random.randn(5, 10))  # Too small
    config = DLConfig(seq_len=15)

    # Create a dummy model
    import torch
    model = torch.nn.Linear(10, 1)
    scaler = RobustScaler()

    with pytest.raises(ValueError, match="Insufficient data"):
        predict_proba_latest_dl(model, X, config, scaler)


def test_format_predictions_for_agent():
    """Test format_predictions_for_agent produces valid markdown"""
    X, y = _create_mock_features(n_samples=1000)

    config = DLConfig(max_epochs=3, n_splits=2)

    results = train_all_models(
        X=X,
        y=y,
        model_types=["lightgbm", "gru"],
        dl_config=config,
    )

    markdown = format_predictions_for_agent(results)

    # Check markdown structure
    assert isinstance(markdown, str)
    assert "量化模型预测汇总" in markdown
    assert "LIGHTGBM" in markdown or "lightgbm" in markdown.lower()
    assert "GRU" in markdown or "gru" in markdown.lower()

    # Check for prediction probabilities
    assert "%" in markdown  # Should have percentage format


def test_format_predictions_for_agent_single_model():
    """Test format_predictions_for_agent with single model"""
    X, y = _create_mock_features(n_samples=1000)

    config = DLConfig(max_epochs=3, n_splits=2)

    results = train_all_models(
        X=X,
        y=y,
        model_types=["lightgbm"],
        dl_config=config,
    )

    markdown = format_predictions_for_agent(results)

    assert isinstance(markdown, str)
    assert "量化模型预测汇总" in markdown
    assert "LIGHTGBM" in markdown or "lightgbm" in markdown.lower()


def test_format_predictions_for_agent_includes_historical_similarity():
    results = {
        "lightgbm": {
            "model": object(),
            "metrics": {
                "mean_auc": 0.61,
                "mean_accuracy": 0.56,
                "training_scope": "panel",
            },
            "prediction": 0.73,
            "historical_similarity": {
                "n_matches": 2,
                "avg_future_return_3d": 0.024,
                "target_hit_rate": 0.5,
                "same_symbol_matches": 1,
                "peer_group_matches": 1,
                "market_matches": 0,
                "cross_symbol_matches": 1,
                "matches": [
                    {
                        "symbol": "MSFT",
                        "start_date": "2024-01-02",
                        "end_date": "2024-01-03",
                        "similarity": 0.91,
                        "future_return_3d": 0.03,
                        "scope": "peer_group",
                    }
                ],
            },
        }
    }

    markdown = format_predictions_for_agent(results)

    assert "历史相似期" in markdown
    assert "MSFT" in markdown
    assert "异动命中率" in markdown
    assert "同股票 1 个、peer group 1 个、全市场补充 0 个" in markdown


def test_train_all_models_symbol_uses_panel_for_lightgbm(monkeypatch):
    single_df = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]),
            "ret_1d": [0.1, 0.2, 0.3],
            "ret_3d": [0.0, 0.1, 0.2],
            "ret_5d": [0.0, 0.1, 0.2],
            "ret_10d": [0.0, 0.1, 0.2],
            "volatility_5d": [0.1, 0.1, 0.1],
            "volatility_10d": [0.2, 0.2, 0.2],
            "volume_ratio_5d": [1.0, 1.1, 1.2],
            "gap": [0.0, 0.01, 0.02],
            "ma5_vs_ma20": [0.0, 0.01, 0.02],
            "rsi_14": [50, 55, 60],
            "n_articles": [1, 1, 1],
            "n_relevant": [1, 1, 1],
            "n_positive": [1, 0, 1],
            "n_negative": [0, 1, 0],
            "news_count_3d": [1, 2, 3],
            "news_count_5d": [1, 2, 3],
            "news_count_10d": [1, 2, 3],
            "day_of_week": [1, 2, 3],
            "has_news": [1, 1, 1],
            "n_neutral": [0, 0, 0],
            "sentiment_score": [0.5, -0.2, 0.3],
            "relevance_ratio": [1.0, 1.0, 1.0],
            "positive_ratio": [1.0, 0.0, 1.0],
            "negative_ratio": [0.0, 1.0, 0.0],
            "sentiment_score_3d": [0.5, 0.1, 0.2],
            "sentiment_score_5d": [0.5, 0.1, 0.2],
            "sentiment_score_10d": [0.5, 0.1, 0.2],
            "sentiment_momentum_3d": [0.0, 0.0, 0.0],
            "positive_ratio_3d": [1.0, 0.5, 0.66],
            "positive_ratio_5d": [1.0, 0.5, 0.66],
            "positive_ratio_10d": [1.0, 0.5, 0.66],
            "negative_ratio_3d": [0.0, 0.5, 0.33],
            "negative_ratio_5d": [0.0, 0.5, 0.33],
            "negative_ratio_10d": [0.0, 0.5, 0.33],
            "target_up_big_move_t3": [1, 0, 1],
        }
    )
    panel_df = pd.DataFrame(
        {
            "symbol": pd.Series(["AAPL", "MSFT", "AAPL", "MSFT"], dtype="category"),
            "trade_date": pd.to_datetime(["2024-01-02", "2024-01-02", "2024-01-03", "2024-01-03"]),
            "close": [100.0, 200.0, 103.0, 198.0],
            "ret_1d": [0.1, 0.0, 0.2, -0.1],
            "ret_3d": [0.1, 0.0, 0.2, -0.1],
            "ret_5d": [0.1, 0.0, 0.2, -0.1],
            "ret_10d": [0.1, 0.0, 0.2, -0.1],
            "volatility_5d": [0.1, 0.2, 0.1, 0.2],
            "volatility_10d": [0.1, 0.2, 0.1, 0.2],
            "volume_ratio_5d": [1.0, 0.9, 1.1, 0.8],
            "gap": [0.0, 0.0, 0.01, -0.01],
            "ma5_vs_ma20": [0.1, 0.0, 0.2, -0.1],
            "rsi_14": [55, 45, 60, 40],
            "n_articles": [1, 0, 2, 1],
            "n_relevant": [1, 0, 2, 1],
            "n_positive": [1, 0, 2, 0],
            "n_negative": [0, 0, 0, 1],
            "n_neutral": [0, 0, 0, 0],
            "sentiment_score": [0.5, 0.0, 0.7, -0.2],
            "relevance_ratio": [1.0, 0.0, 1.0, 1.0],
            "positive_ratio": [1.0, 0.0, 1.0, 0.0],
            "negative_ratio": [0.0, 0.0, 0.0, 1.0],
            "has_news": [1, 0, 1, 1],
            "sentiment_score_3d": [0.5, 0.0, 0.6, -0.1],
            "sentiment_score_5d": [0.5, 0.0, 0.6, -0.1],
            "sentiment_score_10d": [0.5, 0.0, 0.6, -0.1],
            "positive_ratio_3d": [1.0, 0.0, 1.0, 0.0],
            "positive_ratio_5d": [1.0, 0.0, 1.0, 0.0],
            "positive_ratio_10d": [1.0, 0.0, 1.0, 0.0],
            "negative_ratio_3d": [0.0, 0.0, 0.0, 1.0],
            "negative_ratio_5d": [0.0, 0.0, 0.0, 1.0],
            "negative_ratio_10d": [0.0, 0.0, 0.0, 1.0],
            "news_count_3d": [1, 0, 2, 1],
            "news_count_5d": [1, 0, 2, 1],
            "news_count_10d": [1, 0, 2, 1],
            "sentiment_momentum_3d": [0.0, 0.0, 0.0, 0.0],
            "day_of_week": [1, 1, 2, 2],
            "market_sentiment_score": [0.25, 0.25, 0.25, 0.25],
            "market_positive_ratio": [0.5, 0.5, 0.5, 0.5],
            "market_negative_ratio": [0.0, 0.0, 0.5, 0.5],
            "market_news_count_3d": [0.5, 0.5, 1.5, 1.5],
            "market_ret_1d": [0.05, 0.05, 0.05, 0.05],
            "market_volatility_5d": [0.15, 0.15, 0.15, 0.15],
            "market_has_news_ratio": [0.5, 0.5, 1.0, 1.0],
            "sentiment_score_residual": [0.25, -0.25, 0.45, -0.45],
            "news_count_3d_residual": [0.5, -0.5, 0.5, -0.5],
            "ret_1d_residual": [0.05, -0.05, 0.15, -0.15],
            "news_text_blob": ["iphone demand", "macro slowdown", "services growth", "cloud pressure"],
            "target_up_big_move_t3": [1, 0, 1, 0],
        }
    )

    calls = {}

    monkeypatch.setattr(model_registry, "build_features", lambda symbol, **kwargs: single_df.copy())
    monkeypatch.setattr(model_registry, "build_panel_features", lambda **kwargs: panel_df.copy())

    def fake_train_lightgbm_panel_with_text(X, y, trade_dates, text_series, categorical_features=None, n_splits=5, text_n_components=10):
        calls["lightgbm_columns"] = list(X.columns)
        calls["lightgbm_rows"] = len(X)
        calls["lightgbm_cats"] = categorical_features
        calls["lightgbm_text"] = list(text_series)
        mock_model = object()
        feature_matrix = X.copy()
        for i in range(text_n_components):
            feature_matrix[f"text_svd_{i}"] = 0.0
        return mock_model, {"mean_auc": 0.61, "mean_accuracy": 0.56, "text_svd_components": text_n_components}, None, feature_matrix

    def fake_predict_proba_latest(model, X):
        calls["predict_columns"] = list(X.columns)
        return 0.73

    monkeypatch.setattr(model_registry, "train_lightgbm_panel_with_text", fake_train_lightgbm_panel_with_text)
    monkeypatch.setattr(model_registry, "predict_proba_latest", fake_predict_proba_latest)
    monkeypatch.setattr(
        model_registry,
        "find_similar_historical_periods",
        lambda history, query, target_col=None: {
            "n_matches": 2,
            "horizon_days": 3,
            "avg_similarity": 0.89,
            "avg_future_return_3d": 0.024,
            "positive_rate": 1.0,
            "target_hit_rate": 0.5,
            "same_symbol_matches": 1,
            "peer_group_matches": 1,
            "market_matches": 0,
            "cross_symbol_matches": 1,
            "strategy": "same_symbol_then_peer_group",
            "matches": [
                {
                    "symbol": "MSFT",
                    "start_date": "2024-01-02",
                    "end_date": "2024-01-03",
                    "similarity": 0.91,
                    "future_return_3d": 0.03,
                    "scope": "peer_group",
                }
            ],
        },
    )

    results = train_all_models(
        symbol="AAPL",
        model_types=["lightgbm"],
        dl_config=DLConfig(max_epochs=1, n_splits=2),
    )

    assert "lightgbm" in results
    assert results["lightgbm"]["prediction"] == 0.73
    assert results["lightgbm"]["metrics"]["training_scope"] == "panel"
    assert results["lightgbm"]["metrics"]["target"] == "target_up_big_move_t3"
    assert calls["lightgbm_cats"] == ["symbol"]
    assert calls["lightgbm_text"] == ["iphone demand", "macro slowdown", "services growth", "cloud pressure"]
    assert "symbol" in calls["lightgbm_columns"]
    assert "text_svd_0" in calls["predict_columns"]
    assert results["lightgbm"]["historical_similarity"]["n_matches"] == 2
    assert results["lightgbm"]["historical_similarity"]["matches"][0]["symbol"] == "MSFT"


def test_train_all_models_symbol_passes_date_range(monkeypatch):
    single_df = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]),
            "ret_1d": [0.1, 0.2, 0.3],
            "ret_3d": [0.0, 0.1, 0.2],
            "ret_5d": [0.0, 0.1, 0.2],
            "ret_10d": [0.0, 0.1, 0.2],
            "volatility_5d": [0.1, 0.1, 0.1],
            "volatility_10d": [0.2, 0.2, 0.2],
            "volume_ratio_5d": [1.0, 1.1, 1.2],
            "gap": [0.0, 0.01, 0.02],
            "ma5_vs_ma20": [0.0, 0.01, 0.02],
            "rsi_14": [50, 55, 60],
            "n_articles": [1, 1, 1],
            "n_relevant": [1, 1, 1],
            "n_positive": [1, 0, 1],
            "n_negative": [0, 1, 0],
            "news_count_3d": [1, 2, 3],
            "news_count_5d": [1, 2, 3],
            "news_count_10d": [1, 2, 3],
            "day_of_week": [1, 2, 3],
            "has_news": [1, 1, 1],
            "n_neutral": [0, 0, 0],
            "sentiment_score": [0.5, -0.2, 0.3],
            "relevance_ratio": [1.0, 1.0, 1.0],
            "positive_ratio": [1.0, 0.0, 1.0],
            "negative_ratio": [0.0, 1.0, 0.0],
            "sentiment_score_3d": [0.5, 0.1, 0.2],
            "sentiment_score_5d": [0.5, 0.1, 0.2],
            "sentiment_score_10d": [0.5, 0.1, 0.2],
            "sentiment_momentum_3d": [0.0, 0.0, 0.0],
            "positive_ratio_3d": [1.0, 0.5, 0.66],
            "positive_ratio_5d": [1.0, 0.5, 0.66],
            "positive_ratio_10d": [1.0, 0.5, 0.66],
            "negative_ratio_3d": [0.0, 0.5, 0.33],
            "negative_ratio_5d": [0.0, 0.5, 0.33],
            "negative_ratio_10d": [0.0, 0.5, 0.33],
            "target_up_big_move_t3": [1, 0, 1],
        }
    )
    panel_df = pd.DataFrame(
        {
            "symbol": pd.Series(["AAPL", "MSFT"], dtype="category"),
            "trade_date": pd.to_datetime(["2024-01-03", "2024-01-03"]),
            "ret_1d": [0.2, -0.1],
            "ret_3d": [0.2, -0.1],
            "ret_5d": [0.2, -0.1],
            "ret_10d": [0.2, -0.1],
            "volatility_5d": [0.1, 0.2],
            "volatility_10d": [0.1, 0.2],
            "volume_ratio_5d": [1.1, 0.8],
            "gap": [0.01, -0.01],
            "ma5_vs_ma20": [0.2, -0.1],
            "rsi_14": [60, 40],
            "n_articles": [2, 1],
            "n_relevant": [2, 1],
            "n_positive": [2, 0],
            "n_negative": [0, 1],
            "n_neutral": [0, 0],
            "sentiment_score": [0.7, -0.2],
            "relevance_ratio": [1.0, 1.0],
            "positive_ratio": [1.0, 0.0],
            "negative_ratio": [0.0, 1.0],
            "has_news": [1, 1],
            "sentiment_score_3d": [0.6, -0.1],
            "sentiment_score_5d": [0.6, -0.1],
            "sentiment_score_10d": [0.6, -0.1],
            "positive_ratio_3d": [1.0, 0.0],
            "positive_ratio_5d": [1.0, 0.0],
            "positive_ratio_10d": [1.0, 0.0],
            "negative_ratio_3d": [0.0, 1.0],
            "negative_ratio_5d": [0.0, 1.0],
            "negative_ratio_10d": [0.0, 1.0],
            "news_count_3d": [2, 1],
            "news_count_5d": [2, 1],
            "news_count_10d": [2, 1],
            "sentiment_momentum_3d": [0.0, 0.0],
            "day_of_week": [2, 2],
            "market_sentiment_score": [0.25, 0.25],
            "market_positive_ratio": [0.5, 0.5],
            "market_negative_ratio": [0.5, 0.5],
            "market_news_count_3d": [1.5, 1.5],
            "market_ret_1d": [0.05, 0.05],
            "market_volatility_5d": [0.15, 0.15],
            "market_has_news_ratio": [1.0, 1.0],
            "sentiment_score_residual": [0.45, -0.45],
            "news_count_3d_residual": [0.5, -0.5],
            "ret_1d_residual": [0.15, -0.15],
            "news_text_blob": ["iphone demand", "macro slowdown"],
            "target_up_big_move_t3": [1, 0],
        }
    )

    calls = {}

    def fake_build_features(symbol, **kwargs):
        calls["symbol_kwargs"] = kwargs
        return single_df.copy()

    def fake_build_panel_features(**kwargs):
        calls["panel_kwargs"] = kwargs
        return panel_df.copy()

    def fake_train_lightgbm_panel_with_text(
        X,
        y,
        trade_dates,
        text_series,
        categorical_features=None,
        n_splits=5,
        text_n_components=10,
    ):
        feature_matrix = X.copy()
        for i in range(text_n_components):
            feature_matrix[f"text_svd_{i}"] = 0.0
        return object(), {"mean_auc": 0.61, "mean_accuracy": 0.56}, None, feature_matrix

    def fake_train_dl_model(X, y, config):
        calls["dl_rows"] = len(X)
        return object(), {"mean_auc": 0.58, "mean_accuracy": 0.55}, object()

    monkeypatch.setattr(model_registry, "build_features", fake_build_features)
    monkeypatch.setattr(model_registry, "build_panel_features", fake_build_panel_features)
    monkeypatch.setattr(model_registry, "train_lightgbm_panel_with_text", fake_train_lightgbm_panel_with_text)
    monkeypatch.setattr(model_registry, "predict_proba_latest", lambda model, X: 0.73)
    monkeypatch.setattr(model_registry, "train_dl_model", fake_train_dl_model)
    monkeypatch.setattr(model_registry, "predict_proba_latest_dl", lambda model, X, config, scaler: 0.52)

    results = train_all_models(
        symbol="AAPL",
        model_types=["lightgbm", "gru"],
        dl_config=DLConfig(max_epochs=1, n_splits=2),
        start_date="2024-01-01",
        end_date="2024-01-31",
    )

    assert results["lightgbm"]["metrics"]["training_scope"] == "panel"
    assert results["gru"]["metrics"]["training_scope"] == "single_symbol"
    assert calls["symbol_kwargs"] == {"start_date": "2024-01-01", "end_date": "2024-01-31"}
    assert calls["panel_kwargs"] == {"start_date": "2024-01-01", "end_date": "2024-01-31"}
    assert calls["dl_rows"] == 3
