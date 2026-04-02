from __future__ import annotations

from app.ml.signal_filter import apply_similarity_signal_filter


def test_similarity_signal_filter_confirms_direction():
    summary = apply_similarity_signal_filter(
        0.44,
        {
            "n_matches": 8,
            "avg_future_return_3d": -0.0229,
        },
    )

    assert summary["alignment"] == "confirmed"
    assert summary["position_multiplier"] == 1.25
    assert summary["ml_policy"] == "primary_signal"
    assert summary["adjusted_probability"] < 0.44


def test_similarity_signal_filter_contradicts_direction():
    summary = apply_similarity_signal_filter(
        0.56,
        {
            "n_matches": 8,
            "avg_future_return_3d": -0.0229,
        },
    )

    assert summary["alignment"] == "contradicted"
    assert summary["position_multiplier"] == 0.5
    assert summary["ml_policy"] == "primary_signal"
    assert 0.5 < summary["adjusted_probability"] < 0.56


def test_similarity_signal_filter_auxiliary_policy_caps_position_by_auc():
    summary = apply_similarity_signal_filter(
        0.56,
        {
            "n_matches": 8,
            "avg_future_return_3d": 0.0229,
        },
        requested_symbol_auc=0.54,
    )

    assert summary["alignment"] == "confirmed"
    assert summary["ml_policy"] == "auxiliary_only"
    assert summary["auc_multiplier"] == 0.5
    assert summary["similarity_multiplier"] == 1.25
    assert summary["position_multiplier"] == 0.625
    assert 0.5 < summary["adjusted_probability"] < 0.56


def test_similarity_signal_filter_event_driven_policy_disables_ml_direction():
    summary = apply_similarity_signal_filter(
        0.56,
        {
            "n_matches": 8,
            "avg_future_return_3d": 0.0229,
        },
        requested_symbol_auc=0.52,
    )

    assert summary["alignment"] == "confirmed"
    assert summary["ml_policy"] == "event_driven_only"
    assert summary["ml_signal_enabled"] is False
    assert summary["position_multiplier"] == 0.0
    assert summary["adjusted_probability"] == 0.5
