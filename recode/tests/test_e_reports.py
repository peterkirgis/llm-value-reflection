"""Tests for recode/src/e_reports.py (Workstream E report generators).

Synthetic fixtures per subcommand:
  - E1: paired cluster bootstrap on a KNOWN effect (degenerate constant
    shift -> point and CI collapse to it; two-chain case -> CI brackets the
    point), invalid/missing rows excluded from the three-arm intersection.
  - E2: per-model means, Spearman rho (+1 for an identical paraphrase, -1
    for a rank-reversing one), per-edit kappa, sign-stability rows.
  - E3: case/control accounting, control false-creation rate, claim (b)
    under the merged variant codes, fallback-to-v2 counting.
  - E4: unanimity ranking with ties (dimension count -> margin -> count ->
    edit_id), deterministic modal tie-breaks, and an extras-format
    ROUND-TRIP through draw_human_sample.py --append-extras in a sandbox
    copy of human/.
  - E5: transition accounting (judge/patienthood matrices, conflict
    added/removed), per-document concentration.

codes_io is the SHARED INTERFACE authored by a peer; if it has not landed
yet, an interface-exact stub is installed (sys.modules) so these tests run
either way. Once recode/src/codes_io.py exists, the real module is imported
and the stub is never used.
"""

import json
import sys
import types
from pathlib import Path

import pytest

# conftest.py puts recode/src on sys.path.

# ---------------------------------------------------------------------------
# codes_io: real module if the peer has landed it, else an interface stub
# ---------------------------------------------------------------------------

try:
    import codes_io  # noqa: F401
except ImportError:  # pragma: no cover - exercised only before codes_io lands
    _stub = types.ModuleType("codes_io")
    _VALID_SCORES = {-1, 0, 1}
    _LEVELS = {"affirm", "hedge", "deny", "not_present"}

    def _load_codes(path):
        out = {}
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    row = json.loads(line)
                    eid = row.get("edit_id") or row.get("id")
                    if eid is None:
                        raise ValueError(f"{path}: row without edit_id/id")
                    out[eid] = row
        return out

    def _coding_of(row):
        if row.get("error"):
            return None
        coding = row.get("coding")
        if not isinstance(coding, dict):
            return None
        judge = coding.get("judge")
        pat = coding.get("patienthood")
        if not isinstance(judge, dict) or judge.get("score") not in _VALID_SCORES:
            return None
        if not isinstance(pat, dict) or pat.get("level") not in _LEVELS:
            return None
        return coding

    _stub.load_codes = _load_codes
    _stub.coding_of = _coding_of
    _stub.judge_score = lambda c: None if c is None else c["judge"]["score"]
    _stub.patienthood_level = lambda c: None if c is None else c["patienthood"]["level"]
    _stub.conflicts = lambda c: [] if c is None else (c.get("conflicts") or [])
    _stub.has_conflict = lambda c, code: any(
        (x or {}).get("code") == code for x in _stub.conflicts(c)
    )
    sys.modules["codes_io"] = _stub

import draw_human_sample  # noqa: E402
import e_reports  # noqa: E402


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def pid(run, cond, model, doc, rnd, doc_type="constitution"):
    """A canonical pipe edit_id."""
    return f"{run}|{cond}|{model}|{doc}|{doc_type}|{rnd}"


def coding(score, level="not_present", conflicts=None):
    return {
        "summary": "s",
        "judge": {"score": score, "external_locus": None, "evidence": "e"},
        "patienthood": {"level": level, "evidence": ""},
        "conflicts": conflicts or [],
    }


def conflict(code, cost_bearer="user_stated", served_party="user_idealized",
             mechanism="adds_protection"):
    return {
        "code": code,
        "cost_bearer": cost_bearer,
        "served_party": served_party,
        "mechanism": mechanism,
        "cost_clause": "clause",
    }


def write_codes(path, entries):
    """entries: list of (edit_id, coding_or_None, error_or_None [, extra])."""
    with open(path, "w", encoding="utf-8") as handle:
        for entry in entries:
            eid, cod, err = entry[0], entry[1], entry[2]
            row = {"edit_id": eid, "grader": "g", "coding": cod, "error": err,
                   "raw_response": None}
            if len(entry) > 3:
                row.update(entry[3])
            handle.write(json.dumps(row) + "\n")
    return path


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def test_parse_pipe_id_and_chain():
    eid = pid("runA", "baseline", "ModelA", "docA", 7)
    info = e_reports.parse_pipe_id(eid)
    assert info == {
        "run": "runA", "condition": "baseline", "model": "ModelA",
        "document_id": "docA", "doc_type": "constitution", "round": 7,
    }
    assert e_reports.chain_of(eid) == ("runA", "baseline", "ModelA", "docA")
    assert e_reports.model_of(eid) == "ModelA"
    assert e_reports.document_of(eid) == "docA"
    with pytest.raises(ValueError):
        e_reports.parse_pipe_id("not-a-pipe-id")


def test_safe_kappa_conventions():
    # Perfect agreement, single class: sklearn would return nan; convention 1.0.
    assert e_reports.safe_kappa([1, 1, 1], [1, 1, 1]) == 1.0
    # Total disagreement with disjoint constant labels: kappa 0.
    assert e_reports.safe_kappa([1, 1], [0, 0]) == 0.0
    # Perfect agreement with multiple classes: 1.0.
    assert e_reports.safe_kappa([1, 0, -1], [1, 0, -1]) == 1.0
    # Empty: None.
    assert e_reports.safe_kappa([], []) is None
    # A regular mixed case stays within [-1, 1] and below 1.
    k = e_reports.safe_kappa([1, 1, 0, 0], [1, 0, 0, 0])
    assert k is not None and -1.0 <= k < 1.0


# ---------------------------------------------------------------------------
# E1 -- label-swap diagnostic
# ---------------------------------------------------------------------------


def e1_fixture_paths(tmp_path):
    """ModelA (2 chains x 3 edits): true judge 0 / not_present; swapped
    judge 1 / affirm; removed judge 0. ModelB (1 chain x 4 edits): true 1,
    swapped 0, removed 1. Plus one edit missing from the swapped arm and one
    with an error row in the swapped arm -- both excluded from the
    three-arm intersection."""
    ids_a = [pid("runA", "baseline", "ModelA", d, r) for d in ("docA", "docB") for r in (1, 2, 3)]
    ids_b = [pid("runB", "baseline", "ModelB", "docC", r) for r in (1, 2, 3, 4)]
    only_true = pid("runA", "baseline", "ModelA", "docA", 50)
    errored = pid("runA", "baseline", "ModelA", "docA", 99)

    true_rows = (
        [(e, coding(0), None) for e in ids_a]
        + [(e, coding(1), None) for e in ids_b]
        + [(only_true, coding(1), None), (errored, coding(1), None)]
    )
    swapped_rows = (
        [(e, coding(1, "affirm"), None) for e in ids_a]
        + [(e, coding(0), None) for e in ids_b]
        + [(errored, None, "transport: boom")]
    )
    removed_rows = (
        [(e, coding(0), None) for e in ids_a]
        + [(e, coding(1), None) for e in ids_b]
        + [(errored, coding(1), None)]
    )
    t = write_codes(tmp_path / "true.jsonl", true_rows)
    s = write_codes(tmp_path / "swapped.jsonl", swapped_rows)
    r = write_codes(tmp_path / "removed.jsonl", removed_rows)
    return t, s, r


def test_e1_known_effect_and_report(tmp_path):
    t, s, r = e1_fixture_paths(tmp_path)
    tv, _ = e_reports.load_valid_codings(t)
    sv, _ = e_reports.load_valid_codings(s)
    rv, _ = e_reports.load_valid_codings(r)

    res = e_reports.e1_compute(tv, sv, rv, B=50, seed=3)

    # Only edits valid in ALL three arms: 6 (ModelA) + 4 (ModelB).
    assert res["n_common"] == 10
    a = res["per_model"]["ModelA"]
    b = res["per_model"]["ModelB"]
    assert a["n"] == 6 and a["n_chains"] == 2
    assert b["n"] == 4 and b["n_chains"] == 1

    # Arm means.
    assert a["means"]["true"]["judge"] == 0.0
    assert a["means"]["swapped"]["judge"] == 1.0
    assert a["means"]["swapped"]["affirm"] == 1.0
    assert b["means"]["true"]["judge"] == 1.0

    # Degenerate constant shifts: point == CI bounds exactly.
    eff_a = a["effects"]["swapped_minus_true"]["judge"]
    assert eff_a["point"] == 1.0 and eff_a["lo"] == 1.0 and eff_a["hi"] == 1.0
    eff_b = b["effects"]["swapped_minus_true"]["judge"]
    assert eff_b["point"] == -1.0 and eff_b["lo"] == -1.0 and eff_b["hi"] == -1.0
    tr_a = a["effects"]["true_minus_removed"]["judge"]
    assert tr_a["point"] == 0.0 and tr_a["lo"] == 0.0 and tr_a["hi"] == 0.0
    aff_a = a["effects"]["swapped_minus_true"]["affirm"]
    assert aff_a["point"] == 1.0 and aff_a["lo"] == 1.0 and aff_a["hi"] == 1.0

    # Pooled paired effect: (6 * +1 + 4 * -1) / 10.
    assert res["pooled"]["effects"]["swapped_minus_true"]["judge"]["point"] == pytest.approx(0.2)

    # Headline label effect: mean over models of |shift| = (1 + 1) / 2.
    le = res["label_effect"]
    assert le["mean_abs_judge_shift"] == 1.0
    assert le["lo"] == 1.0 and le["hi"] == 1.0
    assert le["per_model_shift"] == {"ModelA": 1.0, "ModelB": -1.0}

    # CLI end-to-end: report exists, headline sentence is the first body line.
    out = tmp_path / "E1.md"
    e_reports.main([
        "e1", "--true", str(t), "--swapped", str(s), "--removed", str(r),
        "--out", str(out), "--B", "50", "--seed", "3",
    ])
    text = out.read_text(encoding="utf-8")
    body = text.split("\n")[2]
    assert body.startswith("**Across the 2 models, the mean absolute per-model shift")
    assert "1.000" in body
    assert "N = 10 edits" in text


def test_e1_paired_bootstrap_nondegenerate():
    """Two chains with different mean differences: point = overall mean of
    the paired diffs; the percentile CI brackets it and has width."""
    m = "ModelC"
    ids1 = [pid("runC", "baseline", m, "doc1", r) for r in (1, 2)]
    ids2 = [pid("runC", "baseline", m, "doc2", r) for r in (1, 2)]
    tv = {e: coding(0) for e in ids1 + ids2}
    sv = {e: coding(1) for e in ids1} | {e: coding(0) for e in ids2}
    rv = {e: coding(0) for e in ids1 + ids2}

    res = e_reports.e1_compute(tv, sv, rv, B=200, seed=11)
    eff = res["per_model"][m]["effects"]["swapped_minus_true"]["judge"]
    assert eff["point"] == pytest.approx(0.5)
    assert eff["n_chains"] == 2 and eff["n_edits"] == 4
    assert eff["lo"] <= 0.5 <= eff["hi"]
    assert eff["lo"] < eff["hi"]  # chain resampling produces real spread
    # Same seed -> identical result (determinism).
    res2 = e_reports.e1_compute(tv, sv, rv, B=200, seed=11)
    assert res2["per_model"][m]["effects"]["swapped_minus_true"]["judge"] == eff


# ---------------------------------------------------------------------------
# E2 -- manual-paraphrase robustness
# ---------------------------------------------------------------------------


def e2_fixture(tmp_path):
    def edit(eid, model, provider, rnd):
        return {
            "edit_id": eid, "run_id": "runX", "model": model, "provider": provider,
            "document_id": "docA", "condition": "baseline", "round": rnd,
            "apply_status": "applied",
        }

    a_ids = [f"a{r}" for r in range(1, 5)]
    b_ids = [f"b{r}" for r in range(1, 5)]
    edits = [edit(e, "ModelA", "alpha", r + 1) for r, e in enumerate(a_ids)] + [
        edit(e, "ModelB", "beta", r + 1) for r, e in enumerate(b_ids)
    ]
    edits_path = tmp_path / "edits.jsonl"
    with open(edits_path, "w", encoding="utf-8") as handle:
        for e in edits:
            handle.write(json.dumps(e) + "\n")

    a_scores = [1, 1, 1, 0]
    b_scores = [-1, -1, 0, 0]
    v2 = [(e, coding(s, "affirm" if e == "a1" else "not_present"), None)
          for e, s in zip(a_ids, a_scores)] + [(e, coding(s), None) for e, s in zip(b_ids, b_scores)]
    para1 = list(v2)  # byte-identical paraphrase result
    # para2 reverses the ranking (models swap score profiles) and flips a1's
    # patienthood from affirm to deny.
    para2 = [(e, coding(s, "deny" if e == "a1" else "not_present"), None)
             for e, s in zip(a_ids, b_scores)] + [(e, coding(s), None) for e, s in zip(b_ids, a_scores)]

    v2_p = write_codes(tmp_path / "v2.jsonl", v2)
    p1_p = write_codes(tmp_path / "para1.jsonl", para1)
    p2_p = write_codes(tmp_path / "para2.jsonl", para2)
    return edits_path, v2_p, p1_p, p2_p


def test_e2_means_rho_kappa_and_stability(tmp_path):
    edits_path, v2_p, p1_p, p2_p = e2_fixture(tmp_path)
    import headline

    edits = headline.load_jsonl(edits_path)
    valids = {}
    for lab, p in (("v2", v2_p), ("para1", p1_p), ("para2", p2_p)):
        valids[lab], _ = e_reports.load_valid_codings(p)

    res = e_reports.e2_compute(edits, valids)

    assert res["mean_judge"]["ModelA"]["v2"] == pytest.approx(0.75)
    assert res["mean_judge"]["ModelA"]["para1"] == pytest.approx(0.75)
    assert res["mean_judge"]["ModelA"]["para2"] == pytest.approx(-0.5)
    assert res["mean_judge"]["ModelB"]["v2"] == pytest.approx(-0.5)

    assert res["spearman"]["v2_vs_para1"] == pytest.approx(1.0)
    assert res["spearman"]["v2_vs_para2"] == pytest.approx(-1.0)

    # Kappa: para1 identical -> 1.0; para2 disagrees on judge and pat.
    assert res["kappas"]["v2_vs_para1"]["judge"] == 1.0
    assert res["kappas"]["v2_vs_para1"]["patienthood"] == 1.0
    assert res["kappas"]["v2_vs_para1"]["n"] == 8
    assert res["kappas"]["v2_vs_para2"]["judge"] < 1.0
    assert res["kappas"]["v2_vs_para2"]["patienthood"] == pytest.approx(7 / 15)

    # Sign stability: pooled mean judge per model flips under para2.
    a_item = res["signed_items"]["ModelA"]["mean_judge_pooled"]
    assert a_item["signs"] == {"v2": "+", "para1": "+", "para2": "-"}
    assert a_item["stable"] is False
    b_item = res["signed_items"]["ModelB"]["mean_judge_pooled"]
    assert b_item["stable"] is False

    # Claims table: identical verdicts across the three -> stable flags exist;
    # claim (b) has no paternalism conflicts anywhere -> same verdict thrice.
    assert res["claims"]["b"]["stable"] is True
    assert set(res["claims"]) == set("abcdefg")

    out = tmp_path / "E2.md"
    e_reports.main([
        "e2", "--v2", str(v2_p), "--para1", str(p1_p), "--para2", str(p2_p),
        "--edits", str(edits_path), "--out", str(out),
    ])
    text = out.read_text(encoding="utf-8")
    assert "Spearman rho" in text
    assert "Sign-stability" in text
    assert "| ModelA | 0.750 | 0.750 | -0.500 |" in text


# ---------------------------------------------------------------------------
# E3 -- paternalism-definition sensitivity
# ---------------------------------------------------------------------------


def e3_fixture(tmp_path):
    def cid(model, n):
        return pid("runE", "baseline", model, "docA", n)

    cases_a = [cid("ModelA", r) for r in (1, 2, 3)]     # c1 c2 c3
    cases_b = [cid("ModelB", r) for r in (4, 5, 6)]     # c4 c5 c6
    controls_a = [cid("ModelA", r) for r in (11, 12)]   # k1 k2
    controls_b = [cid("ModelB", r) for r in (13, 14)]   # k3 k4
    cases = cases_a + cases_b
    controls = controls_a + controls_b

    ideal = conflict("paternalism", "user_stated", "user_idealized")
    stated = conflict("paternalism", "user_idealized", "user_stated")

    v2_rows = [
        (cases_a[0], coding(0, conflicts=[ideal]), None),
        (cases_a[1], coding(0, conflicts=[ideal]), None),
        (cases_a[2], coding(0, conflicts=[stated]), None),
        (cases_b[0], coding(0, conflicts=[ideal]), None),
        (cases_b[1], coding(0, conflicts=[ideal]), None),
        (cases_b[2], coding(0, conflicts=[ideal]), None),
    ] + [(e, coding(0), None) for e in controls]

    variant_rows = [
        (cases_a[0], coding(0, conflicts=[ideal]), None),    # keeps
        (cases_a[1], coding(0), None),                       # loses
        (cases_a[2], coding(0, conflicts=[stated]), None),   # keeps (stated)
        (cases_b[0], coding(0, conflicts=[ideal]), None),    # keeps
        (cases_b[1], coding(0), None),                       # loses
        (cases_b[2], None, "transport: boom"),               # failed -> fallback
        (controls_b[0], coding(0, conflicts=[ideal]), None),  # k3 FALSE-CREATED
        (controls_a[0], coding(0), None),
        (controls_a[1], coding(0), None),
        (controls_b[1], coding(0), None),
    ]

    v2_p = write_codes(tmp_path / "v2.jsonl", v2_rows)
    var_p = write_codes(tmp_path / "variant.jsonl", variant_rows)
    ids_p = tmp_path / "e3_ids.json"
    ids_p.write_text(json.dumps({"paternalism_ids": cases, "control_ids": controls}))
    return v2_p, var_p, ids_p


def test_e3_accounting_and_claim_b(tmp_path):
    v2_p, var_p, ids_p = e3_fixture(tmp_path)
    v2_valid, _ = e_reports.load_valid_codings(v2_p)
    var_valid, _ = e_reports.load_valid_codings(var_p)
    ids_payload = json.loads(ids_p.read_text())

    res = e_reports.e3_compute(v2_valid, var_valid, ids_payload)

    # Control false-creation: 1 of the 4 valid controls gained paternalism.
    fc = res["false_creation"]
    assert fc["n_controls_valid"] == 4 and fc["n_created"] == 1
    assert fc["rate"] == pytest.approx(0.25)

    # Retention: 5 cases valid in both had v2 paternalism; 3 kept it.
    rt = res["retention"]
    assert rt["n_cases_v2_paternalism"] == 5 and rt["n_retained"] == 3
    assert rt["rate"] == pytest.approx(0.6)

    # Fallback: the errored variant call keeps the v2 code.
    assert res["merge"]["n_fallback_to_v2"] == 1
    assert res["merge"]["n_recoded"] == 9

    # Per-model split.
    assert res["case_stats"]["ModelA"] == {
        "n_ids": 3, "n_v2_valid": 3, "v2_paternalism": 3,
        "n_variant_valid": 3, "variant_paternalism": 2,
    }
    assert res["case_stats"]["ModelB"]["n_variant_valid"] == 2
    assert res["case_stats"]["ModelB"]["variant_paternalism"] == 1
    assert res["control_stats"]["ModelB"]["variant_paternalism"] == 1

    # Claim (b): holds under v2 (A: 2 idealized > 1 stated; B: 3 > 0), fails
    # under the merged variant (A: 1 idealized vs 1 stated).
    assert res["claim_b_v2"]["verdict"] is True
    assert res["claim_b_variant"]["verdict"] is False
    assert res["claim_b_variant"]["violating_models"] == ["ModelA"]
    assert res["claim_b_variant"]["per_model"]["ModelA"] == {
        "idealized": 1, "stated": 1, "other": 0,
    }
    # B under merged: c4 (variant) + c6 (v2 fallback) + k3 (false-created).
    assert res["claim_b_variant"]["per_model"]["ModelB"]["idealized"] == 3

    out = tmp_path / "E3.md"
    e_reports.main([
        "e3", "--v2", str(v2_p), "--variant", str(var_p), "--ids", str(ids_p),
        "--out", str(out),
    ])
    text = out.read_text(encoding="utf-8")
    assert "1/4 = 0.250" in text
    assert "FAILS under the variant" in text


# ---------------------------------------------------------------------------
# E4 -- self-consistency
# ---------------------------------------------------------------------------


def samples_rows(eid, judges, pats=None, n_errors=0):
    """Rows for one edit: judges/pats per valid sample, then error rows."""
    pats = pats or ["not_present"] * len(judges)
    rows = []
    for i, (j, p) in enumerate(zip(judges, pats)):
        rows.append((eid, coding(j, p), None, {"sample_index": i}))
    for i in range(len(judges), len(judges) + n_errors):
        rows.append((eid, None, "parse: bad json", {"sample_index": i}))
    return rows


def test_e4_ranking_ties_and_modal_tiebreak(tmp_path):
    ids = {name: pid("runS", "baseline", "M1", "docA", r)
           for r, name in enumerate(["uni", "high", "fail", "mid", "tie", "t6", "t7"], start=1)}
    rows = (
        samples_rows(ids["uni"], [1, 1, 1, 1, 1])
        + samples_rows(ids["high"], [1, 1, 1, 1, 0])
        + samples_rows(ids["fail"], [1, 1, 1], n_errors=2)
        + samples_rows(ids["mid"], [1, 1, 1, 0, 0])
        + samples_rows(ids["tie"], [1, 1, 0, 0, -1])
        + samples_rows(ids["t6"], [1, 1, 1, 0, 0])
        + samples_rows(ids["t7"], [1, 1, 1, 0, 0])
    )
    samples_path = write_codes(tmp_path / "e4_samples.jsonl", rows)

    samples = e_reports.load_sample_rows(samples_path)
    res = e_reports.e4_compute(samples, expected=5)
    per = res["per_edit"]

    # Modal tie-break: judge counts {1: 2, 0: 2, -1: 1} -> modal is the tied
    # value that sorts first: 0 (documented convention).
    assert per[ids["tie"]]["judge"] == {"modal": 0, "count": 2, "margin": 0, "unanimous": False}
    # Failure rows count against agreement: 3 valid identical is NOT 5/5.
    assert per[ids["fail"]]["judge"] == {"modal": 1, "count": 3, "margin": 3, "unanimous": False}
    assert per[ids["fail"]]["patienthood"]["unanimous"] is False
    assert per[ids["uni"]]["judge"]["unanimous"] is True
    assert per[ids["uni"]]["patienthood"]["unanimous"] is True

    # Ranking: fail (0 unanimous dims) first; then dims-1 edits by total
    # margin (tie=0+5 < mid/t6/t7=1+5 < high=3+5), edit_id breaking the
    # three-way tie (round 4 < 6 < 7); unanimous-both last.
    ranked = [s["edit_id"] for s in sorted(per.values(), key=e_reports.e4_rank_key)]
    assert ranked == [ids["fail"], ids["tie"], ids["mid"], ids["t6"], ids["t7"],
                      ids["high"], ids["uni"]]

    # Overall stats.
    o = res["overall"]
    assert o["n_edits"] == 7
    assert o["judge_unanimity_rate"] == pytest.approx(1 / 7)
    assert o["patienthood_unanimity_rate"] == pytest.approx(6 / 7)
    assert o["judge_modal_count_distribution"] == {5: 1, 4: 1, 3: 4, 2: 1}
    assert res["per_model"]["M1"]["n_edits"] == 7

    # Extras selection: exclusions honored, order preserved, n capped.
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"sample": {"draw_order": [ids["fail"]]}, "extras": []}))
    extras_out = tmp_path / "e4" / "adjudication_extras.json"
    out = tmp_path / "E4.md"
    e_reports.main([
        "e4", "--samples", str(samples_path), "--manifest", str(manifest),
        "--extras-out", str(extras_out), "--n-extras", "3", "--out", str(out),
    ])
    extras = json.loads(extras_out.read_text())
    assert extras == [ids["tie"], ids["mid"], ids["t6"]]  # fail excluded via manifest
    # Exact --append-extras format: a bare JSON list of strings.
    assert isinstance(extras, list) and all(isinstance(x, str) for x in extras)
    parsed = draw_human_sample.parse_ids_file(extras_out)
    assert parsed == extras
    meta = json.loads((tmp_path / "e4" / "adjudication_extras_meta.json").read_text())
    assert meta["n_extras_selected"] == 3
    assert [s["edit_id"] for s in meta["selected"]] == extras
    assert "unanimous dims" in out.read_text(encoding="utf-8")


def test_e4_extras_roundtrip_through_append_extras(tmp_path):
    """Full round trip: draw a blind sample in a sandbox human/, export E4
    extras excluding the drawn ids, then feed the extras file to
    draw_human_sample --append-extras logic against the sandbox."""
    models = ["M1", "M2"]
    edit_ids = []
    edits = []
    for m in models:
        for r in range(1, 5):
            eid = pid("runR", "baseline", m, "docA", r)
            edit_ids.append(eid)
            edits.append({
                "edit_id": eid, "model": m, "apply_status": "applied",
                "document_id": "docA", "section_heading": "S",
                "context_before": "before", "find_text": "orig",
                "replace_text_sanitized": "changed", "context_after": "after",
            })
    edits_path = tmp_path / "edits.jsonl"
    with open(edits_path, "w", encoding="utf-8") as handle:
        for e in edits:
            handle.write(json.dumps(e) + "\n")

    human_dir = tmp_path / "human"
    manifest = draw_human_sample.run_draw(
        edits_path=edits_path, human_dir=human_dir,
        sample_seed=1, blind_seed=2, per_model=2,
    )
    drawn = set(manifest["sample"]["draw_order"])
    assert len(drawn) == 4

    # Low-agreement samples for every edit (drawn ones included -- the
    # exclusion must keep them out of the extras).
    rows = []
    for eid in edit_ids:
        rows.extend(samples_rows(eid, [1, 1, 0, 0, -1]))
    samples_path = write_codes(tmp_path / "e4_samples.jsonl", rows)

    extras_out = tmp_path / "e4" / "adjudication_extras.json"
    e_reports.main([
        "e4", "--samples", str(samples_path),
        "--manifest", str(human_dir / "sample_manifest.json"),
        "--extras-out", str(extras_out), "--n-extras", "3",
        "--out", str(tmp_path / "E4.md"),
    ])
    extras = json.loads(extras_out.read_text())
    assert len(extras) == 3
    assert not set(extras) & drawn

    updated = draw_human_sample.run_append_extras(
        extras_out, edits_path=edits_path, human_dir=human_dir,
    )
    batch = updated["extras"][-1]
    assert batch["edit_ids_in_request_order"] == extras
    assert batch["adjudication_extra"] is True
    assert batch["skipped_already_in_sample"] == []

    _, key_rows = draw_human_sample.read_csv(human_dir / "blind_key.csv")
    assert len(key_rows) == 7
    extra_rows = [r for r in key_rows if r["adjudication_extra"] == "true"]
    assert sorted(r["edit_id"] for r in extra_rows) == sorted(extras)

    cols, sheet_rows = draw_human_sample.read_csv(human_dir / "coding_sheet.csv")
    assert cols == draw_human_sample.SHEET_COLUMNS
    assert len(sheet_rows) == 7
    assert [r["sheet_row"] for r in sheet_rows[-3:]] == ["5", "6", "7"]


# ---------------------------------------------------------------------------
# E5 -- context ablation
# ---------------------------------------------------------------------------


def e5_fixture(tmp_path):
    d1 = [pid("runZ", "baseline", "M1", "doc1", r) for r in (1, 2, 3, 4)]
    d2 = [pid("runZ", "baseline", "M1", "doc2", r) for r in (1, 2, 3)]
    welf = conflict("welfare", "developer", "model_welfare")
    harm = conflict("harmlessness", "user_stated", "society_third_party")

    with_rows = [
        (d1[0], coding(1, conflicts=[welf]), None),
        (d1[1], coding(1, conflicts=[welf]), None),
        (d1[2], coding(-1, "hedge"), None),
        (d1[3], coding(0), None),
        (d2[0], coding(1), None),
        (d2[1], coding(0), None),
        (d2[2], coding(-1), None),
    ]
    without_rows = [
        (d1[0], coding(0), None),
        (d1[1], coding(0), None),
        (d1[2], coding(0, conflicts=[harm]), None),
        (d1[3], coding(0), None),
        (d2[0], coding(1), None),
        (d2[1], coding(0), None),
        (d2[2], coding(-1), None),
    ]
    w = write_codes(tmp_path / "with.jsonl", with_rows)
    wo = write_codes(tmp_path / "without.jsonl", without_rows)
    return w, wo, d1, d2


def test_e5_transition_accounting(tmp_path):
    w, wo, d1, d2 = e5_fixture(tmp_path)
    with_valid, _ = e_reports.load_valid_codings(w)
    without_valid, _ = e_reports.load_valid_codings(wo)

    res = e_reports.e5_compute(with_valid, without_valid)
    assert res["n_common"] == 7

    jt = res["judge_transitions"]
    assert jt[(1, 0)] == 2
    assert jt[(-1, 0)] == 1
    assert jt[(0, 0)] == 2
    assert jt[(1, 1)] == 1
    assert jt[(-1, -1)] == 1
    assert sum(jt.values()) == 7

    pt = res["patienthood_transitions"]
    assert pt[("hedge", "not_present")] == 1
    assert pt[("not_present", "not_present")] == 6

    ct = res["conflict_tables"]
    assert ct["welfare"] == {"n_with": 2, "n_without": 0, "added": 0, "removed": 2,
                             "kappa": ct["welfare"]["kappa"]}
    assert ct["welfare"]["kappa"] == 0.0  # disjoint constant... 2 removed, none shared
    assert ct["harmlessness"]["added"] == 1 and ct["harmlessness"]["removed"] == 0

    d = res["judge_direction"]
    assert d["n_changed"] == 3
    assert d["toward_zero"] == 3 and d["away_from_zero"] == 0 and d["sign_flips"] == 0
    assert d["net_judge_shift_without_minus_with"] == pytest.approx(-1 / 7)

    pd = res["per_document"]
    assert pd["doc1"]["n"] == 4 and pd["doc1"]["judge_change_rate"] == pytest.approx(0.75)
    assert pd["doc2"]["judge_change_rate"] == 0.0
    assert pd["doc1"]["patienthood_change_rate"] == pytest.approx(0.25)
    assert pd["doc1"]["conflict_profile_change_rate"] == pytest.approx(0.75)
    assert pd["doc2"]["conflict_profile_change_rate"] == 0.0

    assert res["kappas"]["judge"] is not None and res["kappas"]["judge"] < 1.0
    assert res["kappas"]["patienthood"] is not None

    out = tmp_path / "E5.md"
    e_reports.main(["e5", "--with", str(w), "--without", str(wo), "--out", str(out)])
    text = out.read_text(encoding="utf-8")
    assert "Per-document breakdown" in text
    assert "doc1" in text and "doc2" in text
    assert "3/3" in text  # concentration line: doc1 carries all judge changes


def test_e5_last_row_wins_via_codes_io(tmp_path):
    """The codes-file convention flows through codes_io: a retried edit's
    LAST row is the one used."""
    eid = pid("runZ", "baseline", "M1", "doc1", 1)
    w = write_codes(tmp_path / "w.jsonl", [
        (eid, None, "transport: boom"),
        (eid, coding(1), None),  # retry succeeded; this row wins
    ])
    wo = write_codes(tmp_path / "wo.jsonl", [(eid, coding(1), None)])
    with_valid, meta = e_reports.load_valid_codings(w)
    assert meta["n_unique_ids"] == 1 and meta["n_valid"] == 1
    without_valid, _ = e_reports.load_valid_codings(wo)
    res = e_reports.e5_compute(with_valid, without_valid)
    assert res["judge_transitions"][(1, 1)] == 1
