/**
 * Format a number as Brazilian Real currency
 */
export function formatCurrency(value, decimals = 2) {
  if (value === null || value === undefined || isNaN(value)) {
    return 'R$ 0,00'
  }

  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value)
}

/**
 * Format a number with thousand separators
 */
export function formatNumber(value, decimals = 0) {
  if (value === null || value === undefined || isNaN(value)) {
    return '0'
  }

  return new Intl.NumberFormat('pt-BR', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value)
}

/**
 * Format a number in compact notation (K, M, B)
 */
export function formatCompact(value) {
  if (value === null || value === undefined || isNaN(value)) {
    return '0'
  }

  const absValue = Math.abs(value)

  if (absValue >= 1e9) {
    return (value / 1e9).toFixed(1).replace('.', ',') + ' bi'
  }
  if (absValue >= 1e6) {
    return (value / 1e6).toFixed(1).replace('.', ',') + ' mi'
  }
  if (absValue >= 1e3) {
    return (value / 1e3).toFixed(1).replace('.', ',') + ' mil'
  }

  return value.toFixed(0)
}

/**
 * Format a percentage value
 */
export function formatPercent(value, decimals = 1) {
  if (value === null || value === undefined || isNaN(value)) {
    return '0%'
  }

  const sign = value > 0 ? '+' : ''
  return sign + value.toFixed(decimals).replace('.', ',') + '%'
}

/**
 * Format a period string (YYYY-MM) to readable format
 */
export function formatPeriod(period) {
  if (!period) return ''

  const months = [
    'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
    'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'
  ]

  const parts = period.split('-')
  if (parts.length === 2) {
    const year = parts[0]
    const month = parseInt(parts[1], 10) - 1
    return `${months[month]}/${year}`
  }

  return period
}

/**
 * Format a period string to full format
 */
export function formatPeriodFull(period) {
  if (!period) return ''

  const months = [
    'Janeiro', 'Fevereiro', 'Marco', 'Abril', 'Maio', 'Junho',
    'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
  ]

  const parts = period.split('-')
  if (parts.length === 2) {
    const year = parts[0]
    const month = parseInt(parts[1], 10) - 1
    return `${months[month]} de ${year}`
  }

  return period
}

/**
 * Get variation badge class based on value
 */
export function getVariationClass(value) {
  if (value > 0) return 'badge-green'
  if (value < 0) return 'badge-red'
  return 'badge-yellow'
}

/**
 * Calculate percentage variation
 */
export function calculateVariation(current, previous) {
  if (!previous || previous === 0) return null
  return ((current - previous) / previous) * 100
}

/**
 * Category colors
 */
export const CATEGORY_COLORS = {
  'Graos': '#22c55e',
  'Hortalicas': '#f59e0b',
  'Frutas': '#ec4899',
  'Pecuaria': '#8b5cf6',
  'Insumos': '#06b6d4',
  'Florestal': '#14b8a6',
  'Outros': '#64748b',
}

/**
 * Get color for category
 */
export function getCategoryColor(category) {
  return CATEGORY_COLORS[category] || '#64748b'
}

/**
 * Chart color palette
 */
export const CHART_COLORS = [
  '#f59e0b', // amber
  '#22c55e', // green
  '#3b82f6', // blue
  '#ec4899', // pink
  '#8b5cf6', // violet
  '#14b8a6', // teal
  '#f97316', // orange
  '#06b6d4', // cyan
  '#a855f7', // purple
  '#ef4444', // red
]

/**
 * Get chart color by index
 */
export function getChartColor(index) {
  return CHART_COLORS[index % CHART_COLORS.length]
}

/**
 * Map gradient for choropleth
 */
export const MAP_GRADIENT = [
  '#fffbeb',
  '#fef3c7',
  '#fde68a',
  '#fcd34d',
  '#fbbf24',
  '#f59e0b',
  '#d97706',
]

/**
 * Get map color based on value and range
 */
export function getMapColor(value, min, max) {
  if (!value || !max || max === min) return MAP_GRADIENT[0]

  const normalized = (value - min) / (max - min)
  const index = Math.min(
    Math.floor(normalized * MAP_GRADIENT.length),
    MAP_GRADIENT.length - 1
  )

  return MAP_GRADIENT[index]
}
