from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import numpy as np
import pandas as pd
import pandas_ta as ta
import yfinance as yf


@dataclass
class FeatureConfig:
    """Configuration for the feature engineering pipeline.

    This configuration is intentionally lightweight for now but provides a
    single place to adjust lookback windows in a controlled way if needed
    later. All defaults are chosen to match the conventions described in
    ``ml_quant.md``.

    Attributes:
        r1_window: Lookback window (in trading days) for the 1-day return
            feature. This is effectively ``pct_change(1)`` but is kept as a
            parameter for completeness.
        r3_window: Lookback window for the 3-day simple return feature.
        r5_window: Lookback window for the 5-day simple return feature.
        rsi_window: Lookback window for the RSI indicator.
        cci_window: Lookback window for the CCI indicator.
        sma_short: Window for the short simple moving average used in the
            trend-distance features (e.g. 20 days).
        sma_long: Window for the longer SMA used in the trend-distance
            features (e.g. 50 days).
        atr_window: Lookback window for the ATR volatility indicator.
        bb_window: Lookback window for the Bollinger Bands midline.
        bb_std: Standard deviation multiplier for Bollinger Bands.
        volume_ma_window: Window for the moving-average volume used in the
            ``Volume_Ratio`` feature.
    """

    r1_window: int = 1
    r3_window: int = 3
    r5_window: int = 5
    rsi_window: int = 14
    cci_window: int = 14
    sma_short: int = 20
    sma_long: int = 50
    atr_window: int = 14
    bb_window: int = 5
    bb_std: float = 2.0
    volume_ma_window: int = 5


def load_ohlcv(ticker: str, period_years: int = 5) -> pd.DataFrame:
    """Load daily OHLCV history for a ticker using yfinance.

    This helper function provides the raw price and volume history required
    by the downstream feature engineering pipeline. It is intentionally
    conservative and focuses on a simple daily frequency as described in
    ``ml_quant.md``.

    The function:

    - normalizes and uppercases the ticker symbol;
    - requests a configurable number of years of history at daily resolution
      using ``yfinance.download`` (5 years by default);
    - sorts by date in ascending order; and
    - drops any rows containing missing values in the OHLCV columns.

    Args:
        ticker: Asset symbol accepted by Yahoo Finance (e.g. ``\"AAPL\"``,
            ``\"NVDA\"``, ``\"BTC-USD\"``, ``\"DOGE-USD\"``).
        period_years: Minimum number of calendar years of history to request.
            The value is converted to a yfinance ``period`` string such as
            ``\"3y\"``.

    Returns:
        A pandas DataFrame indexed by date with at least the following
        columns: ``Open``, ``High``, ``Low``, ``Close``, ``Volume``. Rows
        with missing values in any of these columns are dropped.

    Raises:
        ValueError: If ``ticker`` is empty or if no valid OHLCV data can be
            retrieved from yfinance.
    """

    normalized = (ticker or "").strip().upper()
    if not normalized:
        raise ValueError("ticker is empty.")

    period_str = f"{max(int(period_years), 1)}y"
    # Disable yfinance's progress bar to avoid noisy console output.
    df = yf.download(
        normalized,
        period=period_str,
        interval="1d",
        auto_adjust=False,
        progress=False,
    )
    if df.empty:
        raise ValueError(f"yfinance returned no data for ticker={normalized!r}.")

    # yfinance can return either a flat Index or a MultiIndex for columns.
    # For a single ticker with a MultiIndex, we select the slice associated
    # with the requested symbol.
    if isinstance(df.columns, pd.MultiIndex):
        if normalized in df.columns.get_level_values(0):
            df = df.xs(normalized, axis=1, level=0)
        elif normalized in df.columns.get_level_values(1):
            df = df.xs(normalized, axis=1, level=1)
        else:
            # Fall back to the first level if we cannot match the ticker name.
            df = df.droplevel(0, axis=1)

    # Standardize column names in a case-insensitive way and ensure the
    # expected OHLCV set is present.
    rename_map: dict[str, str] = {}
    for col in df.columns:
        key = str(col).lower()
        if key == "open":
            rename_map[col] = "Open"
        elif key == "high":
            rename_map[col] = "High"
        elif key == "low":
            rename_map[col] = "Low"
        elif key == "close":
            rename_map[col] = "Close"
        elif key in {"adj close", "adjclose", "adjusted close"}:
            rename_map[col] = "Adj Close"
        elif key == "volume":
            rename_map[col] = "Volume"

    if rename_map:
        df = df.rename(columns=rename_map)

    required_cols = ["Open", "High", "Low", "Close", "Volume"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(
            f"Downloaded data for {normalized!r} is missing columns: {missing}."
        )

    df = df.sort_index()
    df = df.dropna(subset=required_cols)
    return df


def _compute_returns_features(df: pd.DataFrame, cfg: FeatureConfig) -> pd.DataFrame:
    """Compute simple return-based features from OHLCV history."""

    out = df.copy()
    close = out["Close"]
    out["Ret_1d"] = close.pct_change(cfg.r1_window)
    out["Ret_3d"] = close.pct_change(cfg.r3_window)
    out["Ret_5d"] = close.pct_change(cfg.r5_window)
    return out


def _compute_momentum_features(df: pd.DataFrame, cfg: FeatureConfig) -> pd.DataFrame:
    """Compute momentum and oscillator style features using pandas_ta."""

    out = df.copy()
    close = out["Close"]

    # RSI
    rsi_series = ta.rsi(close, length=cfg.rsi_window)
    out["RSI_14"] = rsi_series

    # MACD and histogram
    macd_df = ta.macd(close)
    if not macd_df.empty:
        # The default MACD column names follow the pattern MACD_{fast}_{slow}_{signal}
        macd_col = next((c for c in macd_df.columns if "MACD_" in c and "_signal" not in c and "_histogram" not in c), None)
        signal_col = next((c for c in macd_df.columns if "MACDs_" in c or "MACD_signal" in c), None)
        hist_col = next((c for c in macd_df.columns if "MACDh_" in c or "MACD_histogram" in c), None)

        if macd_col is None:
            macd_col = macd_df.columns[0]
        out["MACD"] = macd_df[macd_col]

        if signal_col is not None:
            out["MACD_Signal"] = macd_df[signal_col]
        else:
            out["MACD_Signal"] = out["MACD"].ewm(span=9, adjust=False).mean()

        if hist_col is not None:
            out["MACD_Hist"] = macd_df[hist_col]
        else:
            out["MACD_Hist"] = out["MACD"] - out["MACD_Signal"]

    # CCI
    cci = ta.cci(
        high=out["High"],
        low=out["Low"],
        close=out["Close"],
        length=cfg.cci_window,
    )
    out["CCI_14"] = cci
    return out


def _compute_trend_distance_features(df: pd.DataFrame, cfg: FeatureConfig) -> pd.DataFrame:
    """Compute distance-to-trend features based on simple moving averages."""

    out = df.copy()
    close = out["Close"]
    sma_short = close.rolling(window=cfg.sma_short, min_periods=cfg.sma_short).mean()
    sma_long = close.rolling(window=cfg.sma_long, min_periods=cfg.sma_long).mean()

    out["SMA_20"] = sma_short
    out["SMA_50"] = sma_long
    out["Dist_SMA_20"] = close / sma_short - 1.0
    out["Dist_SMA_50"] = close / sma_long - 1.0
    return out


def _compute_volatility_volume_features(
    df: pd.DataFrame,
    cfg: FeatureConfig,
) -> pd.DataFrame:
    """Compute volatility and volume-related features."""

    out = df.copy()

    # ATR for volatility.
    atr = ta.atr(
        high=out["High"],
        low=out["Low"],
        close=out["Close"],
        length=cfg.atr_window,
    )
    out["ATR_14"] = atr

    # Bollinger Bands.
    bb = ta.bbands(
        close=out["Close"],
        length=cfg.bb_window,
        std=cfg.bb_std,
    )
    if not bb.empty:
        lower_col = next((c for c in bb.columns if "BBL" in c), bb.columns[0])
        upper_col = next((c for c in bb.columns if "BBU" in c), bb.columns[-1])
        out["BBL_5_2.0"] = bb[lower_col]
        out["BBU_5_2.0"] = bb[upper_col]

    # Volume ratio versus a short moving average.
    volume = out["Volume"].astype(float)
    vol_ma = volume.rolling(
        window=cfg.volume_ma_window,
        min_periods=cfg.volume_ma_window,
    ).mean()
    with np.errstate(divide="ignore", invalid="ignore"):
        out["Volume_Ratio"] = volume / vol_ma
    return out


def build_dataset(
    df: pd.DataFrame,
    cfg: FeatureConfig | None = None,
) -> Tuple[pd.DataFrame, pd.Series]:
    """Transform raw OHLCV data into a supervised learning dataset.

    This function implements the full feature engineering and label
    construction pipeline described in ``ml_quant.md``:

    - Derive four groups of technical/relative features:
      simple returns, momentum oscillators, trend-distance measures, and
      volatility/volume indicators.
    - Construct a binary target label representing the next day's direction:
      ``1`` if ``Close_{t+1} > Close_t`` else ``0``.
    - Drop all rows that contain missing values in any feature or in the
      target label. This includes the last row where the future close is not
      known.

    Args:
        df: Raw OHLCV DataFrame with at least ``Open``, ``High``, ``Low``,
            ``Close`` and ``Volume`` columns, sorted in ascending date order.
        cfg: Optional feature configuration. If omitted, sensible defaults
            matching ``ml_quant.md`` are used.

    Returns:
        A tuple ``(X, y)`` where:

        - ``X`` is a DataFrame of engineered features only (no raw absolute
          prices are required by downstream consumers); and
        - ``y`` is a pandas Series of binary labels with index aligned to
          ``X``.

    Raises:
        ValueError: If the resulting dataset has too few rows to be useful
            for model training.
    """

    if cfg is None:
        cfg = FeatureConfig()

    if df.empty:
        raise ValueError("Input OHLCV DataFrame is empty.")

    # Build up the feature set step by step.
    features = df.copy()
    features = _compute_returns_features(features, cfg)
    features = _compute_momentum_features(features, cfg)
    features = _compute_trend_distance_features(features, cfg)
    features = _compute_volatility_volume_features(features, cfg)

    # Construct the binary next-day direction label.
    close = features["Close"]
    future_close = close.shift(-1)
    label = (future_close > close).astype(int)

    # Combine features and label into a single frame to drop NaNs consistently.
    data = features.assign(label=label)
    data = data.dropna()

    if data.shape[0] < 100:
        raise ValueError(
            "After feature engineering and NaN filtering, fewer than 100 rows "
            "remain. This is insufficient for a meaningful time-series split."
        )

    # Remove any absolute price columns from the feature matrix to stay close
    # to the design philosophy of using relative/indicator features. We keep
    # volume only through ``Volume_Ratio``.
    drop_cols = [c for c in ["Open", "High", "Low", "Close", "Adj Close", "Volume"] if c in data.columns]
    data = data.drop(columns=drop_cols)

    y = data["label"].astype(int)
    X = data.drop(columns=["label"])
    return X, y

