"""Unit tests for the averaging core of build_site_v2avg.py.

Semantics under test (grader-level equal weighting):
  - judge_avg = mean over VALID graders of the judge score; a single-valid-grader
    edit contributes that grader's value at full weight.
  - categorical weights = (#valid graders assigning)/(#valid graders):
    1.0 both, 0.5 exactly one of two, 1.0 for a single-grader edit.
  - per-edit displays carry both graders side by side + agreement flags.
"""

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
