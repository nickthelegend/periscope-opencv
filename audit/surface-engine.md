# Surface and engine notes

Input for a later `AUDIT.md` author. This is not the official audit table. Snapshot of this worktree at `ff54829` (`wip: uncommitted changes left by the Oct 18 Loom run`). Product source was not edited. `README.md`, `server.py`, `tests/test_alerts.py`, and `web/index.html` are owned by another worker and may change after this note.

Any note below about the alert feed or the `web/index.html` publisher is marked **unverified wip ff54829, confirm after the alert-feed task**.

Pytest was not run. No server, browser, or SNR sweep was started.

## Nominal numbers to cite (RESEARCH.md verdict)

`RESEARCH.md` verdict is **conditional GO**: keep building; the fallback stays warm until one real-footage take is scored (it names October 20). Numbers it attributes to `results/sweep.md`, 3 seeds per row:

| Claim in RESEARCH.md | Number |
|---|---|
| Signal on one floor pixel, person 3 m out, red top, lit hallway, 8-bit | 0.47 grey levels (0.31 % of a 150-level floor) |
| Phone noise in a lit room | ~2.3 grey levels; per-pixel SNR 0.21 |
| Signal floor (lowest SNR with ≥ 90 % detection within 3 m, ≤ 6° error, no false alarms) | between 0.052 and 0.069 |
| Margin at nominal | ~3–4× |
| Nominal first detection / bearing error within 3 m / warning lead | 4.3 m / 2.6° / 2.2 s |
| False alarms, 14 s empty hallway × 3 seeds, every noise level up to 12× | 0 |
| Grey top / hidden hallway half as bright | pass (SNR 0.095 / 0.11; detection at 3.2 / 3.7 m) |
| Shake 1 px RMS, lamp flicker 2 %, exposure jump +5 % | pass |
| Phone H.264 ~13 Mbps (CRF 18) | fails: detection within 3 m drops to 88 %, first detection 2.4 m |
| Near-lossless H.264 (~81 Mbps at 1080p30) | detects fully; 1.5 % false alarms on the approach run |

`periscope/quality.py` constants: `NOMINAL_REL_SIGNAL_3M = 0.0031`, `SNR_FLOOR_3M = 0.05`.

The tests do not assert 4.3 m, 2.6°, or 2.2 s. `test_nominal_conditions_give_real_warning` asserts `scene.snr(3.0) == pytest.approx(0.21, abs=0.02)`, `first_detect_distance_m >= 3.5`, and `lead_time_s >= 2.0`.

Shipped demo `web/runs/demo/run.json` (already in the tree; `make_demo.py` was not re-run): `title` `"Synthetic corner · red top · lit hallway"`, `scene.kind` `"synthetic"`, `snr3` 0.224, `noise_dn` 2.29, `signal3_dn` 0.513, `fps` 20, 380 frames, states learning 60 / clear 155 / present 101 / coming 64. Score the console prints from `score.far` / `score.near` with `toFixed`: First detection `4.4` m from corner, Warning lead `2.1` s, Bearing error `2.1` ° mean, Detected within 3 m `100` % of frames, False alarms `0.0` % empty frames, Bearing error p90 `5.4` °.

`RESEARCH.md` also quotes a past `tools/bench.py` run on Apple arm64, OpenCV 5.0.0: full engine 640×360 stabilised 4.2 ms, no stabilisation 0.4 ms, 1080p in 4.3 ms, phase correlation 2.6 ms, binning 0.22 ms. This note did not re-run the bench. `RESEARCH.md` says Graviton/COOL numbers are not measured.

`RESEARCH.md` line 76 says "27 pytest tests, ~50 s". `README.md` line 41 says "72 tests, ~55 s". Counting current test functions with their parametrize expansions (including `tests/test_alerts.py`) gives 72. Confirm the README line after the alert-feed task, because that worker owns `README.md`.

## 1. Console controls (`web/index.html`)

Page title: `Periscope · see who's coming around the corner`. Wordmark text: `PERISCOPE`. H1: `See who's coming around the corner.`

### Run select

- Control: `<select id="runSel" aria-label="Choose a run">`.
- `listRuns()` fills one `<option value="{id}">` per object from `GET api/runs`, using `title` with `<` replaced by `&lt;`.
- If `?run=` matches an id, that option is selected.
- Changing the select sets the query to `?run={id}` via `history.replaceState` and calls `load(id)`.
- Fallback when the fetch throws or the JSON list is empty (quote this exact statement):

```javascript
if (!runs.length) runs = [{ id: "demo", title: "Synthetic corner · red top · lit hallway" }];
```

A test demands: with `GET /api/runs` returning `[]`, `#runSel` has one option, `value` `demo`, text `Synthetic corner · red top · lit hallway`.

A failed load (`runs/{id}/run.json` not ok) replaces `#console` inner HTML with a panel whose `<b>` text is `That run could not be loaded.` and whose following text is `Check that runs/${id}/run.json exists, or pick another run.`

### Synthetic tag

`#kindTag` text is `Synthetic scene`. The element is shipped with the `hidden` attribute. After a successful load, `hidden` is removed only when `run.scene.kind === "synthetic"`. Otherwise it stays hidden, and `#sceneFoot` text is `Recorded footage`.

For the shipped demo, a test demands `#kindTag` is not `hidden` and its text is `Synthetic scene`, and `#sceneFoot` text is exactly:

`Synthetic: per-pixel SNR 0.224 at 3 m · noise 2.29 DN · signal 0.513 DN`

See section 2 for the 640px CSS that still hides `.tag.synth`.

### Autoplay

```javascript
const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
const autoplay = new URLSearchParams(location.search).get("autoplay") !== "0" && !reduced;
```

`load()` calls `play()` when `autoplay && !userPaused`, immediately if `#vFloor.readyState >= 2`, otherwise on the first `canplay`.

A test demands:

- Default URL, `prefers-reduced-motion` not `reduce`, demo run loaded and `canplay` fired: `#playTxt` text is `Pause`, `#playBtn` `aria-label` is `Pause`, `#vFloor.paused` is false, `#vFloor.playbackRate` is `1`.
- `?autoplay=0`: `#playTxt` stays `Play run` and `#vFloor.paused` stays true until `#playBtn` is clicked.
- `prefers-reduced-motion: reduce`: same as `?autoplay=0` (the query is ignored only in the sense that autoplay is off; the code still requires both conditions).
- On `#vFloor` `ended`: `#playTxt` becomes `Replay`. If `autoplay && !userPaused`, a 2500 ms timer then calls `seek(0)` and `play()`.

`play()` catch path: if `vF.play()` rejects, and `playing` is still true, it calls `pause("error")`. **unverified wip ff54829, confirm after the alert-feed task:** that pause posts `{live: false, reason: "error"}`.

### Play and restart

Initial HTML, before `play()`: `#playTxt` is `Play run`, `#playBtn` `aria-label` is `Pause` (the attribute and the label disagree until `setPlayUi` runs).

`setPlayUi` then demands:

| Playback | `#playTxt` | `#playBtn` aria-label |
|---|---|---|
| playing | `Pause` | `Pause` |
| paused, `frameIdx === 0` | `Play run` | `Play` |
| paused, `frameIdx > 0` | `Resume` | `Play` |
| `ended` handler | `Replay` | set by `pause()` to `Play` |

`#playBtn` click while playing sets `userPaused = true` and pauses. Click while paused sets `userPaused = false` and plays.

`#restartBtn` `aria-label` is `Restart`. Click sets `userPaused = false`, seeks frame 0, and plays. Clock text at frame 0 of the demo (380 frames, 20 fps, duration 19.00 s) is `0.00 / 19.00 s`. HUD `#hudT` is `t 0.00 s`.

`Space` on `document` clicks `#playBtn`, unless the event target is inside `select, input, textarea, button, [role=slider]`. ArrowLeft / ArrowRight outside those targets pause and step one frame.

Transport hint text (hidden at `max-width: 640px` by `.keys { display: none }`): `Space` play · `←` `→` step. The `<kbd>` elements are separate; the visible words are `Space`, `play`, `·`, `←`, `→`, `step`.

### Speed

Group `aria-label` `Speed`. Buttons:

| Text | `data-rate` | Initial `aria-pressed` |
|---|---|---|
| `0.5×` | `0.5` | `false` |
| `1×` | `1` | `true` |
| `2×` | `2` | `false` |

Click sets `playbackRate` on `#vFloor`, `#vShadow`, and `#vHidden` to that number, and `aria-pressed="true"` only on the clicked button. A test demands that after clicking `2×`, all three videos have `playbackRate === 2` and only the `2×` button has `aria-pressed="true"`.

At `max-width: 640px`, `.transport .seg { display: none }` hides this speed group. The floor-view group (Split / Camera / Shadow ×70) is in `.ph`, not `.transport`, so it stays displayed.

### Floor view

Group `aria-label` `Floor view`. Heading: `Floor camera`, caption `drag the divider: camera ⟷ shadow amplified 70×`.

| Button text | `data-view` | Initial `aria-pressed` |
|---|---|---|
| `Split` | `split` | `true` |
| `Camera` | `camera` | `false` |
| `Shadow ×70` | `shadow` | `false` |

Click sets `#stage` `data-view` to that value and `aria-pressed="true"` only on the clicked button.

CSS a test can read without changing it:

- `#stage` starts `data-view="split"`.
- `#vShadow` clip-path is `inset(0 0 0 var(--split, 50%))`.
- `[data-view="camera"]` sets `#vShadow` `visibility: hidden`.
- `[data-view="shadow"]` sets `#vFloor` `visibility: hidden`, `#vShadow` `clip-path: none`.
- `.stage:not([data-view="split"]) .wipe` and `.wlab` are `display: none`.

Corner labels on the stage: `Camera` and `Shadow ×70`.

Legend texts: `Calibrated floor wedge, 0° wall to 90°`; `Shadow edge at the tracked bearing`; `Calibration tape marks`.

HUD `#hudPhi` initial text `bearing –`. After `show()`, `bearing –` when `phi == null`, otherwise `bearing {phi.toFixed(1)}°`.

### Wipe `#wipeBtn`

`role="slider"`, `aria-label` `Split between camera and amplified shadow`, `aria-valuemin="0"`, `aria-valuemax="100"`, `aria-valuenow="50"`. Default `--split` is `50%`.

Drag sets `--split` to a percent clamped to 4–96, and `aria-valuenow` to the rounded percent. ArrowLeft / ArrowRight (when the button is focused) change the current value by −5 / +5, then the same clamp. A test demands ArrowRight from 50 yields `aria-valuenow="55"` and `--split` `55%`, and that 100 is clamped to `96`.

### Spacetime scrub `#stBox`

Heading `Spacetime`, caption `light recovered from the hidden side, by bearing and time`.

`#stBox` is `role="slider"`, `tabindex="0"`, `aria-label` `Timeline: drag to scrub`, `aria-valuemin="0"`. After the demo loads, `aria-valuemax` is `19.00`. `show()` sets `aria-valuenow` to `t.toFixed(2)` and `aria-valuetext` to `{t.toFixed(1)} seconds`.

Pointer down sets `userPaused = true`, pauses if playing, and seeks to the frame under the pointer. ArrowRight / ArrowLeft while the box is focused pause and step 1 frame, or `run.fps` frames when Shift is held (demo: 20 frames). Home seeks frame 0. End seeks the last frame.

### Track and Truth

Group `aria-label` `Spacetime overlays`.

| Button | id | Initial `aria-pressed` |
|---|---|---|
| `Track` | (none; `data-ov="track"`) | `true` |
| `Truth` | `#truthBtn` | `true` |

Click toggles that button's `aria-pressed` and redraws. `#truthBtn` is `hidden` when `run.truth` is missing. The demo run has `truth`, so a test demands `#truthBtn` is not hidden.

### Plan vs `#hiddenBtn`

Group `aria-label` `Map view`. Heading `Corner map`, caption `plan view, bearing from the corner`.

| Button | Initial `aria-pressed` |
|---|---|
| `Plan` | `true` |
| `Hidden hallway` (`#hiddenBtn`) | `false` |

`#hiddenBtn` is `hidden` when `run.assets.hidden` is missing. The demo sets `assets.hidden` to `hidden.mp4`, so the button is shown.

Plan selected: `#vHidden` is `hidden`, `#plan` `visibility` is `visible`, `#mapNote` is `hidden`.

Hidden hallway selected: `#vHidden` is shown, `#plan` `visibility` is `hidden`, `#mapNote` is shown with text `Ground-truth camera. Periscope never sees this view.` If the floor video is playing, `#vHidden` seeks to `#vFloor.currentTime` and calls `play()`.

Map legend texts: `Bearing Periscope measured (one corner gives no distance)`; `True position (renderer; Periscope never sees it)`; `Where they step into view`.

SVG `aria-label`: `Plan view of the corner with the tracked bearing`.

### Alert card `#alert`

Initial, before the first `show()`: `data-s="learning"`, large word element text `STOP` (CSS `.alert .big { display: none }` until `data-s="coming"`), `#alertH` `Learning the empty hallway`, `#alertP` `Hold still. Periscope is measuring the floor and its noise before it watches for shadows.`, readouts `Bearing` / `In view in` / `Shadow strength` all `–`. Status pill `#statusTxt` is `Loading run` until `setState`.

`STATE_TXT` (heading, unused body for present/coming, status-pill short label):

| `data-s` | `#alertH` | `#statusTxt` | `.big` computed display | `.big` text |
|---|---|---|---|---|
| `learning` | `Learning the empty hallway` | `Learning` | `none` | `STOP` (not shown) |
| `clear` | `Corner clear` | `Clear` | `none` | `STOP` (not shown) |
| `present` | `Someone in the hidden hallway` | `Someone hidden` | `none` | `STOP` (not shown) |
| `coming` | `Someone at the corner` | `STOP` | `block` | `STOP` |

Bodies `setState` writes into `#alertP`:

- `learning`: `Hold still. Periscope is measuring the floor and its noise before it watches for shadows.`
- `clear`: `No shadow above the noise floor. Nobody is moving in the hidden hallway, or they are out of range.`
- `present`, and `pd != null && pd > 2`: `Bearing {phi.toFixed(0)}° and rising: they are walking away from the corner.`
- `present` otherwise: `Bearing {phi.toFixed(0)}°. Watching which way they move.`
- `coming`: `Bearing {phi.toFixed(0)}° and closing. Stop sent to the forklift before they step into view.`

Readouts:

- `#aPhi`: `–` when `phi == null`, else `{phi.toFixed(1)}` plus a `<small>°</small>`.
- `#aEta`: `–` unless `data-s` is `coming` and `eta != null`, then `{eta.toFixed(1)}` plus `<small>s</small>`.
- `#aZ`: `–` when `learning`, else `{sqrt(max(0, z)).toFixed(1)}` plus `<small>σ</small>`.

Coming card CSS a test demands, without editing it: `#alert[data-s="coming"]` background is the gradient `linear-gradient(180deg, #e8382d, #c42a21)`, and `.big` is `display: block` at `font-weight: 800` with size `clamp(56px, 6.2vw, 92px)`.

Shipped demo, seek by setting the videos' `currentTime` to `(index + 0.5) / 20` or by calling the same frame index the scrub uses. Observable strings:

| Frame index | t | `data-s` | `#alertH` | `#alertP` | `#statusTxt` | `#aPhi` | `#aEta` | `#aZ` |
|---|---|---|---|---|---|---|---|---|
| 0 | 0.00 s | `learning` | `Learning the empty hallway` | `Hold still. Periscope is measuring the floor and its noise before it watches for shadows.` | `Learning` | `–` | `–` | `–` |
| 40 | 2.00 s | `clear` | `Corner clear` | `No shadow above the noise floor. Nobody is moving in the hidden hallway, or they are out of range.` | `Clear` | `–` | `–` | `2.8` σ |
| 116 | 5.80 s | `present` | `Someone in the hidden hallway` | `Bearing 75°. Watching which way they move.` | `Someone hidden` | `75.0` ° | `–` | `6.2` σ |
| 127 | 6.35 s | `coming` | `Someone at the corner` | `Bearing 73° and closing. Stop sent to the forklift before they step into view.` | `STOP` | `73.4` ° | `6.3` s | `10.4` σ |
| 194 | 9.70 s | `present` | `Someone in the hidden hallway` | `Bearing 37° and rising: they are walking away from the corner.` | `Someone hidden` | `37.4` ° | `–` | (sqrt of that frame's `z`, one decimal) |

At frame 127, `.big` text `STOP` is displayed. At frames 0, 40, 116, and 194 it is `display: none`.

### Signal agent `#decision`

`quality.assess` in `periscope/quality.py` returns `action` one of: `watch`, `stop_vehicle`, `recalibrate`, `relearn_background`, `steady_camera`, `add_light`, `reframe`. Priority in that function: `coming` true → `stop_vehicle`; else the first failing check among drift, exposure or clipping, shake, signal or noise, wedge; else `watch`. `why` strings from that function:

| `action` | `why` |
|---|---|
| `stop_vehicle` | `someone is approaching the corner from the hidden side` |
| `recalibrate` | `the camera moved; the corner is no longer where the marks were` |
| `relearn_background` | `lighting or exposure changed; the empty-hallway reference is stale` |
| `steady_camera` | `camera shake is larger than the shadow signal can tolerate` |
| `add_light` | `the floor is too dark or noisy to see a shadow at a safe distance` |
| `reframe` | `too little floor next to the corner is in view` |
| `watch` | `signal is readable` |

The console does not print those `why` strings in `#decW`. It prints `ACTION` labels in `#decA` and its own sentences in `#decW`.

`ACTION` visible labels:

| `data-a` | `#decA` |
|---|---|
| `watch` | `Watching` |
| `stop_vehicle` | `Stop the vehicle` |
| `relearn_background` | `Re-learn the background` |
| `add_light` | `Add light` |
| `steady_camera` | `Steady the camera` |
| `recalibrate` | `Recalibrate` |
| `reframe` | `Reframe the view` |
| `learning` (not a `quality.py` action; forced while `s === "learning"`) | `Learning the background` |

`#decW` sentences:

- `learning`: `Measuring the empty floor and its noise before trusting any change.`
- `stop_vehicle`: `Bearing {phi.toFixed(0)}° and falling {abs(pd||0).toFixed(0)}°/s: the walker is heading for the corner line.`
- `watch` while `present`: `Shadow at {phi.toFixed(0)}° is {sqrt(z).toFixed(1)}σ above noise; not closing on the corner.`
- `watch` otherwise: `Noise, shake and light are inside limits; nothing above the noise floor.`
- `relearn_background`: `Light changed since the background was learned.`
- `add_light`: `Predicted range is too short to warn in time.`
- `steady_camera`: `Shake is larger than the shadow can tolerate.`
- `recalibrate`: `The view has slid since the tape marks were clicked.`
- `reframe`: `Too little floor beside the corner is in view.`

`setState` picks the action as: `coming` → `stop_vehicle`; else `learning` → `learning`; else the latest frame's `q.a`, or `watch` if none. So a `present` frame can still show `Stop the vehicle` when the latest `q.a` is still `stop_vehicle`.

Demo demands:

| Frame | `#decision` `data-a` | `#decA` | `#decW` |
|---|---|---|---|
| 0 | `learning` | `Learning the background` | `Measuring the empty floor and its noise before trusting any change.` |
| 40 | `watch` | `Watching` | `Noise, shake and light are inside limits; nothing above the noise floor.` |
| 116 | `watch` | `Watching` | `Shadow at 75° is 6.2σ above noise; not closing on the corner.` |
| 127 | `stop_vehicle` | `Stop the vehicle` | `Bearing 73° and falling 2°/s: the walker is heading for the corner line.` |
| 194 | `stop_vehicle` | `Stop the vehicle` | `Bearing 37° and falling 3°/s: the walker is heading for the corner line.` |
| 195 | `watch` | `Watching` | `Shadow at 39° is {sqrt(z).toFixed(1)}σ above noise; not closing on the corner.` |
| 335 | `relearn_background` | `Re-learn the background` | `Light changed since the background was learned.` |

Frame 194 is `present` on the alert card (`Bearing 37° and rising: they are walking away from the corner.`) while `#decision` still shows `Stop the vehicle` and a "falling" sentence. Frame 195 is the first later frame whose `q.a` is `watch`.

Check list `#checks` labels and formats (`CHECK`):

| Key | Label | Value format | Row is `.bad` when |
|---|---|---|---|
| `signal` | `Predicted range` | `{range_m.toFixed(1)} m`, or `–` | `range_m < 2.5` |
| `noise` | `Pixel noise` | `{noise_pct.toFixed(2)} %` | `noise_pct >= 2.5` |
| `shake` | `Camera shake` | `{shake_px.toFixed(2)} px` | `shake_px >= 0.6` |
| `drift` | `View drift` | `{drift_px.toFixed(1)} px` | `drift_px >= 3` |
| `exposure` | `Light change` | `+` or the minus sign, then `{offset_pct.toFixed(2)} %` | `abs(offset_pct) >= 1.5` |
| `clipping` | `Clipped pixels` | `{clip_pct.toFixed(2)} %` | `clip_pct >= 2` |
| `wedge` | `Wedge pixels` | `wedge_px.toLocaleString()` (no locale argument; en-US is `29,623`) | `wedge_px < 4000` |

Before any `q` exists, the only check row text is `Checks start once the background is learned`. At demo frame 40 the seven values are `5.2 m`, `1.58 %`, `0.01 px`, `0.0 px`, `-0.02 %`, `0.00 %`, `29,623` (en-US), and none of the `<li>` elements have class `bad`.

Decision log `#log` row templates (`buildLog`):

- leaving `learning`: `Background learned` · `noise floor measured; watching` (or `Background re-learned` if a log row already exists)
- enter `present` from anything except `coming`: `Shadow at {phi.toFixed(0)}°` · `someone is in the hidden hallway`
- enter `coming`: `STOP sent` · `closing on the corner at {phi.toFixed(0)}°`
- `present` after `coming`: `Moving away` · `bearing {phi.toFixed(0)}° and rising`
- `clear` after `present` or `coming`: `Corner clear` · `shadow below the noise floor`
- each `run.events` entry: `ACTION[action]` · `why`, timestamp `{(round(t * fps) / fps).toFixed(1)} s`

Demo event at `t` 16.75, `action` `relearn_background`: the log row's bold text is `Re-learn the background`, the reason is `lighting or exposure changed; the empty-hallway reference is stale`, and the time text is `16.8 s`. Clicking a log row sets `userPaused`, pauses, and seeks to that row's frame.

### Scores `#scores`

Heading `Scored against ground truth`.

When `run.score` is missing, `#scores` contains `No ground truth for this run` and `Score it with tools/score_footage.py and a second camera.`, and `#fine` is empty.

When `run.score` exists, the six labels and units are fixed; values use `score.far` for the first, second, and fifth, and `score.near` for the third, fourth, and sixth (`toFixed(1)` except recall percent `toFixed(0)` and false-alarm percent `toFixed(1)`):

| `dt` | demo `dd` number | `small` unit |
|---|---|---|
| `First detection` | `4.4` | `m from corner` |
| `Warning lead` | `2.1` | `s` |
| `Bearing error` | `2.1` | `° mean` |
| `Detected within 3 m` | `100` | `% of frames` |
| `False alarms` | `0.0` | `% empty frames` |
| `Bearing error p90` | `5.4` | `°` |

`#fine` for `scene.kind === "synthetic"` includes the text `Synthetic run`, then `, scored against the renderer's truth. Lead time is measured to the walker's closest point, 1.4 m from the corner. Real-footage scores come from a second camera in the hidden hallway (FILMING.md).` For any other kind: `Scored against a second camera filming the hidden hallway.`

### Publisher inside `web/index.html`

**unverified wip ff54829, confirm after the alert-feed task.**

`maybeAlert` posts only while `playing` and the frame index moved forward. It does not post during `learning` (`lastSent` is cleared). Mapping a test of the publisher demands:

| Frame `s` | POST `api/alerts` `state` | `level` |
|---|---|---|
| `learning` | no POST | |
| `clear` | `clear` | `null` |
| `present` | `someone` | `watch` |
| `coming` | `someone` | `stop` |

Duplicate `(state, level)` is not posted again. `confidence` is `min(1, log10(1 + z) / log10(401))` when `z > 0`, else `0`. `bearing_deg` is `null` when `state` is `clear` or `phi == null`. `t` is `f.t`, or `i / fps` when `t` is missing.

`KEEPALIVE_MS` is `1000`. While the floor video is advancing (`playing`, not paused, not ended, `readyState >= 3`), the page POSTs `api/alerts/status` with `{run, live: true, reason: "playing"}` on start and every 1000 ms. Pause / seek / switch / error / end POST `{live: false, reason}` with that reason string. `pagehide` while playing sends `reason: "closed"` with `keepalive: true`.

`#alert_token=` is read from the URL fragment, stored in `sessionStorage` key `alert_token`, and `history.replaceState` removes the fragment. Later posts send `Authorization: Bearer {token}`.

## 2. Synthetic label at 640px (fact; do not change CSS)

`PRODUCT.md` principle 4: `Synthetic is labelled synthetic.`

`DESIGN.md` Do: `label synthetic runs with the synthetic tag or in the run name.` The synthetic tag component is described as the only tag, labelling synthetic data.

In `web/index.html`, the block `@media (max-width: 640px)` contains both:

```css
.tag.synth { display: none; }
.transport .seg { display: none; }
```

A test at a viewport of 640px or narrower demands that `#kindTag.tag.synth` has computed `display: none` even after a synthetic load removes the `hidden` attribute. The same viewport demands the speed group (`.transport .seg`, buttons `0.5×` `1×` `2×`) has computed `display: none`.

At that width the demo `<option>` text is still `Synthetic corner · red top · lit hallway`, and `#sceneFoot` is still `Synthetic: per-pixel SNR 0.224 at 3 m · noise 2.29 DN · signal 0.513 DN`. Those two strings are the labels that remain on screen. This note does not change the CSS.

## 3. `web/calibrate.html`

Title: `Periscope · mark the tape`. H1: `Mark the tape`.

Lede includes `first_frame.png`, `tools/calibrate.py --frame-only`, `--marks`, `--gt-marks`, and the link `<a href="./">Back to the console</a>`. A test demands that anchor's `href` is `./` and its text is `Back to the console`.

Empty drop state, before any file: `#drop` is visible and its text is `No frame loaded yet.` plus `Choose an image, or drop one here.` `#cv` has the `hidden` attribute. `#copy` is `disabled`. `#out` value is `""`.

File input: `<input type="file" id="file" accept="image/*">` inside a label whose text is `Choose frame`. Dropping a file on `#stage` uses the same loader. A file whose `type` does not start with `image/` leaves the drop state unchanged.

After an image loads: `#cv` loses `hidden`, `#cv.width` / `#cv.height` equal the image's pixel size, `#drop` is `hidden`, and `pts` is reset to empty.

Mode group `aria-label` `Which camera`:

| Button | `data-mode` | Initial `aria-pressed` |
|---|---|---|
| `Corner camera` | `corner` | `true` |
| `Hidden hallway` | `gt` | `false` |

Corner list keys and descriptions, in order: `1` `corner`; `2` `wall, 50 cm`; `3` `wall, 100 cm`; `4` `90° line, 50 cm`; `5` `90° line, 100 cm`; `6` `diagonal (optional)`.

Hidden-hallway list: `A` `x −1, y 0.4`; `B` `x −1, y 1.6`; `C` `x −5, y 0.4`; `D` `x −5, y 1.6`. The minus signs in those four strings are U+2212 (`−`), not ASCII hyphens.

The next unmarked row has class `next`. Marked rows have class `done` and a third cell of `{x.toFixed(0)}, {y.toFixed(0)}`.

`#out` (readonly, `aria-label` `Mark string`) is the clicked points joined by spaces as `{x.toFixed(1)},{y.toFixed(1)}`.

`#copy` (`Copy marks`) stays `disabled` until 5 points in corner mode or 4 points in hidden-hallway mode. A 6th corner point is accepted (`diagonal (optional)`); further clicks are ignored once `pts.length` reaches the mode length (6 or 4).

`#undo` text is `Undo`. It removes the last point. With no points, `pop` leaves the list empty and `#copy` disabled.

Copy click, clipboard write resolves: button text becomes `Copied`, then after 1400 ms returns to `Copy marks`. Clipboard write rejects: `#out` is selected and the button text becomes `Press ⌘C`, then after 1400 ms returns to `Copy marks`.

Switching mode sets `aria-pressed="true"` on the clicked button only and clears every point.

## 4. HTTP routes (`server.py`)

Documented ports differ: `README.md` says `uvicorn server:app --port 8740`; the `server.py` docstring says port `8040`. The app object does not bind a port.

| Method and path | Observable result |
|---|---|
| `GET /api/health` | status 200, JSON `{"ok": true}` |
| `GET /api/runs` | status 200, JSON array. Each item has `id` (directory name), `title` (`run.json` `title`, or the directory name), `kind` (`run.json` `scene.kind`, or `"footage"`), `frames` (length of `frames`). Directories under `PERISCOPE_RUNS` (default `web/runs`) with no `run.json` are omitted. The demo entry is `{"id":"demo","title":"Synthetic corner · red top · lit hallway","kind":"synthetic","frames":380}`. |
| `POST /api/analyze` | multipart fields `video` (file), `calib` (string), `title` (default `Uploaded clip`). |
| `POST /api/alerts` | **unverified wip ff54829, confirm after the alert-feed task.** |
| `POST /api/alerts/status` | **unverified wip ff54829, confirm after the alert-feed task.** |
| `GET /api/alerts/stream` | **unverified wip ff54829, confirm after the alert-feed task.** |
| `GET /` | status 200, body is `web/index.html` (`FileResponse`). Title in that body: `Periscope · see who's coming around the corner`. |
| `GET /calibrate.html` | status 200 via the `StaticFiles` mount of `web/`. Title: `Periscope · mark the tape`. |

`POST /api/analyze` demands:

- `Calibration.from_json(calib)` raising (invalid JSON, missing fields, or any other exception): status 400, detail starts with `bad calibration:`. No `web/runs/up-*` directory is created, because the directory is made only after this `try`.
- Body larger than `MAX_BYTES = 500 * 1024 * 1024`: status 413, detail `clip too large (500 MB max)`. The `up-*` directory is deleted. A body of exactly 500 × 1024 × 1024 bytes is under the `size > MAX_BYTES` check.
- `read_video` or `export_run` raising `ValueError`: status 422, detail `str(e)`, directory deleted. `read_video` raises `ValueError` with text `cannot open video: {path}` when OpenCV cannot open the saved upload.
- Success: status 200, JSON `{"id": "up-"}` plus 8 hex characters. The directory `web/runs/{id}/` contains `run.json`, `floor.mp4`, `shadow.mp4`, and `spacetime.png`. `run.json` `scene.kind` is `"footage"` and `title` is the form title. The uploaded `input*` file is unlinked.

No control in `web/index.html` or `web/calibrate.html` calls `/api/analyze`. The fetches in `web/index.html` are `api/runs`, `runs/{id}/run.json`, `api/alerts/status`, and `api/alerts`. `web/calibrate.html` has no `fetch`.

`listRuns()` fallback, quoted again because a route test and a page test meet here:

```javascript
if (!runs.length) runs = [{ id: "demo", title: "Synthetic corner · red top · lit hallway" }];
```

### Alert feed routes

**unverified wip ff54829, confirm after the alert-feed task.**

These match the current `server.py` and `tests/test_alerts.py`. Re-read both after that task.

`POST /api/alerts/status` body: `run` (string 1–64 chars, or null), `live` (bool), `reason` one of `playing`, `paused`, `ended`, `seek`, `switched`, `closed`, `error`, or null. `live: true` with no `run` is 422, detail from `live status needs a run`. Success is 200 and the heartbeat object `{"t": <unix seconds>, "live": <bool>, "run": <id or null>, "age_s": <float or null>}`.

`POST /api/alerts` body: `run`, `state` `clear` or `someone`, `level` `watch` or `stop` or null, `bearing_deg` float or null, `confidence` in `[0, 1]`, `t` `>= 0`. `level` is required for `someone` and must be null for `clear`; otherwise 422, detail `level is required for someone and must be null for clear`. A `clear` alert is stored with `bearing_deg` forced to null. Success is 200 `{"sent": <bool>, "subscribers": <int>}`. `sent` is false when the `(state, level)` pair equals the last one for that run.

Not live, or `run` is not the live run: 409, detail `that run is not playing; post /api/alerts/status first`. `t` older than the last `t` in the live span: 409, detail `alert is older than the last one in this live span`.

`GET /api/alerts/stream`: status 200, `content-type` starts with `text/event-stream`, headers `Cache-Control: no-cache` and `X-Accel-Buffering: no`. First event is `event: heartbeat` with the heartbeat JSON. While a live alert exists, the next event is `event: alert` with the alert JSON. Later heartbeats arrive at least every `HEARTBEAT_S` (5.0 s in `server.py`; the tests patch it to 0.2). A subscriber that falls `QUEUE_MAX` (64) events behind gets `event: resync` whose data includes `reason` `subscriber too slow; reconnect`, then the stream ends.

`stale` data is `{"run", "reason", "t"}` with `reason` one of `paused`, `ended`, `seek`, `switched`, `closed`, `error`, `timeout`. `STALE_S` is 3.0 s.

Publisher trust, as the current tests assert:

- Client host other than `127.0.0.1` or `::1`, no `PERISCOPE_ALERT_TOKEN`: `POST /api/alerts/status` and `POST /api/alerts` are 403, detail `alerts can only be published from this machine (or set PERISCOPE_ALERT_TOKEN)`. `server.bus.live` stays false. `test_non_loopback_publisher_forbidden` demands `[403, 403]`.
- `PERISCOPE_ALERT_TOKEN=s3cret`: missing or wrong `Authorization` is 401, detail `alert token required`. `Authorization: Bearer s3cret` from a non-loopback client is 200. `test_token_required_when_set` demands `[401, 401, 200]`.
- `Origin` not equal to `{scheme}://{Host}`: 403, detail `cross-origin publisher refused`. `test_cross_origin_post_forbidden` posts `Origin: http://evil.example` and demands 403. `test_same_origin_post_allowed` demands 200 and `live: true`.
- `Content-Type: text/plain` on `POST /api/alerts`: 422. `test_bad_alert_rejected`.
- `WEB_CONCURRENCY=4`: `check_single_worker()` raises `RuntimeError` matching `single worker`. `WEB_CONCURRENCY=1` does not. `test_multi_worker_refused`.

`GET /api/alerts/stream` has no publisher check in `server.py`.

## 5. CLIs and what they write

### `tools/calibrate.py`

Positional `video`. Flags:

| Flag | Default | Effect |
|---|---|---|
| `--marks` | none | `"x,y x,y ..."` in protocol order, 5 or 6 marks |
| `--auto` | off | `detect_corner` |
| `--min-confidence` | `MIN_AUTO_CONFIDENCE` which is `0.5` | `--auto` refuses below this |
| `--frame-only` | off | write the frame and return |
| `--r-min` | `0.12` m with `--marks`; `0.054` fraction of the short side with `--auto` | wedge inner radius |
| `--r-max` | `1.0` m with `--marks`; `0.45` fraction with `--auto` | wedge outer radius |
| `--out` | the video path with its suffix removed | output directory |

The frame written is the frame at 0.5 s (`skip_s`). Unreadable video: process exit via `SystemExit`, stderr `cannot read {path}`.

`--frame-only` writes `{out}/first_frame.png` and stdout `wrote {path}`. It does not write `calib.json`.

`--marks` or `--auto` also writes `{out}/calib.json` (`Calibration.to_json()`) and `{out}/calib_preview.png`. Stdout is one JSON line `{"calib": ".../calib.json", "preview": ".../calib_preview.png"}`. `--auto` also prints, before that, `{"auto_confidence": <3 decimals>, "corner_px": [x, y]}`.

Neither `--marks` nor `--auto`: exit `give --marks or --auto`.

`--auto` with `--r-min` or `--r-max` greater than 1: exit `with --auto, --r-min/--r-max are fractions of the frame's short side (0-1)`.

`--auto` below confidence: exit `auto calibration refused ({reason}); click the tape marks and use --marks`, and `calib.json` is not written. `test_cli_auto_writes_calibration_or_refuses` demands return code 0 and `calib.json` `source == "auto"` and corner within 6 px on a synthetic floor clip; `--r-min 0.1 --r-max 0.3` demands `r_min ≈ 0.1 * short_side` and `r_max ≈ 0.3 * short_side`; a flat frame demands return code not 0, stderr containing `refused` and `--marks`, and no `calib.json`.

### `tools/score_footage.py`

| Flag | Default |
|---|---|
| `--corner` | required |
| `--calib` | required |
| `--gt` | required |
| `--gt-marks` | required, `"x,y x,y x,y x,y"` |
| `--gt-floor` | `-1,0.4 -1,1.6 -5,0.4 -5,1.6` |
| `--offset` | none; otherwise seconds added to the ground-truth clock. Omitted: `clap_offset`, and if that returns null the process prints `no audio clap found; assuming the clips start together (pass --offset to fix)` and uses 0 |
| `--out` | `results/take` |
| `--d-max` | `6.0` |

Writes:

- `{out}/score.json` with the `score_track` fields plus `offset_s`, `gt_fps`, `fps`. Fields: `frames`, `eval_frames`, `recall`, `false_alarm_rate`, `angle_mae_deg`, `angle_median_deg`, `angle_p90_deg`, and when any truth sample is finite also `first_detect_distance_m`, `lead_time_s`, `max_detect_distance_m`.
- `{out}/track.png`.
- `{out}/run/run.json`, `floor.mp4`, `shadow.mp4`, `spacetime.png` from `export_run`, then `run.json` is rewritten with `truth` (`phi`, `d`, `xy`) and `score`.
- Stdout is `json.dumps(sc, indent=1)` of the score object.

`test_score_footage_end_to_end` (marked `slow`) runs this on two synthetic clips it writes itself, with `--offset 0 --d-max 3`, and demands `score.json` `recall >= 0.8`, `angle_mae_deg < 8.0`, and that `track.png` and `run/run.json` exist.

### `tools/make_demo.py`

| Flag | Default |
|---|---|
| `--out` | `web/runs/demo` |
| `--fps` | `20` |
| `--noise` | `1.0` (docstring: `1` = phone in a lit room) |

Writes in `--out`: `run.json`, `floor.mp4`, `shadow.mp4`, `spacetime.png` (`export_run`), `hidden.mp4`, then `floor.webm`, `shadow.webm`, `hidden.webm` via `ffmpeg` libvpx-vp9 CRF 32. `run.json` `assets.hidden` is `hidden.mp4`, `scene.kind` is `synthetic`, `title` is `Synthetic corner · red top · lit hallway`. Stdout is the score JSON (`indent=1`) and a line `events: ` plus `run["events"]`.

`export_run` shadow video uses `amp_gain` 70, matching the console caption `shadow amplified 70×`.

### `tools/snr_sweep.py`

| Flag | Default |
|---|---|
| `--seeds` | `2` |
| `--quick` | off. On: noise multipliers `[1, 3, 8]`, first three clothing/light variants only, no H.264 CRF rows |
| `--out` | `results/` |

Full run noise multipliers: `0.5, 1, 1.5, 2, 3, 4, 6, 8, 12`. Pass rule in the file: recall ≥ 0.9 and angle MAE ≤ 6° within 3 m, `fa_empty == 0`, approach false-alarm rate < 0.02.

Writes `{out}/sweep.json`, `{out}/sweep.md`, `{out}/sweep.png`. Stdout includes one line per row and `signal floor (per-pixel SNR at 3 m): {floor}`. `sweep.json` keys: `snr_floor_3m`, `sweep`, `variants`, `seeds`, `criteria` (the string `recall >= 0.9 and angle MAE <= 6 deg within 3 m of the corner, zero false alarms on 14 s of empty hallway`).

Do not start this sweep for the audit. `results/sweep.json`, `results/sweep.md`, and `results/sweep.png` are already in the tree. `RESEARCH.md` says its table was read from `results/sweep.md` at 3 seeds per row; the CLI default is `--seeds 2`.

### `tools/bench.py`

No flags. Writes no file. Stdout is one JSON object with keys `machine`, `python`, `opencv`, `threads`, `ms_640x360_stabilised`, `ms_640x360_no_stab`, `ms_1080p_in_stabilised`, `ms_phase_correlate_640x360`, `ms_binning_640x360`. A test of the CLI demands those keys and that each `ms_*` value is a number. It does not demand the 4.2 / 0.4 / 4.3 / 2.6 / 0.22 figures; those are the past run quoted in `RESEARCH.md`.

## 6. Engine guarantees already encoded as tests

Names below are the test functions. Assertions are what those functions already `assert`.

### `tests/test_geometry.py`

- `test_marks_give_true_floor_angles`: for angles 5, 30, 45, 60, 85° and radii 0.3 and 0.8 m, `to_floor` angle error `< 0.2`° and radius error `< 0.01` m.
- `test_click_noise_costs_little_angle`: `click_noise_px=3`, max angle error over 9 angles from 5° to 85° at 0.6 m `< 4.0`°.
- `test_scaled_and_json_roundtrip`: `scaled(0.5)` matches `to_floor` within `atol=1e-6`; `Calibration.from_json(to_json())` matches; every point of `wedge_outline(8)` has radius inside `[r_min, r_max]` within `1e-6`.
- `test_auto_calibrate_finds_the_corner`: `auto_calibrate` `corner_px` within `< 10` px of the true corner; wall direction cosine `> cos(8°)`; the open side dots positive with the true 90° mark.

### `tests/test_autocalib.py`

- `test_corner_within_6px_across_snr`: noise scales `0.5, 1, 3, 4, 8, 12` × seeds `0, 1, 2` (18 cases). `detect_corner(...).ok` is true; corner error `<= 6.0` px; wall angle `< 8.0`°; open side dots positive with mark 4.
- `test_detection_is_a_usable_calibration`: `source == "auto"`, `H is None`, `image_size` equals the scene, `0 < r_min < r_max`, `confidence >= 0.5`, some note contains `auto`, wall-mark angle `abs(theta[2]) < 5.0`°, floor marks `theta` in `(0, 120)`, JSON round-trip matches `to_floor`.
- `test_no_corner_falls_back_with_a_reason`: ids `flat`, `noise`, `one-edge`, `clutter`. `ok` is false, `calibration is None`, `confidence < 0.5`, `reason` is truthy.
- `test_confidence_threshold_is_honoured`: `min_confidence=1.01` → not ok, `reason` starts with `low confidence`, `suggestion["corner_px"]` is not None.
- `test_cli_auto_writes_calibration_or_refuses`: see section 5.

### `tests/test_recon.py`

- `test_forward_matrix_is_cumulative`: `forward_matrix` on measured angles 0, 45, 90 against edges 0, 30, 60, 90. Row 0 is all 0. Row 1 in degrees is `[30, 15, 0]`. Row 2 in degrees is `[30, 30, 30]`.
- `test_inverse_recovers_a_hidden_object_and_ignores_global_light`: binner `n_pixels > 8000`; a hidden object planted at 41° plus a global `0.03` is recovered with peak `|x|` within `<= 2.5`° of 41, the global coefficient `b` within `atol=0.003` of 0.03, and the summed colour around that bin has red `> 0`, green `< 0`, blue `< 0`.
- `test_noise_prediction_matches_monte_carlo`: 400-draw std / `x_sigma` has mean ratio in `(0.85, 1.15)`.

### `tests/test_snr.py`

- `test_above_the_floor_tracks_the_hidden_person`: noise scales `1.0` and `3.0`. Within 3 m: `recall >= 0.9`, `angle_mae_deg <= 6.0`, `angle_p90_deg <= 12.0`. Out to 8 m: `false_alarm_rate == 0.0`, `first_detect_distance_m >= 2.5`, `lead_time_s >= 1.0`.
- `test_nominal_conditions_give_real_warning`: `scene.snr(3.0) == pytest.approx(0.21, abs=0.02)`, `first_detect_distance_m >= 3.5`, `lead_time_s >= 2.0`.
- `test_range_shrinks_as_noise_grows`: first-detection distance at noise 0.5 > noise 2 > noise 8 (missing distance counts as 0).
- `test_below_the_floor_fails_safe`: noise scale 12, `first_detect_distance_m` (or 0) `< 2.0`, `false_alarm_rate == 0.0`.
- `test_empty_hallway_raises_no_alarm`: noise `1.0` and `12.0`, 15 s empty. False-alarm fraction `== 0.0`, and no record has `coming` true.

### `tests/test_nuisance.py`

- `test_survives`: ids `shake-1px` (`shake_px=1`), `flicker-2pct` (`flicker=0.02`), `exposure-jump` (`exposure_step=0.05`). Within 3 m `recall >= 0.9` and `angle_mae_deg <= 6.0`. Approach out to 8 m `false_alarm_rate == 0.0`. 12 s empty hallway false-alarm fraction `== 0.0`.
- `test_shake_is_robust_across_seeds`: seeds `1` and `2`, `shake_px=1`. 14 s empty false-alarm fraction `== 0.0`. Approach out to 8 m `false_alarm_rate == 0.0`.
- `test_lamp_switch_makes_the_agent_relearn`: `exposure_step=0.05` at `exposure_at_s=6` on a 12 s empty clip. Some `eng.events` item has `action == "relearn_background"`. False-alarm fraction `== 0.0`.
- `test_without_stabilisation_shake_is_flagged`: `shake_px=1`, stabilisation off, 6 s empty. `assess()["metrics"]["shake_px"] > 0.6` and the check named `shake` has `ok is False`.

### `tests/test_agent.py`

`test_decisions_follow_the_numbers` demands `quality.assess(...)["action"]`:

| Input on top of the healthy base | `action` |
|---|---|
| base (`noise_pct=1.5`, `shake_px=0.05`, `drift_px=0.1`, `offset_pct=0`, `clip_pct=0`, `wedge_px=15000`, `range_m=4`, `coming=False`) | `watch` |
| `coming=True` | `stop_vehicle` |
| `drift_px=6` | `recalibrate` |
| `offset_pct=3` | `relearn_background` |
| `shake_px=1.5` | `steady_camera` |
| `range_m=1.2` | `add_light` |
| `wedge_px=1500` | `reframe` |

No test asserts `clip_pct`. In `assess`, `clip_pct >= 2` is a failing `clipping` check and shares the `relearn_background` branch with exposure.

- `test_every_decision_cites_its_evidence`: `assess(base(range_m=1.2))` has at least one check with `ok` false, and every such check has `value is not None` and a non-empty `detail`.
- `test_predicted_range_falls_with_noise`: `predicted_range_m(0.015, 15000) > predicted_range_m(0.06, 15000) > 0`, and the first value is in `(3.0, 6.0)`.
- `test_engine_reports_range_in_the_right_ballpark`: 4 s empty nominal scene, `metrics()["range_m"]` in `(3.0, 6.5)`; the same scene at `noise_scale=4` reports a smaller `range_m`.

### `tests/test_groundtruth.py`

- `test_second_camera_recovers_true_angle`: more than 100 frames with finite truth and estimate and distance `< 7.5` m. Median distance error `< 0.3` m. Median angle error `< 3.0`°. On frames where truth is not finite (skipping the first 5), the fraction of NaN estimates is `> 0.9`.
- `test_score_footage_end_to_end`: see section 5. Demands `recall >= 0.8`, `angle_mae_deg < 8.0`, `track.png` exists, `run/run.json` exists.

### `tests/test_alerts.py`

**unverified wip ff54829, confirm after the alert-feed task.** The function names and the assertions in this worktree:

- `test_state_change_is_emitted`: after status live on run `A`, an alert POST returns `{"sent": true, "subscribers": 1}`. The stream's `alert` event equals `{"run":"A","state":"someone","level":"watch","bearing_deg":41.5,"confidence":0.8,"t":1.0}`. A following `clear` event has `state` `clear`, `bearing_deg` null, `level` null.
- `test_duplicate_state_not_reemitted`: second POST with the same state and level, different bearing, returns `sent: false`. The next stream event after the first alert is `heartbeat`.
- `test_escalation_present_to_coming_emitted`: `level` `watch` then `level` `stop` both emit. The second event has `state` `someone` and `level` `stop`. A third identical `stop` returns `sent: false`.
- `test_heartbeat_carries_liveness`: connect heartbeat has `live` true, `run` `A`, `age_s` a float. The next event is `heartbeat` with `t` a float, and it arrives in under `2 * 0.2 + 0.3` seconds (tests patch `HEARTBEAT_S` to 0.2).
- `test_clean_disconnect`: one subscriber while the stream is open; zero after it closes; a later alert returns `subscribers == 0`.
- `test_bad_alert_rejected`: `state="maybe"` → 422; `confidence=1.5` → 422; `level=null` on `someone` → 422; `state="clear"` with `level="stop"` → 422; `content-type: text/plain` → 422.
- `test_pause_marks_alert_stale`: reasons `paused`, `ended`, `error`. After a live alert, `live: false` with that reason emits `stale` `{"run":"A","reason":<reason>,"t": approx now}` and the next event is `heartbeat` with `live` false. A subscriber that connects after that gets `live` false and then another `heartbeat`, not the old alert.
- `test_keepalive_timeout_marks_stale`: with `STALE_S` patched to 0.3, after one alert the stream emits `stale` with `reason` `timeout` in under 1.0 s.
- `test_run_switch_while_learning`: status for run `B` while `A` was live emits `stale` reason `switched` for run `A`. A new subscriber sees `live` true, `run` `B`, and the next event is `heartbeat`.
- `test_backward_t_rejected_and_seek_resets`: `t` 4.0 after `t` 5.0 returns 409. Status reason `seek` emits `stale` reason `seek`. After going live again, the same alert at `t` 4.0 returns `sent` true and the stream event has `t == 4.0`.
- `test_replay_from_ended_republishes`: reason `ended` emits `stale` reason `ended`. An alert before the next live status is 409. After live again, an alert at `t` 0.5 returns `sent` true and the event `t` is 0.5.
- `test_alert_requires_live_run`: alert with nothing playing is 409. Alert for run `B` while `A` is live is 409.
- `test_non_loopback_publisher_forbidden`, `test_token_required_when_set`, `test_cross_origin_post_forbidden`, `test_same_origin_post_allowed`, `test_multi_worker_refused`: see section 4.
- `test_overflowing_subscriber_closed`: with `QUEUE_MAX` 2, three publishes set `sub.overflow` and drop the subscriber. The stream's last chunk starts with `event: resync`.

## 7. Absences

- No on-chain client. No wallet, chain, or contract code. A search of `*.py`, `*.html`, `*.md`, `*.json`, `*.toml`, `*.yml`, and `*.txt` finds no `mcp`, `on-chain`, `blockchain`, or `wallet` hits. The only `http` hits outside docs and fonts are localhost in `README.md` and `server.py`, the SVG namespace, and the test origins `http://periscope.local` and `http://evil.example`.
- No MCP server. No MCP manifest or server module in the repo.
- No deployed URL of this app. `PRODUCT.md` says there are no deployments. `README.md` and `server.py` name `localhost` only (`8740` and `8040`). No `Dockerfile`, `fly.toml`, `vercel.json`, `netlify.toml`, or `AUDIT.md`. `RESEARCH.md` cites Devpost, AWS Marketplace, and paper URLs. Those are bibliography links, not a host for this server.
- External network from the pages: `web/index.html` lines 9–11 and `web/calibrate.html` lines 8–10 load Google Fonts stylesheets (`https://fonts.googleapis.com` and `https://fonts.gstatic.com`, CSS2 Geist and Geist Mono). The CornerCam PDF is a footer link in `web/index.html`, `href` `https://people.csail.mit.edu/klbouman/pw/papers_and_presentations/cornercam_iccv2017.pdf`, link text `CornerCam paper (ICCV 2017)`. No script fetches that PDF.
- Real footage: `FILMING.md` is the protocol. It tells the operator to copy takes to `data/raw/` (git-ignored) and then run `tools/calibrate.py` and `tools/score_footage.py`. `.gitignore` ignores `data/raw/`, `*.mp4`, and `*.mov`, with an exception for `web/runs/demo/*.mp4`. This worktree has no `data/` directory. The only videos present are the synthetic demo under `web/runs/demo/` (`floor`, `shadow`, `hidden` in mp4 and webm). `tools/score_footage.py` cannot be run on a real second camera from this repo, because no real take is in the tree. `test_score_footage_end_to_end` renders both clips itself.
- `FILMING.md` go gate, for when a real take exists: detected at ≥ 2 m from the corner on most passes, angle error under ~8°, empty take raises no alarm. Marginal: only within ~1.5 m, or only with the red top and all lights on. No-go: nothing above noise with a red top, bright hallway, and ProRes.
- `PRODUCT.md`: output is a 1-D angle, 0–90°, not a distance. Synthetic results exist; real-footage results do not. The limits section of `web/index.html` prints `Bearing, not distance`, `Needs light and a steady view`, and `Compression erases it`.
