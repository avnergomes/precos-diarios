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

        setData({
          aggregated,
          detailed,
          timeseries,
          filters,
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

    // Filter by regional
    if (filters.regional) {
      records = records.filter(r => r.r === filters.regional)
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
        uniqueRegions: 0,
        topProducts: [],
        byCategory: {},
        byRegional: {},
        byPeriod: {},
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
    const regions = new Set(filteredData.filter(r => r.r).map(r => r.r))

    // Group by product for top products
    const productStats = {}
    filteredData.forEach(r => {
      if (!r.p) return
      if (!productStats[r.p]) {
        productStats[r.p] = { count: 0, sum: 0, categoria: r.c }
      }
      productStats[r.p].count++
      if (r.pm) productStats[r.p].sum += r.pm
    })

    const topProducts = Object.entries(productStats)
      .map(([produto, stats]) => ({
        produto,
        categoria: stats.categoria,
        media: stats.count > 0 ? stats.sum / stats.count : 0,
        registros: stats.count,
      }))
      .sort((a, b) => b.registros - a.registros)
      .slice(0, 20)

    // Group by category
    const byCategory = {}
    filteredData.forEach(r => {
      if (!r.c) return
      if (!byCategory[r.c]) {
        byCategory[r.c] = { count: 0, sum: 0, min: Infinity, max: -Infinity }
      }
      byCategory[r.c].count++
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
      }
    })

    // Group by regional
    const byRegional = {}
    filteredData.forEach(r => {
      if (!r.r) return
      if (!byRegional[r.r]) {
        byRegional[r.r] = { count: 0, sum: 0 }
      }
      byRegional[r.r].count++
      if (r.pm) byRegional[r.r].sum += r.pm
    })

    Object.keys(byRegional).forEach(reg => {
      const stats = byRegional[reg]
      byRegional[reg] = {
        media: stats.count > 0 ? stats.sum / stats.count : 0,
        registros: stats.count,
      }
    })

    return {
      totalRecords: filteredData.length,
      avgPrice,
      minPrice,
      maxPrice,
      uniqueProducts: products.size,
      uniqueCategories: categories.size,
      uniqueRegions: regions.size,
      topProducts,
      byCategory,
      byRegional,
    }
  }, [filteredData, data])
}
