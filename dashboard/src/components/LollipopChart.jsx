import { useMemo } from 'react'
import * as d3 from 'd3'

const MARGIN = { top: 20, right: 40, bottom: 20, left: 180 }

const CATEGORY_COLORS = {
  'Graos': '#009E73',
  'Pecuaria': '#D55E00',
  'Cafe': '#6B4423',
  'Florestal': '#0072B2',
  'Mandioca': '#CC79A7'
}

export default function LollipopChart({
  data,
  title = "Preço Médio por Produto",
  width = 500,
  height = 450
}) {
  const chartData = useMemo(() => {
    if (!data) return null

    // Support both object format { name: { media, categoria } } and array format [{ produto, media, categoria }]
    let items
    if (Array.isArray(data)) {
      items = data.map(item => ({
        name: item.produto || item.name,
        value: item.media || item.value || 0,
        category: item.categoria || item.category
      }))
    } else {
      items = Object.entries(data).map(([name, info]) => ({
        name,
        value: info.media || info.value || 0,
        category: info.categoria || info.category
      }))
    }

    const sorted = items.filter(d => d.value > 0).sort((a, b) => b.value - a.value).slice(0, 15)
    if (sorted.length === 0) return null

    const maxValue = Math.max(...sorted.map(d => d.value))

    return { items: sorted, maxValue }
  }, [data])

  if (!chartData) {
    return (
      <div className="bg-white rounded-xl shadow-lg p-6">
        <h3 className="text-lg font-semibold text-slate-700 mb-4">{title}</h3>
        <div className="h-64 flex items-center justify-center text-slate-400">
          Sem dados disponíveis
        </div>
      </div>
    )
  }

  const innerWidth = width - MARGIN.left - MARGIN.right
  const innerHeight = height - MARGIN.top - MARGIN.bottom

  const { items, maxValue } = chartData

  const xScale = d3.scaleLinear()
    .domain([0, maxValue * 1.1])
    .range([0, innerWidth])

  const yScale = d3.scaleBand()
    .domain(items.map(d => d.name))
    .range([0, innerHeight])
    .padding(0.35)

  const formatValue = (v) => {
    if (v >= 1000) return `R$ ${(v/1000).toFixed(1)}K`
    return `R$ ${v.toFixed(2)}`
  }

  return (
    <div className="bg-white rounded-xl shadow-lg p-6">
      <h3 className="text-lg font-semibold text-slate-700 mb-4">{title}</h3>

      <svg width={width} height={height}>
        <g transform={`translate(${MARGIN.left}, ${MARGIN.top})`}>
          {/* Grid lines */}
          {xScale.ticks(5).map((tick, i) => (
            <line
              key={`grid-${i}`}
              x1={xScale(tick)}
              x2={xScale(tick)}
              y1={0}
              y2={innerHeight}
              stroke="#e2e8f0"
              strokeDasharray="4,4"
            />
          ))}

          {/* X-axis labels */}
          {xScale.ticks(5).map((tick, i) => (
            <text
              key={`x-label-${i}`}
              x={xScale(tick)}
              y={innerHeight + 15}
              fill="#64748b"
              fontSize={10}
              textAnchor="middle"
            >
              {formatValue(tick)}
            </text>
          ))}

          {/* Lollipops */}
          {items.map((item, i) => {
            const y = yScale(item.name) + yScale.bandwidth() / 2
            const xEnd = xScale(item.value)
            const color = CATEGORY_COLORS[item.category] || '#64748b'

            return (
              <g key={item.name} className="group cursor-pointer">
                {/* Hover background */}
                <rect
                  x={-MARGIN.left}
                  y={yScale(item.name) - 2}
                  width={innerWidth + MARGIN.left + MARGIN.right}
                  height={yScale.bandwidth() + 4}
                  fill="#f1f5f9"
                  fillOpacity={0}
                  className="transition-all group-hover:fill-opacity-100"
                />

                {/* Line */}
                <line
                  x1={0}
                  x2={xEnd}
                  y1={y}
                  y2={y}
                  stroke={color}
                  strokeWidth={2}
                  className="transition-all"
                />

                {/* Circle */}
                <circle
                  cx={xEnd}
                  cy={y}
                  r={8}
                  fill={color}
                  stroke="white"
                  strokeWidth={2}
                >
                  <title>{`${item.name}: ${formatValue(item.value)}`}</title>
                </circle>

                {/* Value label on hover */}
                <text
                  x={xEnd + 14}
                  y={y}
                  fill="#334155"
                  fontSize={11}
                  fontFamily="monospace"
                  alignmentBaseline="middle"
                  className="opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  {formatValue(item.value)}
                </text>

                {/* Y-axis label */}
                <text
                  x={-8}
                  y={y}
                  fill="#334155"
                  fontSize={11}
                  textAnchor="end"
                  alignmentBaseline="middle"
                >
                  {item.name.length > 25 ? item.name.substring(0, 25) + '...' : item.name}
                </text>

                {/* Category dot */}
                <circle
                  cx={-MARGIN.left + 10}
                  cy={y}
                  r={4}
                  fill={color}
                />
              </g>
            )
          })}
        </g>
      </svg>

      {/* Legend */}
      <div className="mt-4 flex flex-wrap items-center justify-center gap-4">
        {Object.entries(CATEGORY_COLORS).map(([cat, color]) => (
          <div key={cat} className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
            <span className="text-xs text-slate-600">{cat}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
