import { TrendingUp, TrendingDown } from 'lucide-react'
import { formatCurrency } from '../utils/format'

// Same palette as ForecastChart
const MODEL_META = {
  linear:        { color: '#8b5cf6', bg: 'bg-purple-100', text: 'text-purple-600', label: 'Regressão Linear' },
  arima:         { color: '#3b82f6', bg: 'bg-blue-100',   text: 'text-blue-600',   label: 'ARIMA' },
  auto_arima:    { color: '#06b6d4', bg: 'bg-cyan-100',   text: 'text-cyan-600',   label: 'Auto ARIMA' },
  random_forest: { color: '#f97316', bg: 'bg-orange-100', text: 'text-orange-600',  label: 'Random Forest' },
  xgboost:       { color: '#ef4444', bg: 'bg-red-100',    text: 'text-red-600',    label: 'XGBoost' },
  prophet:       { color: '#22c55e', bg: 'bg-green-100',  text: 'text-green-600',  label: 'Prophet' },
}

function getMeta(key) {
  return MODEL_META[key] || { color: '#6366f1', bg: 'bg-indigo-100', text: 'text-indigo-600', label: key }
}

function formatSubtitle(key, model) {
  const parts = []
  if (model.ordem) parts.push(`Ordem: (${model.ordem.join(', ')})`)
  if (model.ordem_sazonal) parts.push(`Sazonal: (${model.ordem_sazonal.join(', ')})`)
  if (model.r_squared != null) parts.push(`R²: ${model.r_squared.toFixed(4)}`)
  if (key === 'prophet') parts.push('Meta/Facebook')
  if (key === 'random_forest') parts.push('Ensemble')
  if (key === 'xgboost') parts.push('Gradient Boosting')
  return parts.join(' · ') || null
}

export default function ForecastKpis({ modelos = {}, historico = [], horizon = 30 }) {
  const modelKeys = Object.keys(modelos)
  const currentPrice = historico.length > 0 ? historico[historico.length - 1].valor : 0

  if (modelKeys.length === 0) {
    return (
      <div className="card p-6 text-center text-dark-400">
        Nenhum modelo de previsão disponível
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {modelKeys.map(key => {
        const model = modelos[key]
        const meta = getMeta(key)
        const forecast = model.previsoes?.[0]?.previsto || 0
        const variation = currentPrice > 0 ? ((forecast - currentPrice) / currentPrice) * 100 : 0
        const subtitle = formatSubtitle(key, model)
        const metrics = model.metricas || {}

        return (
          <div key={key} className="card p-5">
            {/* Header */}
            <div className="flex items-center gap-3 mb-4">
              <div className={`w-3 h-8 rounded-full`} style={{ backgroundColor: meta.color }} />
              <div>
                <h4 className="font-semibold text-dark-800">{model.nome || meta.label}</h4>
                {subtitle && <p className="text-xs text-dark-400">{subtitle}</p>}
              </div>
            </div>

            {/* Forecast value + variation */}
            <div className="mb-4">
              <p className="text-xs text-dark-500 mb-1">Previsão {horizon}d</p>
              <p className="text-xl font-bold" style={{ color: meta.color }}>
                {formatCurrency(forecast)}
              </p>
              <p className={`text-sm flex items-center gap-1 ${variation >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {variation >= 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                {variation >= 0 ? '+' : ''}{variation.toFixed(1)}%
              </p>
            </div>

            {/* Metrics */}
            <div className="space-y-1.5 border-t border-dark-100 pt-3">
              <div className="flex justify-between text-sm">
                <span className="text-dark-500">MAE:</span>
                <span className="font-medium">{metrics.mae != null ? metrics.mae.toFixed(2) : '-'}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-dark-500">RMSE:</span>
                <span className="font-medium">{metrics.rmse != null ? metrics.rmse.toFixed(2) : '-'}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-dark-500">MAPE:</span>
                <span className="font-medium">{metrics.mape != null ? `${metrics.mape.toFixed(1)}%` : '-'}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-dark-500">R²:</span>
                <span className="font-medium">{metrics.r2 != null ? metrics.r2.toFixed(4) : '-'}</span>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
