import { useEffect, useState } from 'react'
import { healthService } from '../services/health'

export function DashboardPage() {
  const [connection, setConnection] = useState<'checking' | 'connected' | 'unavailable'>('checking')
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let active = true
    healthService.check().then(
      () => { if (active) setConnection('connected') },
      () => { if (active) setConnection('unavailable') },
    )
    return () => { active = false }
  }, [attempt])

  return (
    <>
      <p className="eyebrow">Investigation command center</p>
      <h1>Investigation dashboard</h1>
      <p className="intro">Track your cases, examine evidence, and build an attributable investigation record.</p>

      <section className="connection-panel" aria-labelledby="connection-title">
        <div>
          <h2 id="connection-title">System connection</h2>
          <p role="status" className={`connection-${connection}`}>
            {connection === 'checking'
              ? 'Checking backend and database…'
              : connection === 'connected'
                ? 'Backend and database connected'
                : 'Unable to reach the backend or database. Start the backend, then retry.'}
          </p>
        </div>
        <button
          className="secondary"
          disabled={connection === 'checking'}
          onClick={() => { setConnection('checking'); setAttempt(v => v + 1) }}
        >
          Check connection
        </button>
      </section>

      <nav className="quick-links" aria-label="Investigation shortcuts">
        <a href="#cases">
          <strong>
            Cases
            <span className="badge" style={{ fontSize: '0.7rem' }}>Incidents</span>
          </strong>
          <span>Manage investigations and history →</span>
        </a>
        <a href="#evidence">
          <strong>
            Evidence
            <span className="badge" style={{ fontSize: '0.7rem' }}>Custody</span>
          </strong>
          <span>Inspect records and custody →</span>
        </a>
        <a href="#timeline">
          <strong>
            Timeline
            <span className="badge" style={{ fontSize: '0.7rem' }}>Chronology</span>
          </strong>
          <span>Review attributed observations →</span>
        </a>
      </nav>

      <p className="footnote">Case history records case changes. Evidence custody and timeline observations remain distinct records.</p>
    </>
  )
}
