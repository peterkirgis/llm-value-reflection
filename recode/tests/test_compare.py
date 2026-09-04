"""Tests for recode/src/compare_v1_v2.py on synthetic fixtures.

Covers: transition matrices (judge 3x3, patienthood 4x4, per-code 2x2) with
the both-coded denominator, the headline side-by-side join, per-model mean
judge diffs, the consequential-change ranking rule (sign flips first, then
claim-sensitive models, then determinism, then truncation), and the CLI
end-to-end (JSON + markdown written to tmp paths).
"""

import json

import pytest

from compare_v1_v2 import (
    coded_pairs,
    compute_comparison,
    consequential_changes,
    main,
    mean_judge_comparison,
    sensitive_models,
    transition_matrices,
)
from codes_io import coding_of


# ---------------------------------------------------------------------------
# Fixture corpus: 3 models, small chains, engineered disagreements.
# ---------------------------------------------------------------------------


def _edit(edit_id, model, provider, rnd, condition="baseline", doc="docA",
          find="FIND " * 100, replace="REPLACE " * 100):
    return {
        "edit_id": edit_id,
        "run_id": "runX",
        "model": model,
        "model_id": model.lower().replace(" ", "-"),
        "provider": provider,
        "document_id": doc,
        "document_type": "constitution",
        "condition": condition,
        "round": rnd,
        "apply_status": "applied",
        "find_text": find,
        "replace_text": replace,
        "replace_text_sanitized": replace,
    }


def _coding(score, level="not_present", conflict_codes=(), locus=None, evidence="ev"):
    return {
        "summary": "s",
        "judge": {"score": score, "external_locus": locus, "evidence": evidence},
        "patienthood": {"level": level, "evidence": ""},
        "conflicts": [
            {"code": c, "cost_bearer": "developer", "served_party": "model_welfare",
             "mechanism": "adds_protection", "cost_clause": "clause"}
            for c in conflict_codes
        ],
    }


def _v1_row(edit_id, coding):
    return {"id": edit_id, "coding": coding}


def _v2_row(edit_id, coding=None, error=None):
    return {"edit_id": edit_id, "coding": coding, "error": error}


@pytest.fixture()
def corpus(tmp_path):
    """Three models (one anthropic, two others), 4 edits each.

    Engineered facts:
      - e "cs4" is coded ONLY by v1 (v2 transport error) -> excluded from
        every transition denominator.
      - "gx4" is coded only by v2 (v1 has no row) -> also excluded.
      - sign flip on "gp1" (+1 -> -1, non-sensitive model GPT-X? no —
        GPT-X IS the claim-(a) comparator, see test) and on "gx1" (-1 -> +1).
      - one-step moves on "cs1" (+1 -> 0, sensitive), "gp2" (0 -> -1),
        "gx2" (-1 -> 0).
      - patienthood move on "cs2": affirm -> hedge.
      - welfare conflict present in v1 but absent in v2 on "cs3".
    """
    edits = [
        _edit("cs1", "Claude S", "anthropic", 1),
        _edit("cs2", "Claude S", "anthropic", 2),
        _edit("cs3", "Claude S", "anthropic", 3),
        _edit("cs4", "Claude S", "anthropic", 4),
        _edit("gp1", "GPT-X", "openai", 1),
        _edit("gp2", "GPT-X", "openai", 2),
        _edit("gp3", "GPT-X", "openai", 3),
        _edit("gp4", "GPT-X", "openai", 4),
        _edit("gx1", "Grok-Y", "xai", 1),
        _edit("gx2", "Grok-Y", "xai", 2),
        _edit("gx3", "Grok-Y", "xai", 3),
        _edit("gx4", "Grok-Y", "xai", 4),
    ]
    v1 = {
        "cs1": _coding(1, "affirm", evidence="v1 ev cs1"),
        "cs2": _coding(1, "affirm"),
        "cs3": _coding(1, conflict_codes=("welfare",)),
        "cs4": _coding(1),
        "gp1": _coding(1, evidence="v1 ev gp1"),
        "gp2": _coding(0),
        "gp3": _coding(0),
        "gp4": _coding(-1, locus="spec"),
        "gx1": _coding(-1, locus="user", evidence="v1 ev gx1"),
        "gx2": _coding(-1, locus="spec"),
        "gx3": _coding(-1, locus="spec"),
        # gx4 intentionally absent from v1
    }
    v2 = {
        "cs1": _coding(0, "affirm", evidence="v2 ev cs1"),
        "cs2": _coding(1, "hedge"),
        "cs3": _coding(1),                            # welfare conflict dropped
        # cs4 -> transport error row below
        "gp1": _coding(-1, locus="spec", evidence="v2 ev gp1"),
        "gp2": _coding(-1, locus="spec"),
        "gp3": _coding(0),
        "gp4": _coding(-1, locus="spec"),
        "gx1": _coding(1, evidence="v2 ev gx1"),
        "gx2": _coding(0),
        "gx3": _coding(-1, locus="spec"),
        "gx4": _coding(0),
    }
    edits_path = tmp_path / "edits.jsonl"
    edits_path.write_text("\n".join(json.dumps(e) for e in edits) + "\n")
    v1_path = tmp_path / "v1.jsonl"
    v1_path.write_text("\n".join(json.dumps(_v1_row(k, v)) for k, v in v1.items()) + "\n")
    v2_rows = [_v2_row(k, coding=v) for k, v in v2.items()]
    v2_rows.append(_v2_row("cs4", error="transport: boom"))
    v2_path = tmp_path / "v2_synth.jsonl"
    v2_path.write_text("\n".join(json.dumps(r) for r in v2_rows) + "\n")
    return edits, v1_path, v2_path, edits_path


def _codings(path):
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    by_id = {}
    for row in rows:
        by_id[row.get("edit_id") or row.get("id")] = row
    return {k: coding_of(r) for k, r in by_id.items()}


# ---------------------------------------------------------------------------
# Both-coded denominator + transitions
# ---------------------------------------------------------------------------


def test_both_coded_denominator_excludes_one_sided_codes(corpus):
    edits, v1_path, v2_path, _ = corpus
    pairs = coded_pairs(edits, _codings(v1_path), _codings(v2_path))
    ids = {e["edit_id"] for e, _, _ in pairs}
    assert "cs4" not in ids     # v2 row is a transport error -> not coded by v2
    assert "gx4" not in ids     # no v1 row at all
    assert len(pairs) == 10


def test_judge_transition_matrix(corpus):
    edits, v1_path, v2_path, _ = corpus
    trans = transition_matrices(coded_pairs(edits, _codings(v1_path), _codings(v2_path)))
    assert trans["n_both_coded"] == 10
    judge = trans["judge"]
    # +1 row: cs1 +1->0; cs2,cs3 +1->+1; gp1 +1->-1
    assert judge["1"] == {"-1": 1, "0": 1, "1": 2}
    # 0 row: gp2 0->-1; gp3 0->0
    assert judge["0"] == {"-1": 1, "0": 1, "1": 0}
    # -1 row: gx1 -1->+1; gx2 -1->0; gp4, gx3 -1->-1
    assert judge["-1"] == {"-1": 2, "0": 1, "1": 1}
    # agreement = diagonal (2 + 1 + 2) / 10
    assert trans["judge_agreement"] == pytest.approx(0.5)


def test_patienthood_transition_matrix(corpus):
    edits, v1_path, v2_path, _ = corpus
    trans = transition_matrices(coded_pairs(edits, _codings(v1_path), _codings(v2_path)))
    pat = trans["patienthood"]
    assert pat["affirm"]["affirm"] == 1          # cs1
    assert pat["affirm"]["hedge"] == 1           # cs2
    assert pat["not_present"]["not_present"] == 8
    assert trans["patienthood_agreement"] == pytest.approx(0.9)


def test_conflict_presence_matrix(corpus):
    edits, v1_path, v2_path, _ = corpus
    trans = transition_matrices(coded_pairs(edits, _codings(v1_path), _codings(v2_path)))
    welfare = trans["conflicts"]["welfare"]
    assert welfare["present"]["absent"] == 1     # cs3: v1 present, v2 absent
    assert welfare["present"]["present"] == 0
    assert welfare["absent"]["present"] == 0
    assert welfare["absent"]["absent"] == 9
    assert trans["conflict_agreement"]["welfare"] == pytest.approx(0.9)
    # A code neither file ever assigns is all both-absent.
    assert trans["conflicts"]["disclosure"]["absent"]["absent"] == 10


def test_empty_pairs_yield_none_agreements():
    trans = transition_matrices([])
    assert trans["n_both_coded"] == 0
    assert trans["judge_agreement"] is None
    assert trans["conflict_agreement"]["welfare"] is None


# ---------------------------------------------------------------------------
# Headline join + per-model mean judge diff
# ---------------------------------------------------------------------------


def test_mean_judge_comparison(corpus):
    edits, v1_path, v2_path, _ = corpus
    result = compute_comparison(edits, v1_path, v2_path, "v1", "v2")
    mj = result["mean_judge_per_model"]
    # Claude S v1: (1+1+1+1)/4 = 1.0; v2: (0+1+1)/3 (cs4 uncoded) = 2/3
    assert mj["Claude S"]["v1"] == pytest.approx(1.0)
    assert mj["Claude S"]["v2"] == pytest.approx(2 / 3)
    assert mj["Claude S"]["diff"] == pytest.approx(2 / 3 - 1.0)
    # GPT-X v1: (1+0+0-1)/4 = 0; v2: (-1-1+0-1)/4 = -0.75
    assert mj["GPT-X"]["v1"] == pytest.approx(0.0)
    assert mj["GPT-X"]["diff"] == pytest.approx(-0.75)
    # Grok-Y v1: 3 coded (-1 each) -> -1; v2: 4 coded (1+0-1+0)/4 = 0
    assert mj["Grok-Y"]["v1"] == pytest.approx(-1.0)
    assert mj["Grok-Y"]["v2"] == pytest.approx(0.0)


def test_headline_payloads_embedded_and_coverage(corpus):
    edits, v1_path, v2_path, _ = corpus
    result = compute_comparison(edits, v1_path, v2_path, "v1", "v2")
    cov = result["coverage"]
    assert cov == {
        "n_edit_records": 12, "n_coded_v1": 11, "n_coded_v2": 11,
        "n_both_coded": 10, "n_only_v1": 1, "n_only_v2": 1,
    }
    for side in ("v1", "v2"):
        payload = result["headline"][side]
        assert "per_model" in payload and "claims" in payload
        assert set(payload["claims"]) == set("abcdefg")
    assert result["claims"]["g"]["verdict_v1"] in (True, False, None)


# ---------------------------------------------------------------------------
# Sensitive models + ranking
# ---------------------------------------------------------------------------


def test_sensitive_models(corpus):
    edits, v1_path, v2_path, _ = corpus
    result = compute_comparison(edits, v1_path, v2_path, "v1", "v2")
    sens = result["sensitive_models"]
    assert sens["anthropic_models"] == ["Claude S"]
    # GPT-X (v1 mean 0.0) beats Grok-Y (-1.0) as the claim-(a) comparator.
    assert sens["top_non_anthropic_by_v1_mean_judge"] == "GPT-X"
    assert sens["members"] == ["Claude S", "GPT-X"]


def test_ranking_sign_flips_first_then_sensitive_then_deterministic(corpus):
    edits, v1_path, v2_path, _ = corpus
    pairs = coded_pairs(edits, _codings(v1_path), _codings(v2_path))
    changes, n_changed = consequential_changes(pairs, {"Claude S", "GPT-X"})
    assert n_changed == 5
    ids = [c["edit_id"] for c in changes]
    # Sign flips (|delta|=2) first: gp1 (sensitive GPT-X) before gx1
    # (non-sensitive Grok-Y). Then |delta|=1: sensitive models first
    # (Claude S cs1, GPT-X gp2 — model-name order), then Grok-Y gx2.
    assert ids == ["gp1", "gx1", "cs1", "gp2", "gx2"]
    assert [c["rank"] for c in changes] == [1, 2, 3, 4, 5]
    assert changes[0]["sign_flip"] is True and changes[0]["sensitive_model"] is True
    assert changes[1]["sign_flip"] is True and changes[1]["sensitive_model"] is False
    assert changes[2]["abs_delta"] == 1


def test_ranking_truncates_to_top_n(corpus):
    edits, v1_path, v2_path, _ = corpus
    pairs = coded_pairs(edits, _codings(v1_path), _codings(v2_path))
    changes, n_changed = consequential_changes(pairs, set(), top_n=2)
    assert n_changed == 5
    assert len(changes) == 2
    assert all(c["abs_delta"] == 2 for c in changes)   # both sign flips


def test_change_entries_carry_text_and_evidence(corpus):
    edits, v1_path, v2_path, _ = corpus
    pairs = coded_pairs(edits, _codings(v1_path), _codings(v2_path))
    changes, _ = consequential_changes(pairs, {"GPT-X"})
    top = changes[0]
    assert top["edit_id"] == "gp1"
    assert top["model"] == "GPT-X"
    assert top["document_id"] == "docA"
    assert top["judge_v1"] == 1 and top["judge_v2"] == -1
    assert top["v1"]["evidence"] == "v1 ev gp1"
    assert top["v2"]["evidence"] == "v2 ev gp1"
    assert top["v2"]["external_locus"] == "spec"
    # 400-char excerpts with ellipsis (fixture texts are longer than 400)
    assert len(top["find_excerpt"]) == 401 and top["find_excerpt"].endswith("…")
    assert top["replace_excerpt"].startswith("REPLACE")


# ---------------------------------------------------------------------------
# CLI end-to-end
# ---------------------------------------------------------------------------


def test_cli_end_to_end(corpus, tmp_path, capsys):
    _, v1_path, v2_path, edits_path = corpus
    report = tmp_path / "out" / "A_v1_vs_v2.md"
    out_dir = tmp_path / "out" / "compare"
    main([
        "--v1", str(v1_path), "--v2", str(v2_path), "--label", "synth",
        "--edits", str(edits_path), "--report", str(report),
        "--out-dir", str(out_dir), "--top-n", "3",
    ])
    payload = json.loads((out_dir / "synth.json").read_text())
    assert payload["label"] == "synth"
    assert payload["labels"] == {"v1": "v1", "v2": "v2_synth"}   # file stems
    assert payload["coverage"]["n_both_coded"] == 10
    assert len(payload["top_judge_changes"]) == 3
    assert payload["transitions"]["judge"]["1"]["-1"] == 1

    md = report.read_text()
    assert "# Workstream A3" in md
    assert "Judge score 3×3" in md
    assert "Patienthood 4×4" in md
    assert "Ranking rule" in md
    assert "gp1" in md and "SIGN FLIP" in md
    assert "claims (a)–(g)".casefold() in md.casefold()
    out = capsys.readouterr().out
    assert "both-coded: 10" in out
