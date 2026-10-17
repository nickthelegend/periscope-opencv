"""Per-frame cost of the Periscope engine, split into its stages (for the Graviton/COOL comparison).

    python tools/bench.py            # prints ms/frame for 640x360 work frames from a 1080p source
"""

from __future__ import annotations

import json
import platform
import sys
import time
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from periscope.engine import Periscope  # noqa: E402
from periscope.render import Scene, approach_and_leave  # noqa: E402


def main():
    s = Scene(width=640, height=360, fps=30.0)
    frames = list(s.render(approach_and_leave(30.0)[:240]))
    big = [cv2.resize(f, (1920, 1080), interpolation=cv2.INTER_LINEAR) for f in frames[:60]]
    out = {"machine": platform.machine(), "python": platform.python_version(), "opencv": cv2.__version__,
           "threads": cv2.getNumThreads()}

    def run(src, size, stabilize):
        cal = s.calibration().scaled(size[0] / s.width)
        eng = Periscope(cal, size, s.fps, stabilize=stabilize)
        for f in src[:70]:            # warm up + learn
            eng.update(f)
        t0 = time.perf_counter()
        n = 0
        for f in src[70:] if len(src) > 70 else src:
            eng.update(f)
            n += 1
        return (time.perf_counter() - t0) / n * 1000

    out["ms_640x360_stabilised"] = round(run(frames, (640, 360), True), 2)
    out["ms_640x360_no_stab"] = round(run(frames, (640, 360), False), 2)
    big = big + big + big
    out["ms_1080p_in_stabilised"] = round(run(big, (1920, 1080), True), 2)
    # stage costs
    g = cv2.cvtColor(frames[0], cv2.COLOR_BGR2GRAY).astype(np.float32)
    win = cv2.createHanningWindow(g.shape[::-1], cv2.CV_32F)
    t0 = time.perf_counter()
    for _ in range(100):
        cv2.phaseCorrelate(g.copy(), g.copy(), win)
    out["ms_phase_correlate_640x360"] = round((time.perf_counter() - t0) * 10, 2)
    eng = Periscope(s.calibration(), (640, 360), s.fps)
    t0 = time.perf_counter()
    for _ in range(100):
        eng.recon.binner(frames[0])
    out["ms_binning_640x360"] = round((time.perf_counter() - t0) * 10, 2)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
