import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Label,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import { formatCurrency, formatPeriod } from '../utils/format'

export default function TimeSeriesChart({
  data,
  title,
  description,
  height = 300,
  showMinMax = false,
  color = '#f59e0b',
  yAxisLabel = 'Preço médio (R$)',
}) {
  if (!data || Object.keys(data).length === 0) {
    return (
      <div className="chart-container">
        <h3 className="chart-title">{title}</h3>
        {description && (
          <p className="text-sm text-dark-500 mb-4">{description}</p>
        )}
        <div className="h-64 flex items-center justify-center text-dark-400">
          Sem dados disponíveis
        </div>
      </div>
    )
  }

  // Transform data for Recharts
  const chartData = Object.entries(data)
    .map(([period, values]) => {
      const isNumber = typeof values === 'number'
      const media = isNumber ? values : values.media || 0
      const min = isNumber ? media : (values.min ?? values.media ?? 0)
      const max = isNumber ? media : (values.max ?? values.media ?? 0)
      const count = isNumber ? 0 : values.count || 0

      return {
        period,
        periodLabel: formatPeriod(period),
        media,
        min,
        max,
        count,
      }
    })
    .sort((a, b) => a.period.localeCompare(b.period))

  const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload || !payload.length) return null

    return (
      <div className="bg-white/95 backdrop-blur-sm border border-dark-200 rounded-lg shadow-lg p-3">
        <p className="font-semibold text-dark-800 mb-2">
          {formatPeriod(label)}
        </p>
        {payload.map((entry, index) => (
          <p key={index} className="text-sm" style={{ color: entry.color }}>
            {entry.name}: {formatCurrency(entry.value)}
          </p>
        ))}
      </div>
    )
  }

  return (
    <div className="chart-container">
      <h3 className="chart-title">{title}</h3>
      {description && (
        <p className="text-sm text-dark-500 mb-4">{description}</p>
      )}

      <ResponsiveContainer width="100%" height={height}>
        {showMinMax ? (
          <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="colorMedia" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={color} stopOpacity={0.3} />
                <stop offset="95%" stopColor={color} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis
              dataKey="periodLabel"
              tick={{ fontSize: 11, fill: '#64748b' }}
              tickLine={false}
              axisLine={{ stroke: '#e2e8f0' }}
              interval="preserveStartEnd"
            />
            <YAxis
              tick={{ fontSize: 11, fill: '#64748b' }}
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
            <Legend />
            <Area
              type="monotone"
              dataKey="max"
              stroke="#22c55e"
              fill="none"
              strokeWidth={1}
              strokeDasharray="3 3"
              name="Máximo"
            />
            <Area
              type="monotone"
              dataKey="media"
              stroke={color}
              fill="url(#colorMedia)"
              strokeWidth={2}
              name="Média"
            />
            <Area
              type="monotone"
              dataKey="min"
              stroke="#ef4444"
              fill="none"
              strokeWidth={1}
              strokeDasharray="3 3"
              name="Mínimo"
            />
          </AreaChart>
        ) : (
          <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="colorMedia2" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={color} stopOpacity={0.3} />
                <stop offset="95%" stopColor={color} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis
              dataKey="periodLabel"
              tick={{ fontSize: 11, fill: '#64748b' }}
              tickLine={false}
              axisLine={{ stroke: '#e2e8f0' }}
              interval="preserveStartEnd"
            />
            <YAxis
              tick={{ fontSize: 11, fill: '#64748b' }}
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
            <Area
              type="monotone"
              dataKey="media"
              stroke={color}
              fill="url(#colorMedia2)"
              strokeWidth={2}
              name="Preço médio"
            />
          </AreaChart>
        )}
      </ResponsiveContainer>
    </div>
  )
}
