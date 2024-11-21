import asyncio
import time


class RateLimiter:
    """Rate limiter for API calls."""

    def __init__(self, calls: int, period: float = 60.0):
        """Initialize rate limiter.

        Args:
            calls: Number of calls allowed per period
            period: Time period in seconds
        """
        self.calls = calls
        self.period = period
        self.tokens = calls
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1):
        """Acquire tokens from the rate limiter.

        Args:
            tokens: Number of tokens to acquire
        """
        async with self._lock:
            while self.tokens < tokens:
                now = time.monotonic()
                time_passed = now - self.last_update
                new_tokens = time_passed * (self.calls / self.period)

                if new_tokens > 1:
                    self.tokens = min(self.calls, self.tokens + new_tokens)
                    self.last_update = now

                if self.tokens < tokens:
                    sleep_time = (tokens - self.tokens) * (self.period / self.calls)
                    await asyncio.sleep(sleep_time)

            self.tokens -= tokens
