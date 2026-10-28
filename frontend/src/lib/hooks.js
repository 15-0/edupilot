import { useCallback, useEffect, useState } from 'react'
import api, { errorMessage } from './api'

/** GET a resource; returns { data, loading, error, reload }. */
export function useApi(url, params) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const key = JSON.stringify(params || {})

  const reload = useCallback(async () => {
    if (!url) return
    setLoading(true)
    setError(null)
    try {
      const res = await api.get(url, { params: JSON.parse(key) })
      setData(res.data)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [url, key])

  useEffect(() => { reload() }, [reload])
  return { data, loading, error, reload, setData }
}

export const todayISO = () => {
  const d = new Date()
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10)
}

export const fmtDate = (iso, opts = { day: 'numeric', month: 'short' }) =>
  iso ? new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, opts) : ''
