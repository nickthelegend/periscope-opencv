import numpy as np
import pytest

from periscope.pipeline import run_frames, score_track
from periscope.render import Scene, approach_and_leave, empty_hallway, truth_angles


def approach(scene: Scene, **engine_kw):
    pos = approach_and_leave(scene.fps)
    phi, d = truth_angles(pos)
    eng, recs = run_frames(scene.render(pos), scene.calibration(), scene.fps, (scene.width, scene.height),
                           keep_x=False, **engine_kw)
    return eng, recs, phi, d


def empty(scene: Scene, seconds=15.0):
    eng, recs = run_frames(scene.with_(seed=scene.seed + 100).render(empty_hallway(scene.fps, seconds)),
                           scene.calibration(), scene.fps, (scene.width, scene.height), keep_x=False)
    live = [r for r in recs if r["state"] != "learning"]
    return eng, recs, float(np.mean([r["present"] for r in live]))


@pytest.fixture(scope="session")
def scene():
    return Scene()


__all__ = ["approach", "empty", "score_track"]
