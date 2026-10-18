"""Make calib.json for a corner clip from the five tape marks, and a preview to check it.

    # 1. grab the first frame, find the marks' pixel positions (web/calibrate.html helps)
    python tools/calibrate.py corner.mp4 --frame-only
    # 2. write the calibration from the clicked marks, in protocol order
    python tools/calibrate.py corner.mp4 --marks "812,402 701,520 560,680 1010,455 1240,520"

Mark order (see FILMING.md): corner, wall 50 cm, wall 100 cm, 90-degree line 50 cm,
90-degree line 100 cm, and optionally the diagonal mark at (1 m, 1 m).
Without marks, --auto detects the corner and wall ray from the image (approximate angles); it
refuses with a reason below --min-confidence, and then you need the marks.
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

from periscope.geometry import MIN_AUTO_CONFIDENCE, Calibration, detect_corner  # noqa: E402


def first_frame(path: str, skip_s: float = 0.5):
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(skip_s * fps))
    ok, f = cap.read()
    cap.release()
    if not ok:
        raise SystemExit(f"cannot read {path}")
    return f


def preview(frame, cal: Calibration, marks=None):
    img = frame.copy()
    poly = np.array(cal.wedge_outline(48), np.int32)
    over = img.copy()
    cv2.fillPoly(over, [poly], (0, 200, 255))
    img = cv2.addWeighted(over, 0.25, img, 0.75, 0)
    cv2.polylines(img, [poly], True, (0, 200, 255), 2, cv2.LINE_AA)
    for a in (0, 30, 60, 90):
        p = np.array(cal.ray(a, 0, cal.r_max), np.int32)
        cv2.line(img, tuple(p[0]), tuple(p[1]), (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(img, f"{a}", tuple(p[1] + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
    if marks is not None:
        for i, m in enumerate(marks):
            cv2.circle(img, (int(m[0]), int(m[1])), 6, (0, 0, 255), 2, cv2.LINE_AA)
            cv2.putText(img, str(i + 1), (int(m[0]) + 8, int(m[1]) - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--marks", help='"x,y x,y ..." in protocol order (5 or 6 marks)')
    ap.add_argument("--auto", action="store_true", help="suggest a corner and wall ray from the image")
    ap.add_argument("--min-confidence", type=float, default=MIN_AUTO_CONFIDENCE,
                    help="with --auto: refuse (and ask for --marks) below this detection confidence")
    ap.add_argument("--frame-only", action="store_true", help="just write first_frame.png")
    ap.add_argument("--r-min", type=float, default=None,
                    help="wedge inner radius: metres with --marks (default 0.12); with --auto there is no "
                         "metric floor, so a fraction of the frame's short side (default 0.054)")
    ap.add_argument("--r-max", type=float, default=None,
                    help="wedge outer radius: metres with --marks (default 1.0); fraction of the short side "
                         "with --auto (default 0.45)")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    out = Path(a.out or Path(a.video).with_suffix("")).resolve()
    out.mkdir(parents=True, exist_ok=True)
    f = first_frame(a.video)
    cv2.imwrite(str(out / "first_frame.png"), f)
    if a.frame_only:
        print("wrote", out / "first_frame.png")
        return
    h, w = f.shape[:2]
    if a.marks:
        marks = [tuple(map(float, p.split(","))) for p in a.marks.split()]
        cal = Calibration.from_marks(marks, (w, h), 0.12 if a.r_min is None else a.r_min,
                                     1.0 if a.r_max is None else a.r_max)
    elif a.auto:
        radii = {k: v for k, v in (("r_min_frac", a.r_min), ("r_max_frac", a.r_max)) if v is not None}
        if any(v > 1 for v in radii.values()):
            raise SystemExit("with --auto, --r-min/--r-max are fractions of the frame's short side (0-1)")
        det = detect_corner(f, min_confidence=a.min_confidence, **radii)
        if not det.ok:
            raise SystemExit(f"auto calibration refused ({det.reason}); click the tape marks and use --marks")
        marks = None
        cal = det.calibration
        print(json.dumps({"auto_confidence": round(det.confidence, 3), "corner_px": list(cal.corner_px)}))
    else:
        raise SystemExit("give --marks or --auto")
    (out / "calib.json").write_text(cal.to_json())
    cv2.imwrite(str(out / "calib_preview.png"), preview(f, cal, marks))
    print(json.dumps({"calib": str(out / "calib.json"), "preview": str(out / "calib_preview.png")}))


if __name__ == "__main__":
    main()
