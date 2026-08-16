"""v4 phase 7 · Task 1 — the spend rails, written fresh.

The v2 limiter was deleted with the v2 app at phase 0, so this is the first one
this tree has had. AD-CL-008 asks for two: **per-IP** so one visitor cannot
drain the demo, and a **global** cap so the sum of well-behaved visitors cannot
either. The second is the one that protects the API key.

Every test drives an **injected clock**. A limiter whose window comes from
`time.monotonic()` can only be tested by sleeping, and a test that sleeps for a
24-hour window is a test nobody writes — which is how daily caps come to be
shipped unexercised.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.web.console.ratelimit import (Allowance, RateLimitExceeded,
                                       RateLimiter, install_rate_limit)


class FakeClock:
    """A monotonic clock the test moves by hand."""

    def __init__(self, start: float = 1000.0) -> None:
        self.t = start

    def __call__(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


def build(*, per_ip=3, ip_window=60.0, total=10, total_window=86_400.0):
    clock = FakeClock()
    limiter = RateLimiter(per_ip=Allowance(per_ip, ip_window),
                          overall=Allowance(total, total_window),
                          clock=clock)
    return limiter, clock


# ── the per-IP allowance ───────────────────────────────────────────────
def test_allows_up_to_the_cap_then_refuses():
    limiter, _ = build(per_ip=3)
    for _ in range(3):
        limiter.admit("1.2.3.4")
    with pytest.raises(RateLimitExceeded):
        limiter.admit("1.2.3.4")


def test_the_window_rolls_forward_rather_than_resetting_on_the_hour():
    """A fixed midnight reset lets one caller spend twice the cap across it."""
    limiter, clock = build(per_ip=2, ip_window=60.0)
    limiter.admit("1.2.3.4")
    clock.advance(30)
    limiter.admit("1.2.3.4")
    with pytest.raises(RateLimitExceeded):
        limiter.admit("1.2.3.4")
    clock.advance(31)  # the first hit is now outside the window, the second is not
    limiter.admit("1.2.3.4")
    with pytest.raises(RateLimitExceeded):
        limiter.admit("1.2.3.4")


def test_one_caller_cannot_spend_another_callers_allowance():
    limiter, _ = build(per_ip=1)
    limiter.admit("1.2.3.4")
    limiter.admit("5.6.7.8")  # untouched by the first
    with pytest.raises(RateLimitExceeded):
        limiter.admit("1.2.3.4")


# ── the global allowance — the one that protects the key ───────────────
def test_the_global_cap_refuses_a_caller_who_has_spent_nothing():
    """The rail AD-CL-008 actually needs: many polite visitors are still spend."""
    limiter, _ = build(per_ip=100, total=3)
    for ip in ("1.1.1.1", "2.2.2.2", "3.3.3.3"):
        limiter.admit(ip)
    with pytest.raises(RateLimitExceeded) as exc:
        limiter.admit("4.4.4.4")
    assert "daily" in str(exc.value).lower()


def test_the_two_caps_are_reported_apart():
    """A 429 that cannot say which rail was hit cannot be acted on."""
    limiter, _ = build(per_ip=1, total=100)
    limiter.admit("1.2.3.4")
    with pytest.raises(RateLimitExceeded) as exc:
        limiter.admit("1.2.3.4")
    assert "daily" not in str(exc.value).lower()


def test_a_refused_request_is_not_counted_against_the_allowance():
    """Otherwise a caller who keeps retrying extends their own lockout for ever."""
    limiter, clock = build(per_ip=1, ip_window=60.0)
    limiter.admit("1.2.3.4")
    for _ in range(5):
        with pytest.raises(RateLimitExceeded):
            limiter.admit("1.2.3.4")
    clock.advance(61)
    limiter.admit("1.2.3.4")  # the five refusals left no trace


# ── memory, on a URL anyone can hit ────────────────────────────────────
def test_idle_callers_are_forgotten():
    """Bounded by callers *active in the window*, not by callers ever seen."""
    limiter, clock = build(per_ip=1, ip_window=60.0, total=1000)
    for n in range(50):
        limiter.admit(f"10.0.0.{n}")
    assert limiter.tracked_callers() == 50
    clock.advance(61)
    limiter.admit("10.0.0.0")
    assert limiter.tracked_callers() == 1


# ── mounted on an app ──────────────────────────────────────────────────
def _app(limiter, **kw):
    app = FastAPI()

    @app.get("/api/agent")
    def agent() -> dict:
        return {"ok": True}

    @app.get("/healthz")
    def healthz() -> dict:
        return {"ok": True}

    install_rate_limit(app, limiter, **kw)
    return TestClient(app)


def test_the_endpoint_returns_429_with_a_plain_reason():
    limiter, _ = build(per_ip=1)
    client = _app(limiter)
    assert client.get("/api/agent").status_code == 200
    refused = client.get("/api/agent")
    assert refused.status_code == 429
    assert "detail" in refused.json()
    assert refused.json()["detail"].strip()


def test_healthz_is_never_rate_limited():
    """A health check that 429s makes the platform kill a service that is fine."""
    limiter, _ = build(per_ip=1, total=1)
    client = _app(limiter, exempt=("/healthz",))
    client.get("/api/agent")
    client.get("/api/agent")  # blows both caps
    for _ in range(5):
        assert client.get("/healthz").status_code == 200


def test_an_exempt_path_does_not_spend_the_allowance_either():
    limiter, _ = build(per_ip=2)
    client = _app(limiter, exempt=("/healthz",))
    for _ in range(10):
        client.get("/healthz")
    assert client.get("/api/agent").status_code == 200
    assert client.get("/api/agent").status_code == 200
    assert client.get("/api/agent").status_code == 429


# ── who the caller is, behind a proxy ──────────────────────────────────
def test_a_forwarded_header_is_ignored_by_default():
    """Rule 11's shape: never take from the client's say-so unless told to.

    Trusted by default, a caller sets X-Forwarded-For per request and has an
    unlimited number of allowances.
    """
    limiter, _ = build(per_ip=1)
    client = _app(limiter)
    assert client.get("/api/agent", headers={"X-Forwarded-For": "9.9.9.1"}).status_code == 200
    assert client.get("/api/agent", headers={"X-Forwarded-For": "9.9.9.2"}).status_code == 429


def test_one_trusted_hop_reads_the_client_from_the_right_of_the_header():
    """On Render every request arrives from the platform's proxy, so without
    this every visitor shares one bucket and the per-IP cap becomes a global
    one. With exactly one trusted proxy the rightmost entry is the peer it saw."""
    limiter, _ = build(per_ip=1)
    client = _app(limiter, trusted_proxy_hops=1)
    assert client.get("/api/agent",
                      headers={"X-Forwarded-For": "9.9.9.1"}).status_code == 200
    assert client.get("/api/agent",
                      headers={"X-Forwarded-For": "9.9.9.2"}).status_code == 200
    assert client.get("/api/agent",
                      headers={"X-Forwarded-For": "9.9.9.1"}).status_code == 429


def test_a_spoofed_chain_cannot_widen_its_own_allowance():
    """With one trusted hop the caller controls everything left of the last
    entry — and none of it is read."""
    limiter, _ = build(per_ip=1)
    client = _app(limiter, trusted_proxy_hops=1)
    assert client.get("/api/agent",
                      headers={"X-Forwarded-For": "1.1.1.1, 9.9.9.1"}).status_code == 200
    assert client.get("/api/agent",
                      headers={"X-Forwarded-For": "2.2.2.2, 9.9.9.1"}).status_code == 429


# ── mounted on the real console ────────────────────────────────────────
def test_the_console_refuses_over_cap_and_leaves_its_assets_alone():
    """The wiring, not the algorithm: a limiter passed to `create_console_app`
    covers the API and leaves `/static` reachable."""
    from src.web.console.app import create_console_app

    limiter, _ = build(per_ip=2, total=100)
    client = TestClient(create_console_app(secret="test-secret", rate_limit=limiter))

    assert client.post("/api/login", json={"role": "front_office",
                                           "actor": "handler_1"}).status_code == 200
    assert client.get("/api/policy/WL-88213").status_code in (200, 401, 403, 428)
    assert client.get("/api/policy/WL-88213").status_code == 429
    for _ in range(5):
        assert client.get("/static/console.css").status_code == 200


def test_the_console_is_unlimited_unless_a_limiter_is_supplied():
    """Why the whole suite did not have to learn about allowances."""
    from src.web.console.app import create_console_app

    client = TestClient(create_console_app(secret="test-secret"))
    for _ in range(25):
        assert client.post("/api/login", json={"role": "front_office",
                                               "actor": "handler_1"}).status_code == 200


def test_no_wall_clock_anywhere_in_the_module():
    """Rule 8, asserted rather than trusted — the whole file is injected time."""
    import inspect

    import src.web.console.ratelimit as module

    source = inspect.getsource(module)
    assert "datetime.now" not in source
    assert "time.time()" not in source
