from __future__ import annotations

import numpy as np
import pandas as pd

from app.ml.text_features import (
    fit_text_svd_features,
    get_text_svd_columns,
    transform_text_svd_features,
)


def test_fit_text_svd_features_returns_fixed_width_output():
    train_text = pd.Series(
        [
            "apple iphone demand strong services growth",
            "microsoft azure growth and copilot demand",
            "apple services margin expands on installed base",
            "microsoft cloud margins improve with enterprise demand",
        ]
    )
    inference_text = pd.Series(["apple launches new iphone and services bundle"])

    train_df, infer_df, artifacts = fit_text_svd_features(
        train_text,
        inference_text,
        n_components=4,
        min_df=1,
    )

    assert list(train_df.columns) == get_text_svd_columns(4)
    assert list(infer_df.columns) == get_text_svd_columns(4)
    assert train_df.shape == (4, 4)
    assert infer_df.shape == (1, 4)
    assert artifacts is not None
    assert np.isfinite(train_df.to_numpy()).all()


def test_transform_text_svd_features_without_artifacts_returns_zeros():
    text = pd.Series(["", "no news"])
    out = transform_text_svd_features(text, artifacts=None)

    assert out.shape == (2, 10)
    assert out.eq(0.0).all().all()
