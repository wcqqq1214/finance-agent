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
    n_splits: int = 5
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
# CRITICAL: RSI_14 must be included to prevent gradient imbalance during training
COLUMNS_TO_SCALE = [
    # Returns (percentage changes) - CamelCase from build_dataset
    "Ret_1d",
    "Ret_3d",
    "Ret_5d",
    "Ret_10d",
    # Volatility features
    "Volatility_5d",
    "Volatility_10d",
    # Volume ratio
    "Volume_Ratio",
    # Gap (price gap from previous close)
    "Gap",
    # Moving average ratio
    "Dist_SMA_20",
    # RSI (0-100 scale, but needs normalization for neural networks)
    "RSI_14",
    # MACD features
    "MACD",
    "MACD_Signal",
    "MACD_Hist",
    # Technical indicators
    "CCI_14",
    "ADX_14",
    "PlusDI_14",
    "MinusDI_14",
    "ATR_14",
    # Bollinger Bands
    "BBL_5_2.0",
    "BBU_5_2.0",
]

# Feature columns that pass through without scaling
# These are categorical or already normalized features (typically -1 to 1 or 0 to 1)
PASSTHROUGH_COLUMNS = [
    # Categorical: day of week (0-4 for Mon-Fri)
    "DayOfWeek",
    # Categorical: has news flag
    "HasNews",
    # DXY features
    "DXY_Ret_1d",
    "DXY_Ret_5d",
    # VIX
    "VIX",
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
