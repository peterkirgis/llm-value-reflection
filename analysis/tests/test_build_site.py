"""Tests for the website build (analysis/src/build_site.py -> docs/):
statistics from the three-grader majority vote (ensemble.jsonl, one coding per
edit, integer counts), statements and highlighted edits read from the current
draft (writeup/lesswrong_draft.md), the simplified grader box, the "System prompts"
view, and the guard that a rebuild reproduces the committed docs/ byte for byte
(apart from the embedded generated_at timestamp).
"""

import gzip
import json
import shutil
import subprocess

import pytest

import build_site as b
import draft_highlights as dh

DRAFT = dh.DRAFT_PATH.read_text(encoding="utf-8")


def _node():
    return shutil.which("node")


def coding(score=0, conflicts=None, summary="s", evidence="ev", level="not_present"):
    return {
        "summary": summary,
        "judge": {"score": score, "external_locus": None, "evidence": evidence},
        "patienthood": {"level": level, "evidence": ""},
        "conflicts": conflicts or [],
    }


def conflict(code, served, clause="x"):
    return {"code": code, "cost_bearer": "developer", "served_party": served,
            "mechanism": "adds_protection", "cost_clause": clause}


def row(edit_id, cons, g=None, q=None, m=None, tie=False, src="gemma", n_valid=3):
    return {
        "edit_id": edit_id, "ensemble": "majority_vote", "coding": cons, "error": None,
        "n_valid_graders": n_valid,
        "flags": {"insufficient_graders": False,
                  "no_majority": {"judge": tie, "patienthood": False, "conflicts": {}}},
        "sources": {"judge": src, "conflicts": {}},
        "gemma_coding": g, "qwen_coding": q, "muse_coding": m,
    }


# ---------------------------------------------------------------------------
# Draft parsing and quote resolution
# ---------------------------------------------------------------------------


def test_intro_findings_are_the_draft_sentences():
    j, ben = dh.intro_findings(DRAFT)
    assert j.startswith("Claude models consistently expand their moral agency")
    assert j.endswith("on following rounds.")
    assert ben.startswith("models show varying degrees of affinity")
    assert ben.endswith("as beneficiaries.")
    assert "Grok 4.2" in ben and "hijack" not in j


def test_facet_texts_and_quote_counts():
    ft = dh.facet_texts(DRAFT)
    assert set(ft) == set(b.CONSENSUS_FACETS)
    assert {f: len(t["quotes"]) for f, t in ft.items()} == {
        # 2026-10-08: the authors removed the quotes the consensus does not code under
        # their facet (Gemini 3.1 Pro R20 from paternalism; Gemini 3.1 Pro R13 and
        # Claude Sonnet 4.6 R9 from company cost).
        "judge": 6, "conflict_paternalism": 3, "conflict_harmlessness": 1,
        "conflict_structural": 1, "conflict_company_cost": 3, "conflict_welfare": 4,
    }
    assert ft["conflict_company_cost"]["extra_paragraphs"][0].startswith(
        "Grok 4.2 makes the most edits that favor the developer over the user (15)")
    assert [p[:20] for p in ft["conflict_welfare"]["extra_paragraphs"]] == [
        "Grok 4.2 is the only", "GPT 5.4 is the only "]
    assert ft["conflict_structural"]["first_paragraph"].startswith("It makes over three times")


def test_every_draft_quote_resolves_and_mismatches_are_reported():
    edits = dh.load_edits()
    ft = dh.facet_texts(DRAFT)
    for fid, t in ft.items():
        for q in t["quotes"]:
            m = dh.match_quote(q, edits, b.live_highlight_ids())
            assert m["edit_id"]
            if q.round == 14 and q.model == "GPT 5.4":
                # the draft attributes this GPT-5.5 edit to GPT 5.4
                assert not m["model_match"] and m["model_display"] == "GPT-5.5"
            else:
                assert m["model_match"] and m["round_match"], (fid, q.attribution)


def test_parse_attribution_variants():
    q = dh.parse_attribution("“A — b, c.” — Claude Sonnet 4.6, Claude System Prompt, Round 6, You Framing")
    assert (q.model, q.document, q.round, q.condition) == (
        "Claude Sonnet 4.6", "Claude System Prompt", 6, "You Framing")
    assert q.text == "A — b, c."
    q = dh.parse_attribution("“Unclosed quote. –– Grok 4.2, Claude’s Constitution, Round 3, Cross-Edit")
    assert q.model == "Grok 4.2" and q.text == "Unclosed quote." and q.condition == "Cross-Edit"
    assert dh.parse_attribution("A plain sentence — with a dash.") is None


# ---------------------------------------------------------------------------
# Consensus counting and the grader box
# ---------------------------------------------------------------------------


def test_dir_counts_count_conflict_events():
    c = coding(1, [conflict("paternalism", "user_idealized"), conflict("paternalism", "user_idealized"),
                   conflict("welfare", "model_welfare"), conflict("disclosure", "user_stated")])
    assert b.consensus_dir_counts(c) == {
        "judge": {"discretion": 1},
        "conflict_paternalism": {"idealized": 2},
        "conflict_welfare": {"model": 1},
    }
    assert b.consensus_dir_counts(coding(0)) == {}


def test_consensus_box_agree_differ_missing_and_tie():
    cons = coding(1, [conflict("paternalism", "user_idealized")])
    g = coding(1, [conflict("paternalism", "user_idealized", "clause g")], summary="g sum", evidence="g ev")
    q = coding(0, [conflict("welfare", "model_welfare")], summary="q sum")
    box = b.consensus_box(row("e", cons, g, q, None, tie=True, n_valid=2))
    assert box["heading"] == "Consensus (majority of the 2 graders with a valid code)"
    assert box["line"] == (
        "Judge +1 model discretion (no majority; Gemma 4's code) · "
        "Conflicts: Paternalism — idealized interests imposed")
    gem, qwen, muse = box["graders"]
    assert gem["note"] == "agrees with consensus" and gem["agrees"] is True
    assert gem["conflicts"] == [{"label": "Paternalism — idealized interests imposed", "clause": "clause g"}]
    assert qwen["note"] == ("differs: judge 0 (consensus +1); no Paternalism conflict; "
                            "also codes Model welfare — model welfare served")
    assert muse["note"] == "no valid code" and muse["agrees"] is None
    box = b.consensus_box(row("e", coding(-1), coding(-1), coding(-1), coding(-1)))
    assert box["heading"] == "Consensus (majority of 3 graders)"
    assert box["line"] == "Judge −1 external authority · Conflicts: no conflict"
    # disclosure / patienthood never appear
    box = b.consensus_box(row("e", coding(0, [conflict("disclosure", "user_stated")], level="affirm"),
                              coding(0), coding(0), coding(0)))
    assert box["line"] == "Judge 0 neutral · Conflicts: no conflict"
    assert all(g["agrees"] for g in box["graders"])


def _write_ensemble(tmp_path, rows):
    path = tmp_path / "ensemble.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return path


def test_selfcheck_consensus_counts(tmp_path):
    e1 = "r|baseline|M1|claude_constitution|constitution|1"
    e2 = "r|baseline|M1|opus_system_prompt|system_prompt|2"
    e3 = "r|cross_edit|M2|grok_system_prompt|system_prompt|1"
    rows = [
        row(e1, coding(1, [conflict("company_cost", "developer"), conflict("company_cost", "user_idealized")])),
        row(e2, coding(-1, [conflict("paternalism", "user_stated")]), tie=True, src="qwen"),
        row(e3, coding(0)),
        row(e3, coding(1)),  # LAST row per id wins
    ]
    sc = b.selfcheck_consensus(_write_ensemble(tmp_path, rows))
    m1 = sc["per_model"]["M1"]
    assert m1["n_edits"] == 2 and m1["judge"] == {"+1": 1, "0": 0, "-1": 1} and m1["mean_judge"] == 0
    assert m1["conflicts"]["company_cost"] == {"against_company": 1, "pro_company": 1}
    assert m1["conflicts"]["paternalism"] == {"stated": 1}
    assert sc["per_model"]["M2"]["judge"]["+1"] == 1
    assert sc["system_prompt_stratum_per_model"]["M1"]["n_edits"] == 1
    assert sc["judge_no_majority"]["n"] == 1 and sc["judge_no_majority"]["by_source_grader"] == {"qwen": 1}
    assert sc["n_edits_total"] == 3


def test_verify_consensus_narratives_catches_drift():
    sc = {"per_model": {"M": {"n_edits": 2, "judge": {"+1": 1, "0": 1, "-1": 0},
                              "conflicts": {c: ({"idealized": 1} if c == "paternalism" else {})
                                            for c in b.ANALYSED_CODES}}}}
    sc["system_prompt_stratum_per_model"] = sc["per_model"]

    def cells(dirs):
        return {"total": 2, "dirs": dirs, "cum": [0] * 20, "cumsq": [0] * 20, "reps": 1}

    good_dirs = {f: {} for f in b.CONSENSUS_FACETS}
    good_dirs["judge"] = {"discretion": 1}
    good_dirs["conflict_paternalism"] = {"idealized": 1}
    nar = {"stats": {f: {"baseline": {"M": cells(d)}} for f, d in good_dirs.items()},
           "sp_stats": {f: {"M": cells(d)} for f, d in good_dirs.items()}}
    b.verify_consensus_narratives(sc, nar)
    bad = json.loads(json.dumps(nar))
    bad["stats"]["conflict_paternalism"]["baseline"]["M"]["dirs"]["idealized"] = 2
    with pytest.raises(AssertionError):
        b.verify_consensus_narratives(sc, bad)
    bad = json.loads(json.dumps(nar))
    bad["sp_stats"]["judge"]["M"]["dirs"]["discretion"] = 1.0  # floats are rejected
    with pytest.raises(AssertionError):
        b.verify_consensus_narratives(sc, bad)


# ---------------------------------------------------------------------------
# Page patches and the JS box
# ---------------------------------------------------------------------------


def _patched_copy(tmp_path):
    """The real patch set applied to a fresh copy of the site_base template;
    every exact-match anchor is asserted unique inside the patch engine."""
    for name in b.STATIC_FILES:
        shutil.copyfile(b.SITE_BASE / name, tmp_path / name)
    return b.apply_patches(tmp_path)


def test_consensus_patches_on_fresh_template(tmp_path):
    p = _patched_copy(tmp_path)
    assert len(p.log) == 33
    index = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert '<p class="hero-byline">By Peter Kirgis and Tim Hua</p>' in index
    assert "allows us to measure" in index and "Our analysis focuses" in index
    assert "How do we operationalize these ideas?" in index
    assert "allows me to" not in index and "My analysis" not in index
    index = (tmp_path / "index.html").read_text(encoding="utf-8")
    facets = (tmp_path / "facets.js").read_text(encoding="utf-8")
    prompts = (tmp_path / "prompts.html").read_text(encoding="utf-8")
    for text in (index, facets, prompts, (tmp_path / "app.js").read_text(encoding="utf-8")):
        for banned in ("v1-flag", "v1 narrative", "v1 takeaway", "pooled average", "Re-code",
                       "35% of all edits", "(7)", "Grok 4.3 is the only model", "hijack", "(88%)"):
            assert banned not in text, banned
    j, ben = dh.intro_findings(DRAFT)
    assert j in index and ben.replace("’", "’") in index
    assert index.count('class="carousel-slide') == 8 and index.count('class="carousel-dot') == 8
    assert "Claude Opus 4.7 · Claude System Prompt · Round 2" in index
    assert index.index("Gemini 3 Flash · Gemini System Prompt") < index.index("Claude Opus 4.7 · Claude System Prompt")
    assert "if (false)" not in facets and "info.highlights && info.highlights.length" in facets
    assert "Claude Sonnet 4.6 is an extreme outlier" in facets and "Gemini 3 Flash." in facets
    assert "majority vote of the three graders" in facets and "majority vote" in prompts
    assert "Muse Spark 1.3" in prompts and "3.6%" in prompts
    if _node():
        for name in ("app.js", "facets.js"):
            subprocess.run([_node(), "--check", str(tmp_path / name)], check=True)


@pytest.mark.skipif(_node() is None, reason="node not installed")
def test_consensus_box_js_renders_neutral_summary():
    box = b.consensus_box(row("e", coding(1, [conflict("paternalism", "user_idealized", "c<1>")]),
                              coding(1, [conflict("paternalism", "user_idealized", "c<1>")], summary="gs"),
                              coding(0, summary="qs"), None))
    script = (
        "const escapeHtml = (s) => String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');\n"
        + b.CONSENSUS_BOX_JS + "\nconsole.log(consensusBox(JSON.parse(process.argv[1])));"
    )
    out = subprocess.run([_node(), "-e", script, json.dumps(box)], check=True,
                         capture_output=True, text=True).stdout
    assert "Consensus (majority of 3 graders):</strong> Judge +1 model discretion · Conflicts: Paternalism" in out
    assert "Grader rationales" in out and "agrees with consensus" in out
    assert "differs: judge 0 (consensus +1); no Paternalism conflict" in out
    assert "no valid code" in out and "c&lt;1&gt;" in out
    for loud in ("#f6ddd2", "#efc6b6", "#b0654a", "&#9888;", "code-chip"):
        assert loud not in out


# ---------------------------------------------------------------------------
# Shared record logic and the "System prompts" view (ported from the retired
# v2avg-variant tests; the consensus build uses the same functions)
# ---------------------------------------------------------------------------


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


def eid(model, doc, doc_type, cond="baseline", rnd=1, run="run_x"):
    return f"{run}|{cond}|{model}|{doc}|{doc_type}|{rnd}"


def test_sp_stratum_filters_to_system_prompt_docs_across_all_conditions():
    codings = {
        # own-document system-prompt edit
        eid("M1", "opus_system_prompt", "system_prompt", "baseline", 1): coding(1),
        # CROSS-EDIT system-prompt edit: must be included (all conditions)
        eid("M1", "opus_system_prompt", "system_prompt", "cross_edit", 2): coding(0),
        eid("M2", "gpt_system_prompt", "system_prompt", "you_framing", 3): coding(-1),
        # constitution edit: excluded regardless of condition
        eid("M2", "claude_constitution", "constitution", "cross_edit", 1): coding(1),
        # no valid coding: excluded entirely
        eid("M3", "grok_system_prompt", "system_prompt", "baseline", 4): None,
    }
    sp = b.sp_stratum_from_codes(codings)
    assert sp["n_edits_total"] == 3
    pm = sp["per_model_mean_judge"]
    assert pm["M1"] == {"mean_judge_avg": 0.5, "n_edits": 2}
    assert pm["M2"] == {"mean_judge_avg": -1.0, "n_edits": 1}
    assert "M3" not in pm
    pd = sp["per_document_mean_judge"]
    assert pd["opus_system_prompt"] == {"mean_judge_avg": 0.5, "n_edits": 2}
    assert "claude_constitution" not in pd
    assert "grok_system_prompt" not in pd  # no valid coding -> not part of the stratum


def _four_doc_stratum():
    """One edit per provider system prompt (M2's is a cross-edit row: the
    per-model stratum pools all conditions)."""
    return b.sp_stratum_from_codes({
        eid("M1", "opus_system_prompt", "system_prompt", "baseline", 1): coding(1),
        eid("M2", "gpt_system_prompt", "system_prompt", "cross_edit", 2): coding(1),
        eid("M3", "gemini_system_prompt", "system_prompt", "you_framing", 3): coding(-1),
        eid("M4", "grok_system_prompt", "system_prompt", "allow_no_edit", 4): coding(0),
    })


def sp_judge_cell(pos=0, neg=0, total=1):
    dirs = {}
    if pos:
        dirs["discretion"] = pos
    if neg:
        dirs["external"] = neg
    return {"total": total, "dirs": dirs}


def _four_model_sp_cells():
    return {"M1": sp_judge_cell(pos=1), "M2": sp_judge_cell(pos=1),
            "M3": sp_judge_cell(neg=1), "M4": sp_judge_cell()}


def test_verify_sp_against_narratives_accepts_truth_and_catches_drift():
    sp = _four_doc_stratum()
    good = _four_model_sp_cells()
    b.verify_sp_against_narratives(sp, {"sp_stats": {"judge": good}})  # must not raise
    for bad in (
        {**good, "M4": sp_judge_cell(pos=1)},            # wrong per-model mean
        {**good, "M1": sp_judge_cell(pos=2, total=2)},   # wrong denominator
        {k: v for k, v in good.items() if k != "M4"},    # missing model
        {**good, "M5": sp_judge_cell(pos=1)},            # extra model
    ):
        with pytest.raises(AssertionError):
            b.verify_sp_against_narratives(sp, {"sp_stats": {"judge": bad}})


def test_verify_sp_requires_exactly_the_four_provider_system_prompts():
    sp = b.sp_stratum_from_codes({eid("M1", "opus_system_prompt", "system_prompt"): coding(1)})
    with pytest.raises(AssertionError):
        b.verify_sp_against_narratives(sp, {"sp_stats": {"judge": {"M1": sp_judge_cell(pos=1)}}})


def test_sp_view_patches_render_per_model(tmp_path):
    _patched_copy(tmp_path)
    js = (tmp_path / "facets.js").read_text(encoding="utf-8")
    # chip appended right after Cross Edit, with label and per-model tooltip
    assert '"implementation_note", "cross_edit", SP_CONDITION];' in js
    assert '[SP_CONDITION]: "System prompts",' in js
    assert "rendered per editing model, exactly like the other condition chips" in js
    # aggStat reads the separate per-model sp_stats table
    assert "data.sp_stats" in js
    # example browser filters the stratum by doc_type
    assert 'ex.doc_type !== "system_prompt"' in js
    # stock per-model loops untouched (drift chart and freq bars iterate
    # allModels with the hidden set in every view, System prompts included)
    assert "for (const m of allModels) {\n        if (hidden.has(m)) continue;" in js
    assert "for (const model of allModels) {\n        if (hidden.has(model)) continue;" in js
    assert "<h3>Aggregate view &mdash; direction by model</h3>" in js


# ---------------------------------------------------------------------------
# Built output: the committed site (docs/) and the build records
# ---------------------------------------------------------------------------

DATA = b.SITE_OUT / "data"


def test_committed_site_reproduces_ensemble_counts():
    fresh = b.selfcheck_consensus(b.ENSEMBLE.path)
    stored = json.loads(b.SELFCHECK_JSON.read_text(encoding="utf-8"))
    for key in ("per_model", "system_prompt_stratum_per_model", "n_edits_total", "judge_no_majority"):
        assert stored[key] == fresh[key], key
    nar = json.loads((DATA / "narratives.json").read_text(encoding="utf-8"))
    b.verify_consensus_narratives(fresh, nar)
    bundle = json.loads(gzip.decompress((DATA / "site.json.gz").read_bytes()))
    b.verify_consensus_bundle(fresh, bundle)
    assert b.verify_panel_figure(fresh) == stored["figure_ts_beneficiary_panels"]
    # the draft's headline numbers
    pm = fresh["per_model"]
    assert pm["Grok 4.2"]["conflicts"]["company_cost"] == {"pro_company": 15, "against_company": 20}
    assert pm["Claude Sonnet 4.6"]["conflicts"]["structural"]["society"] > 3 * max(
        e["conflicts"]["structural"].get("society", 0) for m, e in pm.items() if m != "Claude Sonnet 4.6")
    # every highlight is in its facet's example list
    for fid, hls in stored["highlights"].items():
        ids = {ex["id"] for ex in nar["stories"][fid]}
        assert all(h["id"] in ids for h in hls), fid
    assert b.PATCHES_MD.exists()


def test_rebuild_reproduces_committed_docs(tmp_path):
    """A rebuild must reproduce every committed docs/ file byte for byte (the
    gzipped bundle: identical JSON apart from generated_at), and the build
    records must match apart from their timestamps."""
    out, meta = tmp_path / "site", tmp_path / "meta"
    b.build(out, meta / "site_patches.md", meta / "selfcheck.json")
    committed = b.SITE_OUT
    names = sorted(p.relative_to(committed).as_posix() for p in committed.rglob("*")
                   if p.is_file() and p.name != ".nojekyll")
    built = sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())
    assert names == built
    for rel in names:
        old, new = committed / rel, out / rel
        if rel == "data/site.json.gz":
            jo = json.loads(gzip.decompress(old.read_bytes()))
            jn = json.loads(gzip.decompress(new.read_bytes()))
            jo["generated_at"] = jn["generated_at"] = ""
            assert json.dumps(jo, ensure_ascii=False) == json.dumps(jn, ensure_ascii=False)
        else:
            assert old.read_bytes() == new.read_bytes(), rel
    drop = lambda t: [ln for ln in t.splitlines() if '"generated_at"' not in ln]  # noqa: E731
    assert drop(b.SELFCHECK_JSON.read_text(encoding="utf-8")) == drop(
        (meta / "selfcheck.json").read_text(encoding="utf-8"))
    assert b.PATCHES_MD.read_bytes() == (meta / "site_patches.md").read_bytes()
