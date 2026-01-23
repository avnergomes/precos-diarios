import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import { formatCurrency, formatPeriod } from '../utils/format'

export default function TimeSeriesChart({
  data,
  title,
  height = 300,
  showMinMax = false,
  color = '#f59e0b',
}) {
  if (!data || Object.keys(data).length === 0) {
    return (
      <div className="chart-container">
        <h3 className="chart-title">{title}</h3>
        <div className="h-64 flex items-center justify-center text-dark-400">
          Sem dados disponiveis
        </div>
      </div>
    )
  }

  // Transform data for Recharts
  const chartData = Object.entries(data)
    .map(([period, values]) => ({
      period,
      periodLabel: formatPeriod(period),
      media: values.media || 0,
      min: values.min || 0,
      max: values.max || 0,
      count: values.count || 0,
    }))
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
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend />
            <Area
              type="monotone"
              dataKey="max"
              stroke="#22c55e"
              fill="none"
              strokeWidth={1}
              strokeDasharray="3 3"
              name="Maximo"
            />
            <Area
              type="monotone"
              dataKey="media"
              stroke={color}
              fill="url(#colorMedia)"
              strokeWidth={2}
              name="Media"
            />
            <Area
              type="monotone"
              dataKey="min"
              stroke="#ef4444"
              fill="none"
              strokeWidth={1}
              strokeDasharray="3 3"
              name="Minimo"
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
            />
            <Tooltip content={<CustomTooltip />} />
            <Area
              type="monotone"
              dataKey="media"
              stroke={color}
              fill="url(#colorMedia2)"
              strokeWidth={2}
              name="Preco Medio"
            />
          </AreaChart>
        )}
      </ResponsiveContainer>
    </div>
  )
}
