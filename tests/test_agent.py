from periscope import quality


def base(**kw):
    m = dict(noise_pct=1.5, shake_px=0.05, drift_px=0.1, offset_pct=0.0, clip_pct=0.0, wedge_px=15000,
             range_m=4.0, coming=False)
    m.update(kw)
    return m


def test_decisions_follow_the_numbers():
    assert quality.assess(base())["action"] == "watch"
    assert quality.assess(base(coming=True))["action"] == "stop_vehicle"
    assert quality.assess(base(drift_px=6.0))["action"] == "recalibrate"
    assert quality.assess(base(offset_pct=3.0))["action"] == "relearn_background"
    assert quality.assess(base(shake_px=1.5))["action"] == "steady_camera"
    assert quality.assess(base(range_m=1.2))["action"] == "add_light"
    assert quality.assess(base(wedge_px=1500))["action"] == "reframe"


def test_every_decision_cites_its_evidence():
    q = quality.assess(base(range_m=1.2))
    bad = [c for c in q["checks"] if not c["ok"]]
    assert bad and all(c["value"] is not None and c["detail"] for c in bad)


def test_predicted_range_falls_with_noise():
    a = quality.predicted_range_m(0.015, 15000)
    b = quality.predicted_range_m(0.06, 15000)
    assert a > b > 0
    assert 3.0 < a < 6.0         # matches the synthetic first-detection range at nominal noise


def test_engine_reports_range_in_the_right_ballpark(scene):
    from conftest import empty
    eng, _, _ = empty(scene, seconds=4.0)
    m = eng.metrics()
    assert 3.0 < m["range_m"] < 6.5
    eng4, _, _ = empty(scene.with_(noise_scale=4.0), seconds=4.0)
    assert eng4.metrics()["range_m"] < m["range_m"]
