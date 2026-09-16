"""Small, process-local admission budget. No queue, persistence or retries."""
from collections import deque
from threading import Lock
import time
from fastapi import HTTPException


class UsageControl:
    def __init__(self, interval=5, per_minute=6, max_attempts=96, clock=time.monotonic):
        self.interval, self.per_minute, self.max_attempts = interval, per_minute, max_attempts
        self.clock = clock
        self.recent = deque()
        self.attempts = 0
        self.lock = Lock()

    def admit(self):
        with self.lock:
            now = self.clock()
            while self.recent and now - self.recent[0] >= 60:
                self.recent.popleft()
            if (self.attempts >= self.max_attempts or len(self.recent) >= self.per_minute
                    or (self.recent and now - self.recent[-1] < self.interval)):
                raise HTTPException(429, 'AI usage limit reached; retry manually only when permitted')
            self.recent.append(now)
            self.attempts += 1  # Failed/timeout attempts consume budget too.
