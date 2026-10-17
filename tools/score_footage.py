"""Score Periscope on real footage against a second camera that films the hidden hallway.

    python tools/score_footage.py \
        --corner data/raw/take1_corner.mp4 --calib data/raw/take1_corner/calib.json \
        --gt data/raw/take1_hidden.mp4 \
        --gt-marks "x,y x,y x,y x,y" --gt-floor "-1,0.4 -1,1.6 -5,0.4 -5,1.6" \
        --out results/take1

Synchronisation: a hand clap in view of both phones at the start (found in the audio), or pass
--offset SECONDS (added to the ground-truth camera's clock).

Writes score.json (angle error, detection rate, false alarms, warning lead time), track.png
(estimated vs true angle over time) and a run folder the web page can open.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from periscope.geometry import Calibration  # noqa: E402
from periscope.groundtruth import clap_offset, floor_homography, to_angles, track_feet  # noqa: E402
from periscope.pipeline import export_run, read_video, score_track  # noqa: E402


def parse_pts(s: str):
    return [tuple(map(float, p.split(","))) for p in s.split()]


def resample(t_src, v_src, t_dst):
    """Linear interpolation that keeps NaN gaps (nobody in view) as NaN."""
    ok = np.isfinite(v_src)
    out = np.interp(t_dst, t_src, np.where(ok, v_src, 0.0))
    near = np.interp(t_dst, t_src, ok.astype(float))
    out[near < 0.999] = np.nan
    return out


def plot_track(recs, phi_true, fps, path):
    W, H, m = 900, 320, 48
    img = np.full((H, W, 3), 255, np.uint8)
    T = len(recs)
    X = lambda i: int(m + i / max(T - 1, 1) * (W - 2 * m))
    Y = lambda p: int(H - m - p / 90.0 * (H - 2 * m))
    for p in (0, 30, 60, 90):
        cv2.line(img, (m, Y(p)), (W - m, Y(p)), (232, 232, 232), 1)
        cv2.putText(img, f"{p}", (10, Y(p) + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (90, 90, 90), 1, cv2.LINE_AA)
    for i in range(1, T):
        a, b = phi_true[i - 1], phi_true[i]
        if np.isfinite(a) and np.isfinite(b):
            cv2.line(img, (X(i - 1), Y(np.clip(a, 0, 90))), (X(i), Y(np.clip(b, 0, 90))), (60, 60, 60), 2, cv2.LINE_AA)
        r0, r1 = recs[i - 1], recs[i]
        if r0["phi"] is not None and r1["phi"] is not None:
            col = (40, 60, 230) if r1["coming"] else (230, 120, 40)
            cv2.line(img, (X(i - 1), Y(r0["phi"])), (X(i), Y(r1["phi"])), col, 2, cv2.LINE_AA)
    cv2.putText(img, "hidden angle (deg): ground truth (grey) vs Periscope (blue; red = 'someone is coming')",
                (m, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (60, 60, 60), 1, cv2.LINE_AA)
    cv2.imwrite(str(path), img)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corner", required=True)
    ap.add_argument("--calib", required=True)
    ap.add_argument("--gt", required=True)
    ap.add_argument("--gt-marks", required=True, help="pixel positions of the hidden-hallway tape marks")
    ap.add_argument("--gt-floor", default="-1,0.4 -1,1.6 -5,0.4 -5,1.6", help="the same marks in floor metres")
    ap.add_argument("--offset", type=float, default=None, help="seconds added to the ground-truth clock")
    ap.add_argument("--out", default="results/take")
    ap.add_argument("--d-max", type=float, default=6.0)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    cal = Calibration.from_json(Path(a.calib).read_text())
    H = floor_homography(parse_pts(a.gt_marks), parse_pts(a.gt_floor))
    gt_frames, gt_fps, _ = read_video(a.gt)
    xy = track_feet(gt_frames, H)
    phi_gt, d_gt = to_angles(xy)
    offset = a.offset if a.offset is not None else clap_offset(a.corner, a.gt)
    if offset is None:
        print("no audio clap found; assuming the clips start together (pass --offset to fix)")
        offset = 0.0
    frames, fps, size = read_video(a.corner)
    run, recs = export_run(frames, cal, fps, size, out / "run", title=Path(a.corner).stem)
    T = len(run["frames"])
    t_corner = np.arange(T) / fps
    t_gt = np.arange(len(phi_gt)) / gt_fps + offset
    phi_t = resample(t_gt, phi_gt, t_corner)
    d_t = resample(t_gt, d_gt, t_corner)
    x_t, y_t = resample(t_gt, xy[:, 0], t_corner), resample(t_gt, xy[:, 1], t_corner)

    sc = score_track(recs, phi_t, d_t, fps, d_max=a.d_max)
    sc.update(offset_s=offset, gt_fps=gt_fps, fps=fps)
    (out / "score.json").write_text(json.dumps(sc, indent=1))
    plot_track(recs, phi_t, fps, out / "track.png")
    # add the truth to the run so the web page shows both tracks
    run["truth"] = {"phi": [None if not np.isfinite(p) else round(float(p), 2) for p in phi_t],
                    "d": [None if not np.isfinite(v) else round(float(v), 2) for v in d_t],
                    "xy": [None if not (np.isfinite(x) and np.isfinite(y)) else [round(float(x), 3), round(float(y), 3)]
                           for x, y in zip(x_t, y_t)]}
    run["score"] = sc
    (out / "run" / "run.json").write_text(json.dumps(run, separators=(",", ":")))
    print(json.dumps(sc, indent=1))


if __name__ == "__main__":
    main()
