from __future__ import annotations

from typing import Dict, Tuple

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.metrics import accuracy_score, roc_auc_score


def _time_series_split_indices(n_rows: int, train_ratio: float = 0.8) -> Tuple[int, int]:
    """Return start/end indices for a simple time-ordered train/test split.

    The split policy follows the guidance from ``ml_quant.md``:

    - No shuffling is performed.
    - The first ``train_ratio`` fraction of samples (by time index order) are
      used for training.
    - The remaining samples form the test set.

    Args:
        n_rows: Total number of rows in the dataset.
        train_ratio: Fraction of data to allocate to the training segment.

    Returns:
        A tuple ``(train_end, test_start)`` where:

        - training rows occupy ``[0, train_end)``; and
        - test rows occupy ``[test_start, n_rows)``.

    Raises:
        ValueError: If there are not enough rows to create both train and
            test segments.
    """

    if n_rows < 50:
        raise ValueError(
            "At least 50 samples are required to perform a meaningful "
            "time-series train/test split."
        )

    train_end = max(int(n_rows * train_ratio), 1)
    if train_end >= n_rows:
        train_end = n_rows - 1
    test_start = train_end
    if test_start <= 0 or test_start >= n_rows:
        raise ValueError("Failed to compute a valid time-series split boundary.")
    return train_end, test_start


def train_lightgbm(
    X: pd.DataFrame,
    y: pd.Series,
) -> Tuple[LGBMClassifier, Dict[str, float | str]]:
    """Train a lightweight LightGBM classifier on time-ordered data.

    This helper encapsulates the entire model fitting and basic evaluation
    workflow described in ``ml_quant.md``:

    - It performs a chronological 80/20 split of the dataset into train and
      test sets.
    - It fits a shallow ``LGBMClassifier`` to reduce overfitting risk on
      noisy financial series.
    - It computes accuracy and ROC-AUC on the test segment.

    Args:
        X: Feature matrix with rows ordered in time (oldest first).
        y: Binary target label vector aligned with ``X``.

    Returns:
        A tuple ``(model, metrics)`` where ``model`` is the trained
        ``LGBMClassifier`` instance and ``metrics`` is a dictionary containing
        at least:

        - ``\"accuracy\"``: Test-set accuracy as a float in ``[0, 1]``.
        - ``\"auc\"``: Test-set ROC-AUC, or ``NaN`` if it cannot be computed
          (for example, only one class is present in the test labels).
        - ``\"train_test_split\"``: A short descriptor string such as
          ``\"80_20_time_series\"``.
    """

    if X.empty:
        raise ValueError("Feature matrix X is empty.")
    if y.empty:
        raise ValueError("Target vector y is empty.")
    if len(X) != len(y):
        raise ValueError("X and y must have the same number of rows.")

    n_rows = len(X)
    train_end, test_start = _time_series_split_indices(n_rows, train_ratio=0.8)

    X_train = X.iloc[:train_end].copy()
    y_train = y.iloc[:train_end].copy()
    X_test = X.iloc[test_start:].copy()
    y_test = y.iloc[test_start:].copy()

    model = LGBMClassifier(
        objective="binary",
        # Keep trees relatively shallow for noisy financial data, but
        # allow LightGBM enough flexibility to find useful splits.
        max_depth=4,
        n_estimators=300,
        learning_rate=0.03,
        subsample=0.9,
        colsample_bytree=0.9,
        # Make it easier to find splits on small datasets by relaxing
        # the default constraints.
        min_data_in_leaf=10,
        min_gain_to_split=0.0,
        random_state=42,
        n_jobs=-1,
        # Silence training logs in the console; metrics are reported
        # explicitly by this module instead.
        verbose=-1,
        verbosity=-1,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    acc = float(accuracy_score(y_test, y_pred))

    try:
        proba_test = model.predict_proba(X_test)[:, 1]
        auc = float(roc_auc_score(y_test, proba_test))
    except Exception:
        auc = float("nan")

    metrics: Dict[str, float | str] = {
        "accuracy": acc,
        "auc": auc,
        "train_test_split": "80_20_time_series",
    }
    return model, metrics


def predict_proba_latest(model: LGBMClassifier, X: pd.DataFrame) -> float:
    """Return the predicted probability of an upward move for the latest row.

    This utility is intended to be called after training, using the full
    feature matrix (including both train and test periods). It extracts the
    last row in ``X`` and returns the model's probability estimate for the
    positive class (``y = 1``), which corresponds to
    ``\"next day close > today close\"`` in this project.

    Args:
        model: A trained LightGBM classifier.
        X: Full feature matrix used during training, with at least one row.

    Returns:
        A float in ``[0, 1]`` representing the model's estimated probability
        that the next day's return is positive.

    Raises:
        ValueError: If ``X`` is empty.
    """

    if X.empty:
        raise ValueError("Feature matrix X is empty; cannot compute prediction.")

    latest_row = X.iloc[[-1]]
    proba = model.predict_proba(latest_row)[0, 1]
    # Ensure the value is a plain Python float for JSON serialization.
    return float(proba)

