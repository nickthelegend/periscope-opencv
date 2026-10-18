"""Corner and floor-wedge calibration.

Floor coordinates (metres), shared by the renderer, the calibration and the map:

    corner of the wall at the origin, floor is z = 0
    the wall we can see runs from the corner along -y (wall material on x < 0, y < 0)
    the hidden hallway lies at x < 0, 0 < y < hall_width
    the camera's floor is x > 0

A floor point at angle theta from the wall (theta = atan2(x, -y)) sees the hidden scene over
hidden angles phi in [0, theta]. phi = 0 looks straight past the corner along +y, phi = 90 looks
down the hidden hallway along -x.

Calibration is five tape marks at known floor positions, clicked in the image: the corner,
two marks along the wall base and two along the 90-degree line. They give a homography from
image pixels to the floor, so angles are true floor angles even with an oblique camera.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field

import cv2
import numpy as np

# Tape marks in floor metres, in the order the filming protocol asks you to click them.
MARKS_M = np.array([
    [0.0, 0.0],    # corner
    [0.0, -0.5],   # wall base, 50 cm from the corner
    [0.0, -1.0],   # wall base, 100 cm
    [0.5, 0.0],    # 90-degree line, 50 cm
    [1.0, 0.0],    # 90-degree line, 100 cm
    [1.0, -1.0],   # diagonal, optional sixth mark
], dtype=np.float64)


@dataclass
class Calibration:
    """Image-to-floor mapping plus the wedge of floor we read the shadow from."""

    corner_px: tuple[float, float]
    H: list[list[float]] | None = None          # image px -> floor metres
    wall_px: tuple[float, float] | None = None  # used when H is None: a point on the wall base
    open_px: tuple[float, float] | None = None  # used when H is None: a point on the 90-degree ray
    r_min: float = 0.12                          # wedge inner radius (m, or px without H)
    r_max: float = 1.0                           # wedge outer radius
    theta_max: float = 90.0                      # degrees
    image_size: tuple[int, int] | None = None   # (width, height) the points were clicked on
    source: str = "marks"
    notes: list[str] = field(default_factory=list)

    # ---- construction -------------------------------------------------------------
    @classmethod
    def from_marks(cls, marks_px, image_size=None, r_min=0.12, r_max=1.0) -> "Calibration":
        """marks_px: the first 5 (or 6) tape marks in MARKS_M order, in image pixels."""
        pts = np.asarray(marks_px, dtype=np.float64)
        n = len(pts)
        if n < 5:
            raise ValueError("need at least 5 tape marks: corner, wall 50/100 cm, 90-degree 50/100 cm")
        H, _ = cv2.findHomography(pts, MARKS_M[:n], 0)
        if H is None:
            raise ValueError("tape marks are degenerate (are any three of them on one line by mistake?)")
        return cls(corner_px=tuple(pts[0]), H=H.tolist(), r_min=r_min, r_max=r_max,
                   image_size=image_size, source="marks")

    @classmethod
    def from_rays(cls, corner_px, wall_px, open_px, image_size=None, r_min=20.0, r_max=200.0) -> "Calibration":
        """Two clicks plus the corner, no homography. Angles are only approximate (affine)."""
        return cls(corner_px=tuple(corner_px), wall_px=tuple(wall_px), open_px=tuple(open_px),
                   r_min=r_min, r_max=r_max, image_size=image_size, source="rays")

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_json(cls, s: str) -> "Calibration":
        d = json.loads(s)
        for k in ("corner_px", "wall_px", "open_px", "image_size"):
            if d.get(k) is not None:
                d[k] = tuple(d[k])
        return cls(**d)

    def scaled(self, s: float) -> "Calibration":
        """The same calibration for an image resized by factor s."""
        H = None
        if self.H is not None:
            S_inv = np.diag([1 / s, 1 / s, 1.0])
            H = (np.asarray(self.H) @ S_inv).tolist()
        sc = lambda p: None if p is None else (p[0] * s, p[1] * s)
        r_scale = 1.0 if self.H is not None else s
        size = None if self.image_size is None else (round(self.image_size[0] * s), round(self.image_size[1] * s))
        return Calibration(corner_px=sc(self.corner_px), H=H, wall_px=sc(self.wall_px), open_px=sc(self.open_px),
                           r_min=self.r_min * r_scale, r_max=self.r_max * r_scale, theta_max=self.theta_max,
                           image_size=size, source=self.source, notes=list(self.notes))

    # ---- mapping ------------------------------------------------------------------
    def to_floor(self, pts_px) -> np.ndarray:
        """Image px (N,2) -> floor coordinates relative to the corner, in the (wall, 90) basis.

        Returns (N,2) array of (a, b): a along the wall (positive away from the corner), b along
        the 90-degree ray. theta = atan2(b, a).
        """
        p = np.asarray(pts_px, dtype=np.float64).reshape(-1, 2)
        if self.H is not None:
            f = cv2.perspectiveTransform(p.reshape(-1, 1, 2), np.asarray(self.H)).reshape(-1, 2)
            # floor frame: wall direction is -y, 90-degree direction is +x
            return np.stack([-f[:, 1], f[:, 0]], axis=1)
        c = np.asarray(self.corner_px)
        B = np.stack([np.asarray(self.wall_px) - c, np.asarray(self.open_px) - c], axis=1)
        # affine basis scaled so |wall vector| = 1 px unit length along each ray
        B = B / np.linalg.norm(B, axis=0, keepdims=True)
        return np.linalg.solve(B, (p - c).T).T

    def polar_maps(self, width: int, height: int, shift=(0.0, 0.0)):
        """Per-pixel (theta_deg, r) maps for an image of this size."""
        u, v = np.meshgrid(np.arange(width, dtype=np.float64) + shift[0],
                           np.arange(height, dtype=np.float64) + shift[1])
        ab = self.to_floor(np.stack([u.ravel(), v.ravel()], axis=1))
        theta = np.degrees(np.arctan2(ab[:, 1], ab[:, 0])).reshape(height, width)
        r = np.hypot(ab[:, 0], ab[:, 1]).reshape(height, width)
        return theta, r

    def wedge_outline(self, n: int = 24) -> list[list[float]]:
        """Image-px polygon of the wedge (for drawing the overlay)."""
        th = np.radians(np.linspace(0, self.theta_max, n))
        outer = np.stack([np.cos(th) * self.r_max, np.sin(th) * self.r_max], 1)
        inner = np.stack([np.cos(th) * self.r_min, np.sin(th) * self.r_min], 1)[::-1]
        return self.from_floor(np.concatenate([outer, inner])).tolist()

    def ray(self, theta_deg: float, r0: float | None = None, r1: float | None = None, n: int = 2):
        r = np.linspace(self.r_min if r0 is None else r0, self.r_max if r1 is None else r1, n)
        t = np.radians(theta_deg)
        return self.from_floor(np.stack([np.cos(t) * r, np.sin(t) * r], 1)).tolist()

    def from_floor(self, ab) -> np.ndarray:
        """(a, b) wedge-basis floor coordinates -> image px."""
        ab = np.asarray(ab, dtype=np.float64).reshape(-1, 2)
        if self.H is not None:
            f = np.stack([ab[:, 1], -ab[:, 0]], 1)
            Hinv = np.linalg.inv(np.asarray(self.H))
            return cv2.perspectiveTransform(f.reshape(-1, 1, 2), Hinv).reshape(-1, 2)
        c = np.asarray(self.corner_px)
        B = np.stack([np.asarray(self.wall_px) - c, np.asarray(self.open_px) - c], axis=1)
        B = B / np.linalg.norm(B, axis=0, keepdims=True)
        return (B @ ab.T).T + c


CANNY_LEVELS = ((60, 180), (40, 120), (25, 75))
MIN_AUTO_CONFIDENCE = 0.5
STEP_FULL = 2.0          # brightness step (in units of strip noise) that counts as a sure wall edge


def auto_calibrate(frame_bgr: np.ndarray) -> dict:
    """Suggest the corner and wall ray from one frame (the agent checks it; a human confirms).

    A wall corner shows up as two straight edges that end at the same point: the wall base
    (wall meets floor) and the wall's vertical edge. We look for the strongest such pair of
    Hough segments. The vertical edge is the one that rises in the image; the floor, and so the
    wedge's 90-degree ray, is on the other side of the wall base. Angles from this are only
    approximate (no metric floor plane); the tape marks give exact ones.

    Confidence is how long the two edges are (relative to the frame) times how clean a
    brightness step each one is: wall against floor is a step on both edges, while floor grain,
    tape or cables give thin lines with the same brightness on either side.
    """
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY) if frame_bgr.ndim == 3 else frame_bgr
    h, w = gray.shape
    blur = cv2.GaussianBlur(gray, (5, 5), 1.5)
    # Several edge strengths: floor grain makes many short, weak edges; the wall's are strong.
    cands = [_corner_pair(cv2.Canny(blur, lo, hi), h, w) for lo, hi in CANNY_LEVELS]
    found = [c for c in cands if c is not None]
    if not found:
        return {"corner_px": None, "confidence": 0.0, "reason": "no pair of straight edges meets at a corner"}
    score, P, vert, base = max(found, key=lambda c: c[0])
    length = float(np.clip(score / (0.6 * min(h, w)), 0, 1))
    g = gray.astype(np.float32)
    step = min(_step_contrast(g, P, base), _step_contrast(g, P, vert))
    contrast = float(np.clip(step / STEP_FULL, 0, 1))
    conf = length * contrast
    wall_dir = (base - P) / np.linalg.norm(base - P)
    perp = np.array([-wall_dir[1], wall_dir[0]])
    up = vert - P
    open_dir = perp if perp @ up < 0 else -perp
    return {"corner_px": P.tolist(), "wall_px": (P + wall_dir * 100).tolist(),
            "open_px": (P + open_dir * 100).tolist(), "vertical_px": vert.tolist(), "base_px": base.tolist(),
            "confidence": conf, "edge_length": length, "edge_step": step,
            "reason": "wall base and vertical wall edge meet at the corner"}


def _step_contrast(gray, P, far, n=48, near=3, depth=8):
    """How much of a brightness step the segment P -> far is: |mean left - mean right| / noise.

    Strips `near`..`near+depth` px either side of the segment, skipping the ends (the other
    edge meets this one at the corner).
    """
    h, w = gray.shape
    d = far - P
    L = np.linalg.norm(d)
    if L < 1:
        return 0.0
    t = d / L
    nrm = np.array([-t[1], t[0]])
    along = P + np.outer(np.linspace(0.15, 0.9, n) * L, t)                       # (n, 2)
    offs = np.arange(near, near + depth, dtype=np.float64)
    sides = []
    for sgn in (1, -1):
        pts = along[:, None, :] + sgn * offs[None, :, None] * nrm                  # (n, depth, 2)
        x = np.clip(np.round(pts[..., 0]).astype(int), 0, w - 1)
        y = np.clip(np.round(pts[..., 1]).astype(int), 0, h - 1)
        sides.append(gray[y, x])
    a, b = sides
    noise = np.sqrt(0.5 * (a.var() + b.var())) + 1.0
    return float(abs(a.mean() - b.mean()) / noise)


@dataclass
class CornerDetection:
    """Result of detect_corner: a ready Calibration, or None and the reason it was refused."""

    calibration: Calibration | None
    confidence: float
    reason: str
    suggestion: dict = field(default_factory=dict)   # auto_calibrate's raw output, for overlays

    @property
    def ok(self) -> bool:
        return self.calibration is not None


def detect_corner(frame_bgr: np.ndarray, min_confidence: float = MIN_AUTO_CONFIDENCE,
                  r_min_frac: float = 0.054, r_max_frac: float = 0.45) -> CornerDetection:
    """Corner and floor-wedge edges from one floor frame, as a ray Calibration (no tape marks).

    The wedge's two edges are the wall base (theta = 0) and the image-perpendicular to it on the
    floor side (theta = 90, approximate without a homography). Radii are fractions of the
    frame's short side. Below min_confidence it refuses rather than guess: the caller should
    fall back to the tape marks.
    """
    s = auto_calibrate(frame_bgr)
    conf = float(s["confidence"])
    if s["corner_px"] is None:
        return CornerDetection(None, conf, s["reason"], s)
    if conf < min_confidence:
        why = []
        if s["edge_step"] < STEP_FULL:
            why.append(f"edges are not a clear wall/floor brightness step ({s['edge_step']:.1f} x noise)")
        if s["edge_length"] < 1:
            why.append(f"edges are short ({s['edge_length']:.2f} of the expected length)")
        return CornerDetection(None, conf, f"low confidence {conf:.2f} < {min_confidence:.2f}: "
                               + ("; ".join(why) or "weak corner"), s)
    h, w = frame_bgr.shape[:2]
    rr = min(w, h)
    cal = Calibration.from_rays(s["corner_px"], s["wall_px"], s["open_px"], (w, h),
                                r_min=r_min_frac * rr, r_max=r_max_frac * rr)
    cal.source = "auto"
    cal.notes.append(f"auto, confidence {conf:.2f}: angles are approximate without tape marks")
    return CornerDetection(cal, conf, s["reason"], s)


def _corner_pair(edges, h, w):
    """Best pair of Hough segments that end at a shared point (the corner)."""
    lines = cv2.HoughLinesP(edges, 1, np.pi / 360, threshold=40, minLineLength=min(h, w) // 6, maxLineGap=8)
    if lines is None:
        return None
    segs = np.asarray(lines).reshape(-1, 4).astype(np.float64)       # (N,1,4) in OpenCV 4, (N,4) in 5
    segs = segs[np.argsort(-np.hypot(segs[:, 2] - segs[:, 0], segs[:, 3] - segs[:, 1]))][:16]
    tol = 0.03 * max(h, w)
    best = None
    for i in range(len(segs)):
        for j in range(i + 1, len(segs)):
            a, b = segs[i], segs[j]
            da, db = a[2:] - a[:2], b[2:] - b[:2]
            la, lb = np.linalg.norm(da), np.linalg.norm(db)
            if abs(da @ db) / (la * lb) > np.cos(np.radians(20)):
                continue
            try:
                ta, _ = np.linalg.solve(np.array([da, -db]).T, b[:2] - a[:2])
            except np.linalg.LinAlgError:
                continue
            P = a[:2] + ta * da
            ea = min(np.linalg.norm(P - a[:2]), np.linalg.norm(P - a[2:]))
            eb = min(np.linalg.norm(P - b[:2]), np.linalg.norm(P - b[2:]))
            if ea > tol or eb > tol:
                continue                                   # the edges must end at the corner
            far = lambda s_: s_[2:] if np.linalg.norm(s_[2:] - P) > np.linalg.norm(s_[:2] - P) else s_[:2]
            fa, fb = far(a), far(b)
            rise = lambda f: (P[1] - f[1]) / (np.linalg.norm(f - P) + 1e-9)
            vert, base = (fa, fb) if rise(fa) > rise(fb) else (fb, fa)
            # the wall's vertical edge goes up from the corner; the wall base goes down/sideways
            if rise(vert) < 0.6 or rise(base) > 0.2:
                continue
            score = la + lb - 2 * (ea + eb)
            if best is None or score > best[0]:
                best = (score, P, vert, base)
    return best
