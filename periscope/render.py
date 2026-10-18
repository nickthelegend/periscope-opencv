"""Synthetic corner scene: a lit L-shaped hallway, a wall corner, a camera looking at the floor
beside the corner, and a person in strong colours walking in the hidden hallway.

The light model is the CornerCam one (Bouman et al., ICCV 2017): a Lambertian floor point at
angle theta from the wall receives light from the hidden hallway over hidden angles [0, theta].
Each pixel is ray-cast from a pinhole camera to the floor or the wall face, so the image has
real perspective, floor texture, camera noise, and optional shake, flicker and JPEG damage.

Units: radiance is relative (lit wall ~ 0.7). Pixel values are 8-bit like a phone video.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

import cv2
import numpy as np

from .geometry import MARKS_M, Calibration

PHI_FINE = np.linspace(0.0, 180.0, 1801)          # hidden-angle grid, 0.1 degree
D_PHI = np.radians(PHI_FINE[1] - PHI_FINE[0])


@dataclass
class Scene:
    width: int = 480
    height: int = 360
    fps: float = 15.0
    cam_pos: tuple = (1.05, -1.75, 1.55)          # metres, floor frame
    cam_target: tuple = (0.40, -0.40, 0.0)
    focal_px: float = 360.0
    wall_height: float = 2.4
    hall_width: float = 2.0                       # hidden hallway: 0 < y < hall_width
    hall_length: float = 14.0
    shirt_rgb: tuple = (0.82, 0.10, 0.08)         # strong red top
    person_radius: float = 0.22
    person_height: float = 1.75
    wall_rgb: tuple = (0.72, 0.70, 0.66)          # hidden hallway walls
    floor_rgb: tuple = (0.52, 0.50, 0.47)
    floor_texture: float = 0.08                   # +-8 % albedo grain
    camera_wall_rgb: tuple = (0.80, 0.78, 0.74)
    visible_light: float = 1.0                    # radiance of the camera's side of the room
    hidden_light: float = 1.0                     # lamp level in the hidden hallway
    target_dn: float = 150.0                      # mean floor level in the wedge (auto exposure, then locked)
    read_noise: float = 1.5                       # DN
    shot_noise: float = 0.02                      # DN^2 per DN
    noise_scale: float = 1.0
    shake_px: float = 0.0                         # RMS image shake
    flicker: float = 0.0                          # relative amplitude of lamp flicker
    flicker_hz: float = 2.7                       # aliased mains flicker as seen at video rate
    exposure_step: float = 0.0                    # one sudden exposure jump (relative)
    exposure_at_s: float | None = None            # when it happens (default: mid-clip)
    jpeg_quality: int | None = None
    camera_look: bool = False                     # demo dressing: concrete mottling, safety stripe,
                                                  # tape marks, skirting, vignette, lens softness, warm WB
    seed: int = 0
    _cache: dict = field(default_factory=dict, repr=False, compare=False)

    # ---- camera -------------------------------------------------------------------
    def _basis(self):
        C = np.asarray(self.cam_pos, float)
        f = np.asarray(self.cam_target, float) - C
        f /= np.linalg.norm(f)
        right = np.cross(f, [0, 0, 1.0])
        right /= np.linalg.norm(right)
        down = np.cross(f, right)
        return C, f, right, down

    def project(self, pts_floor) -> np.ndarray:
        """Floor points (N,2) or (N,3) metres -> image px."""
        P = np.asarray(pts_floor, float)
        if P.shape[1] == 2:
            P = np.concatenate([P, np.zeros((len(P), 1))], 1)
        C, f, right, down = self._basis()
        d = P - C
        z = d @ f
        return np.stack([self.width / 2 + self.focal_px * (d @ right) / z,
                         self.height / 2 + self.focal_px * (d @ down) / z], 1)

    def marks_px(self, click_noise_px: float = 0.0, seed: int = 1) -> np.ndarray:
        px = self.project(MARKS_M)
        if click_noise_px:
            px = px + np.random.default_rng(seed).normal(0, click_noise_px, px.shape)
        return px

    def calibration(self, click_noise_px: float = 0.0, r_min=0.12, r_max=1.0) -> Calibration:
        return Calibration.from_marks(self.marks_px(click_noise_px), (self.width, self.height), r_min, r_max)

    # ---- static maps ----------------------------------------------------------------
    def _static(self):
        if "static" in self._cache:
            return self._cache["static"]
        W, H = self.width, self.height
        C, f, right, down = self._basis()
        u, v = np.meshgrid(np.arange(W) + 0.5, np.arange(H) + 0.5)
        d = f[None, None] + ((u - W / 2) / self.focal_px)[..., None] * right + ((v - H / 2) / self.focal_px)[..., None] * down
        with np.errstate(divide="ignore", invalid="ignore"):
            t_floor = np.where(d[..., 2] < 0, -C[2] / d[..., 2], np.inf)
            t_wall = np.where(d[..., 0] < 0, -C[0] / d[..., 0], np.inf)
        yw = C[1] + t_wall * d[..., 1]
        zw = C[2] + t_wall * d[..., 2]
        wall = (t_wall < t_floor) & (yw < 0) & (zw > 0) & (zw < self.wall_height)
        X = C[0] + t_floor * d[..., 0]
        Y = C[1] + t_floor * d[..., 1]
        floor = ~wall & np.isfinite(t_floor) & (Y < self.hall_width) & ((X >= 0) | (Y > 0))
        wall |= ~floor            # everything else we treat as static wall / far wall
        # A sliver of the hidden hallway's floor is visible past the corner. It is outside the
        # wedge; we keep it static (the walker's pause point is chosen so the camera never sees
        # the person directly).
        hidden_floor = floor & (X < 0)
        theta = np.degrees(np.arctan2(X, -Y))
        theta = np.where(floor & ~hidden_floor, np.clip(theta, 0, 180), 0)
        theta = np.where(hidden_floor, 180.0, theta)          # it sees the whole hidden side
        idx = np.clip(np.round(theta / 0.1).astype(int), 0, len(PHI_FINE) - 1)

        # Floor albedo: blurred noise in floor coordinates (2 cm grain), slight colour.
        rng = np.random.default_rng(1234)
        tex = cv2.GaussianBlur(rng.normal(0, 1, (400, 400)).astype(np.float32), (0, 0), 1.2)
        tex /= tex.std()
        ok = np.isfinite(X) & np.isfinite(Y)
        ti = np.where(ok, np.nan_to_num(X + 1) / 0.01, 0).astype(int) % 400
        tj = np.where(ok, np.nan_to_num(Y + 3) / 0.01, 0).astype(int) % 400
        grain = np.where(floor, tex[tj, ti], 0)
        albedo = np.asarray(self.floor_rgb)[None, None] * (1 + self.floor_texture * grain)[..., None]
        if self.camera_look:
            albedo = self._dress_floor(albedo, X, Y, floor, ok)

        # Light from the camera's side of the room: a ceiling lamp plus ambient (static).
        lamp = np.array([1.1, -1.4, 2.6])
        rr = (X - lamp[0]) ** 2 + (Y - lamp[1]) ** 2 + lamp[2] ** 2
        e_vis = 0.5 * np.pi * self.visible_light * (0.55 + 0.45 * (lamp[2] ** 3 / rr ** 1.5) / 1.0)
        e_vis = np.where(floor, e_vis, 0)

        # Wall pixels: lit flat paint with a gentle gradient, unaffected by the hidden scene.
        wall_val = np.asarray(self.camera_wall_rgb)[None, None] * (0.55 + 0.15 * (v / H))[..., None]
        optics = np.ones((H, W, 3))
        if self.camera_look:
            skirting = wall & (zw > 0) & (zw < 0.09) & (yw < 0)
            wall_val = np.where(skirting[..., None], np.array([0.20, 0.20, 0.21])[None, None], wall_val)
            rr2 = ((u - W / 2) ** 2 + (v - H / 2) ** 2) / ((W / 2) ** 2 + (H / 2) ** 2)
            optics = (1 - 0.38 * rr2 ** 1.3)[..., None] * np.array([1.05, 1.0, 0.93])[None, None]

        st = dict(floor=floor, wall=wall, theta=theta, idx=idx, albedo=albedo, e_vis=e_vis,
                  wall_val=wall_val, X=X, Y=Y, optics=optics)
        # Exposure: put the wedge's mean at target_dn with an empty hallway.
        cal = self.calibration()
        th, r = cal.polar_maps(W, H)
        wedge = floor & (th > 2) & (th < 88) & (r > cal.r_min) & (r < cal.r_max)
        st["wedge"] = wedge
        self._cache["static"] = st
        L0 = self.hidden_radiance(None)
        E0 = self._irradiance(st, L0)
        st["gain"] = self.target_dn / float((albedo * E0 * optics)[wedge].mean())
        return st

    # ---- hidden hallway -------------------------------------------------------------
    def _hall_light(self, x):
        """Illumination along the hidden hallway (lamps near the corner, dimmer far away)."""
        return self.hidden_light * (0.45 + 0.55 * np.exp(-np.abs(x) / 5.0))

    def hidden_radiance(self, person_xy):
        """Elevation-integrated radiance per hidden angle, (len(PHI_FINE), 3)."""
        phi = PHI_FINE
        wall = np.asarray(self.wall_rgb)
        with np.errstate(divide="ignore", invalid="ignore"):
            x_hit = -self.hall_width * np.tan(np.radians(np.minimum(phi, 89.9)))
        x_hit = np.maximum(x_hit, -self.hall_length)
        L_bg = wall[None] * self._hall_light(x_hit)[:, None]
        # beyond 90 degrees the floor point sees the hallway's near wall: constant
        L_bg[phi > 90] = wall * self._hall_light(-1.0)
        L = 0.5 * L_bg
        if person_xy is not None and np.all(np.isfinite(person_xy)):
            px, py = person_xy
            d = np.hypot(px, py)
            phi_p = np.degrees(np.arctan2(py, px)) - 90.0
            half = np.degrees(np.arcsin(min(self.person_radius / max(d, 1e-3), 1.0)))
            # fractional angular coverage (anti-aliased box)
            cov = np.clip((half - np.abs(phi - phi_p)) / 0.1 + 0.5, 0, 1)
            # rounded body: thinner at the edges
            cov *= np.sqrt(np.clip(1 - ((phi - phi_p) / max(half, 1e-6)) ** 2, 0, 1)) * 0.5 + 0.5
            elev = np.arctan2(self.person_height, d)
            frac = np.sin(elev) ** 2
            # body is lit from the side by the hallway lamps: a little shading
            L_p = np.asarray(self.shirt_rgb) * self._hall_light(px) * 0.9
            L = L + (0.5 * frac * cov)[:, None] * (L_p[None] - L_bg)
        return L

    @staticmethod
    def _irradiance(st, L):
        cum = np.cumsum(L, axis=0) * D_PHI                     # (n_phi, 3)
        return st["e_vis"][..., None] + cum[st["idx"]]

    def reference_signal(self, distance=3.0):
        """Per-pixel change (DN, RMS over colour) a person at `distance` makes at theta = 90."""
        st = self._static()
        y = self.hall_width * 0.55
        x = -np.sqrt(max(distance ** 2 - y ** 2, 0.01))
        dL = (self.hidden_radiance((x, y)) - self.hidden_radiance(None)).sum(0) * D_PHI
        mean_alb = np.asarray(self.floor_rgb)
        return float(np.sqrt(np.mean((st["gain"] * mean_alb * dL) ** 2)))

    def pixel_noise(self, level=None):
        level = self.target_dn if level is None else level
        return self.noise_scale * np.sqrt(self.read_noise ** 2 + self.shot_noise * level)

    def snr(self, distance=3.0):
        """Per-pixel SNR of the reference person: the number the sweep is indexed by."""
        return self.reference_signal(distance) / self.pixel_noise()

    # ---- frames -----------------------------------------------------------------------
    def render(self, positions):
        """Yield uint8 BGR frames for a (T, 2) array of person positions (NaN = nobody)."""
        st = self._static()
        rng = np.random.default_rng(self.seed)
        W, H = self.width, self.height
        T = len(positions)
        for t in range(T):
            pos = positions[t]
            L = self.hidden_radiance(pos if np.all(np.isfinite(pos)) else None)
            light = 1.0 + self.flicker * np.sin(2 * np.pi * self.flicker_hz * t / self.fps)
            t_jump = T // 2 if self.exposure_at_s is None else int(self.exposure_at_s * self.fps)
            if self.exposure_step and t >= t_jump:
                light *= 1 + self.exposure_step
            E = self._irradiance(st, L)
            img = st["gain"] * st["albedo"] * E
            img = np.where(st["wall"][..., None], st["gain"] * st["wall_val"] * 1.0, img) * light
            if self.camera_look:
                img = cv2.GaussianBlur((img * st["optics"]).astype(np.float32), (0, 0), 0.7).astype(np.float64)
            if self.shake_px:
                dx, dy = rng.normal(0, self.shake_px, 2)
                M = np.float32([[1, 0, dx], [0, 1, dy]])
                img = cv2.warpAffine(img.astype(np.float32), M, (W, H), flags=cv2.INTER_LINEAR,
                                     borderMode=cv2.BORDER_REFLECT)
            sigma = self.noise_scale * np.sqrt(self.read_noise ** 2 + self.shot_noise * np.maximum(img, 0))
            img = img + rng.standard_normal(img.shape) * sigma
            frame = np.clip(np.round(img), 0, 255).astype(np.uint8)[..., ::-1]   # RGB -> BGR
            frame = np.ascontiguousarray(frame)
            if self.jpeg_quality:
                ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, int(self.jpeg_quality)])
                frame = cv2.imdecode(buf, cv2.IMREAD_COLOR)
            yield frame

    @staticmethod
    def _dress_floor(albedo, X, Y, floor, ok):
        """Make the floor read as a real one: concrete mottling, a yellow lane stripe along the
        wall (outside the wedge) and the five calibration tape crosses. All static, so the
        empty-hallway background removes them exactly as it would on a real floor."""
        rng = np.random.default_rng(77)
        mott = cv2.GaussianBlur(rng.normal(0, 1, (300, 300)).astype(np.float32), (0, 0), 14)
        mott /= mott.std()
        mi = np.where(ok, np.nan_to_num(X + 1) / 0.02, 0).astype(int) % 300
        mj = np.where(ok, np.nan_to_num(Y + 3) / 0.02, 0).astype(int) % 300
        a = albedo * (1 + 0.07 * np.where(floor, mott[mj, mi], 0))[..., None]
        Xn, Yn = np.nan_to_num(X), np.nan_to_num(Y)
        stripe = floor & (Xn > 1.28) & (Xn < 1.38) & (Yn < -0.05)
        a = np.where(stripe[..., None], np.array([0.78, 0.62, 0.10])[None, None], a)
        tape = np.zeros_like(floor)
        for mx, my in MARKS_M[:5]:
            dx, dy = np.abs(Xn - mx), np.abs(Yn - my)
            tape |= floor & (((dx < 0.035) & (dy < 0.007)) | ((dy < 0.035) & (dx < 0.007)))
        return np.where(tape[..., None], np.array([0.15, 0.42, 0.80])[None, None], a)

    def with_(self, **kw) -> "Scene":
        return replace(self, _cache={}, **kw)


# ---- trajectories ------------------------------------------------------------------------

def approach_and_leave(fps=15.0, empty_s=2.5, speed=1.3, y=1.1, x_far=-8.0, x_near=-0.8,
                       pause_s=1.0, tail_s=2.0):
    """Empty hallway, then a person walks toward the corner, pauses, and walks back.

    The pause point (0.8 m short of the corner line) is still out of the corner camera's direct
    line of sight, so everything the camera knows comes from the floor shadow.
    """
    n_empty = int(empty_s * fps)
    n_walk = int(abs(x_far - x_near) / speed * fps)
    n_pause = int(pause_s * fps)
    n_tail = int(tail_s * fps)
    xs = np.concatenate([np.full(n_empty, np.nan), np.linspace(x_far, x_near, n_walk),
                         np.full(n_pause, x_near), np.linspace(x_near, x_far, n_walk), np.full(n_tail, np.nan)])
    pos = np.stack([xs, np.where(np.isfinite(xs), y, np.nan)], 1)
    return pos


def empty_hallway(fps=15.0, seconds=12.0):
    return np.full((int(seconds * fps), 2), np.nan)


def truth_angles(positions):
    """Hidden angle phi (deg) and distance from the corner for each position."""
    x, y = positions[:, 0], positions[:, 1]
    phi = np.degrees(np.arctan2(y, x)) - 90.0
    d = np.hypot(x, y)
    return phi, d


# ---- a second camera that films the hidden hallway (synthetic ground truth) --------------

GT_MARKS_M = np.array([[-1.0, 0.4], [-1.0, 1.6], [-5.0, 0.4], [-5.0, 1.6]])


@dataclass
class GroundTruthCamera:
    """Looks down the hidden hallway toward the corner, like the protocol's second phone."""

    width: int = 480
    height: int = 270
    cam_pos: tuple = (-9.5, 1.0, 2.3)
    cam_target: tuple = (-1.5, 1.0, 0.0)
    focal_px: float = 330.0
    hall_width: float = 2.0
    noise: float = 2.0
    seed: int = 0

    def _basis(self):
        return Scene._basis(self)

    def project(self, P):
        return Scene.project(self, P)

    def marks_px(self):
        return self.project(GT_MARKS_M)

    def _background(self):
        W, H = self.width, self.height
        C, f, right, down = self._basis()
        u, v = np.meshgrid(np.arange(W) + 0.5, np.arange(H) + 0.5)
        d = f[None, None] + ((u - W / 2) / self.focal_px)[..., None] * right + ((v - H / 2) / self.focal_px)[..., None] * down
        with np.errstate(divide="ignore", invalid="ignore"):
            t = np.where(d[..., 2] < 0, -C[2] / d[..., 2], np.inf)
        X, Y = C[0] + t * d[..., 0], C[1] + t * d[..., 1]
        floor = np.isfinite(t) & (Y > 0) & (Y < self.hall_width) & (X < 1.5)
        rng = np.random.default_rng(5)
        tex = cv2.GaussianBlur(rng.normal(0, 1, (300, 300)).astype(np.float32), (0, 0), 1.5)
        ti = (np.nan_to_num(X, posinf=0, neginf=0) / 0.03).astype(int) % 300
        tj = (np.nan_to_num(Y, posinf=0, neginf=0) / 0.03).astype(int) % 300
        img = np.where(floor[..., None], (np.array([118, 122, 126]) * (1 + 0.06 * tex[tj, ti])[..., None]),
                       np.array([175, 178, 182]) * (0.8 + 0.2 * (v / H))[..., None])
        for m in self.marks_px():           # the tape marks
            cv2.circle(img, (int(m[0]), int(m[1])), 3, (40, 200, 230), -1)
        return img.astype(np.float32)

    def render(self, positions, shirt_rgb=(0.82, 0.10, 0.08), radius=0.22, height=1.75):
        bg = self._background()
        rng = np.random.default_rng(self.seed)
        ang = np.linspace(0, 2 * np.pi, 24, endpoint=False)
        shirt = (np.array(shirt_rgb[::-1]) * 230).tolist()
        legs = [50, 45, 40]
        for p in positions:
            img = bg.copy()
            if np.all(np.isfinite(p)):
                for z0, z1, col in ((0.0, 0.85, legs), (0.85, height, shirt)):
                    pts = [[p[0] + radius * np.cos(a), p[1] + radius * np.sin(a), z] for z in (z0, z1) for a in ang]
                    px = self.project(np.array(pts)).astype(np.int32)
                    cv2.fillConvexPoly(img, cv2.convexHull(px), col, cv2.LINE_AA)
            img = img + rng.normal(0, self.noise, img.shape)
            yield np.clip(img, 0, 255).astype(np.uint8)
