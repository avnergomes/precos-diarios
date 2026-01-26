import {
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
  Label,
} from 'recharts'
import { formatCurrency } from '../utils/format'

/**
 * ForecastChart - Display historical data and forecasts
 * Shows ARIMA and Prophet predictions with confidence intervals
 */
export default function ForecastChart({
  historico = [],
  modelos = {},
  title = 'Previsão de preços',
  description,
  height = 400,
  yAxisLabel = 'Preço previsto (R$)',
}) {
  // Combine historical and forecast data
  const chartData = []

  // Add historical data
  historico.forEach(item => {
    chartData.push({
      data: item.data,
      label: formatDateLabel(item.data),
      historico: item.valor,
      tipo: 'historico',
    })
  })

  // Determine where forecast starts
  const lastHistoricalDate = historico.length > 0
    ? historico[historico.length - 1].data
    : null

  // Add ARIMA forecast
  const arimaData = modelos.arima?.previsoes || []
  arimaData.forEach(item => {
    const existing = chartData.find(d => d.data === item.data)
    if (existing) {
      existing.arima = item.previsto
      existing.arima_lower = item.ic_inferior
      existing.arima_upper = item.ic_superior
    } else {
      chartData.push({
        data: item.data,
        label: formatDateLabel(item.data),
        arima: item.previsto,
        arima_lower: item.ic_inferior,
        arima_upper: item.ic_superior,
        tipo: 'previsao',
      })
    }
  })

  // Add Prophet forecast
  const prophetData = modelos.prophet?.previsoes || []
  prophetData.forEach(item => {
    const existing = chartData.find(d => d.data === item.data)
    if (existing) {
      existing.prophet = item.previsto
      existing.prophet_lower = item.ic_inferior
      existing.prophet_upper = item.ic_superior
    } else {
      chartData.push({
        data: item.data,
        label: formatDateLabel(item.data),
        prophet: item.previsto,
        prophet_lower: item.ic_inferior,
        prophet_upper: item.ic_superior,
        tipo: 'previsao',
      })
    }
  })

  // Add Linear regression forecast (fallback)
  const linearData = modelos.linear?.previsoes || []
  linearData.forEach(item => {
    const existing = chartData.find(d => d.data === item.data)
    if (existing) {
      existing.linear = item.previsto
      existing.linear_lower = item.ic_inferior
      existing.linear_upper = item.ic_superior
    } else {
      chartData.push({
        data: item.data,
        label: formatDateLabel(item.data),
        linear: item.previsto,
        linear_lower: item.ic_inferior,
        linear_upper: item.ic_superior,
        tipo: 'previsao',
      })
    }
  })

  // Sort by date
  chartData.sort((a, b) => new Date(a.data) - new Date(b.data))

  // Custom tooltip
  const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload || payload.length === 0) return null

    const dataPoint = payload[0]?.payload

    return (
      <div className="bg-white p-3 rounded-lg shadow-lg border border-dark-100">
        <p className="font-medium text-dark-800 mb-2">{label}</p>

        {dataPoint?.historico && (
          <p className="text-sm text-dark-600">
            Histórico: <span className="font-medium">{formatCurrency(dataPoint.historico)}</span>
          </p>
        )}

        {dataPoint?.arima && (
          <p className="text-sm text-blue-600">
            ARIMA: <span className="font-medium">{formatCurrency(dataPoint.arima)}</span>
            <span className="text-xs text-dark-400 ml-1">
              ({formatCurrency(dataPoint.arima_lower)} - {formatCurrency(dataPoint.arima_upper)})
            </span>
          </p>
        )}

        {dataPoint?.prophet && (
          <p className="text-sm text-green-600">
            Prophet: <span className="font-medium">{formatCurrency(dataPoint.prophet)}</span>
            <span className="text-xs text-dark-400 ml-1">
              ({formatCurrency(dataPoint.prophet_lower)} - {formatCurrency(dataPoint.prophet_upper)})
            </span>
          </p>
        )}

        {dataPoint?.linear && (
          <p className="text-sm text-purple-600">
            Linear: <span className="font-medium">{formatCurrency(dataPoint.linear)}</span>
            <span className="text-xs text-dark-400 ml-1">
              ({formatCurrency(dataPoint.linear_lower)} - {formatCurrency(dataPoint.linear_upper)})
            </span>
          </p>
        )}
      </div>
    )
  }

  if (chartData.length === 0) {
    return (
      <div className="card p-6">
        <h3 className="chart-title">{title}</h3>
        {description && (
          <p className="text-sm text-dark-500 mb-4">{description}</p>
        )}
        <div className="flex items-center justify-center text-dark-400" style={{ height: height - 80 }}>
          Sem dados para exibir
        </div>
      </div>
    )
  }

  return (
    <div className="card p-6">
      <h3 className="chart-title">{title}</h3>
      {description && (
        <p className="text-sm text-dark-500 mb-4">{description}</p>
      )}

      <ResponsiveContainer width="100%" height={height}>
        <ComposedChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
          <defs>
            {/* ARIMA confidence interval gradient */}
            <linearGradient id="arimaGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.05} />
            </linearGradient>
            {/* Prophet confidence interval gradient */}
            <linearGradient id="prophetGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#22c55e" stopOpacity={0.05} />
            </linearGradient>
            {/* Linear regression confidence interval gradient */}
            <linearGradient id="linearGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0.05} />
            </linearGradient>
          </defs>

          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />

          <XAxis
            dataKey="label"
            tick={{ fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: '#e5e7eb' }}
          />

          <YAxis
            tick={{ fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(value) => `R$${(value / 1).toFixed(0)}`}
          >
            <Label
              value={yAxisLabel}
              angle={-90}
              position="insideLeft"
              offset={10}
              style={{ fill: '#64748b', fontSize: 11 }}
            />
          </YAxis>

          <Tooltip content={<CustomTooltip />} />

          <Legend
            verticalAlign="top"
            height={36}
            formatter={(value) => {
              const labels = {
                historico: 'Histórico',
                arima: 'ARIMA',
                prophet: 'Prophet',
                linear: 'Regressão Linear',
              }
              return labels[value] || value
            }}
          />

          {/* Reference line where forecast starts */}
          {lastHistoricalDate && (
            <ReferenceLine
              x={formatDateLabel(lastHistoricalDate)}
              stroke="#9ca3af"
              strokeDasharray="5 5"
              label={{ value: 'Previsão', position: 'top', fill: '#6b7280', fontSize: 11 }}
            />
          )}

          {/* ARIMA confidence interval */}
          {modelos.arima && (
            <Area
              type="monotone"
              dataKey="arima_upper"
              stackId="arima"
              stroke="none"
              fill="url(#arimaGradient)"
              connectNulls
            />
          )}

          {/* Prophet confidence interval */}
          {modelos.prophet && (
            <Area
              type="monotone"
              dataKey="prophet_upper"
              stackId="prophet"
              stroke="none"
              fill="url(#prophetGradient)"
              connectNulls
            />
          )}

          {/* Historical line */}
          <Line
            type="monotone"
            dataKey="historico"
            stroke="#1f2937"
            strokeWidth={2}
            dot={false}
            connectNulls
          />

          {/* ARIMA forecast line */}
          {modelos.arima && (
            <Line
              type="monotone"
              dataKey="arima"
              stroke="#3b82f6"
              strokeWidth={2}
              strokeDasharray="5 5"
              dot={false}
              connectNulls
            />
          )}

          {/* Prophet forecast line */}
          {modelos.prophet && (
            <Line
              type="monotone"
              dataKey="prophet"
              stroke="#22c55e"
              strokeWidth={2}
              strokeDasharray="3 3"
              dot={false}
              connectNulls
            />
          )}

          {/* Linear regression confidence interval */}
          {modelos.linear && (
            <Area
              type="monotone"
              dataKey="linear_upper"
              stackId="linear"
              stroke="none"
              fill="url(#linearGradient)"
              connectNulls
            />
          )}

          {/* Linear regression forecast line */}
          {modelos.linear && (
            <Line
              type="monotone"
              dataKey="linear"
              stroke="#8b5cf6"
              strokeWidth={2}
              strokeDasharray="8 4"
              dot={false}
              connectNulls
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}

// Format date for display
function formatDateLabel(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const month = date.toLocaleDateString('pt-BR', { month: 'short' })
  const year = date.getFullYear().toString().slice(-2)
  return `${month}/${year}`
}
