"""Ground truth from a second camera that films the hidden hallway directly.

Four or more tape marks on the hidden hallway's floor, measured from the corner, give a
homography from that camera's image to the floor. The person is found by background
subtraction; the bottom of their silhouette is where their feet touch the floor. That floor
point gives the true hidden angle and distance for every frame.

The two cameras are synchronised with a hand clap at the start (audio), or a manual offset.
"""

from __future__ import annotations

import shutil
import subprocess

import cv2
import numpy as np


def floor_homography(marks_px, marks_floor_m) -> np.ndarray:
    H, _ = cv2.findHomography(np.asarray(marks_px, np.float64), np.asarray(marks_floor_m, np.float64), 0)
    if H is None:
        raise ValueError("ground-truth marks are degenerate")
    return H


def track_feet(frames, H: np.ndarray, learn: int = 20, min_area: int = 400, diff_thresh: float = 18.0):
    """Floor position (x, y) metres of the person per frame, NaN when nobody is in view.

    Background = median of the first `learn` frames (the hallway must be empty then).
    """
    frames = iter(frames)
    first = []
    for f in frames:
        first.append(f)
        if len(first) >= learn:
            break
    bg = np.median(np.stack(first), axis=0).astype(np.float32)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    out = [(np.nan, np.nan)] * len(first)
    for f in frames:
        d = np.abs(f.astype(np.float32) - bg).max(axis=2)
        m = (d > diff_thresh).astype(np.uint8)
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, kernel)
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, kernel, iterations=2)
        n, lab, stats, _ = cv2.connectedComponentsWithStats(m)
        if n <= 1 or stats[1:, cv2.CC_STAT_AREA].max() < min_area:
            out.append((np.nan, np.nan))
            continue
        k = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        ys, xs = np.nonzero(lab == k)
        y_foot = ys.max()
        # feet: the bottom 5% of the silhouette, centred horizontally
        sel = ys >= y_foot - max(2, int(0.05 * (ys.max() - ys.min())))
        p = np.array([[[xs[sel].mean(), float(y_foot)]]])
        fx, fy = cv2.perspectiveTransform(p, H)[0, 0]
        out.append((float(fx), float(fy)))
    return np.array(out, dtype=np.float64)


def to_angles(xy: np.ndarray):
    phi = np.degrees(np.arctan2(xy[:, 1], xy[:, 0])) - 90.0
    return phi, np.hypot(xy[:, 0], xy[:, 1])


def audio_envelope(path: str, rate: int = 4000) -> np.ndarray | None:
    if shutil.which("ffmpeg") is None:
        return None
    p = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(path), "-ac", "1", "-ar", str(rate), "-f", "s16le", "-"],
                       capture_output=True)
    if p.returncode != 0 or not p.stdout:
        return None
    a = np.frombuffer(p.stdout, np.int16).astype(np.float32)
    return np.abs(a)


def clap_offset(path_a: str, path_b: str, rate: int = 4000, search_s: float = 15.0) -> float | None:
    """Seconds to add to b's timeline to line it up with a, from the loudest clap near the start."""
    ea, eb = audio_envelope(path_a, rate), audio_envelope(path_b, rate)
    if ea is None or eb is None:
        return None
    n = int(search_s * rate)
    ta = np.argmax(ea[:n]) / rate
    tb = np.argmax(eb[:n]) / rate
    return float(ta - tb)
