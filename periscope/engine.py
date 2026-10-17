"""Streaming Periscope engine: one frame in, one decision out.

    frame ─► register (phase correlation on floor grain) ─► whole-pixel align
          ─► angular bins ─► undo the sub-pixel shift with the background's binned gradients
          ─► / empty-hallway background ─► moving average ─► regularised inverse ─► x(phi)
          ─► z-score against the measured noise ─► angle tracker ─► state + agent decision

The first `learn_s` seconds learn the empty hallway: the background, its gradients and the noise
level. After that the background follows slow light changes, but only while nobody is detected,
and the noise scale keeps recalibrating on clear frames.

Why not just warp each frame back? The floor's grain is ~10x stronger than the shadow, and
bilinear resampling blurs it by a different amount at every sub-pixel offset. That alone makes
false detections at 0.3 px of shake. Shifting by whole pixels is exact, and the leftover
fraction is removed in the bin domain with a second-order Taylor model.
"""

from __future__ import annotations

from collections import deque

import cv2
import numpy as np

from . import quality
from .geometry import Calibration
from .recon import Reconstructor
from .track import AngleTracker, TrackerConfig, peak_angle, smooth_angle


class Periscope:
    def __init__(self, calib: Calibration, frame_size: tuple[int, int], fps: float, *, n_meas: int = 90,
                 n_phi: int = 45, lam_rel: float = 0.3, smooth_s: float = 0.4, learn_s: float = 2.0,
                 stabilize: bool = True, work_width: int = 640, tracker: TrackerConfig | None = None,
                 auto_relearn: bool = True):
        w, h = frame_size
        self.scale = min(1.0, work_width / w)
        self.size = (int(round(w * self.scale)), int(round(h * self.scale)))
        self.calib = calib.scaled(self.scale) if self.scale != 1.0 else calib
        self.fps = fps
        self.recon = Reconstructor(self.calib, *self.size, n_meas=n_meas, n_phi=n_phi, lam_rel=lam_rel)
        self.phi = self.recon.phi
        self.K = max(1, int(round(smooth_s * fps)))
        self.learn_n = max(self.K + 4, int(round(learn_s * fps)))
        self.stabilize = stabilize
        self.nuisance_terms = ("x", "y", "xx", "xy", "yy")
        self.auto_relearn = auto_relearn
        self.tracker = AngleTracker(fps, tracker, lag_s=(self.K - 1) / (2 * fps))
        self.t = 0
        self.events: list[dict] = []
        self._ref = None
        self._win = None
        self._shifts = deque(maxlen=int(fps * 2))
        self.G = None
        self._start_learning()

    # ---- background -----------------------------------------------------------------
    def _start_learning(self, seconds: float | None = None):
        self.learning = True
        self._learn_target = self.learn_n if seconds is None else max(self.K + 4, int(seconds * self.fps))
        self._learn_bins: list[np.ndarray] = []
        self._learn_frac: list[tuple[float, float]] = []
        self._learn_frame = None
        self.bg = None
        self.bg_frame = None
        self.pixel_var = None
        self.sigma_x = None
        self.z_scale = 1.0
        self._n_bg = 1
        self._ybuf: deque = deque(maxlen=self.K)
        self._offset_hist = deque(maxlen=max(3, int(self.fps * 0.5)))
        self.tracker.reset()

    def _shift_model(self, bg_frame: np.ndarray):
        """Binned first and second derivatives of the background, for sub-pixel shift correction."""
        f = bg_frame.astype(np.float64)
        gy, gx = np.gradient(f, axis=(0, 1))
        gxy, gxx = np.gradient(gx, axis=(0, 1))
        gyy, _ = np.gradient(gy, axis=(0, 1))
        b = self.recon.binner
        return {k: b(v) for k, v in dict(x=gx, y=gy, xx=gxx, xy=gxy, yy=gyy).items()}

    def _correct(self, bins, frac):
        if self.G is None or frac is None:
            return bins
        fx, fy = frac
        G = self.G
        # frame(p) = bg(p - f)  =>  bins ~ B - Gx fx - Gy fy + 1/2 (Gxx fx^2 + 2 Gxy fx fy + Gyy fy^2)
        return bins + G["x"] * fx + G["y"] * fy - 0.5 * (G["xx"] * fx * fx + 2 * G["xy"] * fx * fy + G["yy"] * fy * fy)

    def _finish_learning(self):
        n = len(self._learn_bins)
        self.bg_frame = self._learn_frame / n
        if self.stabilize:
            self.G = self._shift_model(self.bg_frame)
        B = np.stack([self._correct(b, f) for b, f in zip(self._learn_bins, self._learn_frac)])
        self.bg = B.mean(0)
        if self.stabilize:
            # Whatever shift the Taylor step misses (phase-correlation bias, slow drift) leaves
            # this texture fingerprint on the bins; fit it in the inverse and throw it away.
            cols = np.stack([self.G[k] / np.maximum(self.bg, 1e-6) for k in self.nuisance_terms], axis=1)
            self.recon.set_nuisance(cols)
        self._n_bg = n
        Y = B / np.maximum(self.bg, 1e-6)[None] - 1
        dY = np.diff(Y, axis=0)
        counts = self.recon.binner.counts
        ok = counts > 0
        D = (dY[:, ok] * np.sqrt(counts[ok])[None, :, None]).reshape(-1, dY.shape[2])
        # per-pixel noise covariance across colour channels: demosaicing and video codecs
        # share noise between channels, so treating them as independent overstates evidence
        self.pixel_cov = D.T @ D / (2 * len(D))
        self.pixel_var = np.diag(self.pixel_cov).copy()
        self.sigma_x = self.recon.x_sigma(self.pixel_var, self._k_eff())
        self._shape = self.recon.x_sigma(np.ones(len(self.pixel_var)), 1.0).mean(1)   # (n_phi,) per unit variance
        self._W = np.linalg.inv(np.linalg.cholesky(self.pixel_cov + 1e-12 * np.eye(len(self.pixel_cov)))).T
        # Calibrate the z scale on the learning window itself. Frame differences miss noise
        # that is correlated in time (video compression, slow shake), so measure x directly.
        zs = []
        for i in range(self.K, n + 1):
            x, _ = self.recon.solve(Y[i - self.K:i].mean(0))
            zs.append(self._z(x, 1.0).mean())
        # the background was fitted to these same frames, which removes part of their noise
        expected = 3.0 * (1.0 / self.K - 1.0 / n) / (1.0 / self.K + 1.0 / n)
        self.z_scale = max(1.0, float(np.mean(zs)) / expected) if zs else 1.0
        self.learning = False
        self._learn_bins, self._learn_frac = [], []

    def _z(self, x: np.ndarray, var_scale: float) -> np.ndarray:
        """Whitened chi-square-3 score per angle: x^T C^-1 x / (shape^2 / k_eff)."""
        xw = x @ self._W
        return (xw ** 2).sum(1) / (self._shape ** 2 * var_scale / self._k_eff())

    def _k_eff(self, k: int | None = None) -> float:
        # the moving average and the background both carry noise: 1/K + 1/N_background
        return 1.0 / (1.0 / (k or self.K) + 1.0 / max(self._n_bg, 1))

    # ---- per frame ---------------------------------------------------------------------
    def _prepare(self, frame):
        if self.scale != 1.0:
            frame = cv2.resize(frame, self.size, interpolation=cv2.INTER_AREA)
        shift, frac = (0.0, 0.0), None
        if self.stabilize:
            g = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32)
            # Register on floor grain only: the hidden person's shadow is smooth and would
            # otherwise pull the estimate by tenths of a pixel exactly when it matters.
            g = g - cv2.GaussianBlur(g, (0, 0), 3.0)
            if self._ref is None:
                self._ref = g
                self._win = cv2.createHanningWindow(g.shape[::-1], cv2.CV_32F)
            # OpenCV 5.0.0 applies the window to both inputs in place, so pass copies.
            (dx, dy), _ = cv2.phaseCorrelate(self._ref.copy(), g.copy(), self._win)
            shift = (dx, dy)
            ix, iy = int(round(dx)), int(round(dy))
            if ix or iy:
                M = np.float32([[1, 0, -ix], [0, 1, -iy]])
                frame = cv2.warpAffine(frame, M, self.size, flags=cv2.INTER_NEAREST, borderMode=cv2.BORDER_REPLICATE)
                g = cv2.warpAffine(g, M, self.size, flags=cv2.INTER_NEAREST, borderMode=cv2.BORDER_REPLICATE)
            frac = (dx - ix, dy - iy)
        self._shifts.append(shift)
        return frame, shift, frac

    def update(self, frame: np.ndarray) -> dict:
        frame, shift, frac = self._prepare(frame)
        self.aligned = frame
        bins = self.recon.binner(frame)
        t = self.t
        self.t += 1
        out = {"i": t, "t": round(t / self.fps, 4), "shift": [round(shift[0], 3), round(shift[1], 3)]}

        if self.learning:
            self._learn_bins.append(bins)
            self._learn_frac.append(frac)
            f = frame.astype(np.float32)
            self._learn_frame = f if self._learn_frame is None else self._learn_frame + f
            if len(self._learn_bins) >= self._learn_target:
                self._finish_learning()
            out.update(state="learning", present=False, phi=None, phi_dot=None, eta_s=None, coming=False,
                       z_peak=0.0, phi_meas=None, x=None, xn=None, offset=None)
            return out

        bins = self._correct(bins, frac)
        y = bins / np.maximum(self.bg, 1e-6) - 1
        self._ybuf.append(y)
        ys = np.mean(self._ybuf, axis=0)
        x, b = self.recon.solve(ys)
        var_scale = self.z_scale * self._k_eff() / self._k_eff(len(self._ybuf))
        sig = self.sigma_x * np.sqrt(var_scale)
        z = smooth_angle(self._z(x, var_scale))
        phi_meas, z_peak = peak_angle(z, self.phi)
        st = self.tracker.update(phi_meas, z_peak)

        if not st["present"]:
            # follow slow light changes, and keep the noise scale honest, only while it's clear
            a = 1.0 / (self.fps * 20)
            if z_peak < self.tracker.cfg.z_off:
                self.bg = (1 - a) * self.bg + a * bins
            if len(self._ybuf) == self.K:
                self.z_scale = float(np.clip(0.99 * self.z_scale + 0.01 * self.z_scale * z.mean() / 3.0, 1.0, 50.0))
        self._offset_hist.append(float(np.mean(b)) * 100)

        state = "coming" if st["coming"] else ("present" if st["present"] else "clear")
        out.update(st, state=state, z_peak=round(z_peak, 2), phi_meas=round(phi_meas, 2),
                   x=x, xn=x / np.maximum(sig, 1e-12), offset=b)
        if t % 5 == 0 or st["coming"]:
            out["quality"] = self.assess(st, frame)
            q = out["quality"]
            if self.auto_relearn and q["action"] == "relearn_background" and not st["present"]:
                self.events.append({"t": out["t"], "action": "relearn_background", "why": q["why"]})
                self._start_learning(seconds=1.0)
        return out

    # ---- quality --------------------------------------------------------------------
    def metrics(self, frame=None) -> dict:
        sh = np.array(self._shifts) if self._shifts else np.zeros((1, 2))
        jitter = sh - np.median(sh, axis=0)
        noise_rel = float(np.sqrt(np.mean(self.pixel_var) * self.z_scale)) if self.pixel_var is not None else 0.0
        n_px = self.recon.binner.n_pixels
        m = {
            "noise_pct": noise_rel * 100,
            "z_scale": float(self.z_scale),
            "shake_px": float(np.sqrt((jitter ** 2).sum(1).mean())),
            "drift_px": float(np.hypot(*np.median(sh, axis=0))),
            "offset_pct": float(np.median(self._offset_hist)) if self._offset_hist else 0.0,
            "wedge_px": n_px,
            "range_m": quality.predicted_range_m(noise_rel, n_px) if noise_rel > 0 else None,
        }
        if frame is not None:
            f = frame.reshape(-1, 3)[self.recon.binner.flat]
            m["clip_pct"] = float(((f >= 254) | (f <= 1)).any(1).mean() * 100)
        return m

    def assess(self, st=None, frame=None) -> dict:
        m = self.metrics(frame)
        m["coming"] = bool(st and st.get("coming"))
        q = quality.assess(m)
        q["metrics"] = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in m.items()}
        return q
