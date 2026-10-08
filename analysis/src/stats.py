"""Statistical primitives for the re-coding workstreams (BRIEF section 10, Appendix VI).

- Cohen's kappa: sklearn.metrics.cohen_kappa_score.
- Krippendorff's alpha: the krippendorff package, nominal metric, np.nan missing.
- Cluster bootstrap: runs are the resampling unit (BRIEF Workstream D).
- PPI mean: ppi_py when available, with the Appendix VI manual estimator as
  the tested fallback.
"""

from __future__ import annotations

import numpy as np
from sklearn.metrics import cohen_kappa_score


def cohen_kappa(labels_a, labels_b) -> float:
    return float(cohen_kappa_score(labels_a, labels_b))


def kripp_alpha(reliability_data, level_of_measurement: str = "nominal") -> float:
    """reliability_data: rows = raters, columns = units, np.nan for missing."""
    import krippendorff

    return float(
        krippendorff.alpha(
            reliability_data=reliability_data,
            level_of_measurement=level_of_measurement,
        )
    )


def cluster_bootstrap(
    clusters: list[np.ndarray],
    stat_fn,
    B: int = 2000,
    seed: int = 0,
    ci: float = 0.95,
) -> dict:
    """Resample whole clusters (runs) with replacement, within one stratum.

    stat_fn receives the concatenation of the drawn clusters and returns a
    scalar (or ndarray) statistic. Returns point estimate, percentile CI
    bounds, and the raw bootstrap draws.
    """
    clusters = [np.asarray(c) for c in clusters]
    rng = np.random.default_rng(seed)
    k = len(clusters)
    point = stat_fn(np.concatenate(clusters))
    draws = []
    for _ in range(B):
        idx = rng.integers(0, k, size=k)
        draws.append(stat_fn(np.concatenate([clusters[i] for i in idx])))
    draws = np.asarray(draws)
    lo_q, hi_q = (1 - ci) / 2, 1 - (1 - ci) / 2
    return {
        "point": point,
        "lo": np.quantile(draws, lo_q, axis=0),
        "hi": np.quantile(draws, hi_q, axis=0),
        "draws": draws,
    }


def ppi_mean_manual(
    y_labeled: np.ndarray,
    f_labeled: np.ndarray,
    f_unlabeled_all: np.ndarray,
    alpha: float = 0.05,
) -> dict:
    """Appendix VI PPI mean estimator.

    y_labeled: n human labels; f_labeled: grader labels on the same n units;
    f_unlabeled_all: grader labels on ALL N units of the stratum (the labeled
    subsample's grader labels included).
    """
    from scipy.stats import norm

    y = np.asarray(y_labeled, dtype=float)
    f_lab = np.asarray(f_labeled, dtype=float)
    f_all = np.asarray(f_unlabeled_all, dtype=float)
    n, N = len(y), len(f_all)
    rectifier = float(np.mean(f_lab - y))
    point = float(np.mean(f_all)) - rectifier
    var = np.var(f_all, ddof=1) / N + np.var(f_lab - y, ddof=1) / n if n > 1 else np.nan
    z = norm.ppf(1 - alpha / 2)
    half = z * np.sqrt(var)
    return {"point": point, "lo": point - half, "hi": point + half, "se": float(np.sqrt(var))}


def ppi_mean(
    y_labeled,
    f_labeled,
    f_unlabeled_all,
    alpha: float = 0.05,
) -> dict:
    """Prefer ppi_py (PPI++ tuning); fall back to the manual estimator."""
    try:
        from ppi_py import ppi_mean_ci, ppi_mean_pointestimate

        y = np.asarray(y_labeled, dtype=float)
        f_lab = np.asarray(f_labeled, dtype=float)
        f_all = np.asarray(f_unlabeled_all, dtype=float)
        point = float(ppi_mean_pointestimate(y, f_lab, f_all))
        lo, hi = ppi_mean_ci(y, f_lab, f_all, alpha=alpha)
        return {"point": point, "lo": float(lo), "hi": float(hi), "impl": "ppi_py"}
    except Exception:  # noqa: BLE001  (package missing or shape issue)
        return {**ppi_mean_manual(y_labeled, f_labeled, f_unlabeled_all, alpha), "impl": "manual"}
