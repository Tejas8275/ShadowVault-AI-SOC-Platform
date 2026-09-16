import hashlib
import tempfile
import unittest
from pathlib import Path
from uuid import UUID, uuid4
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import select, func, text
from sqlalchemy.exc import OperationalError
from app.core.config import BACKEND_DIR, Settings
from app.core.security import token_digest
from app.db.migrate import upgrade_database
from app.db.session import build_engine, build_session_factory
from app.main import create_app
from app.models import Evidence, Incident, User, CustodyEvent, CollectionJob, EvidenceIntegrityCheck, TimelineEvent
from app.services import evidence_reader
from app.services.custody import verify_chain


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=BACKEND_DIR)
        self.root = Path(self.temp.name)
        self.settings = Settings(_env_file=None, environment='test', database_url=f'sqlite:///{self.root.as_posix()}/test.db',
            evidence_dir=self.root/'evidence', retrieval_dir=self.root/'retrieval',
            operator_token_sha256=token_digest('sv_operator_retrieval'))
        upgrade_database(self.settings)
        self.engine = build_engine(self.settings)
        self.factory = build_session_factory(self.engine)
        self.content = b'original\x00\xff evidence'
        self.key = uuid4().hex + '.blob'
        self.settings.evidence_dir.mkdir(mode=0o700)
        self.original = self.settings.evidence_dir/self.key
        self.original.write_bytes(self.content)
        with self.factory() as db:
            owner = User(email='retrieval@example.test', display_name='Reader', password_hash='!disabled')
            other = User(email='foreign@example.test', display_name='Other', password_hash='!disabled')
            own = Incident(title='Own', created_by=owner)
            foreign = Incident(title='Foreign', created_by=other)
            db.add_all([own, foreign]); db.flush()
            evidence = Evidence(incident_id=own.id, collected_by_id=owner.id, filename='hostile\r\n<script>.exe',
                size_bytes=len(self.content), sha256=hashlib.sha256(self.content).hexdigest(), storage_key=self.key)
            outside = Evidence(incident_id=foreign.id, collected_by_id=other.id, filename='foreign',
                size_bytes=0, sha256='a'*64, storage_key='foreign')
            db.add_all([evidence, outside]); db.commit()
            self.id, self.foreign, self.incident, self.other = evidence.id, outside.id, own.id, other.id
            self.settings.operator_user_id = owner.id
        self.app = create_app(self.settings)
        self.client = TestClient(self.app); self.client.__enter__()
        self.headers = {'Authorization': 'Bearer sv_operator_retrieval'}
        self.base = '/api/v2/investigation'

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.engine.dispose(); self.temp.cleanup()

    def download(self, id=None, headers=None):
        return self.client.post(f'{self.base}/evidence/{id or self.id}/download', headers=self.headers if headers is None else headers)

    def assert_clean(self):
        self.assertEqual(list(self.settings.retrieval_dir.glob('*')), [])
        self.assertTrue(self.app.state.retrieval_slots.acquire(blocking=False))
        self.app.state.retrieval_slots.release()

    def test_verified_attachment_custody_original_and_revision_preserved(self):
        response = self.download()
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.content, self.content)
        self.assertEqual(response.headers['content-type'], 'application/octet-stream')
        self.assertEqual(response.headers['content-length'], str(len(self.content)))
        self.assertEqual(response.headers['content-disposition'], f'attachment; filename="evidence-{self.id}.bin"')
        self.assertEqual(response.headers['cache-control'], 'no-store')
        self.assertEqual(response.headers['x-content-type-options'], 'nosniff')
        self.assertEqual(self.original.read_bytes(), self.content)
        with self.factory() as db:
            e = db.get(Evidence, self.id)
            self.assertEqual((e.metadata_revision, e.verification_status), (0, 'legacy'))
            self.assertEqual(e.custody_sequence, 2)
            self.assertTrue(verify_chain(db, self.id))
            events = db.scalars(select(CustodyEvent).order_by(CustodyEvent.sequence)).all()
            self.assertEqual(events[0].details['reason'], 'tracking_started_at_first_retrieval')
            self.assertEqual(events[1].actor_user_id, self.settings.operator_user_id)
            self.assertEqual(events[1].event_type, 'evidence_retrieval_prepared')
            self.assertEqual(events[1].details['observed_sha256'], e.sha256)
            self.assertNotIn('storage_key', events[1].details)
            self.assertEqual(db.scalar(select(func.count()).select_from(EvidenceIntegrityCheck)), 0)
            self.assertEqual(db.scalar(select(func.count()).select_from(TimelineEvent)), 0)
            self.assertEqual(db.scalar(text('select version_num from alembic_version')), '0008')
        self.assert_clean()

    def test_auth_owner_and_unknown_id_never_open_bytes(self):
        with patch.object(evidence_reader, 'open_original') as opening:
            for headers in [{}, {'Authorization': 'Bearer sv_agent_invalid'}]:
                self.assertEqual(self.download(headers=headers).status_code, 401)
            self.assertEqual(self.download(self.foreign).status_code, 404)
            self.assertEqual(self.download(uuid4()).status_code, 404)
            with self.factory() as db:
                db.get(User, self.settings.operator_user_id).is_active = False; db.commit()
            self.assertEqual(self.download().status_code, 401)
            opening.assert_not_called()

    def test_mismatch_missing_and_unsupported_key_do_not_write_custody(self):
        for content in [b'x'*len(self.content), b'short', b'longer'*30]:
            self.original.write_bytes(content)
            self.assertEqual(self.download().status_code, 409)
            self.assert_clean()
        self.original.unlink()
        self.assertEqual(self.download().status_code, 503)
        with self.factory() as db:
            db.get(Evidence, self.id).storage_key = '../outside'; db.commit()
        response = self.download()
        self.assertEqual(response.status_code, 503)
        self.assertNotIn(str(self.root), response.text)
        with self.factory() as db:
            self.assertEqual(db.get(Evidence, self.id).custody_sequence, 0)
            self.assertEqual(db.scalar(select(func.count()).select_from(CustodyEvent)), 0)

    def test_limits_ranges_and_capacity(self):
        self.settings.max_retrieval_bytes = 1
        self.assertEqual(self.download().status_code, 413)
        self.settings.max_retrieval_bytes = 1024
        self.assertEqual(self.download(headers={**self.headers, 'Range': 'bytes=0-1'}).status_code, 416)
        slots = self.app.state.retrieval_slots
        for _ in range(self.settings.max_concurrent_retrievals): slots.acquire()
        try:
            response = self.download()
            self.assertEqual(response.status_code, 429)
            self.assertEqual(response.headers['retry-after'], '5')
        finally:
            for _ in range(self.settings.max_concurrent_retrievals): slots.release()
        self.assertEqual(self.download().status_code, 200)

    def test_custody_and_commit_failures_release_no_bytes_and_rollback(self):
        for target in ['app.services.custody.append_event', 'sqlalchemy.orm.Session.commit']:
            with patch(target, side_effect=OperationalError('test', {}, Exception('private path'))):
                response = self.download()
            self.assertEqual(response.status_code, 503)
            self.assertNotIn('private path', response.text)
            with self.factory() as db:
                self.assertEqual(db.get(Evidence, self.id).custody_sequence, 0)
                self.assertEqual(db.scalar(select(func.count()).select_from(CustodyEvent)), 0)
            self.assert_clean()
        self.assertEqual(self.download().status_code, 200)

    def test_disabled_operator_during_preparation_denied(self):
        original = evidence_reader.prepare_copy
        def disable(*args):
            result = original(*args)
            with self.factory() as db:
                db.get(User, self.settings.operator_user_id).is_active = False; db.commit()
            return result
        with patch('app.services.evidence_retrieval.prepare_copy', side_effect=disable):
            self.assertEqual(self.download().status_code, 401)
        self.assert_clean()

    def test_prepared_copy_is_served_even_if_original_changes_after_preparation(self):
        original = evidence_reader.prepare_copy
        def change(*args):
            result = original(*args)
            self.original.write_bytes(b'changed later')
            return result
        with patch('app.services.evidence_retrieval.prepare_copy', side_effect=change):
            response = self.download()
        self.assertEqual(response.content, self.content)
        self.assertEqual(self.download().status_code, 409)
        self.assert_clean()

    def test_empty_copy_and_explicit_repeats_record_separate_preparations(self):
        self.original.write_bytes(b'')
        with self.factory() as db:
            e = db.get(Evidence, self.id); e.size_bytes = 0; e.sha256 = hashlib.sha256(b'').hexdigest(); db.commit()
        for _ in range(2):
            response = self.download(); self.assertEqual(response.status_code, 200); self.assertEqual(response.content, b'')
        with self.factory() as db:
            self.assertEqual(db.get(Evidence, self.id).custody_sequence, 3)
            self.assertTrue(verify_chain(db, self.id))
        self.assert_clean()

    def test_metadata_reads_stay_read_only_and_get_download_not_allowed(self):
        for suffix in ['', '/custody', '/notes']:
            self.assertEqual(self.client.get(f'{self.base}/evidence/{self.id}{suffix}', headers=self.headers).status_code, 200)
        self.assertEqual(self.client.get(f'{self.base}/evidence/{self.id}/download', headers=self.headers).status_code, 405)
        with self.factory() as db: self.assertEqual(db.get(Evidence, self.id).custody_sequence, 0)

    def test_annotation_during_preparation_preserves_both_custody_actions(self):
        original = evidence_reader.prepare_copy
        def annotate(*args):
            result = original(*args)
            response = self.client.patch(f'{self.base}/evidence/{self.id}/annotations', headers=self.headers,
                json={'expected_revision': 0, 'display_title': 'During preparation'})
            self.assertEqual(response.status_code, 200)
            return result
        with patch('app.services.evidence_retrieval.prepare_copy', side_effect=annotate):
            self.assertEqual(self.download().status_code, 200)
        with self.factory() as db:
            e = db.get(Evidence, self.id)
            self.assertEqual(e.display_title, 'During preparation'); self.assertEqual(e.metadata_revision, 1)
            self.assertEqual(e.custody_sequence, 3); self.assertTrue(verify_chain(db, self.id))

    def test_metadata_identity_change_during_preparation_is_rejected(self):
        original = evidence_reader.prepare_copy
        def change(*args):
            result = original(*args)
            with self.factory() as db:
                db.get(Evidence, self.id).sha256 = '0'*64; db.commit()
            return result
        with patch('app.services.evidence_retrieval.prepare_copy', side_effect=change):
            self.assertEqual(self.download().status_code, 409)
        with self.factory() as db: self.assertEqual(db.get(Evidence, self.id).custody_sequence, 0)
        self.assert_clean()

    def test_upload_annotation_timeline_retrieval_and_repeat_receipt(self):
        history_url=f'{self.base}/incidents/{self.incident}/history'
        history_before=self.client.get(history_url,headers=self.headers).json()
        agent = self.client.post('/api/v1/agents', headers=self.headers, json={'name': 'Retrieval fixture'}).json()
        job = self.client.post('/api/v1/collection-jobs', headers=self.headers, json={
            'incident_id': str(self.incident), 'agent_id': agent['id'],
            'files': [{'source_path': r'C:\Cases\original.bin', 'max_bytes': 1024}]}).json()
        headers = {'Authorization': f"Bearer {agent['token']}", 'Content-Type': 'application/octet-stream',
            'X-Evidence-SHA256': hashlib.sha256(self.content).hexdigest(), 'X-Evidence-Size': str(len(self.content)),
            'X-Collected-At': '2026-09-06T00:00:00Z'}
        path = f"/api/v1/agents/jobs/{job['id']}/files/{job['files'][0]['id']}"
        first = self.client.put(path, content=self.content, headers=headers)
        self.assertEqual(first.status_code, 201)
        id = first.json()['id']
        self.assertEqual(self.client.patch(f'{self.base}/evidence/{id}/annotations', headers=self.headers,
            json={'expected_revision': 0, 'display_title': 'Examined', 'tags': ['case']}).status_code, 200)
        self.assertEqual(self.client.post(f'{self.base}/evidence/{id}/timeline-events', headers=self.headers,
            json={'submission_id': str(uuid4()), 'occurred_at': '2026-09-06T00:00:00Z',
                  'title': 'Observation', 'source': 'Investigator'}).status_code, 201)
        self.assertEqual(self.download(id, headers).status_code, 401)
        self.assertEqual(self.download(id).content, self.content)
        repeated = self.client.put(path, content=self.content, headers=headers)
        self.assertEqual(repeated.status_code, 200); self.assertEqual(first.json(), repeated.json())
        with self.factory() as db:
            e = db.get(Evidence, UUID(id)); self.assertEqual(e.metadata_revision, 1)
            self.assertTrue(verify_chain(db, e.id))
            db.get(CollectionJob, UUID(job['id'])).requested_by_id = self.other; db.commit()
        self.assertEqual(self.download(id).status_code, 404)
        self.assertEqual(self.client.get(history_url,headers=self.headers).json(),history_before)
