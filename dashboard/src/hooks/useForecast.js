import { useState, useEffect, useCallback } from 'react'

// API URL from environment variable or fallback
const API_URL = import.meta.env.VITE_API_URL || ''

/**
 * Hook to fetch forecast data for a product
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
      const url = `${API_URL}/api/forecast/${encodeURIComponent(produto)}?horizonte=${horizonte}`
      const response = await fetch(url)

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const result = await response.json()

      if (!result.success) {
        throw new Error(result.error || 'Forecast failed')
      }

      setData(result)
    } catch (err) {
      console.error('Forecast error:', err)
      setError(err.message)
      setData(null)
    } finally {
      setLoading(false)
    }
  }, [produto, horizonte])

  useEffect(() => {
    fetchForecast()
  }, [fetchForecast])

  return { data, loading, error, refetch: fetchForecast }
}

/**
 * Hook to fetch list of products available for forecasting
 */
export function useForecastProducts() {
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    async function fetchProducts() {
      try {
        const url = `${API_URL}/api/forecast/produtos`
        const response = await fetch(url)

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }

        const result = await response.json()

        if (result.success) {
          setProducts(result.produtos || [])
        } else {
          throw new Error(result.error || 'Failed to load products')
        }
      } catch (err) {
        console.error('Error loading forecast products:', err)
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchProducts()
  }, [])

  return { products, loading, error }
}

export default useForecast
