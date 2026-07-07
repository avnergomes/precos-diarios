// Centralized data loader for the dashboard.
//
// When VITE_API_URL is set, data is fetched from the live API (/api/data/<path>)
// first and, on any non-OK response or network error, transparently falls back
// to the static JSON bundled with the site. The free Render instance hibernates
// and can be slow or unavailable, so the static copy keeps the dashboard working.
//
// The API attempt has a short timeout: during a Render cold start the request
// does not fail, it just hangs for 30-60s. Racing it against a timer lets the
// dashboard fall back to the bundled static copy in a few seconds instead of
// leaving the user stuck on a spinner.
const API_URL = import.meta.env.VITE_API_URL
const STATIC_BASE = (import.meta.env.BASE_URL || '/') + 'data/'
const API_BASE = API_URL ? `${API_URL}/api/data/` : null

// How long to wait for the live API before falling back to the static copy.
const API_TIMEOUT_MS = 4000

let staticFallbackUsed = false

/**
 * True when at least one request was served by the bundled static copy
 * because the live API was slow or unavailable.
 */
export function wasStaticFallbackUsed() {
  return staticFallbackUsed
}

/**
 * fetch() with an optional timeout, still honoring the caller's signal.
 * A timeout abort is converted into a regular error so the candidate loop
 * can fall through to the static copy; a caller abort keeps its AbortError.
 */
async function fetchWithTimeout(url, opts, timeoutMs) {
  if (!timeoutMs) return fetch(url, opts)

  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  const outerSignal = opts?.signal
  const onOuterAbort = () => controller.abort()

  if (outerSignal) {
    if (outerSignal.aborted) controller.abort()
    else outerSignal.addEventListener('abort', onOuterAbort, { once: true })
  }

  try {
    return await fetch(url, { ...opts, signal: controller.signal })
  } catch (err) {
    if (err.name === 'AbortError' && !(outerSignal && outerSignal.aborted)) {
      // Timeout, not a caller cancellation: surface as a normal failure.
      throw new Error(`Timeout after ${timeoutMs}ms for ${url}`)
    }
    throw err
  } finally {
    clearTimeout(timer)
    if (outerSignal) outerSignal.removeEventListener('abort', onOuterAbort)
  }
}

/**
 * Fetch a JSON data file by its path relative to the data root, e.g.
 * 'aggregated.json' or 'forecasts/boi-em-pe.json'. Tries the live API first
 * (when configured, with a short timeout), then the static bundled copy.
 * AbortErrors from the caller's signal propagate so callers can cancel
 * in-flight requests.
 *
 * @param {string} path - file path relative to the data root
 * @param {RequestInit} [opts] - fetch options (e.g. { signal })
 * @returns {Promise<any>} parsed JSON
 */
export async function fetchData(path, opts) {
  const candidates = API_BASE
    ? [
        { url: API_BASE + path, timeout: API_TIMEOUT_MS, isStatic: false },
        { url: STATIC_BASE + path, timeout: 0, isStatic: true },
      ]
    : [{ url: STATIC_BASE + path, timeout: 0, isStatic: true }]

  let lastError
  for (const candidate of candidates) {
    try {
      const response = await fetchWithTimeout(candidate.url, opts, candidate.timeout)
      if (response.ok) {
        if (candidate.isStatic && API_BASE) staticFallbackUsed = true
        return await response.json()
      }
      lastError = new Error(`HTTP ${response.status} for ${path}`)
    } catch (err) {
      if (err.name === 'AbortError') throw err
      lastError = err
    }
  }
  throw lastError || new Error(`Failed to load ${path}`)
}
