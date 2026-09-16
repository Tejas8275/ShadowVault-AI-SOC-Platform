import tempfile
import unittest
from pathlib import Path
from uuid import uuid4, UUID
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, OperationalError
from app.core.config import BACKEND_DIR, Settings
from app.core.security import token_digest
from app.db.migrate import upgrade_database
from app.db.session import build_engine, build_session_factory
from app.main import create_app
from app.models import Evidence, Incident, User, TimelineEvent, CustodyEvent, Agent, CollectionJob
from app.models.common import utc_now
from app.services.custody import verify_chain


class TimelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=BACKEND_DIR)
        root = Path(self.temp.name)
        self.settings = Settings(_env_file=None, environment='test', database_url=f'sqlite:///{root.as_posix()}/test.db',
            evidence_dir=root / 'evidence', operator_token_sha256=token_digest('sv_operator_' + 'T' * 43))
        upgrade_database(self.settings)
        self.engine = build_engine(self.settings)
        self.factory = build_session_factory(self.engine)
        with self.factory() as db:
            owner = User(email='timeline@example.test', display_name='Investigator', password_hash='!disabled')
            other = User(email='other@example.test', display_name='Other', password_hash='!disabled')
            own_case = Incident(title='Owned', created_by=owner)
            foreign_case = Incident(title='Foreign', created_by=other)
            db.add_all([own_case, foreign_case]); db.flush()
            records = [Evidence(incident_id=case.id, collected_by_id=user.id, filename='original.bin',
                        size_bytes=3, sha256='a' * 64, storage_key=str(uuid4()))
                       for case, user in [(own_case, owner), (foreign_case, other)]]
            db.add_all(records); db.commit()
            self.settings.operator_user_id = owner.id
            self.incident_id, self.foreign_incident = own_case.id, foreign_case.id
            self.evidence_id, self.foreign_evidence = [e.id for e in records]
        self.client = TestClient(create_app(self.settings)); self.client.__enter__()
        self.headers = {'Authorization': 'Bearer sv_operator_' + 'T' * 43}
        self.base = '/api/v2/investigation'

    def tearDown(self):
        self.client.__exit__(None, None, None); self.engine.dispose(); self.temp.cleanup()

    def payload(self, **values):
        return {'occurred_at': '2026-09-06T12:30:00+05:30', 'title': 'Observed 100%_ activity',
                'source': 'Investigator observation', 'description': 'Explicitly reported',
                'source_locator': 'Record 12', 'submission_id': str(uuid4()), **values}

    def create(self, payload=None, evidence_id=None):
        return self.client.post(f'{self.base}/evidence/{evidence_id or self.evidence_id}/timeline-events',
                                headers=self.headers, json=payload or self.payload())

    def search(self, **params):
        return self.client.get(self.base + '/timeline-events', headers=self.headers,
                               params={'incident_id': str(self.incident_id), **params})

    def test_create_attribution_utc_and_safe_detail(self):
        response = self.create()
        self.assertEqual(response.status_code, 201, response.text)
        record = response.json()
        self.assertEqual(record['occurred_at'], '2026-09-06T07:00:00Z')
        self.assertEqual(record['reported_time'], '2026-09-06T12:30:00+05:30')
        self.assertEqual(record['recorded_by_label'], 'Investigator')
        self.assertEqual(record['recorded_by_id'], str(self.settings.operator_user_id))
        self.assertEqual(record['origin'], 'investigator')
        self.assertNotIn('request_sha256', record)
        details = self.client.get(f"{self.base}/timeline-events/{record['id']}", headers=self.headers)
        self.assertEqual(details.json(), record)
        self.assertNotIn('storage_key', details.text)

    def test_atomic_custody_baseline_and_original_metadata_unchanged(self):
        self.settings.evidence_dir.mkdir()
        original = self.settings.evidence_dir / 'untouched.blob'; original.write_bytes(b'abc')
        self.assertEqual(self.create().status_code, 201)
        with self.factory() as db:
            evidence = db.get(Evidence, self.evidence_id)
            self.assertEqual((evidence.metadata_revision, evidence.verification_status, evidence.sha256), (0, 'legacy', 'a' * 64))
            events = db.scalars(select(CustodyEvent).order_by(CustodyEvent.sequence)).all()
            self.assertEqual([e.event_type for e in events], ['baseline_registered', 'timeline_observation_added'])
            self.assertEqual(events[0].details['reason'], 'tracking_started_at_first_timeline_event')
            self.assertTrue(verify_chain(db, self.evidence_id))
        self.assertEqual(original.read_bytes(), b'abc')
        self.assertEqual(list(self.settings.evidence_dir.iterdir()), [original])

    def test_identical_retry_returns_receipt_without_duplicate_history(self):
        payload = self.payload()
        first = self.create(payload); again = self.create(payload)
        self.assertEqual((first.status_code, again.status_code), (201, 200))
        self.assertEqual(first.json(), again.json())
        self.assertEqual(self.create({**payload, 'description': 'Changed'}).status_code, 409)
        with self.factory() as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(TimelineEvent)), 1)
            self.assertEqual(db.scalar(select(func.count()).select_from(CustodyEvent)), 2)

    def test_every_endpoint_auth_and_owner_boundary(self):
        record = self.create().json()
        routes = [('get', '/timeline-events', None), ('get', f"/timeline-events/{record['id']}", None),
                  ('post', f'/evidence/{self.evidence_id}/timeline-events', self.payload())]
        for method, path, body in routes:
            for headers in ({}, {'Authorization': 'Bearer sv_agent_' + 'T' * 43}):
                response = self.client.request(method, self.base + path, headers=headers, **({'json': body} if body else {}))
                self.assertEqual(response.status_code, 401)
        self.assertEqual(self.create(evidence_id=self.foreign_evidence).status_code, 404)
        self.assertEqual(self.search(incident_id=str(self.foreign_incident)).status_code, 404)
        self.assertEqual(self.search(evidence_id=str(self.foreign_evidence)).status_code, 404)
        with self.factory() as db:
            db.get(User, self.settings.operator_user_id).is_active = False; db.commit()
        self.assertEqual(self.search().status_code, 401)

    def test_legacy_visibility_and_foreign_event_not_found(self):
        with self.factory() as db:
            for case in (self.incident_id, self.foreign_incident):
                db.add(TimelineEvent(incident_id=case, recorded_by_id=self.settings.operator_user_id,
                    occurred_at=utc_now(), title='Legacy', source='Original'))
            db.commit()
            foreign = db.scalar(select(TimelineEvent).where(TimelineEvent.incident_id == self.foreign_incident)).id
        page = self.search(origin='legacy').json()
        self.assertEqual(page['total'], 1)
        self.assertIsNone(page['items'][0]['evidence_id'])
        self.assertIsNone(page['items'][0]['recorded_by_label'])
        self.assertEqual(self.client.get(f'{self.base}/timeline-events/{foreign}', headers=self.headers).status_code, 404)

    def test_linked_event_obeys_job_owner_even_when_incident_owned(self):
        with self.factory() as db:
            other = db.scalar(select(User).where(User.email == 'other@example.test'))
            agent = Agent(name='Foreign owner', collector_version='1', registered_by_id=other.id,
                          token_sha256='b' * 64, token_expires_at=utc_now())
            db.add(agent); db.flush()
            job = CollectionJob(incident_id=self.incident_id, requested_by_id=other.id, agent_id=agent.id, selected_files=[])
            db.add(job); db.flush()
            evidence = db.get(Evidence, self.evidence_id)
            evidence.collection_job_id = job.id; evidence.collection_item_id = uuid4()
            evidence.source_path = r'C:\fixture.bin'; evidence.collected_at = utc_now(); evidence.verified_at = utc_now(); evidence.verification_status = 'verified'
            event = TimelineEvent(incident_id=self.incident_id, evidence_id=evidence.id,
                recorded_by_id=other.id, title='Restricted', source='Original', occurred_at=utc_now())
            db.add(event); db.commit(); event_id = event.id
        self.assertEqual(self.search().json()['total'], 0)
        self.assertEqual(self.client.get(f'{self.base}/timeline-events/{event_id}', headers=self.headers).status_code, 404)
        self.assertEqual(self.create().status_code, 404)

    def test_filters_literal_search_range_and_cursor_ties(self):
        for _ in range(3): self.assertEqual(self.create().status_code, 201)
        for sort in ('oldest', 'newest'):
            seen = []; cursor = None
            while True:
                response = self.search(limit=1, sort=sort, **({'cursor': cursor} if cursor else {}))
                self.assertEqual(response.status_code, 200, response.text)
                page = response.json(); seen.extend(e['id'] for e in page['items'])
                cursor = page['next_cursor']
                if cursor is None: break
            self.assertEqual(len(set(seen)), 3)
        self.assertEqual(self.search(q='%_', origin='investigator', evidence_id=str(self.evidence_id)).json()['total'], 3)
        self.assertEqual(self.search(occurred_from='2026-09-06T07:00:00Z', occurred_to='2026-09-06T07:00:00Z').json()['total'], 3)
        self.assertEqual(self.search(q='missing').json()['total'], 0)
        cursor = self.search(limit=1).json()['next_cursor']
        self.assertEqual(self.search(cursor=cursor, q='changed').status_code, 422)
        self.assertEqual(self.search(cursor='!!!').status_code, 422)

    def test_request_validation_and_server_owned_fields(self):
        for change in ({'occurred_at': '2026-09-06T12:00:00'}, {'occurred_at': 123}, {'title': ''},
                       {'source': ''}, {'description': 'x' * 10001}, {'title': '\x00'},
                       {'recorded_by_id': str(uuid4())}, {'origin': 'legacy'}, {'incident_id': str(self.foreign_incident)}):
            self.assertEqual(self.create(self.payload(**change)).status_code, 422)
        for change in ({'limit': 101}, {'occurred_from': '2026-10-01T00:00:00Z', 'occurred_to': '2026-01-01T00:00:00Z'}, {'extra': 'x'}):
            self.assertEqual(self.search(**change).status_code, 422)
        response = self.client.post(f'{self.base}/evidence/{self.evidence_id}/timeline-events', headers=self.headers, content='x' * 131073)
        self.assertEqual(response.status_code, 413)

    def test_custody_failure_rolls_back_every_write(self):
        from app.services import custody
        original = custody.append_event
        def fail(*args, **kwargs):
            if kwargs['event_type'] == 'timeline_observation_added':
                raise OperationalError('injected', {}, Exception())
            return original(*args, **kwargs)
        with patch('app.services.custody.append_event', side_effect=fail):
            self.assertEqual(self.create().status_code, 503)
        with self.factory() as db:
            for model in (TimelineEvent, CustodyEvent):
                self.assertEqual(db.scalar(select(func.count()).select_from(model)), 0)
            self.assertEqual(db.get(Evidence, self.evidence_id).custody_sequence, 0)

    def test_commit_failure_can_retry_same_submission(self):
        payload = self.payload()
        with patch('sqlalchemy.orm.Session.commit', side_effect=OperationalError('injected', {}, Exception())):
            self.assertEqual(self.create(payload).status_code, 503)
        self.assertEqual(self.create(payload).status_code, 201)
        self.assertEqual(self.create(payload).status_code, 200)

    def test_new_observations_are_immutable_but_legacy_behavior_remains(self):
        id = UUID(self.create().json()['id'])
        with self.factory() as db:
            event = db.get(TimelineEvent, id); event.origin = 'legacy'
            with self.assertRaises(ValueError): db.flush()
            db.rollback(); event = db.get(TimelineEvent, id); db.expire(event)
            event.origin = 'legacy'
            with self.assertRaises(ValueError): db.flush()
            db.rollback(); db.delete(db.get(TimelineEvent, id))
            with self.assertRaises(ValueError): db.flush()
            db.rollback()
            old = TimelineEvent(incident_id=self.incident_id, recorded_by_id=self.settings.operator_user_id,
                title='Legacy', source='Original', occurred_at=utc_now())
            db.add(old); db.commit(); old.title = 'Legacy update'; db.commit()
        self.assertEqual(self.client.delete(f'{self.base}/timeline-events/{id}', headers=self.headers).status_code, 405)

    def test_database_rejects_cross_incident_and_missing_provenance(self):
        with self.factory() as db:
            for values in ({'evidence_id': self.foreign_evidence}, {'origin': 'investigator'}):
                db.add(TimelineEvent(incident_id=self.incident_id, recorded_by_id=self.settings.operator_user_id,
                    occurred_at=utc_now(), title='Invalid', source='test', **values))
                with self.assertRaises(IntegrityError): db.flush()
                db.rollback()

    def test_concurrent_identical_submissions_resolve_to_one_record(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from fastapi import HTTPException
        from app.schemas.timeline import TimelineCreate
        from app.services.timeline import create
        payload = self.payload(); barrier = Barrier(2)
        def submit(_):
            with self.factory() as db:
                actor = db.get(User, self.settings.operator_user_id); barrier.wait(timeout=10)
                try:
                    result, created = create(db, self.evidence_id, actor, TimelineCreate(**payload)); db.commit()
                    return 201 if created else 200
                except (IntegrityError, OperationalError): db.rollback(); return 409
                except HTTPException as error: db.rollback(); return error.status_code
        with ThreadPoolExecutor(max_workers=2) as pool: statuses = list(pool.map(submit, range(2)))
        self.assertIn(201, statuses)
        self.assertTrue(all(status in (200, 201, 409) for status in statuses))
        self.assertEqual(self.create(payload).status_code, 200)
        self.assertEqual(self.search().json()['total'], 1)
        with self.factory() as db: self.assertTrue(verify_chain(db, self.evidence_id))

    def test_phase2a_upload_timeline_and_repeat_preserve_bytes_and_receipt(self):
        import hashlib
        agent = self.client.post('/api/v1/agents', headers=self.headers, json={'name': 'Timeline compatibility'}).json()
        job = self.client.post('/api/v1/collection-jobs', headers=self.headers, json={
            'incident_id': str(self.incident_id), 'agent_id': agent['id'],
            'files': [{'source_path': r'C:\Cases\timeline.bin', 'max_bytes': 10}]}).json()
        headers = {'Authorization': f"Bearer {agent['token']}", 'Content-Type': 'application/octet-stream',
            'X-Evidence-SHA256': hashlib.sha256(b'abc').hexdigest(), 'X-Evidence-Size': '3', 'X-Collected-At': '2026-09-06T00:00:00Z'}
        path = f"/api/v1/agents/jobs/{job['id']}/files/{job['files'][0]['id']}"
        first = self.client.put(path, content=b'abc', headers=headers)
        self.assertEqual(first.status_code, 201, first.text)
        self.assertEqual(self.create(evidence_id=first.json()['id']).status_code, 201)
        repeat = self.client.put(path, content=b'abc', headers=headers)
        self.assertEqual(repeat.status_code, 200, repeat.text)
        self.assertEqual(repeat.json(), first.json())
        with self.factory() as db:
            evidence = db.get(Evidence, UUID(first.json()['id']))
            self.assertEqual((self.settings.evidence_dir / evidence.storage_key).read_bytes(), b'abc')
            self.assertEqual(evidence.metadata_revision, 0)
            self.assertTrue(verify_chain(db, evidence.id))
