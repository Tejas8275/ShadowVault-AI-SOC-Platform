import tempfile
import unittest
from pathlib import Path
from uuid import UUID, uuid4
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError, OperationalError
from app.core.config import BACKEND_DIR, Settings
from app.core.security import token_digest
from app.db.migrate import upgrade_database
from app.db.session import build_engine, build_session_factory
from app.main import create_app
from app.models import CustodyEvent, Evidence, EvidenceIntegrityCheck, EvidenceNote, EvidenceTag, Incident, User
from app.models.common import utc_now
from app.services.custody import verify_chain


class InvestigationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=BACKEND_DIR)
        self.settings = Settings(_env_file=None, environment='test',
            evidence_dir=Path(self.temp.name) / 'evidence',
            database_url=f'sqlite:///{Path(self.temp.name).as_posix()}/test.db',
            operator_token_sha256=token_digest('sv_operator_' + 'A' * 43))
        upgrade_database(self.settings)
        self.engine = build_engine(self.settings)
        self.factory = build_session_factory(self.engine)
        with self.factory() as db:
            user = User(email='owner@example.com', display_name='Owner', password_hash='!disabled')
            other = User(email='other@example.com', display_name='Other', password_hash='!disabled')
            incident = Incident(title='Case', created_by=user)
            foreign = Incident(title='Other', created_by=other)
            db.add_all([incident, foreign])
            db.flush()
            now = utc_now()
            records = [Evidence(incident_id=case.id, collected_by_id=owner.id, filename=name,
                                size_bytes=size, sha256=digest * 64, storage_key=str(uuid4()), created_at=now)
                       for case, owner, name, size, digest in [(incident, user, '100%_sample.bin', 10, 'a'),
                            (incident, user, 'ordinary.bin', 20, 'b'), (foreign, other, 'secret.bin', 30, 'c')]]
            db.add_all(records)
            db.commit()
            self.settings.operator_user_id = user.id
            self.ids = [record.id for record in records]
            self.incident_id = incident.id
        self.client = TestClient(create_app(self.settings))
        self.client.__enter__()
        self.headers = {'Authorization': 'Bearer sv_operator_' + 'A' * 43}
        self.base = '/api/v2/investigation/evidence'
        self.url = f'{self.base}/{self.ids[0]}'

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.engine.dispose()
        self.temp.cleanup()

    def get(self, path=None, **kwargs):
        return self.client.get(path or self.url, headers=self.headers, **kwargs)

    def annotate(self, revision=0, **values):
        return self.client.patch(self.url + '/annotations', headers=self.headers,
                                 json={'expected_revision': revision, **values})

    def note(self, revision=0, body='Observation'):
        return self.client.post(self.url + '/notes', headers=self.headers,
                                json={'expected_revision': revision, 'body': body})

    def test_details_are_safe_and_reads_do_not_write(self):
        response = self.get()
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertEqual(data['initial_verification_status'], 'legacy')
        self.assertEqual(data['integrity_result'], 'not_checked')
        self.assertFalse(data['custody_started'])
        self.assertNotIn('storage_key', data)
        self.assertNotIn('password_hash', response.text)
        self.assertEqual(self.get(self.url + '/custody').json()['items'], [])
        self.assertEqual(self.get(self.url + '/notes').json()['items'], [])
        with self.factory() as db:
            self.assertEqual(db.scalar(select(func.count()).select_from(CustodyEvent)), 0)

    def test_annotations_tags_revision_and_custody(self):
        response = self.annotate(display_title='Important', review_state='in_review', tags=[' Urgent ', 'urgent', 'disk'])
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertEqual(data['tags'], ['disk', 'urgent'])
        self.assertEqual(data['metadata_revision'], 1)
        self.assertEqual(data['display_title'], 'Important')
        self.assertEqual(data['custody_sequence'], 2)
        events = self.get(self.url + '/custody').json()['items']
        self.assertEqual([e['event_type'] for e in events], ['baseline_registered', 'annotations_updated'])
        self.assertEqual(events[1]['actor_user_id'], str(self.settings.operator_user_id))
        self.assertEqual(events[1]['actor_label'], 'Owner')
        self.assertTrue(events[1]['recorded_at'].endswith('Z'))
        self.assertEqual(events[1]['previous_hash'], events[0]['event_hash'])
        self.assertEqual(self.annotate(display_title='Stale').status_code, 409)
        self.assertEqual(self.annotate(1, display_title=None, tags=[]).status_code, 200)
        with self.factory() as db:
            self.assertTrue(verify_chain(db, self.ids[0]))
            self.assertEqual(db.get(Evidence, self.ids[0]).sha256, 'a' * 64)
        self.assertEqual(self.get().json()['display_title'], None)
        self.assertEqual(self.get().json()['tags'], [])

    def test_notes_are_attributed_paginated_and_append_only(self):
        first = self.note()
        self.assertEqual(first.status_code, 201, first.text)
        self.assertEqual(first.json()['note']['author_label'], 'Owner')
        self.assertEqual(self.note(1, 'Second').status_code, 201)
        self.assertEqual(self.note(1, 'Repeat').status_code, 409)
        page = self.get(self.url + '/notes', params={'limit': 1}).json()
        second = self.get(self.url + '/notes', params={'cursor': page['next_cursor']}).json()
        self.assertEqual([page['items'][0]['body'], second['items'][0]['body']], ['Observation', 'Second'])
        self.assertEqual(self.get().json()['note_count'], 2)
        with self.factory() as db:
            note = db.get(EvidenceNote, UUID(first.json()['note']['id']))
            note.body = 'tamper'
            with self.assertRaises(ValueError):
                db.flush()
            db.rollback()
            db.delete(db.get(EvidenceNote, UUID(first.json()['note']['id'])))
            with self.assertRaises(ValueError):
                db.flush()
        self.assertEqual(self.client.delete(self.url + '/notes', headers=self.headers).status_code, 405)

    def test_custody_pagination_and_tamper_detection(self):
        self.note()
        page = self.get(self.url + '/custody', params={'limit': 1}).json()
        self.assertEqual(page['next_sequence'], 1)
        self.assertEqual(self.get(self.url + '/custody', params={'after_sequence': 1}).json()['items'][0]['sequence'], 2)
        with self.factory() as db:
            self.assertTrue(verify_chain(db, self.ids[0]))
            event = db.scalar(select(CustodyEvent).where(CustodyEvent.sequence == 2))
            event.actor_label = 'Forged'
            with self.assertRaises(ValueError):
                db.flush()
            db.rollback()
            db.execute(update(CustodyEvent).where(CustodyEvent.sequence == 2).values(actor_label='Forged'))
            db.commit()
            self.assertFalse(verify_chain(db, self.ids[0]))

    def test_custody_failure_rolls_back_entire_annotation_and_note(self):
        from app.services import custody
        original = custody.append_event
        def fail_user_event(*args, **kwargs):
            if kwargs.get('actor_user'):
                raise OperationalError('injected', {}, Exception('unavailable'))
            return original(*args, **kwargs)
        with patch('app.services.custody.append_event', side_effect=fail_user_event):
            self.assertEqual(self.annotate(display_title='Lost', tags=['lost']).status_code, 503)
            self.assertEqual(self.note().status_code, 503)
        with self.factory() as db:
            evidence = db.get(Evidence, self.ids[0])
            self.assertEqual((evidence.metadata_revision, evidence.custody_sequence, evidence.display_title), (0, 0, None))
            for model in (CustodyEvent, EvidenceTag, EvidenceNote):
                self.assertEqual(db.scalar(select(func.count()).select_from(model)), 0)

    def test_commit_failure_rolls_back(self):
        with patch('sqlalchemy.orm.Session.commit', side_effect=OperationalError('injected', {}, Exception())):
            self.assertEqual(self.note().status_code, 503)
        self.assertEqual(self.get().json()['metadata_revision'], 0)
        self.assertEqual(self.get().json()['note_count'], 0)
        self.assertFalse(self.get().json()['custody_started'])

    def test_concurrent_metadata_writers_do_not_overwrite(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from fastapi import HTTPException
        from app.schemas.investigation import AnnotationPatch
        from app.services.evidence_metadata import annotate
        barrier = Barrier(2)
        def write(title):
            with self.factory() as db:
                actor = db.get(User, self.settings.operator_user_id)
                barrier.wait(timeout=10)
                try:
                    annotate(db, self.ids[0], actor, AnnotationPatch(expected_revision=0, display_title=title))
                    db.commit()
                    return 200
                except HTTPException as error:
                    db.rollback()
                    return error.status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(write, ['First', 'Second'])), [200, 409])
        data = self.get().json()
        self.assertEqual(data['metadata_revision'], 1)
        self.assertEqual(data['custody_sequence'], 2)
        with self.factory() as db:
            self.assertTrue(verify_chain(db, self.ids[0]))

    def test_annotation_foreign_keys_uniqueness_and_lengths(self):
        with self.factory() as db:
            for record in (EvidenceTag(evidence_id=uuid4(), tag='orphan'),
                           EvidenceTag(evidence_id=self.ids[0], tag=''),
                           EvidenceNote(evidence_id=self.ids[0], author_id=uuid4(), author_label='Orphan', body='note'),
                           EvidenceNote(evidence_id=self.ids[0], author_id=self.settings.operator_user_id, author_label='Owner', body='')):
                db.add(record)
                with self.assertRaises(IntegrityError):
                    db.flush()
                db.rollback()
            db.add_all([EvidenceTag(evidence_id=self.ids[0], tag='same'), EvidenceTag(evidence_id=self.ids[0], tag='same')])
            with self.assertRaises(IntegrityError):
                db.flush()

    def test_queued_integrity_check_does_not_claim_verification(self):
        with self.factory() as db:
            check = EvidenceIntegrityCheck(evidence_id=self.ids[0], requested_by_id=self.settings.operator_user_id,
                                           expected_sha256='a' * 64, expected_size_bytes=10)
            db.add(check)
            db.commit()
            self.assertEqual((check.status, check.result, check.attempts), ('queued', None, 0))
        self.assertEqual(self.get().json()['integrity_result'], 'not_checked')

    def test_search_filters_literal_wildcards_and_all_tags(self):
        self.annotate(tags=['disk', 'urgent'], review_state='reviewed', display_title='Useful')
        for params in ({'q': '%_'}, {'q': 'useful'}, {'sha256': 'A' * 64}, {'max_size': 10},
                       {'review_state': 'reviewed'}, {'tags': ['disk', 'urgent']}):
            response = self.get(self.base, params=params)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual([e['id'] for e in response.json()['items']], [str(self.ids[0])])
        self.assertEqual(self.get(self.base, params={'tags': ['disk', 'missing']}).json()['total'], 0)
        self.assertEqual(self.get(self.base).json()['total'], 2)
        self.assertEqual(self.get(self.base, params={'incident_id': str(self.incident_id)}).json()['total'], 2)
        self.assertEqual(self.get(self.base, params={'created_from': '2000-01-01T00:00:00Z', 'integrity_result': 'not_checked'}).json()['total'], 2)

    def test_search_cursor_is_stable_with_timestamp_ties_and_bound_to_filters(self):
        for sort in ('newest', 'oldest'):
            page = self.get(self.base, params={'limit': 1, 'sort': sort}).json()
            response = self.get(self.base, params={'cursor': page['next_cursor'], 'sort': sort})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertNotEqual(response.json()['items'][0]['id'], page['items'][0]['id'])
            self.assertEqual(response.json()['next_cursor'], None)
            self.assertEqual(self.get(self.base, params={'cursor': page['next_cursor'], 'q': 'changed'}).status_code, 422)
        self.assertEqual(self.get(self.base, params={'cursor': '!!!'}).status_code, 422)

    def test_every_operation_requires_operator_and_owner(self):
        for suffix, method, payload in [('', 'get', None), ('/custody', 'get', None), ('/notes', 'get', None),
                                        ('/annotations', 'patch', {'expected_revision': 0, 'display_title': 'X'}),
                                        ('/notes', 'post', {'expected_revision': 0, 'body': 'X'})]:
            kwargs = {'json': payload} if payload else {}
            for headers in ({}, {'Authorization': 'Bearer sv_agent_' + 'A' * 43}):
                response = self.client.request(method, self.url + suffix, headers=headers, **kwargs)
                self.assertEqual(response.status_code, 401, response.text)
            response = self.client.request(method, f'{self.base}/{self.ids[2]}{suffix}', headers=self.headers, **kwargs)
            self.assertEqual(response.status_code, 404, response.text)
        self.assertEqual(self.client.get(self.base).status_code, 401)
        self.assertEqual(self.get(self.base, params={'q': 'secret'}).json()['total'], 0)
        with self.factory() as db:
            db.get(User, self.settings.operator_user_id).is_active = False
            db.commit()
        self.assertEqual(self.get().status_code, 401)

    def test_validation_and_acquisition_fields_are_immutable(self):
        for values in ({'sha256': 'b' * 64}, {'incident_id': str(self.ids[2])}, {'storage_key': 'x'},
                       {'actor_user_id': str(self.ids[2])}, {'review_state': None}, {'tags': None},
                       {'tags': ['invalid tag']}, {'display_title': ''}, {}):
            self.assertEqual(self.annotate(**values).status_code, 422)
        self.assertEqual(self.note(body=' ').status_code, 422)
        for params in ({'limit': 101}, {'min_size': 20, 'max_size': 1}, {'created_from': '2026-01-01'}, {'unknown': 'x'}):
            self.assertEqual(self.get(self.base, params=params).status_code, 422)
        self.assertEqual(self.client.post(self.url + '/notes', headers=self.headers, content='x' * 131073).status_code, 413)

    def test_integrity_structure_constraints_and_separate_historical_status(self):
        with self.factory() as db:
            for override in ({'status': 'completed'}, {'expected_size_bytes': -1}, {'expected_sha256': 'bad'},
                             {'evidence_id': uuid4()}, {'status': 'queued', 'result': 'matches'}):
                values = dict(evidence_id=self.ids[0], requested_by_id=self.settings.operator_user_id,
                              expected_sha256='a' * 64, expected_size_bytes=10)
                values.update(override)
                db.add(EvidenceIntegrityCheck(**values))
                with self.assertRaises(IntegrityError):
                    db.flush()
                db.rollback()
            db.add(EvidenceIntegrityCheck(evidence_id=self.ids[0], requested_by_id=self.settings.operator_user_id,
                expected_sha256='a' * 64, expected_size_bytes=10, status='completed', result='mismatch',
                observed_sha256='b' * 64, observed_size_bytes=10, completed_at=utc_now()))
            db.commit()
        data = self.get().json()
        self.assertEqual(data['initial_verification_status'], 'legacy')
        self.assertEqual(data['integrity_result'], 'mismatch')
        self.assertEqual(self.get(self.base, params={'integrity_result': 'mismatch'}).json()['total'], 1)

    def test_phase2a_upload_then_annotation_preserves_receipt(self):
        import hashlib
        response = self.client.post('/api/v1/agents', headers=self.headers, json={'name': 'Fixture'})
        agent = response.json()
        job = self.client.post('/api/v1/collection-jobs', headers=self.headers, json={
            'incident_id': str(self.incident_id), 'agent_id': agent['id'],
            'files': [{'source_path': r'C:\Cases\sample.bin', 'max_bytes': 10}]}).json()
        headers = {'Authorization': f"Bearer {agent['token']}", 'Content-Type': 'application/octet-stream',
                   'X-Evidence-SHA256': hashlib.sha256(b'abc').hexdigest(), 'X-Evidence-Size': '3',
                   'X-Collected-At': '2026-09-06T00:00:00Z'}
        upload_url = f"/api/v1/agents/jobs/{job['id']}/files/{job['files'][0]['id']}"
        first = self.client.put(upload_url, headers=headers, content=b'abc')
        self.assertEqual(first.status_code, 201, first.text)
        self.url = f"{self.base}/{first.json()['id']}"
        self.assertFalse(self.get().json()['custody_started'])
        self.assertEqual(self.annotate(tags=['collected']).status_code, 200)
        repeat = self.client.put(upload_url, headers=headers, content=b'abc')
        self.assertEqual(repeat.status_code, 200, repeat.text)
        self.assertEqual(repeat.json(), first.json())
        self.assertEqual(self.get().json()['initial_verification_status'], 'verified')
        self.assertEqual(self.get(self.base, params={'agent_id': agent['id'], 'collection_job_id': job['id'],
            'collected_from': '2026-09-05T00:00:00Z', 'verification_status': 'verified'}).json()['total'], 1)
