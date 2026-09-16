import { useCallback, useState } from 'react'
import type { EvidenceDetails, ReviewState } from './contracts'
import type { InvestigationService } from './service'
import { ApiError } from '../../services/http'
import { useResource } from './useResource'

export function AnnotationsPanel({
  api,
  evidence,
  onUpdated,
}: {
  api: InvestigationService
  evidence: EvidenceDetails
  onUpdated: (value: EvidenceDetails) => void
}) {
  const [title, setTitle] = useState(evidence.display_title || '')
  const [review, setReview] = useState<ReviewState>(evidence.review_state)
  const [tags, setTags] = useState(evidence.tags.join(', '))
  const [body, setBody] = useState('')
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [blocked, setBlocked] = useState(false)
  const [cursor, setCursor] = useState<string>()
  const [history, setHistory] = useState<(string | undefined)[]>([])
  const [refresh, setRefresh] = useState(0)
  const load = useCallback((signal: AbortSignal) => api.notes(evidence.id, cursor, signal), [api, evidence.id, cursor, refresh])
  const notes = useResource(load)

  async function reload() {
    const [latest] = await Promise.all([api.details(evidence.id), api.notes(evidence.id)])
    onUpdated(latest)
    setCursor(undefined)
    setHistory([])
    setRefresh(v => v + 1)
    setBlocked(false)
  }

  async function save(kind: 'annotations' | 'note') {
    if (busy || blocked) return
    const normalized = [...new Set(tags.split(',').map(tag => tag.trim().toLowerCase()).filter(Boolean))].sort()
    if (
      kind === 'annotations' &&
      (normalized.length > 20 || normalized.some(tag => !/^[a-z0-9][a-z0-9._-]{0,63}$/.test(tag)))
    ) {
      setMessage('Use up to 20 tags, each 1–64 letters, digits, dots, underscores or hyphens, starting with a letter or digit.')
      return
    }
    setBusy(true)
    setMessage('')
    try {
      if (kind === 'annotations') {
        const saved = await api.annotate(evidence.id, {
          expected_revision: evidence.metadata_revision,
          display_title: title.trim() || null,
          review_state: review,
          tags: normalized,
        })
        onUpdated(saved)
        setTitle(saved.display_title || '')
        setReview(saved.review_state)
        setTags(saved.tags.join(', '))
      } else {
        await api.addNote(evidence.id, body.trim(), evidence.metadata_revision)
        setBody('')
        setCursor(undefined)
        setHistory([])
        await reload()
      }
      setRefresh(v => v + 1)
      setMessage('Saved.')
    } catch (error) {
      setBlocked(true)
      const conflict = error instanceof ApiError && error.status === 409
      setMessage(
        conflict
          ? 'Metadata changed. Your draft is preserved. Reload current metadata and review it before resubmitting.'
          : 'Save was not confirmed. Your remaining draft is preserved. Reload current metadata and notes before deciding whether to submit again.',
      )
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="evidence-panel">
      <h2>Investigator annotations</h2>
      <p className="muted">
        Current revision: {evidence.metadata_revision}. Current title: {evidence.display_title || 'None'}; review:{' '}
        {evidence.review_state.replace('_', ' ')}; tags: {evidence.tags.join(', ') || 'None'}.
      </p>
      <form
        onSubmit={e => {
          e.preventDefault()
          void save('annotations')
        }}
      >
        <fieldset disabled={busy || blocked} style={{ border: 0, padding: 0, margin: 0 }}>
          <div style={{ display: 'grid', gap: '0.85rem' }}>
            <label>
              Display title
              <input value={title} maxLength={200} onChange={e => setTitle(e.target.value)} />
            </label>
            <label>
              Review state
              <select value={review} onChange={e => setReview(e.target.value as ReviewState)}>
                <option value="unreviewed">Unreviewed</option>
                <option value="in_review">In review</option>
                <option value="reviewed">Reviewed</option>
              </select>
            </label>
            <label>
              Evidence tags (comma-separated)
              <input value={tags} maxLength={1300} onChange={e => setTags(e.target.value)} />
            </label>
          </div>
          <p className="muted" style={{ margin: '0.5rem 0 0.85rem' }}>
            Remove a tag from the list to remove it from the evidence. Leave the list empty to clear all tags.
          </p>
          <button>Save annotations</button>
        </fieldset>
      </form>

      <h2 style={{ marginTop: '2rem' }}>Investigator notes ({evidence.note_count})</h2>
      <form
        onSubmit={e => {
          e.preventDefault()
          void save('note')
        }}
      >
        <label htmlFor="evidence-note">New note</label>
        <textarea
          id="evidence-note"
          value={body}
          required
          maxLength={10000}
          rows={4}
          disabled={busy || blocked}
          onChange={e => setBody(e.target.value)}
        />
        <p className="muted">Notes are appended with your identity and timestamp. Existing notes cannot be edited or deleted.</p>
        <button disabled={busy || blocked || !body.trim()}>Add note</button>
      </form>

      {message && <p role="status" style={{ fontWeight: 500, color: 'var(--accent)' }}>{message}</p>}
      {blocked && (
        <button
          disabled={busy}
          onClick={async () => {
            setBusy(true)
            try {
              await reload()
              setMessage('Current metadata and notes reloaded. Review them alongside your preserved draft before resubmitting.')
            } catch {
              setMessage('Reload failed. Submission remains blocked; check your connection and try again.')
            } finally {
              setBusy(false)
            }
          }}
        >
          Reload before resubmitting
        </button>
      )}

      {notes.loading && <p role="status">Loading notes…</p>}
      {notes.error && (
        <p role="alert">
          {notes.error} <button onClick={() => setRefresh(v => v + 1)}>Retry notes</button>
        </p>
      )}

      {notes.data && (
        <>
          <ol className="history-list">
            {notes.data.items.map(note => (
              <li key={note.id}>
                <p style={{ fontSize: '0.82rem', fontFamily: 'var(--font-mono)' }}>
                  <strong>{note.author_label}</strong> · {new Date(note.created_at).toISOString()} (UTC)
                </p>
                <p className="plain-text" style={{ marginTop: '0.4rem', color: 'var(--text-bright)' }}>{note.body}</p>
              </li>
            ))}
          </ol>
          {!notes.data.items.length && <p className="muted">No notes recorded.</p>}
          <div className="actions" style={{ marginTop: '1rem' }}>
            <button
              disabled={!history.length}
              onClick={() => {
                setCursor(history.at(-1))
                setHistory(v => v.slice(0, -1))
              }}
            >
              Previous notes
            </button>
            <button
              disabled={!notes.data.next_cursor}
              onClick={() => {
                setHistory(v => [...v, cursor])
                setCursor(notes.data!.next_cursor!)
              }}
            >
              Next notes
            </button>
          </div>
        </>
      )}
    </section>
  )
}
