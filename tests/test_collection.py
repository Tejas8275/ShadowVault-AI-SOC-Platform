import hashlib
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from app.core.config import BACKEND_DIR, Settings
from app.core.security import token_digest
from app.db.base import Base
from app.db.session import build_engine, build_session_factory
from app.main import create_app
from app.models import Agent, CollectionJob, Evidence, Incident, User
from app.models.common import utc_now


class CollectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=BACKEND_DIR)
        self.root = Path(self.temp.name)
        self.operator_token = 'sv_operator_' + 'A' * 43
        self.settings = Settings(_env_file=None, environment='test',
                                 database_url=f"sqlite:///{self.root.as_posix()}/test.db",
                                 evidence_dir=self.root / 'evidence', max_upload_bytes=1024,
                                 max_job_bytes=4096, operator_token_sha256=token_digest(self.operator_token))
        self.engine = build_engine(self.settings)
        Base.metadata.create_all(self.engine)
        self.factory = build_session_factory(self.engine)
        with self.factory() as db:
            user = User(email='operator@example.com', display_name='Operator', password_hash='!disabled')
            other = User(email='other@example.com', display_name='Other', password_hash='!disabled')
            incident = Incident(title='Authorized', created_by=user)
            foreign = Incident(title='Foreign', created_by=other)
            db.add_all([incident, foreign])
            db.commit()
            self.settings.operator_user_id = user.id
            self.incident_id, self.foreign_id = str(incident.id), str(foreign.id)
        self.app = create_app(self.settings)
        self.client = TestClient(self.app)
        self.client.__enter__()
        self.operator_headers = {'Authorization': f'Bearer {self.operator_token}'}
        self.agent = self.register()
        self.agent_headers = {'Authorization': f"Bearer {self.agent['token']}"}
        self.job = self.create_job()
        self.item = self.job['files'][0]

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.engine.dispose()
        self.temp.cleanup()

    def register(self):
        response = self.client.post('/api/v1/agents', json={'name': 'Windows fixture'}, headers=self.operator_headers)
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.headers['cache-control'], 'no-store')
        return response.json()

    def create_job(self, **overrides):
        values = {'incident_id': self.incident_id, 'agent_id': self.agent['id'],
                  'files': [{'source_path': r'C:\Cases\sample.bin', 'max_bytes': 1024}]}
        values.update(overrides)
        response = self.client.post('/api/v1/collection-jobs', json=values, headers=self.operator_headers)
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def upload(self, content=b'forensic fixture', *, digest=None, size=None, headers=None, item_id=None):
        supplied = dict(self.agent_headers if headers is None else headers)
        supplied.update({'Content-Type': 'application/octet-stream',
                         'X-Evidence-SHA256': digest or hashlib.sha256(content).hexdigest(),
                         'X-Evidence-Size': str(len(content) if size is None else size),
                         'X-Collected-At': '2026-09-06T12:00:00+05:30'})
        return self.client.put(f"/api/v1/agents/jobs/{self.job['id']}/files/{item_id or self.item['id']}",
                               content=content, headers=supplied)

    def evidence_count(self):
        with self.factory() as db:
            return db.scalar(select(func.count()).select_from(Evidence))

    def test_valid_upload_stores_verified_bytes_and_metadata(self):
        data = b'forensic fixture\x00\xff'
        response = self.upload(data)
        self.assertEqual(response.status_code, 201, response.text)
        result = response.json()
        self.assertEqual(result['sha256'], hashlib.sha256(data).hexdigest())
        self.assertEqual(result['verification_status'], 'verified')
        self.assertNotIn('storage_key', result)
        self.assertEqual(result['collected_at'], '2026-09-06T06:30:00Z')
        with self.factory() as db:
            evidence = db.scalar(select(Evidence))
            self.assertEqual((self.settings.evidence_dir / evidence.storage_key).read_bytes(), data)
            self.assertEqual(evidence.collected_by_id, self.settings.operator_user_id)
            self.assertEqual(evidence.collected_at.hour, 6)
        metadata = self.client.get(f"/api/v1/collection-jobs/{self.job['id']}/evidence", headers=self.operator_headers)
        self.assertEqual(metadata.status_code, 200)
        self.assertEqual(len(metadata.json()), 1)
        status = self.client.get(f"/api/v1/collection-jobs/{self.job['id']}", headers=self.operator_headers).json()
        self.assertEqual(status['status'], 'complete')

    def test_hash_mismatch_rejected_without_stored_evidence(self):
        response = self.upload(digest='0' * 64)
        self.assertEqual(response.status_code, 422)
        self.assertIn('SHA256 mismatch', response.text)
        self.assertEqual(self.evidence_count(), 0)
        self.assertEqual(list(self.settings.evidence_dir.iterdir()), [])

    def test_duplicate_submission_returns_same_receipt(self):
        first, second = self.upload(), self.upload()
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual(first.json()['id'], second.json()['id'])
        self.assertEqual(self.evidence_count(), 1)
        self.assertEqual(len(list(self.settings.evidence_dir.glob('*.blob'))), 1)
        self.assertFalse(list(self.settings.evidence_dir.glob('*.part')))

    def test_duplicate_with_changed_bytes_conflicts(self):
        self.assertEqual(self.upload().status_code, 201)
        self.assertEqual(self.upload(b'changed').status_code, 409)
        self.assertEqual(self.evidence_count(), 1)
        self.assertEqual(len(list(self.settings.evidence_dir.iterdir())), 1)

    def test_unauthenticated_and_wrong_credential_type_denied(self):
        self.assertEqual(self.upload(headers={}).status_code, 401)
        self.assertEqual(self.upload(headers=self.operator_headers).status_code, 401)
        self.assertEqual(self.client.post('/api/v1/agents', json={'name': 'bad'}, headers=self.agent_headers).status_code, 401)
        self.assertEqual(self.client.get(f"/api/v1/collection-jobs/{self.job['id']}/evidence", headers=self.agent_headers).status_code, 401)
        self.assertEqual(self.evidence_count(), 0)
        self.assertFalse(self.settings.evidence_dir.exists())

    def test_another_agent_cannot_access_job_or_upload(self):
        second = self.register()
        headers = {'Authorization': f"Bearer {second['token']}"}
        self.assertEqual(self.client.get(f"/api/v1/agents/jobs/{self.job['id']}", headers=headers).status_code, 404)
        self.assertEqual(self.upload(headers=headers).status_code, 404)

    def test_operator_cannot_create_job_for_foreign_incident(self):
        response = self.client.post('/api/v1/collection-jobs', headers=self.operator_headers,
                                    json={'incident_id': self.foreign_id, 'agent_id': self.agent['id'],
                                          'files': [{'source_path': r'C:\test.bin', 'max_bytes': 100}]})
        self.assertEqual(response.status_code, 404)

    def test_expired_revoked_and_disabled_owner_denied(self):
        with self.factory() as db:
            agent = db.scalar(select(Agent))
            agent.token_expires_at = utc_now() - timedelta(seconds=1)
            db.commit()
        self.assertEqual(self.upload().status_code, 401)
        with self.factory() as db:
            agent = db.scalar(select(Agent))
            agent.token_expires_at = utc_now() + timedelta(hours=1)
            agent.is_active = False
            db.commit()
        self.assertEqual(self.upload().status_code, 401)
        with self.factory() as db:
            db.scalar(select(Agent)).is_active = True
            db.get(User, self.settings.operator_user_id).is_active = False
            db.commit()
        self.assertEqual(self.upload().status_code, 401)

    def test_unselected_file_and_cancelled_job_denied(self):
        self.assertEqual(self.upload(item_id=str(uuid4())).status_code, 404)
        response = self.client.post(f"/api/v1/collection-jobs/{self.job['id']}/cancel", headers=self.operator_headers)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.upload().status_code, 409)

    def test_size_limits_and_empty_file(self):
        self.assertEqual(self.upload(b'huge', size=1025).status_code, 413)
        self.assertEqual(self.upload(b'longer', size=1).status_code, 413)
        self.assertEqual(self.upload(b'short', size=10).status_code, 422)
        self.assertEqual(self.upload(b'').status_code, 201)
        self.assertEqual(self.evidence_count(), 1)

    def test_manifest_path_restrictions(self):
        for path in [r'..\secret', r'\\server\share\secret', r'C:\file:stream', r'C:\*.log', r'C:\a\..\secret', r'C:\NUL']:
            with self.subTest(path=path):
                response = self.client.post('/api/v1/collection-jobs', headers=self.operator_headers,
                                            json={'incident_id': self.incident_id, 'agent_id': self.agent['id'],
                                                  'files': [{'source_path': path, 'max_bytes': 100}]})
                self.assertEqual(response.status_code, 422)

    def test_database_failure_cleans_files(self):
        with patch('sqlalchemy.orm.Session.commit', side_effect=OperationalError('private path', {}, Exception())):
            response = self.upload()
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('private path', response.text)
        self.assertEqual(self.evidence_count(), 0)
        self.assertEqual(list(self.settings.evidence_dir.iterdir()), [])

    def test_revocation_during_stream_prevents_commit(self):
        from app.services.storage import EvidenceStore
        original = EvidenceStore.receive

        async def receive_and_revoke(store, *args):
            path = await original(store, *args)
            with self.factory() as db:
                db.scalar(select(Agent)).is_active = False
                db.commit()
            return path

        with patch.object(EvidenceStore, 'receive', receive_and_revoke):
            self.assertEqual(self.upload().status_code, 401)
        self.assertEqual(self.evidence_count(), 0)
        self.assertEqual(list(self.settings.evidence_dir.iterdir()), [])

    def test_simultaneous_duplicates_keep_one_object(self):
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(lambda _: self.upload(), range(2)))
        self.assertEqual(sorted(response.status_code for response in responses), [200, 201])
        self.assertEqual(responses[0].json()['id'], responses[1].json()['id'])
        self.assertEqual(self.evidence_count(), 1)
        self.assertEqual(len(list(self.settings.evidence_dir.iterdir())), 1)

    def test_registration_never_stores_plaintext_token(self):
        with self.factory() as db:
            agent = db.scalar(select(Agent))
            self.assertEqual(agent.token_sha256, token_digest(self.agent['token']))
            self.assertNotEqual(agent.token_sha256, self.agent['token'])

    def test_oversized_json_is_rejected_before_parsing(self):
        response = self.client.post('/api/v1/agents', content=b' ' * (129 * 1024),
                                    headers={'Content-Type': 'application/json'})
        self.assertEqual(response.status_code, 413)
