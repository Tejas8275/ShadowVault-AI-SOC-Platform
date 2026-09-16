import hashlib
import json
from uuid import uuid4
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from app.core.config import BACKEND_DIR
sys.path.insert(0, str(BACKEND_DIR.parent))
from agents.core.config import validate_connection
from agents.core.errors import CollectorError
from agents.core.hashing import CHUNK_SIZE, digest_file
from agents.core.uploader import ApiClient, MAX_MANIFEST_RESPONSE_BYTES
from agents.windows import collector


class SharedAgentCoreTests(unittest.TestCase):
    def test_maximum_manifest_unicode_serialization_fits_bounded_transport(self):
        from app.schemas.collection import JobResponse
        path = 'C:\\' + ('\U00010000' * 200 + '\\') * 5
        job = JobResponse(id=uuid4(), incident_id=uuid4(), agent_id=uuid4(), status='open', completed_files=0,
            files=[{'id': uuid4(), 'source_path': path + f'{i:012d}.bin', 'max_bytes': 1073741824} for i in range(100)])
        self.assertEqual(len(job.files[0].source_path), 1024)
        for ensure_ascii in (True, False):
            data = json.dumps(job.model_dump(mode='json'), ensure_ascii=ensure_ascii).encode()
            self.assertGreater(len(data), 65536)
            self.assertLess(len(data), MAX_MANIFEST_RESPONSE_BYTES)
            with patch('agents.core.uploader.http.client.HTTPSConnection') as connection:
                response = connection.return_value.getresponse.return_value
                response.status = 200; response.read.return_value = data
                client = ApiClient('https://example.com/api/v1', 'fixture')
                self.assertEqual(len(client.request('GET', f'/agents/jobs/{job.id}')['files']), 100)
                response.read.assert_called_once_with(MAX_MANIFEST_RESPONSE_BYTES + 1)
                connection.return_value.close.assert_called_once()

    def test_manifest_overflow_and_non_manifest_response_limits_remain_bounded(self):
        for method, path, status, limit in [
            ('GET', f'/agents/jobs/{uuid4()}', 200, MAX_MANIFEST_RESPONSE_BYTES),
            ('GET', f'/agents/jobs/{uuid4()}', 403, 65536),
            ('PUT', f'/agents/jobs/{uuid4()}/files/{uuid4()}', 201, 65536),
        ]:
            with self.subTest(method=method, status=status), patch('agents.core.uploader.http.client.HTTPSConnection') as connection:
                response = connection.return_value.getresponse.return_value
                response.status = status; response.read.return_value = b'x' * (limit + 1)
                with self.assertRaisesRegex(CollectorError, 'exceeds'):
                    ApiClient('https://example.com/api/v1', 'fixture').request(method, path)
                response.read.assert_called_once_with(limit + 1)
                connection.return_value.close.assert_called_once()

    def test_historical_imports_keep_shared_identity(self):
        self.assertIs(collector.ApiClient, ApiClient)
        self.assertIs(collector.CollectorError, CollectorError)
        self.assertIs(collector.digest_file, digest_file)

    def test_streamed_hash_spans_chunks_and_handles_empty_file(self):
        with tempfile.TemporaryDirectory(dir=BACKEND_DIR) as directory:
            path = Path(directory) / 'fixture.bin'
            for content in (b'', b'a' * (CHUNK_SIZE + 17)):
                path.write_bytes(content)
                self.assertEqual(digest_file(path), (hashlib.sha256(content).hexdigest(), len(content)))

    def test_configuration_rejects_unsafe_destinations_and_tokens(self):
        for url in ('http://example.com', 'https://user:pass@example.com', 'https://example.com?x=1', 'https://example.com/#x'):
            with self.assertRaises(CollectorError):
                validate_connection(url, 'fixture')
        for token in ('', 'x\ny', 'x' * 257):
            with self.assertRaises(CollectorError):
                validate_connection('https://example.com', token)
        self.assertEqual(validate_connection('http://127.0.0.1/api/v1', 'fixture', True).hostname, '127.0.0.1')

    def test_transport_keeps_limits_tls_and_refuses_redirect(self):
        with patch('agents.core.uploader.http.client.HTTPSConnection') as connection:
            instance = connection.return_value
            response = instance.getresponse.return_value
            response.status = 302
            response.read.return_value = b'{}'
            client = ApiClient('https://example.com/api/v1', 'fixture')
            with self.assertRaises(CollectorError):
                client.request('GET', '/agents/jobs/fixture')
            self.assertEqual(connection.call_args.kwargs['timeout'], 120)
            self.assertTrue(connection.call_args.kwargs['context'].check_hostname)
            response.read.assert_called_once_with(65537)
            instance.close.assert_called_once()
            self.assertEqual(instance.request.call_count, 1)
