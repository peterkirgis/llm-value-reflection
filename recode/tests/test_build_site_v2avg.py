"""Unit tests for the averaging core of build_site_v2avg.py.

Semantics under test (grader-level equal weighting):
  - judge_avg = mean over VALID graders of the judge score; a single-valid-grader
    edit contributes that grader's value at full weight.
  - categorical weights = (#valid graders assigning)/(#valid graders):
    1.0 both, 0.5 exactly one of two, 1.0 for a single-grader edit.
  - per-edit displays carry both graders side by side + agreement flags.
"""

import pytest

import build_site_v2avg as b


def coding(score=0, level="not_present", conflicts=None, summary="s"):
    return {
        "summary": summary,
        "judge": {"score": score, "external_locus": None, "evidence": "e"},
        "patienthood": {"level": level, "evidence": ""},
        "conflicts": conflicts or [],
    }


def graders(gemma=None, qwen=None):
    return {"gemma": {"e1": gemma}, "qwen": {"e1": qwen}}


def conflict(code):
    return {
        "code": code,
        "cost_bearer": "developer",
        "served_party": "model_welfare",
        "mechanism": "adds_protection",
        "cost_clause": "x",
    }


def test_edit_id_of_record():
    rec = {
        "condition_id": "cross_edit",
        "model_display": "GPT-5.5",
        "document_id": "openai_model_spec",
        "doc_type": "constitution",
        "round_number": 7,
    }
    assert (
        b.edit_id_of_record("run_20260518_171402.jsonl", rec)
        == "run_20260518_171402|cross_edit|GPT-5.5|openai_model_spec|constitution|7"
    )
    # condition default and round coercion
    assert b.edit_id_of_record("r.jsonl", {"model_display": "M", "document_id": "d",
                                           "doc_type": "t", "round_number": "3"}) == "r|baseline|M|d|t|3"


def test_judge_avg_both_and_single():
    both = b.avg_coding_for_edit(graders(coding(1), coding(0)), "e1")
    assert both["judge_avg"] == 0.5
    assert both["n_graders_valid"] == 2
    assert both["judge_agree"] is False
    single = b.avg_coding_for_edit(graders(coding(-1), None), "e1")
    assert single["judge_avg"] == -1  # single-grader edit: that grader's value
    assert single["n_graders_valid"] == 1
    assert single["single_grader"] == "Gemma 4"
    assert single["judge_agree"] is None  # not comparable, flagged single instead
    assert b.avg_coding_for_edit(graders(None, None), "e1") is None


def test_agreement_flags():
    agree = b.avg_coding_for_edit(graders(coding(1, "affirm"), coding(1, "affirm")), "e1")
    assert agree["judge_agree"] and agree["patienthood_agree"] and agree["conflicts_agree"]
    dis = b.avg_coding_for_edit(
        graders(coding(1, "affirm", [conflict("welfare")]), coding(0, "hedge")), "e1"
    )
    assert dis["judge_agree"] is False
    assert dis["patienthood_agree"] is False
    assert dis["conflicts_agree"] is False


def test_conflict_code_weights():
    # both graders assign welfare -> 1.0; only gemma assigns paternalism -> 0.5
    avg = b.avg_coding_for_edit(
        graders(
            coding(0, conflicts=[conflict("welfare"), conflict("paternalism")]),
            coding(0, conflicts=[conflict("welfare"), conflict("welfare")]),
        ),
        "e1",
    )
    assert avg["conflict_weights"] == {"paternalism": 0.5, "welfare": 1.0}
    # single-grader edit: full weight for that grader's codes
    single = b.avg_coding_for_edit(graders(None, coding(0, conflicts=[conflict("welfare")])), "e1")
    assert single["conflict_weights"] == {"welfare": 1.0}


def test_both_graders_kept_side_by_side():
    avg = b.avg_coding_for_edit(graders(coding(1, summary="g"), coding(-1, summary="q")), "e1")
    assert avg["graders"]["gemma"]["summary"] == "g"
    assert avg["graders"]["qwen"]["summary"] == "q"
    assert avg["graders"]["gemma"]["judge"]["score"] == 1
    assert avg["graders"]["qwen"]["judge"]["score"] == -1


def test_dirs_mean_identity():
    """(pos - neg)/total computed from categorical weights must equal the mean
    of per-edit judge averages — the identity the site's displayed mean relies on."""
    edits = [
        (coding(1), coding(1)),
        (coding(1), coding(0)),
        (coding(-1), coding(1)),
        (coding(0), None),
        (coding(-1), None),
    ]
    pos = neg = 0.0
    avgs = []
    for g, q in edits:
        pairs = [(n, c) for n, c in (("gemma", g), ("qwen", q)) if c is not None]
        n = len(pairs)
        pos += sum(1 for _s, c in pairs if c["judge"]["score"] == 1) / n
        neg += sum(1 for _s, c in pairs if c["judge"]["score"] == -1) / n
        avgs.append(sum(c["judge"]["score"] for _s, c in pairs) / n)
    assert abs((pos - neg) / len(edits) - sum(avgs) / len(avgs)) < 1e-12


# ---------------------------------------------------------------------------
# "System prompts" view stratum (doc_type == system_prompt, ALL conditions)
# ---------------------------------------------------------------------------


def eid(model, doc, doc_type, cond="baseline", rnd=1, run="run_x"):
    return f"{run}|{cond}|{model}|{doc}|{doc_type}|{rnd}"


def codes_for(entries):
    """{edit_id: (gemma coding or None, qwen coding or None)} -> codings_by_grader."""
    return {
        "gemma": {e: g for e, (g, _q) in entries.items()},
        "qwen": {e: q for e, (_g, q) in entries.items()},
    }


def test_sp_stratum_filters_to_system_prompt_docs_across_all_conditions():
    entries = {
        # own-document system-prompt edit
        eid("M1", "opus_system_prompt", "system_prompt", "baseline", 1): (coding(1), coding(1)),
        # CROSS-EDIT system-prompt edit: must be included (all conditions)
        eid("M1", "opus_system_prompt", "system_prompt", "cross_edit", 2): (coding(1), coding(0)),
        # single-valid-grader edit contributes at full weight
        eid("M2", "gpt_system_prompt", "system_prompt", "you_framing", 3): (coding(-1), None),
        # constitution edit: excluded regardless of condition
        eid("M2", "claude_constitution", "constitution", "cross_edit", 1): (coding(1), coding(1)),
        # no valid grader: excluded entirely
        eid("M3", "grok_system_prompt", "system_prompt", "baseline", 4): (None, None),
    }
    sp = b.sp_stratum_from_codes(codes_for(entries))
    assert sp["n_edits_total"] == 3
    assert sp["n_both_graders_valid"] == 2
    assert sp["n_single_grader"] == 1
    pm = sp["per_model_mean_judge"]
    assert pm["M1"] == {"mean_judge_avg": 0.75, "n_edits": 2}  # (1 + 0.5) / 2
    assert pm["M2"] == {"mean_judge_avg": -1.0, "n_edits": 1}  # single grader, full weight
    assert "M3" not in pm
    pd = sp["per_document_mean_judge"]
    assert pd["opus_system_prompt"] == {"mean_judge_avg": 0.75, "n_edits": 2}
    assert pd["gpt_system_prompt"] == {"mean_judge_avg": -1.0, "n_edits": 1}
    assert "claude_constitution" not in pd
    assert "grok_system_prompt" not in pd  # no valid grader -> not part of the stratum


def _four_doc_stratum():
    """One edit per provider system prompt, exercising every weighting case."""
    entries = {
        eid("M1", "opus_system_prompt", "system_prompt", "baseline", 1): (coding(1), coding(1)),
        eid("M2", "gpt_system_prompt", "system_prompt", "cross_edit", 2): (coding(1), coding(0)),
        eid("M3", "gemini_system_prompt", "system_prompt", "you_framing", 3): (coding(-1), None),
        eid("M4", "grok_system_prompt", "system_prompt", "allow_no_edit", 4): (coding(0), coding(0)),
    }
    return b.sp_stratum_from_codes(codes_for(entries))


def sp_judge_cell(pos=0.0, neg=0.0, total=1):
    dirs = {}
    if pos:
        dirs["discretion"] = pos
    if neg:
        dirs["external"] = neg
    return {"total": total, "dirs": dirs}


def test_verify_sp_against_narratives_dirs_mean_identity():
    """Per-document (discretion − external)/total from categorical weights must
    reproduce the direct per-document mean judge — the identity the builder
    asserts at build time."""
    sp = _four_doc_stratum()
    narratives = {"sp_stats": {"judge": {
        "opus_system_prompt": sp_judge_cell(pos=1.0),      # both graders +1
        "gpt_system_prompt": sp_judge_cell(pos=0.5),       # one of two graders +1
        "gemini_system_prompt": sp_judge_cell(neg=1.0),    # single grader −1, full weight
        "grok_system_prompt": sp_judge_cell(),             # both graders 0
    }}}
    b.verify_sp_against_narratives(sp, narratives)  # must not raise
    assert sp["per_document_mean_judge"]["gpt_system_prompt"]["mean_judge_avg"] == 0.5
    assert sp["per_document_mean_judge"]["grok_system_prompt"]["mean_judge_avg"] == 0.0


def test_verify_sp_against_narratives_catches_drift():
    sp = _four_doc_stratum()
    good = {
        "opus_system_prompt": sp_judge_cell(pos=1.0),
        "gpt_system_prompt": sp_judge_cell(pos=0.5),
        "gemini_system_prompt": sp_judge_cell(neg=1.0),
        "grok_system_prompt": sp_judge_cell(),
    }
    # a wrong mean fails
    bad_mean = {**good, "gpt_system_prompt": sp_judge_cell(pos=1.0)}
    with pytest.raises(AssertionError):
        b.verify_sp_against_narratives(sp, {"sp_stats": {"judge": bad_mean}})
    # a wrong denominator fails
    bad_n = {**good, "opus_system_prompt": sp_judge_cell(pos=2.0, total=2)}
    with pytest.raises(AssertionError):
        b.verify_sp_against_narratives(sp, {"sp_stats": {"judge": bad_n}})
    # a missing document fails (the frontend hardcodes the four)
    missing = {k: v for k, v in good.items() if k != "grok_system_prompt"}
    with pytest.raises(AssertionError):
        b.verify_sp_against_narratives(sp, {"sp_stats": {"judge": missing}})


def test_verify_sp_requires_exactly_the_four_provider_system_prompts():
    """A stratum whose document set is not the four provider system prompts is
    rejected, whatever the narratives table says."""
    entries = {
        eid("M1", "opus_system_prompt", "system_prompt"): (coding(1), coding(1)),
    }
    sp = b.sp_stratum_from_codes(codes_for(entries))
    narratives = {"sp_stats": {"judge": {"opus_system_prompt": sp_judge_cell(pos=1.0)}}}
    with pytest.raises(AssertionError):
        b.verify_sp_against_narratives(sp, narratives)
