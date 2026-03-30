"""Deep learning configuration module for time-series models.

Provides configuration dataclass, feature grouping constants, and seed fixing utility
for GRU/LSTM models used in stock price prediction.
"""

import random
from dataclasses import dataclass

import numpy as np


@dataclass
class DLConfig:
    """Configuration for deep learning time-series models.

    This dataclass centralizes all hyperparameters and settings for GRU/LSTM
    models used in stock price prediction. It provides sensible defaults while
    allowing full customization.

    Attributes:
        sequence_length: Number of past time steps to use as input (lookback window).
            Default: 20 trading days.
        batch_size: Number of samples per batch during training. Default: 32.
        epochs: Number of training epochs. Default: 50.
        learning_rate: Learning rate for the optimizer. Default: 0.001.
        dropout_rate: Dropout probability for regularization. Default: 0.2.
        hidden_dim: Number of hidden units in RNN layers. Default: 64.
        num_layers: Number of stacked RNN layers. Default: 2.
        model_type: Type of RNN model ("gru" or "lstm"). Default: "gru".
        seed: Random seed for reproducibility. Default: 42.
    """

    sequence_length: int = 20
    batch_size: int = 32
    epochs: int = 50
    learning_rate: float = 0.001
    dropout_rate: float = 0.2
    hidden_dim: int = 64
    num_layers: int = 2
    model_type: str = "gru"
    seed: int = 42


# Feature columns that require scaling (StandardScaler)
# These are continuous features with varying ranges that benefit from normalization
# CRITICAL: rsi_14 must be included to prevent gradient imbalance during training
COLUMNS_TO_SCALE = [
    # Returns (percentage changes)
    "ret_1d",
    "ret_3d",
    "ret_5d",
    "ret_10d",
    # Volatility features
    "volatility_5d",
    "volatility_10d",
    # Volume ratio
    "volume_ratio_5d",
    # Gap (price gap from previous close)
    "gap",
    # Moving average ratio
    "ma5_vs_ma20",
    # RSI (0-100 scale, but needs normalization for neural networks)
    "rsi_14",
    # News sentiment features (typically -1 to 1)
    "sentiment_score",
    "relevance_ratio",
    "positive_ratio",
    "negative_ratio",
    # Rolling news features
    "sentiment_score_3d",
    "sentiment_score_5d",
    "sentiment_score_10d",
    "positive_ratio_3d",
    "positive_ratio_5d",
    "positive_ratio_10d",
    "negative_ratio_3d",
    "negative_ratio_5d",
    "negative_ratio_10d",
    # Sentiment momentum
    "sentiment_momentum_3d",
]

# Feature columns that pass through without scaling
# These are categorical or already normalized features
PASSTHROUGH_COLUMNS = [
    # Categorical: day of week (0-4 for Mon-Fri)
    "day_of_week",
    # Count features (already in reasonable range)
    "n_articles",
    "n_relevant",
    "n_positive",
    "n_negative",
    "n_neutral",
    "has_news",
    "news_count_3d",
    "news_count_5d",
    "news_count_10d",
]


def set_seed(seed: int) -> None:
    """Fix random seed for reproducibility across all libraries.

    Sets the random seed for:
    - Python's built-in random module
    - NumPy's random number generator
    - PyTorch (if available)
    - TensorFlow (if available)

    This ensures reproducible results across different runs with the same seed.

    Args:
        seed: Integer seed value for all random number generators.

    Example:
        >>> set_seed(42)
        >>> import numpy as np
        >>> val1 = np.random.randn()
        >>> set_seed(42)
        >>> val2 = np.random.randn()
        >>> assert val1 == val2  # Same seed produces same values
    """
    random.seed(seed)
    np.random.seed(seed)

    # Try to set PyTorch seed if available
    try:
        import torch

        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
    except ImportError:
        pass

    # Try to set TensorFlow seed if available
    try:
        import tensorflow as tf

        tf.random.set_seed(seed)
    except ImportError:
        pass
