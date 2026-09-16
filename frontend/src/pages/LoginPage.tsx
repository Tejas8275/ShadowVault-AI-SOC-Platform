import type { FormEventHandler } from 'react'

export function LoginPage({ pending, error, onSubmit }: {
  pending: boolean; error: string; onSubmit: FormEventHandler<HTMLFormElement>
}) {
  return <section className="operator-panel" aria-labelledby="operator-title">
    <div className="operator-brand"><span className="brand-mark" aria-hidden="true">SV</span><span>ShadowVault AI<span className="operator-subtitle">Investigation access</span></span></div>
    <p className="eyebrow">Operator disconnected</p>
    <h1 id="operator-title">Connect operator</h1>
    <p id="operator-guidance">An operator token is required to access your authorized cases and evidence. Use the token provisioned by your local administrator.</p>
    <form onSubmit={onSubmit} aria-busy={pending} aria-describedby="operator-guidance operator-privacy">
      <label htmlFor="operator-token">Operator token</label>
      <input id="operator-token" name="operator-token" type="password" autoComplete="off" autoCapitalize="none" spellCheck={false} required maxLength={256} disabled={pending} aria-describedby={error?'operator-format operator-error':'operator-format'} aria-invalid={error?true:undefined} />
      <p id="operator-format" className="muted operator-hint">Paste only the token, without quotes or surrounding spaces. Email and password sign-in is not supported.</p>
      {error && <p id="operator-error" className="error" role="alert">{error}</p>}
      <button disabled={pending}>{pending?'Connecting…':'Connect operator'}</button>
    </form>
    <p role="status" aria-live="polite">{pending?'Checking operator access…':''}</p>
    <p id="operator-privacy" className="operator-privacy">The token stays in this tab’s memory and is never saved to browser storage. Disconnecting or reloading the tab clears the connection and transient investigation work.</p>
  </section>
}
