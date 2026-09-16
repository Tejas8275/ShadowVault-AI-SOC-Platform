"""Explicit request-scoped adapter process. No shell, model, SDK or fallback.

The reviewed script reads one JSON request from stdin and writes one JSON
response to stdout. Counting MUST be local and include actual model framing.
Selection MUST perform at most one bounded request, without tools or retries.
This is resource isolation, not a sandbox for hostile administrator code.
"""
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys


class CommandProvider:
    def __init__(self, script, key=None):
        script = Path(script)
        if not script.is_absolute() or not script.is_file() or script.suffix != '.py':
            raise ValueError('AI adapter requires an existing absolute Python script')
        self.script = script.resolve()
        # Do not inherit operator/database settings or Python injection variables.
        self.environment = {k: v for k, v in os.environ.items()
                            if k.upper() in {'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP'}}
        if key is not None:
            self.environment['SHADOWVAULT_AI_PROVIDER_API_KEY'] = key.get_secret_value()

    async def _call(self, operation, instructions, data, limit, **options):
        payload = json.dumps(dict(operation=operation, instructions=instructions,
                                  data=data, **options), ensure_ascii=False).encode('utf-8')
        process = await asyncio.create_subprocess_exec(
            sys.executable, '-I', '-X', 'utf8', str(self.script), stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
            cwd=str(self.script.parent), env=self.environment,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        async def exchange():
            process.stdin.write(payload)
            await process.stdin.drain()
            process.stdin.close()
            chunks = bytearray()
            while True:
                part = await process.stdout.read(min(4096, limit + 1 - len(chunks)))
                if not part:
                    break
                chunks.extend(part)
                if len(chunks) > limit:
                    raise ValueError('AI adapter response exceeds limits')
            if await process.wait() != 0:
                raise ValueError('AI adapter failed')
            return chunks.decode('utf-8')
        try:
            return await exchange()
        finally:
            if process.returncode is None:
                try:
                    process.kill()
                except ProcessLookupError:
                    pass
            process.stdin.close()
            # Consume/discard remaining bounded pipe chunks after termination;
            # wait() alone can leave a paused Windows stdout transport open.
            async def drain():
                while await process.stdout.read(4096):
                    pass
                await process.wait()
            try:
                await asyncio.wait_for(drain(), timeout=1)
            finally:
                # Process has no public close() API. Close its transport even if
                # an incorrectly written adapter left an inherited pipe open.
                process._transport.close()

    async def count_input_tokens(self, *, instructions, data):
        raw = await self._call('count', instructions, data, 128)
        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError('Duplicate token count field')
                result[key] = value
            return result
        value = json.loads(raw, object_pairs_hook=unique)
        if not isinstance(value, dict) or set(value) != {'input_tokens'} or type(value['input_tokens']) is not int:
            raise ValueError('Invalid token count')
        return value['input_tokens']

    async def select_sources(self, *, instructions, data, max_output_bytes, max_output_tokens):
        return await self._call('select', instructions, data, max_output_bytes,
                                max_output_bytes=max_output_bytes, max_output_tokens=max_output_tokens)
