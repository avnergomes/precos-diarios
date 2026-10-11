#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Price Forecasting Module
Implements ARIMA and Prophet models for agricultural price prediction.
With fallback to simple linear regression when ML models fail.

Shared utilities (RECENCY_MONTHS, calc_metrics, sanitize_for_json) are imported
by scripts/generate_forecasts.py to avoid metric-logic duplication.
"""

import logging
import math
import os
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

# Check if Prophet is available (heavy dependency, not on Render free tier)
try:
    import prophet  # noqa: F401
    HAS_PROPHET = True
except ImportError:
    HAS_PROPHET = False
    logger.info("Prophet not installed - using ARIMA and Linear models only")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"

# Minimum months required for forecasting
MIN_MONTHS_REQUIRED = 6

# Products with last data point older than this many months are excluded.
RECENCY_MONTHS = 3

# ---------------------------------------------------------------------------
# Shared utilities (also imported by generate_forecasts.py)
# ---------------------------------------------------------------------------

def calc_metrics(actual: np.ndarray, predicted: np.ndarray) -> Dict:
    """MAE, RMSE, MAPE, R² — all out-of-sample safe; zero-division guarded."""
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    mask = actual != 0
    mae = float(np.mean(np.abs(actual - predicted)))
    rmse = float(np.sqrt(np.mean((actual - predicted) ** 2)))
    mape = (
        float(np.mean(np.abs((actual[mask] - predicted[mask]) / actual[mask])) * 100)
        if mask.any()
        else None
    )
    ss_res = float(np.sum((actual - predicted) ** 2))
    ss_tot = float(np.sum((actual - np.mean(actual)) ** 2))
    r2 = float(1 - ss_res / ss_tot) if ss_tot > 0 else None
    return {
        "mae": round(mae, 2),
        "rmse": round(rmse, 2),
        "mape": round(mape, 2) if mape is not None else None,
        "r2": round(r2, 4) if r2 is not None else None,
    }


def sanitize_for_json(obj):
    """Recursively replace NaN/Infinity with None so json.dumps never raises."""
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_for_json(v) for v in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    return obj


# ---------------------------------------------------------------------------
# CSV cache (avoid re-reading on every API request)
# ---------------------------------------------------------------------------
_csv_cache: Dict = {"mtime": None, "df": None}


def _load_csv_cached(csv_path: Path) -> Optional[pd.DataFrame]:
    """Return the consolidated CSV, re-reading only when the file changes."""
    try:
        mtime = csv_path.stat().st_mtime
    except OSError:
        return None
    if _csv_cache["mtime"] != mtime or _csv_cache["df"] is None:
        df = pd.read_csv(csv_path, encoding='utf-8-sig')
        df['data'] = pd.to_datetime(df['data'], errors='coerce')
        df = df.dropna(subset=['data'])
        # Defensive dedup by (data, produto, unidade)
        dedup_cols = [c for c in ['data', 'produto', 'unidade'] if c in df.columns]
        if dedup_cols:
            df = df.groupby(dedup_cols, as_index=False)['preco_medio'].mean()
        _csv_cache.update({"mtime": mtime, "df": df})
    return _csv_cache["df"]


# ---------------------------------------------------------------------------
# PriceForecaster class (API endpoint use)
# ---------------------------------------------------------------------------

class PriceForecaster:
    """
    Time series forecasting for agricultural prices.
    Supports ARIMA, Prophet, and simple linear regression models.
    """

    def __init__(self, product: str):
        self.product = product
        self.data = None
        self.monthly_data = None
        self.arima_model = None
        self.prophet_model = None

    def load_data(self) -> bool:
        """Load and prepare data for the specified product."""
        try:
            csv_path = PROCESSED_DIR / "consolidated.csv"
            df = _load_csv_cached(csv_path)
            if df is None:
                logger.error(f"Data file not found: {csv_path}")
                return False

            product_data = df[df['produto'] == self.product].copy()

            if product_data.empty:
                for prod in df['produto'].unique():
                    if self.product.lower() in prod.lower() or prod.lower() in self.product.lower():
                        product_data = df[df['produto'] == prod].copy()
                        self.product = prod
                        break

            if product_data.empty:
                logger.warning(f"No data found for product: {self.product}")
                return False

            product_data = product_data.sort_values('data')
            self.data = product_data
            self.monthly_data = self._aggregate_monthly(product_data)

            logger.info(f"Loaded {len(self.monthly_data)} months of data for {self.product}")
            return True

        except Exception as e:
            logger.error(f"Error loading data: {e}")
            return False

    def _aggregate_monthly(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aggregate daily data to monthly averages, drop current partial month."""
        df = df.copy()
        df['year_month'] = df['data'].dt.to_period('M')
        # Drop current partial month
        current_period = pd.Timestamp.now().to_period('M')
        df = df[df['year_month'] < current_period]

        monthly = df.groupby('year_month').agg({'preco_medio': 'mean'}).reset_index()
        monthly['ds'] = monthly['year_month'].dt.to_timestamp()
        monthly['y'] = monthly['preco_medio']
        return monthly.sort_values('ds').reset_index(drop=True)

    def has_sufficient_data(self) -> bool:
        """Check if there's enough data for forecasting."""
        if self.monthly_data is None:
            return False
        return len(self.monthly_data) >= MIN_MONTHS_REQUIRED

    def fit_arima(self) -> Dict:
        """Fit ARIMA model to the data (auto p,d,q)."""
        try:
            from statsmodels.tsa.arima.model import ARIMA
            from statsmodels.tsa.stattools import adfuller

            if not self.has_sufficient_data():
                return {'success': False, 'error': f'Dados insuficientes (mínimo {MIN_MONTHS_REQUIRED} meses)'}

            series = self.monthly_data.set_index('ds')['y']

            try:
                d = 0 if adfuller(series, autolag='AIC')[1] < 0.05 else 1
            except Exception:
                d = 1

            best_aic = float('inf')
            best_order = (1, d, 1)

            for p in range(0, 3):
                for q in range(0, 3):
                    try:
                        model = ARIMA(series, order=(p, d, q))
                        fitted = model.fit()
                        if fitted.aic < best_aic:
                            best_aic = fitted.aic
                            best_order = (p, d, q)
                    except Exception:
                        continue

            self.arima_model = ARIMA(series, order=best_order).fit()

            return {
                'success': True,
                'order': best_order,
                'aic': self.arima_model.aic,
            }

        except ImportError:
            logger.error("statsmodels not installed")
            return {'success': False, 'error': 'statsmodels não instalado'}
        except Exception as e:
            logger.error(f"ARIMA fitting error: {e}")
            return {'success': False, 'error': str(e)}

    def fit_prophet(self) -> Dict:
        """Fit Facebook Prophet model. No-op if Prophet is not installed."""
        if not HAS_PROPHET:
            return {'success': False, 'error': 'Prophet não instalado'}
        try:
            from prophet import Prophet

            if not self.has_sufficient_data():
                return {'success': False, 'error': f'Dados insuficientes (mínimo {MIN_MONTHS_REQUIRED} meses)'}

            prophet_df = self.monthly_data[['ds', 'y']].copy()

            import logging as lg
            lg.getLogger('prophet').setLevel(lg.WARNING)
            lg.getLogger('cmdstanpy').setLevel(lg.WARNING)

            self.prophet_model = Prophet(
                yearly_seasonality=True,
                weekly_seasonality=False,
                daily_seasonality=False,
                changepoint_prior_scale=0.05,
            )
            self.prophet_model.fit(prophet_df)

            return {'success': True}

        except Exception as e:
            logger.error(f"Prophet fitting error: {e}")
            return {'success': False, 'error': str(e)}

    def fit_linear(self) -> Dict:
        """Fit simple linear regression as fallback model."""
        try:
            if not self.has_sufficient_data():
                return {'success': False, 'error': f'Dados insuficientes (mínimo {MIN_MONTHS_REQUIRED} meses)'}

            y = self.monthly_data['y'].values
            x = np.arange(len(y))
            n = len(x)
            slope = (n * np.sum(x * y) - np.sum(x) * np.sum(y)) / (n * np.sum(x ** 2) - np.sum(x) ** 2)
            intercept = (np.sum(y) - slope * np.sum(x)) / n

            self.linear_slope = slope
            self.linear_intercept = intercept

            y_pred = intercept + slope * x
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r_squared = float(1 - ss_res / ss_tot) if ss_tot > 0 else 0.0

            return {
                'success': True,
                'slope': float(slope),
                'intercept': float(intercept),
                'r_squared': r_squared,
            }

        except Exception as e:
            logger.error(f"Linear fitting error: {e}")
            return {'success': False, 'error': str(e)}

    def predict_arima(self, horizon: int = 30) -> Dict:
        """Generate ARIMA predictions."""
        try:
            if self.arima_model is None:
                return {'success': False, 'error': 'Modelo ARIMA não ajustado'}

            months = max(1, horizon // 30)
            forecast = self.arima_model.get_forecast(steps=months)
            pred_mean = np.asarray(forecast.predicted_mean)
            conf_int = np.asarray(forecast.conf_int(alpha=0.05))

            last_date = self.monthly_data['ds'].iloc[-1]
            dates = pd.date_range(
                start=last_date + pd.DateOffset(months=1),
                periods=months,
                freq='MS'
            )

            predictions = []
            for i, date in enumerate(dates):
                predictions.append({
                    'data': date.strftime('%Y-%m-%d'),
                    'previsto': round(float(pred_mean[i]), 2),
                    'ic_inferior': round(float(conf_int[i, 0]), 2),
                    'ic_superior': round(float(conf_int[i, 1]), 2),
                })

            metrics = self._calculate_metrics_arima()

            return {
                'success': True,
                'previsoes': predictions,
                'metricas': metrics,
            }

        except Exception as e:
            logger.error(f"ARIMA prediction error: {e}")
            return {'success': False, 'error': str(e)}

    def predict_prophet(self, horizon: int = 30) -> Dict:
        """Generate Prophet predictions."""
        try:
            if self.prophet_model is None:
                return {'success': False, 'error': 'Modelo Prophet não ajustado'}

            months = max(1, horizon // 30)
            future = self.prophet_model.make_future_dataframe(periods=months, freq='MS')
            forecast = self.prophet_model.predict(future)

            last_date = self.monthly_data['ds'].iloc[-1]
            future_forecast = forecast[forecast['ds'] > last_date]

            predictions = []
            for _, row in future_forecast.iterrows():
                predictions.append({
                    'data': row['ds'].strftime('%Y-%m-%d'),
                    'previsto': round(float(row['yhat']), 2),
                    'ic_inferior': round(float(row['yhat_lower']), 2),
                    'ic_superior': round(float(row['yhat_upper']), 2),
                })

            metrics = self._calculate_metrics_prophet()

            return {
                'success': True,
                'previsoes': predictions,
                'metricas': metrics,
            }

        except Exception as e:
            logger.error(f"Prophet prediction error: {e}")
            return {'success': False, 'error': str(e)}

    def predict_linear(self, horizon: int = 30) -> Dict:
        """Generate linear regression predictions (fallback)."""
        try:
            if not hasattr(self, 'linear_slope'):
                return {'success': False, 'error': 'Modelo linear não ajustado'}

            months = max(1, horizon // 30)
            n = len(self.monthly_data)

            last_date = self.monthly_data['ds'].iloc[-1]
            dates = pd.date_range(
                start=last_date + pd.DateOffset(months=1),
                periods=months,
                freq='MS'
            )

            y = self.monthly_data['y'].values
            x = np.arange(len(y))
            y_pred = self.linear_intercept + self.linear_slope * x
            mse = np.mean((y - y_pred) ** 2)
            std_error = np.sqrt(mse) * 1.96

            predictions = []
            for i, date in enumerate(dates):
                x_future = n + i
                pred = self.linear_intercept + self.linear_slope * x_future
                predictions.append({
                    'data': date.strftime('%Y-%m-%d'),
                    'previsto': round(float(pred), 2),
                    'ic_inferior': round(float(pred - std_error), 2),
                    'ic_superior': round(float(pred + std_error), 2),
                })

            metrics = calc_metrics(y, y_pred)

            return {
                'success': True,
                'previsoes': predictions,
                'metricas': metrics,
            }

        except Exception as e:
            logger.error(f"Linear prediction error: {e}")
            return {'success': False, 'error': str(e)}

    def _calculate_metrics_arima(self) -> Dict:
        """ARIMA in-sample metrics (used by API endpoint only)."""
        try:
            fitted_values = np.asarray(self.arima_model.fittedvalues)
            actual = self.monthly_data['y'].values[-len(fitted_values):]
            return calc_metrics(actual, fitted_values)
        except Exception:
            return {'mae': None, 'rmse': None, 'mape': None, 'r2': None}

    def _calculate_metrics_prophet(self) -> Dict:
        """Prophet in-sample metrics (used by API endpoint only)."""
        try:
            df = self.monthly_data[['ds', 'y']].copy()
            forecast = self.prophet_model.predict(df)
            actual = df['y'].values
            predicted = forecast['yhat'].values
            return calc_metrics(actual, predicted)
        except Exception:
            return {'mae': None, 'rmse': None, 'mape': None, 'r2': None}

    def get_historical_data(self, months: int = 24) -> List[Dict]:
        """Get historical monthly data for charting."""
        if self.monthly_data is None:
            return []

        recent = self.monthly_data.tail(months)
        return [
            {
                'data': row['ds'].strftime('%Y-%m-%d'),
                'valor': round(float(row['y']), 2),
            }
            for _, row in recent.iterrows()
        ]


def get_available_products() -> List[str]:
    """Get list of products available for forecasting (with sufficient data)."""
    try:
        csv_path = PROCESSED_DIR / "consolidated.csv"
        df = _load_csv_cached(csv_path)
        if df is None:
            return []

        df['year_month'] = df['data'].dt.to_period('M')
        product_months = df.groupby('produto')['year_month'].nunique()
        valid_products = product_months[product_months >= MIN_MONTHS_REQUIRED].index.tolist()

        return sorted(valid_products)
    except Exception as e:
        logger.error(f"Error getting products: {e}")
        return []


def generate_forecast(product: str, horizon: int = 30) -> Dict:
    """
    Generate complete forecast for a product using available models.

    Args:
        product: Product name
        horizon: Forecast horizon in days

    Returns:
        Complete forecast dictionary with available models
    """
    forecaster = PriceForecaster(product)

    if not forecaster.load_data():
        return {
            'success': False,
            'error': f'Produto não encontrado: {product}',
            'produto': product,
        }

    if not forecaster.has_sufficient_data():
        months_available = len(forecaster.monthly_data) if forecaster.monthly_data is not None else 0
        return {
            'success': False,
            'error': f'Dados insuficientes: {months_available} meses (mínimo {MIN_MONTHS_REQUIRED})',
            'produto': product,
        }

    result = {
        'success': False,
        'produto': product,
        'gerado_em': datetime.now(timezone.utc).isoformat(),
        'horizonte_dias': horizon,
        'meses_historico': len(forecaster.monthly_data),
        'historico': forecaster.get_historical_data(24),
        'modelos': {},
    }

    # Linear regression (always attempted)
    linear_fit = forecaster.fit_linear()
    if linear_fit.get('success'):
        linear_pred = forecaster.predict_linear(horizon)
        if linear_pred.get('success'):
            result['modelos']['linear'] = {
                'nome': 'Regressão Linear',
                'r_squared': round(linear_fit.get('r_squared', 0), 4),
                'previsoes': linear_pred['previsoes'],
                'metricas': linear_pred['metricas'],
            }

    # ARIMA
    arima_fit = forecaster.fit_arima()
    if arima_fit.get('success'):
        arima_pred = forecaster.predict_arima(horizon)
        if arima_pred.get('success'):
            result['modelos']['arima'] = {
                'nome': 'ARIMA',
                'ordem': arima_fit.get('order'),
                'previsoes': arima_pred['previsoes'],
                'metricas': arima_pred['metricas'],
            }

    # Prophet — optional, silent if not installed
    if HAS_PROPHET:
        prophet_fit = forecaster.fit_prophet()
        if prophet_fit.get('success'):
            prophet_pred = forecaster.predict_prophet(horizon)
            if prophet_pred.get('success'):
                result['modelos']['prophet'] = {
                    'nome': 'Prophet',
                    'previsoes': prophet_pred['previsoes'],
                    'metricas': prophet_pred['metricas'],
                }

    result['success'] = len(result['modelos']) > 0

    if not result['success']:
        result['error'] = 'Nenhum modelo conseguiu gerar previsões'

    return sanitize_for_json(result)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    products = get_available_products()
    print(f"Available products ({len(products)}): {products[:5]}...")

    if products:
        test_product = products[0]
        print(f"\nTesting forecast for: {test_product}")
        result = generate_forecast(test_product, horizon=90)
        print(f"Success: {result.get('success')}")
        print(f"Error: {result.get('error', 'None')}")
        print(f"Models: {list(result.get('modelos', {}).keys())}")

        for model_name, model_data in result.get('modelos', {}).items():
            print(f"  {model_name} metrics: {model_data.get('metricas')}")
