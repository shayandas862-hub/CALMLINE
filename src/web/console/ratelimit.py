"""The spend rails — two allowances, one injected clock.

AD-CL-008 asks for a **per-IP cap** and a **global daily cap** in the app, in
front of the Anthropic console's own spend cap. They protect different things
and neither substitutes for the other: the per-IP cap stops one visitor draining
the demo, and the global cap stops the sum of well-behaved visitors doing the
same to the API key. Only the second one is a real spend rail.

**Both windows roll; neither resets on a clock boundary.** A cap that resets at
midnight lets a caller spend the whole allowance at 23:59 and the whole of it
again at 00:01 — twice the cap across two minutes, which is exactly the shape a
daily rail exists to prevent. A rolling window has no boundary to sit astride.

**Time is injected** (rule 8). A window measured from `time.monotonic()` can only
be exercised by sleeping, and nobody writes a test that sleeps for a day — which
is how daily caps come to be shipped never having been run.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Optional

import time

from fastapi.responses import JSONResponse

_DAY_SECONDS = 24 * 60 * 60

# Path prefixes that are never limited and never counted. The health check,
# because a 429 there makes the platform kill a service that is fine; the static
# assets, because a visitor whose CSS was refused sees a broken site rather than
# a rate-limited one. `/` is deliberately absent — it is a page load and costs
# the visitor one request, and listing it would prefix-match every route.
UNLIMITED_PATHS = ("/healthz", "/static", "/favicon.ico")


class RateLimitExceeded(Exception):
    """A caller has spent an allowance. The message names *which* one.

    A 429 that cannot say which rail was hit cannot be acted on — "wait a
    minute" and "the demo is done for today" are different instructions.
    """


@dataclass(frozen=True)
class Allowance:
    """``limit`` requests per rolling ``window_seconds``."""

    limit: int
    window_seconds: float = _DAY_SECONDS


class RateLimiter:
    """Two rolling windows: one per caller, one over everybody.

    Memory is bounded by callers **active inside the per-caller window**, not by
    callers ever seen: a caller whose hits have all aged out is forgotten. That
    matters here because the URL is public and the visitor list is unbounded.
    """

    def __init__(self, *, per_ip: Allowance, overall: Allowance,
                 clock: Optional[Callable[[], float]] = None) -> None:
        self.per_ip = per_ip
        self.overall = overall
        self._clock = clock or time.monotonic
        self._per_caller: dict[str, deque[float]] = {}
        self._all: deque[float] = deque()

    def admit(self, caller: str) -> None:
        """Record one request from ``caller``, or raise ``RateLimitExceeded``.

        **A refused request is not recorded.** Counting refusals would let a
        caller who keeps retrying extend their own lockout indefinitely, which
        punishes the impatient rather than the abusive.
        """
        now = self._clock()
        self._forget_idle(now)
        hits = self._per_caller.setdefault(caller, deque())
        _expire(hits, now - self.per_ip.window_seconds)
        _expire(self._all, now - self.overall.window_seconds)

        if len(hits) >= self.per_ip.limit:
            self._forget_idle(now)  # do not leave an empty deque behind
            raise RateLimitExceeded(
                f"too many requests from this address — "
                f"{self.per_ip.limit} per {_human(self.per_ip.window_seconds)}. "
                f"Try again shortly.")
        if len(self._all) >= self.overall.limit:
            self._forget_idle(now)
            raise RateLimitExceeded(
                f"the demo's daily request cap has been reached — "
                f"{self.overall.limit} per {_human(self.overall.window_seconds)}. "
                f"It frees up as the day rolls forward.")

        hits.append(now)
        self._all.append(now)

    def tracked_callers(self) -> int:
        """How many callers are currently held in memory, idle ones dropped."""
        self._forget_idle(self._clock())
        return len(self._per_caller)

    def _forget_idle(self, now: float) -> None:
        cutoff = now - self.per_ip.window_seconds
        for caller in [c for c, hits in self._per_caller.items()
                       if not _expire(hits, cutoff)]:
            del self._per_caller[caller]


def _expire(hits: deque[float], cutoff: float) -> int:
    """Drop hits at or before ``cutoff``; return how many remain."""
    while hits and hits[0] <= cutoff:
        hits.popleft()
    return len(hits)


def _human(seconds: float) -> str:
    if seconds >= _DAY_SECONDS:
        return "day"
    if seconds >= 3600:
        return f"{int(seconds // 3600)}h"
    return f"{int(seconds)}s"


def caller_of(request: Any, trusted_proxy_hops: int = 0) -> str:
    """Who this request is from, for allowance purposes.

    ``trusted_proxy_hops`` is **0 by default, and that is rule 11's shape**: a
    header is the client's say-so, and a limiter that trusts `X-Forwarded-For`
    unconditionally gives every caller as many allowances as they can invent
    values.

    Set it to the number of proxies you actually run in front of this app. Each
    proxy appends the peer it saw, so with one trusted hop the rightmost entry
    is the visitor and everything left of it is caller-controlled and unread.
    **Render puts exactly one proxy in front**, and without this every visitor
    shares the proxy's address — which silently turns the per-IP cap into a
    second global one.
    """
    if trusted_proxy_hops > 0:
        parts = [part.strip() for part
                 in (request.headers.get("x-forwarded-for") or "").split(",")
                 if part.strip()]
        if len(parts) >= trusted_proxy_hops:
            return parts[-trusted_proxy_hops]
    client = getattr(request, "client", None)
    return getattr(client, "host", None) or "unknown"


def install_rate_limit(app: Any, limiter: RateLimiter, *,
                       exempt: Iterable[str] = UNLIMITED_PATHS,
                       trusted_proxy_hops: int = 0) -> None:
    """Refuse over-cap requests with a 429 before they reach a route.

    ``exempt`` defaults to ``UNLIMITED_PATHS`` — what must never be limited is a
    property of rate limiting, not of any one app, so the default lives beside
    the limiter rather than at each mount point.
    """
    exempt = tuple(exempt)

    @app.middleware("http")
    async def _rate_limit(request: Any, call_next: Any) -> Any:
        if request.url.path.startswith(exempt) if exempt else False:
            return await call_next(request)
        try:
            limiter.admit(caller_of(request, trusted_proxy_hops))
        except RateLimitExceeded as exc:
            return JSONResponse(status_code=429, content={"detail": str(exc)})
        return await call_next(request)
