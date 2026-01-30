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

// Color palette for dynamic models
const MODEL_STYLES = {
  linear:        { color: '#8b5cf6', label: 'Regressão Linear', dash: '8 4' },
  arima:         { color: '#3b82f6', label: 'ARIMA',            dash: '5 5' },
  auto_arima:    { color: '#06b6d4', label: 'Auto ARIMA',       dash: '6 3' },
  random_forest: { color: '#f97316', label: 'Random Forest',    dash: '4 2' },
  xgboost:       { color: '#ef4444', label: 'XGBoost',          dash: '3 6' },
  prophet:       { color: '#22c55e', label: 'Prophet',          dash: '3 3' },
}

const FALLBACK_COLORS = ['#6366f1', '#ec4899', '#14b8a6', '#eab308']

function getModelStyle(key, index) {
  if (MODEL_STYLES[key]) return MODEL_STYLES[key]
  return {
    color: FALLBACK_COLORS[index % FALLBACK_COLORS.length],
    label: key,
    dash: '5 5',
  }
}

export default function ForecastChart({
  historico = [],
  modelos = {},
  title = 'Previsão de preços',
  description,
  height = 400,
  yAxisLabel = 'Preço previsto (R$)',
}) {
  const modelKeys = Object.keys(modelos)
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

  const lastHistoricalDate = historico.length > 0
    ? historico[historico.length - 1].data
    : null

  // Add forecast data for each model
  modelKeys.forEach(key => {
    const previsoes = modelos[key]?.previsoes || []
    previsoes.forEach(item => {
      const existing = chartData.find(d => d.data === item.data)
      if (existing) {
        existing[key] = item.previsto
        existing[`${key}_lower`] = item.ic_inferior
        existing[`${key}_upper`] = item.ic_superior
      } else {
        const entry = {
          data: item.data,
          label: formatDateLabel(item.data),
          tipo: 'previsao',
        }
        entry[key] = item.previsto
        entry[`${key}_lower`] = item.ic_inferior
        entry[`${key}_upper`] = item.ic_superior
        chartData.push(entry)
      }
    })
  })

  chartData.sort((a, b) => new Date(a.data) - new Date(b.data))

  const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload || payload.length === 0) return null
    const dp = payload[0]?.payload

    return (
      <div className="bg-white p-3 rounded-lg shadow-lg border border-dark-100 max-w-xs">
        <p className="font-medium text-dark-800 mb-2">{label}</p>

        {dp?.historico != null && (
          <p className="text-sm text-dark-600">
            Histórico: <span className="font-medium">{formatCurrency(dp.historico)}</span>
          </p>
        )}

        {modelKeys.map((key, i) => {
          if (dp?.[key] == null) return null
          const style = getModelStyle(key, i)
          return (
            <p key={key} className="text-sm" style={{ color: style.color }}>
              {style.label}: <span className="font-medium">{formatCurrency(dp[key])}</span>
              {dp[`${key}_lower`] != null && (
                <span className="text-xs text-dark-400 ml-1">
                  ({formatCurrency(dp[`${key}_lower`])} – {formatCurrency(dp[`${key}_upper`])})
                </span>
              )}
            </p>
          )
        })}
      </div>
    )
  }

  if (chartData.length === 0) {
    return (
      <div className="card p-6">
        <h3 className="chart-title">{title}</h3>
        {description && <p className="text-sm text-dark-500 mb-4">{description}</p>}
        <div className="flex items-center justify-center text-dark-400" style={{ height: height - 80 }}>
          Sem dados para exibir
        </div>
      </div>
    )
  }

  return (
    <div className="card p-6">
      <h3 className="chart-title">{title}</h3>
      {description && <p className="text-sm text-dark-500 mb-4">{description}</p>}

      <ResponsiveContainer width="100%" height={height}>
        <ComposedChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
          <defs>
            {modelKeys.map((key, i) => {
              const style = getModelStyle(key, i)
              return (
                <linearGradient key={key} id={`grad_${key}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={style.color} stopOpacity={0.25} />
                  <stop offset="95%" stopColor={style.color} stopOpacity={0.03} />
                </linearGradient>
              )
            })}
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
            tickFormatter={(v) => `R$${v.toFixed(0)}`}
          >
            <Label value={yAxisLabel} angle={-90} position="insideLeft" offset={10}
              style={{ fill: '#64748b', fontSize: 11 }} />
          </YAxis>

          <Tooltip content={<CustomTooltip />} />

          <Legend
            verticalAlign="top"
            height={36}
            formatter={(value) => {
              if (value === 'historico') return 'Histórico'
              const idx = modelKeys.indexOf(value)
              return getModelStyle(value, idx).label
            }}
          />

          {lastHistoricalDate && (
            <ReferenceLine
              x={formatDateLabel(lastHistoricalDate)}
              stroke="#9ca3af"
              strokeDasharray="5 5"
              label={{ value: 'Previsão', position: 'top', fill: '#6b7280', fontSize: 11 }}
            />
          )}

          {/* Confidence intervals */}
          {modelKeys.map((key, i) => (
            <Area
              key={`area_${key}`}
              type="monotone"
              dataKey={`${key}_upper`}
              stroke="none"
              fill={`url(#grad_${key})`}
              connectNulls
              legendType="none"
            />
          ))}

          {/* Historical line */}
          <Line
            type="monotone"
            dataKey="historico"
            stroke="#1f2937"
            strokeWidth={2}
            dot={false}
            connectNulls
          />

          {/* Model forecast lines */}
          {modelKeys.map((key, i) => {
            const style = getModelStyle(key, i)
            return (
              <Line
                key={`line_${key}`}
                type="monotone"
                dataKey={key}
                stroke={style.color}
                strokeWidth={2}
                strokeDasharray={style.dash}
                dot={false}
                connectNulls
              />
            )
          })}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}

function formatDateLabel(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr + 'T12:00:00')
  const month = date.toLocaleDateString('pt-BR', { month: 'short' })
  const year = date.getFullYear().toString().slice(-2)
  return `${month}/${year}`
}
