"""CornerCam 1-D angular reconstruction.

Each floor pixel in the wedge, at angle theta from the wall, integrates the hidden scene over
hidden angles [0, theta]. Averaging pixels in thin angular bins gives one measurement per bin:

    y(theta_i) = sum_j A[i, j] * x(phi_j) + b

A[i, j] is the overlap (radians) of hidden-angle cell j with [0, theta_i], x is the hidden
scene's radiance change per angle and b soaks up any global light change. We invert with
regularised, pixel-count-weighted least squares:

    x = argmin ||W^1/2 (A x + b - y)||^2 + lam ||D x||^2 + eps ||x||^2

which is one precomputed matrix, so every frame costs a single matrix-vector product.
"""

from __future__ import annotations

import numpy as np

from .geometry import Calibration


class AngularBinner:
    """Mean colour of the floor wedge in thin angular bins, per frame (np.bincount, no loops)."""

    def __init__(self, calib: Calibration, width: int, height: int, n_bins: int = 90):
        theta, r = calib.polar_maps(width, height)
        valid = (theta >= 0) & (theta < calib.theta_max) & (r >= calib.r_min) & (r <= calib.r_max)
        idx = np.floor(theta / calib.theta_max * n_bins).astype(np.int64)
        self.n_bins = n_bins
        self.width, self.height = width, height
        self.flat = np.flatnonzero(valid.ravel())
        self.idx = idx.ravel()[self.flat]
        self.counts = np.bincount(self.idx, minlength=n_bins).astype(np.float64)
        th = theta.ravel()[self.flat]
        sums = np.bincount(self.idx, weights=th, minlength=n_bins)
        edges = np.linspace(0, calib.theta_max, n_bins + 1)
        centres = (edges[:-1] + edges[1:]) / 2
        self.theta = np.where(self.counts > 0, sums / np.maximum(self.counts, 1), centres)
        self.valid_mask = valid

    @property
    def n_pixels(self) -> int:
        return int(self.counts.sum())

    def __call__(self, frame: np.ndarray) -> np.ndarray:
        f = frame.reshape(-1, frame.shape[2] if frame.ndim == 3 else 1)[self.flat].astype(np.float64)
        out = np.empty((self.n_bins, f.shape[1]))
        for c in range(f.shape[1]):
            out[:, c] = np.bincount(self.idx, weights=f[:, c], minlength=self.n_bins)
        return out / np.maximum(self.counts, 1)[:, None]


def forward_matrix(theta_meas_deg: np.ndarray, phi_edges_deg: np.ndarray) -> np.ndarray:
    """A[i, j] = length (radians) of hidden cell j that floor angle theta_i can see."""
    lo, hi = phi_edges_deg[:-1], phi_edges_deg[1:]
    seen = np.clip(theta_meas_deg[:, None], lo[None], hi[None]) - lo[None]
    return np.radians(seen)


def inverse_operator(A: np.ndarray, weights: np.ndarray, lam_rel: float = 0.3, eps_rel: float = 1e-3,
                     extra: np.ndarray | None = None) -> np.ndarray:
    """Precompute M so that [x; b; n] = M @ y. Returns shape (n_phi + 1 + k, n_meas).

    `extra` (n_meas, k) are nuisance columns fitted alongside the scene and then ignored, e.g.
    the signature a sub-pixel camera shift leaves on the binned floor texture.
    """
    n_m, n_p = A.shape
    w = weights / max(weights[weights > 0].mean(), 1e-12)
    cols = [A, np.ones((n_m, 1))] + ([extra] if extra is not None else [])
    Aa = np.hstack(cols)
    AtW = Aa.T * w[None]
    G = AtW @ Aa
    scale = np.trace(G[:n_p, :n_p]) / n_p
    D = np.diff(np.eye(n_p), axis=0)
    R = np.zeros_like(G)
    R[:n_p, :n_p] = lam_rel * scale * (D.T @ D) + eps_rel * scale * np.eye(n_p)
    if extra is not None:
        k = extra.shape[1]
        R[-k:, -k:] = 1e-6 * np.diag(np.diag(G[-k:, -k:]) + 1e-12)
    return np.linalg.solve(G + R, AtW)


class Reconstructor:
    """Binning + forward model + inverse for one calibrated view."""

    def __init__(self, calib: Calibration, width: int, height: int, n_meas: int = 90, n_phi: int = 45,
                 lam_rel: float = 0.3):
        self.binner = AngularBinner(calib, width, height, n_meas)
        self.phi_edges = np.linspace(0, calib.theta_max, n_phi + 1)
        self.phi = (self.phi_edges[:-1] + self.phi_edges[1:]) / 2
        self.A = forward_matrix(self.binner.theta, self.phi_edges)
        self.lam_rel = lam_rel
        self.M = inverse_operator(self.A, self.binner.counts, lam_rel)
        self.Mc = None                      # per-channel operators once nuisance columns are set
        self.n_phi = n_phi

    def set_nuisance(self, cols: np.ndarray | None):
        """cols: (n_meas, k, C) per-channel nuisance columns, or None to clear."""
        if cols is None:
            self.Mc = None
            return
        self.Mc = [inverse_operator(self.A, self.binner.counts, self.lam_rel, extra=cols[:, :, c])
                   for c in range(cols.shape[2])]

    def solve(self, y: np.ndarray):
        """y: (n_meas, C) relative change -> x (n_phi, C), offset (C,)."""
        if self.Mc is None:
            sol = self.M @ y
            return sol[:self.n_phi], sol[self.n_phi]
        x = np.stack([M[:self.n_phi] @ y[:, c] for c, M in enumerate(self.Mc)], 1)
        b = np.array([M[self.n_phi] @ y[:, c] for c, M in enumerate(self.Mc)])
        return x, b

    def x_sigma(self, pixel_var: np.ndarray, frames_averaged: float = 1.0) -> np.ndarray:
        """Noise std of x per (phi, channel) given per-pixel variance per channel (relative units)."""
        y_var = np.where(self.binner.counts > 0, 1.0 / np.maximum(self.binner.counts, 1), 0)
        mats = [self.M] * len(pixel_var) if self.Mc is None else self.Mc
        base = np.stack([(mats[min(c, len(mats) - 1)][:self.n_phi] ** 2) @ y_var for c in range(len(pixel_var))], 1)
        return np.sqrt(base * pixel_var[None, :] / max(frames_averaged, 1e-9))


def spacetime_offline(bins: np.ndarray, recon: Reconstructor, smooth: int = 1):
    """Whole-clip reconstruction with the clip's temporal median as background (CornerCam style).

    bins: (T, n_meas, C). Returns x (T, n_phi, C).
    """
    bg = np.median(bins, axis=0)
    y = bins / np.maximum(bg, 1e-6)[None] - 1
    if smooth > 1:
        k = np.ones(smooth) / smooth
        y = np.apply_along_axis(lambda s: np.convolve(s, k, mode="same"), 0, y)
    sol = np.einsum("pm,tmc->tpc", recon.M, y)
    return sol[:, :recon.n_phi], sol[:, recon.n_phi]
