import { useMemo, useState } from 'react'
import {
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  ReferenceArea,
} from 'recharts'
import { formatCurrency } from '../utils/format'

const MODEL_STYLES = {
  linear:        { color: '#8b5cf6', label: 'Regressão Linear' },
  arima:         { color: '#3b82f6', label: 'ARIMA' },
  auto_arima:    { color: '#06b6d4', label: 'Auto ARIMA' },
  random_forest: { color: '#f97316', label: 'Random Forest' },
  xgboost:       { color: '#ef4444', label: 'XGBoost' },
  prophet:       { color: '#22c55e', label: 'Prophet' },
}

const FALLBACK_COLORS = ['#6366f1', '#ec4899', '#14b8a6', '#eab308']

function getModelStyle(key, index) {
  if (MODEL_STYLES[key]) return MODEL_STYLES[key]
  return {
    color: FALLBACK_COLORS[index % FALLBACK_COLORS.length],
    label: key,
  }
}

function formatDateLabel(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr + 'T12:00:00')
  const month = date.toLocaleDateString('pt-BR', { month: 'short' })
  const year = date.getFullYear().toString().slice(-2)
  return `${month}/${year}`
}

export default function ForecastChart({
  historico = [],
  modelos = {},
  title = 'Previsão de preços',
  description,
  height = 420,
}) {
  const modelKeys = Object.keys(modelos)
  const [visibleModels, setVisibleModels] = useState(() =>
    Object.fromEntries(modelKeys.map(k => [k, true]))
  )

  // Find best model by R²
  const bestModel = useMemo(() => {
    let best = null
    let bestR2 = -Infinity
    for (const key of modelKeys) {
      const r2 = modelos[key]?.metricas?.r2
      if (r2 != null && r2 > bestR2) {
        bestR2 = r2
        best = key
      }
    }
    return best
  }, [modelos, modelKeys])

  // Sort model keys by R² (best first) for tooltip ordering
  const sortedModelKeys = useMemo(() => {
    return [...modelKeys].sort((a, b) => {
      const r2a = modelos[a]?.metricas?.r2 ?? -1
      const r2b = modelos[b]?.metricas?.r2 ?? -1
      return r2b - r2a
    })
  }, [modelos, modelKeys])

  const toggleModel = (key) => {
    setVisibleModels(prev => ({ ...prev, [key]: !prev[key] }))
  }

  // Build chart data with bridge point
  const { chartData, lastHistLabel, firstForecastLabel } = useMemo(() => {
    const data = []

    // Historical points
    historico.forEach(item => {
      data.push({
        data: item.data,
        label: formatDateLabel(item.data),
        historico: item.valor,
      })
    })

    const lastHist = historico.length > 0 ? historico[historico.length - 1] : null
    const lastLabel = lastHist ? formatDateLabel(lastHist.data) : null

    // Bridge: add last historical value as first forecast point for each model
    if (lastHist) {
      const bridgeEntry = data[data.length - 1]
      for (const key of modelKeys) {
        bridgeEntry[key] = lastHist.valor
      }
    }

    let firstFcLabel = null

    // Forecast points
    modelKeys.forEach(key => {
      const previsoes = modelos[key]?.previsoes || []
      previsoes.forEach(item => {
        const lbl = formatDateLabel(item.data)
        if (!firstFcLabel) firstFcLabel = lbl
        const existing = data.find(d => d.data === item.data)
        if (existing) {
          existing[key] = item.previsto
          existing[`${key}_lower`] = item.ic_inferior
          existing[`${key}_upper`] = item.ic_superior
          existing[`${key}_range`] = [item.ic_inferior, item.ic_superior]
        } else {
          const entry = {
            data: item.data,
            label: lbl,
          }
          entry[key] = item.previsto
          entry[`${key}_lower`] = item.ic_inferior
          entry[`${key}_upper`] = item.ic_superior
          entry[`${key}_range`] = [item.ic_inferior, item.ic_superior]
          data.push(entry)
        }
      })
    })

    data.sort((a, b) => new Date(a.data) - new Date(b.data))

    return {
      chartData: data,
      lastHistLabel: lastLabel,
      firstForecastLabel: firstFcLabel,
    }
  }, [historico, modelos, modelKeys])

  // Last forecast label for ReferenceArea
  const lastForecastLabel = chartData.length > 0
    ? chartData[chartData.length - 1].label
    : null

  // Custom tooltip
  const CustomTooltip = ({ active, payload }) => {
    if (!active || !payload || payload.length === 0) return null
    const dp = payload[0]?.payload

    return (
      <div className="bg-white/95 backdrop-blur-sm p-3 rounded-xl shadow-lg border border-dark-100 min-w-[200px]">
        <p className="font-semibold text-dark-800 mb-2 text-sm">{dp?.label}</p>

        {dp?.historico != null && (
          <div className="flex items-center gap-2 mb-1.5 pb-1.5 border-b border-dark-100">
            <span className="w-2.5 h-2.5 rounded-full bg-dark-800 shrink-0" />
            <span className="text-sm text-dark-600">Histórico</span>
            <span className="text-sm font-semibold text-dark-800 ml-auto">{formatCurrency(dp.historico)}</span>
          </div>
        )}

        <div className="space-y-1">
          {sortedModelKeys.map((key, i) => {
            if (dp?.[key] == null || !visibleModels[key]) return null
            const style = getModelStyle(key, modelKeys.indexOf(key))
            const isBest = key === bestModel
            return (
              <div key={key} className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: style.color }} />
                <span className="text-xs text-dark-600 truncate">
                  {style.label}
                  {isBest && <span className="text-[10px] font-medium text-amber-600 ml-1">★</span>}
                </span>
                <span className="text-xs font-semibold ml-auto" style={{ color: style.color }}>
                  {formatCurrency(dp[key])}
                </span>
              </div>
            )
          })}
        </div>

        {/* Show IC for best visible model */}
        {bestModel && visibleModels[bestModel] && dp?.[`${bestModel}_lower`] != null && dp?.[bestModel] != null && (
          <div className="mt-2 pt-1.5 border-t border-dark-100 text-[10px] text-dark-400">
            IC 95%: {formatCurrency(dp[`${bestModel}_lower`])} – {formatCurrency(dp[`${bestModel}_upper`])}
          </div>
        )}
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

      {/* Interactive legend */}
      <div className="flex flex-wrap items-center gap-2 mb-4">
        {/* Historical chip */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-dark-50 text-xs font-medium text-dark-700">
          <span className="w-2.5 h-0.5 bg-dark-800 rounded" />
          Histórico
        </div>

        {/* Model chips */}
        {modelKeys.map((key, i) => {
          const style = getModelStyle(key, i)
          const active = visibleModels[key]
          const isBest = key === bestModel
          return (
            <button
              key={key}
              type="button"
              onClick={() => toggleModel(key)}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition-all
                ${active
                  ? 'bg-white shadow-sm border border-dark-200 text-dark-700'
                  : 'bg-dark-50 text-dark-400 border border-transparent'
                }`}
            >
              <span
                className="w-2.5 h-2.5 rounded-full shrink-0 transition-opacity"
                style={{
                  backgroundColor: style.color,
                  opacity: active ? 1 : 0.3,
                }}
              />
              {style.label}
              {isBest && active && (
                <span className="text-[10px] font-semibold text-amber-500 ml-0.5">★</span>
              )}
            </button>
          )
        })}
      </div>

      <ResponsiveContainer width="100%" height={height}>
        <ComposedChart data={chartData} margin={{ top: 5, right: 20, left: 10, bottom: 0 }}>
          <defs>
            {modelKeys.map((key, i) => {
              const style = getModelStyle(key, i)
              return (
                <linearGradient key={key} id={`grad_${key}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={style.color} stopOpacity={0.15} />
                  <stop offset="95%" stopColor={style.color} stopOpacity={0.02} />
                </linearGradient>
              )
            })}
          </defs>

          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />

          {/* Forecast zone background */}
          {firstForecastLabel && lastForecastLabel && (
            <ReferenceArea
              x1={firstForecastLabel}
              x2={lastForecastLabel}
              fill="#f8fafc"
              fillOpacity={0.8}
            />
          )}

          <XAxis
            dataKey="label"
            tick={{ fontSize: 11, fill: '#94a3b8' }}
            tickLine={false}
            axisLine={{ stroke: '#e2e8f0' }}
          />

          <YAxis
            tick={{ fontSize: 11, fill: '#94a3b8' }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) => `R$${v.toFixed(0)}`}
            width={65}
          />

          <Tooltip content={<CustomTooltip />} />

          {/* Divider line */}
          {lastHistLabel && (
            <ReferenceLine
              x={lastHistLabel}
              stroke="#cbd5e1"
              strokeDasharray="4 4"
              label={{
                value: 'Previsão',
                position: 'top',
                fill: '#94a3b8',
                fontSize: 10,
                fontWeight: 500,
              }}
            />
          )}

          {/* Confidence interval bands for visible models */}
          {modelKeys.map((key, i) => {
            if (!visibleModels[key]) return null
            const style = getModelStyle(key, i)
            return (
              <Area
                key={`band_${key}`}
                type="monotone"
                dataKey={`${key}_range`}
                stroke="none"
                fill={style.color}
                fillOpacity={key === bestModel ? 0.1 : 0.05}
                connectNulls
                legendType="none"
                isAnimationActive={false}
              />
            )
          })}

          {/* Historical line */}
          <Line
            type="monotone"
            dataKey="historico"
            stroke="#1e293b"
            strokeWidth={2.5}
            dot={false}
            connectNulls
            legendType="none"
          />

          {/* Model forecast lines */}
          {modelKeys.map((key, i) => {
            if (!visibleModels[key]) return null
            const style = getModelStyle(key, i)
            const isBest = key === bestModel
            return (
              <Line
                key={`line_${key}`}
                type="monotone"
                dataKey={key}
                stroke={style.color}
                strokeWidth={isBest ? 2.5 : 1.5}
                strokeDasharray={isBest ? undefined : '6 3'}
                dot={false}
                connectNulls
                legendType="none"
              />
            )
          })}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
