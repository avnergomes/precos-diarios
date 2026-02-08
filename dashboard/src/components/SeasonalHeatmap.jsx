import { useMemo } from 'react'
import { formatCurrency } from '../utils/format'

const MONTHS = [
  'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
  'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'
]

/**
 * SeasonalHeatmap - Visualize seasonal price patterns
 * Displays a heatmap of months (rows) vs years (columns)
 * Uses per-year normalization to highlight seasonal patterns within each year
 */
export default function SeasonalHeatmap({
  data = [],
  title = 'Sazonalidade de Preços',
  description,
  height = 350,
  onCellClick,
  selectedMonth,
  selectedYear,
}) {
  // Process data into month x year matrix with per-year min/max
  const { matrix, years, yearStats, globalMin, globalMax } = useMemo(() => {
    if (!data || data.length === 0) {
      return { matrix: {}, years: [], yearStats: {}, globalMin: 0, globalMax: 0 }
    }

    // Group by year-month and calculate averages
    const grouped = {}

    data.forEach(record => {
      const year = record.a || record.ano
      const month = getRecordMonth(record)
      const price = record.pm || record.preco_medio

      if (!year || !price || price <= 0) return

      const key = `${year}-${month}`
      if (!grouped[key]) {
        grouped[key] = { sum: 0, count: 0, year, month }
      }
      grouped[key].sum += price
      grouped[key].count++
    })

    // Build matrix
    const matrix = {}
    const yearsSet = new Set()
    const yearValues = {} // Store all values per year for min/max calculation

    Object.entries(grouped).forEach(([key, stats]) => {
      const { year, month } = stats
      const avg = stats.sum / stats.count

      yearsSet.add(year)

      if (!matrix[month]) {
        matrix[month] = {}
      }
      matrix[month][year] = avg

      // Track values per year
      if (!yearValues[year]) {
        yearValues[year] = []
      }
      yearValues[year].push(avg)
    })

    const years = [...yearsSet].sort((a, b) => a - b)

    // Calculate min/max for each year
    const yearStats = {}
    let globalMin = Infinity
    let globalMax = -Infinity

    years.forEach(year => {
      const values = yearValues[year] || []
      if (values.length > 0) {
        const min = Math.min(...values)
        const max = Math.max(...values)
        yearStats[year] = { min, max }
        globalMin = Math.min(globalMin, min)
        globalMax = Math.max(globalMax, max)
      }
    })

    return {
      matrix,
      years,
      yearStats,
      globalMin: globalMin === Infinity ? 0 : globalMin,
      globalMax: globalMax === -Infinity ? 0 : globalMax,
    }
  }, [data])

  // Color scale function (green to red) - normalized within each year
  const getColor = (value, year) => {
    if (!value || value <= 0) return '#f3f4f6' // gray-100 for no data

    const stats = yearStats[year]
    if (!stats) return '#f3f4f6'

    const { min, max } = stats
    const range = max - min || 1
    const normalized = (value - min) / range

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
        {description && (
          <p className="text-sm text-dark-500 mb-4">{description}</p>
        )}
        <div className="flex items-center justify-center text-dark-400" style={{ height: height - 80 }}>
          Sem dados disponíveis para o heatmap
        </div>
      </div>
    )
  }

  const cellWidth = Math.max(40, Math.min(60, (800 - 60) / years.length))
  const cellHeight = 28

  return (
    <div className="card p-6">
      <h3 className="chart-title">{title}</h3>
      {description && (
        <p className="text-sm text-dark-500 mb-4">{description}</p>
      )}

      <div className="overflow-x-auto overflow-y-visible">
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
            const tooltipBelow = monthIndex < 2
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
                  const stats = yearStats[year]
                  const isSelected = selectedMonth === month && selectedYear === year

                  return (
                    <div
                      key={`${month}-${year}`}
                      className="relative group"
                      style={{
                        width: cellWidth,
                        height: cellHeight,
                        padding: 1,
                      }}
                      onClick={() => hasData && onCellClick?.({ mes: month, ano: year })}
                    >
                      <div
                        className={`w-full h-full rounded transition-all duration-200 hover:ring-2 hover:ring-primary-400 hover:ring-offset-1 ${
                          onCellClick && hasData ? 'cursor-pointer' : ''
                        } ${isSelected ? 'ring-2 ring-primary-600 ring-offset-1' : ''}`}
                        style={{
                          backgroundColor: getColor(value, year),
                          opacity: (selectedMonth && selectedYear && !isSelected) ? 0.5 : 1,
                        }}
                      />

                      {/* Tooltip */}
                      {hasData && (
                        <div
                          className={`absolute left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity z-20 pointer-events-none ${
                            tooltipBelow ? 'top-full mt-2' : 'bottom-full mb-2'
                          }`}
                        >
                          <div className="bg-dark-800 text-white text-xs px-2 py-1 rounded shadow-lg whitespace-nowrap">
                            <div className="font-medium">{monthName} {year}</div>
                            <div>{formatCurrency(value)}</div>
                            {stats && (
                              <div className="text-dark-300 text-[10px] mt-1">
                                Ano: {formatCurrency(stats.min)} - {formatCurrency(stats.max)}
                              </div>
                            )}
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
        <span>Menor preço do ano</span>
        <div className="flex gap-0.5">
          {[0, 0.25, 0.5, 0.75, 1].map((t, i) => (
            <div
              key={t}
              className="w-6 h-4 rounded-sm"
              style={{
                backgroundColor: getColorForLegend(t),
              }}
            />
          ))}
        </div>
        <span>Maior preço do ano</span>
      </div>

      {/* Info text */}
      <div className="mt-2 text-center text-xs text-dark-400">
        Cores normalizadas por ano - destaca sazonalidade dentro de cada ano
      </div>

      {selectedMonth && selectedYear && (
        <p className="text-xs text-center text-primary-600 mt-2 font-medium">
          Selecionado: {MONTHS[selectedMonth - 1]} {selectedYear}
        </p>
      )}

      {onCellClick && !selectedMonth && (
        <p className="text-xs text-center text-dark-400 mt-2">
          Clique em uma célula para filtrar por mês/ano
        </p>
      )}
    </div>
  )
}

// Fixed color for legend (not dependent on data)
function getColorForLegend(normalized) {
  if (normalized < 0.5) {
    const t = normalized * 2
    const r = Math.round(34 + t * (234 - 34))
    const g = Math.round(197 + t * (179 - 197))
    const b = Math.round(94 + t * (8 - 94))
    return `rgb(${r}, ${g}, ${b})`
  } else {
    const t = (normalized - 0.5) * 2
    const r = Math.round(234 + t * (239 - 234))
    const g = Math.round(179 - t * 111)
    const b = Math.round(8 + t * (68 - 8))
    return `rgb(${r}, ${g}, ${b})`
  }
}

function getRecordMonth(record) {
  if (record?.m) return record.m
  if (record?.mes) return record.mes
  if (record?.d && typeof record.d === 'string') {
    const parts = record.d.split('-')
    if (parts.length >= 2) {
      const month = parseInt(parts[1], 10)
      if (!Number.isNaN(month)) return month
    }
  }
  return 1
}
