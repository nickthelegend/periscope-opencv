# Periscope feasibility spike: research and verdict

*October 17, 2026. Target: OpenCV AI Competition 2026, powered by AWS; final submissions due
**October 26, 11:59 pm Pacific**.*

## Verdict: conditional GO

**Keep building Periscope. The fallback stays warm until one real-footage take is scored, by
October 20 at the latest.**

What the synthetic spike shows (numbers from `results/sweep.md`, 3 seeds per row):

| | Result |
|---|---|
| Signal a person makes on one floor pixel, 3 m from the corner (red top, lit hallway, 8-bit phone video) | **0.47 grey levels** (0.31 % of a 150-level floor) |
| Per-pixel noise of a phone in a lit room | ~2.3 grey levels, so a per-pixel **SNR of 0.21** |
| Signal floor: lowest SNR with ≥ 90 % detection within 3 m, ≤ 6° error, no false alarms | **between 0.052 and 0.069** |
| Margin at nominal conditions | **~3–4×** |
| At nominal: first detection / bearing error ≤ 3 m / warning before the closest point | **4.3 m** from the corner / **2.6°** / **2.2 s** |
| False alarms, 14 s empty hallway × 3 seeds, at every noise level tested (up to 12× noise) | **0** |
| Grey top / hidden hallway half as bright | still pass (SNR 0.095 / 0.11; detection at 3.2 / 3.7 m) |
| Camera shake 1 px RMS, lamp flicker 2 %, a +5 % exposure jump | pass |
| **Phone H.264 at ~13 Mbps** (CRF 18) | **fails**: detection within 3 m drops to 88 % and first detection to 2.4 m |
| Near-lossless H.264 (~81 Mbps at 1080p30) | detects fully, but 1.5 % false alarms on the approach run |

So the method has real margin in theory, degrades gracefully, and fails safe: below the
floor it sees the person later, it does not make people up. The three things that decide the
real outcome, in order:

1. **Compression.** Ordinary phone video destroys a 0.3 % signal. The protocol requires ProRes
   or ≥ 50 Mbps. The product answer is to bin the floor on the device, before compression.
2. **Light on the hidden side.** The shadow is the hidden hallway's light being blocked. Half
   the light halves the SNR, which still passes; a dark hidden hallway does not.
3. **Our light model may be optimistic.** It assumes the hidden hallway is lit as brightly as
   the camera's side. CornerCam measured "less than 0.1 %" on its scenes [1]; we model 0.31 %
   at 3 m. If real footage is 3× weaker, the 3–4× margin is gone. Only footage settles this,
   so FILMING.md is the next step, not more code.

**Go / no-go gate (FILMING.md):** on the first real take, detected ≥ 2 m from the corner on
most passes, bearing error under ~8°, no alarm on the empty take. If it only works within
~1.5 m, demo it as a controlled set-up and say so. If nothing rises above the noise with a red
top, bright hidden hallway and ProRes, switch to the fallback (the agentic Quiver variant).

## What the spike built

- `periscope/geometry.py`: corner and floor-wedge calibration from five tape marks
  (homography to metric floor angles, so oblique cameras work), plus a corner-finding helper
  (`auto_calibrate`) that pairs the wall base with the wall's vertical edge.
- `periscope/recon.py`: angular binning of the wedge (`np.bincount`, 0.22 ms/frame at
  640×360), the CornerCam forward model (floor angle θ sees hidden angles 0…θ), and a
  pixel-count-weighted, smoothness-regularised least-squares inverse with a global-light
  column. It is one precomputed matrix, so every frame costs a single matrix–vector product.
- `periscope/engine.py`: the streaming engine.
  - **Background:** learns the empty hallway for 2 s, then follows slow light changes, but only
    while the corner is clear.
  - **Noise model:** measures a colour-channel noise covariance and keeps the detection score
    calibrated (χ² with 3 degrees of freedom under noise alone).
  - **Shake:** phase correlation on the floor grain, whole-pixel alignment, then the leftover
    sub-pixel shift is removed with the background's binned first and second derivatives, both
    as a Taylor correction and as nuisance columns in the inverse.
- `periscope/track.py`: whitened detection score with hysteresis, an α-β bearing tracker with
  lag compensation, and the "someone is coming" state. The time-to-corner uses the hallway
  geometry, t = sin 2φ / (2|φ̇|); a plain φ/φ̇ overstates it about 3×.
- `periscope/quality.py`: the signal agent. It turns measured noise, shake, drift, exposure,
  clipping and wedge size into one action, each citing its number: watch, stop the vehicle,
  re-learn the background, add light, steady the camera, recalibrate, or reframe. The engine
  acts on re-learn by itself.
- `periscope/render.py`: the synthetic scene. A ray-cast pinhole camera looks at a textured
  floor and wall; the CornerCam light model gives the hidden hallway's contribution; a coloured,
  cylindrical walker moves through it. Options cover Poisson–Gaussian noise, shake, flicker,
  exposure jumps and JPEG. There is also a second "ground-truth" camera that films the hidden
  hallway.
- `tools/snr_sweep.py` (the signal floor), `tools/score_footage.py` (real footage against a
  second camera, synced by a hand clap), `tools/calibrate.py` + `web/calibrate.html` (tape
  marks), `tools/make_demo.py`, `tools/bench.py`, and `web/index.html` (the console).
- 27 pytest tests, ~50 s: geometry, the inverse, the SNR floor on both sides, nuisances,
  agent decisions, the ground-truth tracker and the end-to-end footage scorer.

### Bugs found on the way

These are worth knowing for anyone on OpenCV 5.0.0 from Python:

- **`cv2.phaseCorrelate` applies the Hanning window to its input arrays in place.** A cached
  reference frame decays a little on every call. This produced phantom 0.3 px "shake" and
  false tracks until we passed copies. Worth an upstream issue; it's a good, concrete OpenCV
  contribution to mention.
- `cv2.HoughLinesP` returns `(N, 4)` in 5.0 instead of `(N, 1, 4)` in 4.x.

Spike findings that changed the design:

- **Never resample the frame to stabilise it.** The floor grain is about 10× stronger than
  the shadow, and bilinear warping blurs it differently at every sub-pixel offset: 0.3 px of
  shake made constant false alarms. Whole-pixel shifts plus bin-domain correction fixed it.
- **Colour channels share noise** (demosaicing, codecs). Treating R, G and B as independent
  overstated the evidence 2×, so the score is whitened with the measured covariance.

## The competition

From the official pages, read on October 17 [2][3][4]:

- **Requirements:**
  - OpenCV 5 doing "substantive image/video analysis", plus "a meaningful AWS component".
  - A judge-accessible web endpoint is preferred; a scheduled live demo is acceptable.
  - Deliverables: a technical report, a repo with pinned dependencies, an architecture
    diagram, a video of **≤ 5 minutes**, and evaluation evidence **including failure cases**.
- **Overall rubric:**

  | Criterion | Weight |
  |---|---|
  | Technical execution | 30 % |
  | Innovation | 20 % |
  | Real-world impact | 20 % |
  | User experience | 10 % |
  | Documentation | 10 % |
  | Cloud delivery / reproducibility / responsible operation | 10 % |

  Ties go to technical execution first.
- **Prizes:** $5k / $3k / $2k overall, plus **$1k Best Use of COOL** and **$1k Agentic Vision**.
  An entry can win one overall prize plus both special awards.
- **Judges** include **Gary Bradski (OpenCV founder)** and Phil Nelson (OpenCV) [3].
- **Responsible use:** judges may reject entries that create "safety, privacy… surveillance
  risks without appropriate safeguards" or "misrepresent capabilities, results, benchmarks" [4].
  A safety product must label synthetic results as synthetic and show its failure modes; the
  console and this report do.
- **To confirm on Devpost:** that the team is registered (opencv.org says registration closed
  Aug 17) and whether the cloud-compute grant proposal was filed. Team size is stated as both
  1–5 and "no more than four" [2]; check it.

### The AWS / Graviton angle

- **COOL** is the Cloud-Optimized OpenCV Library: an OpenCV 5 build with Arm's KleidiCV,
  sold as an AWS Marketplace AMI for Graviton4. Examples: c8g.large at about $0.01/h software
  fee; m8g.4xlarge recommended; Python 3.10–3.12 environments in `/opt/cool` [5][6].
- **The Best-Use-of-COOL award** wants the core workload on Graviton with **reproducible
  latency, throughput or cost against a baseline** [2][5]. Its rubric:

  | Criterion | Weight |
  |---|---|
  | Verified COOL on Graviton | 30 % |
  | Architecture | 25 % |
  | Measured performance | 20 % |
  | Innovation | 15 % |
  | Reproducibility | 10 % |

- **KleidiCV** accelerates exactly the kernels Periscope leans on (resize, blur and filters;
  "up to 4×" per Arm) [7]. Graviton4 C8g claims up to 30 % over C7g [8].
- **Measured here** (Apple M-series arm64, stock OpenCV 5.0.0, `tools/bench.py`):

  | Workload | ms per frame |
  |---|---|
  | Full engine at 640×360, stabilised | 4.2 |
  | Full engine, no stabilisation | 0.4 |
  | 1080p input, including the resize | 4.3 |
  | Phase correlation alone | 2.6 (the dominant cost) |
  | Binning alone | 0.22 |

  So one core handles about 200 frames/s, or ~6 corners at 30 fps. Graviton/COOL numbers are
  **not measured yet**.
- **Architecture this suggests** (and that compression forces anyway):
  - **On the camera** (Pi or phone): reduce each raw frame, before compression, to the 90×3
    bin means plus a 2-number shift. That is about **1 KB per frame, ~32 KB/s at 30 fps**.
  - **To AWS:** stream that over IoT Core / MQTT or Kinesis.
  - **On Graviton (COOL):** inversion, tracking, the agent and the alert endpoint for many
    corners, plus a full-frame path for calibration and audits.
  - **Benchmark for the award:** COOL on c8g vs stock OpenCV on c7i/x86, as ms/frame and
    $/corner-month.

  The KVS producer SDK can carry frames [9], but compressed video is exactly what kills the
  signal, so it only suits the audit path.

### The Agentic Vision angle

The award requires the vision output to "change a later plan, tool call, action or
human-approval request", with a trace and an evaluation of failure handling and human control
[2]. The signal agent already does this: measured noise → "add light", a light jump → it
re-learns the background by itself, drift → "recalibrate", a tracked approach → "stop the
vehicle", and every decision cites its number.

Missing before submission:

- a human-approval step for recalibration (show the new wedge, approve);
- an exported decision trace (JSON plus a screenshot of the log);
- an MCP or HTTP tool the vehicle calls.

## Prior art

- **CornerCam, Bouman et al., ICCV 2017** [1]:
  - Recovers a 1-D angular video of the hidden scene from the floor at a wall edge, where the
    signal is "less than 0.1 %" of pixel intensity.
  - People walking 2–16 ft from the corner were tracked on brick, tile, wood and asphalt, in
    sun, cloud and rain. Two edges (a doorway) give 2-D position.
  - The phone camera was their noisiest. Background was the mean frame of the whole video
    (offline), and the corner was identified by hand.
- **ShadowCam, Naser et al., ITSC 2018 / IROS 2019** [10][11]:
  - Detects a moving hidden obstacle from shadow changes, about **0.72 s** before LiDAR in a
    garage; 85.9 % accuracy over 125 sequences at 20 Hz.
  - Earlier: ~70 % on real corners, on an autonomous wheelchair.
  - Tuned to one garage's lighting, headlights off, indoors.
- **Corner occluder periscopy, Seidel et al., ICCP 2019; IEEE TCI 2021**: a hidden scene from a
  single photograph, with angle and range [12].
- **Recent:**
  - PathFinder (2024): NLOS tracking from RGB video on a drone [13].
  - Event-camera passive NLOS (2023–24) [14].
  - Active NLOS (SPAD lidar; consumer-phone LiDAR in *Nature*, May 2026) [15][16].
- **Nobody has productized passive corner cameras.** No commercial product was found.

**Where Periscope differs from ShadowCam:** a calibrated angular inverse rather than a
shadow-change classifier, so it gives a bearing and a bearing rate, not just a yes/no. It runs
live with a learned background rather than offline. Its noise model knows when it can't see.
And it has an agent that acts on signal quality. Its lead time on synthetic data (**2.2 s at
1.3 m/s**) is to the walker's closest point, not to LiDAR detection, so it is not directly
comparable to ShadowCam's 0.72 s.

## Risks and what to do about them

| Risk | Likelihood | Mitigation |
|---|---|---|
| Real signal weaker than the model | medium | Film first (Oct 18–20); brighter hidden hallway, saturated top, matte floor; widen the wedge to 1.5 m for more pixels |
| Compression | high with default settings | ProRes / Blackmagic Camera app at high bitrate; for the product, bin before encoding |
| Auto exposure / white balance drift | medium | Lock AE/AWB in the protocol; the engine's offset column and auto re-learn |
| Moving light (clouds, people on the camera side) | medium | Indoors for the demo; the agent flags "light change" |
| Judges doubt synthetic numbers | high if we only show synthetic | The ground-truth camera scorer exists; the console overlays truth; show the failure cases |
| Deadline (9 days) | medium | Remaining work is filming, AWS deployment, the video; no new algorithms |

## Next steps

| Date | Step |
|---|---|
| Oct 18–20 | Film per FILMING.md; score with `tools/score_footage.py`; **go/no-go**. |
| Oct 20–22 | Bin-on-device path; Graviton c8g + COOL deployment; benchmark against an x86 baseline; alert endpoint. |
| Oct 22–24 | Agent: human approval for recalibration, decision-trace export, vehicle-stop tool. |
| Oct 24–26 | Real run in the console, technical report, architecture diagram, ≤ 5-minute video, submit before Oct 26 11:59 pm PT. |

## Sources

1. Bouman, Ye, Yedidia, Durand, Wornell, Torralba, Freeman. *Turning Corners into Cameras: Principles and Methods.* ICCV 2017. https://openaccess.thecvf.com/content_ICCV_2017/papers/Bouman_Turning_Corners_Into_ICCV_2017_paper.pdf
2. OpenCV AI Competition 2026 (official page, rules, focus paths, rubric). https://opencv.org/opencv-ai-competition-2026/
3. Devpost: OpenCV AI Competition 2026 (deadline, prizes, judges). https://opencv26.devpost.com/
4. Devpost official rules. https://opencv26.devpost.com/rules
5. COOL: Cloud-Optimized OpenCV Library. https://opencv.org/COOL/
6. AWS Marketplace: Cloud Optimized OpenCV for AWS Graviton4. https://aws.amazon.com/marketplace/pp/prodview-fdvbfiewzuehs
7. Arm: KleidiCV integration into OpenCV (Feb 18, 2025). https://newsroom.arm.com/blog/arm-kleidicv-opencv-integration
8. Amazon EC2 C8g instances. https://aws.amazon.com/ec2/instance-types/c8g/
9. Kinesis Video Streams producer SDK. https://docs.aws.amazon.com/kinesisvideostreams/latest/dg/producer-sdk.md
10. Naser et al. *ShadowCam: Real-Time Detection of Moving Obstacles Behind a Corner for Autonomous Vehicles.* ITSC 2018. https://dspace.mit.edu/handle/1721.1/119439
11. Naser et al. *Infrastructure-free NLoS Obstacle Detection for Autonomous Cars.* IROS 2019. https://tisl.utm.utoronto.ca/publication/201911-iros-nlos_obstacle_detection/iros19-nlos_obstacle_detection.pdf ; summary: https://news.mit.edu/2019/helping-autonomous-vehicles-see-around-corners-1028
12. Seidel et al. *Two-Dimensional Non-Line-of-Sight Scene Estimation from a Single Edge Occluder.* IEEE TCI 2021. https://arxiv.org/abs/2006.09241
13. PathFinder (2024). https://arxiv.org/abs/2404.05024
14. Passive NLOS imaging with event cameras (2024). https://arxiv.org/abs/2404.05977
15. Single-photon LiDAR NLOS navigation (2024). https://arxiv.org/abs/2410.03555
16. MIT Media Lab: everyday LiDAR as an around-the-corner camera (May 2026). https://www.media.mit.edu/posts/mit-media-lab-researchers-turn-everyday-lidar-into-an-around-the-corner-camera/

*Competition facts were read from the official pages on Oct 17, 2026. Where the opencv.org page
and Devpost disagree (team size, credit counts, check-in dates), Devpost's rules govern; check
before submitting.*
