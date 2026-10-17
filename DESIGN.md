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
  ink-2: "#a9b1bf"
  ink-3: "#7b8494"
  accent: "#9b97ff"
  accent-2: "#b9b6ff"
  accent-ink: "#110f2b"
  clear: "#3ccf8e"
  present: "#f2b53c"
  coming: "#ff5b4f"
typography:
  display:
    fontFamily: "Geist, system-ui, sans-serif"
    fontSize: "clamp(32px, 4.2vw, 54px)"
    fontWeight: 600
    lineHeight: 1.02
    letterSpacing: "-0.03em"
  headline:
    fontFamily: "Geist, system-ui, sans-serif"
    fontSize: "clamp(24px, 2.6vw, 34px)"
    fontWeight: 600
    lineHeight: 1.08
    letterSpacing: "-0.025em"
  title:
    fontFamily: "Geist, system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "-0.005em"
  body:
    fontFamily: "Geist, system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: "Geist, system-ui, sans-serif"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.4
  control:
    fontFamily: "Geist, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 500
    lineHeight: 1
  readout:
    fontFamily: "Geist Mono, ui-monospace, SFMono-Regular, Menlo, monospace"
    fontSize: "22px"
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
  control: "9px"
  inner: "7px"
  chip: "6px"
  pill: "99px"
spacing:
  control-gap: "10px"
  well-inset: "12px"
  panel-pad: "16px"
  panel-gap: "16px"
  gutter: "24px"
  gutter-compact: "14px"
  section: "64px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.accent-ink}"
    typography: "{typography.control}"
    rounded: "{rounded.control}"
    padding: "0 14px"
    height: "34px"
  button-primary-hover:
    backgroundColor: "{colors.accent-2}"
  button-secondary:
    backgroundColor: "{colors.panel-2}"
    textColor: "{colors.ink}"
    typography: "{typography.control}"
    rounded: "{rounded.control}"
    padding: "0 14px"
    height: "34px"
  button-icon:
    backgroundColor: "{colors.panel-2}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    size: "34px"
  segmented:
    backgroundColor: "{colors.well}"
    rounded: "{rounded.well}"
    padding: "3px"
  segmented-option:
    textColor: "{colors.ink-3}"
    typography: "{typography.control}"
    rounded: "{rounded.inner}"
    padding: "0 10px"
    height: "26px"
  segmented-option-active:
    backgroundColor: "{colors.panel-2}"
    textColor: "{colors.ink}"
  status-pill:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.ink}"
    typography: "{typography.control}"
    rounded: "{rounded.pill}"
    padding: "0 14px"
    height: "34px"
  run-select:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.ink}"
    typography: "{typography.control}"
    rounded: "{rounded.pill}"
    padding: "0 12px"
    height: "34px"
  tag-synthetic:
    backgroundColor: "rgba(155,151,255,.08)"
    textColor: "#d9d7ff"
    rounded: "{rounded.pill}"
    padding: "0 10px"
    height: "26px"
  panel:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.ink}"
    rounded: "{rounded.panel}"
    padding: "{spacing.panel-pad}"
  well:
    backgroundColor: "{colors.well}"
    rounded: "{rounded.well}"
  hud-chip:
    backgroundColor: "rgba(7,9,12,.72)"
    textColor: "{colors.ink}"
    typography: "{typography.readout-small}"
    rounded: "{rounded.chip}"
    padding: "3px 7px"
  alert-card:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.ink}"
    typography: "{typography.headline}"
    rounded: "{rounded.panel}"
    padding: "18px 18px 16px"
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

Periscope is the category-standard monitoring console, played straight and finished to the bar of Linear, Vercel, Grafana and Waymo-style perception views. Near-black panels carry the instruments: the floor camera with its calibrated wedge, a plan-view map, a spacetime strip, the alert, the agent's reasoning and the scores. Every view runs on the same clock, so any warning can be followed back to the shadow on the floor that caused it. The interface's job is to make a 0.3% change in floor brightness readable and believable.

The system is dense but quiet. Panels sit edge to edge on a 16px gap and are separated by hairlines. Data sits in recessed wells. Type stays small and steady, and colour carries meaning instead of decoration. The only loud thing on the page is the alarm, and it is loud only while someone is actually coming. Indigo is Periscope's own ink, for whatever the system drew or computed. Green, amber and red describe the corner and nothing else. Geist Mono, with tabular figures, appears only where a number is a measurement.

The secondary tool pages (calibration) use the same tokens with fewer parts: the panel recipe without the gradient, the same segmented control, buttons and wells. A new surface should look like another panel in the same console, not like a separate site.

**Key Characteristics:**
- Dark only (`color-scheme: dark`), on a cool blue-black neutral ramp.
- Hairline borders (1px) do the structural work; there is almost no shadow.
- Recessed wells hold every video, canvas, map and diagram.
- One indigo system accent, plus a three-colour state triad reserved for corner state.
- Geist for language, Geist Mono for measurements.
- Motion only on state change; reduced motion turns it all off.

## Colors

A cool blue-black graphite ramp with one indigo voice for the system and a strictly reserved green/amber/red triad for what is happening at the corner.

### Primary
- **Wedge Indigo** (accent): the system's own marks. It is used for the calibrated floor wedge and corner point on the camera overlay, the wedge on the plan, the bearing ray while the corner is not in alarm, the shadow-strength trace, the alert progress bar, the focus ring, text selection (at 34% alpha) and the primary button fill.
- **Bearing Lilac** (accent-2): the lighter step of the same hue, for the tracked bearing line in the spacetime strip, links, the agent's decision icon, the highlighted half of the hero line and primary-button hover.
- **Indigo Ink** (accent-ink): text on an indigo fill. It appears only on the primary button.

### Secondary
The corner-state triad. These are not accent colours. Each one means one state of the hidden hallway.
- **Clear Green** (clear): hallway empty and signal readable. Used for the status dot and for passing signal checks.
- **Caution Amber** (present): someone is present but not closing, or a signal check is failing. Also used for the agent's corrective actions (relearn, add light, steady the camera, recalibrate) and the dashed detection threshold on the shadow-strength trace.
- **Alarm Red** (coming): someone is coming around the corner. Used for the status dot and its ping, the alert card's border and wash, the bearing ray and wedge on camera and plan, the alarm segment of the spacetime track, and the stop-vehicle decision. Its light tint (#ffb3ad) sets warning text in the agent panel and the log.

### Neutral
- **Night Console** (bg): page ground; the body background and the canvas fill behind HUD text halos.
- **Panel Floor** (bg-2): the lower stop of the panel's vertical gradient, so panels darken slightly toward their base.
- **Graphite Panel** (panel): panel surface, the status pill and the run selector.
- **Raised Graphite** (panel-2): raised controls: secondary buttons, the active segment and row hover in the decision log.
- **Instrument Well** (well): the recessed surface under every video, canvas, map, diagram and mono field. It is the darkest value in the system.
- **Hairline** (line): the default 1px border for panels, wells, header and footer rules, readout dividers and dashed list rows.
- **Strong Hairline** (line-2): borders on interactive controls (buttons, tags, keycaps, the textarea) and the scrollbar thumb.
- **Signal White** (ink): primary text, readout numbers and the time cursor. It is also the tracked shadow edge on the camera overlay, drawn white for contrast with the floor.
- **Instrument Grey** (ink-2): body copy, secondary values, the clock.
- **Quiet Grey** (ink-3): captions, units, dt labels, axis ticks, legend text, inactive segments. The "learning" state uses this same grey, so learning has no hue of its own.

### Named Rules
**The Reserved Triad Rule.** Green, amber and red mean corner state (clear, present, coming) and nothing else: no branding, no decorative tints, no category colours. If a colour has to say something that isn't corner state, it is indigo or a neutral.

**The System Ink Rule.** Indigo marks what Periscope itself measured or drew: the wedge, the corner, the bearing, the track. When the alarm fires, the bearing switches from indigo (or white on camera) to Alarm Red. It does not get a third colour.

**The Washes, Not Fills Rule.** A state colour fills an area only as a low-alpha wash (10–20% for the alert card, the plan's bearing cone and the status pill). Full-strength state colour is kept for dots, rays, borders and traces.

## Typography

**Display Font:** Geist (with system-ui, sans-serif)
**Body Font:** Geist (with system-ui, sans-serif)
**Label/Mono Font:** Geist Mono (with ui-monospace, SFMono-Regular, Menlo, monospace)

**Character:** One neutral grotesk is set tight at the top of the scale and relaxed in body text. Its mono sibling is kept for numbers that measure something, so a reader can tell a measurement from prose at a glance.

### Hierarchy
- **Display** (600, clamp(32px, 4.2vw, 54px), 1.02, -0.03em, `text-wrap: balance`): the single thesis line at the top of the console. Use one per surface.
- **Headline** (600, clamp(24px, 2.6vw, 34px), 1.08, -0.025em): section statements ("how it works") and the alert's state line, which runs slightly smaller (clamp(24px, 2.4vw, 32px)). Tool pages use a fixed 28px headline.
- **Title** (600, 15px, -0.005em): panel headings. A 12px Quiet Grey caption follows on the same baseline to say what the panel shows ("plan view", "calibrated wedge, 0° wall to 90°").
- **Body** (400, 15px, 1.55): prose and explanations, at 58–70ch. The intro lede runs at 16px; dense panel text runs at 13–14px in Instrument Grey.
- **Label** (400, 12–13px, Quiet Grey): dt labels, legends, captions, map notes. Sentence case, never tracked uppercase.
- **Control** (500, 13px): buttons, segments, pills, the run selector.
- **Readout** (Geist Mono 500, 22–24px, 1.1–1.15, -0.02em, tabular figures): the headline numbers in the alert and evidence panels. The unit follows in Quiet Grey at 13px.
- **Readout Small** (Geist Mono 500, 11–13px, tabular figures): HUD chips, the transport clock, canvas axis ticks, tape-mark coordinates, keycaps.

### Named Rules
**The Measurement Mono Rule.** If a string is a measurement (bearing, seconds, σ, metres, pixel coordinates), set it in Geist Mono with `tabular-nums` so values hold still while they update. Words stay in Geist, including words inside a mono-heavy panel.

**The Small Unit Rule.** A unit sits beside its number, smaller (13px) and in Quiet Grey. The number carries the weight.

## Layout

The console is a two-column instrument grid inside a 1320px container with a 24px gutter (14px under 640px). Tool pages use a 1180px container. The upper grid splits 1.42fr : 1fr. The floor camera spans two rows on the left, and the alert card and corner map stack on the right. The spacetime strip runs the full width at the fold, and the agent and evidence panels repeat the 1.42 : 1 split below it. Panels sit 16px apart. Wells are inset 12px from their panel's edge. Panel headers pad 12px top, 14px right, 16px left and are at least 46px tall. Controls inside headers and transport rows sit 8–10px apart. Long-form explanation follows 64px below the console in a 0.9 : 1.1 split, then a three-column limits row and a footer, each opened by a hairline.

Responsive behaviour collapses rather than reflows. At 1080px both grids go to one column, and the floor panel reorders so the transport sits above the camera, which keeps Play within reach. At 640px the gutter tightens to 14px, panel captions drop under their titles, the evidence readouts shrink to 20px, keyboard hints and the speed control hide, and the decision log moves under the checks. The calibration tool's grid (1fr + 320px rail) collapses at 860px.

### Named Rules
**The One Clock Rule.** Every view registers to one frame index: the floor overlay, the plan's bearing, the spacetime cursor, the shadow-strength cursor, the alert readouts and the decision log (future entries fade to 38%). Any new view of run data takes its time from the same cursor and scrubs with it.

**The Wedge-First Rule.** The floor camera is the largest panel and reads first, because it holds the evidence. Derived views (map, spacetime, scores) are always smaller and placed after it.

## Elevation & Depth

Mostly flat, with depth from tone. Panels lift off the page by a near-invisible recipe: a 180° gradient from Graphite Panel to Panel Floor, a 1px top inner highlight at 3.5% white, and a 2px drop shadow. Data surfaces go the other way. They sink into Instrument Well, darker than the page, behind a hairline. The active segment and the HUD chips are the only other raised items, the chips with a 6px backdrop blur over video.

### Shadow Vocabulary
- **Panel** (`box-shadow: 0 1px 0 rgba(255,255,255,.035) inset, 0 2px 4px rgba(0,0,0,.3)`): every panel, and nothing else.
- **Active segment** (`box-shadow: 0 1px 0 rgba(255,255,255,.05) inset, 0 1px 2px rgba(0,0,0,.4)`): the pressed option in a segmented control.
- **State halo** (`box-shadow: 0 0 0 3px <state colour at 18–25%>`): the ring around a status dot.
- **Alarm ring** (`0 0 0 0 → 0 0 0 14px rgba(255,91,79,0)` over 0.7s): plays once when the alert enters the coming state.

### Named Rules
**The Wells Sink Rule.** Anything that shows signal (video, canvas, plan, diagram, coordinate field) sits in a well darker than its panel. Panels rise slightly and data sinks. Panels never nest inside panels.

**The State-Only Motion Rule.** Motion marks state changes. Transitions run 150–350ms on `cubic-bezier(.16, 1, .3, 1)`. The 1s ping loops only while someone is coming. `prefers-reduced-motion` removes all animation and transitions.

## Shapes

Softly rounded, nested radii that step down as you go inward: panels 14px, wells and segment tracks 10px, buttons and fields 9px, segment options and log rows 7px, HUD chips and the focus ring 6px, keycaps 5px. Header-level status items (the run selector, the status pill, the synthetic tag) are full pills, so they read as state rather than panel content. Borders are always 1px. Dashed hairlines divide checklist and tape-mark rows, and solid hairlines divide everything else. Keycaps take a 2px bottom border. Map and diagram geometry is drawn with thin strokes. Truth is dashed, and Periscope's estimate is solid.

### Named Rules
**The Truth Is Dashed Rule.** Ground truth and thresholds draw dashed at reduced opacity (true position, truth trace, the 4.9σ line). Periscope's own estimate draws solid. A reader always knows which line is the camera and which is the referee.

## Components

### Buttons
Compact and tactile, with a 34px row height throughout.
- **Shape:** gently rounded (9px), 1px border.
- **Primary:** Wedge Indigo fill and border, Indigo Ink text, Control type, 0 14px padding, optional 16px stroked SVG icon with an 8px gap. There is one per surface (Play run, Copy marks).
- **Hover / Focus:** primary lightens to Bearing Lilac. Every button presses to `scale(.97)` on 150ms expo-out. Focus is a 2px Wedge Indigo outline offset 2px. Disabled drops to 45% opacity with a not-allowed cursor.
- **Secondary:** Raised Graphite fill, Strong Hairline border, Signal White text. Hover deepens to #1b2029 with a #3d4556 border.
- **Icon:** the secondary button squared to 34×34 with a single 16px line icon (1.8 stroke, round caps).

### Segmented control
The console's standard view switcher (Camera / Shadow ×70, Plan / Hidden hallway, speed, overlays, camera mode).
- **Style:** Instrument Well track, Hairline border, 10px radius, 3px padding, 2px gap. Options are 26px tall (28px on tool pages), Control type, Quiet Grey.
- **State:** the pressed option (`aria-pressed="true"`) takes Raised Graphite with Signal White text and the active-segment shadow. Hover brightens text to Signal White.

### Status pill and tags
- **Status pill:** 34px pill on Graphite Panel with a Hairline border. An 8px dot carries the state colour inside a 3px halo. In the coming state the border and a 10% wash turn Alarm Red and the dot pings. It doubles as the live region.
- **Synthetic tag:** 26px pill, 12px/500 text in pale indigo on an 8% indigo wash with a 40% indigo border. It labels synthetic data and is the only tag in the system.

### Cards / Containers
- **Corner Style:** 14px.
- **Background:** Graphite Panel fading to Panel Floor (180° gradient). Tool pages use flat Graphite Panel.
- **Shadow Strategy:** the Panel shadow only (see Elevation & Depth).
- **Border:** 1px Hairline.
- **Internal Padding:** 16px horizontally; content wells inset 12px.

### Inputs / Fields
- **Run selector:** a pill-shaped native select (34px, Graphite Panel, Hairline border) with a drawn chevron. Focus-within turns the border Wedge Indigo.
- **Mono field:** Instrument Well background, Strong Hairline border, 9px radius, 10px padding, Readout Small type. Used for machine-readable output such as mark strings.

### Navigation
A single header row: a wordmark (a 30px rounded-square glyph of the wall corner with indigo rays, then PERISCOPE at 17px/700 with 0.2em tracking), followed by the run selector, the synthetic tag and the status pill. The row is closed by a Hairline rule. Tool pages link back to the console inline in their lede.

### Alert card (signature)
The console's verdict. It is a panel with 18px padding. A Headline-scale state line is led by an 11px state dot. One sentence of Instrument Grey explanation follows, at a fixed minimum of two lines so the card doesn't jump. Below that, a three-up readout row (Bearing, In view in, Shadow strength) uses Label dt over Readout dd, with columns split by hairlines. A 3px progress bar runs along the bottom edge. Present tints the border amber at 38%. Coming tints the border red at 70%, washes the panel red (16% to 4%), turns the title white, pings the dot, and plays the alarm ring once.

### Instrument well with HUD
Video or canvas filling a well (the camera at 4:3, the map at 16:9, the spacetime strip at 210px, or 170px on mobile, with a 58px shadow-strength trace beneath). Overlays draw in canvas: the indigo wedge at 10% fill with a 90% stroke, dashed 22% white 15° rays, mono angle labels with a dark halo, and the bearing ray. HUD chips sit bottom-left in Readout Small on a 72%-black blurred chip. A legend row below the panel spells out each overlay with a 14×2px line swatch.

### Readout list and decision log
Evidence and agent panels share one row grammar. Label dt over Readout dd in a two-column grid with hairline dividers. A checklist row has an 8px state dot, a label, and a right-aligned mono value over dashed hairlines. Log rows have a 52px mono timestamp, then a bold action and its reason. Log rows are clickable to seek (Raised Graphite hover, 7px radius), and future rows fade.

## Do's and Don'ts

### Do:
- **Do** put every video, canvas, map and diagram in an Instrument Well with a 1px Hairline and a 10px radius, inset 12px inside its panel.
- **Do** set every measurement in Geist Mono with tabular figures, with its unit smaller and in Quiet Grey beside it.
- **Do** give each panel a Title-scale heading plus a one-line Quiet Grey caption saying what the view shows.
- **Do** draw ground truth and thresholds dashed and Periscope's estimate solid.
- **Do** tie every new run-data view to the shared time cursor, so scrubbing one scrubs all.
- **Do** label synthetic runs with the synthetic tag or in the run name.
- **Do** keep one primary (Wedge Indigo) button per surface.

### Don't:
- **Don't** use green, amber or red for anything but corner state: no decorative glows, category colours or brand moments in the triad.
- **Don't** fill large areas with full-strength state colour. State reaches surfaces only as washes at 20% or less.
- **Don't** set measurements in proportional Geist, or set prose in Geist Mono.
- **Don't** nest a panel inside a panel. Inner structure is wells, hairlines and dashed rows.
- **Don't** animate anything that isn't a state change, and don't loop motion outside the coming state.
- **Don't** introduce a light theme or a second accent hue. The console is dark-only with one system voice.
