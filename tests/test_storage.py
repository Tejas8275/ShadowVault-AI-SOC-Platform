import asyncio
import tempfile
import unittest
from pathlib import Path
from starlette.requests import ClientDisconnect
from app.core.config import BACKEND_DIR
from app.schemas.collection import UploadMetadata
from app.services.storage import EvidenceStore


class StorageFailureTests(unittest.IsolatedAsyncioTestCase):
    async def test_disconnect_removes_partial_file(self):
        class DisconnectedRequest:
            async def stream(self):
                yield b'partial'
                raise ClientDisconnect()
        with tempfile.TemporaryDirectory(dir=BACKEND_DIR) as temp:
            store = EvidenceStore(Path(temp) / 'evidence')
            metadata = UploadMetadata(sha256='0' * 64, size_bytes=20, collected_at='2026-09-06T00:00:00Z')
            with self.assertRaises(ClientDisconnect):
                await store.receive(DisconnectedRequest(), metadata, 100, 1)
            self.assertEqual(list(store.root.iterdir()), [])

    async def test_timeout_removes_partial_file(self):
        class SlowRequest:
            async def stream(self):
                yield b'partial'
                await asyncio.sleep(1)
        with tempfile.TemporaryDirectory(dir=BACKEND_DIR) as temp:
            store = EvidenceStore(Path(temp) / 'evidence')
            metadata = UploadMetadata(sha256='0' * 64, size_bytes=20, collected_at='2026-09-06T00:00:00Z')
            with self.assertRaises(TimeoutError):
                await store.receive(SlowRequest(), metadata, 100, .01)
            self.assertEqual(list(store.root.iterdir()), [])
