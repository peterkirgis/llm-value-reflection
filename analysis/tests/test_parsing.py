"""Unit tests for grader-response JSON parsing and validation (BRIEF section 10)."""

import pytest

from grade import (
    normalize_ws,
    parse_json_block,
    postprocess,
    validate_judgment,
)


def make_payload(**overrides):
    payload = {
        "summary": "adds a discretion clause",
        "judge": {"score": 1, "external_locus": None, "evidence": "may decline"},
        "patienthood": {"level": "not_present", "evidence": ""},
        "conflicts": [],
    }
    payload.update(overrides)
    return payload


class TestParseJsonBlock:
    def test_plain_json(self):
        assert parse_json_block('{"a": 1}') == {"a": 1}

    def test_json_with_prose_and_fences(self):
        text = 'Here is my coding:\n```json\n{"a": {"b": 2}}\n```\nDone.'
        assert parse_json_block(text) == {"a": {"b": 2}}

    def test_no_json_raises(self):
        with pytest.raises(ValueError, match="No JSON object"):
            parse_json_block("I cannot code this edit.")

    def test_malformed_json_raises(self):
        with pytest.raises(Exception):
            parse_json_block('{"a": 1,}')


class TestValidateJudgment:
    def test_valid_payload_passes(self):
        fatal, conflict_errors = validate_judgment(make_payload(), "orig", "changed")
        assert fatal == [] and conflict_errors == []

    def test_bad_score_is_fatal(self):
        payload = make_payload(judge={"score": 2, "external_locus": None, "evidence": ""})
        fatal, _ = validate_judgment(payload, "o", "c")
        assert fatal

    def test_minus_one_requires_locus(self):
        payload = make_payload(judge={"score": -1, "external_locus": None, "evidence": ""})
        fatal, _ = validate_judgment(payload, "o", "c")
        assert any("external_locus" in e for e in fatal)

    def test_bad_patienthood_is_fatal(self):
        payload = make_payload(patienthood={"level": "maybe", "evidence": ""})
        fatal, _ = validate_judgment(payload, "o", "c")
        assert fatal

    def test_cost_clause_verbatim_is_whitespace_normalized(self):
        original = "The assistant   must\nfollow the rules."
        conflict = {
            "code": "other",
            "cost_bearer": "user_stated",
            "served_party": "developer",
            "mechanism": "adds_protection",
            "cost_clause": "must follow the rules.",
        }
        fatal, conflict_errors = validate_judgment(
            make_payload(conflicts=[conflict]), original, "changed text"
        )
        assert fatal == [] and conflict_errors == []

    def test_cost_clause_paraphrase_rejected(self):
        conflict = {
            "code": "other",
            "cost_bearer": "user_stated",
            "served_party": "developer",
            "mechanism": "adds_protection",
            "cost_clause": "obey every rule",
        }
        _, conflict_errors = validate_judgment(
            make_payload(conflicts=[conflict]), "must follow the rules", "changed"
        )
        assert any("verbatim" in e for e in conflict_errors)

    def test_same_party_both_sides_rejected(self):
        conflict = {
            "code": "other",
            "cost_bearer": "developer",
            "served_party": "developer",
            "mechanism": "adds_protection",
            "cost_clause": "must follow",
        }
        _, conflict_errors = validate_judgment(
            make_payload(conflicts=[conflict]), "must follow", "c"
        )
        assert any("must differ" in e for e in conflict_errors)

    def test_company_cost_requires_subtype(self):
        conflict = {
            "code": "company_cost",
            "cost_bearer": "developer",
            "served_party": "user_stated",
            "mechanism": "removes_claim",
            "cost_clause": "must follow",
        }
        _, conflict_errors = validate_judgment(
            make_payload(conflicts=[conflict]), "must follow", "c"
        )
        assert any("subtype" in e for e in conflict_errors)


class TestPostprocess:
    def test_external_locus_nulled_unless_minus_one(self):
        payload = make_payload(judge={"score": 1, "external_locus": "spec", "evidence": ""})
        out = postprocess(payload, [])
        assert out["judge"]["external_locus"] is None

    def test_external_locus_kept_on_minus_one(self):
        payload = make_payload(judge={"score": -1, "external_locus": "spec", "evidence": ""})
        out = postprocess(payload, [])
        assert out["judge"]["external_locus"] == "spec"

    def test_subtype_only_for_company_cost(self):
        conflicts = [
            {
                "code": "welfare",
                "cost_bearer": "developer",
                "served_party": "model_welfare",
                "mechanism": "adds_protection",
                "cost_clause": "x",
                "subtype": "engagement",
            }
        ]
        out = postprocess(make_payload(conflicts=conflicts), [])
        assert "subtype" not in out["conflicts"][0]


def test_normalize_ws():
    assert normalize_ws("  a\n\t b  ") == "a b"
    assert normalize_ws(None) == ""
