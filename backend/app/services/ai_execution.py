"""One bounded request, including counting. No automatic retry."""
import asyncio
import inspect
import time
from fastapi import HTTPException
from starlette.concurrency import run_in_threadpool
from app.services.ai_adapter import CommandProvider
from app.services.ai_model import SYSTEM_INSTRUCTIONS


class BoundedCall:
    def __init__(self, provider, data, seconds, input_tokens, output_bytes):
        self.provider, self.data, self.seconds = provider, data, seconds
        self.input_tokens, self.output_bytes = input_tokens, output_bytes
        self.task = self.loop = self.operation_task = None
        self.cancelled = False

    async def _operation(self):
        self.loop = asyncio.get_running_loop()
        self.operation_task = asyncio.current_task()
        start = time.monotonic()
        if self.cancelled:
            raise TimeoutError()
        count = self.provider.count_input_tokens(instructions=SYSTEM_INSTRUCTIONS, data=self.data)
        if inspect.isawaitable(count):
            count = await count
        if self.cancelled or time.monotonic() - start >= self.seconds:
            raise TimeoutError()
        if type(count) is not int or count < 1:
            raise ValueError('Invalid token count')
        if count > self.input_tokens:
            raise HTTPException(413, 'AI metadata context exceeds limits')
        return await self.provider.select_sources(instructions=SYSTEM_INSTRUCTIONS, data=self.data,
            max_output_bytes=self.output_bytes, max_output_tokens=1024)

    def _trusted_injected_call(self):
        # Existing injected providers remain supported, off the ASGI event loop.
        # Unlike a command adapter, arbitrary Python cannot be forcibly killed.
        async def run():
            return await asyncio.wait_for(self._operation(), self.seconds)
        return asyncio.run(run())

    def _cancel(self):
        self.cancelled = True
        if self.loop and not self.loop.is_closed() and self.operation_task:
            try:
                self.loop.call_soon_threadsafe(self.operation_task.cancel)
            except RuntimeError:
                pass  # The private loop already finished.

    async def run(self):
        if isinstance(self.provider, CommandProvider):
            return await asyncio.wait_for(self._operation(), self.seconds)
        self.task = asyncio.create_task(run_in_threadpool(self._trusted_injected_call))
        try:
            done, _ = await asyncio.wait({self.task}, timeout=self.seconds)
            if not done:
                self._cancel()
                # Brief grace for cooperative cleanup, never wait indefinitely.
                await asyncio.wait({self.task}, timeout=0.1)
                raise TimeoutError()
            return self.task.result()
        except BaseException:
            self._cancel()
            raise

    def release(self, release_slot):
        def finished(task):
            try:
                task.exception()  # Consume sanitized failure, never log context.
            except BaseException:
                pass
            release_slot()
        if self.task:
            # A non-cooperative injected provider quarantines the one slot until
            # it finishes. Repeated calls cannot accumulate abandoned threads.
            if self.task.done():
                finished(self.task)
            else:
                self.task.add_done_callback(finished)
        else:
            release_slot()
