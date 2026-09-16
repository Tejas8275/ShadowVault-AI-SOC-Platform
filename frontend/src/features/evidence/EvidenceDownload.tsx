import { useEffect, useRef, useState } from 'react'
import type { InvestigationService } from './service'
import { downloadFilename, MAX_DOWNLOAD_BYTES } from './download'

export function EvidenceDownload({
  api,
  id,
  size,
  onAttempt,
}: {
  api: InvestigationService
  id: string
  size: number
  onAttempt: () => void
}) {
  const active = useRef<AbortController | null>(null)
  const objectUrl = useRef<string | null>(null)
  const [ready, setReady] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  useEffect(() => () => {
    active.current?.abort()
    active.current = null
    if (objectUrl.current) URL.revokeObjectURL(objectUrl.current)
    objectUrl.current = null
  }, [api, id])

  function discard() {
    if (objectUrl.current) URL.revokeObjectURL(objectUrl.current)
    objectUrl.current = null
    setReady(null)
  }

  async function prepare() {
    if (active.current) return
    discard()
    setError('')
    setMessage('Preparing a verified copy…')
    setBusy(true)
    const controller = new AbortController()
    active.current = controller
    try {
      const blob = await api.download(id, size, controller.signal, received => {
        if (active.current === controller && !controller.signal.aborted) {
          setMessage(`Receiving copy: ${received.toLocaleString()} of ${size.toLocaleString()} bytes`)
        }
      })
      if (active.current !== controller || controller.signal.aborted) return
      objectUrl.current = URL.createObjectURL(blob)
      setReady(objectUrl.current)
      setMessage('Copy received and ready to save. The server recorded preparation; local saving is not confirmed.')
    } catch (reason) {
      if (active.current !== controller) return
      setMessage('')
      if (controller.signal.aborted) {
        setMessage('Download cancelled. A preparation event may already be recorded in custody.')
      } else {
        setError(reason instanceof Error ? reason.message : 'Download failed. Review custody before retrying.')
      }
    } finally {
      if (active.current === controller) {
        active.current = null
        setBusy(false)
        onAttempt()
      }
    }
  }

  return (
    <section className="evidence-panel">
      <h2>Retrieve evidence copy</h2>
      <p>Prepare a verified copy of the original bytes, then save it as a .bin file. No preview or analysis is performed.</p>
      <p className="muted">
        Each preparation is recorded in custody. Retrying creates another preparation attempt. Browser limit: 100 MiB.
      </p>
      <div className="actions">
        <button disabled={busy || size > MAX_DOWNLOAD_BYTES} onClick={() => void prepare()}>
          <svg aria-hidden="true" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="7 10 12 15 17 10" />
            <line x1="12" y1="15" x2="12" y2="3" />
          </svg>
          Prepare download
        </button>
        {busy && (
          <button className="secondary" onClick={() => active.current?.abort()}>
            Cancel download
          </button>
        )}
        {ready && (
          <>
            <a className="button-link" href={ready} download={downloadFilename(id)}>
              <svg aria-hidden="true" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="7 10 12 15 17 10" />
                <line x1="12" y1="15" x2="12" y2="3" />
              </svg>
              Save evidence copy
            </a>
            <button
              className="secondary"
              onClick={() => {
                discard()
                setMessage('Prepared browser copy discarded.')
              }}
            >
              Discard copy
            </button>
          </>
        )}
      </div>
      {size > MAX_DOWNLOAD_BYTES && <p className="error">Evidence exceeds the browser download limit.</p>}
      {message && <p role="status" style={{ color: 'var(--accent)', fontWeight: 500 }}>{message}</p>}
      {error && <p role="alert">{error}</p>}
    </section>
  )
}
