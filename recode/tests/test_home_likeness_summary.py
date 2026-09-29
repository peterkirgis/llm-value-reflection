"""Tests for recode/src/home_likeness_summary.py."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "recode" / "src"))
import home_likeness as hl  # noqa: E402
import home_likeness_summary as hs  # noqa: E402


@pytest.fixture(scope="module")
def frame():
    return hl.load_frame(hl.CODES_DIR / "ensemble.jsonl")


# ---------------------------------------------------------------------------
# Reproduces the committed four-panel analysis
# ---------------------------------------------------------------------------

def test_averages_reproduce_committed_analysis(frame):
    res = hl.analyze(frame, hl.ALL_IDX, run_perm=False)
    dist = {d: res["per_doc"][d]["distance"] for d in hl.DOC_IDS}
    avg = hs.average_foreign(dist)
    assert set(avg) == set(res["visitor_avg"])
    for m, v in res["visitor_avg"].items():
        assert avg[m] == v["mean"]  # exactly, same arithmetic
        assert v["n_docs"] == 3
        assert round(avg[m], 3) == hs.COMMITTED_AVG[m]


def test_profile_path_matches_analyze(frame):
    """The bootstrap's profile -> distance path equals hl.analyze on the observed data."""
    res = hl.analyze(frame, hl.ALL_IDX, run_perm=False)
    prof = {k: v.mean(axis=0) for k, v in hs.cell_arrays(frame).items()}
    dist = hs.distances_from_profiles(prof)
    for d in hl.DOC_IDS:
        for m, v in res["per_doc"][d]["distance"].items():
            assert dist[d][m] == pytest.approx(v, abs=1e-12)


def test_reference_line_is_mean_home_loo(frame):
    res = hl.analyze(frame, hl.ALL_IDX, run_perm=False)
    loo = [res["per_doc"][d]["distance"][h] for d in hl.DOC_IDS for h in res["per_doc"][d]["homes"]]
    assert len(loo) == 10
    dist = {d: res["per_doc"][d]["distance"] for d in hl.DOC_IDS}
    assert np.mean(hs.within_family(dist)) == pytest.approx(np.mean(loo), abs=1e-12)


# ---------------------------------------------------------------------------
# Block bootstrap
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("n", [5, 7, 16, 20])
def test_block_indices_length_and_contiguity(n):
    rng = np.random.default_rng(0)
    idx = hs.block_indices(n, 300, rng, block=5)
    assert idx.shape == (300, n)
    assert idx.min() >= 0 and idx.max() < n
    L = min(5, n)
    for row in idx:
        for start in range(0, n, L):
            blk = row[start:start + L]
            assert np.all(np.diff(blk) == 1), blk  # each block is a contiguous run of rounds


def test_block_indices_cover_all_starts():
    idx = hs.block_indices(20, 2000, np.random.default_rng(1), block=5)
    starts = idx[:, ::5].ravel()
    assert set(starts.tolist()) == set(range(16))  # overlapping (moving) blocks


def test_cell_arrays_preserve_run_lengths_and_round_order(frame):
    arrays = hs.cell_arrays(frame)
    assert len(arrays) == 40
    for (m, d), X in arrays.items():
        es = sorted((e for e in frame if e["model"] == m and e["doc"] == d), key=lambda e: e["round"])
        assert X.shape == (len(es), len(hl.METRICS))
        assert np.array_equal(X, np.array([e["vec"] for e in es]))


def test_bootstrap_deterministic_and_seed_sensitive(frame):
    a = hs.block_bootstrap(frame, 50, 123)
    b = hs.block_bootstrap(frame, 50, 123)
    c = hs.block_bootstrap(frame, 50, 124)
    for m in a["avg"]:
        assert np.array_equal(a["avg"][m], b["avg"][m])
    assert np.array_equal(a["reference"], b["reference"])
    assert any(not np.array_equal(a["avg"][m], c["avg"][m]) for m in a["avg"])
    assert len(a["avg"]) == 10 and all(v.shape == (50,) for v in a["avg"].values())


# ---------------------------------------------------------------------------
# P(most home-like), sort order, title rule
# ---------------------------------------------------------------------------

def test_p_sums_to_one_and_splits_ties():
    draws = {"A": np.array([1.0, 2.0, 1.0, 3.0]), "B": np.array([2.0, 1.0, 1.0, 3.0]),
             "C": np.array([3.0, 3.0, 2.0, 3.0])}
    p = hs.p_most_home_like(draws)
    assert sum(p.values()) == pytest.approx(1.0)
    assert p["A"] == pytest.approx((1 + 0 + 0.5 + 1 / 3) / 4)
    assert p["C"] == pytest.approx((1 / 3) / 4)


def test_p_sums_to_one_on_data(frame):
    boot = hs.block_bootstrap(frame, 40, 7)
    assert sum(hs.p_most_home_like(boot["avg"]).values()) == pytest.approx(1.0)


def test_sort_most_home_like_first():
    vals = {"GPT-5.5": 1.1, "Claude Opus 4.7": 0.4, "Grok 4.3": 0.4, "GPT-5.4": 0.8}
    assert hs.sort_most_home_like(vals) == ["Claude Opus 4.7", "Grok 4.3", "GPT-5.4", "GPT-5.5"]


def test_title_rule_branches():
    order = ["A", "B", "C", "D"]
    t, b = hs.title_rule(order, {"A": 0.96, "B": 0.04, "C": 0.0, "D": 0.0})
    assert b == "p_top>=0.95" and t == "A Edits Other Providers' Documents Most Like Their Own Models"
    t, b = hs.title_rule(order, {"A": 0.6, "B": 0.4, "C": 0.0, "D": 0.0})
    assert b == "hedged_multi" and t == "A and B Edit Other Providers' Documents Most Like Their Own Models"
    t, b = hs.title_rule(order, {"A": 0.5, "B": 0.3, "C": 0.2, "D": 0.0})
    assert t.startswith("A, B and C Edit ")
    t, b = hs.title_rule(order, {"A": 0.9, "B": 0.04, "C": 0.03, "D": 0.03})
    assert b == "hedged_single" and t.startswith("A Likely Edits ")
    # top model is always named even if below 0.05 (ties in point estimate vs. draws)
    t, b = hs.title_rule(order, {"A": 0.02, "B": 0.5, "C": 0.48, "D": 0.0})
    assert t.startswith("A, B and C Edit ")


def test_committed_summary_consistent():
    import json
    s = json.loads((hs.DATA_DIR / f"{hs.STEM}.json").read_text())
    order = s["order_most_home_like_first"]
    vals = [s["models"][m]["avg_distance"] for m in order]
    assert vals == sorted(vals)
    assert sum(s["models"][m]["p_most_home_like"] for m in order) == pytest.approx(1.0)
    p = {m: s["models"][m]["p_most_home_like"] for m in order}
    assert (s["title"], s["title_branch"]) == hs.title_rule(order, p)
