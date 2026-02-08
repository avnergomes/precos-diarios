import { useState } from 'react'
import {
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  Label,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import {
  formatCurrency,
  formatCategoryName,
  getCategoryColor,
  CHART_COLORS,
} from '../utils/format'

export default function CategoryChart({
  data,
  title,
  description,
  height = 300,
  showPie = false,
  xAxisLabel = 'Preço médio (R$)',
  onCategoriaClick,
  selectedCategoria,
}) {
  const [viewMode, setViewMode] = useState(showPie ? 'pie' : 'bar')

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
    .map(([categoria, values]) => ({
      name: formatCategoryName(categoria),
      rawName: categoria,
      media: values.media || 0,
      registros: values.registros || 0,
      produtos: values.produtos || 0,
      color: getCategoryColor(categoria),
    }))
    .sort((a, b) => b.registros - a.registros)

  const CustomTooltip = ({ active, payload }) => {
    if (!active || !payload || !payload.length) return null

    const data = payload[0].payload
    return (
      <div className="bg-white/95 backdrop-blur-sm border border-dark-200 rounded-lg shadow-lg p-3">
        <p className="font-semibold text-dark-800 mb-2">{data.name}</p>
        <p className="text-sm text-dark-600">
          Preço médio: {formatCurrency(data.media)}
        </p>
        <p className="text-sm text-dark-600">
          Registros: {data.registros.toLocaleString('pt-BR')}
        </p>
        {data.produtos && (
          <p className="text-sm text-dark-600">
            Produtos: {data.produtos}
          </p>
        )}
      </div>
    )
  }

  const renderCustomLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent, name }) => {
    if (percent < 0.05) return null
    const RADIAN = Math.PI / 180
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5
    const x = cx + radius * Math.cos(-midAngle * RADIAN)
    const y = cy + radius * Math.sin(-midAngle * RADIAN)

    return (
      <text
        x={x}
        y={y}
        fill="white"
        textAnchor={x > cx ? 'start' : 'end'}
        dominantBaseline="central"
        className="text-xs font-medium"
      >
        {`${(percent * 100).toFixed(0)}%`}
      </text>
    )
  }

  return (
    <div className="chart-container">
      <div className="flex items-center justify-between mb-4">
        <h3 className="chart-title mb-0">{title}</h3>
        {showPie && (
          <div className="flex gap-1 bg-dark-100 rounded-lg p-1">
            <button
              onClick={() => setViewMode('bar')}
              className={`px-3 py-1 text-xs font-medium rounded ${
                viewMode === 'bar'
                  ? 'bg-white shadow text-dark-800'
                  : 'text-dark-500 hover:text-dark-700'
              }`}
            >
              Barras
            </button>
            <button
              onClick={() => setViewMode('pie')}
              className={`px-3 py-1 text-xs font-medium rounded ${
                viewMode === 'pie'
                  ? 'bg-white shadow text-dark-800'
                  : 'text-dark-500 hover:text-dark-700'
              }`}
            >
              Pizza
            </button>
          </div>
        )}
      </div>
      {description && (
        <p className="text-sm text-dark-500 mb-4">{description}</p>
      )}

      {selectedCategoria && (
        <p className="text-xs text-center text-primary-600 mb-2 font-medium">
          Categoria selecionada: {formatCategoryName(selectedCategoria)}
        </p>
      )}

      <ResponsiveContainer width="100%" height={height}>
        {viewMode === 'pie' ? (
          <PieChart>
            <Pie
              data={chartData}
              dataKey="registros"
              nameKey="name"
              cx="50%"
              cy="50%"
              outerRadius={height / 3}
              label={renderCustomLabel}
              labelLine={false}
              onClick={(data) => onCategoriaClick?.(data.rawName)}
              cursor={onCategoriaClick ? 'pointer' : 'default'}
            >
              {chartData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={CHART_COLORS[index % CHART_COLORS.length]}
                  opacity={selectedCategoria && entry.rawName !== selectedCategoria ? 0.4 : 1}
                />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
            <Legend
              layout="vertical"
              align="right"
              verticalAlign="middle"
              formatter={(value) => <span className="text-sm text-dark-600">{value}</span>}
            />
          </PieChart>
        ) : (
          <BarChart
            data={chartData}
            layout="vertical"
            margin={{ top: 5, right: 30, left: 80, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" horizontal={false} />
            <XAxis
              type="number"
              tick={{ fontSize: 11, fill: '#64748b' }}
              tickLine={false}
              axisLine={{ stroke: '#e2e8f0' }}
              tickFormatter={(value) => formatCurrency(value)}
            >
              <Label
                value={xAxisLabel}
                position="insideBottom"
                offset={-5}
                style={{ fill: '#64748b', fontSize: 11 }}
              />
            </XAxis>
            <YAxis
              type="category"
              dataKey="name"
              tick={{ fontSize: 12, fill: '#334155' }}
              tickLine={false}
              axisLine={false}
              width={75}
            />
            <Tooltip content={<CustomTooltip />} />
            <Bar
              dataKey="media"
              radius={[0, 4, 4, 0]}
              onClick={(data) => onCategoriaClick?.(data.rawName)}
              cursor={onCategoriaClick ? 'pointer' : 'default'}
            >
              {chartData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={CHART_COLORS[index % CHART_COLORS.length]}
                  opacity={selectedCategoria && entry.rawName !== selectedCategoria ? 0.4 : 1}
                />
              ))}
            </Bar>
          </BarChart>
        )}
      </ResponsiveContainer>

      {onCategoriaClick && (
        <p className="text-xs text-center text-dark-400 mt-2">
          Clique para filtrar por categoria
        </p>
      )}
    </div>
  )
}
