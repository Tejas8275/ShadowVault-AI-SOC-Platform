import type { Evidence } from './contracts'

const results = {
  not_checked: ['○', 'Not checked', 'No completed subsequent integrity check is recorded.'],
  matches: ['✓', 'Matches', 'Bytes matched the recorded expectations at the displayed check time. This is not continuous monitoring.'],
  mismatch: ['!', 'Mismatch', 'A subsequent check reported different content or size. Investigate before relying on this evidence.'],
  missing: ['!', 'Missing', 'The subsequent check could not find the evidence object.'],
  unavailable: ['?', 'Unavailable', 'The subsequent check could not establish content integrity.'],
} as const

export function IntegrityStatus({ evidence }: { evidence: Evidence }) {
  const [icon, label, explanation] = results[evidence.integrity_result]
  return (
    <section className="evidence-panel" style={{ borderLeft: '4px solid var(--accent)' }}>
      <h2>Evidence integrity</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))', gap: '1rem', margin: '1rem 0' }}>
        <div style={{ padding: '1rem', background: 'var(--bg-void)', borderRadius: '6px', border: '1px solid var(--border-subtle)' }}>
          <h3 style={{ marginTop: 0, fontSize: '0.95rem' }}>Initial upload verification</h3>
          <p style={{ fontWeight: 600, color: evidence.initial_verification_status === 'verified' ? 'var(--status-nominal)' : 'var(--muted)' }}>
            {evidence.initial_verification_status === 'verified' ? 'Verified at upload' : 'Legacy — upload verification not recorded'}
          </p>
          <p style={{ fontSize: '0.82rem', fontFamily: 'var(--font-mono)', color: 'var(--muted)' }}>
            {evidence.initial_verified_at ? `${new Date(evidence.initial_verified_at).toISOString()} (UTC)` : 'No initial verification timestamp'}
          </p>
        </div>

        <div style={{ padding: '1rem', background: 'var(--bg-void)', borderRadius: '6px', border: '1px solid var(--border-subtle)' }}>
          <h3 style={{ marginTop: 0, fontSize: '0.95rem' }}>Subsequent integrity result</h3>
          <p className={`integrity-${evidence.integrity_result}`} style={{ fontSize: '1.05rem', margin: '0.35rem 0' }}>
            <span aria-hidden="true">{icon} </span>
            <strong>{label}</strong>
          </p>
          <p style={{ fontSize: '0.85rem', color: 'var(--muted)' }}>{explanation}</p>
          {evidence.integrity_checked_at && (
            <p style={{ fontSize: '0.82rem', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)' }}>
              Checked: {new Date(evidence.integrity_checked_at).toISOString()} (UTC)
            </p>
          )}
        </div>
      </div>
      <p className="muted">Check execution is not available in this phase. Pending-check state is not exposed by this API.</p>
    </section>
  )
}
