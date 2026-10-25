"""Live alert feed: the console publishes its state, /api/alerts/stream relays it over SSE.

Streaming tests run a real uvicorn on a free loopback port (an endless SSE body hangs in-process transports);
every read has a timeout so a bug fails instead of hanging. Publisher-trust tests use httpx's ASGI transport,
which lets them pretend to be a remote client.
"""

import asyncio
import json
import socket
import threading
import time

import httpx
import pytest
import uvicorn

import server

TIMEOUT = httpx.Timeout(3.0)


@pytest.fixture(scope="module")
def base():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    srv = uvicorn.Server(uvicorn.Config(server.app, host="127.0.0.1", port=port, log_level="warning", lifespan="on"))
    th = threading.Thread(target=srv.run, daemon=True)
    th.start()
    deadline = time.monotonic() + 10
    while not srv.started:
        assert th.is_alive() and time.monotonic() < deadline, "uvicorn did not start"
        time.sleep(0.02)
    yield f"http://127.0.0.1:{port}"
    srv.should_exit = True
    th.join(timeout=5)


@pytest.fixture(autouse=True)
def fresh_bus(monkeypatch):
    monkeypatch.setattr(server, "HEARTBEAT_S", 0.2)
    monkeypatch.setattr(server, "STALE_S", 3.0)
    monkeypatch.delenv("PERISCOPE_ALERT_TOKEN", raising=False)
    monkeypatch.delenv("WEB_CONCURRENCY", raising=False)
    server.bus.reset()
    yield
    server.bus.reset()


class Stream:
    def __init__(self, resp):
        self.lines = resp.iter_lines()

    def next(self):
        event = data = None
        for line in self.lines:
            if line.startswith("event: "):
                event = line[7:]
            elif line.startswith("data: "):
                data = json.loads(line[6:])
            elif line == "" and event:
                return event, data
        raise EOFError("stream closed")

    def until(self, event, limit=40):
        """Next `event`, skipping heartbeats; fails on any other event first."""
        for _ in range(limit):
            ev, data = self.next()
            if ev == event:
                return data
            assert ev == "heartbeat", f"expected {event}, got {ev} {data}"
        raise AssertionError(f"no {event} event")


def subscribe(client, base):
    """Open the stream and consume the connect heartbeat, so the subscriber is registered before we post."""
    cm = client.stream("GET", base + "/api/alerts/stream")
    resp = cm.__enter__()
    assert resp.status_code == 200 and resp.headers["content-type"].startswith("text/event-stream")
    s = Stream(resp)
    ev, hb = s.next()
    assert ev == "heartbeat"
    return cm, s, hb


def status(client, base, run, live=True, reason=None):
    r = client.post(base + "/api/alerts/status", json={"run": run, "live": live, "reason": reason})
    assert r.status_code == 200, r.text
    return r.json()


def alert(client, base, run="A", state="someone", level="watch", bearing=41.5, conf=0.8, t=1.0):
    return client.post(base + "/api/alerts", json={"run": run, "state": state, "level": level, "bearing_deg": bearing,
                                                   "confidence": conf, "t": t})


def test_state_change_is_emitted(base):
    with httpx.Client(timeout=TIMEOUT) as c:
        status(c, base, "A")
        cm, s, _ = subscribe(c, base)
        try:
            r = alert(c, base, t=1.0)
            assert r.json() == {"sent": True, "subscribers": 1}
            assert s.until("alert") == {"run": "A", "state": "someone", "level": "watch", "bearing_deg": 41.5,
                                        "confidence": 0.8, "t": 1.0}
            alert(c, base, state="clear", level=None, bearing=12.0, conf=0.1, t=2.0)
            got = s.until("alert")
            assert got["state"] == "clear" and got["bearing_deg"] is None and got["level"] is None
        finally:
            cm.__exit__(None, None, None)


def test_duplicate_state_not_reemitted(base):
    with httpx.Client(timeout=TIMEOUT) as c:
        status(c, base, "A")
        cm, s, _ = subscribe(c, base)
        try:
            assert alert(c, base, t=1.0).json()["sent"] is True
            assert alert(c, base, bearing=44.0, t=1.5).json()["sent"] is False
            s.until("alert")
            ev, _ = s.next()
            assert ev == "heartbeat"              # nothing else queued: the duplicate was dropped
        finally:
            cm.__exit__(None, None, None)


def test_escalation_present_to_coming_emitted(base):
    with httpx.Client(timeout=TIMEOUT) as c:
        status(c, base, "A")
        cm, s, _ = subscribe(c, base)
        try:
            alert(c, base, level="watch", t=1.0)
            assert s.until("alert")["level"] == "watch"
            assert alert(c, base, level="stop", t=1.2).json()["sent"] is True
            got = s.until("alert")
            assert got["state"] == "someone" and got["level"] == "stop"
            assert alert(c, base, level="stop", t=1.4).json()["sent"] is False
        finally:
            cm.__exit__(None, None, None)


def test_heartbeat_carries_liveness(base):
    with httpx.Client(timeout=TIMEOUT) as c:
        status(c, base, "A")
        cm, s, hb = subscribe(c, base)
        try:
            assert hb["live"] is True and hb["run"] == "A" and isinstance(hb["age_s"], float)
            t0 = time.monotonic()
            ev, hb2 = s.next()
            assert ev == "heartbeat" and isinstance(hb2["t"], float)
            assert time.monotonic() - t0 < 2 * 0.2 + 0.3
        finally:
            cm.__exit__(None, None, None)


def test_clean_disconnect(base):
    with httpx.Client(timeout=TIMEOUT) as c:
        cm, s, _ = subscribe(c, base)
        assert len(server.bus.subscribers) == 1
        cm.__exit__(None, None, None)
        deadline = time.monotonic() + 2
        while server.bus.subscribers and time.monotonic() < deadline:
            time.sleep(0.05)
        assert not server.bus.subscribers
        status(c, base, "A")
        r = alert(c, base)
        assert r.status_code == 200 and r.json()["subscribers"] == 0


def test_bad_alert_rejected(base):
    with httpx.Client(timeout=TIMEOUT) as c:
        status(c, base, "A")
        assert alert(c, base, state="maybe").status_code == 422
        assert alert(c, base, conf=1.5).status_code == 422
        assert alert(c, base, level=None).status_code == 422            # someone needs a level
        assert alert(c, base, state="clear", level="stop").status_code == 422
        r = c.post(base + "/api/alerts", content=json.dumps({"run": "A", "state": "clear", "confidence": 0, "t": 1}),
                   headers={"content-type": "text/plain"})
        assert r.status_code == 422                                     # a CORS "simple" request cannot publish


@pytest.mark.parametrize("reason", ["paused", "ended", "error"])
def test_pause_marks_alert_stale(base, reason):
    with httpx.Client(timeout=TIMEOUT) as c:
        status(c, base, "A")
        cm, s, _ = subscribe(c, base)
        try:
            alert(c, base, t=1.0)
            s.until("alert")
            status(c, base, "A", live=False, reason=reason)
            assert s.until("stale") == {"run": "A", "reason": reason, "t": pytest.approx(time.time(), abs=5)}
            ev, hb = s.next()
            assert ev == "heartbeat" and hb["live"] is False
        finally:
            cm.__exit__(None, None, None)
        cm, late, hb = subscribe(c, base)                               # a late subscriber gets no old alert
        try:
            assert hb["live"] is False
            assert late.next()[0] == "heartbeat"
        finally:
            cm.__exit__(None, None, None)


def test_keepalive_timeout_marks_stale(base, monkeypatch):
    monkeypatch.setattr(server, "STALE_S", 0.3)
    with httpx.Client(timeout=TIMEOUT) as c:
        status(c, base, "A")
        cm, s, _ = subscribe(c, base)
        try:
            assert alert(c, base, t=1.0).status_code == 200
            s.until("alert")
            t0 = time.monotonic()
            assert s.until("stale")["reason"] == "timeout"
            assert time.monotonic() - t0 < 1.0
        finally:
            cm.__exit__(None, None, None)


def test_run_switch_while_learning(base):
    with httpx.Client(timeout=TIMEOUT) as c:
        status(c, base, "A")
        cm, s, _ = subscribe(c, base)
        try:
            alert(c, base, run="A", t=5.0)
            s.until("alert")
            status(c, base, "B")                                       # B is still learning: it publishes nothing
            assert s.until("stale") == {"run": "A", "reason": "switched", "t": pytest.approx(time.time(), abs=5)}
        finally:
            cm.__exit__(None, None, None)
        cm, late, hb = subscribe(c, base)
        try:
            assert hb["live"] is True and hb["run"] == "B"
            assert late.next()[0] == "heartbeat"                       # no alert from A carried over
        finally:
            cm.__exit__(None, None, None)


def test_backward_t_rejected_and_seek_resets(base):
    with httpx.Client(timeout=TIMEOUT) as c:
        status(c, base, "A")
        cm, s, _ = subscribe(c, base)
        try:
            alert(c, base, level="watch", t=5.0)
            s.until("alert")
            r = alert(c, base, state="clear", level=None, t=4.0)
            assert r.status_code == 409
            status(c, base, "A", live=False, reason="seek")
            assert s.until("stale")["reason"] == "seek"
            status(c, base, "A")
            assert alert(c, base, level="watch", t=4.0).json()["sent"] is True   # resent after the seek
            assert s.until("alert")["t"] == 4.0
        finally:
            cm.__exit__(None, None, None)


def test_replay_from_ended_republishes(base):
    """The console's replay sequence: the run ends (stale), Play restarts at frame 0 and goes live again. The
    replay's alerts start back at t≈0 and must be accepted and emitted, even the same state the run ended on."""
    with httpx.Client(timeout=TIMEOUT) as c:
        status(c, base, "A")
        cm, s, _ = subscribe(c, base)
        try:
            alert(c, base, level="watch", t=20.0)
            s.until("alert")
            status(c, base, "A", live=False, reason="ended")
            assert s.until("stale")["reason"] == "ended"
            assert alert(c, base, state="clear", level=None, t=0.5).status_code == 409   # not live until it really plays
            status(c, base, "A")
            assert alert(c, base, level="watch", t=0.5).json()["sent"] is True
            assert s.until("alert")["t"] == 0.5
        finally:
            cm.__exit__(None, None, None)


def test_alert_requires_live_run(base):
    with httpx.Client(timeout=TIMEOUT) as c:
        assert alert(c, base, run="A").status_code == 409              # nothing playing
        status(c, base, "A")
        assert alert(c, base, run="B").status_code == 409              # not the playing run


def asgi(fn, client=("10.0.0.5", 1234)):
    async def go():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(server.app, client=client),
                                     base_url="http://periscope.local") as c:
            return await fn(c)
    return asyncio.run(go())


def test_non_loopback_publisher_forbidden():
    async def fn(c):
        return [(await c.post("/api/alerts/status", json={"run": "A", "live": True})).status_code,
                (await c.post("/api/alerts", json={"run": "A", "state": "clear", "confidence": 0, "t": 1})).status_code]
    assert asgi(fn) == [403, 403]
    assert server.bus.live is False


def test_token_required_when_set(monkeypatch):
    monkeypatch.setenv("PERISCOPE_ALERT_TOKEN", "s3cret")
    body = {"run": None, "live": False, "reason": "paused"}

    async def fn(c):
        return [(await c.post("/api/alerts/status", json=body)).status_code,
                (await c.post("/api/alerts/status", json=body, headers={"Authorization": "Bearer nope"})).status_code,
                (await c.post("/api/alerts/status", json=body, headers={"Authorization": "Bearer s3cret"})).status_code]
    assert asgi(fn) == [401, 401, 200]          # the token replaces the loopback check, even from 10.0.0.5


def test_cross_origin_post_forbidden(base):
    with httpx.Client(timeout=TIMEOUT) as c:
        r = c.post(base + "/api/alerts/status", json={"run": "A", "live": True}, headers={"Origin": "http://evil.example"})
        assert r.status_code == 403
        assert server.bus.live is False


def test_same_origin_post_allowed(base):
    with httpx.Client(timeout=TIMEOUT) as c:
        r = c.post(base + "/api/alerts/status", json={"run": "A", "live": True}, headers={"Origin": base})
        assert r.status_code == 200 and r.json()["live"] is True


def test_overflowing_subscriber_closed(monkeypatch):
    monkeypatch.setattr(server, "QUEUE_MAX", 2)

    async def go():
        b = server.AlertBus()
        sub = b.subscribe()                                            # never reads
        b.set_status(server.Status(run="A", live=True))
        for k, (state, level) in enumerate([("someone", "watch"), ("clear", None), ("someone", "stop")]):
            b.publish(server.Alert(run="A", state=state, level=level, confidence=0.5, t=float(k)))
        assert sub.overflow and sub not in b.subscribers

        async def connected():
            return False
        out = [chunk async for chunk in server._events(b, connected, sub)]
        assert out[-1].startswith("event: resync")                     # told to reconnect, then the stream ends
        assert sub not in b.subscribers
    asyncio.run(go())


def test_multi_worker_refused(monkeypatch):
    monkeypatch.setenv("WEB_CONCURRENCY", "4")
    with pytest.raises(RuntimeError, match="single worker"):
        server.check_single_worker()
    monkeypatch.setenv("WEB_CONCURRENCY", "1")
    server.check_single_worker()
