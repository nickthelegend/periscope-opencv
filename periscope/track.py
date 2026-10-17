"""Detect and track the hidden person's angle in the spacetime image.

Detection: each angle cell gets z = x^T C^-1 x / var, with C the colour noise covariance: a
chi-square-3 score under noise alone, lightly smoothed across angle. A person is present when the peak stays above
`z_on` for `n_on` frames, and gone after `off_s` seconds below `z_off`.

Tracking: an alpha-beta filter on (angle, angular speed), with a gate so one noisy peak can't
yank the track. Walking toward the corner along the hidden hallway means the angle falls to 0,
where the person steps into view; that's the "someone is coming" state.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

KERNEL = np.array([0.25, 0.5, 0.25])


def smooth_angle(z: np.ndarray) -> np.ndarray:
    """Light smoothing across neighbouring angles (a person spans a few cells)."""
    return np.convolve(np.pad(z, 1, mode="edge"), KERNEL, mode="valid")


def score(x: np.ndarray, sigma: np.ndarray) -> np.ndarray:
    """Independent-channel version of the score: sum over colour of (x / sigma)^2, smoothed."""
    return smooth_angle(((x / np.maximum(sigma, 1e-12)) ** 2).sum(axis=1))


def peak_angle(z: np.ndarray, phi: np.ndarray) -> tuple[float, float]:
    j = int(np.argmax(z))
    if 0 < j < len(z) - 1:
        a, b, c = z[j - 1], z[j], z[j + 1]
        den = a - 2 * b + c
        off = 0.5 * (a - c) / den if den < 0 else 0.0
    else:
        off = 0.0
    step = phi[1] - phi[0]
    return float(phi[j] + np.clip(off, -0.5, 0.5) * step), float(z[j])


@dataclass
class TrackerConfig:
    z_on: float = 24.0
    z_off: float = 16.0
    n_on: int = 3
    off_s: float = 0.7
    alpha: float = 0.45
    beta: float = 0.06
    gate_deg: float = 18.0
    coming_speed: float = 2.0      # deg/s toward the corner
    coming_angle: float = 30.0     # inside this angle we warn regardless of speed


class AngleTracker:
    def __init__(self, fps: float, cfg: TrackerConfig | None = None, lag_s: float = 0.0):
        self.cfg = cfg or TrackerConfig()
        self.dt = 1.0 / fps
        self.lag_s = lag_s          # the moving average reports the past; predict back to now
        self.reset()

    def reset(self):
        self.present = False
        self.above = 0
        self.below = 0
        self.phi = None
        self.phi_dot = 0.0

    def update(self, phi_meas: float, z_peak: float) -> dict:
        c = self.cfg
        if z_peak > c.z_on:
            self.above += 1
        else:
            self.above = 0
        if not self.present and self.above >= c.n_on:
            self.present = True
            self.below = 0
            self.phi, self.phi_dot = phi_meas, 0.0
        elif self.present:
            if z_peak < c.z_off:
                self.below += 1
                if self.below * self.dt >= c.off_s:
                    self.reset()
            else:
                self.below = 0
        if self.present:
            pred = self.phi + self.phi_dot * self.dt
            r = phi_meas - pred
            if z_peak >= c.z_off and abs(r) < c.gate_deg:
                self.phi = pred + c.alpha * r
                self.phi_dot = self.phi_dot + c.beta * r / self.dt
            elif z_peak >= c.z_on * 2:           # strong peak far from the track: jump to it
                self.phi, self.phi_dot = phi_meas, 0.0
            else:
                self.phi = pred
            self.phi = float(np.clip(self.phi, 0.0, 90.0))
            self.phi_dot = float(np.clip(self.phi_dot, -60, 60))
        return self.state()

    def state(self) -> dict:
        c = self.cfg
        if not self.present:
            return {"present": False, "phi": None, "phi_dot": None, "eta_s": None, "coming": False}
        phi = float(np.clip(self.phi + self.phi_dot * self.lag_s, 0.0, 90.0))
        approaching = self.phi_dot < -c.coming_speed
        coming = approaching or phi < c.coming_angle
        # Time until the walker reaches the corner line (x = 0), for someone walking straight
        # along the hidden hallway at constant speed: x = -y tan(phi), so
        # t = |x / x'| = sin(2 phi) / (2 |phi'|). A plain phi / phi' overestimates it ~3x.
        eta = None
        if self.phi_dot < -1.0:
            eta = np.sin(2 * np.radians(phi)) / (2 * np.radians(-self.phi_dot))
        return {"present": True, "phi": round(phi, 2), "phi_dot": round(self.phi_dot, 2),
                "eta_s": None if eta is None else round(min(eta, 99.0), 2), "coming": bool(coming)}
