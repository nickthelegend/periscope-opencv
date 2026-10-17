"""Find the signal floor: sweep per-pixel SNR (and real-world nuisances) on the synthetic corner.

    python tools/snr_sweep.py            # writes results/sweep.json, results/sweep.md, results/sweep.png

SNR is indexed the way a camera sees it: the per-pixel change (DN) a strongly coloured person
3 m from the corner makes on the floor, divided by the per-pixel noise (DN). CornerCam's paper
calls this signal "less than 0.1% of the pixel intensity".
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from periscope.pipeline import run_frames, score_track  # noqa: E402
from periscope.render import Scene, approach_and_leave, empty_hallway, truth_angles  # noqa: E402


def h264(frames, crf: int, fps: float):
    """Round-trip frames through libx264 like a phone would (yuv420p), return decoded frames."""
    frames = list(frames)
    h, w = frames[0].shape[:2]
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "c.mp4"
        proc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24",
                                 "-s", f"{w}x{h}", "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "medium",
                                 "-crf", str(crf), "-pix_fmt", "yuv420p", str(p)], stdin=subprocess.PIPE)
        for f in frames:
            proc.stdin.write(f.tobytes())
        proc.stdin.close()
        proc.wait()
        cap = cv2.VideoCapture(str(p))
        out = []
        while True:
            ok, f = cap.read()
            if not ok:
                break
            out.append(f)
        kbps = p.stat().st_size * 8 / 1000 / (len(frames) / fps)
    return out, kbps


def one(scene: Scene, seed: int = 0, codec: int | None = None) -> dict:
    s = scene.with_(seed=seed)
    cal = s.calibration()
    pos = approach_and_leave(s.fps)
    phi, d = truth_angles(pos)
    frames = s.render(pos)
    empty = s.with_(seed=seed + 100).render(empty_hallway(s.fps, 14))
    extra = {}
    if codec is not None:
        frames, kbps = h264(frames, codec, s.fps)
        empty, _ = h264(empty, codec, s.fps)
        # scale the bitrate to 1080p30 so it can be compared with a phone's recording settings
        extra["kbps_1080p30_equiv"] = round(kbps * (1920 * 1080) / (s.width * s.height) * 30 / s.fps)
    _, recs = run_frames(frames, cal, s.fps, (s.width, s.height), keep_x=False)
    near = score_track(recs, phi, d, s.fps, d_max=3.0)
    allr = score_track(recs, phi, d, s.fps, d_max=8.0)
    _, er = run_frames(empty, cal, s.fps, (s.width, s.height), keep_x=False)
    live = [r for r in er if r["state"] != "learning"]
    fa = float(np.mean([r["present"] for r in live]))
    return {
        "snr3": s.snr(3.0), "noise_dn": s.pixel_noise(), "signal3_dn": s.reference_signal(3.0),
        "recall_3m": near["recall"], "mae_3m": near["angle_mae_deg"], "median_3m": near["angle_median_deg"],
        "first_detect_m": allr["first_detect_distance_m"], "lead_s": allr["lead_time_s"],
        "fa_empty": fa, "fa_approach": allr["false_alarm_rate"], **extra,
    }


def mean_runs(rs):
    out = {}
    for k in rs[0]:
        vals = [r[k] for r in rs if r[k] is not None]
        out[k] = float(np.mean(vals)) if vals else None
    return out


def passes(r, mae_max=6.0, recall_min=0.9):
    return (r["recall_3m"] or 0) >= recall_min and (r["mae_3m"] or 99) <= mae_max and r["fa_empty"] == 0 and (r["fa_approach"] or 0) < 0.02


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=2)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--out", default=str(ROOT / "results"))
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    seeds = range(a.seeds)
    base = Scene()

    levels = [0.5, 1, 1.5, 2, 3, 4, 6, 8, 12] if not a.quick else [1, 3, 8]
    sweep = []
    for ns in levels:
        r = mean_runs([one(base.with_(noise_scale=ns), s) for s in seeds])
        r["noise_scale"] = ns
        r["pass"] = passes(r)
        sweep.append(r)
        print(f"noise x{ns:<4} SNR3={r['snr3']:.3f}  recall3m={r['recall_3m']:.2f}  mae3m={r['mae_3m']}  "
              f"first={r['first_detect_m']}  lead={r['lead_s']}  FA={r['fa_empty']:.3f}  pass={r['pass']}", flush=True)
    passing = [r["snr3"] for r in sweep if r["pass"]]
    floor = min(passing) if passing else None

    variants = {
        "red top (baseline)": {},
        "navy top": dict(shirt_rgb=(0.08, 0.10, 0.35)),
        "mid-grey top": dict(shirt_rgb=(0.45, 0.45, 0.45)),
        "white top": dict(shirt_rgb=(0.90, 0.90, 0.88)),
        "hidden hallway half as bright": dict(hidden_light=0.5),
        "shake 1 px RMS": dict(shake_px=1.0),
        "lamp flicker 2%": dict(flicker=0.02),
        "exposure jump +5%": dict(exposure_step=0.05),
        "JPEG q90 per frame": dict(jpeg_quality=90),
        "JPEG q75 per frame": dict(jpeg_quality=75),
    }
    if a.quick:
        variants = {k: variants[k] for k in list(variants)[:3]}
    var_rows = []
    for name, kw in variants.items():
        r = mean_runs([one(base.with_(**kw), s) for s in seeds])
        r["name"] = name
        r["pass"] = passes(r)
        var_rows.append(r)
        print(f"{name:32s} SNR3={r['snr3']:.3f} recall3m={r['recall_3m']:.2f} mae3m={r['mae_3m']} first={r['first_detect_m']} "
              f"FA={r['fa_empty']:.3f} pass={r['pass']}", flush=True)
    for crf in ([12, 18, 23] if not a.quick else []):
        r = mean_runs([one(base, s, codec=crf) for s in seeds])
        r["name"] = f"H.264 CRF {crf}"
        r["pass"] = passes(r)
        var_rows.append(r)
        print(f"{r['name']:32s} ~{r['kbps_1080p30_equiv']:.0f} kbps@1080p30 recall3m={r['recall_3m']:.2f} "
              f"mae3m={r['mae_3m']} FA={r['fa_empty']:.3f} pass={r['pass']}", flush=True)

    res = {"snr_floor_3m": floor, "sweep": sweep, "variants": var_rows, "seeds": a.seeds,
           "criteria": "recall >= 0.9 and angle MAE <= 6 deg within 3 m of the corner, zero false alarms on 14 s of empty hallway"}
    (out / "sweep.json").write_text(json.dumps(res, indent=1))
    write_md(res, out / "sweep.md")
    plot(res, out / "sweep.png")
    print("signal floor (per-pixel SNR at 3 m):", floor)


def fmt(v, nd=2):
    return "–" if v is None else f"{v:.{nd}f}"


def write_md(res, path):
    L = ["| noise × | per-pixel SNR @3 m | recall ≤3 m | angle MAE ≤3 m (°) | first detection (m) | warning lead (s) | false alarms | pass |",
         "|---|---|---|---|---|---|---|---|"]
    for r in res["sweep"]:
        L.append(f"| {r['noise_scale']} | {r['snr3']:.3f} | {fmt(r['recall_3m'])} | {fmt(r['mae_3m'], 1)} | {fmt(r['first_detect_m'], 1)} | "
                 f"{fmt(r['lead_s'], 1)} | {fmt(r['fa_empty'], 3)} | {'yes' if r['pass'] else 'no'} |")
    L += ["", "| condition | per-pixel SNR @3 m | recall ≤3 m | angle MAE ≤3 m (°) | first detection (m) | false alarms | pass |",
          "|---|---|---|---|---|---|---|"]
    for r in res["variants"]:
        name = r["name"] + (f" (≈{r['kbps_1080p30_equiv'] / 1000:.0f} Mbps at 1080p30)" if r.get("kbps_1080p30_equiv") else "")
        L.append(f"| {name} | {r['snr3']:.3f} | {fmt(r['recall_3m'])} | {fmt(r['mae_3m'], 1)} | {fmt(r['first_detect_m'], 1)} | "
                 f"{fmt(r['fa_empty'], 3)} | {'yes' if r['pass'] else 'no'} |")
    Path(path).write_text("\n".join(L) + "\n")


def plot(res, path):
    """Small dependency-free chart (OpenCV drawing): first-detection distance vs SNR."""
    W, H, m = 720, 360, 56
    img = np.full((H, W, 3), 255, np.uint8)
    xs = [r["snr3"] for r in res["sweep"]]
    lx = np.log10(xs)
    x0, x1 = lx.min() - 0.05, lx.max() + 0.05
    X = lambda v: int(m + (np.log10(v) - x0) / (x1 - x0) * (W - 2 * m))
    Y = lambda v: int(H - m - v / 6.0 * (H - 2 * m))
    grid, ink, acc = (232, 232, 232), (60, 60, 60), (40, 110, 230)
    for d in range(0, 7):
        cv2.line(img, (m, Y(d)), (W - m, Y(d)), grid, 1)
        cv2.putText(img, f"{d} m", (8, Y(d) + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, ink, 1, cv2.LINE_AA)
    for v in (0.02, 0.05, 0.1, 0.2, 0.5):
        if x0 <= np.log10(v) <= x1:
            cv2.line(img, (X(v), m), (X(v), H - m), grid, 1)
            cv2.putText(img, f"{v}", (X(v) - 12, H - m + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.4, ink, 1, cv2.LINE_AA)
    pts = [(X(r["snr3"]), Y(r["first_detect_m"] or 0)) for r in res["sweep"]]
    cv2.polylines(img, [np.array(pts, np.int32)], False, acc, 2, cv2.LINE_AA)
    for p, r in zip(pts, res["sweep"]):
        cv2.circle(img, p, 4, acc if r["pass"] else (180, 180, 180), -1, cv2.LINE_AA)
    if res["snr_floor_3m"]:
        fx = X(res["snr_floor_3m"])
        cv2.line(img, (fx, m), (fx, H - m), (60, 60, 200), 1, cv2.LINE_AA)
        cv2.putText(img, "signal floor", (fx + 4, m + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (60, 60, 200), 1, cv2.LINE_AA)
    cv2.putText(img, "first detection distance vs per-pixel SNR (person 3 m from corner)", (m, 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, ink, 1, cv2.LINE_AA)
    cv2.imwrite(str(path), img)


if __name__ == "__main__":
    main()
