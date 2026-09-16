import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4
from app.core.config import BACKEND_DIR

spec = importlib.util.spec_from_file_location('windows_collector', BACKEND_DIR.parent / 'agents/windows/collector.py')
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)


class AgentFileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=BACKEND_DIR)
        self.root = Path(self.temp.name)
        self.source = self.root / 'selected ü.bin'
        self.source.write_bytes(b'fixture\x00\xff')

    def tearDown(self):
        self.temp.cleanup()

    def test_staging_preserves_source_and_computes_digest(self):
        destination = self.root / 'staged.bin'
        metadata = collector.stage_file(self.source, destination, 100)
        self.assertEqual(destination.read_bytes(), self.source.read_bytes())
        digest, size = collector.digest_file(destination)
        self.assertEqual(metadata['sha256'], digest)
        self.assertEqual(metadata['size_bytes'], size)

    def test_directory_and_oversized_source_rejected(self):
        for source, limit in [(self.root, 100), (self.source, 1)]:
            with self.assertRaises(collector.CollectorError):
                collector.stage_file(source, self.root / 'staged.bin', limit)
        self.assertFalse((self.root / 'staged.bin').exists())

    def test_transport_rejects_remote_http_and_credentials_in_url(self):
        for url in ['http://example.com/api/v1', 'https://user:secret@example.com/api/v1', 'file:///tmp', 'http://127.0.0.1/api/v1']:
            with self.assertRaises(collector.CollectorError):
                collector.ApiClient(url, 'test-token')
        collector.ApiClient('http://127.0.0.1:8000/api/v1', 'test-token', allow_http_local=True)

    @unittest.skipUnless(os.name == 'nt', 'Windows collector requires Windows')
    def test_retry_uses_staged_bytes_and_receipt_prevents_reacquisition(self):
        job_id, item_id = str(uuid4()), str(uuid4())
        source = self.source
        original = source.read_bytes()

        class FakeClient:
            base_url = 'https://backend.example/api/v1'
            failed = False
            uploaded = None

            def request(self, method, path, body=None, headers=None):
                if method == 'GET':
                    return {'id': job_id, 'status': 'open', 'files': [
                        {'id': item_id, 'source_path': str(source), 'max_bytes': 100}]}
                self.uploaded = body.read()
                if not self.failed:
                    self.failed = True
                    raise collector.CollectorError('simulated connection failure')
                return {'id': str(uuid4()), 'collection_job_id': job_id, 'collection_item_id': item_id,
                        'sha256': headers['X-Evidence-SHA256'], 'size_bytes': int(headers['X-Evidence-Size']),
                        'verification_status': 'verified'}

        client = FakeClient()
        spool = self.root / 'spool'
        with self.assertRaises(collector.CollectorError):
            collector.collect(client, job_id, [source], spool)
        self.assertEqual(len(list(spool.glob('*.bin'))), 1)
        source.write_bytes(b'changed after first attempt')
        receipts = collector.collect(client, job_id, [source], spool)
        self.assertEqual(client.uploaded, original)
        self.assertFalse(list(spool.glob('*.bin')))
        source.unlink()
        self.assertEqual(collector.collect(client, job_id, [source], spool), receipts)

    @unittest.skipUnless(os.name == 'nt', 'Windows collector requires Windows')
    def test_unapproved_selection_never_reads_source(self):
        class FakeClient:
            def request(self, *args):
                return {'id': job_id, 'status': 'open', 'files': []}
        job_id = str(uuid4())
        with self.assertRaises(collector.CollectorError):
            collector.collect(FakeClient(), job_id, [self.source], self.root / 'spool')
        self.assertFalse((self.root / 'spool').exists())
