import { useState, useEffect, useMemo, useRef, useCallback } from 'react'
import { fetchData, wasStaticFallbackUsed } from '../lib/apiData'

export function useData() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [usedStaticFallback, setUsedStaticFallback] = useState(false)
  const [regionalDetailLoading, setRegionalDetailLoading] = useState(false)
  const [regionalDetailError, setRegionalDetailError] = useState(false)
  const regionalRequestedRef = useRef(false)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState(false)
  const detailRequestedRef = useRef(false)

  useEffect(() => {
    const controller = new AbortController()
    const { signal } = controller

    async function loadData() {
      try {
        setLoading(true)
        setError(null)

        // Carga inicial: só arquivos agregados, ~50 KB no total.
        // detailed.json (4,5 MB) saiu daqui e virou loadDetail(), sob demanda,
        // porque travava o first paint e a interatividade sem necessidade: a
        // visão sem filtro é inteiramente servida por aggregated/timeseries.
        const [aggregated, latest, timeseries, filters] = await Promise.all([
          fetchData('aggregated.json', { signal }),
          fetchData('latest.json', { signal }).catch(() => null),
          fetchData('timeseries.json', { signal }),
          fetchData('filters.json', { signal }),
        ])
        const detailed = null

        if (signal.aborted) return

        // Try to load regional filters (optional - may not exist).
        // detailed_regional.json (~33 MB) fica para loadRegionalDetail, sob demanda.
        let regionalFilters = null

        try {
          regionalFilters = await fetchData('regional_filters.json', { signal })
        } catch (err) {
          if (err.name !== 'AbortError') {
            console.warn('Regional data not available:', err)
          }
        }

        if (signal.aborted) return

        const normalizedFilters = normalizeFilters(filters, aggregated, detailed, regionalFilters)

        if (!signal.aborted) {
          setData({
            aggregated,
            latest,
            detailed,
            detailedRegional: null,
            timeseries,
            filters: normalizedFilters,
            hasRegionalData: false,
          })
          setUsedStaticFallback(wasStaticFallbackUsed())
        }
      } catch (err) {
        if (err.name !== 'AbortError' && !signal.aborted) {
          console.error('Error loading data:', err)
          setError(err.message)
        }
      } finally {
        if (!signal.aborted) {
          setLoading(false)
        }
      }
    }

    loadData()
    return () => controller.abort()
  }, [])

  // Carrega detailed.json (~4,5 MB) só quando o usuário aplica um filtro, que
  // é quando a granularidade por registro passa a ser necessária. Sem filtro,
  // a tela inteira sai de aggregated.json + timeseries.json + latest.json.
  const loadDetail = useCallback(() => {
    if (detailRequestedRef.current) return
    detailRequestedRef.current = true
    setDetailLoading(true)
    setDetailError(false)
    fetchData('detailed.json')
      .catch(() => null)
      .then(detailed => {
        if (detailed?.records?.length) {
          setData(prev => (prev ? { ...prev, detailed } : prev))
        } else {
          detailRequestedRef.current = false
          setDetailError(true)
        }
      })
      .finally(() => setDetailLoading(false))
  }, [])

  // Carrega o detalhamento regional (~33 MB) só quando o usuário seleciona
  // uma regional. Até lá, a UI usa os dados agregados normalmente.
  // Em caso de falha, libera o ref para permitir "Tentar novamente" sem reload.
  const loadRegionalDetail = useCallback(() => {
    if (regionalRequestedRef.current) return
    regionalRequestedRef.current = true
    setRegionalDetailLoading(true)
    setRegionalDetailError(false)
    fetchData('detailed_regional.json')
      .catch(() => null)
      .then(regDetailed => {
        if (regDetailed?.records?.length) {
          setData(prev => prev
            ? { ...prev, detailedRegional: regDetailed, hasRegionalData: true }
            : prev)
        } else {
          regionalRequestedRef.current = false
          setRegionalDetailError(true)
        }
      })
      .finally(() => setRegionalDetailLoading(false))
  }, [])

  return {
    data,
    loading,
    error,
    usedStaticFallback,
    loadRegionalDetail,
    regionalDetailLoading,
    regionalDetailError,
    loadDetail,
    detailLoading,
    detailError,
  }
}

/** Há algum filtro ativo? Sem filtro, a visão sai só dos agregados. */
export function hasActiveFilters(filters) {
  return Boolean(
    filters?.produto || filters?.categoria || filters?.regional ||
    filters?.anoMin || filters?.anoMax
  )
}

function normalizeFilters(filtersJson, aggregated, detailed, regionalFilters) {
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

  // Extract regionais from regional filters
  const regionais = regionalFilters?.regionais_com_dados || regionalFilters?.regionais || []

  return {
    anos: Array.from(anos).sort((a, b) => a - b),
    categorias: Array.from(categorias).sort((a, b) => a.localeCompare(b)),
    produtos: Array.from(produtos).sort((a, b) => a.localeCompare(b)),
    regionais: regionais.sort((a, b) => a.localeCompare(b)),
    category_products: categoryProducts,
    regional_products: regionalFilters?.regional_products || {},
    regional_anos: regionalFilters?.regional_anos || {},
  }
}

export function useFilteredData(data, filters) {
  return useMemo(() => {
    // Use regional data if available and regional filter is active, otherwise use regular detailed
    const useRegionalData = data?.hasRegionalData && filters.regional
    const records = useRegionalData
      ? data?.detailedRegional?.records
      : data?.detailed?.records

    if (!records) return []

    let filtered = records

    // Filter by year range
    if (filters.anoMin) {
      filtered = filtered.filter(r => r.a >= filters.anoMin)
    }
    if (filters.anoMax) {
      filtered = filtered.filter(r => r.a <= filters.anoMax)
    }

    // Filter by category
    if (filters.categoria) {
      filtered = filtered.filter(r => r.c === filters.categoria)
    }

    // Filter by product
    if (filters.produto) {
      filtered = filtered.filter(r => r.p === filters.produto)
    }

    // Filter by regional (only in regional data)
    if (filters.regional && useRegionalData) {
      filtered = filtered.filter(r => r.r === filters.regional)
    }

    return filtered
  }, [data, filters])
}

/**
 * Monta as mesmas estruturas de `useAggregations` a partir de aggregated.json,
 * sem precisar dos registros crus. Usado na visão sem filtro.
 *
 * Além de dispensar o download de 4,5 MB, isto é mais correto do que o caminho
 * antigo: detailed.json é uma amostra de 50 mil registros, então os números de
 * destaque saíam da amostra. Aqui vêm do conjunto completo (77 mil).
 */
export function aggregationsFromSummary(aggregated) {
  const byYear = aggregated?.by_year || {}
  const byProductRaw = aggregated?.by_product || {}
  const byCategoryRaw = aggregated?.by_category || {}

  const years = Object.keys(byYear).map(Number).filter(n => !Number.isNaN(n)).sort((a, b) => b - a)

  // Média ponderada por registros: a média das médias anuais seria enviesada.
  let somaPonderada = 0
  let totalRegistros = 0
  Object.values(byYear).forEach(y => {
    if (y?.media > 0 && y?.registros > 0) {
      somaPonderada += y.media * y.registros
      totalRegistros += y.registros
    }
  })

  let yoyChange = 0
  if (years.length >= 2) {
    const atual = byYear[years[0]]?.media
    const anterior = byYear[years[1]]?.media
    if (atual > 0 && anterior > 0) yoyChange = ((atual - anterior) / anterior) * 100
  }

  const minimos = Object.values(byCategoryRaw).map(c => c.minimo).filter(v => v > 0)
  const maximos = Object.values(byCategoryRaw).map(c => c.maximo).filter(v => v > 0)

  // A API e o bundle estático podem servir versões diferentes de
  // aggregated.json: minimo/maximo/produtos só existem no formato novo.
  // Quando faltarem, derivamos de by_product; se nem lá houver, devolvemos
  // null para a UI mostrar "—" em vez de um R$ 0,00 que seria falso.
  const produtosPorCategoria = {}
  const faixaPorCategoria = {}
  Object.values(byProductRaw).forEach(p => {
    const cat = p?.categoria
    if (!cat) return
    produtosPorCategoria[cat] = (produtosPorCategoria[cat] || 0) + 1
    if (p.minimo > 0 || p.maximo > 0) {
      const faixa = faixaPorCategoria[cat] || { min: Infinity, max: -Infinity }
      if (p.minimo > 0) faixa.min = Math.min(faixa.min, p.minimo)
      if (p.maximo > 0) faixa.max = Math.max(faixa.max, p.maximo)
      faixaPorCategoria[cat] = faixa
    }
  })

  const byCategory = {}
  Object.entries(byCategoryRaw).forEach(([cat, c]) => {
    const faixa = faixaPorCategoria[cat]
    byCategory[cat] = {
      media: c.media ?? 0,
      minimo: c.minimo ?? (faixa && faixa.min !== Infinity ? faixa.min : null),
      maximo: c.maximo ?? (faixa && faixa.max !== -Infinity ? faixa.max : null),
      registros: c.registros ?? 0,
      produtos: c.produtos ?? produtosPorCategoria[cat] ?? 0,
    }
  })

  const sparklineData = {}
  const topProducts = Object.entries(byProductRaw).map(([produto, p]) => {
    sparklineData[produto] = p.sparkline || []
    return {
      produto,
      categoria: p.categoria,
      unidade: p.unidade ?? null,
      media: p.media ?? 0,
      registros: p.registros ?? 0,
      variacao: p.variacao ?? null,
    }
  }).sort((a, b) => b.registros - a.registros)

  return {
    totalRecords: aggregated?.metadata?.total_records ?? totalRegistros,
    avgPrice: totalRegistros > 0 ? somaPonderada / totalRegistros : 0,
    minPrice: minimos.length ? Math.min(...minimos) : 0,
    maxPrice: maximos.length ? Math.max(...maximos) : 0,
    uniqueProducts: Object.keys(byProductRaw).length,
    uniqueCategories: Object.keys(byCategoryRaw).length,
    uniqueRegionais: 0,
    yoyChange,
    topProducts,
    byCategory,
    byRegional: {},
    sparklineData,
  }
}

export function useAggregations(filteredData, data) {
  return useMemo(() => {
    // Sem registros carregados, serve a visão a partir dos agregados em vez de
    // devolver zeros. Isto é o que permite a tela renderizar completa sem os
    // 4,5 MB de detailed.json.
    if ((!filteredData || filteredData.length === 0) && data?.aggregated && !data?.detailed) {
      return aggregationsFromSummary(data.aggregated)
    }

    if (!filteredData || filteredData.length === 0) {
      return {
        totalRecords: 0,
        avgPrice: 0,
        minPrice: 0,
        maxPrice: 0,
        uniqueProducts: 0,
        uniqueCategories: 0,
        uniqueRegionais: 0,
        yoyChange: 0,
        topProducts: [],
        byCategory: {},
        byRegional: {},
        sparklineData: {},
      }
    }

    // Get price field (pm for detailed, v for regional)
    const getPrice = (r) => r.pm ?? r.v

    // Calculate aggregations from filtered data
    const prices = filteredData
      .filter(r => getPrice(r) && getPrice(r) > 0)
      .map(r => getPrice(r))

    const avgPrice = prices.length > 0
      ? prices.reduce((a, b) => a + b, 0) / prices.length
      : 0

    const minPrice = prices.length > 0 ? Math.min(...prices) : 0
    const maxPrice = prices.length > 0 ? Math.max(...prices) : 0

    const products = new Set(filteredData.map(r => r.p))
    const categories = new Set(filteredData.map(r => r.c))
    const regionais = new Set(filteredData.filter(r => r.r).map(r => r.r))

    // Calculate YoY (Year over Year) change
    const years = [...new Set(filteredData.map(r => r.a))].sort((a, b) => b - a)
    let yoyChange = 0
    if (years.length >= 2) {
      const currentYear = years[0]
      const prevYear = years[1]

      const currentYearPrices = filteredData
        .filter(r => r.a === currentYear && getPrice(r) > 0)
        .map(r => getPrice(r))
      const prevYearPrices = filteredData
        .filter(r => r.a === prevYear && getPrice(r) > 0)
        .map(r => getPrice(r))

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
      const price = getPrice(r)
      if (!productStats[r.p]) {
        productStats[r.p] = { count: 0, sum: 0, categoria: r.c, unidade: r.u || null }
        productByYear[r.p] = {}
      }
      if (!productStats[r.p].unidade && r.u) {
        productStats[r.p].unidade = r.u
      }
      productStats[r.p].count++
      if (price) {
        productStats[r.p].sum += price
        // Track by year for variation calculation
        if (!productByYear[r.p][r.a]) {
          productByYear[r.p][r.a] = { sum: 0, count: 0 }
        }
        productByYear[r.p][r.a].sum += price
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
          .filter(r => r.p === produto && getPrice(r) > 0)
          .forEach(r => {
            const month = getRecordMonth(r)
            const key = `${r.a}-${String(month).padStart(2, '0')}`
            if (!monthlyData[key]) {
              monthlyData[key] = { sum: 0, count: 0 }
            }
            monthlyData[key].sum += getPrice(r)
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
      const price = getPrice(r)
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
      if (price) {
        byCategory[r.c].sum += price
        byCategory[r.c].min = Math.min(byCategory[r.c].min, price)
        byCategory[r.c].max = Math.max(byCategory[r.c].max, price)
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

    // Group by regional
    const byRegional = {}
    filteredData.forEach(r => {
      if (!r.r) return
      const price = getPrice(r)
      if (!byRegional[r.r]) {
        byRegional[r.r] = {
          count: 0,
          sum: 0,
          min: Infinity,
          max: -Infinity,
          products: new Set(),
        }
      }
      byRegional[r.r].count++
      if (r.p) byRegional[r.r].products.add(r.p)
      if (price) {
        byRegional[r.r].sum += price
        byRegional[r.r].min = Math.min(byRegional[r.r].min, price)
        byRegional[r.r].max = Math.max(byRegional[r.r].max, price)
      }
    })

    Object.keys(byRegional).forEach(reg => {
      const stats = byRegional[reg]
      byRegional[reg] = {
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
      uniqueRegionais: regionais.size,
      yoyChange,
      topProducts,
      byCategory,
      byRegional,
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
export function useFilteredTimeSeries(filteredData, data) {
  return useMemo(() => {
    // Sem registros carregados, usa a série mensal já pré-agregada.
    // timeseries.json não traz min/max por período, então caem para a própria
    // média: o gráfico mostra a linha corretamente, sem a faixa min-max, que
    // volta assim que o detalhamento é carregado por um filtro.
    if ((!filteredData || filteredData.length === 0) && data?.timeseries?.by_period) {
      const result = {}
      Object.entries(data.timeseries.by_period).forEach(([period, stats]) => {
        const media = stats?.media ?? 0
        result[period] = {
          media,
          min: media,
          max: media,
          count: stats?.count ?? 0,
        }
      })
      return result
    }

    if (!filteredData || filteredData.length === 0) return {}

    const getPrice = (r) => r.pm ?? r.v
    const byPeriod = {}

    filteredData.forEach(r => {
      const price = getPrice(r)
      if (!r.a || !price) return
      const month = getRecordMonth(r)
      const period = `${r.a}-${String(month).padStart(2, '0')}`

      if (!byPeriod[period]) {
        byPeriod[period] = { sum: 0, count: 0, min: Infinity, max: -Infinity }
      }

      byPeriod[period].sum += price
      byPeriod[period].count++
      byPeriod[period].min = Math.min(byPeriod[period].min, price)
      byPeriod[period].max = Math.max(byPeriod[period].max, price)
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
  }, [filteredData, data])
}
