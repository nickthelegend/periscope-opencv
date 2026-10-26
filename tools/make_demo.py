"""Render the synthetic corner, run Periscope on it and write the run the web page plays.

    python tools/make_demo.py            # -> web/runs/demo/{run.json, floor.mp4, shadow.mp4, spacetime.png, hidden.mp4}
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from periscope.pipeline import _FFmpegWriter, export_run  # noqa: E402
from periscope.render import GroundTruthCamera, Scene, approach_and_leave, truth_angles  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "web" / "runs" / "demo"))
    ap.add_argument("--fps", type=float, default=20.0)
    ap.add_argument("--noise", type=float, default=1.0, help="noise multiplier (1 = phone in a lit room)")
    ap.add_argument("--title", default="Synthetic corner · red top · lit hallway", help="name shown in the console's run picker")
    a = ap.parse_args()

    pos = approach_and_leave(a.fps, empty_s=3.0, tail_s=4.0)
    tail_start = len(pos) / a.fps - 4.0
    # Someone switches a lamp on 1.2 s after the hallway empties: the agent should re-learn.
    scene = Scene(fps=a.fps, noise_scale=a.noise, exposure_step=0.04, exposure_at_s=tail_start + 1.2,
                  width=640, height=480, focal_px=480.0, floor_texture=0.05, camera_look=True)
    phi, d = truth_angles(pos)
    info = {
        "kind": "synthetic",
        "snr3": round(scene.snr(3.0), 3),
        "noise_dn": round(scene.pixel_noise(), 2),
        "signal3_dn": round(scene.reference_signal(3.0), 3),
        "hall_width": scene.hall_width,
        "shirt": scene.shirt_rgb,
        "lamp_on_s": round(tail_start + 1.2, 2),
        "description": "Rendered L-shaped hallway. A person in a red top walks toward the corner in the hidden "
                       "hallway, pauses 1.4 m from the corner (still out of the camera's sight), walks away; then a lamp switches on.",
    }
    run, _ = export_run(scene.render(pos), scene.calibration(), a.fps, (scene.width, scene.height), a.out,
                        truth=(phi, d, pos), title=a.title, scene_info=info)
    gt = GroundTruthCamera()
    w = _FFmpegWriter(Path(a.out) / "hidden.mp4", (gt.width, gt.height), a.fps)
    for f in gt.render(pos):
        w.write(f)
    w.close()
    run["assets"]["hidden"] = "hidden.mp4"
    # VP9 copies for browsers built without H.264
    for name in ("floor", "shadow", "hidden"):
        src = Path(a.out) / f"{name}.mp4"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(src), "-c:v", "libvpx-vp9", "-crf", "32",
                        "-b:v", "0", "-row-mt", "1", str(src.with_suffix(".webm"))], check=True)
    (Path(a.out) / "run.json").write_text(json.dumps(run, separators=(",", ":")))
    print(json.dumps(run["score"], indent=1))
    print("events:", run["events"])


if __name__ == "__main__":
    main()
