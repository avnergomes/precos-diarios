import { useState, useEffect, useCallback } from 'react'

const BASE = import.meta.env.BASE_URL || '/'

/**
 * Hook to load pre-computed forecast for a product (static JSON).
 */
export function useForecast(produto, horizonte = 30) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const fetchForecast = useCallback(async () => {
    if (!produto) {
      setData(null)
      return
    }

    setLoading(true)
    setError(null)

    try {
      const slug = produto.slug || produto
      const url = `${BASE}data/forecasts/${encodeURIComponent(slug)}.json`
      const response = await fetch(url)

      if (!response.ok) {
        throw new Error(`Previsão não disponível (${response.status})`)
      }

      const result = await response.json()

      if (!result.success) {
        throw new Error(result.error || 'Falha ao carregar previsão')
      }

      // Trim forecasts to match selected horizon (months)
      const months = Math.max(1, Math.round(horizonte / 30))
      const trimmed = { ...result }
      trimmed.modelos = {}
      for (const [key, model] of Object.entries(result.modelos || {})) {
        trimmed.modelos[key] = {
          ...model,
          previsoes: (model.previsoes || []).slice(0, months),
        }
      }

      setData(trimmed)
    } catch (err) {
      console.error('Forecast error:', err)
      setError(err.message)
      setData(null)
    } finally {
      setLoading(false)
    }
  }, [produto, horizonte])

  // Reset state when product changes
  useEffect(() => {
    setData(null)
    setError(null)
  }, [produto])

  return { data, loading, error, refetch: fetchForecast }
}

/**
 * Hook to load list of products available for forecasting (static JSON).
 */
export function useForecastProducts() {
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    async function load() {
      try {
        const url = `${BASE}data/forecast_products.json`
        const response = await fetch(url)

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`)
        }

        const result = await response.json()
        setProducts(result.produtos || [])
      } catch (err) {
        console.error('Error loading forecast products:', err)
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    load()
  }, [])

  return { products, loading, error }
}

export default useForecast
