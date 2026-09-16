import unittest
from pydantic import SecretStr
from uuid import UUID, uuid4
from unittest.mock import patch
from sqlalchemy import MetaData, select
from sqlalchemy.exc import OperationalError
import test_incidents
import test_indicators
from app.models import Evidence, Incident, TimelineEvent, IndicatorObservation
from app.models.common import utc_now
from app.services import case_report


class ReportTests(unittest.TestCase):
    setUp = test_incidents.CaseTests.setUp
    tearDown = test_incidents.CaseTests.tearDown
    evidence = test_indicators.IndicatorTests.evidence
    add = test_indicators.IndicatorTests.add

    def report(self, case=None):
        return self.client.get(self.base + '/' + (case or self.id) + '/report-draft', headers=self.headers)

    def test_create_view_empty_transient_and_existing_contract(self):
        original = self.client.get(self.base+'/'+self.id, headers=self.headers).json()
        response = self.report()
        self.assertEqual(response.status_code, 200, response.text)
        draft = response.json()
        self.assertEqual(draft['case'], original)
        self.assertEqual(draft['status'], 'draft')
        self.assertTrue(draft['generated_at'].endswith('Z'))
        self.assertEqual(sum(draft['summary'].values()), 0)
        self.assertEqual(response.headers['cache-control'], 'no-store')
        self.assertEqual(self.report().json()['sections'], draft['sections'])
        self.assertEqual(self.client.get(self.base+'/'+self.id, headers=self.headers).json(), original)

    def test_authentication_and_foreign_case(self):
        path = self.base+'/'+self.id+'/report-draft'
        self.assertEqual(self.client.get(path).status_code, 401)
        self.assertEqual(self.client.get(path, headers={'Authorization':'Bearer wrong'}).status_code, 401)
        self.assertEqual(self.report(self.foreign).status_code, 404)

    def test_complete_sources_corrections_citations_and_preservation(self):
        eid = self.evidence()
        original = self.add(eid, source_locator='<script>inert citation</script>').json()
        correction = self.add(eid, raw_value='correct.example', supersedes_id=original['id']).json()
        note = self.client.post('/api/v2/investigation/evidence/'+eid+'/notes', headers=self.headers,
            json={'expected_revision':0, 'body':'Investigator recorded this note'}).json()['note']
        event = self.client.post('/api/v2/investigation/evidence/'+eid+'/timeline-events', headers=self.headers,
            json={'title':'Observation', 'source':'Investigator', 'source_locator':'line 4',
                  'occurred_at':'2026-01-01T12:00:00+05:30', 'submission_id':str(uuid4())}).json()
        self.client.patch(self.base+'/'+self.id, headers=self.headers,
            json={'expected_revision':0,'status':'investigating','title':'Own','severity':'high'})
        with self.engine.connect() as conn:
            metadata = MetaData(); metadata.reflect(conn)
            before = {n:conn.execute(select(t)).all() for n,t in metadata.tables.items()}
        with patch('app.services.evidence_reader.open_original', side_effect=AssertionError('no blob reads')):
            response = self.report()
        self.assertEqual(response.status_code, 200, response.text)
        draft = response.json(); records = {r['citation']:r for s in draft['sections'] for r in s['records']}
        self.assertIn('note:'+note['id'], records)
        self.assertEqual(records['timeline:'+event['id']]['fields']['source_locator'], 'line 4')
        self.assertEqual(records['indicator:'+original['id']]['fields']['superseded_by_id'], correction['id'])
        self.assertEqual(records['indicator:'+original['id']]['fields']['source_locator'], '<script>inert citation</script>')
        self.assertNotIn('storage_key', response.text)
        self.assertNotIn('source_path', response.text)
        self.assertNotIn('request_sha256', response.text)
        with self.engine.connect() as conn:
            for name, rows in before.items(): self.assertEqual(conn.execute(select(metadata.tables[name])).all(), rows, name)

    def test_hidden_evidence_indicators_and_timeline_never_leak(self):
        visible = self.evidence(); hidden = self.evidence(hidden=True); foreign = self.evidence(foreign=True)
        self.add(visible)
        with self.factory() as db:
            for eid in (hidden, foreign):
                e = db.get(Evidence, UUID(eid))
                db.add(TimelineEvent(incident_id=e.incident_id, evidence_id=e.id, recorded_by_id=e.collected_by_id,
                    occurred_at=utc_now(), title='PRIVATE SENTINEL', source='legacy'))
                db.add(IndicatorObservation(incident_id=e.incident_id, evidence_id=e.id, kind='domain',
                    raw_value='private.example', normalized_value='private.example', source_kind='manual',
                    created_by_id=e.collected_by_id, actor_label='PRIVATE SENTINEL', submission_id=uuid4(), request_sha256='f'*64))
            db.commit()
        response = self.report()
        self.assertEqual(response.status_code, 200, response.text)
        for text in (hidden, foreign, 'PRIVATE SENTINEL', 'private.example'): self.assertNotIn(text, response.text)
        self.assertEqual(response.json()['summary']['Evidence records'], 1)

    def test_all_pages_and_row_byte_timeout_limits_fail_closed(self):
        with self.factory() as db:
            for index in range(55):
                db.add(Evidence(incident_id=UUID(self.id), collected_by_id=self.settings.operator_user_id,
                    filename=str(index), size_bytes=0, sha256='a'*64, storage_key=str(uuid4())))
            db.commit()
        self.assertEqual(self.report().json()['summary']['Evidence records'], 55)
        for setting, amount, status in [('MAX_ROWS',54,413),('MAX_BYTES',10,413),('MAX_SECONDS',-1,503)]:
            with patch.object(case_report, setting, amount):
                response = self.report(); self.assertEqual(response.status_code, status, response.text)
                self.assertNotIn('sections', response.json())
        self.assertEqual(self.report().status_code, 200)  # snapshot/handler released on failure

    def test_failure_sanitization(self):
        with patch.object(case_report, 'build', side_effect=OperationalError('private path',{},Exception('secret'))):
            response = self.report()
        self.assertEqual(response.status_code,503)
        self.assertNotIn('secret',response.text)
        self.assertNotIn('private path',response.text)

    def test_sqlite_snapshot_is_explicit_and_consistent_during_concurrent_write(self):
        # WAL allows a concurrent writer while the report's explicit read snapshot stays pinned.
        with self.engine.connect() as conn: conn.exec_driver_sql('PRAGMA journal_mode=WAL')
        self.evidence()
        require = case_report.incidents.require_incident
        changed = False
        def concurrent(db, ident, actor):
            nonlocal changed
            record = require(db, ident, actor)
            if not changed:
                changed = True
                with self.factory() as writer:
                    writer.get(Incident, UUID(self.id)).title = 'Concurrent title'
                    writer.add(Evidence(incident_id=UUID(self.id), collected_by_id=actor,
                        filename='Concurrent evidence',size_bytes=0,sha256='b'*64,storage_key=str(uuid4())))
                    writer.commit()
            return record
        with patch.object(case_report.incidents,'require_incident',side_effect=concurrent):
            response=self.report()
        self.assertEqual(response.status_code,200,response.text)
        self.assertNotEqual(response.json()['case']['title'],'Concurrent title')
        self.assertEqual(response.json()['summary']['Evidence records'],1)
        self.assertEqual(self.report().json()['summary']['Evidence records'],2)

    def test_authorization_rechecked_after_snapshot(self):
        build = case_report.build
        def revoked(*args):
            draft = build(*args)
            self.settings.operator_token_sha256 = SecretStr('0'*64)
            return draft
        with patch.object(case_report, 'build', side_effect=revoked):
            response = self.report()
        self.assertEqual(response.status_code,401,response.text)
