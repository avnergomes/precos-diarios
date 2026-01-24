#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Price Forecasting Module
Implements ARIMA and Prophet models for agricultural price prediction.
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


class PriceForecaster:
    """
    Time series forecasting for agricultural prices.
    Supports ARIMA and Prophet models.
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

            df = pd.read_csv(csv_path)

            # Filter for product
            product_data = df[df['produto'] == self.product].copy()
            if product_data.empty:
                logger.warning(f"No data found for product: {self.product}")
                return False

            # Convert date and sort
            product_data['data'] = pd.to_datetime(product_data['data'])
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
            'preco_minimo': 'min',
            'preco_maximo': 'max',
            'num_cotacoes': 'sum'
        }).reset_index()

        monthly['ds'] = monthly['year_month'].dt.to_timestamp()
        monthly['y'] = monthly['preco_medio']

        return monthly.sort_values('ds')

    def fit_arima(self) -> Dict:
        """
        Fit ARIMA model to the data.
        Uses auto-selection of parameters (p, d, q).
        """
        try:
            from statsmodels.tsa.arima.model import ARIMA
            from statsmodels.tsa.stattools import adfuller

            if self.monthly_data is None or len(self.monthly_data) < 12:
                return {'success': False, 'error': 'Insufficient data for ARIMA'}

            series = self.monthly_data['y'].values

            # Test for stationarity
            adf_result = adfuller(series, autolag='AIC')
            d = 0 if adf_result[1] < 0.05 else 1

            # Simple parameter selection
            best_aic = float('inf')
            best_order = (1, d, 1)

            for p in range(0, 4):
                for q in range(0, 4):
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

        except Exception as e:
            logger.error(f"ARIMA fitting error: {e}")
            return {'success': False, 'error': str(e)}

    def fit_prophet(self) -> Dict:
        """
        Fit Facebook Prophet model to the data.
        """
        try:
            from prophet import Prophet

            if self.monthly_data is None or len(self.monthly_data) < 12:
                return {'success': False, 'error': 'Insufficient data for Prophet'}

            # Prepare data for Prophet
            prophet_df = self.monthly_data[['ds', 'y']].copy()

            # Fit model
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

    def predict_arima(self, horizon: int = 30) -> Dict:
        """
        Generate ARIMA predictions.

        Args:
            horizon: Number of days to forecast

        Returns:
            Dictionary with predictions and confidence intervals
        """
        try:
            if self.arima_model is None:
                return {'success': False, 'error': 'ARIMA model not fitted'}

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
                    'previsto': float(pred_mean.iloc[i]),
                    'ic_inferior': float(conf_int.iloc[i, 0]),
                    'ic_superior': float(conf_int.iloc[i, 1]),
                })

            # Calculate metrics on historical data
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
        """
        Generate Prophet predictions.

        Args:
            horizon: Number of days to forecast

        Returns:
            Dictionary with predictions and confidence intervals
        """
        try:
            if self.prophet_model is None:
                return {'success': False, 'error': 'Prophet model not fitted'}

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
                    'previsto': float(row['yhat']),
                    'ic_inferior': float(row['yhat_lower']),
                    'ic_superior': float(row['yhat_upper']),
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
        """Calculate Prophet model metrics using cross-validation."""
        try:
            # Simple in-sample prediction
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

    def get_historical_data(self, months: int = 12) -> List[Dict]:
        """Get historical monthly data for charting."""
        if self.monthly_data is None:
            return []

        recent = self.monthly_data.tail(months)
        return [
            {
                'data': row['ds'].strftime('%Y-%m-%d'),
                'valor': float(row['y']),
            }
            for _, row in recent.iterrows()
        ]


def get_available_products() -> List[str]:
    """Get list of products available for forecasting."""
    try:
        csv_path = PROCESSED_DIR / "consolidated.csv"
        if not csv_path.exists():
            return []

        df = pd.read_csv(csv_path)
        products = df['produto'].unique().tolist()
        return sorted(products)
    except:
        return []


def generate_forecast(product: str, horizon: int = 30) -> Dict:
    """
    Generate complete forecast for a product using both models.

    Args:
        product: Product name
        horizon: Forecast horizon in days

    Returns:
        Complete forecast dictionary with both models
    """
    forecaster = PriceForecaster(product)

    if not forecaster.load_data():
        return {
            'success': False,
            'error': f'Could not load data for product: {product}'
        }

    result = {
        'produto': product,
        'gerado_em': datetime.now().isoformat(),
        'horizonte_dias': horizon,
        'historico': forecaster.get_historical_data(24),
        'modelos': {},
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

    # Prophet
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
    return result


if __name__ == '__main__':
    # Test forecasting
    logging.basicConfig(level=logging.INFO)

    products = get_available_products()
    print(f"Available products: {products[:5]}...")

    if products:
        result = generate_forecast(products[0], horizon=90)
        print(f"\nForecast for {products[0]}:")
        print(f"Success: {result.get('success')}")
        print(f"Models: {list(result.get('modelos', {}).keys())}")

        if 'arima' in result.get('modelos', {}):
            print(f"ARIMA metrics: {result['modelos']['arima']['metricas']}")
        if 'prophet' in result.get('modelos', {}):
            print(f"Prophet metrics: {result['modelos']['prophet']['metricas']}")
