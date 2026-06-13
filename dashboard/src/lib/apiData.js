// Centralized data loader for the dashboard.
//
// When VITE_API_URL is set, data is fetched from the live API (/api/data/<path>)
// first and, on any non-OK response or network error, transparently falls back
// to the static JSON bundled with the site. The free Render instance hibernates
// and can be slow or unavailable, so the static copy keeps the dashboard working.
const API_URL = import.meta.env.VITE_API_URL
const STATIC_BASE = (import.meta.env.BASE_URL || '/') + 'data/'
const API_BASE = API_URL ? `${API_URL}/api/data/` : null

/**
 * Fetch a JSON data file by its path relative to the data root, e.g.
 * 'aggregated.json' or 'forecasts/boi-em-pe.json'. Tries the live API first
 * (when configured), then the static bundled copy. AbortErrors propagate so
 * callers can cancel in-flight requests.
 *
 * @param {string} path - file path relative to the data root
 * @param {RequestInit} [opts] - fetch options (e.g. { signal })
 * @returns {Promise<any>} parsed JSON
 */
export async function fetchData(path, opts) {
  const candidates = API_BASE
    ? [API_BASE + path, STATIC_BASE + path]
    : [STATIC_BASE + path]

  let lastError
  for (const url of candidates) {
    try {
      const response = await fetch(url, opts)
      if (response.ok) return await response.json()
      lastError = new Error(`HTTP ${response.status} for ${path}`)
    } catch (err) {
      if (err.name === 'AbortError') throw err
      lastError = err
    }
  }
  throw lastError || new Error(`Failed to load ${path}`)
}
