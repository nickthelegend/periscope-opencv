---
name: Periscope
description: A dark monitoring console where every corner warning traces back to the floor shadow that caused it.
colors:
  bg: "#0a0c10"
  bg-2: "#0d1015"
  panel: "#11141a"
  panel-2: "#161a22"
  well: "#07090c"
  line: "#20252f"
  line-2: "#2c3340"
  ink: "#eceff4"
  ink-2: "#b3bac7"
  ink-3: "#8a93a3"
  accent: "#9b97ff"
  accent-2: "#b9b6ff"
  accent-ink: "#110f2b"
  clear: "#3ccf8e"
  present: "#f2b53c"
  coming: "#ff5b4f"
  stop: "#e5352b"
  stop-top: "#e8382d"
  stop-base: "#c42a21"
  alarm-tint: "#ff8a80"
  hall-floor: "#151a24"
  hall-wall: "#262c38"
  wall-line: "#6a7387"
  tape-blue: "#2f6fd6"
typography:
  stop-word:
    fontFamily: "Geist, system-ui, sans-serif"
    fontSize: "clamp(56px, 6.2vw, 92px)"
    fontWeight: 800
    lineHeight: 0.9
    letterSpacing: "-0.035em"
  display:
    fontFamily: "Geist, system-ui, sans-serif"
    fontSize: "clamp(34px, 4vw, 56px)"
    fontWeight: 600
    lineHeight: 1.02
    letterSpacing: "-0.03em"
  headline:
    fontFamily: "Geist, system-ui, sans-serif"
    fontSize: "clamp(26px, 2.6vw, 36px)"
    fontWeight: 600
    lineHeight: 1.08
    letterSpacing: "-0.025em"
  title:
    fontFamily: "Geist, system-ui, sans-serif"
    fontSize: "16px"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "-0.005em"
  body-large:
    fontFamily: "Geist, system-ui, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.55
  body:
    fontFamily: "Geist, system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.55
  body-dense:
    fontFamily: "Geist, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Geist, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.4
  label-small:
    fontFamily: "Geist, system-ui, sans-serif"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.4
  control:
    fontFamily: "Geist, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 600
    lineHeight: 1
  segment:
    fontFamily: "Geist, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 500
    lineHeight: 1
  readout:
    fontFamily: "Geist Mono, ui-monospace, SFMono-Regular, Menlo, monospace"
    fontSize: "26px"
    fontWeight: 500
    lineHeight: 1.15
    letterSpacing: "-0.02em"
    fontFeature: "tnum"
  readout-small:
    fontFamily: "Geist Mono, ui-monospace, SFMono-Regular, Menlo, monospace"
    fontSize: "12px"
    fontWeight: 500
    lineHeight: 1.3
    fontFeature: "tnum"
rounded:
  panel: "14px"
  well: "10px"
  control: "10px"
  strip: "8px"
  inner: "7px"
  chip: "6px"
  key: "5px"
  pill: "99px"
spacing:
  control-gap: "10px"
  well-inset: "12px"
  panel-gap: "16px"
  panel-pad: "18px"
  gutter: "28px"
  gutter-compact: "14px"
  section: "72px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.accent-ink}"
    typography: "{typography.control}"
    rounded: "{rounded.control}"
    padding: "0 16px"
    height: "38px"
  button-primary-hover:
    backgroundColor: "{colors.accent-2}"
  button-secondary:
    backgroundColor: "{colors.panel-2}"
    textColor: "{colors.ink}"
    typography: "{typography.control}"
    rounded: "{rounded.control}"
    padding: "0 16px"
    height: "38px"
  button-icon:
    backgroundColor: "{colors.panel-2}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    size: "38px"
  segmented:
    backgroundColor: "{colors.well}"
    rounded: "{rounded.well}"
    padding: "3px"
  segmented-option:
    textColor: "{colors.ink-3}"
    typography: "{typography.segment}"
    rounded: "{rounded.inner}"
    padding: "0 11px"
    height: "28px"
  segmented-option-active:
    backgroundColor: "{colors.panel-2}"
    textColor: "{colors.ink}"
  status-pill:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.ink}"
    typography: "{typography.control}"
    rounded: "{rounded.pill}"
    padding: "0 16px"
    height: "36px"
  status-pill-stop:
    backgroundColor: "{colors.stop}"
    textColor: "#ffffff"
  run-select:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.ink}"
    typography: "{typography.body-dense}"
    rounded: "{rounded.pill}"
    padding: "0 14px"
    height: "36px"
  tag-synthetic:
    backgroundColor: "rgba(155,151,255,.08)"
    textColor: "#dcdaff"
    typography: "{typography.segment}"
    rounded: "{rounded.pill}"
    padding: "0 11px"
    height: "28px"
  panel:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.ink}"
    rounded: "{rounded.panel}"
    padding: "{spacing.panel-pad}"
  well:
    backgroundColor: "{colors.well}"
    rounded: "{rounded.well}"
  hud-chip:
    backgroundColor: "rgba(7,9,12,.74)"
    textColor: "{colors.ink}"
    typography: "{typography.readout-small}"
    rounded: "{rounded.chip}"
    padding: "4px 8px"
  wipe-handle:
    backgroundColor: "#ffffff"
    textColor: "{colors.panel}"
    rounded: "{rounded.pill}"
    size: "36px"
  alert-card:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.ink}"
    typography: "{typography.headline}"
    rounded: "{rounded.panel}"
    padding: "18px 20px"
  alert-card-stop:
    backgroundColor: "{colors.stop-base}"
    textColor: "#ffffff"
    typography: "{typography.stop-word}"
  field-mono:
    backgroundColor: "{colors.well}"
    textColor: "{colors.ink}"
    typography: "{typography.readout-small}"
    rounded: "{rounded.control}"
    padding: "10px"
---

# Design System: Periscope

## Overview

**Creative North Star: "The Evidence Console"**

Periscope is the category-standard monitoring console, played straight and finished to the bar of Linear, Vercel, Grafana and Waymo-style perception views. Near-black panels carry the instruments: the floor camera with its calibrated wedge and a camera/shadow wipe, a plan-view corner map with a protractor, a spacetime strip, the alert, the agent's reasoning and the scores. Every view runs on the same clock, so any warning can be followed back to the shadow on the floor that caused it. The interface's job is to make a 0.3% change in floor brightness readable and believable, from a judge's distance, without anyone touching it: the run starts on its own and loops.

The system is dense but quiet. Panels sit edge to edge on a 16px gap and are separated by hairlines. Data sits in recessed wells. Type is steady and never smaller than 12px, and colour carries meaning instead of decoration. The only loud thing on the page is STOP. When someone is coming, the alert card and the header status pill go solid red and the word STOP appears at poster size. It is the single moment the console raises its voice. Indigo is Periscope's own ink, for whatever the system drew or computed. Green, amber and red describe the corner and nothing else. Geist Mono, with tabular figures, appears only where a number is a measurement.

The secondary tool pages (calibration) use the same tokens with fewer parts: the panel recipe without the gradient, the same segmented control, buttons and wells. A new surface should look like another panel in the same console, not like a separate site.

**Key Characteristics:**
- Dark only (`color-scheme: dark`), on a cool blue-black neutral ramp.
- Hairline borders (1px) do the structural work; there is almost no shadow.
- Recessed wells hold every video, canvas, map and diagram.
- One indigo system accent, plus a three-colour state triad reserved for corner state.
- One sanctioned solid fill: STOP red, on the alert card and the status pill, only while someone is coming.
- Geist for language, Geist Mono for measurements; a 12px legibility floor.
- Motion only on state change and playback; reduced motion turns it all off, including autoplay.

## Colors

A cool blue-black graphite ramp with one indigo voice for the system, a strictly reserved green/amber/red triad for what is happening at the corner, and one solid STOP red.

### Primary
- **Wedge Indigo** (accent): the system's own marks. It is used for the calibrated floor wedge and corner point on the camera overlay, the wedge and protractor arc on the plan, the shadow-strength trace, the HUD recording dot, the alert progress bar, the focus ring, text selection (at 34% alpha) and the primary button fill.
- **Bearing Lilac** (accent-2): the lighter step of the same hue, for the measured bearing (the plan's bearing ray, its protractor fill and the protractor ticks, and the tracked line in the spacetime strip), links, the agent's decision icon, the highlighted half of the hero line and primary-button hover.
- **Indigo Ink** (accent-ink): text on an indigo fill. It appears only on the primary button.

### Secondary
The corner-state triad. These are not accent colours. Each one means one state of the hidden hallway.
- **Clear Green** (clear): hallway empty and signal readable. Used for the status dot and for passing signal checks.
- **Caution Amber** (present): someone is present but not closing, or a signal check is failing. It tints the alert card (45% border, 10% wash) and its progress bar, marks the agent's corrective actions (relearn, add light, steady the camera, recalibrate), and draws the dashed detection threshold on the shadow-strength trace. Its light tint (#f6cf7d) sets amber log text.
- **Alarm Red** (coming): someone is coming around the corner, as a line or a mark. Used for the bearing ray on camera and plan, the plan's protractor fill and bearing cone (30% wash), the alarm segment of the spacetime track and the stop-vehicle decision icon. Its light tint (#ffb3ad) sets warning text in the agent panel and the log.

### Tertiary: STOP
The fill family for the one state that is allowed to take over a surface.
- **Stop Red** (stop): the solid fill of the header status pill in the coming state, and the base hue of the plan's "in view" zone (32% wash) and its legend key.
- **Stop Red, top and base** (stop-top to stop-base): the 180° gradient that fills the alert card in the coming state. The deeper base keeps white text readable.
- **Alarm Tint** (alarm-tint): the light red that edges the STOP card (its 1px border) and recolours the plan's large bearing readout while someone is coming.

### Neutral
- **Night Console** (bg): page ground; the body background and the canvas fill behind HUD text halos.
- **Panel Floor** (bg-2): the lower stop of the panel's vertical gradient, so panels darken slightly toward their base.
- **Graphite Panel** (panel): panel surface, the status pill at rest and the run selector.
- **Raised Graphite** (panel-2): raised controls: secondary buttons, the active segment and row hover in the decision log.
- **Instrument Well** (well): the recessed surface under every video, canvas, diagram and mono field. It is the darkest value in the system.
- **Hairline** (line): the default 1px border for panels, wells, header and footer rules, readout dividers and dashed list rows.
- **Strong Hairline** (line-2): borders on interactive controls (buttons, tags, keycaps, the textarea), the map well, and the scrollbar thumb.
- **Signal White** (ink): primary text, readout numbers and the time cursor. It is also the tracked shadow edge on the camera overlay and the wipe divider, drawn white for contrast with the floor.
- **Instrument Grey** (ink-2): body copy, secondary values, the clock, plan labels. Lightened for legibility at distance.
- **Quiet Grey** (ink-3): captions, units, dt labels, axis ticks, legend text, inactive segments. The "learning" state uses this same grey, so learning has no hue of its own.

### Plan materials
The corner map draws the physical world in its own greys so walls read as solid at a glance.
- **Hallway Floor** (hall-floor): walkable floor in the plan view.
- **Wall Block** (hall-wall): solid wall mass in the plan and in the how-it-works diagram; the plan's large bearing readout sits inside it.
- **Wall Edge** (wall-line): the drawn wall outline in the plan and diagram.
- **Tape Blue** (tape-blue): the colour of the physical calibration tape crosses on the floor. It appears only as the legend key that names them in the camera view. It is a scene material, not an accent.

### Named Rules
**The Reserved Triad Rule.** Green, amber and red mean corner state (clear, present, coming) and nothing else: no branding, no decorative tints, no category colours. If a colour has to say something that isn't corner state, it is indigo or a neutral.

**The System Ink Rule.** Indigo marks what Periscope itself measured or drew: the wedge, the corner, the protractor, the bearing, the track. When the alarm fires, the bearing switches from lilac (or white on camera) to Alarm Red. It does not get a third colour.

**The Washes, Not Fills Rule.** A state colour fills an area only as a low-alpha wash (10–32%: the present alert card, the plan's bearing cone, the "in view" zone). Full-strength state colour is kept for dots, rays, arcs, borders and traces. STOP is the single sanctioned exception: in the coming state, and only then, the alert card and the header status pill fill solid Stop Red with white text. No other surface, state or component takes a solid state fill.

## Typography

**Display Font:** Geist (with system-ui, sans-serif)
**Body Font:** Geist (with system-ui, sans-serif)
**Label/Mono Font:** Geist Mono (with ui-monospace, SFMono-Regular, Menlo, monospace)

**Character:** One neutral grotesk is set tight at the top of the scale and relaxed in body text. Its mono sibling is kept for numbers that measure something, so a reader can tell a measurement from prose at a glance.

### Hierarchy
The working ramp is five steps (12 / 13 / 14 / 15 / 16px), with display sizes above it (26px readouts, the 26–36px headline, the 34–56px thesis, the 56–92px STOP word).
- **Stop Word** (800, clamp(56px, 6.2vw, 92px), 0.9, -0.035em, white): the word STOP on the alert card in the coming state. Nothing else uses it.
- **Display** (600, clamp(34px, 4vw, 56px), 1.02, -0.03em, `text-wrap: balance`): the single thesis line at the top of the console. Use one per surface.
- **Headline** (600, clamp(26px, 2.6vw, 36px), 1.08, -0.025em): section statements ("how it works"). The alert's state line runs at clamp(26px, 2.3vw, 34px), and steps down to clamp(22px, 1.9vw, 28px) under the STOP word. Tool pages use a fixed 28px headline.
- **Title** (600, 16px, -0.005em): panel headings, the agent's decision and the limits headings. A 13px Quiet Grey caption follows on the same baseline to say what the panel shows ("plan view, bearing from the corner").
- **Body Large** (400, 16px, 1.55): the intro lede and the long-form explanation, at 60–62ch.
- **Body** (400, 15px, 1.55): alert explanation, how-it-works steps, limits text.
- **Body Dense** (400, 14px): panel text in Instrument Grey (checks, log, the evidence footnote, the decision reason), and the run selector.
- **Label** (400, 13px, Quiet Grey): captions, legends, alert dt labels, the map note, footer. Sentence case, never tracked uppercase.
- **Label Small** (12px): the floor. Keyboard hints, keycaps, wipe labels (600, white), HUD chips and canvas axis ticks. Nothing renders smaller.
- **Control** (600, 14px): buttons and the status pill.
- **Segment** (500, 13px): segmented-control options and the synthetic tag.
- **Readout** (Geist Mono 500, 26px, 1.1–1.15, -0.02em, tabular figures): the headline numbers in the alert and evidence panels (21–22px under 640px). The unit follows in Geist at 14px, Quiet Grey.
- **Readout Small** (Geist Mono 500, 12–14px, tabular figures): HUD chips, keycaps, canvas axis ticks and overlay angle labels (12px), log timestamps and check values (13px), the transport clock (14px). The plan's bearing readout is the one large mono label: 600 weight, white, sized to the wall block it sits in.

### Named Rules
**The Measurement Mono Rule.** If a string is a measurement (bearing, seconds, σ, metres, pixel coordinates), set it in Geist Mono with `tabular-nums` so values hold still while they update. Words stay in Geist, including words inside a mono-heavy panel.

**The Small Unit Rule.** A unit sits beside its number, smaller (14px next to a 26px readout) and in Quiet Grey. The number carries the weight.

**The Legibility Floor Rule.** No text is set below 12px, in HTML or canvas. Anything a judge must read from a distance (alert text, readouts, panel titles, the status) sits at 14–16px or larger. Labels at 12–13px use Quiet Grey or brighter, never a dimmer tone.

## Layout

The console is a two-column instrument grid inside a 1480px container with a 28px gutter (14px under 640px). Tool pages use a 1180px container. The upper grid splits 1.12fr : 1fr. The floor camera is the left column, and the alert card and corner map stack on the right. The spacetime strip runs the full width below them, and the agent and evidence panels repeat the 1.12 : 1 split. Panels sit 16px apart. Wells are inset 12px from their panel's edge. Panel headers pad 12px top, 14px right, 18px left and are at least 48px tall; legends, checklists and readout grids keep the same 18px side padding. Controls inside headers and transport rows sit 10px apart. Long-form explanation follows 72px below the console in a 0.9 : 1.1 split, then a three-column limits row and a footer, each opened by a hairline.

Responsive behaviour collapses rather than reflows. Above 1700px the spacetime strip grows from 220px to 250px. At 1080px both grids go to one column, and the floor panel reorders so the transport sits above the camera, which keeps Play within reach. At 640px the gutter tightens to 14px, panel captions drop under their titles, readouts shrink to 21–22px, keyboard hints, the speed control and the synthetic tag hide, the status pill moves beside the wordmark, the map well deepens (10.4 : 5.6), the spacetime strip drops to 180px and the decision log moves under the checks. The calibration tool's grid (1fr + 320px rail) collapses at 860px.

### Named Rules
**The One Clock Rule.** Every view registers to one frame index: both floor videos and the overlay, the plan's bearing and protractor, the spacetime cursor, the shadow-strength cursor, the alert readouts and the decision log (future entries fade to 42%). Any new view of run data takes its time from the same cursor and scrubs with it.

**The Wedge-First Rule.** The floor camera is the largest panel and reads first, because it holds the evidence. Derived views (map, spacetime, scores) are always smaller and placed after it.

**The Kiosk Rule.** The console plays itself. A run autoplays on load and loops 2.5s after it ends, until someone pauses it. Autoplay is off under `prefers-reduced-motion` and with `?autoplay=0`; a user pause always wins.

## Elevation & Depth

Mostly flat, with depth from tone. Panels lift off the page by a near-invisible recipe: a 180° gradient from Graphite Panel to Panel Floor, a 1px top inner highlight at 3.5% white, and a 2px drop shadow. Data surfaces go the other way. They sink into Instrument Well (the map sits on its own near-well #0b0e14 so the hallway floor and walls can read above it), behind a hairline. The page ground carries one faint indigo glow at the top right (7%), which turns to a 14% red glow while someone is coming. Only three things rise above the panel plane: the STOP card, the wipe handle, and the HUD chips (a 6px backdrop blur over video).

### Shadow Vocabulary
- **Panel** (`box-shadow: 0 1px 0 rgba(255,255,255,.035) inset, 0 2px 4px rgba(0,0,0,.3)`): every panel.
- **STOP lift** (`box-shadow: 0 10px 28px -12px rgba(0,0,0,.7)` added to Panel): the alert card in the coming state only.
- **Wipe handle** (`box-shadow: 0 4px 12px rgba(0,0,0,.45)`): the white drag handle on the camera/shadow divider.
- **Active segment** (`box-shadow: 0 1px 0 rgba(255,255,255,.05) inset, 0 1px 2px rgba(0,0,0,.4)`): the pressed option in a segmented control.
- **State halo** (`box-shadow: 0 0 0 3px <state colour at 18–20%>`): the ring around a status dot at rest.

### Named Rules
**The Wells Sink Rule.** Anything that shows signal (video, canvas, plan, diagram, coordinate field) sits in a well darker than its panel. Panels rise slightly and data sinks. Panels never nest inside panels.

**The State-Only Motion Rule.** Motion marks state changes and playback. Transitions run 150–350ms on `cubic-bezier(.16, 1, .3, 1)`. Entering STOP plays a 0.6s scale settle (0.985 → 1.012 → 1) once. The 1s white ping loops only while someone is coming, and the HUD recording dot blinks only while the run is playing. `prefers-reduced-motion` removes all animation and transitions.

## Shapes

Softly rounded, nested radii that step down as you go inward: panels 14px, wells, segment tracks and buttons 10px, the shadow-strength strip 8px, segment options and log rows 7px, HUD chips, the map note and the focus ring 6px, keycaps 5px. Header-level status items (the run selector, the status pill, the synthetic tag) and the wipe labels are full pills, so they read as state rather than panel content; the wipe handle is a full circle. Borders are always 1px. Dashed hairlines divide checklist and tape-mark rows, and solid hairlines divide everything else. Keycaps take a 2px bottom border. Map and diagram geometry is drawn with thin strokes. Truth is dashed, and Periscope's estimate is solid.

### Named Rules
**The Truth Is Dashed Rule.** Ground truth and thresholds draw dashed at reduced opacity (the true-position ring on the plan, the truth trace, the 4.9σ line, the calibrated angle rays). Periscope's own estimate draws solid. A reader always knows which line is the camera and which is the referee.

## Components

### Buttons
Compact and tactile, with a 38px row height on the console.
- **Shape:** gently rounded (10px), 1px border.
- **Primary:** Wedge Indigo fill and border, Indigo Ink text, Control type, 0 16px padding, a 118px minimum width so Play/Pause/Replay don't resize, optional 16px SVG icon with an 8px gap. There is one per surface (Play run, Copy marks).
- **Hover / Focus:** primary lightens to Bearing Lilac. Every button presses to `scale(.97)` on 150ms expo-out. Focus is a 2px Wedge Indigo outline offset 2px. Disabled drops to 45% opacity with a not-allowed cursor.
- **Secondary:** Raised Graphite fill, Strong Hairline border, Signal White text. Hover deepens to #1b2029 with a #3d4556 border.
- **Icon:** the secondary button squared to 38×38 with a single 16px line icon (1.8 stroke, round caps).

### Segmented control
The console's standard view switcher (Split / Camera / Shadow ×70, Plan / Hidden hallway, speed, Track / Truth, camera mode).
- **Style:** Instrument Well track, Hairline border, 10px radius, 3px padding, 2px gap. Options are 28px tall, Segment type, Quiet Grey.
- **State:** the pressed option (`aria-pressed="true"`) takes Raised Graphite with Signal White text and the active-segment shadow. Hover brightens text to Signal White.

### Status pill and tags
- **Status pill:** 36px pill on Graphite Panel with a Hairline border, Control type. A 9px dot carries the state colour inside a 3px halo; present adds a 50% amber border. In the coming state the whole pill fills solid Stop Red, the text goes white with 0.04em tracking, and the dot turns white and pings. It doubles as the live region.
- **Synthetic tag:** 28px pill, Segment type in pale indigo on an 8% indigo wash with a 40% indigo border. It labels synthetic data and is the only tag in the system.

### Cards / Containers
- **Corner Style:** 14px.
- **Background:** Graphite Panel fading to Panel Floor (180° gradient). Tool pages use flat Graphite Panel.
- **Shadow Strategy:** the Panel shadow only (see Elevation & Depth).
- **Border:** 1px Hairline.
- **Internal Padding:** 18px horizontally; content wells inset 12px.

### Inputs / Fields
- **Run selector:** a pill-shaped native select (36px, Graphite Panel, Hairline border, 14px) with a drawn chevron. Focus-within turns the border Wedge Indigo.
- **Mono field:** Instrument Well background, Strong Hairline border, rounded corners, 10px padding, mono type. Used for machine-readable output such as mark strings.

### Navigation
A single header row: a wordmark (a 30px rounded-square glyph of the wall corner with indigo rays, then PERISCOPE at 17px/700 with 0.2em tracking), followed by the run selector, the synthetic tag and the status pill. The row is closed by a Hairline rule. Tool pages link back to the console inline in their lede.

### Alert card (signature)
The console's verdict. It is a panel with 18px × 20px padding. A Headline-scale state line is led by a 12px state dot. One sentence of Instrument Grey explanation at 15px follows, at a fixed minimum of two lines so the card doesn't jump. Below that, a three-up readout row (Bearing, In view in, Shadow strength) uses 13px Label dt over Readout dd, with columns split by hairlines. A 3px progress bar runs along the bottom edge (indigo, amber when present).
- **Present:** amber border at 45% and a 10% → 2% amber wash.
- **Coming (STOP):** the card fills with the Stop Red gradient behind an Alarm Tint border and lifts with the STOP shadow. The Stop Word "STOP" appears above the state line in white. All text turns white (explanation at 92%, labels and units at 82%), the dividers go 30% white, the progress bar turns white on a 20% black track, the dot turns white and pings, and the card plays its scale settle once.

### Floor camera with wipe (signature)
Two synced videos fill one 4:3 well: the ordinary camera and the floor shadow amplified 70×. The default Split view stacks them behind a draggable vertical divider (a 2px 85%-white line with a 36px white circular handle carrying a dark double chevron), clipped at 4–96%. The handle is a keyboard slider (arrow keys move it 5%). Pill labels ("Camera", "Shadow ×70", 12px/600 white on a 70% blurred well chip) sit at the top corners. Camera and Shadow ×70 show one video full-frame and hide the divider. The overlay canvas draws over both: the indigo wedge (10% fill, 95% stroke), dashed 25% white 15° rays, 12px mono angle labels with a dark halo, the bearing ray (white, Alarm Red in STOP) and the indigo corner point. HUD chips sit bottom-left. The legend under the panel keys the wedge (indigo), the shadow edge (white) and the calibration tape marks (Tape Blue).

### Corner map (signature)
A plan view of the corner in its own 10.4 : 4.9 well with a Strong Hairline border. Hallway Floor and Wall Block shapes are outlined in Wall Edge over a 4.5%-white metre grid, with 13px Instrument Grey labels and mono metre marks. A protractor arc (35% indigo) with ticks every 15° (longer at 0°, 45° and 90°) sits in the hidden quadrant; the measured bearing fills the arc from 0° to the bearing in Bearing Lilac, or Alarm Red in STOP, along with a 6° bearing cone and a bright ray. A large mono bearing readout ("64°") sits inside the wall block above a "bearing from the corner" label. In STOP the "in view" zone fills with a 32% Stop Red wash. The true position draws as a dashed white ring. The legend under the map keys the bearing (lilac), the true-position ring (dashed) and the zone (red key). The Hidden hallway segment swaps the plan for the ground-truth video with a note that Periscope never sees it.

### Readout list and decision log
Evidence and agent panels share one row grammar. A 14px Quiet Grey dt over a Readout dd in a two-column grid with hairline dividers. A checklist row has an 8px state dot, a 14px label, and a right-aligned 13px mono value over dashed hairlines. Log rows have a 54px mono timestamp column, then a bold action and its reason at 14px. Log rows are clickable to seek (Raised Graphite hover, 7px radius), and future rows fade.

## Do's and Don'ts

### Do:
- **Do** put every video, canvas, map and diagram in a well with a 1px border and a 10px radius, inset 12px inside its panel.
- **Do** set every measurement in Geist Mono with tabular figures, with its unit smaller and in Quiet Grey beside it.
- **Do** give each panel a Title-scale heading plus a one-line Quiet Grey caption saying what the view shows.
- **Do** keep text at 12px or larger, and judge-critical text (alert, readouts, titles, status) at 14–16px or larger.
- **Do** draw ground truth and thresholds dashed and Periscope's estimate solid.
- **Do** tie every new run-data view to the shared time cursor, so scrubbing one scrubs all.
- **Do** put a legend under any panel that draws keyed marks, with a swatch for each.
- **Do** label synthetic runs with the synthetic tag or in the run name.
- **Do** keep one primary (Wedge Indigo) button per surface.
- **Do** keep autoplay off under reduced motion and when `?autoplay=0` is set.

### Don't:
- **Don't** use green, amber or red for anything but corner state: no decorative glows, category colours or brand moments in the triad.
- **Don't** fill a surface with solid state colour anywhere except the STOP alert card and the STOP status pill. Every other state surface is a wash at 32% or less.
- **Don't** put text on the STOP fill in anything but white or near-white, and don't set it below 14px.
- **Don't** set measurements in proportional Geist, or set prose in Geist Mono.
- **Don't** nest a panel inside a panel. Inner structure is wells, hairlines and dashed rows.
- **Don't** animate anything that isn't a state change or playback, and don't loop motion outside the coming state and a playing run.
- **Don't** introduce a light theme or a second accent hue. The console is dark-only with one system voice; Tape Blue keys a physical material, not a UI accent.
