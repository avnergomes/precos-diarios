import { useMemo } from 'react'
import * as d3 from 'd3'

const MARGIN = { top: 30, right: 30, bottom: 40, left: 60 }

// Color scale for years (green gradient)
const YEAR_COLORS = [
  '#dcfce7', '#bbf7d0', '#86efac', '#4ade80', '#22c55e',
  '#16a34a', '#15803d', '#166534', '#14532d', '#052e16'
]

export default function RidgelineChart({
  data,
  title = "Distribuição de Preços por Ano",
  width = 700,
  height = 450
}) {
  const chartData = useMemo(() => {
    if (!data) return null

    // Group data by year
    const byYear = {}
    Object.entries(data).forEach(([period, info]) => {
      const year = period.substring(0, 4)
      if (!byYear[year]) byYear[year] = []
      byYear[year].push(info.media || info)
    })

    const years = Object.keys(byYear).filter(y => byYear[y].length >= 6).sort()
    if (years.length === 0) return null

    // Calculate global min/max for consistent scale
    const allValues = years.flatMap(y => byYear[y])
    const minVal = d3.min(allValues) * 0.9
    const maxVal = d3.max(allValues) * 1.1

    // Create kernel density estimates for each year
    const kde = kernelDensityEstimator(
      kernelEpanechnikov(20),
      d3.range(minVal, maxVal, (maxVal - minVal) / 80)
    )

    const densities = years.map((year, idx) => ({
      year,
      density: kde(byYear[year]),
      mean: d3.mean(byYear[year]),
      count: byYear[year].length,
      colorIdx: Math.floor((idx / (years.length - 1)) * (YEAR_COLORS.length - 1))
    }))

    return { densities, minVal, maxVal, years }
  }, [data])

  if (!chartData) {
    return (
      <div className="bg-white rounded-xl shadow-lg p-6">
        <h3 className="text-lg font-semibold text-slate-700 mb-4">{title}</h3>
        <div className="h-64 flex items-center justify-center text-slate-400">
          Dados insuficientes para análise de distribuição
        </div>
      </div>
    )
  }

  const innerWidth = width - MARGIN.left - MARGIN.right
  const innerHeight = height - MARGIN.top - MARGIN.bottom

  const { densities, minVal, maxVal, years } = chartData

  // Find max density for scaling
  const maxDensity = d3.max(densities.flatMap(d => d.density.map(p => p[1])))

  // Scales
  const xScale = d3.scaleLinear()
    .domain([minVal, maxVal])
    .range([0, innerWidth])

  const yScale = d3.scaleBand()
    .domain(years)
    .range([0, innerHeight])
    .paddingInner(0.1)

  // Height scale for density curves
  const heightScale = d3.scaleLinear()
    .domain([0, maxDensity])
    .range([0, yScale.bandwidth() * 1.8])

  // Area generator
  const areaGenerator = d3.area()
    .x(d => xScale(d[0]))
    .y0(0)
    .y1(d => -heightScale(d[1]))
    .curve(d3.curveBasis)

  const formatValue = (v) => {
    if (v >= 1000) return `R$${(v/1000).toFixed(0)}K`
    return `R$${v.toFixed(0)}`
  }

  return (
    <div className="bg-white rounded-xl shadow-lg p-6">
      <h3 className="text-lg font-semibold text-slate-700 mb-4">{title}</h3>

      <svg width={width} height={height}>
        <defs>
          {densities.map((yearData, i) => (
            <linearGradient
              key={`gradient-${yearData.year}`}
              id={`ridge-gradient-${yearData.year}`}
              x1="0%"
              y1="0%"
              x2="0%"
              y2="100%"
            >
              <stop offset="0%" stopColor={YEAR_COLORS[yearData.colorIdx]} stopOpacity={0.9} />
              <stop offset="100%" stopColor={YEAR_COLORS[yearData.colorIdx]} stopOpacity={0.3} />
            </linearGradient>
          ))}
        </defs>

        <g transform={`translate(${MARGIN.left}, ${MARGIN.top})`}>
          {/* X-axis */}
          <g transform={`translate(0, ${innerHeight})`}>
            {xScale.ticks(8).map((tick, i) => (
              <g key={`x-tick-${i}`} transform={`translate(${xScale(tick)}, 0)`}>
                <line y1={0} y2={5} stroke="#94a3b8" />
                <text
                  y={18}
                  fill="#64748b"
                  fontSize={10}
                  textAnchor="middle"
                >
                  {formatValue(tick)}
                </text>
              </g>
            ))}
            <text
              x={innerWidth / 2}
              y={35}
              fill="#475569"
              fontSize={11}
              textAnchor="middle"
            >
              Preço Médio (R$)
            </text>
          </g>

          {/* Vertical grid lines */}
          {xScale.ticks(8).map((tick, i) => (
            <line
              key={`vgrid-${i}`}
              x1={xScale(tick)}
              x2={xScale(tick)}
              y1={0}
              y2={innerHeight}
              stroke="#f1f5f9"
              strokeDasharray="4,4"
            />
          ))}

          {/* Ridge lines */}
          {densities.map((yearData, i) => {
            const yOffset = yScale(yearData.year) + yScale.bandwidth()
            const color = YEAR_COLORS[yearData.colorIdx]

            return (
              <g key={yearData.year} transform={`translate(0, ${yOffset})`} className="group">
                {/* Fill area */}
                <path
                  d={areaGenerator(yearData.density)}
                  fill={`url(#ridge-gradient-${yearData.year})`}
                  className="transition-opacity"
                />

                {/* Line */}
                <path
                  d={d3.line()
                    .x(d => xScale(d[0]))
                    .y(d => -heightScale(d[1]))
                    .curve(d3.curveBasis)(yearData.density)}
                  fill="none"
                  stroke={d3.color(color).darker(0.5).toString()}
                  strokeWidth={1.5}
                />

                {/* Mean line */}
                <line
                  x1={xScale(yearData.mean)}
                  x2={xScale(yearData.mean)}
                  y1={0}
                  y2={-heightScale(maxDensity) * 0.7}
                  stroke={d3.color(color).darker(1).toString()}
                  strokeWidth={1}
                  strokeDasharray="3,3"
                  className="opacity-0 group-hover:opacity-100 transition-opacity"
                />

                {/* Year label */}
                <text
                  x={-8}
                  y={0}
                  fill="#475569"
                  fontSize={11}
                  fontWeight="500"
                  textAnchor="end"
                  alignmentBaseline="middle"
                >
                  {yearData.year}
                </text>

                {/* Stats on hover */}
                <text
                  x={innerWidth - 5}
                  y={-5}
                  fill="#334155"
                  fontSize={10}
                  textAnchor="end"
                  className="opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  média: {formatValue(yearData.mean)} | n={yearData.count}
                </text>
              </g>
            )
          })}
        </g>
      </svg>

      {/* Summary */}
      <div className="mt-4 pt-4 border-t flex items-center justify-between text-sm">
        <div className="text-slate-500">
          <span className="font-medium">{years.length}</span> anos analisados
        </div>
        <div className="flex items-center gap-2">
          <span className="text-slate-500">Evolução:</span>
          <div className="flex">
            {YEAR_COLORS.slice(0, 6).map((color, i) => (
              <div key={i} className="w-4 h-3" style={{ backgroundColor: color }} />
            ))}
          </div>
          <span className="text-xs text-slate-400">antigo → recente</span>
        </div>
      </div>
    </div>
  )
}

// Kernel density estimator helper functions
function kernelDensityEstimator(kernel, X) {
  return function(V) {
    return X.map(x => [x, d3.mean(V, v => kernel(x - v))])
  }
}

function kernelEpanechnikov(k) {
  return function(v) {
    return Math.abs(v /= k) <= 1 ? 0.75 * (1 - v * v) / k : 0
  }
}
