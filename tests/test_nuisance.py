"""Things a real corner throws at it: shake, flicker, a lamp switching, compression."""

import pytest

from conftest import approach, empty, score_track


@pytest.mark.parametrize("kw", [dict(shake_px=1.0), dict(flicker=0.02), dict(exposure_step=0.05)],
                         ids=["shake-1px", "flicker-2pct", "exposure-jump"])
def test_survives(scene, kw):
    s = scene.with_(**kw)
    _, recs, phi, d = approach(s)
    near = score_track(recs, phi, d, s.fps, d_max=3.0)
    assert near["recall"] >= 0.9 and near["angle_mae_deg"] <= 6.0
    assert score_track(recs, phi, d, s.fps, d_max=8.0)["false_alarm_rate"] == 0.0
    _, _, fa = empty(s, seconds=12.0)
    assert fa == 0.0


@pytest.mark.parametrize("seed", [1, 2])
def test_shake_is_robust_across_seeds(scene, seed):
    s = scene.with_(shake_px=1.0, seed=seed)
    _, _, fa = empty(s, seconds=14.0)
    assert fa == 0.0
    _, recs, phi, d = approach(s)
    assert score_track(recs, phi, d, s.fps, d_max=8.0)["false_alarm_rate"] == 0.0


def test_lamp_switch_makes_the_agent_relearn(scene):
    s = scene.with_(exposure_step=0.05, exposure_at_s=6.0)
    eng, recs, fa = empty(s, seconds=12.0)
    assert any(e["action"] == "relearn_background" for e in eng.events)
    assert fa == 0.0


def test_without_stabilisation_shake_is_flagged(scene):
    s = scene.with_(shake_px=1.0)
    eng, recs, _ = empty(s, seconds=6.0)
    q = eng.assess()
    assert q["metrics"]["shake_px"] > 0.6
    assert {c["name"]: c["ok"] for c in q["checks"]}["shake"] is False
