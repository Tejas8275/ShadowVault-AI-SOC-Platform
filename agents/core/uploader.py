"""Shared HTTPS transport; redirects are never followed."""
import http.client
import json
import ssl
import re
from .errors import CollectorError
from .config import REQUEST_TIMEOUT_SECONDS, validate_connection

MAX_RESPONSE_BYTES = 64 * 1024
# 100 paths of 1024 Unicode characters can expand to 12 JSON escape bytes per
# character, plus bounded job/item metadata. Keep a finite 2 MiB manifest ceiling.
MAX_MANIFEST_RESPONSE_BYTES = 2 * 1024 * 1024

class ApiClient:
    def __init__(self, base_url, token, *, allow_http_local=False, ca_file=None):
        parsed = validate_connection(base_url, token, allow_http_local)
        self.base_url = base_url.rstrip('/')
        self.parsed = parsed
        self.token = token
        self.ssl_context = ssl.create_default_context(cafile=ca_file)

    def request(self, method, path, *, body=None, headers=None):
        if self.parsed.scheme == 'https':
            connection = http.client.HTTPSConnection(self.parsed.hostname, self.parsed.port or 443,
                                                     timeout=REQUEST_TIMEOUT_SECONDS, context=self.ssl_context)
        else:
            connection = http.client.HTTPConnection(self.parsed.hostname, self.parsed.port or 80, timeout=REQUEST_TIMEOUT_SECONDS)
        supplied = {'Authorization': f'Bearer {self.token}', 'Accept': 'application/json'}
        supplied.update(headers or {})
        try:
            connection.request(method, self.parsed.path.rstrip('/') + path, body=body, headers=supplied)
            response = connection.getresponse()
            manifest = method == 'GET' and re.fullmatch(
                r'/agents/jobs/[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}', path)
            limit = MAX_MANIFEST_RESPONSE_BYTES if manifest and response.status == 200 else MAX_RESPONSE_BYTES
            data = response.read(limit + 1)
            if len(data) > limit:
                raise CollectorError("Backend response exceeds the expected size")
            if response.status not in (200, 201):
                # No redirects are followed; credentials never travel to a redirect target.
                raise CollectorError(f"Backend returned HTTP {response.status}; staged evidence retained")
            try:
                return json.loads(data)
            except (ValueError, UnicodeError):
                raise CollectorError("Backend returned invalid JSON") from None
        except (OSError, http.client.HTTPException) as error:
            raise CollectorError(f"Connection failed ({type(error).__name__}); staged evidence retained") from None
        finally:
            connection.close()

