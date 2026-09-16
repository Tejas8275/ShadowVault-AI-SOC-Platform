import type { IndicatorSubmission, IndicatorObservation, IndicatorPage, IndicatorFilters } from '../indicators/contracts.ts'
import type { CaseReportDraft } from '../cases/report.ts'
import type { CaseBriefingResult } from '../cases/briefing.ts'
import { ApiError } from '../../services/http.ts'
import type { Annotations, CustodyPage, EvidenceDetails, Filters, Note, NotesPage, SearchPage } from './contracts.ts'
import type { TimelineEvent, TimelinePage, TimelineSubmission } from '../timeline/contracts.ts'
import { MAX_DOWNLOAD_BYTES, readDownload } from './download.ts'
import type { CaseDraft, CaseRecord, CasePage, CaseStatus, CaseHistoryPage, CaseIntelligenceRecord } from '../cases/contracts.ts'

export function searchParameters(filters: Filters, cursor?: string) {
  const query = new URLSearchParams()
  for (const [key, raw] of Object.entries(filters)) {
    const value = raw.trim()
    if (!value) continue
    if (key === 'tags') {
      for (const tag of new Set(value.split(',').map(v => v.trim().toLowerCase()).filter(Boolean))) query.append('tags', tag)
    } else if (['created_from', 'created_to', 'collected_from', 'collected_to'].includes(key)) {
      query.set(key, new Date(value).toISOString())
    } else query.set(key, value)
  }
  if (cursor) query.set('cursor', cursor)
  return query.toString()
}

export function validateFilters(filters: Filters): string | null {
  for (const [low, high] of [['created_from', 'created_to'], ['collected_from', 'collected_to'], ['min_size', 'max_size']]) {
    const number = (value: string) => low.includes('size') ? Number(value) : new Date(value).getTime()
    if ((filters[low] && !Number.isFinite(number(filters[low]))) || (filters[high] && !Number.isFinite(number(filters[high])))) return 'Enter a valid date or size.'
    if (filters[low] && filters[high] && number(filters[low]) > number(filters[high])) return 'Range start must not exceed range end.'
  }
  return null
}

// The closure owns the credential. It is never persisted or exposed to callers.
export function createInvestigationService(baseUrl: string, onUnauthorized: () => void, fetcher: typeof fetch = fetch) {
  const base = new URL(baseUrl, globalThis.location?.origin || 'http://localhost')
  if (base.username || base.password || base.search || base.hash ||
      (base.protocol !== 'https:' && !(base.protocol === 'http:' && ['localhost', '127.0.0.1', '[::1]'].includes(base.hostname)))) {
    throw new Error('Investigation API requires HTTPS or loopback HTTP without URL credentials, query, or fragment.')
  }
  let token = ''
  const pending = new Set<AbortController>()
  function disconnect() {
    token = ''
    for (const controller of pending) controller.abort()
    pending.clear()
  }
  async function request<T>(path: string, options: RequestInit = {}, timeoutMs = 10_000): Promise<T> {
    if (!token) throw new ApiError(401, 'Connect an operator first.')
    const controller = new AbortController()
    pending.add(controller)
    const signal = AbortSignal.any([controller.signal, AbortSignal.timeout(timeoutMs), ...(options.signal ? [options.signal] : [])])
    try {
      const response = await fetcher(`${base.href.replace(/\/+$/, '')}/${path}`, {
        ...options, signal, redirect: 'error', credentials: 'omit', cache: 'no-store',
        headers: { Accept: 'application/json', Authorization: `Bearer ${token}`, ...(options.body ? { 'Content-Type': 'application/json' } : {}) },
      })
      if (signal.aborted) throw new DOMException('Request cancelled', 'AbortError')
      if (!response.ok) {
        if (response.status === 401) { disconnect(); onUnauthorized() }
        // Do not echo backend error bodies into credential or investigation forms.
        throw new ApiError(response.status, response.status === 401 ? 'Operator connection expired or was rejected.' : `Request failed (${response.status}).`)
      }
      const data = await response.json() as T
      if (signal.aborted) throw new DOMException('Request cancelled', 'AbortError')
      return data
    } finally { pending.delete(controller) }
  }
  async function download(id: string, size: number, external: AbortSignal, progress?: (received: number) => void) {
    if (!token) throw new ApiError(401, 'Connect an operator first.')
    if (!Number.isSafeInteger(size) || size < 0 || size > MAX_DOWNLOAD_BYTES) throw new Error('Evidence exceeds the browser download limit of 100 MiB.')
    const controller = new AbortController()
    pending.add(controller)
    const signal = AbortSignal.any([controller.signal, external, AbortSignal.timeout(240_000)])
    try {
      signal.throwIfAborted()
      const response = await fetcher(`${base.href.replace(/\/+$/, '')}/evidence/${encodeURIComponent(id)}/download`, {
        method: 'POST', signal, redirect: 'error', credentials: 'omit', cache: 'no-store',
        headers: { Accept: 'application/octet-stream', Authorization: `Bearer ${token}` },
      })
      if (signal.aborted) { await response.body?.cancel(); signal.throwIfAborted() }
      if (!response.ok) {
        await response.body?.cancel()
        if (response.status === 401) { disconnect(); onUnauthorized() }
        const messages: Record<number, string> = {
          401: 'Operator connection expired or was rejected.', 404: 'Evidence is unavailable to this operator.',
          409: 'Evidence could not be prepared consistently. Review custody and contact the operator before retrying.',
          413: 'Evidence exceeds the server retrieval limit.', 429: 'Retrieval capacity is busy. Retry manually later.',
          503: 'Evidence retrieval is unavailable. Review custody before retrying.',
        }
        throw new ApiError(response.status, messages[response.status] || `Download failed (${response.status}).`)
      }
      const blob = await readDownload(response, size, signal, progress)
      signal.throwIfAborted()
      return blob
    } finally { pending.delete(controller) }
  }
  return {
    async connect(value: string) {
      disconnect()
      if (!/^sv_operator_[!-~]{1,240}$/.test(value)) throw new Error('Enter a valid provisioned operator token.')
      token = value
      try { await request<SearchPage>('evidence?limit=1') } catch (error) { disconnect(); throw error }
    },
    disconnect,
    async aiBriefing(id: string, signal?: AbortSignal) {
      const result = await request<CaseBriefingResult>(`incidents/${encodeURIComponent(id)}/ai-briefing`, {
        method:'POST', body:JSON.stringify({schema_version:1}), signal,
      }, 50_000)
      if (result.case_id!==id || result.schema_version!==1 || result.kind!=='ai_selected_metadata'
          || result.prompt_version!=='metadata-selection-v1' || !Array.isArray(result.sources)
          || result.sources.length<1 || result.sources.length>40 || !Array.isArray(result.limitations)
          || result.sources.some(source=>!source.fields || typeof source.fields!=='object'
            || !/^(incident|evidence|timeline|indicator|custody|history):[0-9a-f-]{36}$/.test(source.citation))) {
        throw new Error('Briefing scope or schema does not match this case.')
      }
      return result
    },
    async caseReport(id: string, signal?: AbortSignal) {
      const report = await request<CaseReportDraft>(`incidents/${encodeURIComponent(id)}/report-draft`, {signal})
      if (report.case.id !== id || report.status !== 'draft' || report.schema_version !== 1) throw new Error('Report scope or version does not match this case.')
      return report
    },
    cases: (filters: Filters, cursor?: string, signal?: AbortSignal) => request<CasePage>(`incidents?${new URLSearchParams({ ...Object.fromEntries(Object.entries(filters).filter(([, value]) => value.trim()).map(([key, value]) => [key, value.trim()])), ...(cursor ? { cursor } : {}) })}`, { signal }),
    indicators: (id: string, cursor?: string, signal?: AbortSignal, filters: IndicatorFilters = {}) => request<IndicatorPage>(`incidents/${encodeURIComponent(id)}/indicators?${new URLSearchParams({limit:'50', ...Object.fromEntries(Object.entries(filters).filter(([,value])=>value?.trim()).map(([key,value])=>[key,value!.trim()])), ...(cursor ? {cursor} : {})})}`, {signal}),
    addIndicator: (id: string, payload: IndicatorSubmission, signal?: AbortSignal) => request<IndicatorObservation>(`evidence/${encodeURIComponent(id)}/indicators`, {method:'POST', body:JSON.stringify(payload), signal}),
    caseIntelligence: (id: string, signal?: AbortSignal) => request<CaseIntelligenceRecord>(`incidents/${encodeURIComponent(id)}?include_intelligence=true`, { signal }),
    caseDetail: (id: string, signal?: AbortSignal) => request<CaseRecord>(`incidents/${encodeURIComponent(id)}`, { signal }),
    caseHistory: (id: string, after?: number, signal?: AbortSignal) => request<CaseHistoryPage>(`incidents/${encodeURIComponent(id)}/history?${new URLSearchParams({limit:'50',...(after===undefined?{}:{after_revision:String(after)})})}`, {signal}),
    createCase: (payload: CaseDraft) => request<CaseRecord>('incidents', { method: 'POST', body: JSON.stringify(payload) }),
    updateCase: (id: string, payload: CaseDraft & { status: CaseStatus; expected_revision: number }) => request<CaseRecord>(`incidents/${encodeURIComponent(id)}`, { method: 'PATCH', body: JSON.stringify(payload) }),
    download,
    createTimeline: (id: string, payload: TimelineSubmission) => request<TimelineEvent>(`evidence/${encodeURIComponent(id)}/timeline-events`, { method: 'POST', body: JSON.stringify(payload) }),
    timelineDetails: (id: string, signal?: AbortSignal) => request<TimelineEvent>(`timeline-events/${encodeURIComponent(id)}`, { signal }),
    timelineSearch: (filters: Filters, cursor?: string, signal?: AbortSignal) => request<TimelinePage>(`timeline-events?${new URLSearchParams({ ...Object.fromEntries(Object.entries(filters).filter(([, value]) => value.trim()).map(([key, value]) => [key, value.trim()])), ...(cursor ? { cursor } : {}) })}`, { signal }),
    search: (filters: Filters, cursor?: string, signal?: AbortSignal) => request<SearchPage>(`evidence?${searchParameters(filters, cursor)}`, { signal }),
    details: (id: string, signal?: AbortSignal) => request<EvidenceDetails>(`evidence/${encodeURIComponent(id)}`, { signal }),
    annotate: (id: string, value: Annotations) => request<EvidenceDetails>(`evidence/${encodeURIComponent(id)}/annotations`, { method: 'PATCH', body: JSON.stringify(value) }),
    addNote: (id: string, body: string, expected_revision: number) => request<{ note: Note; metadata_revision: number }>(`evidence/${encodeURIComponent(id)}/notes`, { method: 'POST', body: JSON.stringify({ body, expected_revision }) }),
    notes: (id: string, cursor?: string, signal?: AbortSignal) => request<NotesPage>(`evidence/${encodeURIComponent(id)}/notes?${new URLSearchParams({ limit: '50', ...(cursor ? { cursor } : {}) })}`, { signal }),
    custody: (id: string, after = 0, signal?: AbortSignal) => request<CustodyPage>(`evidence/${encodeURIComponent(id)}/custody?after_sequence=${after}&limit=50`, { signal }),
  }
}
export type InvestigationService = ReturnType<typeof createInvestigationService>
