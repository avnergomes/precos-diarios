#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Price Forecasting Module
Implements ARIMA and Prophet models for agricultural price prediction.
With fallback to simple linear regression when ML models fail.
"""

import logging
import warnings
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

# Configuration
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"

# Minimum months required for forecasting
MIN_MONTHS_REQUIRED = 6


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
            if not csv_path.exists():
                logger.error(f"Data file not found: {csv_path}")
                return False

            # Read with proper encoding
            df = pd.read_csv(csv_path, encoding='utf-8-sig')

            # Filter for product (handle encoding variations)
            product_data = df[df['produto'] == self.product].copy()

            if product_data.empty:
                # Try matching without encoding issues
                for prod in df['produto'].unique():
                    if self.product.lower() in prod.lower() or prod.lower() in self.product.lower():
                        product_data = df[df['produto'] == prod].copy()
                        self.product = prod  # Update to matched name
                        break

            if product_data.empty:
                logger.warning(f"No data found for product: {self.product}")
                return False

            # Convert date and sort
            product_data['data'] = pd.to_datetime(product_data['data'], errors='coerce')
            product_data = product_data.dropna(subset=['data'])
            product_data = product_data.sort_values('data')

            self.data = product_data

            # Aggregate to monthly data (required for forecasting)
            self.monthly_data = self._aggregate_monthly(product_data)

            logger.info(f"Loaded {len(self.monthly_data)} months of data for {self.product}")
            return True

        except Exception as e:
            logger.error(f"Error loading data: {e}")
            return False

    def _aggregate_monthly(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aggregate daily data to monthly averages."""
        df = df.copy()
        df['year_month'] = df['data'].dt.to_period('M')

        monthly = df.groupby('year_month').agg({
            'preco_medio': 'mean',
        }).reset_index()

        monthly['ds'] = monthly['year_month'].dt.to_timestamp()
        monthly['y'] = monthly['preco_medio']

        return monthly.sort_values('ds')

    def has_sufficient_data(self) -> bool:
        """Check if there's enough data for forecasting."""
        if self.monthly_data is None:
            return False
        return len(self.monthly_data) >= MIN_MONTHS_REQUIRED

    def fit_arima(self) -> Dict:
        """
        Fit ARIMA model to the data.
        Uses auto-selection of parameters (p, d, q).
        """
        try:
            from statsmodels.tsa.arima.model import ARIMA
            from statsmodels.tsa.stattools import adfuller

            if not self.has_sufficient_data():
                return {'success': False, 'error': f'Dados insuficientes (mínimo {MIN_MONTHS_REQUIRED} meses)'}

            series = self.monthly_data['y'].values

            # Test for stationarity
            try:
                adf_result = adfuller(series, autolag='AIC')
                d = 0 if adf_result[1] < 0.05 else 1
            except:
                d = 1

            # Simple parameter selection
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
                    except:
                        continue

            # Fit final model
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
        """
        Fit Facebook Prophet model to the data.
        """
        try:
            from prophet import Prophet

            if not self.has_sufficient_data():
                return {'success': False, 'error': f'Dados insuficientes (mínimo {MIN_MONTHS_REQUIRED} meses)'}

            # Prepare data for Prophet
            prophet_df = self.monthly_data[['ds', 'y']].copy()

            # Fit model with suppressed logging
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

        except ImportError:
            logger.error("prophet not installed")
            return {'success': False, 'error': 'Prophet não instalado'}
        except Exception as e:
            logger.error(f"Prophet fitting error: {e}")
            return {'success': False, 'error': str(e)}

    def fit_linear(self) -> Dict:
        """
        Fit simple linear regression as fallback model.
        """
        try:
            if not self.has_sufficient_data():
                return {'success': False, 'error': f'Dados insuficientes (mínimo {MIN_MONTHS_REQUIRED} meses)'}

            # Simple linear regression using numpy
            y = self.monthly_data['y'].values
            x = np.arange(len(y))

            # Calculate slope and intercept
            n = len(x)
            sum_x = np.sum(x)
            sum_y = np.sum(y)
            sum_xy = np.sum(x * y)
            sum_x2 = np.sum(x ** 2)

            self.linear_slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
            self.linear_intercept = (sum_y - self.linear_slope * sum_x) / n

            # Calculate R²
            y_pred = self.linear_intercept + self.linear_slope * x
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

            return {
                'success': True,
                'slope': self.linear_slope,
                'intercept': self.linear_intercept,
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

            # Convert days to months
            months = max(1, horizon // 30)

            # Forecast
            forecast = self.arima_model.get_forecast(steps=months)
            pred_mean = forecast.predicted_mean
            conf_int = forecast.conf_int(alpha=0.05)

            # Generate dates
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
                    'previsto': round(float(pred_mean.iloc[i]), 2),
                    'ic_inferior': round(float(conf_int.iloc[i, 0]), 2),
                    'ic_superior': round(float(conf_int.iloc[i, 1]), 2),
                })

            # Calculate metrics
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

            # Convert days to months
            months = max(1, horizon // 30)

            # Create future dataframe
            future = self.prophet_model.make_future_dataframe(periods=months, freq='MS')
            forecast = self.prophet_model.predict(future)

            # Get only future predictions
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

            # Calculate metrics
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

            # Convert days to months
            months = max(1, horizon // 30)
            n = len(self.monthly_data)

            # Generate dates
            last_date = self.monthly_data['ds'].iloc[-1]
            dates = pd.date_range(
                start=last_date + pd.DateOffset(months=1),
                periods=months,
                freq='MS'
            )

            # Calculate standard error for confidence interval
            y = self.monthly_data['y'].values
            x = np.arange(len(y))
            y_pred = self.linear_intercept + self.linear_slope * x
            mse = np.mean((y - y_pred) ** 2)
            std_error = np.sqrt(mse) * 1.96  # 95% CI

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

            # Calculate metrics
            mae = np.mean(np.abs(y - y_pred))
            rmse = np.sqrt(mse)
            mape = np.mean(np.abs((y - y_pred) / y)) * 100

            return {
                'success': True,
                'previsoes': predictions,
                'metricas': {
                    'mae': round(mae, 2),
                    'rmse': round(rmse, 2),
                    'mape': round(mape, 2),
                },
            }

        except Exception as e:
            logger.error(f"Linear prediction error: {e}")
            return {'success': False, 'error': str(e)}

    def _calculate_metrics_arima(self) -> Dict:
        """Calculate ARIMA model metrics using in-sample predictions."""
        try:
            fitted_values = self.arima_model.fittedvalues
            actual = self.monthly_data['y'].values[-len(fitted_values):]

            mae = np.mean(np.abs(actual - fitted_values))
            rmse = np.sqrt(np.mean((actual - fitted_values) ** 2))
            mape = np.mean(np.abs((actual - fitted_values) / actual)) * 100

            return {
                'mae': round(mae, 2),
                'rmse': round(rmse, 2),
                'mape': round(mape, 2),
            }
        except:
            return {'mae': None, 'rmse': None, 'mape': None}

    def _calculate_metrics_prophet(self) -> Dict:
        """Calculate Prophet model metrics using in-sample predictions."""
        try:
            df = self.monthly_data[['ds', 'y']].copy()
            forecast = self.prophet_model.predict(df)

            actual = df['y'].values
            predicted = forecast['yhat'].values

            mae = np.mean(np.abs(actual - predicted))
            rmse = np.sqrt(np.mean((actual - predicted) ** 2))
            mape = np.mean(np.abs((actual - predicted) / actual)) * 100

            return {
                'mae': round(mae, 2),
                'rmse': round(rmse, 2),
                'mape': round(mape, 2),
            }
        except:
            return {'mae': None, 'rmse': None, 'mape': None}

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
        if not csv_path.exists():
            return []

        df = pd.read_csv(csv_path, encoding='utf-8-sig')
        df['data'] = pd.to_datetime(df['data'], errors='coerce')
        df = df.dropna(subset=['data'])
        df['year_month'] = df['data'].dt.to_period('M')

        # Only return products with sufficient data
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
        'gerado_em': datetime.now().isoformat(),
        'horizonte_dias': horizon,
        'meses_historico': len(forecaster.monthly_data),
        'historico': forecaster.get_historical_data(24),
        'modelos': {},
    }

    # Try ARIMA first
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

    # Try Prophet
    prophet_fit = forecaster.fit_prophet()
    if prophet_fit.get('success'):
        prophet_pred = forecaster.predict_prophet(horizon)
        if prophet_pred.get('success'):
            result['modelos']['prophet'] = {
                'nome': 'Prophet',
                'previsoes': prophet_pred['previsoes'],
                'metricas': prophet_pred['metricas'],
            }

    # Fallback to linear regression if no models succeeded
    if not result['modelos']:
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

    result['success'] = len(result['modelos']) > 0

    if not result['success']:
        result['error'] = 'Nenhum modelo conseguiu gerar previsões'

    return result


if __name__ == '__main__':
    # Test forecasting
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
