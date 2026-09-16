"""Shared URL and credential validation. Secrets are never written to configuration files."""
from urllib.parse import urlsplit
from .errors import CollectorError

REQUEST_TIMEOUT_SECONDS = 120

def validate_connection(base_url, token, allow_http_local=False):
    parsed = urlsplit(base_url)
    if not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise CollectorError("Use a backend URL without credentials, query or fragment")
    if parsed.scheme != 'https' and not (
        parsed.scheme == 'http' and allow_http_local and parsed.hostname in {'localhost', '127.0.0.1', '::1'}
    ):
        raise CollectorError("HTTPS is required; --allow-http-local permits loopback development only")
    if not token or len(token) > 256 or any(ord(c) < 33 or ord(c) > 126 for c in token):
        raise CollectorError("A valid agent token is required")
    return parsed
