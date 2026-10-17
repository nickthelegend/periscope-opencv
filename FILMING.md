# Filming protocol: the first real-footage test

Goal: one afternoon of footage that answers **"is the floor shadow there with our camera?"**,
scored against a second camera that sees the hidden hallway. Budget about two hours.

The synthetic sweep (`results/sweep.md`) says what has to be true: the per-pixel signal from a
person 3 m around the corner must be at least ~0.06 of the per-pixel noise, the camera must not
move more than ~1 px, and the video must not be compressed like a normal phone clip. Everything
below exists to meet those three numbers.

## What you need

- **Corner camera:** an iPhone 13 Pro or newer (ProRes), or any phone/camera that can record
  at ≥ 50 Mbps. A Raspberry Pi HQ camera or a USB webcam saving lossless frames also works.
- **Ground-truth camera:** any second phone (normal settings are fine).
- Two tripods (or a tripod plus a stack of books for the second phone).
- Masking tape in a bright colour, a tape measure, a marker.
- One helper who walks, wearing a **saturated top**: red, royal blue or green. Not grey, black
  or white for the first take (the sweep shows mid-grey costs about a quarter of the range).
- Optional: a floor lamp or two to brighten the hidden hallway.

## Pick the corner

- An L-shaped corridor corner, ideally with a matte, light, even floor (concrete, vinyl, matte
  tile). Avoid glossy floors with reflections, and avoid patterned carpet.
- **Both hallways lit.** The hidden hallway's lights are what make the shadow; the brighter it
  is relative to your side, the stronger the signal. Daylight from a window is fine if no
  clouds are moving (moving cloud = changing light = false signal).
- No moving things on either side apart from the walker: no screens, fans, flickering tubes.
- Sunlit corners outdoors work too (CornerCam showed this), as long as the sun is steady.

## Tape the floor (5 marks, about 5 minutes)

All distances are measured from the corner, the point where the wall's vertical edge meets
the floor. "Wall line" = along the base of the wall on the camera's side. "90° line" = across
your hallway, continuing the line of the hidden hallway's near wall.

| # | Mark | Where |
|---|---|---|
| 1 | corner | the corner itself |
| 2 | wall 50 | on the wall line, 50 cm from the corner |
| 3 | wall 100 | on the wall line, 100 cm from the corner |
| 4 | 90° 50 | on the 90° line, 50 cm from the corner |
| 5 | 90° 100 | on the 90° line, 100 cm from the corner |
| 6 | (optional) diagonal | 100 cm along the wall line and 100 cm across |

Use small tape crosses (2–3 cm), not long strips: tape is part of the floor the shadow falls on.

**Hidden hallway marks for the ground-truth camera** (x is along the hidden hallway, negative
going away from the corner; y is across it from the near wall):

| Mark | Floor position (m) |
|---|---|
| A | x = −1, y = 0.4 |
| B | x = −1, y = 1.6 |
| C | x = −5, y = 0.4 |
| D | x = −5, y = 1.6 |

If the hallway is narrower than 2 m, put B and D 0.4 m from the far wall and note the real y.

## Set up the cameras

**Corner camera**
- Tripod about 1.5 m high, 1.5–2 m back from the corner on your side, pointing **down at the
  floor next to the corner**. All five marks and about 1 m of floor around the corner must be in
  frame. The hidden hallway should **not** be visible (that's the point).
- Settings: 1080p or 4K, 30 fps, **ProRes** (iPhone: Settings → Camera → Formats → Apple
  ProRes) or the highest bitrate the app offers (Blackmagic Camera app: H.265 at 100+ Mbps or
  ProRes). Normal phone H.264 (~15 Mbps) is not enough: the sweep shows it loses about half the
  range.
- **Lock exposure, focus and white balance** (iPhone: long-press on the floor until AE/AF LOCK
  appears; the Blackmagic app has explicit locks). Auto exposure chasing the walker would
  swamp the shadow.
- Turn off stabilisation if the app allows it (it resamples every frame). Don't touch the
  phone once recording; start it with a Bluetooth remote, Apple Watch or a timer.

**Ground-truth camera**
- In the hidden hallway, at the far end, about 2 m high if possible, looking back toward the
  corner so marks A–D and the walker's feet are visible the whole way.
- Normal video settings are fine.

## The takes (about 1 minute each)

Start **both** cameras, then **clap once** where both phones can hear it (this syncs them).
Stay out of both views for the first **5 seconds** (Periscope learns the empty hallway), and
keep the camera side empty the whole take.

1. **Approach and retreat** (the main test): walker starts 8 m down the hidden hallway, walks
   toward the corner at a normal pace along the middle, stops about 1 m before the corner line
   (do not step into the camera's view), waits 2 s, walks back. Repeat 3 times per take.
2. **Empty hallway**, 60 s: nobody anywhere. This measures false alarms.
3. **Slow walk** close to the far wall, then close to the near wall (different angles).
4. **Grey top** repeat of take 1 (realistic clothing).
5. **Lights**: half the hidden hallway lights off, repeat take 1 (signal floor).
6. Optional: **someone nudges the tripod** mid-take (the agent should flag recalibration).

Write down each take's number, top colour and lighting in a notes file next to the videos.

## Process it

Copy the files to `data/raw/` (git-ignored), then:

```bash
.venv/bin/python tools/calibrate.py data/raw/take1_corner.mov --frame-only
```

Open `web/calibrate.html`, load `first_frame.png`, click the five marks in table order, copy
the mark string it prints, then:

```bash
.venv/bin/python tools/calibrate.py data/raw/take1_corner.mov --marks "PASTE MARKS HERE"
```

Check `calib_preview.png`: the yellow wedge must sit on the floor beside the corner, its 0°
edge along the wall base. Do the same for the ground-truth camera's marks A–D (only the mark
string is needed). Then score the take:

```bash
.venv/bin/python tools/score_footage.py --corner data/raw/take1_corner.mov --calib data/raw/take1_corner/calib.json --gt data/raw/take1_hidden.mov --gt-marks "PASTE A-D MARKS HERE" --out results/take1
```

It prints and saves `score.json` (angle error, detection rate, false alarms, warning lead
time) and `track.png`, and writes a run the console page can open.

## Go / no-go for real footage

- **Go:** on take 1, the person is detected at ≥ 2 m from the corner on most passes, the angle
  error is under ~8°, and the empty take raises no alarm.
- **Marginal:** detected only within ~1.5 m, or only with the red top and all lights on.
  Still demo-able as a controlled set-up; say so in the video.
- **No-go:** nothing above noise even with the red top, bright hallway and ProRes. Switch to
  the fallback (the agentic Quiver variant) and keep this repo as a documented negative result.
