# Periscope

**See who's coming around the corner with an ordinary camera.** A person in a hidden hallway
blocks a sliver of the light that reaches the floor beside a wall corner, about 0.3 % of the
floor's brightness. Periscope reads that faint shadow, recovers the person's bearing around
the corner every frame, and warns a forklift, robot or wheelchair before they step into view.

Built for the **OpenCV AI Competition 2026, powered by AWS**. Status: **feasibility spike**.
The synthetic results are in; real footage is next (see [FILMING.md](FILMING.md)). The verdict
and its numbers are in [RESEARCH.md](RESEARCH.md).

## How it works

```
corner camera ─► 5 tape marks → floor homography → wedge from the wall (0°) to 90°
     frame ─► phase-correlation registration (floor grain) ─► whole-pixel align
           ─► 90 angular bins ─► undo the sub-pixel shift (binned background derivatives)
           ─► ÷ empty-hallway background ─► 0.4 s moving average
           ─► regularised least-squares inverse (CornerCam forward model) ─► 45 hidden bearings
           ─► colour-whitened χ² score ─► α-β bearing tracker ─► clear / present / coming
           ─► signal agent: watch · stop vehicle · re-learn · add light · steady · recalibrate
```

Floor angle θ sees the hidden hallway over bearings 0…θ (Bouman et al., *Turning Corners into
Cameras*, ICCV 2017). Comparing neighbouring floor angles recovers the light coming from each
hidden bearing; a person is a moving dip in their own colour.

## Synthetic results (`results/sweep.md`)

| Condition | Result |
|---|---|
| Nominal (phone in a lit room, red top) | First detection 4.3 m from the corner, bearing error 2.6° within 3 m, warning 2.2 s before the closest point, 0 false alarms |
| Signal floor | Per-pixel SNR ≈ 0.06 for a person 3 m away; nominal is 0.21 |
| Grey top, half-lit hidden hallway, 1 px shake, 2 % flicker, exposure jump | Pass |
| Phone-grade H.264 (~13 Mbps) | Fails: record ProRes, or bin before compressing |

## Run it

```bash
uv venv .venv -p 3.12 && uv pip install -p .venv/bin/python -r requirements.txt
.venv/bin/python -m pytest -q                 # 27 tests, ~50 s
.venv/bin/python tools/make_demo.py           # render + run the synthetic corner → web/runs/demo
.venv/bin/python -m uvicorn server:app --port 8740   # console at http://localhost:8740
.venv/bin/python tools/snr_sweep.py           # the signal-floor sweep (~10 min)
.venv/bin/python tools/bench.py               # ms/frame per stage
```

Real footage: [FILMING.md](FILMING.md), then `tools/calibrate.py` (with `web/calibrate.html`
for clicking the tape marks) and `tools/score_footage.py` against a second camera.

## Layout

| Path | What |
|---|---|
| `periscope/geometry.py` | tape-mark calibration, wedge maps, corner finder |
| `periscope/recon.py` | angular binning, forward model, regularised inverse |
| `periscope/engine.py` | streaming engine: registration, background, noise model |
| `periscope/track.py` | detection score, bearing tracker, time-to-corner |
| `periscope/quality.py` | signal agent: checks and actions |
| `periscope/render.py` | synthetic corner scene and ground-truth camera |
| `periscope/groundtruth.py` | second-camera tracking, clap sync |
| `periscope/pipeline.py` | run, score, export for the console |
| `web/index.html` | console: floor view, spacetime, corner map, alert, agent |

MIT licence.
