import { useEffect, useState } from 'react'
export function useResource<T>(load: (signal: AbortSignal) => Promise<T>) {
  const [state, setState] = useState<{ data?: T; error?: string; loading: boolean }>({ loading: true })
  useEffect(() => {
    const controller = new AbortController()
    setState({ loading: true })
    load(controller.signal).then(data => {
      if (!controller.signal.aborted) setState({ data, loading: false })
    }, () => {
      if (!controller.signal.aborted) setState({ error: 'Unable to load this information. Check your connection and access, then retry.', loading: false })
    })
    return () => controller.abort()
  }, [load])
  return state
}
