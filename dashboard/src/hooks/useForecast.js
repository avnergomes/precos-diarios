import { useState, useEffect, useCallback, useRef } from 'react'
import { fetchData } from '../lib/apiData'

/**
 * Hook to load pre-computed forecast for a product (static JSON).
 * horizonte is in months (default 3).
 */
export function useForecast(produto, horizonte = 3) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const abortRef = useRef(null)

  const fetchForecast = useCallback(async () => {
    if (!produto) {
      setData(null)
      return
    }

    // Cancel any in-flight request before starting a new one
    if (abortRef.current) abortRef.current.abort()
    const controller = new AbortController()
    abortRef.current = controller
    const { signal } = controller

    setLoading(true)
    setError(null)

    try {
      const slug = produto.slug || produto
      const result = await fetchData(`forecasts/${encodeURIComponent(slug)}.json`, { signal })

      if (signal.aborted) return

      if (!result.success) {
        throw new Error(result.error || 'Falha ao carregar previsão')
      }

      // Trim forecasts to the selected horizon (already in months)
      const months = Math.max(1, horizonte)
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
      if (err.name === 'AbortError') return
      setError(err.message)
      setData(null)
    } finally {
      if (!signal.aborted) setLoading(false)
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
    const controller = new AbortController()
    const { signal } = controller

    async function load() {
      try {
        const result = await fetchData('forecast_products.json', { signal })
        if (!signal.aborted) {
          setProducts(result.produtos || [])
        }
      } catch (err) {
        if (err.name !== 'AbortError') {
          setError(err.message)
        }
      } finally {
        if (!signal.aborted) {
          setLoading(false)
        }
      }
    }

    load()
    return () => controller.abort()
  }, [])

  return { products, loading, error }
}

export default useForecast
