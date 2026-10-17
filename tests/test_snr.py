"""Recovered angle vs truth across SNR: where is the signal floor?

Per-pixel SNR is the change a person 3 m from the corner makes on one floor pixel divided by that
pixel's noise. A phone in a lit room is ~0.2 (noise x1); tools/snr_sweep.py puts the floor at
~0.05 (noise x4). These tests pin both sides of it.
"""

import pytest

from conftest import approach, empty, score_track


@pytest.mark.parametrize("noise", [1.0, 3.0])
def test_above_the_floor_tracks_the_hidden_person(scene, noise):
    s = scene.with_(noise_scale=noise)
    _, recs, phi, d = approach(s)
    near = score_track(recs, phi, d, s.fps, d_max=3.0)
    far = score_track(recs, phi, d, s.fps, d_max=8.0)
    assert near["recall"] >= 0.9
    assert near["angle_mae_deg"] <= 6.0
    assert near["angle_p90_deg"] <= 12.0
    assert far["false_alarm_rate"] == 0.0
    assert far["first_detect_distance_m"] >= 2.5          # seen well before the corner
    assert far["lead_time_s"] >= 1.0                       # "someone is coming" with time to stop


def test_nominal_conditions_give_real_warning(scene):
    _, recs, phi, d = approach(scene)
    far = score_track(recs, phi, d, scene.fps, d_max=8.0)
    assert scene.snr(3.0) == pytest.approx(0.21, abs=0.02)
    assert far["first_detect_distance_m"] >= 3.5
    assert far["lead_time_s"] >= 2.0


def test_range_shrinks_as_noise_grows(scene):
    firsts = []
    for noise in (0.5, 2.0, 8.0):
        s = scene.with_(noise_scale=noise)
        _, recs, phi, d = approach(s)
        firsts.append(score_track(recs, phi, d, s.fps, d_max=8.0)["first_detect_distance_m"] or 0.0)
    assert firsts[0] > firsts[1] > firsts[2]


def test_below_the_floor_fails_safe(scene):
    """At SNR ~0.017 the person is only seen very close, and it never invents one."""
    s = scene.with_(noise_scale=12.0)
    _, recs, phi, d = approach(s)
    far = score_track(recs, phi, d, s.fps, d_max=8.0)
    assert (far["first_detect_distance_m"] or 0) < 2.0
    assert far["false_alarm_rate"] == 0.0


@pytest.mark.parametrize("noise", [1.0, 12.0])
def test_empty_hallway_raises_no_alarm(scene, noise):
    _, recs, fa = empty(scene.with_(noise_scale=noise), seconds=15.0)
    assert fa == 0.0
    assert not any(r["coming"] for r in recs)
