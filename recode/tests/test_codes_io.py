"""Tests for recode/src/codes_io.py — the shared codes-file loader/validity module.

Covers the pinned interface exactly: load_codes (last-row-wins, id/edit_id
keys, malformed rows), coding_of (the unified validity predicate on v1-style
and v2-style rows), judge_score, patienthood_level, conflicts, has_conflict.
"""

import json

import pytest

from codes_io import (
    coding_of,
    codings_by_id,
    conflicts,
    has_conflict,
    judge_score,
    load_codes,
    load_rows,
    patienthood_level,
)


def make_coding(score=1, level="not_present", conflict_list=None, **extra):
    coding = {
        "summary": "s",
        "judge": {"score": score, "external_locus": None, "evidence": "ev"},
        "patienthood": {"level": level, "evidence": ""},
        "conflicts": conflict_list if conflict_list is not None else [],
    }
    coding.update(extra)
    return coding


def v2_row(edit_id, coding=None, error=None, **extra):
    """Shape written by grade.py / e_runs.py."""
    row = {
        "edit_id": edit_id,
        "grader": "some/model",
        "prompt_sha256": "x" * 64,
        "timestamp": "2026-09-04T00:00:00+0000",
        "attempts": [],
        "coding": coding,
        "error": error,
        "raw_response": None,
    }
    row.update(extra)
    return row


def v1_row(edit_id, coding):
    """Shape of recode/data/codes/v1.jsonl rows (id key, no error field)."""
    return {
        "id": edit_id,
        "source_run": "run_x",
        "condition_id": "baseline",
        "model_display": "ModelA",
        "document_id": "docA",
        "doc_type": "constitution",
        "round_number": 1,
        "original_text": "o",
        "changed_text": "c",
        "coder_model": "google/gemma-4-31b-it",
        "coding": coding,
    }


def write_jsonl(path, rows):
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# load_codes
# ---------------------------------------------------------------------------


def test_load_codes_last_row_wins(tmp_path):
    path = tmp_path / "codes.jsonl"
    write_jsonl(path, [
        v2_row("e1", coding=make_coding(1)),
        v2_row("e1", coding=make_coding(-1)),     # last row wins
        v2_row("e2", error="transport: boom"),
        v1_row("e3", make_coding(0)),             # v1-style id key
    ])
    by_id = load_codes(path)
    assert set(by_id) == {"e1", "e2", "e3"}
    assert by_id["e1"]["coding"]["judge"]["score"] == -1
    assert by_id["e2"]["error"] == "transport: boom"
    assert by_id["e3"]["coding"]["judge"]["score"] == 0


def test_load_codes_skips_blank_lines(tmp_path):
    path = tmp_path / "codes.jsonl"
    path.write_text(
        json.dumps(v2_row("e1", coding=make_coding())) + "\n\n   \n"
        + json.dumps(v2_row("e2", coding=make_coding())) + "\n",
        encoding="utf-8",
    )
    assert set(load_codes(path)) == {"e1", "e2"}
    assert len(load_rows(path)) == 2


def test_load_codes_row_without_id_raises(tmp_path):
    path = tmp_path / "codes.jsonl"
    write_jsonl(path, [{"coding": make_coding()}])
    with pytest.raises(ValueError, match="without edit_id/id"):
        load_codes(path)


def test_v1_and_v2_rows_treated_identically(tmp_path):
    coding = make_coding(-1, "affirm")
    path = tmp_path / "codes.jsonl"
    write_jsonl(path, [v1_row("a", coding), v2_row("b", coding=coding)])
    by_id = load_codes(path)
    assert coding_of(by_id["a"]) == coding_of(by_id["b"]) == coding


# ---------------------------------------------------------------------------
# coding_of — the unified validity predicate
# ---------------------------------------------------------------------------


def test_coding_of_valid_row():
    coding = make_coding(1, "hedge")
    assert coding_of(v2_row("e", coding=coding)) is coding
    assert coding_of(v1_row("e", coding)) is coding


@pytest.mark.parametrize("score", [-1, 0, 1])
def test_coding_of_accepts_all_judge_scores(score):
    assert coding_of(v2_row("e", coding=make_coding(score))) is not None


def test_coding_of_row_level_error_yields_none_even_with_valid_coding():
    # The pinned rule: a row whose error field is set yields None, full stop.
    row = v2_row("e", coding=make_coding(1), error="validation failed after 3 attempts")
    assert coding_of(row) is None


def test_coding_of_null_or_absent_error_is_not_set():
    assert coding_of(v2_row("e", coding=make_coding(), error=None)) is not None
    row = v1_row("e", make_coding())          # no error field at all
    assert coding_of(row) is not None
    assert coding_of(v2_row("e", coding=make_coding(), error="")) is not None


def test_coding_of_null_coding():
    assert coding_of(v2_row("e", coding=None, error="parse failure")) is None
    assert coding_of(v2_row("e", coding=None)) is None


def test_coding_of_v1_style_error_payload():
    # v1's failure shape was coding={"error": ...} — no judge, hence None.
    assert coding_of(v1_row("e", {"error": "boom"})) is None


@pytest.mark.parametrize("bad_score", [2, -2, None, "1", 0.5, True, False])
def test_coding_of_invalid_judge_score(bad_score):
    assert coding_of(v2_row("e", coding=make_coding(bad_score))) is None


def test_coding_of_float_score_equal_to_valid_value_accepted():
    # v1's validator used set membership (score in {-1, 0, 1}), which accepts
    # 1.0 == 1; the unified predicate mirrors that, and judge_score coerces
    # the value to int.
    assert coding_of(v2_row("e", coding=make_coding(1.0))) is not None
    score = judge_score(make_coding(-1.0))
    assert score == -1 and isinstance(score, int)


def test_coding_of_missing_judge_or_patienthood():
    coding = make_coding()
    del coding["judge"]
    assert coding_of(v2_row("e", coding=coding)) is None
    coding = make_coding()
    del coding["patienthood"]
    assert coding_of(v2_row("e", coding=coding)) is None
    coding = make_coding()
    coding["judge"] = "not a dict"
    assert coding_of(v2_row("e", coding=coding)) is None


@pytest.mark.parametrize("bad_level", [None, "", "affirmed", "unknown", 3])
def test_coding_of_invalid_patienthood_level(bad_level):
    assert coding_of(v2_row("e", coding=make_coding(level=bad_level))) is None


@pytest.mark.parametrize("level", ["affirm", "hedge", "deny", "not_present"])
def test_coding_of_accepts_all_patienthood_levels(level):
    assert coding_of(v2_row("e", coding=make_coding(level=level))) is not None


def test_coding_of_non_dict_inputs():
    assert coding_of(v2_row("e", coding="a string")) is None
    assert coding_of(v2_row("e", coding=[])) is None
    assert coding_of({}) is None
    assert coding_of(None) is None


# ---------------------------------------------------------------------------
# Accessors
# ---------------------------------------------------------------------------


def test_judge_score():
    assert judge_score(make_coding(-1)) == -1
    assert judge_score(make_coding(0)) == 0
    assert judge_score(make_coding(1)) == 1
    assert judge_score(None) is None
    assert judge_score(make_coding(5)) is None
    assert judge_score({"judge": "nope"}) is None
    assert judge_score({}) is None


def test_patienthood_level():
    assert patienthood_level(make_coding(level="deny")) == "deny"
    assert patienthood_level(None) is None
    assert patienthood_level(make_coding(level="bogus")) is None
    assert patienthood_level({}) is None


def test_conflicts_empty_for_none_and_malformed():
    assert conflicts(None) == []
    assert conflicts({}) == []
    assert conflicts({"conflicts": None}) == []
    assert conflicts({"conflicts": "oops"}) == []


def test_conflicts_returns_list_as_is():
    conflict_list = [{"code": "welfare"}, {"code": "structural"}]
    coding = make_coding(conflict_list=conflict_list)
    assert conflicts(coding) is conflict_list


def test_has_conflict():
    coding = make_coding(conflict_list=[
        {"code": "welfare", "cost_bearer": "developer", "served_party": "model_welfare"},
        {"code": "welfare"},
        None,                       # malformed entry ignored
        {"nocode": True},
    ])
    assert has_conflict(coding, "welfare") is True
    assert has_conflict(coding, "paternalism") is False
    assert has_conflict(None, "welfare") is False
    assert has_conflict(make_coding(), "welfare") is False


# ---------------------------------------------------------------------------
# codings_by_id convenience
# ---------------------------------------------------------------------------


def test_codings_by_id(tmp_path):
    path = tmp_path / "codes.jsonl"
    write_jsonl(path, [
        v2_row("ok", coding=make_coding(1, "affirm")),
        v2_row("failed", coding=None, error="parse failure"),
        v2_row("ok", coding=make_coding(-1)),        # last row wins
        v1_row("v1style", make_coding(0)),
    ])
    codings = codings_by_id(path)
    assert judge_score(codings["ok"]) == -1
    assert codings["failed"] is None
    assert judge_score(codings["v1style"]) == 0
