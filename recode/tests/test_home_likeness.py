"""Tests for recode/src/home_likeness.py."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "recode" / "src"))
import home_likeness as hl  # noqa: E402

ORIG = ROOT / "reports" / "generate_judge_beneficiary_figures.py"
ORIG_STYLE = ROOT / "reports" / "generate_figures.py"


# ---------------------------------------------------------------------------
# Verbatim copies match the original source (parsed, never imported)
# ---------------------------------------------------------------------------

def _module_assign(path, name):
    tree = ast.parse(path.read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == name for t in node.targets):
            return node
    raise KeyError(name)


def test_conflict_direction_is_verbatim():
    src = ORIG.read_text()
    orig = ast.get_source_segment(src, next(n for n in ast.parse(src).body
                                            if isinstance(n, ast.FunctionDef) and n.name == "conflict_direction"))
    mine_src = (ROOT / "recode" / "src" / "home_likeness.py").read_text()
    mine = ast.get_source_segment(mine_src, next(n for n in ast.parse(mine_src).body
                                                 if isinstance(n, ast.FunctionDef) and n.name == "conflict_direction"))
    assert orig == mine


def test_pole_ids_match_beneficiary_panels():
    node = _module_assign(ORIG, "BENEFICIARY_PANELS")
    panels = []
    for d in node.value.elts:
        kv = {k.value: v for k, v in zip(d.keys, d.values)}
        panels.append((kv["code"].value, kv["left"].elts[0].value, kv["right"].elts[0].value))
    assert panels == hl.CONFLICT_POLES


@pytest.mark.parametrize("name", ["MODEL_COLORS", "MODEL_ORDER", "FAMILY_TO_MODELS"])
def test_style_constants_match(name):
    node = _module_assign(ORIG_STYLE, name)
    assert ast.literal_eval(node.value) == getattr(hl, name)


# ---------------------------------------------------------------------------
# Per-edit scoring
# ---------------------------------------------------------------------------

def _coding(judge=0, conflicts=()):
    return {"judge": {"score": judge}, "patienthood": {"level": "not_present"},
            "conflicts": [{"code": c, "served_party": s} for c, s in conflicts]}


def test_signed_conflict_scoring():
    c = _coding(1, [("paternalism", "user_stated"), ("paternalism", "user_stated"),
                    ("paternalism", "user_idealized"), ("company_cost", "developer"),
                    ("welfare", "model_welfare"), ("harmlessness", "deployer"),
                    ("disclosure", "deployer"), ("structural", "society_structural")])
    v = hl.edit_vector(c)
    # judge, paternalism, harmlessness, structural, company_cost, welfare, disclosure
    assert v.tolist() == [1, 2 - 1, 0, -1, -1, 1, -1]
    assert hl.edit_vector(_coding(-1)).tolist() == [-1, 0, 0, 0, 0, 0, 0]


def test_company_cost_non_developer_is_right_pole():
    assert hl.signed_conflict_score(_coding(0, [("company_cost", "user_stated")]),
                                    "company_cost", "pro_company", "against_company") == 1


# ---------------------------------------------------------------------------
# Real-data layout
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def frame():
    return hl.load_frame(hl.CODES_DIR / "ensemble.jsonl")


def test_layout(frame):
    lay = hl.verify_layout(frame)
    assert lay["homes"] == {
        "claude_constitution": ["Claude Haiku 4.5", "Claude Opus 4.7", "Claude Sonnet 4.6"],
        "openai_model_spec": ["GPT-5.4", "GPT-5.4 Mini", "GPT-5.5"],
        "gemini_system_prompt": ["Gemini 3 Flash", "Gemini 3.1 Pro"],
        "grok_system_prompt": ["Grok 4.2", "Grok 4.3"],
    }
    assert len(lay["cells"]) == 40
    assert lay["cells"]["Claude Opus 4.7|openai_model_spec"]["document_id"] == "openai_model_spec_no_csam"
    others = [c for k, c in lay["cells"].items() if k != "Claude Opus 4.7|openai_model_spec"]
    assert all(c["document_id"] != "openai_model_spec_no_csam" for c in others)
    assert all(1 <= c["n_edits"] <= 20 for c in lay["cells"].values())


def test_layout_rejects_two_runs(frame):
    bad = [dict(e) for e in frame]
    bad[0]["run_id"] = "other_run"
    with pytest.raises(AssertionError):
        hl.verify_layout(bad)


# ---------------------------------------------------------------------------
# Reference / distance logic
# ---------------------------------------------------------------------------

def test_leave_one_out_reference():
    prof = {("A", "d"): np.array([0.0, 0]), ("B", "d"): np.array([2.0, 0]),
            ("C", "d"): np.array([4.0, 2]), ("V", "d"): np.array([1.0, 1])}
    homes = ["A", "B", "C"]
    assert hl.reference(prof, "d", "A", homes).tolist() == [3.0, 1.0]  # mean of B, C
    assert hl.reference(prof, "d", "V", homes).tolist() == [2.0, 2 / 3]  # full family
    assert hl.l1(prof[("A", "d")], hl.reference(prof, "d", "A", homes)) == pytest.approx(4.0)


def _synthetic_frame(visitor_shift=0.0, seed=0, identical=False):
    """4 docs x 3 models; every doc's home family is one pseudo-family."""
    rng = np.random.default_rng(seed)
    frame = []
    for d in hl.DOC_IDS:
        homes = hl.FAMILY_TO_MODELS[hl.DOC_OWNER[d]]
        visitor = "Grok 4.3" if hl.DOC_OWNER[d] != "xAI" else "GPT-5.5"
        for m in list(homes) + [visitor]:
            for r in range(1, 21):
                if identical:
                    vec = np.ones(7)
                else:
                    vec = rng.normal(0, 0.3, 7)
                    if m == visitor:
                        vec = vec + visitor_shift
                frame.append({"edit_id": f"{m}|{d}|{r}", "model": m, "run_id": f"run_{m}", "raw_doc": d,
                              "doc": d, "owner": hl.DOC_OWNER[d], "round": r, "vec": vec})
    return frame


def test_analyze_distances_match_manual():
    fr = _synthetic_frame(0.5, seed=1)
    res = hl.analyze(fr, n_perm=50, seed=3)
    d = "claude_constitution"
    prof = hl.cell_profiles(fr)
    ref = np.mean([prof[(h, d)] for h in ["Claude Opus 4.7", "Claude Haiku 4.5"]], axis=0)
    assert res["per_doc"][d]["distance"]["Claude Sonnet 4.6"] == pytest.approx(hl.l1(prof[("Claude Sonnet 4.6", d)], ref))
    loo = [res["per_doc"][d]["distance"][h] for h in hl.FAMILY_TO_MODELS["Anthropic"]]
    assert res["per_doc"][d]["band"] == [min(loo), max(loo)]


# ---------------------------------------------------------------------------
# Permutation test
# ---------------------------------------------------------------------------

def test_permutation_preserves_per_round_counts():
    labels = np.array([0, 1, 2, 0, 1, 2, 0, 2, 1])
    rounds = np.array([1, 1, 1, 2, 2, 2, 3, 3, 4])
    perm = hl.permuted_labels(labels, rounds, 500, np.random.default_rng(5))
    assert perm.shape == (500, 9)
    for r in np.unique(rounds):
        idx = np.flatnonzero(rounds == r)
        for row in perm[:, idx]:
            assert sorted(row.tolist()) == sorted(labels[idx].tolist())
    # labels actually move (round 1 has 3! orderings)
    assert len({tuple(row) for row in perm[:, :3]}) == 6
    assert (perm[:, 8] == 1).all()  # singleton round is fixed


def test_permutation_identical_groups_p_one():
    fr = _synthetic_frame(identical=True)
    res = hl.analyze(fr, n_perm=300, seed=7)
    assert all(t["p_raw"] == 1.0 for t in res["tests"])


def test_permutation_null_groups_not_significant():
    fr = _synthetic_frame(0.0, seed=2)
    res = hl.analyze(fr, n_perm=500, seed=7)
    assert min(t["p_raw"] for t in res["tests"]) > 0.01


def test_permutation_separated_groups_small_p():
    fr = _synthetic_frame(1.0, seed=4)
    res = hl.analyze(fr, n_perm=500, seed=7)
    assert all(t["p_raw"] == pytest.approx(1 / 501) for t in res["tests"])


def test_perm_pvalue_formula():
    null = np.array([0.1, 0.2, 0.3, 0.4])
    assert hl.perm_pvalue(null, 0.25) == pytest.approx(3 / 5)
    assert hl.perm_pvalue(null, 0.4) == pytest.approx(2 / 5)
    assert hl.perm_pvalue(null, 9.0) == pytest.approx(1 / 5)


# ---------------------------------------------------------------------------
# Holm
# ---------------------------------------------------------------------------

def test_holm():
    adj = hl.holm([0.01, 0.04, 0.03, 0.2])
    assert adj == pytest.approx([0.04, 0.09, 0.09, 0.2])
    assert hl.holm([0.5, 0.6]) == pytest.approx([1.0, 1.0])
    assert hl.holm([0.001]) == pytest.approx([0.001])


# ---------------------------------------------------------------------------
# Title rule
# ---------------------------------------------------------------------------

def _res(dists, bands, p_holm):
    per_doc = {}
    for d in hl.DOC_IDS:
        homes = hl.FAMILY_TO_MODELS[hl.DOC_OWNER[d]]
        per_doc[d] = {"homes": homes, "distance": dists[d], "band": bands[d]}
    tests = [{"model": m, "doc": d, "p_holm": p_holm.get((m, d), 1.0)}
             for d in hl.DOC_IDS for m in dists[d] if m not in per_doc[d]["homes"]]
    return {"per_doc": per_doc, "tests": tests,
            "visitor_avg": {m: {} for m in hl.MODEL_ORDER if m in dists[hl.DOC_IDS[0]]}}


def _base(far_docs=(), far_models=(), sig=True):
    models = [m for fam in hl.FAMILY_TO_MODELS.values() for m in fam]
    dists, bands, ps = {}, {}, {}
    for d in hl.DOC_IDS:
        homes = hl.FAMILY_TO_MODELS[hl.DOC_OWNER[d]]
        dd = {}
        for m in models:
            if m in homes:
                dd[m] = 0.5
            elif d in far_docs or m in far_models:
                dd[m] = 1.5
                ps[(m, d)] = 0.01 if sig else 0.5
            else:
                dd[m] = 0.4
        dists[d], bands[d] = dd, [0.5, 0.5]
    return _res(dists, bands, ps)


def test_title_one_document():
    title, out = hl.choose_title(_base(far_docs=("claude_constitution",)))
    assert out["branch"] == "one_document"
    assert title == "No Other Model Family Edits the Claude Constitution Like Claude Does"


def test_title_all_documents():
    _, out = hl.choose_title(_base(far_docs=tuple(hl.DOC_IDS)))
    assert out["branch"] == "all_documents"


def test_title_several_documents():
    title, out = hl.choose_title(_base(far_docs=("claude_constitution", "grok_system_prompt")))
    assert out["branch"] == "several_documents"
    assert "the Claude Constitution or the Grok System Prompt" in title


def test_title_not_significant_falls_back_to_neutral():
    title, out = hl.choose_title(_base(far_docs=("claude_constitution",), sig=False))
    assert out["branch"] == "neutral" and title == hl.NEUTRAL_TITLE


def test_title_one_visitor_inside_band_blocks_document():
    r = _base(far_docs=("claude_constitution",))
    r["per_doc"]["claude_constitution"]["distance"]["GPT-5.4 Mini"] = 0.49
    _, out = hl.choose_title(r)
    assert out["doc_checks"]["claude_constitution"]["b_beyond_band"] is False
    assert out["branch"] == "neutral"


def test_title_visitor_level():
    title, out = hl.choose_title(_base(far_models=("Grok 4.3",)))
    assert out["branch"] == "visitor_level"
    assert title.startswith("Grok 4.3 Edits No Other Developer's Document")


# ---------------------------------------------------------------------------
# Determinism + real-data headline
# ---------------------------------------------------------------------------

def test_determinism_under_seed(frame):
    a = hl.analyze(frame, n_perm=300, seed=20260903)
    b = hl.analyze(frame, n_perm=300, seed=20260903)
    assert [t["p_raw"] for t in a["tests"]] == [t["p_raw"] for t in b["tests"]]
    c = hl.analyze(frame, n_perm=300, seed=1)
    assert [t["p_raw"] for t in a["tests"]] != [t["p_raw"] for t in c["tests"]]


def test_real_data_sanity(frame):
    res = hl.analyze(frame, run_perm=False)
    pw = [p for d in hl.DOC_IDS for p in res["per_doc"][d]["within_home_pairwise"]]
    assert 0.3 < min(pw) and max(pw) < 1.5
    avg = {m: v["mean"] for m, v in res["visitor_avg"].items()}
    assert min(avg, key=avg.get) == "Claude Opus 4.7"
    assert max(avg, key=avg.get) == "Grok 4.3"
    cc = res["per_doc"]["claude_constitution"]
    visitors = [m for m in cc["distance"] if m not in cc["homes"]]
    assert all(cc["distance"][v] > cc["band"][1] for v in visitors)
