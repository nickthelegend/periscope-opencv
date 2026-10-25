"""Periscope web server: the console page, recorded runs, analysis of an uploaded corner clip, and the live alert feed.

    uvicorn server:app --port 8040        # then open http://localhost:8040

The alert feed is relayed, not computed: the console (web/index.html) already works out the corner state for
each frame while it plays a run, POSTs every change here, and GET /api/alerts/stream fans it out over SSE.
The bus lives in this process, so run a single worker.
"""

from __future__ import annotations

import asyncio
import hmac
import json
import os
import shutil
import time
import uuid
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator

from periscope.geometry import Calibration
from periscope.pipeline import export_run, read_video

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
RUNS = Path(os.getenv("PERISCOPE_RUNS", WEB / "runs"))
RUNS.mkdir(parents=True, exist_ok=True)
MAX_BYTES = 500 * 1024 * 1024

# Alert-feed timing. The three are independent; the console keeps alive every 1 s (KEEPALIVE_MS in index.html),
# and STALE_S must stay >= 2x that so one lost keepalive does not end the run. Read at call time (tests patch them).
HEARTBEAT_S = 5.0   # subscriber liveness: a heartbeat at least this often
STALE_S = 3.0       # no keepalive or alert from the playing console for this long -> "stale"
WATCH_S = 0.25      # how often the watchdog checks STALE_S
QUEUE_MAX = 64      # events buffered per subscriber before it is told to resync
LOOPBACK = {"127.0.0.1", "::1"}
ALERT_LEVEL_DETAIL = "level is required for someone and must be null for clear"


class Alert(BaseModel):
    run: str = Field(min_length=1, max_length=64)
    state: Literal["clear", "someone"]
    level: Literal["watch", "stop"] | None = None      # someone: "watch" (present) or "stop" (coming)
    bearing_deg: float | None = None
    confidence: float = Field(ge=0, le=1)
    t: float = Field(ge=0)                             # run clock, s

    @model_validator(mode="after")
    def _level_matches_state(self):
        if (self.state == "someone") != (self.level is not None):
            raise ValueError(ALERT_LEVEL_DETAIL)
        if self.state == "clear":
            self.bearing_deg = None
        return self


class Status(BaseModel):
    run: str | None = Field(None, min_length=1, max_length=64)
    live: bool
    reason: Literal["playing", "paused", "ended", "seek", "switched", "closed", "error"] | None = None

    @model_validator(mode="after")
    def _live_needs_run(self):
        if self.live and not self.run:
            raise ValueError("live status needs a run")
        if not self.live and self.reason == "playing":
            raise ValueError("a non-live status needs a stale reason")
        return self


class Subscriber:
    def __init__(self):
        self.q: asyncio.Queue = asyncio.Queue(QUEUE_MAX)
        self.overflow = False


class AlertBus:
    """Process-local relay of the console's alert state. Touched only from the server's event loop."""

    def __init__(self):
        self.subscribers: set[Subscriber] = set()
        self.reset()

    def reset(self):
        self.live_run: str | None = None
        self.live = False
        self.last_seen: float | None = None            # monotonic time of the last keepalive or alert
        self.latest: dict[str, Alert] = {}
        self.last_key: dict[str, tuple] = {}
        self.last_t: dict[str, float] = {}

    def subscribe(self) -> Subscriber:
        sub = Subscriber()
        self.subscribers.add(sub)
        return sub

    def _broadcast(self, event: str, data: dict):
        for sub in list(self.subscribers):
            try:
                sub.q.put_nowait((event, data))
            except asyncio.QueueFull:                  # too slow: its stream sends "resync" and closes
                sub.overflow = True
                self.subscribers.discard(sub)

    def _forget(self, run: str | None):
        for d in (self.latest, self.last_key, self.last_t):
            d.pop(run, None)

    def mark_stale(self, reason: str):
        if not self.live:
            return
        self.live = False
        self._forget(self.live_run)
        self._broadcast("stale", {"run": self.live_run, "reason": reason, "live": False, "t": time.time()})

    def set_status(self, s: Status):
        if not s.live:
            if s.run is None or s.run == self.live_run:
                self.mark_stale(s.reason or "paused")
            return
        if s.run != self.live_run:
            if self.live:
                self.mark_stale("switched")
            self._forget(self.live_run)
            self.live_run = s.run
        if not self.live:                              # a new live span starts with no history
            self._forget(s.run)
        self.live = True
        self.last_seen = time.monotonic()

    def publish(self, a: Alert) -> bool:
        if not self.live or a.run != self.live_run:
            raise HTTPException(409, "that run is not playing; post /api/alerts/status first")
        if a.t < self.last_t.get(a.run, 0.0):
            raise HTTPException(409, "alert is older than the last one in this live span")
        self.last_seen = time.monotonic()
        self.last_t[a.run] = a.t
        key = (a.state, a.level)
        if self.last_key.get(a.run) == key:
            return False
        self.last_key[a.run] = key
        self.latest[a.run] = a
        self._broadcast("alert", a.model_dump())
        return True

    def expire(self):
        if self.live and self.last_seen is not None and time.monotonic() - self.last_seen > STALE_S:
            self.mark_stale("timeout")

    def current(self) -> Alert | None:
        return self.latest.get(self.live_run) if self.live else None

    def heartbeat(self) -> dict:
        age = None if self.last_seen is None else round(time.monotonic() - self.last_seen, 3)
        return {"t": time.time(), "live": self.live, "run": self.live_run, "age_s": age}


bus = AlertBus()


def check_single_worker():
    if int(os.getenv("WEB_CONCURRENCY", "1") or 1) > 1:
        raise RuntimeError("the alert feed is process-local: run a single worker (unset WEB_CONCURRENCY / --workers 1)")


async def _watchdog():
    while True:
        await asyncio.sleep(WATCH_S)
        bus.expire()


@asynccontextmanager
async def lifespan(_app):
    check_single_worker()
    task = asyncio.create_task(_watchdog())
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


app = FastAPI(title="Periscope", lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    if request.url.path == "/api/alerts" and any(
        e["type"] == "value_error" and e["loc"] == ("body",) and e["msg"] == f"Value error, {ALERT_LEVEL_DETAIL}"
        for e in exc.errors()
    ):
        return JSONResponse(status_code=422, content={"detail": ALERT_LEVEL_DETAIL})
    return await request_validation_exception_handler(request, exc)


@app.get("/api/health")
def health():
    return {"ok": True}


def read_run(run_id: str) -> dict | None:
    """Read persisted metadata; an absent or invalid run is unavailable, never a demo substitute."""
    d = (RUNS / run_id).resolve()
    if d.parent != RUNS.resolve():
        return None
    try:
        r = json.loads((d / "run.json").read_text())
    except (OSError, ValueError):
        return None
    if not isinstance(r, dict) or not isinstance(r.get("scene", {}), dict) or not isinstance(r.get("frames", []), list):
        return None
    if not isinstance(r.get("title", run_id), str):
        return None
    return r


@app.get("/api/runs")
def runs():
    out = []
    for d in sorted(RUNS.iterdir()):
        if (r := read_run(d.name)) is not None:
            out.append({"id": d.name, "title": r.get("title", d.name), "kind": r.get("scene", {}).get("kind", "footage"),
                        "frames": len(r.get("frames", []))})
    return out


@app.get("/api/runs/{run_id}")
def resolve_run(run_id: str):
    """Resolve a selection against disk, including a normal unavailable result if it disappeared."""
    return {"run": read_run(run_id)}


@app.post("/api/analyze")
async def analyze(video: UploadFile = File(...), calib: str = Form(...), title: str = Form("Uploaded clip")):
    try:
        cal = Calibration.from_json(calib)
    except Exception as e:  # noqa: BLE001 - report any malformed calibration to the client
        raise HTTPException(400, f"bad calibration: {e}")
    run_id = "up-" + uuid.uuid4().hex[:8]
    d = RUNS / run_id
    d.mkdir()
    src = d / ("input" + (Path(video.filename or "").suffix or ".mp4"))
    size = 0
    with src.open("wb") as f:
        while chunk := await video.read(1 << 20):
            size += len(chunk)
            if size > MAX_BYTES:
                shutil.rmtree(d, ignore_errors=True)
                raise HTTPException(413, "clip too large (500 MB max)")
            f.write(chunk)
    try:
        frames, fps, wh = read_video(str(src))
        await run_in_threadpool(export_run, frames, cal, fps, wh, d, title=title, scene_info={"kind": "footage"})
    except ValueError as e:
        shutil.rmtree(d, ignore_errors=True)
        raise HTTPException(422, str(e))
    src.unlink(missing_ok=True)
    return {"id": run_id}


# ---------- live alert feed ----------
def require_publisher(request: Request):
    """Only the operator's console may publish. Browsers always send Origin, so a page from another site open
    in the operator's browser is refused here; non-browser clients are covered by the token / loopback check."""
    origin = request.headers.get("origin")
    if origin is not None and origin.rstrip("/") != f"{request.url.scheme}://{request.headers.get('host', '')}":
        raise HTTPException(403, "cross-origin publisher refused")
    token = os.getenv("PERISCOPE_ALERT_TOKEN")
    if token:
        if not hmac.compare_digest(request.headers.get("authorization", "").encode(), f"Bearer {token}".encode()):
            raise HTTPException(401, "alert token required")
        return
    if (request.client.host if request.client else None) not in LOOPBACK:
        raise HTTPException(403, "alerts can only be published from this machine (or set PERISCOPE_ALERT_TOKEN)")


@app.post("/api/alerts/status", dependencies=[Depends(require_publisher)])
async def alert_status(s: Status):
    bus.set_status(s)
    return bus.heartbeat()


@app.post("/api/alerts", dependencies=[Depends(require_publisher)])
async def alert_publish(a: Alert):
    return {"sent": bus.publish(a), "subscribers": len(bus.subscribers)}


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def _events(b: AlertBus, disconnected, sub: Subscriber | None = None):
    sub = sub or b.subscribe()
    try:
        b.expire()
        # HEARTBEAT_S is a maximum gap, not a sleep duration. Reserve 20% for event-loop and network delay.
        heartbeat_interval = HEARTBEAT_S * 0.8
        next_heartbeat = time.monotonic() + heartbeat_interval
        yield _sse("heartbeat", b.heartbeat())
        if (a := b.current()) is not None:
            yield _sse("alert", a.model_dump())
        while True:
            if sub.overflow:
                yield _sse("resync", {"t": time.time(), "reason": "subscriber too slow; reconnect"})
                return
            remaining = next_heartbeat - time.monotonic()
            if remaining <= 0:
                next_heartbeat = time.monotonic() + heartbeat_interval
                yield _sse("heartbeat", b.heartbeat())
                continue
            try:
                event, data = await asyncio.wait_for(sub.q.get(), remaining)
            except asyncio.TimeoutError:
                event, data = "heartbeat", b.heartbeat()
                next_heartbeat = time.monotonic() + heartbeat_interval
            yield _sse(event, data)
            if await disconnected():
                return
    finally:
        b.subscribers.discard(sub)


@app.get("/api/alerts/stream")
async def alert_stream(request: Request):
    return StreamingResponse(_events(bus, request.is_disconnected), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return FileResponse(WEB / "favicon.svg", media_type="image/svg+xml")


app.mount("/", StaticFiles(directory=WEB), name="web")
