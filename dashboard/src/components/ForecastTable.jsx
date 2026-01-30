import { Download } from 'lucide-react'
import { formatCurrency } from '../utils/format'

const MODEL_LABELS = {
  linear: 'Linear',
  arima: 'ARIMA',
  auto_arima: 'Auto ARIMA',
  random_forest: 'Random Forest',
  xgboost: 'XGBoost',
  prophet: 'Prophet',
}

const MODEL_COLORS = {
  linear: 'text-purple-600',
  arima: 'text-blue-600',
  auto_arima: 'text-cyan-600',
  random_forest: 'text-orange-600',
  xgboost: 'text-red-600',
  prophet: 'text-green-600',
}

export default function ForecastTable({
  modelos = {},
  title = 'Previsões detalhadas',
}) {
  const modelKeys = Object.keys(modelos).filter(k => (modelos[k]?.previsoes?.length || 0) > 0)

  // Merge all forecasts by date
  const forecastMap = {}

  modelKeys.forEach(key => {
    const previsoes = modelos[key]?.previsoes || []
    previsoes.forEach(item => {
      if (!forecastMap[item.data]) {
        forecastMap[item.data] = { data: item.data }
      }
      forecastMap[item.data][key] = item.previsto
      forecastMap[item.data][`${key}_ic`] = `${formatCurrency(item.ic_inferior)} – ${formatCurrency(item.ic_superior)}`
    })
  })

  const forecasts = Object.values(forecastMap).sort(
    (a, b) => new Date(a.data) - new Date(b.data)
  )

  const exportCSV = () => {
    const headers = ['Data']
    modelKeys.forEach(key => {
      const label = MODEL_LABELS[key] || key
      headers.push(label, `IC 95% ${label}`)
    })

    const rows = forecasts.map(f => {
      const row = [f.data]
      modelKeys.forEach(key => {
        row.push(f[key]?.toFixed(2) || '', f[`${key}_ic`] || '')
      })
      return row
    })

    const csv = [headers, ...rows].map(row => row.join(';')).join('\n')
    const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'previsoes.csv'
    link.click()
  }

  if (forecasts.length === 0) {
    return (
      <div className="card p-6">
        <h3 className="chart-title">{title}</h3>
        <div className="text-center text-dark-400 py-8">
          Nenhuma previsão disponível
        </div>
      </div>
    )
  }

  return (
    <div className="card p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="chart-title mb-0">{title}</h3>
        <button onClick={exportCSV} className="btn-secondary flex items-center gap-2">
          <Download className="w-4 h-4" />
          <span className="hidden sm:inline">Exportar CSV</span>
        </button>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[500px]">
          <thead>
            <tr className="table-header">
              <th className="px-4 py-3 text-left">Data</th>
              {modelKeys.map(key => (
                <th key={key} className={`px-4 py-3 text-right ${MODEL_COLORS[key] || 'text-dark-600'}`}>
                  {MODEL_LABELS[key] || key}
                </th>
              ))}
              <th className="px-4 py-3 text-right text-dark-500">IC 95%</th>
            </tr>
          </thead>
          <tbody>
            {forecasts.map(forecast => (
              <tr key={forecast.data} className="table-row">
                <td className="px-4 py-3 font-medium">
                  {formatDate(forecast.data)}
                </td>
                {modelKeys.map(key => (
                  <td key={key} className={`px-4 py-3 text-right font-medium ${MODEL_COLORS[key] || ''}`}>
                    {forecast[key] != null ? formatCurrency(forecast[key]) : '-'}
                  </td>
                ))}
                <td className="px-4 py-3 text-right text-dark-400 text-sm">
                  {modelKeys.map(k => forecast[`${k}_ic`]).find(v => v) || '-'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
}
