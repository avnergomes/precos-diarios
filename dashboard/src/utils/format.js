// ATLAS-A11Y-HEX-SWEPT
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
 * Format a currency with unit label
 */
export function formatCurrencyWithUnit(value, unitLabel = 'unid.') {
  return `${formatCurrency(value)} / ${unitLabel}`
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
    'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
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
  'Graos': '#0072B2',
  'Grãos': '#0072B2',
  'Cafe': '#a16207',
  'Café': '#a16207',
  'Hortalicas': '#c89b3c',
  'Hortaliças': '#c89b3c',
  'Mandioca': '#a87f2d',
  'Frutas': '#ec4899',
  'Pecuaria': '#CC79A7',
  'Pecuária': '#CC79A7',
  'Insumos': '#06b6d4',
  'Florestal': '#14b8a6',
  'Outros': '#6e6453',
}

/**
 * Format category names with accents for display
 */
export function formatCategoryName(category) {
  if (!category) return ''

  const labels = {
    Graos: 'Grãos',
    Pecuaria: 'Pecuária',
    Hortalicas: 'Hortaliças',
    Cafe: 'Café',
  }

  return labels[category] || category
}

/**
 * Format ISO date/time for display in PT-BR
 */
export function formatDateTime(dateStr) {
  if (!dateStr) return ''
  const raw = typeof dateStr === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(dateStr)
    ? dateStr + 'T12:00:00'
    : dateStr
  const date = new Date(raw)
  if (Number.isNaN(date.getTime())) return ''

  return date.toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/**
 * Get color for category
 */
export function getCategoryColor(category) {
  return CATEGORY_COLORS[category] || '#6e6453'
}

/**
 * Chart color palette
 */
// Legacy palette kept for getChartColor's internal use; the canonical
// CHART_COLORS object is re-exported below from chart-palette (daltonic-safe).
import { ATLAS_CATEGORICAL as _ATLAS_CAT } from './chart-palette.js'
const LEGACY_CHART_COLORS = _ATLAS_CAT

/**
 * Get chart color by index
 */
export function getChartColor(index) {
  return LEGACY_CHART_COLORS[index % LEGACY_CHART_COLORS.length]
}

/**
 * Map gradient for choropleth
 */
export const MAP_GRADIENT = [
  '#fffbeb',
  '#fef3c7',
  '#fde68a',
  '#fcd34d',
  '#e0b850',
  '#c89b3c',
  '#a87f2d',
]

/**
 * Unit labels per product (fallback mapping)
 */
export const PRODUCT_UNITS = {
  // Grãos - sc 60 Kg
  'Soja industrial tipo 1': 'sc 60 Kg',
  'Milho amarelo tipo 1': 'sc 60 Kg',
  'Milho comum': 'sc 60 Kg',
  'Trigo pão': 'sc 60 Kg',
  'Trigo': 'sc 60 Kg',
  'Feijão preto tipo 1': 'sc 60 Kg',
  'Feijão carioca tipo 1': 'sc 60 Kg',
  'Feijão de cor tipo 1': 'sc 60 Kg',
  'Arroz em casca tipo 1': 'sc 60 Kg',
  'Arroz irrigado': 'sc 60 Kg',
  'Arroz sequeiro': 'sc 60 Kg',
  'Café beneficiado bebida dura tipo 6': 'sc 60 Kg',
  // Café em coco - kg renda
  'Café em coco': 'kg renda',
  // Pecuária - arroba ou kg
  'Boi em pé': 'arroba',
  'Vaca em pé': 'arroba',
  'Algodão em caroço': 'arroba',
  'Suíno em pé tipo carne': 'kg',
  'Suíno em pé tipo carne não integrado': 'kg',
  'Frango de corte': 'kg',
  // Florestal - arroba
  'Erva-mate': 'arroba',
  'Erva-mate folha em barranco': 'arroba',
  // Hortaliças - tonelada
  'Mandioca industrial': 'tonelada',
  // Default
  default: 'unid.',
}

/**
 * Get unit label for a product
 */
export function getUnitForProduct(produto) {
  if (!produto) return PRODUCT_UNITS.default

  // Direct lookup
  if (PRODUCT_UNITS[produto]) {
    return PRODUCT_UNITS[produto]
  }

  // Try case-insensitive partial match
  const prodLower = produto.toLowerCase()
  for (const [key, unit] of Object.entries(PRODUCT_UNITS)) {
    if (key !== 'default' && key.toLowerCase() === prodLower) {
      return unit
    }
  }

  return PRODUCT_UNITS.default
}

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

// ATLAS-PALETTE-V1
// Re-export the shared Atlas Editorial palette (daltonic-safe).
export { CHART_COLORS, MAP_GRADIENTS, ATLAS_CATEGORICAL, ATLAS_FOREST, ATLAS_WATER, ATLAS_CLAY, ATLAS_EARTH, ATLAS_HARVEST, ATLAS_DIVERGING, ATLAS_CHROME, categoricalColor, sequentialColor } from './chart-palette.js';
