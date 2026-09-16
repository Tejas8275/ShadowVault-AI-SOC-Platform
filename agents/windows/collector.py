"""Windows selected-file collector. Standard library only; no remote execution."""
import argparse
import getpass
import hashlib
import json
import os
import stat
import sys
from datetime import datetime, timezone
from contextlib import contextmanager
from pathlib import Path, PureWindowsPath
from uuid import UUID, uuid4

VERSION = "0.1.0"
MAX_FILE_BYTES = 100 * 1024 * 1024


# Preserve direct script invocation and the historical import surface.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from agents.core.errors import CollectorError
from agents.core.hashing import CHUNK_SIZE, digest_file
from agents.core.uploader import ApiClient


def validate_source(path: Path):
    if not path.is_absolute():
        raise CollectorError("Select absolute file paths")
    # Inspect each component before opening; never follow symlinks or junctions.
    for component in [path, *path.parents]:
        info = component.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0x400):
            raise CollectorError("Symlinks and reparse points are not supported")
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode):
        raise CollectorError("Only selected regular files can be collected")
    return info


def stage_file(source: Path, destination: Path, limit: int):
    before_path = validate_source(source)
    if before_path.st_size > limit:
        raise CollectorError("Selected file exceeds its approved byte limit")
    partial = destination.with_name(f'{destination.stem}_{uuid4().hex}.partial')
    digest = hashlib.sha256()
    size = 0
    collected_at = datetime.now(timezone.utc).isoformat()
    try:
        with source.open('rb') as original, partial.open('xb') as staged:
            before = os.fstat(original.fileno())
            if (before.st_dev, before.st_ino) != (before_path.st_dev, before_path.st_ino) or not stat.S_ISREG(before.st_mode):
                raise CollectorError("Source changed before acquisition")
            if os.name != 'nt':
                os.chmod(partial, 0o600)
            for chunk in iter(lambda: original.read(CHUNK_SIZE), b''):
                size += len(chunk)
                if size > limit:
                    raise CollectorError("Selected file grew beyond its approved byte limit")
                staged.write(chunk)
                digest.update(chunk)
            after = os.fstat(original.fileno())
            after_path = validate_source(source)
            if ((before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns)
                or size != before.st_size or (after_path.st_dev, after_path.st_ino) != (before.st_dev, before.st_ino)):
                raise CollectorError("Source changed during acquisition; retry with a stable file")
            staged.flush()
            os.fsync(staged.fileno())
        partial.replace(destination)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise
    return {'sha256': digest.hexdigest(), 'size_bytes': size, 'collected_at': collected_at}


def save_manifest(path, metadata):
    temporary = path.with_name(f'{path.stem}_{uuid4().hex}.tmp')
    try:
        with temporary.open('x', encoding='utf-8') as handle:
            json.dump(metadata, handle)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def item_lock(path):
    import msvcrt
    # OS locks are released on process exit; the harmless lock file can persist.
    with path.open('a+b') as handle:
        if handle.tell() == 0:
            handle.write(b'0')
            handle.flush()
        handle.seek(0)
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            raise CollectorError("Another collector is already processing this selected file") from None
        try:
            yield
        finally:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def collect_item(client, job_id, source, item, spool):
    item_id = str(UUID(item['id']))
    prefix = f'{job_id}_{item_id}'
    staged = spool / f'{prefix}.bin'
    manifest = spool / f'{prefix}.json'
    limit = min(item['max_bytes'], MAX_FILE_BYTES)
    with item_lock(spool / f'{prefix}.lock'):
        if manifest.exists():
            metadata = json.loads(manifest.read_text(encoding='utf-8'))
            if (metadata.get('backend') != client.base_url
                or str(PureWindowsPath(metadata.get('source_path', ''))).casefold() != str(PureWindowsPath(source)).casefold()):
                raise CollectorError("Staged evidence belongs to a different backend or source")
            if 'receipt' in metadata:
                # A durable receipt prevents reacquisition after successful collection.
                staged.unlink(missing_ok=True)
                return metadata['receipt']
            digest, size = digest_file(staged)
            if digest != metadata['sha256'] or size != metadata['size_bytes'] or size > limit:
                raise CollectorError("Staged evidence failed its integrity check")
        else:
            if staged.exists():
                raise CollectorError("Incomplete prior staging found; preserve and inspect it before retrying")
            metadata = stage_file(source, staged, limit)
            metadata.update(backend=client.base_url, source_path=item['source_path'])
            save_manifest(manifest, metadata)
        with staged.open('rb') as handle:
            receipt = client.request('PUT', f'/agents/jobs/{job_id}/files/{item_id}', body=handle,
                                     headers={'Content-Type': 'application/octet-stream',
                                              'Content-Length': str(metadata['size_bytes']),
                                              'X-Evidence-Size': str(metadata['size_bytes']),
                                              'X-Evidence-SHA256': metadata['sha256'],
                                              'X-Collected-At': metadata['collected_at']})
        if (receipt.get('collection_job_id') != job_id or receipt.get('collection_item_id') != item_id
            or receipt.get('sha256') != metadata['sha256'] or receipt.get('size_bytes') != metadata['size_bytes']
            or receipt.get('verification_status') != 'verified'):
            raise CollectorError("Backend receipt does not match staged evidence; local copy retained")
        metadata['receipt'] = receipt
        save_manifest(manifest, metadata)
        staged.unlink()
        return receipt


def collect(client: ApiClient, job_id: str, files: list[Path], spool: Path):
    if os.name != 'nt':
        raise CollectorError("Windows Agent v1 must run on Windows")
    if sys.version_info < (3, 13):
        raise CollectorError("Windows collection requires Python 3.13+ for private staging-directory ACLs")
    job_id = str(UUID(job_id))
    job = client.request('GET', f'/agents/jobs/{job_id}')
    if job.get('id') != job_id or job.get('status') not in {'open', 'complete'}:
        raise CollectorError("Backend did not return an active matching job")
    approved = {str(PureWindowsPath(item['source_path'])).casefold(): item for item in job['files']}
    selected = []
    seen = set()
    for source in files:
        key = str(PureWindowsPath(source)).casefold()
        if not source.is_absolute() or key not in approved:
            raise CollectorError("A selected file is not in this job's approved manifest")
        if key in seen:
            raise CollectorError("Do not select a file more than once")
        seen.add(key)
        selected.append((source, approved[key]))
    if not selected:
        raise CollectorError("Select at least one file explicitly")
    spool = spool.resolve()
    spool.mkdir(mode=0o700, parents=True, exist_ok=True)
    results = []
    for source, item in selected:
        results.append(collect_item(client, job_id, source, item, spool))
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', action='version', version=VERSION)
    parser.add_argument('--backend', required=True, help='HTTPS base URL ending in /api/v1')
    parser.add_argument('--job-id', required=True)
    parser.add_argument('--file', type=Path, action='append', required=True, dest='files')
    parser.add_argument('--spool', type=Path, default=Path(__file__).resolve().parent / '.spool')
    parser.add_argument('--ca-file', help='Trusted CA bundle for a private server certificate')
    parser.add_argument('--allow-http-local', action='store_true', help='Allow HTTP only on loopback for development')
    args = parser.parse_args(argv)
    token = os.environ.get('SHADOWVAULT_AGENT_TOKEN') or getpass.getpass('Agent token: ')
    try:
        client = ApiClient(args.backend, token, allow_http_local=args.allow_http_local, ca_file=args.ca_file)
        receipts = collect(client, args.job_id, args.files, args.spool)
        print(json.dumps(receipts, indent=2))
        return 0
    except (CollectorError, OSError, ValueError, KeyError) as error:
        print(f'Collection failed: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
