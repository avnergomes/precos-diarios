#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pre-compute price forecasts for all eligible products.
Generates static JSON files served by GitHub Pages — no API dependency.

Models: Linear Regression, ARIMA, Auto ARIMA (SARIMA), Random Forest, XGBoost, Prophet (optional).
"""

import json
import logging
import re
import warnings
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = BASE_DIR / "data" / "processed" / "consolidated.csv"
OUTPUT_DIR = BASE_DIR / "dashboard" / "public" / "data" / "forecasts"
PRODUCTS_JSON = BASE_DIR / "dashboard" / "public" / "data" / "forecast_products.json"

MIN_MONTHS = 6
HORIZON_MONTHS = 12  # pre-compute 12 months; frontend trims by user selection
HISTORY_MONTHS = 24
CONFIDENCE = 0.05  # 95% CI

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


def calc_metrics(actual: np.ndarray, predicted: np.ndarray) -> Dict:
    """MAE, RMSE, MAPE, R²."""
    mask = actual != 0
    mae = float(np.mean(np.abs(actual - predicted)))
    rmse = float(np.sqrt(np.mean((actual - predicted) ** 2)))
    mape = float(np.mean(np.abs((actual[mask] - predicted[mask]) / actual[mask])) * 100) if mask.any() else None
    ss_res = np.sum((actual - predicted) ** 2)
    ss_tot = np.sum((actual - np.mean(actual)) ** 2)
    r2 = float(1 - ss_res / ss_tot) if ss_tot > 0 else None
    return {
        "mae": round(mae, 2),
        "rmse": round(rmse, 2),
        "mape": round(mape, 2) if mape is not None else None,
        "r2": round(r2, 4) if r2 is not None else None,
    }


def build_lag_features(series: np.ndarray, months: np.ndarray, n_lags: int = 6):
    """Build feature matrix for ML models (RF, XGBoost)."""
    X, y = [], []
    for i in range(n_lags, len(series)):
        row = list(series[i - n_lags : i])  # lag features
        row.append(float(months[i]))        # month-of-year
        row.append(float(i))                # trend index
        X.append(row)
        y.append(series[i])
    return np.array(X), np.array(y)


def future_features(series: np.ndarray, last_month: int, last_index: int, horizon: int, n_lags: int = 6):
    """Iteratively build future feature rows for ML prediction."""
    preds = []
    buf = list(series[-n_lags:])
    idx = last_index + 1
    month = last_month
    for _ in range(horizon):
        month = (month % 12) + 1
        row = list(buf[-n_lags:]) + [float(month), float(idx)]
        preds.append(row)
        idx += 1
    return np.array(preds), preds  # return raw for iterative update


# ---------------------------------------------------------------------------
# Model implementations
# ---------------------------------------------------------------------------

def fit_linear(monthly: pd.DataFrame, horizon: int) -> Optional[Dict]:
    """Simple linear regression."""
    try:
        y = monthly["y"].values
        x = np.arange(len(y))
        n = len(x)
        slope = (n * np.sum(x * y) - np.sum(x) * np.sum(y)) / (n * np.sum(x ** 2) - np.sum(x) ** 2)
        intercept = (np.sum(y) - slope * np.sum(x)) / n

        y_pred = intercept + slope * x
        metrics = calc_metrics(y, y_pred)

        mse = np.mean((y - y_pred) ** 2)
        std_err = np.sqrt(mse) * 1.96

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

        return {
            "nome": "Regressão Linear",
            "r_squared": metrics["r2"],
            "previsoes": preds,
            "metricas": metrics,
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

        fitted = model.fittedvalues
        actual = monthly["y"].values[-len(fitted):]
        metrics = calc_metrics(actual, np.asarray(fitted))

        last_date = monthly["ds"].iloc[-1]
        dates = pd.date_range(start=last_date + pd.DateOffset(months=1), periods=horizon, freq="MS")

        preds = []
        for i, d in enumerate(dates):
            preds.append({
                "data": d.strftime("%Y-%m-%d"),
                "previsto": round(float(pred_mean[i]), 2),
                "ic_inferior": round(float(conf[i, 0]), 2),
                "ic_superior": round(float(conf[i, 1]), 2),
            })

        return {
            "nome": "ARIMA",
            "ordem": list(best_order),
            "previsoes": preds,
            "metricas": metrics,
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

        # Non-seasonal grid
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

        # Seasonal grid (lighter search)
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

        fitted = model.fittedvalues
        actual = monthly["y"].values[-len(fitted):]
        metrics = calc_metrics(actual, np.asarray(fitted))

        last_date = monthly["ds"].iloc[-1]
        dates = pd.date_range(start=last_date + pd.DateOffset(months=1), periods=horizon, freq="MS")

        preds = []
        for i, dt in enumerate(dates):
            preds.append({
                "data": dt.strftime("%Y-%m-%d"),
                "previsto": round(float(pred_mean[i]), 2),
                "ic_inferior": round(float(conf[i, 0]), 2),
                "ic_superior": round(float(conf[i, 1]), 2),
            })

        return {
            "nome": "Auto ARIMA (SARIMA)",
            "ordem": list(best_order),
            "ordem_sazonal": list(best_seasonal),
            "previsoes": preds,
            "metricas": metrics,
        }
    except Exception as e:
        logger.warning(f"  Auto ARIMA failed: {e}")
        return None


def _fit_ml_model(monthly: pd.DataFrame, horizon: int, model_cls, model_name: str, **model_kwargs) -> Optional[Dict]:
    """Generic ML model fitting (Random Forest / XGBoost)."""
    try:
        y_all = monthly["y"].values
        months_all = monthly["ds"].dt.month.values
        n_lags = min(6, len(y_all) - 1)

        if len(y_all) < n_lags + 2:
            return None

        X, y = build_lag_features(y_all, months_all, n_lags)
        model = model_cls(**model_kwargs)
        model.fit(X, y)

        y_pred_train = model.predict(X)
        metrics = calc_metrics(y, y_pred_train)

        # Iterative multi-step forecast
        last_date = monthly["ds"].iloc[-1]
        last_month = int(last_date.month)
        dates = pd.date_range(start=last_date + pd.DateOffset(months=1), periods=horizon, freq="MS")

        buf = list(y_all[-n_lags:])
        preds = []
        residuals = y - y_pred_train
        std_err = float(np.std(residuals)) * 1.96

        idx = len(y_all)
        month = last_month
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

        result = {
            "nome": model_name,
            "previsoes": preds,
            "metricas": metrics,
        }
        return result
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


def fit_prophet_model(monthly: pd.DataFrame, horizon: int) -> Optional[Dict]:
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

        preds = []
        for _, row in future_fc.iterrows():
            preds.append({
                "data": row["ds"].strftime("%Y-%m-%d"),
                "previsto": round(float(row["yhat"]), 2),
                "ic_inferior": round(float(row["yhat_lower"]), 2),
                "ic_superior": round(float(row["yhat_upper"]), 2),
            })

        # In-sample metrics
        in_sample = m.predict(df)
        actual = df["y"].values
        predicted = in_sample["yhat"].values
        metrics = calc_metrics(actual, predicted)

        return {
            "nome": "Prophet",
            "previsoes": preds,
            "metricas": metrics,
        }
    except Exception as e:
        logger.warning(f"  Prophet failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def load_and_prepare() -> pd.DataFrame:
    """Load CSV, return DataFrame with data, produto, preco_medio."""
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    df["data"] = pd.to_datetime(df["data"], errors="coerce")
    df = df.dropna(subset=["data"])
    return df


def get_eligible_products(df: pd.DataFrame) -> List[str]:
    """Products with >= MIN_MONTHS of data."""
    df["ym"] = df["data"].dt.to_period("M")
    counts = df.groupby("produto")["ym"].nunique()
    return sorted(counts[counts >= MIN_MONTHS].index.tolist())


def aggregate_monthly(df: pd.DataFrame) -> pd.DataFrame:
    """Daily -> monthly averages."""
    df = df.copy()
    df["ym"] = df["data"].dt.to_period("M")
    monthly = df.groupby("ym").agg({"preco_medio": "mean"}).reset_index()
    monthly["ds"] = monthly["ym"].dt.to_timestamp()
    monthly["y"] = monthly["preco_medio"]
    return monthly.sort_values("ds").reset_index(drop=True)


def generate_product_forecast(product: str, product_df: pd.DataFrame) -> Dict:
    """Run all models for one product."""
    monthly = aggregate_monthly(product_df)

    if len(monthly) < MIN_MONTHS:
        return {"success": False, "produto": product, "error": f"Dados insuficientes: {len(monthly)} meses"}

    result = {
        "success": False,
        "produto": product,
        "gerado_em": datetime.now().isoformat(),
        "horizonte_meses": HORIZON_MONTHS,
        "meses_historico": len(monthly),
        "historico": [
            {"data": row["ds"].strftime("%Y-%m-%d"), "valor": round(float(row["y"]), 2)}
            for _, row in monthly.tail(HISTORY_MONTHS).iterrows()
        ],
        "modelos": {},
    }

    models = [
        ("linear", fit_linear),
        ("arima", fit_arima),
        ("auto_arima", fit_auto_arima),
        ("random_forest", fit_random_forest),
        ("xgboost", fit_xgboost),
        ("prophet", fit_prophet_model),
    ]

    for key, fn in models:
        logger.info(f"  Fitting {key}...")
        m = fn(monthly, HORIZON_MONTHS)
        if m is not None:
            result["modelos"][key] = m

    result["success"] = len(result["modelos"]) > 0
    if not result["success"]:
        result["error"] = "Nenhum modelo conseguiu gerar previsões"

    return result


def main():
    logger.info("=== Generating forecasts ===")
    logger.info(f"CSV: {CSV_PATH}")

    if not CSV_PATH.exists():
        logger.error(f"File not found: {CSV_PATH}")
        return

    df = load_and_prepare()
    products = get_eligible_products(df)
    logger.info(f"Eligible products: {len(products)}")

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
            product_list.append({"produto": product, "slug": slug, "modelos": models_ok})
            logger.info(f"  OK — models: {models_ok}")
        else:
            logger.warning(f"  FAILED — {result.get('error')}")

    # Write products index
    index = {
        "gerado_em": datetime.now().isoformat(),
        "total": len(product_list),
        "produtos": product_list,
    }
    with open(PRODUCTS_JSON, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    logger.info(f"=== Done: {success_count}/{len(products)} products forecasted ===")
    logger.info(f"Output: {OUTPUT_DIR}")
    logger.info(f"Index: {PRODUCTS_JSON}")


if __name__ == "__main__":
    main()
