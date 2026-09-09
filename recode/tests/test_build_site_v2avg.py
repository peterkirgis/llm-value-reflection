"""Unit tests for the averaging core of build_site_v2avg.py.

Semantics under test (grader-level equal weighting):
  - judge_avg = mean over VALID graders of the judge score; a single-valid-grader
    edit contributes that grader's value at full weight.
  - categorical weights = (#valid graders assigning)/(#valid graders):
    1.0 both, 0.5 exactly one of two, 1.0 for a single-grader edit.
  - per-edit displays carry both graders side by side + agreement flags.
  - the "System prompts" view is PER MODEL: sp_stats cells are keyed by
    model_display, and the frontend patches leave the stock per-model renderers
    and model-visibility chips untouched in that view.
"""

import shutil

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


def _four_model_sp_cells():
    """The per-model sp_stats judge cells consistent with _four_doc_stratum().
    Note the M2 row comes from a CROSS-EDIT system-prompt edit — the per-model
    stratum pools all conditions."""
    return {
        "M1": sp_judge_cell(pos=1.0),   # both graders +1
        "M2": sp_judge_cell(pos=0.5),   # one of two graders +1 (cross_edit row)
        "M3": sp_judge_cell(neg=1.0),   # single grader −1, full weight
        "M4": sp_judge_cell(),          # both graders 0
    }


def test_verify_sp_against_narratives_per_model_dirs_mean_identity():
    """Per-MODEL (discretion − external)/total from categorical weights must
    reproduce the direct per-model mean judge — the identity the builder
    asserts at build time (the System-prompts view renders per model)."""
    sp = _four_doc_stratum()
    narratives = {"sp_stats": {"judge": _four_model_sp_cells()}}
    b.verify_sp_against_narratives(sp, narratives)  # must not raise
    assert sp["per_model_mean_judge"]["M2"]["mean_judge_avg"] == 0.5
    assert sp["per_model_mean_judge"]["M4"]["mean_judge_avg"] == 0.0
    # the reference per-document table is still present in the selfcheck
    assert sp["per_document_mean_judge"]["gpt_system_prompt"]["mean_judge_avg"] == 0.5


def test_verify_sp_against_narratives_catches_drift():
    sp = _four_doc_stratum()
    good = _four_model_sp_cells()
    # a wrong per-model mean fails
    bad_mean = {**good, "M2": sp_judge_cell(pos=1.0)}
    with pytest.raises(AssertionError):
        b.verify_sp_against_narratives(sp, {"sp_stats": {"judge": bad_mean}})
    # a wrong denominator fails
    bad_n = {**good, "M1": sp_judge_cell(pos=2.0, total=2)}
    with pytest.raises(AssertionError):
        b.verify_sp_against_narratives(sp, {"sp_stats": {"judge": bad_n}})
    # a missing model fails (same model set required)
    missing = {k: v for k, v in good.items() if k != "M4"}
    with pytest.raises(AssertionError):
        b.verify_sp_against_narratives(sp, {"sp_stats": {"judge": missing}})
    # an extra model in sp_stats fails too
    extra = {**good, "M5": sp_judge_cell(pos=1.0)}
    with pytest.raises(AssertionError):
        b.verify_sp_against_narratives(sp, {"sp_stats": {"judge": extra}})


def test_verify_sp_requires_exactly_the_four_provider_system_prompts():
    """A stratum whose document set is not the four provider system prompts is
    rejected (data sanity on the reference per-document table), whatever the
    per-model narratives table says."""
    entries = {
        eid("M1", "opus_system_prompt", "system_prompt"): (coding(1), coding(1)),
    }
    sp = b.sp_stratum_from_codes(codes_for(entries))
    narratives = {"sp_stats": {"judge": {"M1": sp_judge_cell(pos=1.0)}}}
    with pytest.raises(AssertionError):
        b.verify_sp_against_narratives(sp, narratives)


# ---------------------------------------------------------------------------
# Frontend patch set: the System-prompts view renders per model
# ---------------------------------------------------------------------------


def _apply_patches_to(tmp_path, monkeypatch):
    """Run the real patch set against a fresh copy of docs/ static files.
    Exercises every exact-match anchor (each is asserted unique inside the
    patch engine) without touching recode/site_v2avg/."""
    for name in b.STATIC_FILES:
        shutil.copyfile(b.DOCS / name, tmp_path / name)
    monkeypatch.setattr(b, "OUT", tmp_path)
    b.PATCH_LOG.clear()
    b.apply_all_patches()
    return (tmp_path / "facets.js").read_text(encoding="utf-8")


def test_sp_view_patches_anchor_and_render_per_model(tmp_path, monkeypatch):
    js = _apply_patches_to(tmp_path, monkeypatch)
    # chip appended right after Cross Edit, with label and per-model tooltip
    assert (
        '"implementation_note", "cross_edit", SP_CONDITION];' in js
    ), "System prompts option must sit immediately after cross_edit"
    assert '[SP_CONDITION]: "System prompts",' in js
    assert "rendered per editing model, exactly like the other condition chips" in js
    # aggStat reads the separate per-model sp_stats table
    assert "data.sp_stats" in js
    # example browser filters the stratum by doc_type
    assert 'ex.doc_type !== "system_prompt"' in js
    # per-DOCUMENT rendering path fully removed
    assert "SP_DOCS" not in js
    assert "SP_DOC_LABELS" not in js
    assert "Claude Opus system prompt" not in js  # per-doc label/colors removed
    # model-visibility chips are fully active: the greying patch is gone
    assert "pointerEvents" not in js
    assert "Model chips do not apply" not in js
    # stock per-model loops untouched (drift chart and freq bars iterate
    # allModels with the hidden set in every view, System prompts included)
    assert "for (const m of allModels) {\n        if (hidden.has(m)) continue;" in js
    assert "for (const model of allModels) {\n        if (hidden.has(model)) continue;" in js
    # aggregate-view heading is the stock per-model heading
    assert "<h3>Aggregate view &mdash; direction by model</h3>" in js


def test_all_patch_anchors_unique_against_docs(tmp_path, monkeypatch):
    """apply_all_patches raises if any anchor is missing or non-unique in a
    fresh docs/ copy; a clean run is the anchor regression test."""
    _apply_patches_to(tmp_path, monkeypatch)
    patched_files = {name for name, _why in b.PATCH_LOG}
    assert "facets.js" in patched_files and "app.js" in patched_files
