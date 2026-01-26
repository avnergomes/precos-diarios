import { useState, useEffect, useMemo } from 'react'

// API URL from environment variable or fallback to local data
const API_URL = import.meta.env.VITE_API_URL
const DATA_BASE_PATH = API_URL
  ? `${API_URL}/api/data/`
  : import.meta.env.BASE_URL + 'data/'

export function useData() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true)
        setError(null)

        const [aggregated, detailed, timeseries, filters] = await Promise.all([
          fetch(DATA_BASE_PATH + 'aggregated.json').then(r => {
            if (!r.ok) throw new Error('Failed to load aggregated.json')
            return r.json()
          }),
          fetch(DATA_BASE_PATH + 'detailed.json').then(r => {
            if (!r.ok) throw new Error('Failed to load detailed.json')
            return r.json()
          }),
          fetch(DATA_BASE_PATH + 'timeseries.json').then(r => {
            if (!r.ok) throw new Error('Failed to load timeseries.json')
            return r.json()
          }),
          fetch(DATA_BASE_PATH + 'filters.json').then(r => {
            if (!r.ok) throw new Error('Failed to load filters.json')
            return r.json()
          }),
        ])

        const normalizedFilters = normalizeFilters(filters, aggregated, detailed)

        setData({
          aggregated,
          detailed,
          timeseries,
          filters: normalizedFilters,
        })
      } catch (err) {
        console.error('Error loading data:', err)
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    loadData()
  }, [])

  return { data, loading, error }
}

function normalizeFilters(filtersJson, aggregated, detailed) {
  const anos = new Set()
  const categorias = new Set()
  const produtos = new Set()
  const categoryProducts = {}

  if (filtersJson?.category_products) {
    Object.entries(filtersJson.category_products).forEach(([cat, items]) => {
      if (!cat) return
      categorias.add(cat)
      categoryProducts[cat] = items
      items.forEach((item) => produtos.add(item))
    })
  }

  if (aggregated?.by_product) {
    Object.entries(aggregated.by_product).forEach(([produto, stats]) => {
      if (produto) produtos.add(produto)
      if (stats?.categoria) {
        categorias.add(stats.categoria)
        if (!categoryProducts[stats.categoria]) {
          categoryProducts[stats.categoria] = []
        }
        if (!categoryProducts[stats.categoria].includes(produto)) {
          categoryProducts[stats.categoria].push(produto)
        }
      }
    })
  }

  if (aggregated?.by_year) {
    Object.keys(aggregated.by_year).forEach((year) => {
      const numeric = parseInt(year, 10)
      if (!Number.isNaN(numeric)) anos.add(numeric)
    })
  }

  if (anos.size === 0 && detailed?.records?.length) {
    detailed.records.forEach((record) => {
      if (record?.a) anos.add(record.a)
    })
  }

  return {
    anos: Array.from(anos).sort((a, b) => a - b),
    categorias: Array.from(categorias).sort((a, b) => a.localeCompare(b)),
    produtos: Array.from(produtos).sort((a, b) => a.localeCompare(b)),
    category_products: categoryProducts,
  }
}

export function useFilteredData(data, filters) {
  return useMemo(() => {
    if (!data?.detailed?.records) return []

    let records = data.detailed.records

    // Filter by year range
    if (filters.anoMin) {
      records = records.filter(r => r.a >= filters.anoMin)
    }
    if (filters.anoMax) {
      records = records.filter(r => r.a <= filters.anoMax)
    }

    // Filter by category
    if (filters.categoria) {
      records = records.filter(r => r.c === filters.categoria)
    }

    // Filter by product
    if (filters.produto) {
      records = records.filter(r => r.p === filters.produto)
    }

    return records
  }, [data, filters])
}

export function useAggregations(filteredData, data) {
  return useMemo(() => {
    if (!filteredData || filteredData.length === 0) {
      return {
        totalRecords: 0,
        avgPrice: 0,
        minPrice: 0,
        maxPrice: 0,
        uniqueProducts: 0,
        uniqueCategories: 0,
        yoyChange: 0,
        topProducts: [],
        byCategory: {},
        sparklineData: {},
      }
    }

    // Calculate aggregations from filtered data
    const prices = filteredData
      .filter(r => r.pm && r.pm > 0)
      .map(r => r.pm)

    const avgPrice = prices.length > 0
      ? prices.reduce((a, b) => a + b, 0) / prices.length
      : 0

    const minPrice = prices.length > 0 ? Math.min(...prices) : 0
    const maxPrice = prices.length > 0 ? Math.max(...prices) : 0

    const products = new Set(filteredData.map(r => r.p))
    const categories = new Set(filteredData.map(r => r.c))

    // Calculate YoY (Year over Year) change
    const years = [...new Set(filteredData.map(r => r.a))].sort((a, b) => b - a)
    let yoyChange = 0
    if (years.length >= 2) {
      const currentYear = years[0]
      const prevYear = years[1]

      const currentYearPrices = filteredData
        .filter(r => r.a === currentYear && r.pm > 0)
        .map(r => r.pm)
      const prevYearPrices = filteredData
        .filter(r => r.a === prevYear && r.pm > 0)
        .map(r => r.pm)

      if (currentYearPrices.length > 0 && prevYearPrices.length > 0) {
        const currentAvg = currentYearPrices.reduce((a, b) => a + b, 0) / currentYearPrices.length
        const prevAvg = prevYearPrices.reduce((a, b) => a + b, 0) / prevYearPrices.length
        yoyChange = prevAvg > 0 ? ((currentAvg - prevAvg) / prevAvg) * 100 : 0
      }
    }

    // Group by product for top products with YoY variation
    const productStats = {}
    const productByYear = {}

    filteredData.forEach(r => {
      if (!r.p) return
      if (!productStats[r.p]) {
        productStats[r.p] = { count: 0, sum: 0, categoria: r.c, unidade: r.u || null }
        productByYear[r.p] = {}
      }
      if (!productStats[r.p].unidade && r.u) {
        productStats[r.p].unidade = r.u
      }
      productStats[r.p].count++
      if (r.pm) {
        productStats[r.p].sum += r.pm
        // Track by year for variation calculation
        if (!productByYear[r.p][r.a]) {
          productByYear[r.p][r.a] = { sum: 0, count: 0 }
        }
        productByYear[r.p][r.a].sum += r.pm
        productByYear[r.p][r.a].count++
      }
    })

    // Calculate product variations and sparkline data
    const sparklineData = {}

    const topProducts = Object.entries(productStats)
      .map(([produto, stats]) => {
        // Calculate YoY variation for this product
        const productYears = Object.keys(productByYear[produto] || {}).map(Number).sort((a, b) => b - a)
        let variacao = null

        if (productYears.length >= 2) {
          const currentYear = productYears[0]
          const prevYear = productYears[1]
          const current = productByYear[produto][currentYear]
          const prev = productByYear[produto][prevYear]

          if (current && prev && current.count > 0 && prev.count > 0) {
            const currentAvg = current.sum / current.count
            const prevAvg = prev.sum / prev.count
            variacao = prevAvg > 0 ? ((currentAvg - prevAvg) / prevAvg) * 100 : null
          }
        }

        // Generate sparkline data (monthly averages, last 12 months)
        const monthlyData = {}
        filteredData
          .filter(r => r.p === produto && r.pm > 0)
          .forEach(r => {
            const month = getRecordMonth(r)
            const key = `${r.a}-${String(month).padStart(2, '0')}`
            if (!monthlyData[key]) {
              monthlyData[key] = { sum: 0, count: 0 }
            }
            monthlyData[key].sum += r.pm
            monthlyData[key].count++
          })

        sparklineData[produto] = Object.entries(monthlyData)
          .map(([period, s]) => ({ period, value: s.sum / s.count }))
          .sort((a, b) => a.period.localeCompare(b.period))
          .slice(-12)

        return {
          produto,
          categoria: stats.categoria,
          unidade: stats.unidade,
          media: stats.count > 0 ? stats.sum / stats.count : 0,
          registros: stats.count,
          variacao,
        }
      })
      .sort((a, b) => b.registros - a.registros)

    // Group by category
    const byCategory = {}
    filteredData.forEach(r => {
      if (!r.c) return
      if (!byCategory[r.c]) {
        byCategory[r.c] = {
          count: 0,
          sum: 0,
          min: Infinity,
          max: -Infinity,
          products: new Set(),
        }
      }
      byCategory[r.c].count++
      if (r.p) byCategory[r.c].products.add(r.p)
      if (r.pm) {
        byCategory[r.c].sum += r.pm
        byCategory[r.c].min = Math.min(byCategory[r.c].min, r.pm)
        byCategory[r.c].max = Math.max(byCategory[r.c].max, r.pm)
      }
    })

    Object.keys(byCategory).forEach(cat => {
      const stats = byCategory[cat]
      byCategory[cat] = {
        media: stats.count > 0 ? stats.sum / stats.count : 0,
        minimo: stats.min === Infinity ? 0 : stats.min,
        maximo: stats.max === -Infinity ? 0 : stats.max,
        registros: stats.count,
        produtos: stats.products.size,
      }
    })

    return {
      totalRecords: filteredData.length,
      avgPrice,
      minPrice,
      maxPrice,
      uniqueProducts: products.size,
      uniqueCategories: categories.size,
      yoyChange,
      topProducts,
      byCategory,
      sparklineData,
    }
  }, [filteredData, data])
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

// Generate time series from filtered data
export function useFilteredTimeSeries(filteredData) {
  return useMemo(() => {
    if (!filteredData || filteredData.length === 0) return {}

    const byPeriod = {}

    filteredData.forEach(r => {
      if (!r.a || !r.pm) return
      const month = getRecordMonth(r)
      const period = `${r.a}-${String(month).padStart(2, '0')}`

      if (!byPeriod[period]) {
        byPeriod[period] = { sum: 0, count: 0, min: Infinity, max: -Infinity }
      }

      byPeriod[period].sum += r.pm
      byPeriod[period].count++
      byPeriod[period].min = Math.min(byPeriod[period].min, r.pm)
      byPeriod[period].max = Math.max(byPeriod[period].max, r.pm)
    })

    const result = {}
    Object.entries(byPeriod).forEach(([period, stats]) => {
      result[period] = {
        media: stats.count > 0 ? stats.sum / stats.count : 0,
        min: stats.min === Infinity ? 0 : stats.min,
        max: stats.max === -Infinity ? 0 : stats.max,
        count: stats.count,
      }
    })

    return result
  }, [filteredData])
}
