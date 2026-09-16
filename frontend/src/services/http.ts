export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export function createApiClient(baseUrl: string, fetcher: typeof fetch = fetch) {
  const base = baseUrl.replace(/\/+$/, '')

  return async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const headers = new Headers(options.headers)
    headers.set('Accept', 'application/json')
    if (options.body != null) headers.set('Content-Type', 'application/json')
    const response = await fetcher(`${base}/${path.replace(/^\/+/, '')}`, {
      ...options,
      headers,
      signal: options.signal ?? AbortSignal.timeout(10_000),
    })
    if (!response.ok) {
      let message = `Request failed (${response.status}).`
      try {
        const body: unknown = await response.json()
        if (body && typeof body === 'object' && 'detail' in body && typeof body.detail === 'string') {
          message = body.detail
        } else if (response.status === 422) {
          message = 'Please check the information you entered.'
        }
      } catch { /* Non-JSON server errors use the status-based fallback. */ }
      throw new ApiError(response.status, message)
    }
    if (response.status === 204) return undefined as T
    return response.json() as Promise<T>
  }
}
