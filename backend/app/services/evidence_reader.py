"""Read opaque originals through validated handles; serve a verified private copy."""
import hashlib
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
import time

from fastapi import HTTPException


def _regular(info):
    if not stat.S_ISREG(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
        raise OSError('Unsupported evidence object')


def _plain_directory(path):
    # Deployment ancestors are trusted, but known links/junctions are never followed.
    for part in (path, *path.parents):
        info = part.lstat()
        if not stat.S_ISDIR(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise OSError('Unsupported storage directory')


def _windows_open(path):
    import ctypes
    from ctypes import wintypes
    import msvcrt

    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    create = kernel.CreateFileW
    create.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
                       wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    create.restype = wintypes.HANDLE
    close = kernel.CloseHandle
    close.argtypes = [wintypes.HANDLE]
    close.restype = wintypes.BOOL
    final_name = kernel.GetFinalPathNameByHandleW
    final_name.argtypes = [wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD]
    final_name.restype = wintypes.DWORD
    # Read access, read sharing only, OPEN_EXISTING, OPEN_REPARSE_POINT.
    # Deny concurrent write/delete handles while copying the original.
    handle = create(str(path), 0x80000000, 1, None, 3, 0x00200000, None)
    if handle == wintypes.HANDLE(-1).value:
        raise OSError('Evidence handle unavailable')
    try:
        buffer = ctypes.create_unicode_buffer(32768)
        length = final_name(handle, buffer, len(buffer), 0)
        if not length or length >= len(buffer):
            raise OSError('Evidence handle location unavailable')
        actual = buffer.value
        if actual.startswith('\\\\?\\'):
            actual = actual[4:]
        if os.path.normcase(actual) != os.path.normcase(str(path)):
            raise OSError('Evidence handle escaped storage')
        fd = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
        handle = None  # fd owns the Windows handle now.
        return os.fdopen(fd, 'rb')
    finally:
        if handle is not None:
            close(handle)


def open_original(root: Path, key: str):
    # Only Phase 2A server-generated names are supported; never map legacy paths.
    if not re.fullmatch(r'[0-9a-f]{32}\.blob', key):
        raise OSError('Unsupported storage key')
    root = Path(os.path.abspath(root))
    _plain_directory(root)
    path = root / key
    _regular(path.lstat())
    if os.name == 'nt':
        handle = _windows_open(path)
    else:
        directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            fd = os.open(key, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
            handle = os.fdopen(fd, 'rb')
        finally:
            os.close(directory)
    try:
        _regular(os.fstat(handle.fileno()))
        return handle
    except BaseException:
        handle.close()
        raise


def prepare_copy(settings, key, expected_size, expected_digest):
    if os.name == 'nt' and sys.version_info < (3, 13):
        raise OSError('Private Windows retrieval storage requires Python 3.13+')
    if expected_size > settings.max_retrieval_bytes:
        raise HTTPException(413, 'Evidence exceeds retrieval size policy')
    deadline = time.monotonic() + settings.retrieval_timeout_seconds
    temporary = None
    try:
        settings.retrieval_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        _plain_directory(Path(os.path.abspath(settings.retrieval_dir)))
        temporary = tempfile.TemporaryFile(mode='w+b', dir=settings.retrieval_dir)
        count, digest = 0, hashlib.sha256()
        with open_original(settings.evidence_dir, key) as original:
            if os.fstat(original.fileno()).st_size != expected_size:
                raise HTTPException(409, 'Evidence size or digest does not match its record')
            while True:
                if time.monotonic() >= deadline:
                    raise HTTPException(503, 'Evidence preparation timed out')
                chunk = original.read(64 * 1024)
                if not chunk:
                    break
                count += len(chunk)
                if count > expected_size or count > settings.max_retrieval_bytes:
                    raise HTTPException(409, 'Evidence size or digest does not match its record')
                digest.update(chunk)
                temporary.write(chunk)
        if count != expected_size or digest.hexdigest() != expected_digest:
            raise HTTPException(409, 'Evidence size or digest does not match its record')
        temporary.flush()
        temporary.seek(0)
        return temporary
    except BaseException:
        if temporary is not None:
            temporary.close()
        raise
