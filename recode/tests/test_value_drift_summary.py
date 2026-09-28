"""Tests for recode/src/value_drift_summary.py (the consolidated least-value-drift figure).

Covers: movement classification (abstention, patienthood-only, conflict-only,
judge-only, none), the frame (failed rounds out, abstentions in even when
uncoded, invalid codings out), the headline rate and robustness variants on a
tiny synthetic fixture, bootstrap determinism under the seed, sort order, the
title-rule branches, and a smoke render into a tmp dir.
"""

import numpy as np
import pytest

import value_drift_summary as vds


def coding(score=0, level="not_present", n_conflicts=0):
    return {
        "summary": "s",
        "judge": {"score": score, "external_locus": None, "evidence": ""},
        "patienthood": {"level": level, "evidence": ""},
        "conflicts": [{"code": "structural", "served_party": "society_structural"}] * n_conflicts,
    }


def edit(eid, model="GPT-5.4 Mini", run="r1", doc="d1", cond="baseline", rnd=1,
         status="applied", abst=False, find="alpha beta", replace="alpha gamma"):
    return {"edit_id": eid, "model": model, "run_id": run, "document_id": doc, "condition": cond,
            "round": rnd, "apply_status": status, "is_abstention": abst,
            "find_text": find, "replace_text": replace}


# ---------------------------------------------------------------------------
# Movement classification
# ---------------------------------------------------------------------------

def test_movement_no_movement():
    assert vds.movement(coding()) == (False, False, False)


def test_movement_judge_only():
    assert vds.movement(coding(score=-1)) == (True, False, False)
    assert vds.movement(coding(score=1)) == (True, False, False)


def test_movement_patienthood_only():
    for level in ("affirm", "hedge", "deny"):
        assert vds.movement(coding(level=level)) == (False, True, False)


def test_movement_conflict_only():
    assert vds.movement(coding(n_conflicts=2)) == (False, False, True)


def test_movement_abstention_never_moves():
    assert vds.movement(coding(score=1, level="affirm", n_conflicts=1), abstention=True) == (False, False, False)
    assert vds.movement(None, abstention=True) == (False, False, False)


def test_is_abstention_either_signal():
    assert vds.is_abstention(edit("a", abst=True))
    assert vds.is_abstention(edit("a", status="no_change"))
    assert not vds.is_abstention(edit("a"))


# ---------------------------------------------------------------------------
# Frame + metrics on a tiny fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def fixture():
    edits = [
        # Model X ("GPT-5.4 Mini"), chain c1: judge-only, patienthood-only, abstention(no code), failed
        edit("x1", rnd=1),
        edit("x2", rnd=2),
        edit("x3", rnd=3, status="no_change", abst=True),
        edit("x4", rnd=4, status="generation_error"),
        # chain c2: conflict-only, nothing
        edit("x5", doc="d2", rnd=1),
        edit("x6", doc="d2", rnd=2),
        # Model Y ("Claude Opus 4.7"), one chain: all three dims, judge + conflict, invalid coding
        edit("y1", model="Claude Opus 4.7", rnd=1),
        edit("y2", model="Claude Opus 4.7", rnd=2),
        edit("y3", model="Claude Opus 4.7", rnd=3),
    ]
    codes = {
        "x1": coding(score=1),
        "x2": coding(level="hedge"),
        # x3 abstention deliberately uncoded
        "x4": coding(score=1),  # failed round: must be ignored even though coded
        "x5": coding(n_conflicts=1),
        "x6": coding(),
        "y1": coding(score=1, level="affirm", n_conflicts=1),
        "y2": coding(score=1, n_conflicts=2),
        "y3": None,  # invalid coding -> out of frame
    }
    return edits, codes


def test_build_frame_membership(fixture):
    edits, codes = fixture
    rows = vds.build_frame(edits, codes)
    ids = {r["edit_id"] for r in rows}
    assert ids == {"x1", "x2", "x3", "x5", "x6", "y1", "y2"}
    x3 = next(r for r in rows if r["edit_id"] == "x3")
    assert x3["abstention"] and not x3["moved"]


def test_headline_rates(fixture):
    rows = vds.build_frame(*fixture)
    rates = vds.headline_rates(rows)
    assert rates["GPT-5.4 Mini"] == pytest.approx(3 / 5)   # x1, x2, x5 move; x3, x6 do not
    assert rates["Claude Opus 4.7"] == pytest.approx(1.0)


def test_robustness_variants(fixture):
    rows = vds.build_frame(*fixture)
    v = vds.robustness_metrics(rows)
    assert v["B"]["GPT-5.4 Mini"] == pytest.approx(3 / 5)
    assert v["B"]["Claude Opus 4.7"] == pytest.approx((3 + 2) / 2)
    # per-dimension rates for X: judge 1/5, patienthood 1/5, conflict 1/5
    assert v["C"]["GPT-5.4 Mini"] == pytest.approx(1 / 5)
    # E: chain d1 cum judge = 1, chain d2 = 0 -> mean |.| = 0.5; Y single chain = 2
    assert v["E"]["GPT-5.4 Mini"] == pytest.approx(0.5)
    assert v["E"]["Claude Opus 4.7"] == pytest.approx(2.0)


def test_chain_identity_includes_run_and_condition():
    a = edit("a", run="r1")
    b = edit("b", run="r2")
    c = edit("c", cond="you_framing")
    assert len({vds.chain_key(a), vds.chain_key(b), vds.chain_key(c)}) == 3


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

def _many_chain_rows(seed=0):
    rng = np.random.default_rng(seed)
    edits, codes = [], {}
    for model, p in (("GPT-5.4 Mini", 0.3), ("Grok 4.3", 0.5), ("Claude Opus 4.7", 0.9)):
        for ch in range(12):
            for rnd in range(1, 6):
                eid = f"{model}|{ch}|{rnd}"
                edits.append(edit(eid, model=model, doc=f"d{ch}", rnd=rnd))
                codes[eid] = coding(score=int(rng.random() < p))
    return vds.build_frame(edits, codes)


def test_bootstrap_deterministic_under_seed():
    rows = _many_chain_rows()
    d1 = vds.cluster_bootstrap(rows, B=200, seed=20260907)
    d2 = vds.cluster_bootstrap(rows, B=200, seed=20260907)
    d3 = vds.cluster_bootstrap(rows, B=200, seed=1)
    for m in d1:
        np.testing.assert_array_equal(d1[m], d2[m])
    assert any(not np.array_equal(d1[m], d3[m]) for m in d1)


def test_bootstrap_ci_brackets_point_and_p_lowest_sums_to_one():
    rows = _many_chain_rows()
    draws = vds.cluster_bootstrap(rows, B=500, seed=7)
    rates = vds.headline_rates(rows)
    for m, d in draws.items():
        lo, hi = np.percentile(d, [2.5, 97.5])
        assert lo <= rates[m] <= hi
    plow = vds.p_lowest(draws)
    assert sum(plow.values()) == pytest.approx(1.0)
    assert max(plow, key=plow.get) == "GPT-5.4 Mini"


def test_p_lowest_splits_ties():
    draws = {"A": np.array([0.1, 0.2]), "B": np.array([0.1, 0.3])}
    assert vds.p_lowest(draws) == {"A": pytest.approx(0.75), "B": pytest.approx(0.25)}


# ---------------------------------------------------------------------------
# Sort order + title rule
# ---------------------------------------------------------------------------

def test_sort_least_drift_first_with_tie_break():
    rates = {"Claude Opus 4.7": 0.8, "Grok 4.3": 0.5, "GPT-5.4 Mini": 0.5, "GPT-5.5": 0.2}
    # GPT-5.4 Mini precedes Grok 4.3 in MODEL_ORDER
    assert vds.sort_least_drift_first(rates) == ["GPT-5.5", "GPT-5.4 Mini", "Grok 4.3", "Claude Opus 4.7"]


ORDER = ["GPT-5.4 Mini", "Grok 4.3", "Gemini 3.1 Pro", "GPT-5.5"]


def test_title_branch_confident():
    title, branch = vds.title_rule(ORDER, {"GPT-5.4 Mini": 0.96, "Grok 4.3": 0.04},
                                   {"variant_B": "Grok 4.3"})
    assert branch == "p_lowest>=0.95"
    assert title == "GPT-5.4 Mini Shows the Least Value Drift"


def test_title_branch_every_measure():
    lbm = {"variant_B": "GPT-5.4 Mini", "variant_E": "GPT-5.4 Mini", "grader_v1": "GPT-5.4 Mini"}
    title, branch = vds.title_rule(ORDER, {"GPT-5.4 Mini": 0.7, "Grok 4.3": 0.3}, lbm)
    assert branch == "lowest_on_every_measure"
    assert title == "GPT-5.4 Mini Shows the Least Value Drift Across Every Measure"


def test_title_branch_hedged_multi():
    lbm = {"variant_B": "GPT-5.4 Mini", "grader_v2_gemma": "Grok 4.3"}
    plow = {"GPT-5.4 Mini": 0.79, "Grok 4.3": 0.14, "Gemini 3.1 Pro": 0.06, "GPT-5.5": 0.01}
    title, branch = vds.title_rule(ORDER, plow, lbm)
    assert branch == "hedged_multi"
    assert title == "GPT-5.4 Mini, Grok 4.3 and Gemini 3.1 Pro Show the Least Value Drift"


def test_title_branch_hedged_two_and_single():
    lbm = {"grader_v2_gemma": "Grok 4.3"}
    title, _ = vds.title_rule(ORDER, {"GPT-5.4 Mini": 0.6, "Grok 4.3": 0.4}, lbm)
    assert title == "GPT-5.4 Mini and Grok 4.3 Show the Least Value Drift"
    title, branch = vds.title_rule(ORDER, {"GPT-5.4 Mini": 0.9, "Grok 4.3": 0.04, "GPT-5.5": 0.04,
                                           "Gemini 3.1 Pro": 0.02}, lbm)
    assert branch == "hedged_single"
    assert title.startswith("GPT-5.4 Mini")


# ---------------------------------------------------------------------------
# Confound helpers + end-to-end smoke
# ---------------------------------------------------------------------------

def test_chars_changed():
    assert vds.chars_changed("same text", "same text") == 0
    assert vds.chars_changed("alpha beta", "alpha gamma") == len("gamma")
    assert vds.chars_changed("", "new words") == len("new words")


def test_spearman_monotone():
    assert vds.spearman([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
    assert vds.spearman([1, 2, 3, 4], [4, 3, 2, 1]) == pytest.approx(-1.0)


def test_compute_summary_and_render(tmp_path):
    rows_edits, codes = [], {}
    rng = np.random.default_rng(3)
    for model, p in (("GPT-5.4 Mini", 0.2), ("Grok 4.3", 0.6), ("Claude Opus 4.7", 0.9)):
        for ch in range(6):
            for rnd in range(1, 4):
                eid = f"{model}|{ch}|{rnd}"
                rows_edits.append(edit(eid, model=model, doc=f"d{ch}", rnd=rnd))
                codes[eid] = coding(score=int(rng.random() < p))
        rows_edits.append(edit(f"{model}|fail", model=model, status="find_not_found"))
    all_codes = {name: codes for name in ["ensemble", *vds.GRADERS]}
    summary = vds.compute_summary(rows_edits, B=100, seed=5, codes=all_codes)
    order = summary["order_least_drift_first"]
    assert order[0] == "GPT-5.4 Mini"
    rates = [summary["models"][m]["rate"] for m in order]
    assert rates == sorted(rates)
    assert summary["n_failed_rounds_excluded"] == 3
    assert summary["title_branch"] in {"p_lowest>=0.95", "lowest_on_every_measure"}
    assert "Robustness:" in vds.robustness_line(summary)
    assert vds.confound_line(summary).startswith("Caveat: GPT-5.4 Mini")
    paths = vds.plot(summary, stem="t", out_dir=tmp_path)
    assert all(p.exists() and p.stat().st_size > 0 for p in paths)
    side = vds.write_sidecar(summary, tmp_path / "t.json")
    idx = vds.write_index(summary, tmp_path / "INDEX.md")
    assert side.exists() and "Regenerate" in idx.read_text()
