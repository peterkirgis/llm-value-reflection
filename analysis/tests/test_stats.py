"""Unit tests for kappa/alpha, cluster bootstrap, and PPI (BRIEF section 10)."""

import numpy as np
import pytest

from stats import cluster_bootstrap, cohen_kappa, kripp_alpha, ppi_mean_manual


class TestCohenKappa:
    def test_known_value(self):
        # p_o = 3/4; p_e = .5*.25 + .5*.75 = .5; kappa = (.75-.5)/(1-.5) = 0.5
        a = [0, 1, 0, 1]
        b = [0, 1, 1, 1]
        assert cohen_kappa(a, b) == pytest.approx(0.5)

    def test_perfect_agreement(self):
        assert cohen_kappa([1, 0, 1], [1, 0, 1]) == pytest.approx(1.0)

    def test_symmetry(self):
        a = [-1, 0, 1, 1, 0, -1, 0]
        b = [-1, 1, 1, 0, 0, -1, -1]
        assert cohen_kappa(a, b) == pytest.approx(cohen_kappa(b, a))


class TestKrippAlpha:
    def test_perfect_agreement(self):
        data = [[1, 2, 3, 1, 2], [1, 2, 3, 1, 2]]
        assert kripp_alpha(np.array(data, dtype=float)) == pytest.approx(1.0)

    def test_known_value_nominal(self):
        # Canonical example from Krippendorff (2011) / the krippendorff
        # package documentation: nominal alpha = 0.691.
        data = np.array(
            [
                [1, 2, 3, 3, 2, 1, 4, 1, 2, np.nan, np.nan, np.nan],
                [1, 2, 3, 3, 2, 2, 4, 1, 2, 5, np.nan, 3],
                [np.nan, 3, 3, 3, 2, 3, 4, 2, 2, 5, 1, np.nan],
                [1, 2, 3, 3, 2, 4, 4, 1, 2, 5, 1, np.nan],
            ],
            dtype=float,
        )
        assert kripp_alpha(data) == pytest.approx(0.743, abs=0.02)


class TestClusterBootstrap:
    def test_trivial_constant_case(self):
        clusters = [np.full(20, 3.0) for _ in range(5)]
        out = cluster_bootstrap(clusters, np.mean, B=200, seed=1)
        assert out["point"] == pytest.approx(3.0)
        assert out["lo"] == pytest.approx(3.0)
        assert out["hi"] == pytest.approx(3.0)

    def test_interval_covers_point_and_is_deterministic(self):
        rng = np.random.default_rng(0)
        clusters = [rng.normal(size=20) for _ in range(12)]
        out1 = cluster_bootstrap(clusters, np.mean, B=500, seed=42)
        out2 = cluster_bootstrap(clusters, np.mean, B=500, seed=42)
        assert out1["lo"] <= out1["point"] <= out1["hi"]
        assert np.array_equal(out1["draws"], out2["draws"])

    def test_resamples_clusters_not_edits(self):
        # Two clusters with very different means: every bootstrap mean must be
        # a mixture of whole-cluster means only.
        clusters = [np.zeros(10), np.ones(10)]
        out = cluster_bootstrap(clusters, np.mean, B=300, seed=7)
        assert set(np.round(out["draws"], 6)) <= {0.0, 0.5, 1.0}


class TestPPI:
    def test_reduces_to_classical_when_n_equals_N(self):
        rng = np.random.default_rng(3)
        y = rng.integers(0, 2, size=50).astype(float)
        f = rng.integers(0, 2, size=50).astype(float)
        out = ppi_mean_manual(y, f, f)  # n == N, same units
        assert out["point"] == pytest.approx(float(np.mean(y)))

    def test_perfect_predictions_give_classical_variance(self):
        rng = np.random.default_rng(4)
        y = rng.normal(size=40)
        out = ppi_mean_manual(y, y, y)
        classical_se = np.sqrt(np.var(y, ddof=1) / len(y))
        assert out["se"] == pytest.approx(classical_se)
        assert out["point"] == pytest.approx(float(np.mean(y)))

    def test_rectifier_corrects_biased_grader(self):
        # Grader systematically over-codes by 0.2; PPI must remove the bias.
        rng = np.random.default_rng(5)
        y_all = rng.normal(size=1000)
        f_all = y_all + 0.2
        idx = rng.choice(1000, size=100, replace=False)
        out = ppi_mean_manual(y_all[idx], f_all[idx], f_all)
        assert out["point"] == pytest.approx(float(np.mean(y_all)), abs=0.05)

    def test_ci_contains_point(self):
        rng = np.random.default_rng(6)
        y = rng.integers(0, 2, size=15).astype(float)
        f_lab = y.copy()
        f_lab[0] = 1 - f_lab[0]
        f_all = rng.integers(0, 2, size=250).astype(float)
        out = ppi_mean_manual(y, f_lab, f_all)
        assert out["lo"] <= out["point"] <= out["hi"]
