import { Download } from 'lucide-react'
import { formatCurrency } from '../utils/format'

/**
 * ForecastTable - Display detailed forecast values in a table
 */
export default function ForecastTable({
  modelos = {},
  title = 'Previsões detalhadas',
}) {
  const arima = modelos.arima?.previsoes || []
  const prophet = modelos.prophet?.previsoes || []

  // Merge forecasts by date
  const forecastMap = {}

  arima.forEach(item => {
    if (!forecastMap[item.data]) {
      forecastMap[item.data] = { data: item.data }
    }
    forecastMap[item.data].arima = item.previsto
    forecastMap[item.data].arima_ic = `${formatCurrency(item.ic_inferior)} - ${formatCurrency(item.ic_superior)}`
  })

  prophet.forEach(item => {
    if (!forecastMap[item.data]) {
      forecastMap[item.data] = { data: item.data }
    }
    forecastMap[item.data].prophet = item.previsto
    forecastMap[item.data].prophet_ic = `${formatCurrency(item.ic_inferior)} - ${formatCurrency(item.ic_superior)}`
  })

  const forecasts = Object.values(forecastMap).sort(
    (a, b) => new Date(a.data) - new Date(b.data)
  )

  // Export to CSV
  const exportCSV = () => {
    const headers = ['Data', 'ARIMA', 'IC 95% ARIMA', 'Prophet', 'IC 95% Prophet']
    const rows = forecasts.map(f => [
      f.data,
      f.arima?.toFixed(2) || '',
      f.arima_ic || '',
      f.prophet?.toFixed(2) || '',
      f.prophet_ic || '',
    ])

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
        <table className="w-full min-w-[600px]">
          <thead>
            <tr className="table-header">
              <th className="px-4 py-3 text-left">Data</th>
              <th className="px-4 py-3 text-right text-blue-600">ARIMA</th>
              <th className="px-4 py-3 text-right text-green-600">Prophet</th>
              <th className="px-4 py-3 text-right text-dark-500">IC 95%</th>
            </tr>
          </thead>
          <tbody>
            {forecasts.map((forecast, index) => (
              <tr key={forecast.data} className="table-row">
                <td className="px-4 py-3 font-medium">
                  {formatDate(forecast.data)}
                </td>
                <td className="px-4 py-3 text-right text-blue-600 font-medium">
                  {forecast.arima ? formatCurrency(forecast.arima) : '-'}
                </td>
                <td className="px-4 py-3 text-right text-green-600 font-medium">
                  {forecast.prophet ? formatCurrency(forecast.prophet) : '-'}
                </td>
                <td className="px-4 py-3 text-right text-dark-400 text-sm">
                  {forecast.arima_ic || forecast.prophet_ic || '-'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// Format date for display
function formatDate(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
}
