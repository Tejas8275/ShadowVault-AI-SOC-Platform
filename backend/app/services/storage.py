"""Opaque storage paths and streamed byte verification; originals are never executed."""
import asyncio
import hashlib
import os
import sys
from pathlib import Path
from uuid import uuid4
from fastapi import HTTPException, Request
from starlette.concurrency import run_in_threadpool


class EvidenceStore:
    def __init__(self, root: Path):
        self.root = root.resolve()

    async def receive(self, request: Request, metadata, limit: int, timeout: int) -> Path:
        if os.name == "nt" and sys.version_info < (3, 13):
            raise OSError("Windows evidence storage requires Python 3.13+ directory ACL support")
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        path = self.root / f"{uuid4().hex}.part"
        count = 0
        digest = hashlib.sha256()
        try:
            with path.open("xb") as handle:
                if os.name != "nt":
                    os.chmod(path, 0o600)
                async with asyncio.timeout(timeout):
                    async for chunk in request.stream():
                        count += len(chunk)
                        if count > limit or count > metadata.size_bytes:
                            raise HTTPException(413, "Upload exceeds the approved size")
                        digest.update(chunk)
                        await run_in_threadpool(handle.write, chunk)
                    await run_in_threadpool(handle.flush)
                    await run_in_threadpool(os.fsync, handle.fileno())
            if count != metadata.size_bytes:
                raise HTTPException(422, "Received size does not match declared size")
            if digest.hexdigest() != metadata.sha256:
                raise HTTPException(422, "SHA256 mismatch; evidence rejected")
            return path
        except BaseException:
            path.unlink(missing_ok=True)
            raise

    def promote(self, temporary: Path) -> Path:
        destination = self.root / f"{uuid4().hex}.blob"
        # Same filesystem: finalized files are never partially visible.
        temporary.rename(destination)
        return destination
