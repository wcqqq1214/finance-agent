from __future__ import annotations

import logging
from typing import Any, Dict, TypedDict, cast

from langchain_core.tools import tool

from app.ml.feature_engine import build_dataset, load_ohlcv
from app.ml.model_trainer import predict_proba_latest, train_lightgbm
from app.ml.shap_explainer import ShapSummary, build_markdown_report, explain_latest_sample


logger = logging.getLogger(__name__)


class MlQuantResult(TypedDict, total=False):
    """Typed dictionary representing the ML quant sub-report.

    This structure is designed to be directly serializable into the
    ``ml_quant`` field of ``quant.json`` as documented in ``ml_quant.md``.

    Attributes:
        model: Short identifier for the underlying model family and version
            (for example, ``\"lightgbm_v1\"``).
        target: Name of the prediction target. For this project it is always
            ``\"next_day_direction\"`` (binary up/down).
        data_source: Identifier of the market data source. For the current
            implementation this is ``\"yfinance_direct\"`` to distinguish it
            from any MCP-based fetchers.
        prob_up: Estimated probability that the next trading day's close is
            higher than today's close.
        prediction: Discrete direction label derived from ``prob_up``, one of
            ``\"up\"`` or ``\"down\"``.
        metrics: Dictionary with basic hold-out evaluation metrics such as
            accuracy and AUC.
        shap_insights: Compact SHAP summary as returned by
            :func:`explain_latest_sample`, containing top positive and
            negative feature contributions.
        markdown_report: Human-readable Chinese Markdown report summarizing
            the model's view on the latest market state.
        error: Optional human-readable error message if the pipeline failed
            before producing a meaningful prediction.
    """

    model: str
    target: str
    data_source: str
    prob_up: float
    prediction: str
    metrics: Dict[str, Any]
    shap_insights: ShapSummary
    markdown_report: str
    error: str


def _run_ml_quant_analysis_impl(ticker: str) -> MlQuantResult:
    """Internal implementation for the ML quant analysis pipeline.

    This function is separated from the LangChain tool wrapper so that it can
    be called both from tools (for agent use) and from the reporting pipeline
    (for scheduled batch runs) without duplication.
    """

    normalized = (ticker or "").strip().upper()
    base: MlQuantResult = MlQuantResult(
        model="lightgbm_v1",
        target="next_day_direction",
        data_source="yfinance_direct",
    )

    if not normalized:
        msg = "ticker is empty; cannot run ML quant analysis."
        logger.warning("run_ml_quant_analysis: %s", msg)
        base["error"] = msg
        return base

    try:
        df = load_ohlcv(normalized, period_years=3)
        X, y = build_dataset(df)
        model, metrics = train_lightgbm(X, y)
        prob_up = predict_proba_latest(model, X)
        shap_summary = explain_latest_sample(model, X)
        markdown = build_markdown_report(
            ticker=normalized,
            prob_up=prob_up,
            metrics=metrics,
            shap_summary=shap_summary,
        )
    except Exception as exc:
        msg = (
            "ML quant pipeline failed; this usually indicates insufficient "
            "history, data quality issues, or an internal error. "
            f"{type(exc).__name__}: {exc}"
        )
        logger.warning("run_ml_quant_analysis failed for %s: %s", normalized, msg, exc_info=True)
        base["error"] = msg
        return base

    prediction = "up" if prob_up >= 0.5 else "down"

    base["prob_up"] = float(prob_up)
    base["prediction"] = prediction
    base["metrics"] = cast(Dict[str, Any], metrics)
    base["shap_insights"] = shap_summary
    base["markdown_report"] = markdown
    return base


@tool("run_ml_quant_analysis")
def run_ml_quant_analysis(ticker: str) -> MlQuantResult:
    """Run a LightGBM + SHAP based next-day direction analysis for a single asset.

    This tool is designed for Quant Agents that need a **compact but
    explainable** machine-learning view of an asset's short-term technical
    outlook. Given a ticker (such as ``\"AAPL\"`` or ``\"BTC-USD\"``), it:

    1. Fetches at least three years of daily OHLCV history directly from
       Yahoo Finance via ``yfinance`` (no MCP indirection in the current
       version).
    2. Applies a standardized feature engineering pipeline based on
       ``pandas_ta`` to compute relative/indicator-style features (returns,
       momentum, trend distance, volatility and volume ratios).
    3. Trains a lightweight ``LGBMClassifier`` using a chronological 80/20
       train/test split and evaluates simple hold-out metrics (Accuracy, AUC).
    4. Uses SHAP (Shapley Additive explanations) to attribute the prediction
       for the **most recent day** to individual features, extracting the top
       positive and negative drivers.
    5. Generates a natural-language Chinese Markdown summary that explains the
       model's conclusion and the main risk/driver features.

    Typical usage:

    - When a user asks for a probability-style technical view such as
      \"How likely is BTC-USD to rise tomorrow based on recent price action?\"
    - When a Quant Agent is preparing a structured ``quant.json`` report and
      needs to populate the ``ml_quant`` sub-field for CIO consumption.

    Args:
        ticker: Asset symbol understood by Yahoo Finance (for example,
            ``\"NVDA\"``, ``\"AAPL\"``, ``\"BTC-USD\"``, ``\"DOGE-USD\"``). The
            symbol is internally uppercased; both US equities and major
            crypto pairs are supported as long as Yahoo provides sufficient
            history.

    Returns:
        An ``MlQuantResult`` dictionary that can be serialized directly into
        ``quant.json.ml_quant``. On success it includes keys:

        - ``model``: Currently ``\"lightgbm_v1\"``.
        - ``target``: Always ``\"next_day_direction\"``.
        - ``data_source``: ``\"yfinance_direct\"`` to distinguish from
          MCP-based sources.
        - ``prob_up``: Next-day up-move probability in ``[0, 1]``.
        - ``prediction``: ``\"up\"`` if ``prob_up >= 0.5`` else ``\"down\"``.
        - ``metrics``: Dictionary with at least ``accuracy`` and ``auc`` plus
          a ``train_test_split`` description.
        - ``shap_insights``: Structured SHAP summary with top positive and
          negative features.
        - ``markdown_report``: Chinese Markdown explanation suitable for
          direct inclusion in human-facing or agent-facing reports.

        If an error occurs (for example, insufficient history or network
        issues when calling yfinance), the return value still contains
        ``model``, ``target`` and ``data_source`` along with an ``error``
        field describing the problem. Callers should check for the presence
        of ``error`` before trusting the numeric outputs.
    """

    return _run_ml_quant_analysis_impl(ticker)

