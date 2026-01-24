import { TrendingUp, TrendingDown, Target, Activity } from 'lucide-react'
import { formatCurrency } from '../utils/format'

/**
 * ForecastKpis - Display comparison metrics for ARIMA and Prophet models
 */
export default function ForecastKpis({ modelos = {}, historico = [], horizon = 30 }) {
  const arima = modelos.arima
  const prophet = modelos.prophet

  // Get current price (last historical value)
  const currentPrice = historico.length > 0 ? historico[historico.length - 1].valor : 0

  // Get first forecast value for each model
  const arimaForecast = arima?.previsoes?.[0]?.previsto || 0
  const prophetForecast = prophet?.previsoes?.[0]?.previsto || 0

  // Calculate variations
  const arimaVariation = currentPrice > 0 ? ((arimaForecast - currentPrice) / currentPrice) * 100 : 0
  const prophetVariation = currentPrice > 0 ? ((prophetForecast - currentPrice) / currentPrice) * 100 : 0

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {/* ARIMA Model Card */}
      {arima && (
        <div className="card p-5">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-100 rounded-lg">
                <Activity className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <h4 className="font-semibold text-dark-800">ARIMA</h4>
                <p className="text-xs text-dark-400">
                  Ordem: ({arima.ordem?.join(', ') || 'N/A'})
                </p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            {/* Forecast Price */}
            <div>
              <p className="text-xs text-dark-500 mb-1">Previsão {horizon}d</p>
              <p className="text-xl font-bold text-blue-600">
                {formatCurrency(arimaForecast)}
              </p>
              <p className={`text-sm flex items-center gap-1 ${arimaVariation >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {arimaVariation >= 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                {arimaVariation >= 0 ? '+' : ''}{arimaVariation.toFixed(1)}%
              </p>
            </div>

            {/* Metrics */}
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-dark-500">MAE:</span>
                <span className="font-medium">{arima.metricas?.mae?.toFixed(2) || '-'}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-dark-500">RMSE:</span>
                <span className="font-medium">{arima.metricas?.rmse?.toFixed(2) || '-'}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-dark-500">MAPE:</span>
                <span className="font-medium">{arima.metricas?.mape?.toFixed(1) || '-'}%</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Prophet Model Card */}
      {prophet && (
        <div className="card p-5">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-green-100 rounded-lg">
                <Target className="w-5 h-5 text-green-600" />
              </div>
              <div>
                <h4 className="font-semibold text-dark-800">Prophet</h4>
                <p className="text-xs text-dark-400">Facebook/Meta</p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            {/* Forecast Price */}
            <div>
              <p className="text-xs text-dark-500 mb-1">Previsão {horizon}d</p>
              <p className="text-xl font-bold text-green-600">
                {formatCurrency(prophetForecast)}
              </p>
              <p className={`text-sm flex items-center gap-1 ${prophetVariation >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {prophetVariation >= 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                {prophetVariation >= 0 ? '+' : ''}{prophetVariation.toFixed(1)}%
              </p>
            </div>

            {/* Metrics */}
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-dark-500">MAE:</span>
                <span className="font-medium">{prophet.metricas?.mae?.toFixed(2) || '-'}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-dark-500">RMSE:</span>
                <span className="font-medium">{prophet.metricas?.rmse?.toFixed(2) || '-'}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-dark-500">MAPE:</span>
                <span className="font-medium">{prophet.metricas?.mape?.toFixed(1) || '-'}%</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* No models available */}
      {!arima && !prophet && (
        <div className="col-span-2 card p-6 text-center text-dark-400">
          Nenhum modelo de previsão disponível
        </div>
      )}
    </div>
  )
}
