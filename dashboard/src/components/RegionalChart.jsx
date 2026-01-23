import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import { formatCurrency, CHART_COLORS } from '../utils/format'

export default function RegionalChart({
  data,
  title,
  height = 300,
  horizontal = false,
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
    .map(([regional, values]) => ({
      name: regional,
      media: values.media || 0,
      registros: values.registros || 0,
    }))
    .sort((a, b) => b.media - a.media)
    .slice(0, 15)

  const CustomTooltip = ({ active, payload }) => {
    if (!active || !payload || !payload.length) return null

    const data = payload[0].payload
    return (
      <div className="bg-white/95 backdrop-blur-sm border border-dark-200 rounded-lg shadow-lg p-3">
        <p className="font-semibold text-dark-800 mb-2">{data.name}</p>
        <p className="text-sm text-dark-600">
          Preco Medio: {formatCurrency(data.media)}
        </p>
        <p className="text-sm text-dark-600">
          Registros: {data.registros.toLocaleString('pt-BR')}
        </p>
      </div>
    )
  }

  return (
    <div className="chart-container">
      <h3 className="chart-title">{title}</h3>

      <ResponsiveContainer width="100%" height={horizontal ? Math.max(height, chartData.length * 35) : height}>
        {horizontal ? (
          <BarChart
            data={chartData}
            layout="vertical"
            margin={{ top: 5, right: 30, left: 100, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" horizontal={false} />
            <XAxis
              type="number"
              tick={{ fontSize: 11, fill: '#64748b' }}
              tickLine={false}
              axisLine={{ stroke: '#e2e8f0' }}
              tickFormatter={(value) => formatCurrency(value)}
            />
            <YAxis
              type="category"
              dataKey="name"
              tick={{ fontSize: 11, fill: '#334155' }}
              tickLine={false}
              axisLine={false}
              width={95}
            />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="media" radius={[0, 4, 4, 0]}>
              {chartData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={CHART_COLORS[index % CHART_COLORS.length]}
                />
              ))}
            </Bar>
          </BarChart>
        ) : (
          <BarChart
            data={chartData}
            margin={{ top: 5, right: 10, left: 10, bottom: 60 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 10, fill: '#64748b', angle: -45, textAnchor: 'end' }}
              tickLine={false}
              axisLine={{ stroke: '#e2e8f0' }}
              height={60}
            />
            <YAxis
              tick={{ fontSize: 11, fill: '#64748b' }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(value) => `R$${(value / 1).toFixed(0)}`}
            />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="media" radius={[4, 4, 0, 0]}>
              {chartData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={CHART_COLORS[index % CHART_COLORS.length]}
                />
              ))}
            </Bar>
          </BarChart>
        )}
      </ResponsiveContainer>
    </div>
  )
}
