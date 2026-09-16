import asyncio
import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from threading import BoundedSemaphore
from unittest.mock import patch, Mock
from types import SimpleNamespace
from fastapi import HTTPException
from starlette.requests import ClientDisconnect
from app.core.config import BACKEND_DIR, Settings
from app.services.evidence_reader import open_original, prepare_copy
from app.api.routes.investigation_retrieval import PreparedDownload, download


class ReaderTests(unittest.TestCase):
    def test_close_failure_releases_response_capacity_on_success_disconnect_and_timeout(self):
        for failure in ('none', 'disconnect', 'timeout'):
            with self.subTest(failure=failure):
                copy = Mock(); copy.read.return_value = b''; copy.close.side_effect = OSError('close failed')
                slots = BoundedSemaphore(1); slots.acquire()
                response = PreparedDownload(copy, 0, 'id', slots, .01)
                async def send(message):
                    if failure == 'disconnect': raise OSError('disconnected')
                    if failure == 'timeout': await asyncio.sleep(10)
                async def receive(): return {'type': 'http.disconnect'}
                async def run():
                    with self.assertRaisesRegex(OSError, 'close failed'):
                        await response({'type': 'http', 'asgi': {'spec_version': '2.4'}}, receive, send)
                asyncio.run(run())
                copy.close.assert_called_once()
                self.assertTrue(slots.acquire(blocking=False)); self.assertFalse(slots.acquire(blocking=False)); slots.release()

    def test_route_constructor_and_close_failure_release_capacity_and_rollback(self):
        slots = BoundedSemaphore(1)
        copy = Mock(); copy.close.side_effect = OSError('private cleanup path')
        db = Mock()
        request = SimpleNamespace(headers={}, app=SimpleNamespace(state=SimpleNamespace(
            retrieval_slots=slots, settings=SimpleNamespace(retrieval_timeout_seconds=1))))
        with patch('app.api.routes.investigation_retrieval.evidence_retrieval.prepare', return_value=(copy, 0)), \
             patch('app.api.routes.investigation_retrieval.PreparedDownload', side_effect=OSError('private constructor path')):
            with self.assertRaises(HTTPException) as caught: download('id', request, db, Mock(), Mock())
        self.assertEqual(caught.exception.status_code, 503)
        self.assertNotIn('private', caught.exception.detail)
        db.rollback.assert_called_once(); copy.close.assert_called_once()
        self.assertTrue(slots.acquire(blocking=False)); self.assertFalse(slots.acquire(blocking=False)); slots.release()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=BACKEND_DIR)
        self.root = Path(self.temp.name)
        self.settings = Settings(_env_file=None, evidence_dir=self.root/'evidence', retrieval_dir=self.root/'copies')
        self.settings.evidence_dir.mkdir(mode=0o700)
        self.key = 'a'*32 + '.blob'
        self.path = self.settings.evidence_dir/self.key
        self.path.write_bytes(b'abc')

    def tearDown(self): self.temp.cleanup()

    def test_untrusted_keys_and_directories_are_never_opened(self):
        for key in ['../'+self.key, '/tmp/'+self.key, r'C:\secret', r'\\server\share', self.key+':stream',
                    self.key+' ', self.key+'.', '%2e%2e', 'legacy', 'a'*32+'.part']:
            with self.subTest(key=key), self.assertRaises(OSError): open_original(self.settings.evidence_dir, key)
        self.path.unlink(); self.path.mkdir()
        with self.assertRaises(OSError): open_original(self.settings.evidence_dir, self.key)

    def test_copy_timeout_and_io_error_clean_temporary_files(self):
        with patch('app.services.evidence_reader.time.monotonic', side_effect=[0, 10000]):
            with self.assertRaises(HTTPException) as caught:
                prepare_copy(self.settings, self.key, 3, hashlib.sha256(b'abc').hexdigest())
            self.assertEqual(caught.exception.status_code, 503)
        with patch('app.services.evidence_reader.open_original', side_effect=OSError('unavailable')):
            with self.assertRaises(OSError): prepare_copy(self.settings, self.key, 3, 'a'*64)
        self.assertEqual(list(self.settings.retrieval_dir.iterdir()), [])

    def test_windows_requires_private_directory_acl_support(self):
        if os.name != 'nt': self.skipTest('Windows directory ACL support')
        with patch('app.services.evidence_reader.sys.version_info', (3, 12)):
            with self.assertRaises(OSError): prepare_copy(self.settings, self.key, 3, 'a'*64)
        self.assertFalse(self.settings.retrieval_dir.exists())

    def test_junction_or_symlink_storage_root_rejected(self):
        link = self.root/'link'
        if os.name == 'nt':
            import _winapi
            _winapi.CreateJunction(str(self.settings.evidence_dir), str(link))
        else:
            link.symlink_to(self.settings.evidence_dir, target_is_directory=True)
        try:
            with self.assertRaises(OSError): open_original(link, self.key)
        finally:
            if os.name == 'nt': link.rmdir()
            else: link.unlink()

    def test_windows_handle_denies_write_and_delete_while_reading(self):
        if os.name != 'nt': self.skipTest('Windows sharing semantics')
        with open_original(self.settings.evidence_dir, self.key) as handle:
            with self.assertRaises(OSError): self.path.write_bytes(b'bad')
            with self.assertRaises(OSError): self.path.unlink()
            self.assertEqual(handle.read(), b'abc')

    def test_response_send_failure_closes_copy_and_releases_capacity(self):
        copy = tempfile.TemporaryFile(); copy.write(b'abc'); copy.seek(0)
        slots = BoundedSemaphore(1); slots.acquire()
        response = PreparedDownload(copy, 3, 'id', slots, 1)
        async def send(message): raise OSError('connection closed')
        async def receive(): return {'type': 'http.disconnect'}
        async def run():
            with self.assertRaises(ClientDisconnect):
                await response({'type': 'http', 'asgi': {'spec_version': '2.4'}}, receive, send)
        asyncio.run(run())
        self.assertTrue(copy.closed); self.assertTrue(slots.acquire(blocking=False)); slots.release()

    def test_response_timeout_releases_copy_and_capacity(self):
        copy = tempfile.TemporaryFile(); copy.write(b'abc'); copy.seek(0)
        slots = BoundedSemaphore(1); slots.acquire()
        response = PreparedDownload(copy, 3, 'id', slots, 0.01)
        async def send(message): await asyncio.sleep(10)
        async def receive(): return {'type': 'http.disconnect'}
        async def run():
            with self.assertRaises(TimeoutError):
                await response({'type': 'http', 'asgi': {'spec_version': '2.4'}}, receive, send)
        asyncio.run(run())
        self.assertTrue(copy.closed); self.assertTrue(slots.acquire(blocking=False)); slots.release()

    def test_windows_parent_replacement_between_validation_and_open_is_rejected(self):
        if os.name != 'nt': self.skipTest('Windows junction replacement')
        import _winapi
        from app.services import evidence_reader
        outside = self.root/'outside'; outside.mkdir(); (outside/self.key).write_bytes(b'abc')
        saved = self.root/'saved'
        original = evidence_reader._windows_open
        def replace(path):
            self.settings.evidence_dir.rename(saved)
            _winapi.CreateJunction(str(outside), str(self.settings.evidence_dir))
            return original(path)
        try:
            with patch.object(evidence_reader, '_windows_open', side_effect=replace):
                with self.assertRaises(OSError): open_original(self.settings.evidence_dir, self.key)
        finally:
            self.settings.evidence_dir.rmdir(); saved.rename(self.settings.evidence_dir)
