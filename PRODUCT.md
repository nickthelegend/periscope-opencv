# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Static HTML/CSS/JS: one self-contained `web/index.html`, served with the run files by a small FastAPI server (`server.py`). No build step. (User's choice, Oct 17 2026.)

## Users

- **First: competition judges and the submission video.** OpenCV AI Competition 2026 (powered by AWS) judges, including OpenCV's founder, watching a ≤5-minute video or opening the demo endpoint. They need to grasp "an ordinary camera sees someone around a corner" within seconds, then see evidence that it is real: the calibration, the spacetime image, scores against ground truth, failure handling.
- **Second: site safety operators.** People responsible for a blind corner in a warehouse, hospital corridor or robot lab, watching a corner live. Their job is to trust the alert and understand why it fired.

## Product Purpose

Periscope reads the faint floor shadow a hidden person casts at a wall corner (≈0.1–0.3 % of pixel brightness) and turns it into the person's angle around the corner over time, so a forklift, robot or wheelchair can slow down before anyone steps into view. Success: a correct "someone is coming" warning seconds before line of sight, with no false alarms on an empty corridor.

## Positioning

Passive non-line-of-sight sensing with one ordinary camera and no infrastructure on the hidden side (MIT CornerCam, ICCV 2017; ShadowCam). Never productized. Periscope adds a signal-quality agent that decides when the shadow is readable and what to do when it is not.

## Operating Context

- A camera on a tripod or vehicle mast points at the floor beside a wall corner; five tape marks calibrate the floor wedge.
- The engine reduces each frame to ~90 angular bin means; the inverse, tracker and agent can run on AWS Graviton.
- Ground truth for evaluation comes from a second phone filming the hidden hallway.

## Capabilities and Constraints

- Output is a 1-D angle (0–90°) over time, not a distance or an image of the person. One corner gives angle only.
- Works best with a bright, evenly lit floor, a steady camera, and a person in strong colours; detection range shrinks as roughly 1/d³.
- Video compression destroys the signal at typical phone bitrates; recording must be near-lossless or the binning must run before compression.
- Synthetic results exist; real-footage results do not yet.

## Evidence on Hand

- Synthetic renderer + SNR sweep (`results/sweep.md`), demo run (`web/runs/demo/`), pytest suite.
- No real-footage results, customers, deployments or benchmarks yet. Do not imply any.

## Product Principles

1. Show the evidence, not just the alert: every warning traces back to the floor signal that caused it.
2. Honest about limits: say when the signal is too weak and what would fix it.
3. Safety first: a missed person is worse than a late one, a false alarm erodes trust; show both.
4. Synthetic is labelled synthetic.
