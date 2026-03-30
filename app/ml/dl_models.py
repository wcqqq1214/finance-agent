"""Neural network models: GRU and LSTM classifiers"""

from __future__ import annotations

import torch
import torch.nn as nn

from app.ml.dl_config import DLConfig


class GRUClassifier(nn.Module):
    """Single-layer GRU binary classifier

    Architecture:
        Input (batch, seq_len, features)
        → GRU (batch, seq_len, hidden_size)
        → Take last timestep (batch, hidden_size)
        → Dropout(0.4)
        → Linear (batch, 1)
        → Output logits (no Sigmoid)

    Design principles:
        - Single layer: prevents overfitting on low-SNR financial data
        - hidden_size=32: ~6k params, suitable for ~5000 daily samples
        - Manual dropout: nn.GRU dropout param ineffective for single layer
        - Output logits: numerically stable with BCEWithLogitsLoss
    """

    def __init__(
        self,
        input_size: int,
        hidden_size: int = 32,
        dropout: float = 0.4,
    ):
        super().__init__()

        self.input_size = input_size
        self.hidden_size = hidden_size

        self.gru = nn.GRU(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=1,
            batch_first=True,
        )

        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass

        Args:
            x: (batch_size, seq_len, input_size)

        Returns:
            logits: (batch_size, 1) raw outputs for BCEWithLogitsLoss
        """
        output, h_n = self.gru(x)
        last_hidden = output[:, -1, :]
        last_hidden = self.dropout(last_hidden)
        logits = self.fc(last_hidden)
        return logits


class LSTMClassifier(nn.Module):
    """Single-layer LSTM binary classifier

    Architecture:
        Input (batch, seq_len, features)
        → LSTM (batch, seq_len, hidden_size)
        → Take last timestep (batch, hidden_size)
        → Dropout(0.4)
        → Linear (batch, 1)
        → Output logits (no Sigmoid)

    Design principles:
        - Single layer: prevents overfitting on low-SNR financial data
        - hidden_size=32: ~6k params, suitable for ~5000 daily samples
        - Manual dropout: nn.LSTM dropout param ineffective for single layer
        - Output logits: numerically stable with BCEWithLogitsLoss
    """

    def __init__(
        self,
        input_size: int,
        hidden_size: int = 32,
        dropout: float = 0.4,
    ):
        super().__init__()

        self.input_size = input_size
        self.hidden_size = hidden_size

        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=1,
            batch_first=True,
        )

        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass

        Args:
            x: (batch_size, seq_len, input_size)

        Returns:
            logits: (batch_size, 1) raw outputs for BCEWithLogitsLoss
        """
        output, (h_n, c_n) = self.lstm(x)
        last_hidden = output[:, -1, :]
        last_hidden = self.dropout(last_hidden)
        logits = self.fc(last_hidden)
        return logits


def create_model(
    input_size: int,
    config: DLConfig,
) -> GRUClassifier | LSTMClassifier:
    """Factory function to create model based on config

    Args:
        input_size: Number of input features
        config: DLConfig with model_type, hidden_size, dropout

    Returns:
        Instantiated model (GRUClassifier or LSTMClassifier)

    Raises:
        ValueError: If model_type not recognized
    """
    if config.model_type == "gru":
        return GRUClassifier(
            input_size=input_size,
            hidden_size=config.hidden_size,
            dropout=config.dropout,
        )
    elif config.model_type == "lstm":
        return LSTMClassifier(
            input_size=input_size,
            hidden_size=config.hidden_size,
            dropout=config.dropout,
        )
    else:
        raise ValueError(f"Unknown model_type: {config.model_type}")
