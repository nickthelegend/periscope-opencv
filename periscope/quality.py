"""Signal-quality checks and the agent's next action.

The agent watches the numbers that decide whether the faint floor shadow is readable and picks
what to do next: keep watching, re-learn the empty-hallway background, ask for more light or a
steadier mount, re-calibrate, or send a stop to the vehicle.

Every decision carries the measured number that triggered it, so a human can audit it.
"""

from __future__ import annotations

import numpy as np

# Per-pixel relative change a strongly coloured person makes at 3 m from the corner in a lit
# hallway, from the CornerCam light model in render.py (0.47 DN on a 150 DN floor).
NOMINAL_REL_SIGNAL_3M = 0.0031
# Per-pixel SNR at 3 m needed to detect, from tools/snr_sweep.py (see RESEARCH.md). The
# signal falls roughly as 1/d^3 with distance d from the corner.
SNR_FLOOR_3M = 0.05


def predicted_range_m(pixel_rel_noise: float, n_pixels: int, ref_pixels: int = 16000) -> float:
    """Distance down the hidden hallway at which a nominal person should still be detected."""
    snr3 = NOMINAL_REL_SIGNAL_3M / max(pixel_rel_noise, 1e-9) * np.sqrt(max(n_pixels, 1) / ref_pixels)
    return float(3.0 * (snr3 / SNR_FLOOR_3M) ** (1 / 3))


def assess(m: dict) -> dict:
    """m: rolling metrics from the engine. Returns checks and one decision."""
    checks = []

    def add(name, ok, value, detail):
        checks.append({"name": name, "ok": bool(ok), "value": value, "detail": detail})

    rng = m.get("range_m")
    add("signal", rng is None or rng >= 2.5, None if rng is None else round(rng, 1),
        "predicted detection range (m) for a person in strong colours")
    add("noise", m.get("noise_pct", 0) < 2.5, round(m.get("noise_pct", 0), 2), "per-pixel noise, % of floor level")
    add("shake", m.get("shake_px", 0) < 0.6, round(m.get("shake_px", 0), 2), "RMS camera shake (px) after stabilisation")
    add("drift", m.get("drift_px", 0) < 3.0, round(m.get("drift_px", 0), 1), "how far the view has slid since calibration (px)")
    add("exposure", abs(m.get("offset_pct", 0)) < 1.5, round(m.get("offset_pct", 0), 2),
        "global light change since the background was learned (%)")
    add("clipping", m.get("clip_pct", 0) < 2.0, round(m.get("clip_pct", 0), 2), "% of wedge pixels at 0 or 255")
    add("wedge", m.get("wedge_px", 0) >= 4000, m.get("wedge_px", 0), "floor pixels in the calibrated wedge")

    bad = {c["name"] for c in checks if not c["ok"]}
    if m.get("coming"):
        action, why = "stop_vehicle", "someone is approaching the corner from the hidden side"
    elif "drift" in bad:
        action, why = "recalibrate", "the camera moved; the corner is no longer where the marks were"
    elif "exposure" in bad or "clipping" in bad:
        action, why = "relearn_background", "lighting or exposure changed; the empty-hallway reference is stale"
    elif "shake" in bad:
        action, why = "steady_camera", "camera shake is larger than the shadow signal can tolerate"
    elif "signal" in bad or "noise" in bad:
        action, why = "add_light", "the floor is too dark or noisy to see a shadow at a safe distance"
    elif "wedge" in bad:
        action, why = "reframe", "too little floor next to the corner is in view"
    else:
        action, why = "watch", "signal is readable"
    return {"checks": checks, "action": action, "why": why}
