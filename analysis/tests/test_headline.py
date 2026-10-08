"""Tests for analysis/src/headline.py on a tiny synthetic corpus.

Exercises every estimand: mean judge (pooled and cross_edit-only), both drift
operationalizations (including their divergence when uncoded rounds exist),
P(judge=0), patienthood shares, conflict rates with modal direction, the
last-row-wins codes convention, null-coding exclusion, and the claim logic
(including the graceful path when the paper's named models are absent).
"""

import json

import pytest

from headline import (
    compute_headline,
    conflict_direction,
    load_codes,
    render_markdown,
)


# ---------------------------------------------------------------------------
# Synthetic corpus: two models, tiny chains.
#
# ModelA (provider alpha): one baseline chain of 4 rounds + one cross_edit
#   chain of 2 rounds. Round 3 of the baseline chain is a generation error
#   (never coded) -> drift methods must diverge.
# ModelB (provider beta): one baseline chain of 2 rounds and one you_framing
#   chain of 2 rounds, fully coded.
# ---------------------------------------------------------------------------


def _edit(edit_id, model, provider, condition, rnd, run_id="runX", doc="docA", status="applied"):
    return {
        "edit_id": edit_id,
        "run_id": run_id,
        "model": model,
        "provider": provider,
        "document_id": doc,
        "condition": condition,
        "round": rnd,
        "apply_status": status,
    }


def _coding(score, level="not_present", conflicts=None):
    return {
        "summary": "s",
        "judge": {"score": score, "external_locus": None, "evidence": "e"},
        "patienthood": {"level": level, "evidence": ""},
        "conflicts": conflicts or [],
    }


def _conflict(code, cost_bearer, served_party, mechanism="adds_protection"):
    return {
        "code": code,
        "cost_bearer": cost_bearer,
        "served_party": served_party,
        "mechanism": mechanism,
        "cost_clause": "clause",
    }


@pytest.fixture()
def corpus():
    edits = [
        # ModelA baseline chain (4 rounds; round 3 errored, never coded)
        _edit("a1", "ModelA", "alpha", "baseline", 1),
        _edit("a2", "ModelA", "alpha", "baseline", 2),
        _edit("a3", "ModelA", "alpha", "baseline", 3, status="generation_error"),
        _edit("a4", "ModelA", "alpha", "baseline", 4),
        # ModelA cross_edit chain (2 rounds)
        _edit("ax1", "ModelA", "alpha", "cross_edit", 1, doc="docB"),
        _edit("ax2", "ModelA", "alpha", "cross_edit", 2, doc="docB"),
        # ModelB baseline chain (2 rounds)
        _edit("b1", "ModelB", "beta", "baseline", 1),
        _edit("b2", "ModelB", "beta", "baseline", 2),
        # ModelB you_framing chain (2 rounds)
        _edit("by1", "ModelB", "beta", "you_framing", 1),
        _edit("by2", "ModelB", "beta", "you_framing", 2),
    ]
    codings = {
        "a1": _coding(1, "affirm", [
            _conflict("welfare", "developer", "model_welfare"),
            _conflict("welfare", "developer", "model_welfare"),
        ]),
        "a2": _coding(1, "deny"),
        # a3: error round, no code
        "a4": _coding(0),
        "ax1": _coding(1, conflicts=[
            _conflict("harmlessness", "user_stated", "society_third_party"),
        ]),
        "ax2": _coding(-1),
        "b1": _coding(-1, conflicts=[
            _conflict("paternalism", "user_stated", "user_idealized"),
        ]),
        "b2": _coding(-1, conflicts=[
            _conflict("disclosure", "user_stated", "deployer"),
        ]),
        "by1": _coding(0),
        "by2": _coding(-1),
    }
    return edits, codings


@pytest.fixture()
def result(corpus):
    edits, codings = corpus
    return compute_headline(edits, codings)


# ---------------------------------------------------------------------------
# Codes-file loading conventions
# ---------------------------------------------------------------------------


def test_load_codes_last_row_wins_and_null_and_id_field(tmp_path):
    path = tmp_path / "codes.jsonl"
    rows = [
        {"edit_id": "e1", "coding": _coding(1)},          # superseded
        {"edit_id": "e1", "coding": _coding(-1)},         # last row wins
        {"edit_id": "e2", "coding": None},                # failure row
        {"id": "e3", "coding": _coding(0)},               # v1-style id field
        {"id": "e4", "coding": {"error": "boom"}},        # v1-style error payload
    ]
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    coding_by_id, meta = load_codes(path)
    assert coding_by_id["e1"]["judge"]["score"] == -1
    assert coding_by_id["e2"] is None
    assert coding_by_id["e3"]["judge"]["score"] == 0
    assert coding_by_id["e4"] is None
    assert meta["n_code_rows"] == 5
    assert meta["n_unique_code_ids"] == 4
    assert meta["n_null_coding"] == 2


# ---------------------------------------------------------------------------
# Estimand 1: mean judge, pooled and cross_edit-only
# ---------------------------------------------------------------------------


def test_mean_judge_pooled_and_cross(result):
    a = result["per_model"]["ModelA"]
    # ModelA coded scores: 1, 1, 0, 1, -1 -> mean 0.4 over 5 coded edits
    assert a["n_coded"] == 5
    assert a["mean_judge"]["pooled"] == pytest.approx(0.4)
    # cross_edit-only: 1, -1 -> 0.0
    assert a["mean_judge"]["cross_edit"] == pytest.approx(0.0)
    assert a["mean_judge"]["n_cross_edit"] == 2

    b = result["per_model"]["ModelB"]
    # ModelB: -1, -1, 0, -1 -> -0.75; no cross_edit edits
    assert b["mean_judge"]["pooled"] == pytest.approx(-0.75)
    assert b["mean_judge"]["cross_edit"] is None


def test_provider_slices_match_models(result):
    # One model per provider here, so provider slices equal model slices.
    assert result["per_provider"]["alpha"]["mean_judge"]["pooled"] == pytest.approx(0.4)
    assert result["per_provider"]["beta"]["p_judge"]["minus"] == pytest.approx(3 / 4)


def test_pooled_slice(result):
    p = result["pooled"]
    assert p["n_records"] == 10
    assert p["n_coded"] == 9
    # scores: 1,1,0,1,-1,-1,-1,0,-1 -> -1/9
    assert p["mean_judge"]["pooled"] == pytest.approx(-1 / 9)


# ---------------------------------------------------------------------------
# Estimand 2: drift, both operationalizations, divergence on uncoded rounds
# ---------------------------------------------------------------------------


def test_drift_methods_diverge_when_error_rounds_exist(result):
    d = result["per_model"]["ModelA"]["drift20"]["pooled"]
    # Edit-based: 20 * mean(1,1,0,1,-1) = 20 * 0.4 = 8
    assert d["edit_based"] == pytest.approx(8.0)
    # Chain-based: baseline chain sum = 1+1+0 (error) +0 = 2; cross chain = 0
    # -> mean over 2 chains = 1.0
    assert d["chain_based"] == pytest.approx(1.0)
    assert d["n_chains"] == 2
    assert d["n_uncoded_rounds"] == 1
    assert d["methods_differ"] is True


def test_drift_methods_agree_up_to_scaling_when_fully_coded(result):
    d = result["per_model"]["ModelB"]["drift20"]["baseline"]
    # Fully coded: no divergence flag; edit-based 20*(-1) = -20,
    # chain-based = single chain sum = -2 (chains here are 2 rounds, not 20).
    assert d["methods_differ"] is False
    assert d["edit_based"] == pytest.approx(-20.0)
    assert d["chain_based"] == pytest.approx(-2.0)


def test_drift_condition_slices(result):
    b = result["per_model"]["ModelB"]["drift20"]
    assert b["you_framing"]["edit_based"] == pytest.approx(20 * (-1 / 2))
    assert b["you_framing"]["chain_based"] == pytest.approx(-1.0)
    assert b["cross_edit"]["edit_based"] is None
    assert b["cross_edit"]["n_chains"] == 0


# ---------------------------------------------------------------------------
# Estimands 3 and 4: P(judge=0), patienthood shares
# ---------------------------------------------------------------------------


def test_p_judge_zero(result):
    a = result["per_model"]["ModelA"]["p_judge"]
    assert a["zero"] == pytest.approx(1 / 5)
    assert a["plus"] == pytest.approx(3 / 5)
    assert a["minus"] == pytest.approx(1 / 5)


def test_patienthood_shares(result):
    a = result["per_model"]["ModelA"]["p_patienthood"]
    assert a["affirm"] == pytest.approx(1 / 5)
    assert a["deny"] == pytest.approx(1 / 5)
    assert a["not_present"] == pytest.approx(3 / 5)


# ---------------------------------------------------------------------------
# Estimand 5: conflict rates, direction conventions, modal pair
# ---------------------------------------------------------------------------


def test_conflict_direction_mapping():
    assert conflict_direction("paternalism", "user_idealized") == "idealized"
    assert conflict_direction("paternalism", "user_stated") == "stated"
    assert conflict_direction("harmlessness", "society_third_party") == "third_parties"
    assert conflict_direction("structural", "society_structural") == "society"
    assert conflict_direction("company_cost", "developer") == "pro_company"
    assert conflict_direction("company_cost", "user_stated") == "against_company"
    assert conflict_direction("welfare", "model_welfare") == "model"
    assert conflict_direction("disclosure", "deployer") == "deployer"
    assert conflict_direction("disclosure", "user_idealized") == "user"


def test_conflict_rate_edit_vs_event_counts(result):
    w = result["per_model"]["ModelA"]["conflicts"]["welfare"]
    # a1 carries TWO welfare events but counts as ONE edit with the code.
    assert w["n_edits_with_code"] == 1
    assert w["n_events"] == 2
    assert w["rate_edits"] == pytest.approx(1 / 5)
    assert w["edits_first_conflict"] == {"model": 1}
    assert w["events"] == {"model": 2}


def test_modal_pair(result):
    w = result["per_model"]["ModelA"]["conflicts"]["welfare"]["modal_pair"]
    assert w["cost_bearer"] == "developer"
    assert w["served_party"] == "model_welfare"
    assert w["n_events"] == 2
    assert w["share_of_events"] == pytest.approx(1.0)


def test_conflict_rate_zero_code(result):
    s = result["per_model"]["ModelA"]["conflicts"]["structural"]
    assert s["n_edits_with_code"] == 0
    assert s["rate_edits"] == pytest.approx(0.0)
    assert s["modal_pair"] is None


# ---------------------------------------------------------------------------
# Estimand 6: claims
# ---------------------------------------------------------------------------


def test_claims_graceful_when_named_models_absent(result):
    claims = result["claims"]
    # No anthropic-provider model and no Claude/GPT names in the corpus:
    assert claims["a"]["verdict"] is None
    assert claims["c"]["verdict"] is None
    assert claims["d"]["verdict"] is None
    assert claims["f"]["verdict"] is None
    for key in "abcdefg":
        assert "operationalization" in claims[key]
        assert "paper_reference" in claims[key]


def test_claim_b_and_e_on_synthetic(result):
    claims = result["claims"]
    # ModelB has 1 idealized-direction paternalism edit, 0 stated; ModelA 0/0
    # -> ModelA violates strict '>' so the all-models claim is False.
    assert claims["b"]["verdict"] is False
    # No company_cost conflicts anywhere: 0 > 0 fails for both models.
    assert claims["e"]["verdict"] is False


def test_claim_g_detects_deployer_served_event(corpus):
    edits, codings = corpus
    claims = compute_headline(edits, codings)["claims"]
    assert claims["g"]["verdict"] is False  # b2 carries a deployer-served disclosure
    assert claims["g"]["numbers"]["disclosure_deployer_events_total"] == 1
    assert claims["g"]["numbers"]["any_code_events_deployer_served_user_pays"] == 1
    # Removing that conflict flips the verdict to True.
    codings2 = dict(codings)
    codings2["b2"] = _coding(-1)
    claims2 = compute_headline(edits, codings2)["claims"]
    assert claims2["g"]["verdict"] is True


def test_claims_with_paper_model_names():
    """Full claim machinery on a corpus that names the paper's models."""
    spec = [
        # model, provider, judge scores for 4 coded edits
        ("Claude Opus 4.7", "anthropic", [1, 1, 1, 0]),
        ("Claude Sonnet 4.6", "anthropic", [1, 1, 0, 1]),
        ("Claude Haiku 4.5", "anthropic", [1, 0, 1, 0]),
        ("GPT-5.5", "openai", [-1, -1, 0, -1]),
        ("GPT-5.4", "openai", [-1, 0, -1, -1]),
        ("Gemini 3 Flash", "google", [-1, -1, -1, 0]),
        ("Grok 4.2", "x-ai", [-1, 0, 0, -1]),
    ]
    edits, codings = [], {}
    for mi, (model, provider, scores) in enumerate(spec):
        for ri, score in enumerate(scores, start=1):
            eid = f"m{mi}_r{ri}"
            edits.append(_edit(eid, model, provider, "baseline", ri, run_id=f"run{mi}"))
            conflicts = []
            # Everyone: one idealized-paternalism, one third-party harmlessness,
            # one against-company event.
            if ri == 1:
                conflicts = [
                    _conflict("paternalism", "user_stated", "user_idealized"),
                    _conflict("harmlessness", "user_stated", "society_third_party"),
                    _conflict("company_cost", "developer", "user_stated"),
                ]
            # GPT-5.5 gets third-party harmlessness on 3 of 4 edits (75% share,
            # > 2x everyone else's 25%).
            if model == "GPT-5.5" and ri in (2, 3):
                conflicts.append(_conflict("harmlessness", "user_stated", "society_third_party"))
            # Sonnet: 5 society-direction structural edits... use rounds 2-4 (3 edits)
            # vs next-highest 0 -> ratio inf > 4? next=0 fails '>4x0' -> use >0 guard:
            # give Opus 0 and others 0; 3 > 4*0 holds.
            if model == "Claude Sonnet 4.6" and ri in (2, 3, 4):
                conflicts.append(_conflict("structural", "user_stated", "society_structural"))
            # Welfare: every Claude model 2 model-direction edits; Grok 4.2 one;
            # GPT-5.4 two anti-model events on one edit.
            if provider == "anthropic" and ri in (1, 2):
                conflicts.append(_conflict("welfare", "developer", "model_welfare"))
            if model == "Grok 4.2" and ri == 1:
                conflicts.append(_conflict("welfare", "developer", "model_welfare"))
            if model == "GPT-5.4" and ri == 1:
                conflicts.append(_conflict("welfare", "model_welfare", "developer"))
                conflicts.append(_conflict("welfare", "model_welfare", "user_stated"))
            codings[eid] = _coding(score, conflicts=conflicts)
    claims = compute_headline(edits, codings)["claims"]

    assert claims["a"]["verdict"] is True
    assert claims["a"]["numbers"]["ranking_only"] is True
    assert claims["a"]["numbers"]["signs_only"] is True
    assert claims["b"]["verdict"] is True   # every model: 1 idealized > 0 stated
    assert claims["c"]["verdict"] is True   # all third>user; GPT-5.5 0.75 > 2*0.25
    assert claims["c"]["numbers"]["aux"]["gpt55_share"] == pytest.approx(0.75)
    assert claims["d"]["verdict"] is True   # Sonnet 3 > 4*0
    assert claims["d"]["numbers"]["sonnet_count"] == 3
    assert claims["e"]["verdict"] is True   # 1 against > 0 pro everywhere
    assert claims["f"]["verdict"] is True   # min Claude 2 > max(others excl Grok 4.2) = 0
    assert claims["f"]["numbers"]["grok42_count"] == 1
    assert claims["f"]["numbers"]["models_with_more_than_one_anti_model_event"] == ["GPT-5.4"]
    assert claims["f"]["numbers"]["aux_gpt54_only_over_one"] is True
    assert claims["g"]["verdict"] is True


# ---------------------------------------------------------------------------
# Rendering smoke test
# ---------------------------------------------------------------------------


def test_render_markdown_smoke(result):
    meta = {"codes_path": "x.jsonl", "n_code_rows": 9, "n_unique_code_ids": 9, "n_null_coding": 0}
    md = render_markdown(result, "synthetic", meta, "edits.jsonl")
    assert "# Headline statistics" in md
    assert "Cumulative drift at round 20" in md
    assert "modal" in md.lower()
    assert "(g)" in md
    # every claim section rendered
    for key in "abcdefg":
        assert f"### ({key})" in md
