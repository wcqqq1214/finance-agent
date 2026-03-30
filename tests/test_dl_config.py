"""Tests for deep learning configuration module (dl_config.py).

Tests follow TDD approach: test first, then implement.
"""

import random

import numpy as np
import pytest

from app.ml.dl_config import DLConfig, set_seed


class TestDLConfig:
    """Test DLConfig dataclass."""

    def test_dlconfig_creation_with_defaults(self):
        """Test DLConfig can be created with default values."""
        config = DLConfig()
        assert config.seq_len == 15
        assert config.batch_size == 32
        assert config.max_epochs == 100
        assert config.learning_rate == 5e-4
        assert config.dropout == 0.4
        assert config.hidden_size == 32
        assert config.num_layers == 1
        assert config.model_type == "gru"
        assert config.scaler_type == "robust"
        assert config.weight_decay == 1e-4
        assert config.early_stopping_patience == 10
        assert config.n_splits == 5
        assert config.device in ("cuda", "cpu")

    def test_dlconfig_creation_with_custom_values(self):
        """Test DLConfig can be created with custom values."""
        config = DLConfig(
            seq_len=30,
            batch_size=64,
            max_epochs=200,
            learning_rate=1e-3,
            dropout=0.3,
            hidden_size=64,
            num_layers=2,
            model_type="lstm",
            scaler_type="standard",
            weight_decay=5e-4,
            early_stopping_patience=15,
            n_splits=10,
            device="cpu",
        )
        assert config.seq_len == 30
        assert config.batch_size == 64
        assert config.max_epochs == 200
        assert config.learning_rate == 1e-3
        assert config.dropout == 0.3
        assert config.hidden_size == 64
        assert config.num_layers == 2
        assert config.model_type == "lstm"
        assert config.scaler_type == "standard"
        assert config.weight_decay == 5e-4
        assert config.early_stopping_patience == 15
        assert config.n_splits == 10
        assert config.device == "cpu"

    def test_dlconfig_is_dataclass(self):
        """Test DLConfig is a proper dataclass."""
        config = DLConfig()
        # Should be able to convert to dict-like representation
        assert hasattr(config, "__dataclass_fields__")

    def test_dlconfig_device_auto_detection(self):
        """Test device is auto-detected when not specified."""
        config = DLConfig()
        assert config.device in ("cuda", "cpu")


class TestFeatureGrouping:
    """Test feature grouping constants."""

    def test_columns_to_scale_exists(self):
        """Test COLUMNS_TO_SCALE constant is defined."""
        from app.ml.dl_config import COLUMNS_TO_SCALE

        assert isinstance(COLUMNS_TO_SCALE, (list, tuple))
        assert len(COLUMNS_TO_SCALE) > 0

    def test_columns_to_scale_contains_rsi_14(self):
        """Test COLUMNS_TO_SCALE includes rsi_14 (critical for gradient stability)."""
        from app.ml.dl_config import COLUMNS_TO_SCALE

        assert "rsi_14" in COLUMNS_TO_SCALE

    def test_columns_to_scale_contains_returns(self):
        """Test COLUMNS_TO_SCALE includes return features."""
        from app.ml.dl_config import COLUMNS_TO_SCALE

        # At least one return feature should be scaled
        return_features = [col for col in COLUMNS_TO_SCALE if "ret_" in col]
        assert len(return_features) > 0

    def test_columns_to_scale_contains_volatility(self):
        """Test COLUMNS_TO_SCALE includes volatility features."""
        from app.ml.dl_config import COLUMNS_TO_SCALE

        volatility_features = [col for col in COLUMNS_TO_SCALE if "volatility_" in col]
        assert len(volatility_features) > 0

    def test_columns_to_scale_contains_count_features(self):
        """Test COLUMNS_TO_SCALE includes count features (n_articles, etc)."""
        from app.ml.dl_config import COLUMNS_TO_SCALE

        count_features = [col for col in COLUMNS_TO_SCALE if col.startswith("n_")]
        assert len(count_features) > 0
        assert "n_articles" in COLUMNS_TO_SCALE
        assert "n_relevant" in COLUMNS_TO_SCALE

    def test_columns_to_scale_contains_news_count_rolling(self):
        """Test COLUMNS_TO_SCALE includes rolling news count features."""
        from app.ml.dl_config import COLUMNS_TO_SCALE

        assert "news_count_3d" in COLUMNS_TO_SCALE
        assert "news_count_5d" in COLUMNS_TO_SCALE
        assert "news_count_10d" in COLUMNS_TO_SCALE

    def test_passthrough_columns_exists(self):
        """Test PASSTHROUGH_COLUMNS constant is defined."""
        from app.ml.dl_config import PASSTHROUGH_COLUMNS

        assert isinstance(PASSTHROUGH_COLUMNS, (list, tuple))

    def test_passthrough_columns_contains_categorical(self):
        """Test PASSTHROUGH_COLUMNS includes categorical features."""
        from app.ml.dl_config import PASSTHROUGH_COLUMNS

        # day_of_week is a categorical feature that should pass through
        assert "day_of_week" in PASSTHROUGH_COLUMNS

    def test_passthrough_columns_contains_sentiment_scores(self):
        """Test PASSTHROUGH_COLUMNS includes sentiment score features."""
        from app.ml.dl_config import PASSTHROUGH_COLUMNS

        assert "sentiment_score" in PASSTHROUGH_COLUMNS
        assert "sentiment_score_3d" in PASSTHROUGH_COLUMNS
        assert "sentiment_score_5d" in PASSTHROUGH_COLUMNS
        assert "sentiment_score_10d" in PASSTHROUGH_COLUMNS

    def test_passthrough_columns_contains_sentiment_ratios(self):
        """Test PASSTHROUGH_COLUMNS includes sentiment ratio features."""
        from app.ml.dl_config import PASSTHROUGH_COLUMNS

        assert "relevance_ratio" in PASSTHROUGH_COLUMNS
        assert "positive_ratio" in PASSTHROUGH_COLUMNS
        assert "negative_ratio" in PASSTHROUGH_COLUMNS

    def test_passthrough_columns_contains_sentiment_momentum(self):
        """Test PASSTHROUGH_COLUMNS includes sentiment momentum."""
        from app.ml.dl_config import PASSTHROUGH_COLUMNS

        assert "sentiment_momentum_3d" in PASSTHROUGH_COLUMNS

    def test_no_overlap_between_scale_and_passthrough(self):
        """Test COLUMNS_TO_SCALE and PASSTHROUGH_COLUMNS don't overlap."""
        from app.ml.dl_config import COLUMNS_TO_SCALE, PASSTHROUGH_COLUMNS

        overlap = set(COLUMNS_TO_SCALE) & set(PASSTHROUGH_COLUMNS)
        assert len(overlap) == 0, f"Overlapping columns: {overlap}"

    def test_feature_grouping_covers_main_features(self):
        """Test feature grouping covers the main feature categories."""
        from app.ml.dl_config import COLUMNS_TO_SCALE, PASSTHROUGH_COLUMNS

        all_features = set(COLUMNS_TO_SCALE) | set(PASSTHROUGH_COLUMNS)

        # Should include news features
        news_features = [f for f in all_features if "sentiment" in f or "news" in f]
        assert len(news_features) > 0

        # Should include price/technical features
        price_features = [f for f in all_features if "ret_" in f or "ma" in f or "rsi" in f]
        assert len(price_features) > 0


class TestSetSeed:
    """Test set_seed utility function."""

    def test_set_seed_fixes_numpy_random(self):
        """Test set_seed fixes numpy random state."""
        set_seed(42)
        val1 = np.random.randn()

        set_seed(42)
        val2 = np.random.randn()

        assert val1 == val2

    def test_set_seed_fixes_python_random(self):
        """Test set_seed fixes Python random state."""
        set_seed(42)
        val1 = random.random()

        set_seed(42)
        val2 = random.random()

        assert val1 == val2

    def test_set_seed_with_different_seeds(self):
        """Test set_seed produces different values with different seeds."""
        set_seed(42)
        val1 = np.random.randn()

        set_seed(123)
        val2 = np.random.randn()

        assert val1 != val2

    def test_set_seed_accepts_integer(self):
        """Test set_seed accepts integer seed."""
        # Should not raise
        set_seed(42)
        set_seed(0)
        set_seed(999)

    def test_set_seed_reproducibility_sequence(self):
        """Test set_seed produces reproducible sequences."""
        set_seed(42)
        seq1 = [np.random.randn() for _ in range(5)]

        set_seed(42)
        seq2 = [np.random.randn() for _ in range(5)]

        assert seq1 == seq2

