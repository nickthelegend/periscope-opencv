import numpy as np

from periscope.recon import Reconstructor, forward_matrix


def test_forward_matrix_is_cumulative():
    A = forward_matrix(np.array([0.0, 45.0, 90.0]), np.linspace(0, 90, 4))
    assert np.allclose(A[0], 0)
    assert np.allclose(np.degrees(A[1]), [30, 15, 0])
    assert np.allclose(np.degrees(A[2]), [30, 30, 30])


def test_inverse_recovers_a_hidden_object_and_ignores_global_light(scene):
    rec = Reconstructor(scene.calibration(), scene.width, scene.height)
    assert rec.binner.n_pixels > 8000
    x_true = np.zeros((rec.n_phi, 3))
    j = int(np.argmin(np.abs(rec.phi - 41)))
    x_true[j - 1:j + 2] = [[0.02, -0.05, -0.04]]
    y = rec.A @ x_true + 0.03                                   # +3 % lamp change everywhere
    x, b = rec.solve(y)
    assert abs(rec.phi[np.argmax(np.abs(x).sum(1))] - 41) <= 2.5
    assert np.allclose(b, 0.03, atol=0.003)
    # colour survives: red up, green and blue down
    s = x[j - 2:j + 3].sum(0)
    assert s[0] > 0 and s[1] < 0 and s[2] < 0


def test_noise_prediction_matches_monte_carlo(scene):
    rec = Reconstructor(scene.calibration(), scene.width, scene.height)
    rng = np.random.default_rng(0)
    var = np.array([1e-4, 1e-4, 1e-4])
    bin_std = np.sqrt(var[None, None] / np.maximum(rec.binner.counts, 1)[None, :, None])
    ys = rng.normal(0, 1, (400, rec.binner.n_bins, 3)) * bin_std
    xs = np.einsum("pm,tmc->tpc", rec.M[:-1], ys)
    pred = rec.x_sigma(var)
    ratio = xs.std(0) / pred
    assert 0.85 < ratio.mean() < 1.15
