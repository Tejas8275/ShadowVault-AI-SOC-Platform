"""Streaming SHA-256 of staged files; no platform acquisition assumptions."""
import hashlib
CHUNK_SIZE = 1024 * 1024

def digest_file(path):
    digest = hashlib.sha256()
    size = 0
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(CHUNK_SIZE), b''):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size

