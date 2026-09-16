import { useEffect, useState } from 'react'
import { Layout } from './components/Layout'
import { InvestigationWorkspace } from './features/evidence/InvestigationWorkspace'

export function App() {
  const [login, setLogin] = useState(window.location.hash === '#login')
  const [evidence, setEvidence] = useState(window.location.hash.startsWith('#evidence'))
  const [evidenceId, setEvidenceId] = useState(window.location.hash.split('/')[1])
  const [route, setRoute] = useState(window.location.hash)

  useEffect(() => {
    function navigate() {
      if (window.location.hash === '#main-content') return
      setLogin(window.location.hash === '#login')
      setEvidence(window.location.hash.startsWith('#evidence'))
      setEvidenceId(window.location.hash.split('/')[1])
      setRoute(window.location.hash)
      document.getElementById('main-content')?.focus()
    }
    window.addEventListener('hashchange', navigate)
    return () => window.removeEventListener('hashchange', navigate)
  }, [])

  useEffect(() => {
    document.title = `${login ? 'Operator connection' : evidence ? 'Evidence' : route.startsWith('#cases') ? 'Cases' : route.startsWith('#timeline') ? 'Timeline' : 'Dashboard'} | ShadowVault AI`
  }, [login, evidence, route])

  const timeline = route.startsWith('#timeline')
  const cases = route === '#cases' || route.startsWith('#cases/')
  return <Layout login={login}>
    <InvestigationWorkspace connectionOnly={login} overview={!evidence && !timeline && !cases && !login} cases={cases} caseId={cases ? route.split('/')[1] : undefined} caseEvidenceId={cases && route.split('/')[2] === 'evidence' ? route.split('/')[3] : undefined} evidenceId={evidence ? evidenceId : undefined} timeline={timeline}
      timelineIncidentId={route.startsWith('#timeline/') ? route.split('/')[1] : undefined}
      timelineEventId={route.startsWith('#timeline-event/') ? route.split('/')[1] : undefined} />
  </Layout>
}
