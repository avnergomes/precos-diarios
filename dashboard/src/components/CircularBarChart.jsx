import { useMemo } from 'react'
import * as d3 from 'd3'

const MONTHS = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

const CATEGORY_COLORS = {
  'Graos': '#009E73',
  'Pecuaria': '#D55E00',
  'Cafe': '#6B4423',
  'Florestal': '#0072B2',
  'Mandioca': '#CC79A7'
}

export default function CircularBarChart({
  data,
  category = null,
  title = "Padrão Sazonal de Preços",
  width = 400,
  height = 400
}) {
  const chartData = useMemo(() => {
    if (!data) return null

    // Extract monthly data for the selected category or overall
    const monthlyData = []

    for (let month = 1; month <= 12; month++) {
      const monthStr = month.toString().padStart(2, '0')
      let values = []

      // Collect all values for this month across years
      Object.entries(data).forEach(([period, info]) => {
        if (period.endsWith(`-${monthStr}`)) {
          if (category && data[period]) {
            values.push(info.media || info)
          } else {
            values.push(info.media || info)
          }
        }
      })

      if (values.length > 0) {
        const avg = values.reduce((a, b) => a + b, 0) / values.length
        monthlyData.push({
          month: MONTHS[month - 1],
          monthNum: month,
          value: avg
        })
      }
    }

    if (monthlyData.length === 0) return null

    const avgValue = monthlyData.reduce((sum, d) => sum + d.value, 0) / monthlyData.length

    return {
      data: monthlyData,
      avgValue,
      maxValue: Math.max(...monthlyData.map(d => d.value))
    }
  }, [data, category])

  if (!chartData) {
    return (
      <div className="bg-white rounded-xl shadow-lg p-6">
        <h3 className="text-lg font-semibold text-slate-700 mb-4">{title}</h3>
        <div className="h-64 flex items-center justify-center text-slate-400">
          Sem dados sazonais disponíveis
        </div>
      </div>
    )
  }

  const centerX = width / 2
  const centerY = height / 2
  const innerRadius = 50
  const outerRadius = Math.min(width, height) / 2 - 50

  const { data: monthlyData, avgValue, maxValue } = chartData

  // Create scales
  const xScale = d3.scaleBand()
    .domain(monthlyData.map(d => d.month))
    .range([0, 2 * Math.PI])
    .padding(0.15)

  const yScale = d3.scaleRadial()
    .domain([0, maxValue * 1.1])
    .range([innerRadius, outerRadius])

  // Arc generator
  const arcGenerator = d3.arc()

  // Grid levels
  const gridLevels = [0.25, 0.5, 0.75, 1.0]

  const formatValue = (v) => {
    if (v >= 1000) return `R$${(v/1000).toFixed(0)}K`
    return `R$${v.toFixed(0)}`
  }

  const color = category ? (CATEGORY_COLORS[category] || '#0072B2') : '#0072B2'

  return (
    <div className="bg-white rounded-xl shadow-lg p-6">
      <h3 className="text-lg font-semibold text-slate-700 mb-2">{title}</h3>
      {category && (
        <p className="text-sm text-slate-500 mb-4">Categoria: {category}</p>
      )}

      <svg width={width} height={height} className="mx-auto">
        <g transform={`translate(${centerX}, ${centerY})`}>
          {/* Grid circles */}
          {gridLevels.map((level, i) => (
            <circle
              key={`grid-${i}`}
              r={innerRadius + (outerRadius - innerRadius) * level}
              fill="none"
              stroke="#e2e8f0"
              strokeDasharray="4,4"
            />
          ))}

          {/* Inner circle */}
          <circle
            r={innerRadius}
            fill="#f8fafc"
            stroke="#e2e8f0"
            strokeWidth={1}
          />

          {/* Average line circle */}
          <circle
            r={yScale(avgValue)}
            fill="none"
            stroke="#64748b"
            strokeWidth={1}
            strokeDasharray="6,3"
          />

          {/* Grid labels */}
          {gridLevels.map((level, i) => (
            <text
              key={`grid-label-${i}`}
              x={4}
              y={-(innerRadius + (outerRadius - innerRadius) * level)}
              fill="#94a3b8"
              fontSize={9}
              alignmentBaseline="middle"
            >
              {formatValue(maxValue * level)}
            </text>
          ))}

          {/* Bars */}
          {monthlyData.map((d, i) => {
            const arcPath = arcGenerator({
              innerRadius: innerRadius,
              outerRadius: yScale(d.value),
              startAngle: xScale(d.month),
              endAngle: xScale(d.month) + xScale.bandwidth()
            })

            // Calculate label position
            const midAngle = xScale(d.month) + xScale.bandwidth() / 2 - Math.PI / 2
            const labelRadius = outerRadius + 20
            const labelX = labelRadius * Math.cos(midAngle)
            const labelY = labelRadius * Math.sin(midAngle)

            const isAboveAvg = d.value > avgValue
            const barColor = isAboveAvg ? color : d3.color(color).darker(0.3).toString()
            const opacity = isAboveAvg ? 0.9 : 0.6

            return (
              <g key={d.month} className="group cursor-pointer">
                <path
                  d={arcPath}
                  fill={barColor}
                  fillOpacity={opacity}
                  stroke="white"
                  strokeWidth={1}
                  className="transition-all group-hover:fill-opacity-100"
                >
                  <title>
                    {`${d.month}\nPreço médio: ${formatValue(d.value)}\n${isAboveAvg ? 'Acima' : 'Abaixo'} da média anual`}
                  </title>
                </path>

                {/* Month label */}
                <text
                  x={labelX}
                  y={labelY}
                  fill="#475569"
                  fontSize={11}
                  fontWeight="500"
                  textAnchor="middle"
                  alignmentBaseline="middle"
                >
                  {d.month}
                </text>
              </g>
            )
          })}

          {/* Center text */}
          <text
            x={0}
            y={-8}
            fill="#334155"
            fontSize={11}
            fontWeight="bold"
            textAnchor="middle"
          >
            Média
          </text>
          <text
            x={0}
            y={10}
            fill="#64748b"
            fontSize={12}
            fontFamily="monospace"
            textAnchor="middle"
          >
            {formatValue(avgValue)}
          </text>
        </g>
      </svg>

      {/* Summary stats */}
      <div className="mt-4 grid grid-cols-3 gap-4 text-center border-t pt-4">
        <div>
          <p className="text-xs text-slate-400">Mês mais caro</p>
          <p className="text-sm font-semibold text-slate-700">
            {monthlyData.reduce((max, d) => d.value > max.value ? d : max, monthlyData[0]).month}
          </p>
        </div>
        <div>
          <p className="text-xs text-slate-400">Variação</p>
          <p className="text-sm font-semibold text-slate-700 font-mono">
            {((maxValue - Math.min(...monthlyData.map(d => d.value))) / avgValue * 100).toFixed(0)}%
          </p>
        </div>
        <div>
          <p className="text-xs text-slate-400">Mês mais barato</p>
          <p className="text-sm font-semibold text-slate-700">
            {monthlyData.reduce((min, d) => d.value < min.value ? d : min, monthlyData[0]).month}
          </p>
        </div>
      </div>
    </div>
  )
}
