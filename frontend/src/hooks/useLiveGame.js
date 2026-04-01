import { useState, useEffect, useRef, useCallback } from 'react'

/**
 * useLiveGame — polls the live game endpoint every `intervalMs` milliseconds.
 *
 * @param {string} apiBase - Base API URL (e.g. '/api')
 * @param {number} gameId  - MLB game ID to poll
 * @param {number} intervalMs - Poll interval (default: 60000ms = 60s)
 *
 * @returns {{ data, loading, error, lastUpdated, refresh }}
 */
export function useLiveGame(apiBase, gameId, intervalMs = 60_000) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [lastUpdated, setLastUpdated] = useState(null)
  const intervalRef = useRef(null)

  const fetchLive = useCallback(() => {
    if (!gameId) return
    fetch(`${apiBase}/game/${gameId}/live`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then((d) => {
        setData(d)
        setError(null)
        setLastUpdated(new Date())
        setLoading(false)
      })
      .catch((err) => {
        setError(err.message)
        setLoading(false)
      })
  }, [apiBase, gameId])

  useEffect(() => {
    fetchLive()
    intervalRef.current = setInterval(fetchLive, intervalMs)
    return () => clearInterval(intervalRef.current)
  }, [fetchLive, intervalMs])

  return { data, loading, error, lastUpdated, refresh: fetchLive }
}
