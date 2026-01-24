import { useMemo } from 'react'
import { formatCurrency } from '../utils/format'

const MONTHS = [
  'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
  'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'
]

/**
 * SeasonalHeatmap - Visualize seasonal price patterns
 * Displays a heatmap of months (rows) vs years (columns)
 */
export default function SeasonalHeatmap({
  data = [],
  title = 'Sazonalidade de Precos',
  height = 350,
}) {
  // Process data into month x year matrix
  const { matrix, years, minPrice, maxPrice } = useMemo(() => {
    if (!data || data.length === 0) {
      return { matrix: {}, years: [], minPrice: 0, maxPrice: 0 }
    }

    // Group by year-month and calculate averages
    const grouped = {}
    let min = Infinity
    let max = -Infinity

    data.forEach(record => {
      const year = record.a || record.ano
      const month = record.m || record.mes || 1
      const price = record.pm || record.preco_medio

      if (!year || !price || price <= 0) return

      const key = `${year}-${month}`
      if (!grouped[key]) {
        grouped[key] = { sum: 0, count: 0 }
      }
      grouped[key].sum += price
      grouped[key].count++
    })

    // Build matrix and find min/max
    const matrix = {}
    const yearsSet = new Set()

    Object.entries(grouped).forEach(([key, stats]) => {
      const [year, month] = key.split('-').map(Number)
      const avg = stats.sum / stats.count

      yearsSet.add(year)

      if (!matrix[month]) {
        matrix[month] = {}
      }
      matrix[month][year] = avg

      min = Math.min(min, avg)
      max = Math.max(max, avg)
    })

    const years = [...yearsSet].sort((a, b) => a - b)

    return {
      matrix,
      years,
      minPrice: min === Infinity ? 0 : min,
      maxPrice: max === -Infinity ? 0 : max,
    }
  }, [data])

  // Color scale function (green to red)
  const getColor = (value) => {
    if (!value || value <= 0) return '#f3f4f6' // gray-100 for no data

    const range = maxPrice - minPrice || 1
    const normalized = (value - minPrice) / range

    // Interpolate from green (low) to yellow (mid) to red (high)
    if (normalized < 0.5) {
      // Green to Yellow
      const t = normalized * 2
      const r = Math.round(34 + t * (234 - 34))
      const g = Math.round(197 + t * (179 - 197))
      const b = Math.round(94 + t * (8 - 94))
      return `rgb(${r}, ${g}, ${b})`
    } else {
      // Yellow to Red
      const t = (normalized - 0.5) * 2
      const r = Math.round(234 + t * (239 - 234))
      const g = Math.round(179 - t * 111)
      const b = Math.round(8 + t * (68 - 8))
      return `rgb(${r}, ${g}, ${b})`
    }
  }

  if (years.length === 0) {
    return (
      <div className="card p-6">
        <h3 className="chart-title">{title}</h3>
        <div className="flex items-center justify-center text-dark-400" style={{ height: height - 80 }}>
          Sem dados disponiveis para o heatmap
        </div>
      </div>
    )
  }

  const cellWidth = Math.max(40, Math.min(60, (800 - 60) / years.length))
  const cellHeight = 28

  return (
    <div className="card p-6">
      <h3 className="chart-title">{title}</h3>

      <div className="overflow-x-auto">
        <div className="inline-block min-w-full">
          {/* Header row with years */}
          <div className="flex">
            <div className="w-12 flex-shrink-0" /> {/* Empty corner */}
            {years.map(year => (
              <div
                key={year}
                className="text-xs font-medium text-dark-500 text-center"
                style={{ width: cellWidth }}
              >
                {year}
              </div>
            ))}
          </div>

          {/* Month rows */}
          {MONTHS.map((monthName, monthIndex) => {
            const month = monthIndex + 1
            return (
              <div key={month} className="flex items-center">
                {/* Month label */}
                <div className="w-12 flex-shrink-0 text-xs font-medium text-dark-600 text-right pr-2">
                  {monthName}
                </div>

                {/* Year cells */}
                {years.map(year => {
                  const value = matrix[month]?.[year]
                  const hasData = value && value > 0

                  return (
                    <div
                      key={`${month}-${year}`}
                      className="relative group"
                      style={{
                        width: cellWidth,
                        height: cellHeight,
                        padding: 1,
                      }}
                    >
                      <div
                        className="w-full h-full rounded transition-all duration-200 hover:ring-2 hover:ring-primary-400 hover:ring-offset-1"
                        style={{
                          backgroundColor: getColor(value),
                        }}
                      />

                      {/* Tooltip */}
                      {hasData && (
                        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 opacity-0 group-hover:opacity-100 transition-opacity z-10 pointer-events-none">
                          <div className="bg-dark-800 text-white text-xs px-2 py-1 rounded shadow-lg whitespace-nowrap">
                            <div className="font-medium">{monthName} {year}</div>
                            <div>{formatCurrency(value)}</div>
                          </div>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            )
          })}
        </div>
      </div>

      {/* Legend */}
      <div className="mt-4 flex items-center justify-center gap-4 text-xs text-dark-500">
        <span>Menor preco</span>
        <div className="flex gap-0.5">
          {[0, 0.25, 0.5, 0.75, 1].map((t) => (
            <div
              key={t}
              className="w-6 h-4 rounded-sm"
              style={{
                backgroundColor: getColor(minPrice + t * (maxPrice - minPrice)),
              }}
            />
          ))}
        </div>
        <span>Maior preco</span>
      </div>

      {/* Price range info */}
      <div className="mt-2 text-center text-xs text-dark-400">
        Faixa: {formatCurrency(minPrice)} - {formatCurrency(maxPrice)}
      </div>
    </div>
  )
}
