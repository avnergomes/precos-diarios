#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pre-compute price forecasts for all eligible products.
Generates static JSON files served by GitHub Pages — no API dependency.

Models: Linear Regression, ARIMA, Auto ARIMA (SARIMA), Random Forest, XGBoost,
        Baseline Sazonal-Ingênuo, Prophet (optional).

Metrics are out-of-sample (holdout last N_OOS months).
IC for ML/linear models uses OOS residual std.
"""

import json
import logging
import os
import re
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

# Add project root to path so we can import from api.forecast
_BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BASE_DIR))
from api.forecast import calc_metrics, sanitize_for_json, RECENCY_MONTHS  # noqa: E402

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_DIR = _BASE_DIR
CSV_PATH = BASE_DIR / "data" / "processed" / "consolidated.csv"

# Default output dirs; override via env vars for testing
_DEFAULT_OUTPUT_DIR = BASE_DIR / "dashboard" / "public" / "data" / "forecasts"
_DEFAULT_PRODUCTS_JSON = BASE_DIR / "dashboard" / "public" / "data" / "forecast_products.json"

OUTPUT_DIR = Path(os.environ.get("FORECAST_OUTPUT_DIR", str(_DEFAULT_OUTPUT_DIR)))
PRODUCTS_JSON = Path(os.environ.get("FORECAST_PRODUCTS_JSON", str(_DEFAULT_PRODUCTS_JSON)))

MIN_MONTHS = 24       # minimum for seasonal models
HORIZON_MONTHS = 12   # pre-compute 12 months
HISTORY_MONTHS = 36
N_OOS = 12            # out-of-sample holdout months for backtest
CONFIDENCE = 0.05     # 95% CI

# Optional heavy deps
try:
    from prophet import Prophet
    HAS_PROPHET = True
except ImportError:
    HAS_PROPHET = False
    logger.info("Prophet not installed — skipping Prophet model")

try:
    import xgboost as xgb
    HAS_XGB = True
except ImportError:
    HAS_XGB = False
    logger.info("XGBoost not installed — skipping XGBoost model")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def slugify(name: str) -> str:
    """Convert product name to filesystem-safe slug."""
    s = name.lower().strip()
    s = re.sub(r"[àáâãäå]", "a", s)
    s = re.sub(r"[èéêë]", "e", s)
    s = re.sub(r"[ìíîï]", "i", s)
    s = re.sub(r"[òóôõö]", "o", s)
    s = re.sub(r"[ùúûü]", "u", s)
    s = re.sub(r"[ç]", "c", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def build_lag_features(series: np.ndarray, months: np.ndarray, n_lags: int = 6):
    """Build feature matrix for ML models (RF, XGBoost)."""
    X, y = [], []
    for i in range(n_lags, len(series)):
        row = list(series[i - n_lags: i]) + [float(months[i]), float(i)]
        X.append(row)
        y.append(series[i])
    return np.array(X), np.array(y)


# ---------------------------------------------------------------------------
# Out-of-sample backtest helper
# ---------------------------------------------------------------------------

def _oos_holdout(monthly: pd.DataFrame, fit_fn, n_oos: int = N_OOS):
    """
    Hold out last n_oos months, refit on the remainder, return OOS metrics dict
    (keys: mae, rmse, mape, r2, residual_std) or None if infeasible.
    """
    if len(monthly) < MIN_MONTHS + n_oos:
        return None
    train = monthly.iloc[:-n_oos].reset_index(drop=True)
    test_actual = monthly.iloc[-n_oos:]["y"].values

    result = fit_fn(train, n_oos)
    if result is None:
        return None

    preds_raw = [p["previsto"] for p in result.get("previsoes", [])[:n_oos]]
    if len(preds_raw) < len(test_actual):
        return None

    preds = np.array(preds_raw[: len(test_actual)], dtype=float)
    residuals = test_actual - preds
    m = calc_metrics(test_actual, preds)
    m["residual_std"] = float(np.std(residuals))
    return m


# ---------------------------------------------------------------------------
# Model implementations
# ---------------------------------------------------------------------------

def fit_linear(monthly: pd.DataFrame, horizon: int) -> Optional[Dict]:
    """Simple linear regression with OOS-based IC."""
    try:
        y = monthly["y"].values
        x = np.arange(len(y))
        n = len(x)
        slope = (n * np.sum(x * y) - np.sum(x) * np.sum(y)) / (n * np.sum(x ** 2) - np.sum(x) ** 2)
        intercept = (np.sum(y) - slope * np.sum(x)) / n

        y_pred = intercept + slope * x
        # IC from training residuals (used only as fallback; caller replaces with OOS std)
        std_err = float(np.std(y - y_pred)) * 1.96

        last_date = monthly["ds"].iloc[-1]
        dates = pd.date_range(start=last_date + pd.DateOffset(months=1), periods=horizon, freq="MS")

        preds = []
        for i, d in enumerate(dates):
            p = intercept + slope * (n + i)
            preds.append({
                "data": d.strftime("%Y-%m-%d"),
                "previsto": round(float(p), 2),
                "ic_inferior": round(float(p - std_err), 2),
                "ic_superior": round(float(p + std_err), 2),
            })

        metrics_train = calc_metrics(y, y_pred)

        return {
            "nome": "Regressão Linear",
            "r_squared": metrics_train["r2"],
            "previsoes": preds,
            "metricas": metrics_train,
            "_slope": float(slope),
            "_intercept": float(intercept),
            "_n": n,
        }
    except Exception as e:
        logger.warning(f"  Linear failed: {e}")
        return None


def fit_arima(monthly: pd.DataFrame, horizon: int) -> Optional[Dict]:
    """ARIMA with auto (p,d,q) selection."""
    try:
        from statsmodels.tsa.arima.model import ARIMA
        from statsmodels.tsa.stattools import adfuller

        series = monthly.set_index("ds")["y"]

        try:
            d = 0 if adfuller(series, autolag="AIC")[1] < 0.05 else 1
        except Exception:
            d = 1

        best_aic, best_order = float("inf"), (1, d, 1)
        for p in range(3):
            for q in range(3):
                try:
                    m = ARIMA(series, order=(p, d, q)).fit()
                    if m.aic < best_aic:
                        best_aic, best_order = m.aic, (p, d, q)
                except Exception:
                    continue

        model = ARIMA(series, order=best_order).fit()
        fc = model.get_forecast(steps=horizon)
        pred_mean = np.asarray(fc.predicted_mean)
        conf = np.asarray(fc.conf_int(alpha=CONFIDENCE))

        fitted = np.asarray(model.fittedvalues)
        actual = monthly["y"].values[-len(fitted):]
        metrics_train = calc_metrics(actual, fitted)

        last_date = monthly["ds"].iloc[-1]
        dates = pd.date_range(start=last_date + pd.DateOffset(months=1), periods=horizon, freq="MS")

        preds = [
            {
                "data": d.strftime("%Y-%m-%d"),
                "previsto": round(float(pred_mean[i]), 2),
                "ic_inferior": round(float(conf[i, 0]), 2),
                "ic_superior": round(float(conf[i, 1]), 2),
            }
            for i, d in enumerate(dates)
        ]

        return {
            "nome": "ARIMA",
            "ordem": list(best_order),
            "previsoes": preds,
            "metricas": metrics_train,
        }
    except Exception as e:
        logger.warning(f"  ARIMA failed: {e}")
        return None


def fit_auto_arima(monthly: pd.DataFrame, horizon: int) -> Optional[Dict]:
    """Auto ARIMA with seasonal component (SARIMA)."""
    try:
        from statsmodels.tsa.statespace.sarimax import SARIMAX
        from statsmodels.tsa.stattools import adfuller

        series = monthly.set_index("ds")["y"]

        try:
            d = 0 if adfuller(series, autolag="AIC")[1] < 0.05 else 1
        except Exception:
            d = 1

        best_aic = float("inf")
        best_order = (1, d, 1)
        best_seasonal = (0, 0, 0, 12)

        for p in range(3):
            for q in range(3):
                try:
                    m = SARIMAX(series, order=(p, d, q), seasonal_order=(0, 0, 0, 12),
                                enforce_stationarity=False, enforce_invertibility=False).fit(disp=False)
                    if m.aic < best_aic:
                        best_aic = m.aic
                        best_order = (p, d, q)
                        best_seasonal = (0, 0, 0, 12)
                except Exception:
                    continue

        if len(series) >= 24:
            for P in range(2):
                for Q in range(2):
                    for D in range(2):
                        try:
                            m = SARIMAX(series, order=best_order,
                                        seasonal_order=(P, D, Q, 12),
                                        enforce_stationarity=False, enforce_invertibility=False).fit(disp=False)
                            if m.aic < best_aic:
                                best_aic = m.aic
                                best_seasonal = (P, D, Q, 12)
                        except Exception:
                            continue

        model = SARIMAX(series, order=best_order, seasonal_order=best_seasonal,
                        enforce_stationarity=False, enforce_invertibility=False).fit(disp=False)

        fc = model.get_forecast(steps=horizon)
        pred_mean = np.asarray(fc.predicted_mean)
        conf = np.asarray(fc.conf_int(alpha=CONFIDENCE))

        fitted = np.asarray(model.fittedvalues)
        actual = monthly["y"].values[-len(fitted):]
        metrics_train = calc_metrics(actual, fitted)

        last_date = monthly["ds"].iloc[-1]
        dates = pd.date_range(start=last_date + pd.DateOffset(months=1), periods=horizon, freq="MS")

        preds = [
            {
                "data": dt.strftime("%Y-%m-%d"),
                "previsto": round(float(pred_mean[i]), 2),
                "ic_inferior": round(float(conf[i, 0]), 2),
                "ic_superior": round(float(conf[i, 1]), 2),
            }
            for i, dt in enumerate(dates)
        ]

        return {
            "nome": "Auto ARIMA (SARIMA)",
            "ordem": list(best_order),
            "ordem_sazonal": list(best_seasonal),
            "previsoes": preds,
            "metricas": metrics_train,
        }
    except Exception as e:
        logger.warning(f"  Auto ARIMA failed: {e}")
        return None


def _fit_ml_model(monthly: pd.DataFrame, horizon: int, model_cls, model_name: str, **model_kwargs) -> Optional[Dict]:
    """Generic ML model fitting (Random Forest / XGBoost) with OOS metrics."""
    try:
        y_all = monthly["y"].values
        months_all = monthly["ds"].dt.month.values
        n_lags = min(6, len(y_all) - 1)

        if len(y_all) < n_lags + 2:
            return None

        # OOS holdout for metrics and IC calibration
        n_oos_actual = min(N_OOS, len(y_all) - MIN_MONTHS)
        oos_metrics_dict = None
        oos_residual_std = None

        if n_oos_actual >= 6:
            train_y = y_all[:-n_oos_actual]
            train_m = months_all[:-n_oos_actual]
            test_y = y_all[-n_oos_actual:]
            n_lags_oos = min(6, len(train_y) - 1)

            X_tr, y_tr = build_lag_features(train_y, train_m, n_lags_oos)
            if len(X_tr) > 0:
                m_oos = model_cls(**model_kwargs)
                m_oos.fit(X_tr, y_tr)

                buf = list(train_y[-n_lags_oos:])
                oos_preds = []
                idx_oos = len(train_y)
                month_oos = int(monthly["ds"].iloc[-n_oos_actual - 1].month)
                for _ in range(n_oos_actual):
                    month_oos = (month_oos % 12) + 1
                    row = np.array([buf[-n_lags_oos:] + [float(month_oos), float(idx_oos)]])
                    p = float(m_oos.predict(row)[0])
                    buf.append(p)
                    oos_preds.append(p)
                    idx_oos += 1

                oos_preds_arr = np.array(oos_preds)
                test_y_trimmed = test_y[: len(oos_preds_arr)]
                oos_residual_std = float(np.std(test_y_trimmed - oos_preds_arr))
                oos_metrics_dict = calc_metrics(test_y_trimmed, oos_preds_arr)

        # Full model on all data for future predictions
        X, y = build_lag_features(y_all, months_all, n_lags)
        model = model_cls(**model_kwargs)
        model.fit(X, y)
        y_pred_train = model.predict(X)

        # Pick metrics and IC std
        if oos_metrics_dict is not None:
            metrics = oos_metrics_dict
            std_err = oos_residual_std * 1.96
        else:
            # ponytail: in-sample fallback; fires only for very short series
            logger.warning(f"  {model_name}: série curta, usando métricas in-sample como fallback")
            metrics = calc_metrics(y, y_pred_train)
            std_err = float(np.std(y - y_pred_train)) * 1.96

        last_date = monthly["ds"].iloc[-1]
        dates = pd.date_range(start=last_date + pd.DateOffset(months=1), periods=horizon, freq="MS")

        buf = list(y_all[-n_lags:])
        preds = []
        idx = len(y_all)
        month = int(last_date.month)
        for dt in dates:
            month = (month % 12) + 1
            row = np.array([buf[-n_lags:] + [float(month), float(idx)]])
            p = float(model.predict(row)[0])
            buf.append(p)
            idx += 1
            preds.append({
                "data": dt.strftime("%Y-%m-%d"),
                "previsto": round(p, 2),
                "ic_inferior": round(p - std_err, 2),
                "ic_superior": round(p + std_err, 2),
            })

        return {"nome": model_name, "previsoes": preds, "metricas": metrics}
    except Exception as e:
        logger.warning(f"  {model_name} failed: {e}")
        return None


def fit_random_forest(monthly: pd.DataFrame, horizon: int) -> Optional[Dict]:
    from sklearn.ensemble import RandomForestRegressor
    return _fit_ml_model(monthly, horizon, RandomForestRegressor, "Random Forest",
                         n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)


def fit_xgboost(monthly: pd.DataFrame, horizon: int) -> Optional[Dict]:
    if not HAS_XGB:
        return None
    return _fit_ml_model(monthly, horizon, xgb.XGBRegressor, "XGBoost",
                         n_estimators=200, max_depth=5, learning_rate=0.1,
                         random_state=42, verbosity=0)


def fit_baseline_naive(monthly: pd.DataFrame, horizon: int) -> Optional[Dict]:
    """
    Seasonal-naive baseline: predicted[t] = actual[t-12] when available,
    else actual[t-1] (simple naive). Also computes OOS metrics from holdout.
    """
    try:
        y = monthly["y"].values
        n = len(y)
        last_date = monthly["ds"].iloc[-1]
        dates = pd.date_range(start=last_date + pd.DateOffset(months=1), periods=horizon, freq="MS")

        # Build baseline predictions for future horizon
        preds = []
        for i in range(horizon):
            # Seasonal lag: look back 12 months from forecast step
            lag = 12
            idx_src = n - lag + i
            if idx_src < 0:
                idx_src = n - 1  # simple naive fallback
            val = float(y[min(idx_src, n - 1)])
            preds.append(val)

        # OOS metrics using same seasonal naive logic
        n_oos_actual = min(N_OOS, n - MIN_MONTHS)
        oos_metrics_dict = None
        if n_oos_actual >= 6:
            test_y = y[-n_oos_actual:]
            oos_preds = []
            for i in range(n_oos_actual):
                lag_idx = n - n_oos_actual - 12 + i
                if lag_idx < 0:
                    lag_idx = max(0, n - n_oos_actual - 1)
                oos_preds.append(float(y[min(lag_idx, n - n_oos_actual - 1)]))
            oos_metrics_dict = calc_metrics(test_y, np.array(oos_preds))

        # IC from OOS residuals
        if oos_metrics_dict is not None:
            test_y_arr = y[-n_oos_actual:]
            oos_arr = np.array([
                float(y[min(n - n_oos_actual - 12 + i, n - n_oos_actual - 1)])
                for i in range(n_oos_actual)
            ])
            std_err = float(np.std(test_y_arr - oos_arr)) * 1.96
        else:
            std_err = float(np.std(y)) * 1.96

        metrics = oos_metrics_dict if oos_metrics_dict is not None else calc_metrics(y[-horizon:], np.array(preds[:len(y[-horizon:])]))

        pred_dicts = [
            {
                "data": d.strftime("%Y-%m-%d"),
                "previsto": round(p, 2),
                "ic_inferior": round(p - std_err, 2),
                "ic_superior": round(p + std_err, 2),
            }
            for d, p in zip(dates, preds)
        ]

        return {
            "nome": "Baseline Sazonal-Ingênuo",
            "previsoes": pred_dicts,
            "metricas": metrics,
        }
    except Exception as e:
        logger.warning(f"  Baseline naive failed: {e}")
        return None


def fit_prophet_model(monthly: pd.DataFrame, horizon: int) -> Optional[Dict]:
    """Prophet — optional; silently skipped if not installed."""
    if not HAS_PROPHET:
        return None
    try:
        import logging as lg
        lg.getLogger("prophet").setLevel(lg.WARNING)
        lg.getLogger("cmdstanpy").setLevel(lg.WARNING)

        df = monthly[["ds", "y"]].copy()
        m = Prophet(yearly_seasonality=True, weekly_seasonality=False,
                    daily_seasonality=False, changepoint_prior_scale=0.05)
        m.fit(df)

        future = m.make_future_dataframe(periods=horizon, freq="MS")
        fc = m.predict(future)

        last_date = monthly["ds"].iloc[-1]
        future_fc = fc[fc["ds"] > last_date]

        preds = [
            {
                "data": row["ds"].strftime("%Y-%m-%d"),
                "previsto": round(float(row["yhat"]), 2),
                "ic_inferior": round(float(row["yhat_lower"]), 2),
                "ic_superior": round(float(row["yhat_upper"]), 2),
            }
            for _, row in future_fc.iterrows()
        ]

        # OOS metrics via holdout (refit on subset)
        oos = _oos_holdout(monthly, fit_prophet_model, n_oos=min(N_OOS, len(monthly) - MIN_MONTHS))
        if oos is not None:
            metrics = {k: v for k, v in oos.items() if k != "residual_std"}
        else:
            in_sample = m.predict(df)
            metrics = calc_metrics(df["y"].values, in_sample["yhat"].values)

        return {"nome": "Prophet", "previsoes": preds, "metricas": metrics}
    except Exception as e:
        logger.warning(f"  Prophet failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def load_and_prepare() -> pd.DataFrame:
    """Load CSV with defensive dedup by (data, produto, unidade)."""
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    df["data"] = pd.to_datetime(df["data"], errors="coerce")
    df = df.dropna(subset=["data"])
    # Defensive dedup: if duplicates exist per (date, product, unit), average price
    dedup_cols = [c for c in ["data", "produto", "unidade"] if c in df.columns]
    if dedup_cols:
        num_before = len(df)
        df = df.groupby(dedup_cols, as_index=False)["preco_medio"].mean()
        if len(df) < num_before:
            logger.info(f"  Deduplication removed {num_before - len(df)} rows")
    return df


def get_eligible_products(df: pd.DataFrame) -> List[str]:
    """
    Products eligible for forecasting:
    - >= MIN_MONTHS distinct month-year observations
    - last data point within RECENCY_MONTHS months of today
    """
    df = df.copy()
    df["ym"] = df["data"].dt.to_period("M")
    current_period = pd.Timestamp.now().to_period("M")
    recency_cutoff = current_period - RECENCY_MONTHS

    last_obs = df.groupby("produto")["ym"].max()
    recent_products = last_obs[last_obs >= recency_cutoff].index

    counts = df[df["produto"].isin(recent_products)].groupby("produto")["ym"].nunique()
    return sorted(counts[counts >= MIN_MONTHS].index.tolist())


def aggregate_monthly(df: pd.DataFrame) -> pd.DataFrame:
    """
    Daily → monthly averages.
    - Drops current (partial) month.
    - Reindexes to fill missing months (forward-fill up to 3 consecutive gaps;
      ponytail: longer gaps stay NaN and are dropped, reducing eligible count).
    """
    df = df.copy()
    df["ym"] = df["data"].dt.to_period("M")

    # Drop current partial month
    current_period = pd.Timestamp.now().to_period("M")
    df = df[df["ym"] < current_period]

    monthly = df.groupby("ym").agg({"preco_medio": "mean"}).reset_index()

    if monthly.empty:
        return pd.DataFrame(columns=["ym", "ds", "y"])

    # Reindex to fill missing months
    full_idx = pd.period_range(monthly["ym"].min(), monthly["ym"].max(), freq="M")
    y_series = pd.Series(monthly["preco_medio"].values, index=monthly["ym"].values)
    y_series = y_series.reindex(full_idx)
    # Forward-fill short gaps (up to 3 months); longer gaps stay NaN
    y_series = y_series.ffill(limit=3)
    y_series = y_series.dropna()

    result = pd.DataFrame({"ym": y_series.index, "y": y_series.values})
    result["ds"] = result["ym"].apply(lambda p: p.to_timestamp())
    return result.sort_values("ds").reset_index(drop=True)


def _apply_oos_metrics(result: Dict, monthly: pd.DataFrame, fit_fn, model_key: str) -> Dict:
    """
    Run OOS holdout for a model and overwrite its metricas with OOS values.
    Also update IC band width in previsoes using OOS residual std (for linear/ML models).
    """
    n_oos_actual = min(N_OOS, len(monthly) - MIN_MONTHS)
    if n_oos_actual < 6:
        return result

    oos = _oos_holdout(monthly, fit_fn, n_oos=n_oos_actual)
    if oos is None:
        return result

    oos_clean = {k: v for k, v in oos.items() if k != "residual_std"}
    result["metricas"] = oos_clean

    # Update IC band for linear/ML models (ARIMA uses its own analytical CI)
    if model_key in ("linear", "random_forest", "xgboost") and oos.get("residual_std") is not None:
        std_err = oos["residual_std"] * 1.96
        new_preds = []
        for p in result.get("previsoes", []):
            pv = p["previsto"]
            new_preds.append({
                "data": p["data"],
                "previsto": pv,
                "ic_inferior": round(pv - std_err, 2),
                "ic_superior": round(pv + std_err, 2),
            })
        result["previsoes"] = new_preds

    return result


def generate_product_forecast(product: str, product_df: pd.DataFrame) -> Dict:
    """Run all models for one product, compute OOS metrics, pick best model."""
    monthly = aggregate_monthly(product_df)

    if len(monthly) < MIN_MONTHS:
        return {"success": False, "produto": product, "error": f"Dados insuficientes: {len(monthly)} meses"}

    result: Dict = {
        "success": False,
        "produto": product,
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "horizonte_meses": HORIZON_MONTHS,
        "meses_historico": len(monthly),
        "historico": [
            {"data": row["ds"].strftime("%Y-%m-%d"), "valor": round(float(row["y"]), 2)}
            for _, row in monthly.tail(HISTORY_MONTHS).iterrows()
        ],
        "modelos": {},
    }

    model_specs = [
        ("linear", fit_linear),
        ("arima", fit_arima),
        ("auto_arima", fit_auto_arima),
        ("random_forest", fit_random_forest),
        ("xgboost", fit_xgboost),
        ("baseline_naive", fit_baseline_naive),
        ("prophet", fit_prophet_model),
    ]

    for key, fn in model_specs:
        logger.info(f"  Fitting {key}...")
        m = fn(monthly, HORIZON_MONTHS)
        if m is None:
            continue

        # OOS metrics: baseline_naive handles its own; others go through _apply_oos_metrics
        if key not in ("baseline_naive", "prophet"):
            m = _apply_oos_metrics(m, monthly, fn, key)

        # Strip internal keys not meant for JSON
        m = {k: v for k, v in m.items() if not k.startswith("_")}
        result["modelos"][key] = m

    result["success"] = len(result["modelos"]) > 0
    if not result["success"]:
        result["error"] = "Nenhum modelo conseguiu gerar previsões"
        return sanitize_for_json(result)

    # Select best model by OOS MAE (exclude baseline from the "winner" selection
    # so the front can compare; baseline is always shown)
    candidate_keys = [k for k in result["modelos"] if k != "baseline_naive"]
    best_model = None
    best_mae = float("inf")
    for k in candidate_keys:
        mae = result["modelos"][k].get("metricas", {}).get("mae")
        if mae is not None and mae < best_mae:
            best_mae = mae
            best_model = k

    result["best_model"] = best_model

    return sanitize_for_json(result)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate agricultural price forecasts")
    parser.add_argument("--output-dir", default=None,
                        help="Override output directory for forecast JSONs")
    parser.add_argument("--products-json", default=None,
                        help="Override output path for forecast_products.json")
    args = parser.parse_args()

    global OUTPUT_DIR, PRODUCTS_JSON
    if args.output_dir:
        OUTPUT_DIR = Path(args.output_dir)
    if args.products_json:
        PRODUCTS_JSON = Path(args.products_json)

    logger.info("=== Generating forecasts ===")
    logger.info(f"CSV: {CSV_PATH}")
    logger.info(f"Output: {OUTPUT_DIR}")

    if not CSV_PATH.exists():
        logger.error(f"File not found: {CSV_PATH}")
        sys.exit(1)

    df = load_and_prepare()
    products = get_eligible_products(df)
    logger.info(f"Eligible products (recent + {MIN_MONTHS}+ months): {len(products)}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    success_count = 0
    product_list = []

    for i, product in enumerate(products, 1):
        logger.info(f"[{i}/{len(products)}] {product}")
        product_df = df[df["produto"] == product]
        result = generate_product_forecast(product, product_df)

        slug = slugify(product)
        out_path = OUTPUT_DIR / f"{slug}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=None)

        if result["success"]:
            success_count += 1
            models_ok = list(result["modelos"].keys())
            product_list.append({
                "produto": product,
                "slug": slug,
                "modelos": models_ok,
                "best_model": result.get("best_model"),
            })
            logger.info(f"  OK — models: {models_ok}, best: {result.get('best_model')}")
        else:
            logger.warning(f"  FAILED — {result.get('error')}")

    # Remove orphan forecast files (products no longer eligible)
    eligible_slugs = {slugify(p) for p in products}
    for orphan in OUTPUT_DIR.glob("*.json"):
        if orphan.stem not in eligible_slugs:
            logger.info(f"  Removing orphan: {orphan.name}")
            orphan.unlink()

    # Write products index
    index = {
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "total": len(product_list),
        "produtos": product_list,
    }
    PRODUCTS_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(PRODUCTS_JSON, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    logger.info(f"=== Done: {success_count}/{len(products)} products forecasted ===")
    logger.info(f"Index: {PRODUCTS_JSON}")


if __name__ == "__main__":
    main()
