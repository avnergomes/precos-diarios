/**
 * Sparkline - Mini line chart component for inline display in tables
 * Uses SVG for lightweight rendering
 */
export default function Sparkline({
  data = [],
  width = 80,
  height = 24,
  color = '#22c55e',
  showEndDot = true
}) {
  if (!data || data.length < 2) {
    return (
      <div
        className="flex items-center justify-center text-dark-300"
        style={{ width, height }}
      >
        <span className="text-xs">-</span>
      </div>
    )
  }

  const values = data.map(d => typeof d === 'object' ? d.value : d)
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1

  // Normalize values to fit in the SVG
  const padding = 2
  const chartWidth = width - padding * 2
  const chartHeight = height - padding * 2

  const points = values.map((value, index) => {
    const x = padding + (index / (values.length - 1)) * chartWidth
    const y = padding + chartHeight - ((value - min) / range) * chartHeight
    return { x, y, value }
  })

  // Create SVG path
  const pathD = points
    .map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`)
    .join(' ')

  // Calculate trend for color
  const firstValue = values[0]
  const lastValue = values[values.length - 1]
  const trend = lastValue >= firstValue ? 'up' : 'down'
  const trendColor = trend === 'up' ? '#22c55e' : '#ef4444'
  const finalColor = color === 'auto' ? trendColor : color

  return (
    <svg
      width={width}
      height={height}
      className="overflow-visible"
      style={{ display: 'block' }}
    >
      {/* Line */}
      <path
        d={pathD}
        fill="none"
        stroke={finalColor}
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* End dot */}
      {showEndDot && points.length > 0 && (
        <circle
          cx={points[points.length - 1].x}
          cy={points[points.length - 1].y}
          r={2.5}
          fill={finalColor}
        />
      )}
    </svg>
  )
}

/**
 * Generate sparkline data from time series
 */
export function generateSparklineData(records, productName, limit = 12) {
  if (!records || !productName) return []

  // Filter records for this product and sort by date
  const productRecords = records
    .filter(r => r.p === productName && r.pm > 0)
    .sort((a, b) => {
      // Sort by year and month
      if (a.a !== b.a) return a.a - b.a
      return (a.m || 0) - (b.m || 0)
    })

  // Group by year-month and calculate average
  const monthlyData = {}
  productRecords.forEach(r => {
    const key = `${r.a}-${String(r.m || 1).padStart(2, '0')}`
    if (!monthlyData[key]) {
      monthlyData[key] = { sum: 0, count: 0 }
    }
    monthlyData[key].sum += r.pm
    monthlyData[key].count++
  })

  // Convert to array and take last N months
  const data = Object.entries(monthlyData)
    .map(([period, stats]) => ({
      period,
      value: stats.sum / stats.count
    }))
    .sort((a, b) => a.period.localeCompare(b.period))
    .slice(-limit)

  return data
}
