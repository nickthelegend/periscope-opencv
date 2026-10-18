"""Run the engine over a clip, score it against ground truth, and export a run for the web UI."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import cv2
import numpy as np

from .engine import Periscope
from .geometry import Calibration


def read_video(path: str):
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise ValueError(f"cannot open video: {path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    def gen():
        while True:
            ok, f = cap.read()
            if not ok:
                break
            yield f
        cap.release()

    return gen(), fps, (w, h)


def run_frames(frames, calib: Calibration, fps: float, frame_size, *, keep_x: bool = True,
               on_frame=None, **engine_kw):
    """Run the engine on an iterator of BGR frames. Returns (engine, list of per-frame records)."""
    eng = Periscope(calib, frame_size, fps, **engine_kw)
    recs = []
    for f in frames:
        r = eng.update(f)
        if on_frame is not None:
            on_frame(eng, r)
        if not keep_x:
            r.pop("x", None)
            r.pop("xn", None)
        recs.append(r)
    return eng, recs


# ---- scoring ------------------------------------------------------------------------------

def score_track(recs, truth_phi, truth_d, fps, *, d_max=None, phi_lo=3.0, phi_hi=87.0, lag_s=0.0, grace_s=1.5):
    """Compare the tracked angle with ground truth.

    truth_phi / truth_d: per-frame hidden angle (deg) and distance (m) of the person, NaN when
    nobody is in the hidden hallway. Returns angle error, detection rate, false alarms and the
    warning lead time before the person reaches the corner. Frames within `grace_s` after the
    person leaves don't count as false alarms (the track takes a moment to let go).
    """
    T = min(len(recs), len(truth_phi))
    phi_t = np.asarray(truth_phi[:T], float)
    d_t = np.asarray(truth_d[:T], float)
    live = np.array([r["state"] != "learning" for r in recs[:T]])
    present = np.array([bool(r["present"]) for r in recs[:T]])
    coming = np.array([bool(r.get("coming")) for r in recs[:T]])
    est = np.array([np.nan if r["phi"] is None else r["phi"] for r in recs[:T]], float)
    if lag_s:
        k = int(round(lag_s * fps))
        est = np.concatenate([est[k:], np.full(k, np.nan)])
    has = np.isfinite(phi_t)
    in_view = has & (phi_t >= phi_lo) & (phi_t <= phi_hi) & live
    if d_max is not None:
        in_view &= d_t <= d_max
    since = np.full(T, np.inf)
    last = -np.inf
    for i in range(T):
        if has[i]:
            last = i
        since[i] = (i - last) / fps
    empty = ~has & live & (since > grace_s)
    hit = in_view & present
    err = np.abs(est - phi_t)[hit & np.isfinite(est)]
    out = {
        "frames": int(T),
        "eval_frames": int(in_view.sum()),
        "recall": float(hit.sum() / max(in_view.sum(), 1)),
        "false_alarm_rate": float((present & empty).sum() / max(empty.sum(), 1)),
        "angle_mae_deg": float(np.mean(err)) if err.size else None,
        "angle_median_deg": float(np.median(err)) if err.size else None,
        "angle_p90_deg": float(np.percentile(err, 90)) if err.size else None,
    }
    # Detection range on the approach: distance at the first sustained detection.
    if has.any():
        first_in = int(np.argmax(has))
        det = np.flatnonzero(present & has & (np.arange(T) >= first_in))
        out["first_detect_distance_m"] = float(d_t[det[0]]) if det.size else None
        # lead time: first "coming" alert before the person reaches the closest point to the corner
        closest = int(np.nanargmin(np.where(has, d_t, np.inf)))
        warn = np.flatnonzero(coming[:closest + 1] & has[:closest + 1])
        out["lead_time_s"] = float((closest - warn[0]) / fps) if warn.size else None
        det_d = d_t[present & has]
        out["max_detect_distance_m"] = float(det_d.max()) if det_d.size else None
    return out


# ---- export for the web UI -----------------------------------------------------------------

class _FFmpegWriter:
    def __init__(self, path, size, fps, crf: int = 18):
        self.p = None
        if shutil.which("ffmpeg") is None:
            self.w = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, size)
            return
        self.p = subprocess.Popen(
            ["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{size[0]}x{size[1]}",
             "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", str(crf), "-pix_fmt", "yuv420p",
             "-movflags", "+faststart", str(path)], stdin=subprocess.PIPE)

    def write(self, frame):
        if self.p is None:
            self.w.write(frame)
        else:
            self.p.stdin.write(np.ascontiguousarray(frame).tobytes())

    def close(self):
        if self.p is None:
            self.w.release()
        else:
            self.p.stdin.close()
            self.p.wait()


def export_run(frames, calib: Calibration, fps: float, frame_size, out_dir, *, truth=None, title="Run",
               scene_info=None, amp_gain=70.0, **engine_kw):
    """Run and write everything the web page needs: run.json, floor.mp4, shadow.mp4, spacetime.png.

    Returns (run dict, per-frame engine records).
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    writers = {}
    amp_buf = []

    def on_frame(eng, r):
        f = eng.aligned
        if not writers:
            h, w = f.shape[:2]
            sz = (w - w % 2, h - h % 2)
            writers["size"] = sz
            writers["floor"] = _FFmpegWriter(out / "floor.mp4", sz, fps)
            writers["shadow"] = _FFmpegWriter(out / "shadow.mp4", sz, fps)
        sz = writers["size"]
        writers["floor"].write(f[:sz[1], :sz[0]])
        # The shadow, made visible: (recent frames - empty hallway), blurred and amplified.
        amp_buf.append(f.astype(np.float32))
        if len(amp_buf) > eng.K:
            amp_buf.pop(0)
        if eng.bg_frame is None:
            a = np.full_like(f, 128)
        else:
            # relative change (a shadow multiplies the light), in grey levels of a 150-level floor,
            # so floor markings with other colours don't light up
            d = (np.mean(amp_buf, axis=0) / np.maximum(eng.bg_frame, 8.0) - 1.0) * 150.0
            d = cv2.GaussianBlur(d, (0, 0), 6)
            d -= d.reshape(-1, 3).mean(0)                       # no global flicker in the view
            a = np.clip(128 + amp_gain * d, 0, 255).astype(np.uint8)
        writers["shadow"].write(a[:sz[1], :sz[0]])

    eng, recs = run_frames(frames, calib, fps, frame_size, on_frame=on_frame, **engine_kw)
    for k in ("floor", "shadow"):
        writers[k].close()

    # Spacetime image: rows = time, columns = hidden angle, colour = recovered light change.
    T, P = len(recs), len(eng.phi)
    st = np.full((T, P, 3), 0.5, np.float32)
    for i, r in enumerate(recs):
        if r["xn"] is not None:
            st[i] = 0.5 + 0.5 * np.tanh(r["xn"][:, ::-1] / 12.0)         # BGR -> RGB, soft-clipped
    st_img = (st * 255).astype(np.uint8)
    cv2.imwrite(str(out / "spacetime.png"), st_img[:, :, ::-1])

    c = eng.calib
    frames_out = []
    for r in recs:
        q = r.get("quality")
        frames_out.append({
            "t": r["t"], "s": r["state"], "phi": r["phi"], "pd": r["phi_dot"], "eta": r["eta_s"],
            "z": r["z_peak"], "pm": r["phi_meas"],
            **({"q": {"a": q["action"], "m": q["metrics"]}} if q else {}),
        })
    run = {
        "title": title,
        "fps": fps,
        "size": list(writers["size"]),
        "phi": [round(float(p), 2) for p in eng.phi],
        "calib": {
            "corner": [round(v, 1) for v in c.corner_px],
            "wedge": [[round(a, 1), round(b, 1)] for a, b in c.wedge_outline(32)],
            "rays": {str(a): [[round(u, 1), round(v, 1)] for u, v in c.ray(a)] for a in (0, 15, 30, 45, 60, 75, 90)},
            "r_min": c.r_min, "r_max": c.r_max, "source": c.source,
        },
        "frames": frames_out,
        "events": eng.events,
        "final_quality": eng.assess(),
        "scene": scene_info or {},
        "assets": {"floor": "floor.mp4", "shadow": "shadow.mp4", "spacetime": "spacetime.png"},
    }
    if truth is not None:
        phi_t, d_t, pos = truth
        run["truth"] = {
            "phi": [None if not np.isfinite(p) else round(float(p), 2) for p in phi_t],
            "d": [None if not np.isfinite(v) else round(float(v), 2) for v in d_t],
            "xy": [None if not np.all(np.isfinite(p)) else [round(float(p[0]), 3), round(float(p[1]), 3)] for p in pos],
        }
        run["score"] = {"near": score_track(recs, phi_t, d_t, fps, d_max=3.0),
                        "far": score_track(recs, phi_t, d_t, fps, d_max=8.0)}
    (out / "run.json").write_text(json.dumps(run, separators=(",", ":")))
    return run, recs
