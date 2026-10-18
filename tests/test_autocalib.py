"""Automatic corner detection: a ray Calibration from one floor frame, or a refusal with a reason.

The noise levels are the ones the SNR tests use: x0.5..x3 is a lit room, x4 the signal floor,
x12 is well below it (per-pixel SNR ~0.017). The corner must still be found to 6 px there; the
wedge it gives is useless for tracking at that SNR, but calibration should not be what breaks.
"""

import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

from periscope.geometry import Calibration, detect_corner
from periscope.render import Scene, empty_hallway

ROOT = Path(__file__).resolve().parents[1]


def floor_frame(scene: Scene):
    return next(scene.render(empty_hallway(scene.fps, 0.1)))


def angle_deg(u, v):
    return np.degrees(np.arccos(np.clip(u @ v / np.linalg.norm(u) / np.linalg.norm(v), -1, 1)))


@pytest.mark.parametrize("noise", [0.5, 1.0, 3.0, 4.0, 8.0, 12.0])
@pytest.mark.parametrize("seed", [0, 1, 2])
def test_corner_within_6px_across_snr(scene, noise, seed):
    s = scene.with_(noise_scale=noise, seed=seed)
    det = detect_corner(floor_frame(s))
    assert det.ok, det.reason
    cal = det.calibration
    marks = s.marks_px()
    assert np.hypot(*(np.asarray(cal.corner_px) - marks[0])) <= 6.0, f"snr {s.snr(3.0):.3f}"
    c = np.asarray(cal.corner_px)
    # wedge edge at theta = 0 runs along the wall base
    assert angle_deg(np.asarray(cal.wall_px) - c, marks[2] - marks[0]) < 8.0
    # the 90-degree edge is on the floor side of the wall base
    assert (np.asarray(cal.open_px) - c) @ (marks[4] - marks[0]) > 0


def test_detection_is_a_usable_calibration(scene):
    det = detect_corner(floor_frame(scene))
    cal = det.calibration
    assert isinstance(cal, Calibration) and cal.source == "auto" and cal.H is None
    assert cal.image_size == (scene.width, scene.height)
    assert 0 < cal.r_min < cal.r_max
    assert det.confidence >= 0.5 and any("auto" in n for n in cal.notes)
    # the wall mark sits on the theta = 0 edge, the floor marks inside the wedge
    ab = cal.to_floor(scene.marks_px())
    theta = np.degrees(np.arctan2(ab[:, 1], ab[:, 0]))
    assert abs(theta[2]) < 5.0
    assert np.all((theta[3:5] > 0) & (theta[3:5] < 120))
    again = Calibration.from_json(cal.to_json())
    assert np.allclose(again.to_floor(scene.marks_px()), ab)


def _clutter(seed=0):
    rng = np.random.default_rng(seed)
    im = np.clip(128 + rng.normal(0, 30, (360, 480, 3)), 0, 255).astype(np.uint8)
    for _ in range(40):
        x0, x1 = rng.integers(0, 480, 2)
        y0, y1 = rng.integers(0, 360, 2)
        cv2.line(im, (int(x0), int(y0)), (int(x1), int(y1)), tuple(int(v) for v in rng.integers(0, 255, 3)), 2)
    return im


def _one_edge():
    im = np.full((360, 480, 3), 100, np.uint8)
    im[:, 240:] = 170
    return im


@pytest.mark.parametrize("make", [
    lambda: np.full((360, 480, 3), 128, np.uint8),
    lambda: np.clip(128 + np.random.default_rng(0).normal(0, 30, (360, 480, 3)), 0, 255).astype(np.uint8),
    _one_edge,
    _clutter,
], ids=["flat", "noise", "one-edge", "clutter"])
def test_no_corner_falls_back_with_a_reason(make):
    det = detect_corner(make())
    assert not det.ok and det.calibration is None
    assert det.confidence < 0.5
    assert det.reason


def test_confidence_threshold_is_honoured(scene):
    det = detect_corner(floor_frame(scene), min_confidence=1.01)
    assert not det.ok
    assert det.reason.startswith("low confidence")
    assert det.suggestion["corner_px"] is not None          # the guess is kept for an overlay


def _write_clip(path, frame, n=12, fps=15.0):
    h, w = frame.shape[:2]
    vw = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    for _ in range(n):
        vw.write(frame)
    vw.release()


def test_cli_auto_writes_calibration_or_refuses(scene, tmp_path):
    good = tmp_path / "corner.mp4"
    _write_clip(good, floor_frame(scene))
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "calibrate.py"), str(good), "--auto",
                        "--out", str(tmp_path / "good")], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    cal = Calibration.from_json((tmp_path / "good" / "calib.json").read_text())
    assert cal.source == "auto"
    assert np.hypot(*(np.asarray(cal.corner_px) - scene.marks_px()[0])) <= 6.0

    # --r-min/--r-max reach the auto wedge (as fractions of the short side)
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "calibrate.py"), str(good), "--auto",
                        "--r-min", "0.1", "--r-max", "0.3", "--out", str(tmp_path / "radii")],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    cal2 = Calibration.from_json((tmp_path / "radii" / "calib.json").read_text())
    short = min(scene.width, scene.height)
    assert cal2.r_min == pytest.approx(0.1 * short) and cal2.r_max == pytest.approx(0.3 * short)

    bad = tmp_path / "flat.mp4"
    _write_clip(bad, np.full((360, 480, 3), 128, np.uint8))
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "calibrate.py"), str(bad), "--auto",
                        "--out", str(tmp_path / "bad")], capture_output=True, text=True)
    assert r.returncode != 0
    assert "refused" in r.stderr and "--marks" in r.stderr
    assert not (tmp_path / "bad" / "calib.json").exists()
