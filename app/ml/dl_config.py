"""Deep learning configuration module for time-series models.

Provides configuration dataclass, feature grouping constants, and seed fixing utility
for GRU/LSTM models used in stock price prediction.
"""

import random
from dataclasses import dataclass

import numpy as np

try:
    import torch
except ImportError:
    torch = None


@dataclass
class DLConfig:
    """Configuration for deep learning time-series models.

    This dataclass centralizes all hyperparameters and settings for GRU/LSTM
    models used in stock price prediction. It provides sensible defaults while
    allowing full customization.

    Attributes:
        seq_len: Number of past time steps to use as input (lookback window).
            Default: 15 trading days.
        scaler_type: Type of scaler for feature normalization ("robust" or "standard").
            Default: "robust".
        model_type: Type of RNN model ("gru" or "lstm"). Default: "gru".
        hidden_size: Number of hidden units in RNN layers. Default: 32.
        num_layers: Number of stacked RNN layers. Default: 1.
        dropout: Dropout probability for regularization. Default: 0.4.
        batch_size: Number of samples per batch during training. Default: 32.
        learning_rate: Learning rate for the optimizer. Default: 5e-4.
        weight_decay: L2 regularization coefficient. Default: 1e-4.
        max_epochs: Maximum number of training epochs. Default: 100.
        early_stopping_patience: Epochs to wait before stopping if no improvement.
            Default: 10.
        n_splits: Number of cross-validation splits. Default: 5.
        device: Device for training ("cuda" or "cpu"). Auto-detected by default.
    """

    seq_len: int = 15
    scaler_type: str = "robust"
    model_type: str = "gru"
    hidden_size: int = 32
    num_layers: int = 1
    dropout: float = 0.4
    batch_size: int = 32
    learning_rate: float = 5e-4
    weight_decay: float = 1e-4
    max_epochs: int = 100
    early_stopping_patience: int = 10
    n_splits: int = 3
    device: str = None

    def __post_init__(self):
        """Set device to cuda if available, else cpu."""
        if self.device is None:
            if torch is not None and torch.cuda.is_available():
                self.device = "cuda"
            else:
                self.device = "cpu"


# Feature columns that require scaling (RobustScaler)
# These are continuous features with varying ranges that benefit from normalization
# CRITICAL: rsi_14 must be included to prevent gradient imbalance during training
COLUMNS_TO_SCALE = [
    # Returns (percentage changes) - lowercase from build_features
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
    # Technical indicators (if present)
    "macd",
    "macd_signal",
    "macd_hist",
    "cci_14",
    "adx_14",
    "plusdi_14",
    "minusdi_14",
    "atr_14",
    # Bollinger Bands (if present)
    "bb_lower",
    "bb_upper",
]

# Feature columns that pass through without scaling
# These are categorical or already normalized features (typically -1 to 1 or 0 to 1)
PASSTHROUGH_COLUMNS = [
    # Categorical: day of week (0-4 for Mon-Fri)
    "day_of_week",
    # Categorical: has news flag
    "has_news",
    "n_neutral",
    # News sentiment features (already normalized to -1 to 1 range)
    "sentiment_score",
    "relevance_ratio",
    "positive_ratio",
    "negative_ratio",
    # Rolling news sentiment features (already normalized)
    "sentiment_score_3d",
    "sentiment_score_5d",
    "sentiment_score_10d",
    # Sentiment momentum (already normalized)
    "sentiment_momentum_3d",
    # Rolling ratio features
    "positive_ratio_3d",
    "positive_ratio_5d",
    "positive_ratio_10d",
    "negative_ratio_3d",
    "negative_ratio_5d",
    "negative_ratio_10d",
    # News counts
    "n_articles",
    "n_positive",
    "n_negative",
    "n_relevant",
    "news_count_3d",
    "news_count_5d",
    "news_count_10d",
]


def set_seed(seed: int) -> None:
    """Fix random seed for reproducibility across all libraries.

    Sets the random seed for:
    - Python's built-in random module
    - NumPy's random number generator
    - PyTorch (if available) with cudnn deterministic mode
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
        # Ensure deterministic behavior for reproducibility
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
    except ImportError:
        pass

    # Try to set TensorFlow seed if available
    try:
        import tensorflow as tf

        tf.random.set_seed(seed)
    except ImportError:
        pass
