"""Tests for deep learning models module (GRU and LSTM classifiers)."""

import torch
from app.ml.dl_config import DLConfig
from app.ml.dl_models import GRUClassifier, LSTMClassifier, create_model


def test_gru_classifier_forward():
    """Test GRUClassifier forward pass"""
    input_size = 35
    hidden_size = 32
    batch_size = 16
    seq_len = 15

    model = GRUClassifier(input_size=input_size, hidden_size=hidden_size, dropout=0.4)

    # Create dummy input
    x = torch.randn(batch_size, seq_len, input_size)

    # Forward pass
    logits = model(x)

    # Check output shape
    assert logits.shape == (batch_size, 1)


def test_gru_classifier_parameters():
    """Test GRUClassifier has expected parameter count"""
    model = GRUClassifier(input_size=35, hidden_size=32)

    total_params = sum(p.numel() for p in model.parameters())

    # Should be around 6000 parameters
    assert 5000 < total_params < 7000


def test_lstm_classifier_forward():
    """Test LSTMClassifier forward pass"""
    model = LSTMClassifier(input_size=35, hidden_size=32)
    x = torch.randn(16, 15, 35)
    logits = model(x)
    assert logits.shape == (16, 1)


def test_create_model_factory():
    """Test create_model factory function"""
    config = DLConfig(model_type="gru", hidden_size=32)
    model = create_model(input_size=35, config=config)

    assert isinstance(model, GRUClassifier)
    assert model.hidden_size == 32

    config_lstm = DLConfig(model_type="lstm", hidden_size=32)
    model_lstm = create_model(input_size=35, config=config_lstm)

    assert isinstance(model_lstm, LSTMClassifier)
