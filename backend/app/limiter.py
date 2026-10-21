import asyncio
import time
from .profiles import capacity

class Limiter:
    """One shared FIFO byte budget, zero initial credit and 2 KiB grants.

    One lock queues audio/video fairly (asyncio.Lock FIFO). The rate is sampled
    every requested <=10 ms, including within a grant. Timer overshoot is kept
    while backlogged, capped at 50 ms of rate / 64 KiB (minimum one grant).
    Idle periods over 50 ms retain at most one grant, not a full wakeup burst.
    """
    def __init__(self, profile, seed, scale):
        self.profile, self.seed, self.scale = profile, seed, scale
        self.start = None
        self.lock = asyncio.Lock()
        self.bytes = 0
        self.active = 0
        self.credit = 0.
        self.updated = None
        self.last_grant = None
        self.discarded_credit = 0.

    async def grant(self, size):
        async with self.lock:
            if self.start is None: self.start = time.monotonic()
            entered=time.monotonic()
            if self.updated is None: self.updated = entered
            idle=self.last_grant is not None and entered-self.last_grant>.05
            while True:
                now = time.monotonic()
                rate = capacity(self.profile, self.seed, self.scale, now - self.start) / 8
                limit=2048 if idle else max(2048,min(65536,rate*.05))
                earned=self.credit+(now-self.updated)*rate
                self.discarded_credit+=max(0,earned-limit)
                self.credit=min(limit,earned)
                idle=False
                self.updated=now
                if self.credit>=size:
                    self.credit-=size
                    break
                await asyncio.sleep(min(.01,(size-self.credit)/rate))
            self.bytes += size
            self.last_grant=time.monotonic()
