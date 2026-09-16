import { useEffect, useState, type ReactNode } from 'react'

export function Layout({ children, login }: { children: ReactNode; login: boolean }) {
  const [collapsed, setCollapsed] = useState(false)
  const [time, setTime] = useState(() => new Date().toISOString().substring(11, 19))

  useEffect(() => {
    const timer = setInterval(() => {
      setTime(new Date().toISOString().substring(11, 19))
    }, 1000)
    return () => clearInterval(timer)
  }, [])

  return (
    <div className={`workspace ${collapsed ? 'collapsed' : ''}`}>
      <a className="skip-link" href="#main-content">Skip to content</a>
      <aside className="sidebar">
        <div className="sidebar-header">
          <a className="brand" href="#dashboard">
            <span className="brand-mark">SV</span>
            <span>ShadowVault AI</span>
          </a>
          <button
            type="button"
            className="sidebar-toggle"
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            onClick={() => setCollapsed(v => !v)}
          >
            <svg aria-hidden="true" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              {collapsed ? (
                <>
                  <polyline points="13 17 18 12 13 7" />
                  <polyline points="6 17 11 12 6 7" />
                </>
              ) : (
                <>
                  <polyline points="11 17 6 12 11 7" />
                  <polyline points="18 17 13 12 18 7" />
                </>
              )}
            </svg>
          </button>
        </div>

        <p className="nav-label">Investigation workspace</p>
        <nav aria-label="Main navigation">
          <a href="#dashboard" aria-current={!login && !window.location.hash.startsWith('#evidence') && !window.location.hash.startsWith('#timeline') && !window.location.hash.startsWith('#cases') ? 'page' : undefined}>
            <svg className="nav-icon" aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="7" height="7" />
              <rect x="14" y="3" width="7" height="7" />
              <rect x="14" y="14" width="7" height="7" />
              <rect x="3" y="14" width="7" height="7" />
            </svg>
            <span>Overview</span>
          </a>
          <a href="#cases" aria-current={window.location.hash.startsWith('#cases') ? 'page' : undefined}>
            <svg className="nav-icon" aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
            </svg>
            <span>Cases</span>
          </a>
          <a href="#evidence" aria-current={window.location.hash.startsWith('#evidence') ? 'page' : undefined}>
            <svg className="nav-icon" aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              <path d="m9 12 2 2 4-4" />
            </svg>
            <span>Evidence</span>
          </a>
          <a href="#timeline" aria-current={window.location.hash.startsWith('#timeline') ? 'page' : undefined}>
            <svg className="nav-icon" aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
            <span>Timeline</span>
          </a>
          <a href="#login" aria-describedby="sign-in-availability" aria-current={login ? 'page' : undefined}>
            <svg className="nav-icon" aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
              <path d="M7 11V7a5 5 0 0 1 10 0v4" />
            </svg>
            <span>Operator connection</span>
          </a>
        </nav>
        <p id="sign-in-availability" className="footnote">Access uses a provisioned operator token.</p>
        <p className="sidebar-note">Evidence  /  Timeline  /  Custody<br /><strong>Investigation workspace</strong></p>
      </aside>
      <div className="workspace-body">
        <header className="topbar">
          <div className="topbar-left">
            <span>Digital forensics &amp; incident response</span>
            <span className="soc-telemetry-badge"><span className="pulse-dot" />SOC ACTIVE</span>
          </div>
          <div className="topbar-right">
            <span className="soc-clock" title="SOC Operational UTC Clock">
              <svg aria-hidden="true" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <polyline points="12 6 12 12 16 14" />
              </svg>
              {time} UTC
            </span>
            <span className="badge">Development</span>
          </div>
        </header>
        <main id="main-content" tabIndex={-1}>{children}</main>
      </div>
    </div>
  )
}
