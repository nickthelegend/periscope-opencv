"""Periscope web server: the console page, recorded runs, and analysis of an uploaded corner clip.

    uvicorn server:app --port 8040        # then open http://localhost:8040
"""

from __future__ import annotations

import json
import os
import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from periscope.geometry import Calibration
from periscope.pipeline import export_run, read_video

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
RUNS = Path(os.getenv("PERISCOPE_RUNS", WEB / "runs"))
RUNS.mkdir(parents=True, exist_ok=True)
MAX_BYTES = 500 * 1024 * 1024

app = FastAPI(title="Periscope")


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/runs")
def runs():
    out = []
    for d in sorted(RUNS.iterdir()):
        f = d / "run.json"
        if f.exists():
            r = json.loads(f.read_text())
            out.append({"id": d.name, "title": r.get("title", d.name), "kind": r.get("scene", {}).get("kind", "footage"),
                        "frames": len(r.get("frames", []))})
    return out


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


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")


app.mount("/", StaticFiles(directory=WEB), name="web")
