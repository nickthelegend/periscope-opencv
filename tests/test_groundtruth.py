import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from periscope.groundtruth import floor_homography, to_angles, track_feet
from periscope.pipeline import _FFmpegWriter
from periscope.render import GT_MARKS_M, GroundTruthCamera, approach_and_leave, truth_angles

ROOT = Path(__file__).resolve().parents[1]


def test_second_camera_recovers_true_angle():
    gt = GroundTruthCamera()
    pos = approach_and_leave(15.0)
    H = floor_homography(gt.marks_px(), GT_MARKS_M)
    xy = track_feet(gt.render(pos), H)
    phi_est, d_est = to_angles(xy)
    phi, d = truth_angles(pos)
    ok = np.isfinite(phi) & np.isfinite(phi_est) & (d < 7.5)
    assert ok.sum() > 100
    # feet are at the near edge of the body, so allow the body radius
    assert np.median(np.abs(d_est[ok] - d[ok])) < 0.3
    assert np.median(np.abs(phi_est[ok] - phi[ok])) < 3.0
    assert np.isnan(phi_est[~np.isfinite(phi)][5:]).mean() > 0.9   # empty hallway reads as empty


@pytest.mark.slow
def test_score_footage_end_to_end(tmp_path, scene):
    """Write both 'phone' clips (near-lossless H.264), then score one against the other."""
    pos = approach_and_leave(scene.fps)
    w = _FFmpegWriter(tmp_path / "corner.mp4", (scene.width, scene.height), scene.fps, crf=4)   # near-lossless, like ProRes
    for f in scene.render(pos):
        w.write(f)
    w.close()
    gt = GroundTruthCamera()
    w = _FFmpegWriter(tmp_path / "hidden.mp4", (gt.width, gt.height), scene.fps)
    for f in gt.render(pos):
        w.write(f)
    w.close()
    (tmp_path / "calib.json").write_text(scene.calibration().to_json())
    marks = " ".join(f"{x:.2f},{y:.2f}" for x, y in gt.marks_px())
    out = tmp_path / "score"
    subprocess.run([sys.executable, str(ROOT / "tools" / "score_footage.py"), "--corner", str(tmp_path / "corner.mp4"),
                    "--calib", str(tmp_path / "calib.json"), "--gt", str(tmp_path / "hidden.mp4"),
                    "--gt-marks", marks, "--offset", "0", "--out", str(out), "--d-max", "3"], check=True,
                   capture_output=True)
    sc = json.loads((out / "score.json").read_text())
    assert sc["recall"] >= 0.8
    assert sc["angle_mae_deg"] < 8.0
    assert (out / "track.png").exists() and (out / "run" / "run.json").exists()
