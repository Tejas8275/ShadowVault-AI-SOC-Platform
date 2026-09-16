"""Real Windows CLI -> HTTP -> migrated SQLite -> stored evidence round trip."""
import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
import httpx
import uvicorn
from sqlalchemy import select
from app.core.config import BACKEND_DIR, Settings
from app.core.security import token_digest
from app.db.migrate import upgrade_database
from app.db.session import build_engine, build_session_factory
from app.main import create_app
from app.models import Evidence, Incident, User


@unittest.skipUnless(os.name == 'nt', 'End-to-end collector requires Windows')
class CollectionEndToEndTests(unittest.TestCase):
    def test_real_cli_upload_and_repeat(self):
        with tempfile.TemporaryDirectory(dir=BACKEND_DIR) as temp:
            root = Path(temp)
            source = root / 'selected ü.txt'
            source.write_bytes(b'End-to-end collection fixture\x00\xff')
            token = 'sv_operator_' + 'E' * 43
            settings = Settings(_env_file=None, environment='test', database_url=f"sqlite:///{root.as_posix()}/test.db",
                                evidence_dir=root / 'storage', operator_token_sha256=token_digest(token))
            upgrade_database(settings)
            engine = build_engine(settings)
            try:
                with build_session_factory(engine)() as db:
                    user = User(email='e2e@example.com', display_name='E2E', password_hash='!disabled')
                    incident = Incident(title='E2E fixture', created_by=user)
                    db.add(incident)
                    db.commit()
                    settings.operator_user_id = user.id
                    incident_id = str(incident.id)
                listener = socket.socket()
                listener.bind(('127.0.0.1', 0))
                port = listener.getsockname()[1]
                server = uvicorn.Server(uvicorn.Config(create_app(settings), log_level='error'))
                thread = threading.Thread(target=server.run, kwargs={'sockets': [listener]}, daemon=True)
                thread.start()
                try:
                    deadline = time.monotonic() + 10
                    while not server.started and time.monotonic() < deadline:
                        time.sleep(.02)
                    self.assertTrue(server.started, 'Local verification server did not start')
                    base = f'http://127.0.0.1:{port}/api/v1'
                    headers = {'Authorization': f'Bearer {token}'}
                    with httpx.Client(base_url=base, headers=headers, trust_env=False) as client:
                        registration = client.post('/agents', json={'name': 'E2E Windows'})
                        self.assertEqual(registration.status_code, 201, registration.text)
                        agent = registration.json()
                        creation = client.post('/collection-jobs', json={'incident_id': incident_id, 'agent_id': agent['id'],
                                                                       'files': [{'source_path': str(source), 'max_bytes': 1000}]})
                        self.assertEqual(creation.status_code, 201, creation.text)
                        job = creation.json()
                        env = os.environ.copy()
                        env['SHADOWVAULT_AGENT_TOKEN'] = agent['token']
                        args = [sys.executable, str(BACKEND_DIR.parent / 'agents/windows/collector.py'),
                                '--backend', base, '--job-id', job['id'], '--file', str(source),
                                '--spool', str(root / 'spool'), '--allow-http-local']
                        for _ in range(2):
                            result = subprocess.run(args, env=env, capture_output=True, text=True, timeout=30)
                            self.assertEqual(result.returncode, 0, result.stderr)
                            receipt = json.loads(result.stdout)[0]
                            self.assertEqual(receipt['sha256'], hashlib.sha256(source.read_bytes()).hexdigest())
                        records = client.get(f"/collection-jobs/{job['id']}/evidence")
                        self.assertEqual(len(records.json()), 1)
                        # An accepted manifest larger than 64 KiB must be consumable
                        # by the actual collector transport, without acquiring these paths.
                        from agents.core.uploader import ApiClient
                        large = client.post('/collection-jobs', json={'incident_id': incident_id, 'agent_id': agent['id'],
                            'files': [{'source_path': 'C:\\' + ('a' * 200 + '\\') * 4 + f'item{i}.bin', 'max_bytes': 1}
                                      for i in range(100)]})
                        self.assertEqual(large.status_code, 201, large.text)
                        self.assertGreater(len(large.content), 65536)
                        manifest = ApiClient(base, agent['token'], allow_http_local=True).request('GET', f"/agents/jobs/{large.json()['id']}")
                        self.assertEqual(manifest, large.json())
                    with build_session_factory(engine)() as db:
                        evidence = db.scalar(select(Evidence))
                        self.assertEqual((settings.evidence_dir / evidence.storage_key).read_bytes(), source.read_bytes())
                finally:
                    server.should_exit = True
                    thread.join(timeout=10)
                    listener.close()
                    self.assertFalse(thread.is_alive(), 'Verification server did not stop')
            finally:
                engine.dispose()
