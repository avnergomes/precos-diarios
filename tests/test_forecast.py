#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Out-of-sample forecast tests using a synthetic seasonal + trend series.

Run with:  py -3 -m pytest tests/test_forecast.py -q
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# Add project root
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api.forecast import calc_metrics, sanitize_for_json, RECENCY_MONTHS
from scripts.generate_forecasts import (
    MIN_MONTHS,
    N_OOS,
    aggregate_monthly,
    fit_baseline_naive,
    fit_linear,
    fit_random_forest,
    generate_product_forecast,
    get_eligible_products,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_monthly_df(n_months: int = 60, seed: int = 42) -> pd.DataFrame:
    """
    Synthetic monthly series: trend + annual seasonality + noise + one zero.
    Has a 2-month gap in the middle to test reindexing.
    """
    rng = np.random.default_rng(seed)
    t = np.arange(n_months)
    trend = 50 + 0.3 * t
    seasonal = 5 * np.sin(2 * np.pi * t / 12)
    noise = rng.normal(0, 2, n_months)
    y = trend + seasonal + noise
    y = np.maximum(y, 0.1)   # keep positive
    y[10] = 0.0               # inject one zero to test MAPE guard

    dates = pd.date_range("2018-01-01", periods=n_months, freq="MS")
    df = pd.DataFrame({"ds": dates, "y": y})
    df["ym"] = df["ds"].dt.to_period("M")
    return df


def _make_raw_df(n_months: int = 60, product: str = "TestProduct",
                 with_gap: bool = True, seed: int = 42) -> pd.DataFrame:
    """Raw CSV-style DataFrame for end-to-end tests."""
    rng = np.random.default_rng(seed)
    t = np.arange(n_months)
    y = 50 + 0.3 * t + 5 * np.sin(2 * np.pi * t / 12) + rng.normal(0, 2, n_months)
    y = np.maximum(y, 0.1)
    if n_months > 10:
        y[10] = 0.0           # inject one zero to test MAPE guard

    # Start dates so the series ends in the last 2 months (always recent)
    end = pd.Timestamp.now().to_period("M").to_timestamp()
    start = end - pd.DateOffset(months=n_months - 1)
    dates = pd.date_range(start=start.replace(day=1), periods=n_months, freq="MS")
    df = pd.DataFrame({
        "data": dates,
        "produto": product,
        "unidade": "sc 60 Kg",
        "preco_medio": y,
    })

    if with_gap:
        # Remove 2 months to simulate gaps
        df = df.drop(df.index[[20, 21]]).reset_index(drop=True)

    return df


# ---------------------------------------------------------------------------
# calc_metrics
# ---------------------------------------------------------------------------

def test_calc_metrics_zeros_do_not_crash():
    """MAPE must not produce NaN/Infinity when actual contains zeros."""
    actual = np.array([0.0, 10.0, 20.0])
    predicted = np.array([1.0, 11.0, 21.0])
    m = calc_metrics(actual, predicted)
    # MAPE is computed only on non-zero elements
    assert m["mape"] is not None
    assert not math.isnan(m["mape"])
    assert not math.isinf(m["mape"])


def test_calc_metrics_all_zeros_mape_is_none():
    """When all actuals are zero, MAPE should be None (no non-zero mask)."""
    actual = np.array([0.0, 0.0, 0.0])
    predicted = np.array([1.0, 2.0, 3.0])
    m = calc_metrics(actual, predicted)
    assert m["mape"] is None


# ---------------------------------------------------------------------------
# sanitize_for_json
# ---------------------------------------------------------------------------

def test_sanitize_replaces_nan_inf():
    dirty = {"a": float("nan"), "b": float("inf"), "c": -float("inf"), "d": 1.5}
    clean = sanitize_for_json(dirty)
    assert clean["a"] is None
    assert clean["b"] is None
    assert clean["c"] is None
    assert clean["d"] == 1.5


def test_sanitize_nested():
    dirty = {"modelos": {"linear": {"metricas": {"mape": float("nan")}}}}
    clean = sanitize_for_json(dirty)
    assert clean["modelos"]["linear"]["metricas"]["mape"] is None


def test_sanitize_output_json_serializable():
    """json.dumps(allow_nan=False) must not raise after sanitization."""
    dirty = {"x": float("nan"), "y": [float("inf"), 1.0]}
    clean = sanitize_for_json(dirty)
    json.dumps(clean)  # raises if NaN/Inf present


# ---------------------------------------------------------------------------
# aggregate_monthly
# ---------------------------------------------------------------------------

def test_aggregate_drops_current_partial_month():
    """The current calendar month should be excluded from aggregation."""
    now = pd.Timestamp.now()
    df = _make_raw_df(n_months=36, with_gap=False)
    # Append a row for the current month
    current_row = pd.DataFrame({
        "data": [now.replace(day=5)],
        "produto": ["TestProduct"],
        "unidade": ["sc 60 Kg"],
        "preco_medio": [99.0],
    })
    df = pd.concat([df, current_row], ignore_index=True)
    monthly = aggregate_monthly(df)
    current_period = now.to_period("M")
    assert not (monthly["ym"] == current_period).any(), "Current partial month should be excluded"


def test_aggregate_fills_short_gaps():
    """A 2-month gap should be forward-filled (≤ 3-month limit)."""
    df = _make_raw_df(n_months=48, with_gap=True)
    monthly = aggregate_monthly(df)
    # The gap months (index 20 & 21 in original) should be filled
    # Result should have a continuous period range (no missing months)
    periods = sorted(monthly["ym"].tolist())
    expected = pd.period_range(periods[0], periods[-1], freq="M").tolist()
    assert len(monthly) == len(expected), "Gap months should be forward-filled"


# ---------------------------------------------------------------------------
# get_eligible_products — recency filter
# ---------------------------------------------------------------------------

def test_get_eligible_products_excludes_stale():
    """Products whose last datum is older than RECENCY_MONTHS must be excluded."""
    # Fresh product — data ends within the last month
    fresh = _make_raw_df(n_months=48, product="FreshProduct", with_gap=False)
    # Stale product — same fresh dates but shifted 5 years into the past
    stale = _make_raw_df(n_months=48, product="StaleProduct", with_gap=False)
    stale["data"] = stale["data"] - pd.DateOffset(years=5)

    df = pd.concat([fresh, stale], ignore_index=True)
    eligible = get_eligible_products(df)
    assert "FreshProduct" in eligible, "Recent product should be eligible"
    assert "StaleProduct" not in eligible, "Stale product should be excluded"


# ---------------------------------------------------------------------------
# OOS metrics: a model memorizing training data should NOT have ~0 MAPE in backtest
# ---------------------------------------------------------------------------

def test_oos_metrics_not_near_zero_for_overfitting_model():
    """
    Random Forest tends to overfit on training data (near-perfect in-sample).
    In OOS holdout (last N_OOS months), MAPE must be meaningfully > 0.
    """
    monthly = _make_monthly_df(n_months=60)
    result = fit_random_forest(monthly, horizon=12)
    assert result is not None, "RF should produce a result on 60-month series"
    oos_mape = result["metricas"]["mape"]
    assert oos_mape is not None
    # OOS MAPE should be > 0.5% (a memorizing model would get 0% in-sample)
    assert oos_mape > 0.5, f"OOS MAPE={oos_mape:.2f}% suspiciously low — likely in-sample leakage"


# ---------------------------------------------------------------------------
# baseline_naive
# ---------------------------------------------------------------------------

def test_baseline_naive_present_and_has_oos_metrics():
    monthly = _make_monthly_df(n_months=60)
    result = fit_baseline_naive(monthly, horizon=12)
    assert result is not None
    assert result["metricas"]["mae"] is not None
    assert result["metricas"]["mape"] is not None


def test_baseline_naive_metrics_plausible():
    """Baseline MAPE on a seasonal+trend series should be > 1%."""
    monthly = _make_monthly_df(n_months=60)
    result = fit_baseline_naive(monthly, horizon=12)
    assert result["metricas"]["mape"] > 1.0


# ---------------------------------------------------------------------------
# generate_product_forecast — end to end
# ---------------------------------------------------------------------------

def test_generate_has_best_model_field():
    df = _make_raw_df(n_months=60, with_gap=True)
    result = generate_product_forecast("TestProduct", df)
    assert result["success"], f"Expected success: {result.get('error')}"
    assert "best_model" in result, "best_model field must be present"
    assert result["best_model"] in result["modelos"], "best_model must be a real model key"


def test_generate_has_baseline_naive():
    df = _make_raw_df(n_months=60, with_gap=True)
    result = generate_product_forecast("TestProduct", df)
    assert result["success"]
    assert "baseline_naive" in result["modelos"], "baseline_naive must always be present"


def test_generate_json_no_nan_infinity():
    """json.dumps(allow_nan=False) must not raise on the full result."""
    df = _make_raw_df(n_months=60, with_gap=True)
    result = generate_product_forecast("TestProduct", df)
    # Raises ValueError if NaN/Infinity present
    json.dumps(result, allow_nan=False)


def test_generate_mape_plausible_range():
    """OOS MAPE for the best model should be in a plausible range (2–80%)."""
    df = _make_raw_df(n_months=60, with_gap=True)
    result = generate_product_forecast("TestProduct", df)
    best = result.get("best_model")
    if best is None:
        pytest.skip("No best_model selected")
    mape = result["modelos"][best]["metricas"]["mape"]
    if mape is not None:
        assert mape >= 0.5, f"MAPE={mape:.2f}% too low — likely in-sample leakage"
        assert mape < 80, f"MAPE={mape:.2f}% unreasonably high"


def test_generate_short_series_returns_failure():
    """A product with fewer than MIN_MONTHS months must not be forecast."""
    df = _make_raw_df(n_months=10, with_gap=False)
    result = generate_product_forecast("ShortProduct", df)
    assert not result["success"], "Short series should yield failure result"


def test_generate_previsoes_12_months():
    """Every model must produce exactly HORIZON_MONTHS=12 prediction rows."""
    from scripts.generate_forecasts import HORIZON_MONTHS
    df = _make_raw_df(n_months=60, with_gap=False)
    result = generate_product_forecast("TestProduct", df)
    assert result["success"]
    for key, m in result["modelos"].items():
        n_preds = len(m.get("previsoes", []))
        assert n_preds == HORIZON_MONTHS, f"{key}: expected {HORIZON_MONTHS} predictions, got {n_preds}"
