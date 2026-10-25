# CLI audit evidence

Logs in this directory store each command's argv, exit code, stdout, and stderr. `AUDIT.md` was not edited and these notes do not grade its rows.

## pytest

- argv: `.venv/bin/python -m pytest -q`
- exit: 0
- observed: 75 passed in 56.58s (`pytest.txt`)

## calibrate --help

- argv: `.venv/bin/python tools/calibrate.py --help`
- exit: 0
- observed: usage lists positional `video`, `--frame-only`, and `--auto` (`calibrate-help.txt`)

## synthetic frame

- argv: `.venv/bin/python` with this stdin script (also copied in `render-frame.txt`):

```python
import cv2
from periscope.render import Scene, empty_hallway
scene = Scene()
frame = next(scene.render(empty_hallway(scene.fps, 0.1)))
path = "audit/cli/calib-out/frame.png"
ok = cv2.imwrite(path, frame)
print("imwrite", ok, "shape", frame.shape, "dtype", frame.dtype, "path", path)
cap = cv2.VideoCapture(path)
fps = cap.get(cv2.CAP_PROP_FPS)
n = cap.get(cv2.CAP_PROP_FRAME_COUNT)
print("capture_opened", cap.isOpened(), "fps", fps, "frame_count", n)
seek = int(0.5 * (fps or 30))
cap.set(cv2.CAP_PROP_POS_FRAMES, seek)
ok2, f = cap.read()
print("seek_to", seek, "read_ok", ok2, "frame_is_none", f is None)
cap.release()
```

- exit: 0
- observed: wrote `calib-out/frame.png`, shape (360, 480, 3); VideoCapture read it after a 0.5 s seek (`render-frame.txt`)

## calibrate --frame-only

- argv: `.venv/bin/python tools/calibrate.py audit/cli/calib-out/frame.png --frame-only --out audit/cli/calib-out/frame-only`
- exit: 0
- observed: wrote `calib-out/frame-only/first_frame.png` (`calibrate-frame-only.txt`)

## calibrate --auto

- argv: `.venv/bin/python tools/calibrate.py audit/cli/calib-out/frame.png --auto --out audit/cli/calib-out/auto`
- exit: 0
- observed: `auto_confidence` 1.0; wrote `calib-out/auto/calib.json` and `calib-out/auto/calib_preview.png` (`calibrate-auto.txt`)

## bench

- argv: `.venv/bin/python tools/bench.py`
- exit: 0
- observed: `ms_640x360_stabilised` 3.63, `ms_1080p_in_stabilised` 4.0 (`bench.txt`)

## snr sweep

- argv: `.venv/bin/python tools/snr_sweep.py --quick --seeds 1 --out audit/cli/sweep-quick`
- exit: 0
- observed: signal floor 0.06875657502570781; wrote `sweep-quick/sweep.json`, `sweep.md`, and `sweep.png` (`snr-sweep.txt`). `results/sweep.md`, `results/sweep.json`, and `results/sweep.png` kept mtime 1792955595.

## make_demo

- argv: `.venv/bin/python tools/make_demo.py --out audit/cli/demo-rerun`
- exit: 0
- observed: pid 83385 finished in 14.8 s (limit 900 s, not killed); near recall 1.0; wrote `demo-rerun/run.json` plus floor/shadow/hidden mp4 and webm (`make-demo.txt`). `web/runs/demo/` kept mtime 1792955595. The three mp4 files match `.gitignore` `*.mp4` and stay untracked.

## score_footage --help

- argv: `.venv/bin/python tools/score_footage.py --help`
- exit: 0
- observed: usage requires `--corner`, `--calib`, `--gt`, and `--gt-marks` (`score-footage-help.txt`). The tool was not run on a video.

## real footage

FILMING.md names `data/raw/take1_corner.mov` (corner clip) and `data/raw/take1_hidden.mov` (hidden-hallway clip). `score_footage.py`'s docstring also names `data/raw/take1_corner.mp4` and `data/raw/take1_hidden.mp4`. `data/raw/` does not exist, and none of those four paths exist. No clip was invented (`footage-absent.txt`).
