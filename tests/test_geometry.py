import numpy as np

from periscope.geometry import Calibration, auto_calibrate
from periscope.render import Scene, empty_hallway


def floor_pt(theta_deg, r):
    t = np.radians(theta_deg)
    return np.array([[r * np.sin(t), -r * np.cos(t)]])     # theta from the wall (-y) toward +x


def test_marks_give_true_floor_angles(scene):
    cal = scene.calibration()
    for th in (5, 30, 45, 60, 85):
        for r in (0.3, 0.8):
            px = scene.project(floor_pt(th, r))
            a, b = cal.to_floor(px)[0]
            assert abs(np.degrees(np.arctan2(b, a)) - th) < 0.2
            assert abs(np.hypot(a, b) - r) < 0.01


def test_click_noise_costs_little_angle(scene):
    cal = scene.calibration(click_noise_px=3.0)
    errs = []
    for th in np.linspace(5, 85, 9):
        a, b = cal.to_floor(scene.project(floor_pt(th, 0.6)))[0]
        errs.append(abs(np.degrees(np.arctan2(b, a)) - th))
    assert max(errs) < 4.0


def test_scaled_and_json_roundtrip(scene):
    cal = scene.calibration()
    half = cal.scaled(0.5)
    px = scene.project(floor_pt(40, 0.5))
    assert np.allclose(cal.to_floor(px), half.to_floor(px * 0.5), atol=1e-6)
    again = Calibration.from_json(cal.to_json())
    assert np.allclose(again.to_floor(px), cal.to_floor(px))
    # the overlay outline maps back onto the wedge
    ab = cal.to_floor(np.array(cal.wedge_outline(8)))
    r = np.hypot(ab[:, 0], ab[:, 1])
    assert np.all((r > cal.r_min - 1e-6) & (r < cal.r_max + 1e-6))


def test_auto_calibrate_finds_the_corner(scene):
    frame = next(scene.render(empty_hallway(scene.fps, 0.1)))
    s = auto_calibrate(frame)
    corner = scene.marks_px()[0]
    assert s["corner_px"] is not None
    assert np.hypot(*(np.array(s["corner_px"]) - corner)) < 10
    wall = scene.marks_px()[2] - corner
    got = np.array(s["wall_px"]) - np.array(s["corner_px"])
    cosang = wall @ got / np.linalg.norm(wall) / np.linalg.norm(got)
    assert cosang > np.cos(np.radians(8))
    # the floor (90-degree side) is on the correct side of the wall
    open_true = scene.marks_px()[4] - corner
    assert (np.array(s["open_px"]) - np.array(s["corner_px"])) @ open_true > 0
