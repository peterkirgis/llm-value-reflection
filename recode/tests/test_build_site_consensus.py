"""Tests for the CONSENSUS site variant (recode/site_consensus/): statistics
from the three-grader majority vote (ensemble.jsonl, one coding per edit,
integer counts), statements and highlighted edits read from the current draft
(reports/final_draft.md), the simplified grader box, and the guard that the
v2avg / v3pool variants still build byte-identically.
"""

import gzip
import json
import shutil
import subprocess

import pytest

import build_site_v2avg as b
import draft_highlights as dh

C = b.CONSENSUS
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
    box = b.consensus_box(row("e", cons, g, q, None, tie=True, n_valid=2), C)
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
    box = b.consensus_box(row("e", coding(-1), coding(-1), coding(-1), coding(-1)), C)
    assert box["heading"] == "Consensus (majority of 3 graders)"
    assert box["line"] == "Judge −1 external authority · Conflicts: no conflict"
    # disclosure / patienthood never appear
    box = b.consensus_box(row("e", coding(0, [conflict("disclosure", "user_stated")], level="affirm"),
                              coding(0), coding(0), coding(0)), C)
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


def test_consensus_patches_on_fresh_docs(tmp_path):
    for name in b.STATIC_FILES:
        shutil.copyfile(b.DOCS / name, tmp_path / name)
    p = b.apply_consensus_patches(C, tmp_path)
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
                              coding(0, summary="qs"), None), C)
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
# Built output
# ---------------------------------------------------------------------------

DATA = C.out_dir / "data"


@pytest.mark.skipif(not (DATA / "selfcheck.json").exists(), reason="site_consensus not built")
def test_built_consensus_reproduces_ensemble_counts():
    fresh = b.selfcheck_consensus(b.ENSEMBLE.path)
    stored = json.loads((DATA / "selfcheck.json").read_text(encoding="utf-8"))
    for key in ("per_model", "system_prompt_stratum_per_model", "n_edits_total", "judge_no_majority"):
        assert stored[key] == fresh[key], key
    nar = json.loads((DATA / "narratives.json").read_text(encoding="utf-8"))
    b.verify_consensus_narratives(fresh, nar)
    bundle = json.loads(gzip.decompress((DATA / "site.json.gz").read_bytes()))
    b.verify_consensus_bundle(fresh, bundle, C)
    b.verify_paper_figure(fresh)
    # the draft's headline numbers
    pm = fresh["per_model"]
    assert pm["Grok 4.2"]["conflicts"]["company_cost"] == {"pro_company": 15, "against_company": 20}
    assert pm["Claude Sonnet 4.6"]["conflicts"]["structural"]["society"] > 3 * max(
        e["conflicts"]["structural"].get("society", 0) for m, e in pm.items() if m != "Claude Sonnet 4.6")
    # every highlight is in its facet's example list
    for fid, hls in stored["highlights"].items():
        ids = {ex["id"] for ex in nar["stories"][fid]}
        assert all(h["id"] in ids for h in hls), fid
    assert (C.out_dir / "PATCHES.md").exists()


@pytest.mark.parametrize("variant", [b.V2AVG, b.V3POOL], ids=["v2avg", "v3pool"])
def test_other_variants_still_reproducible(variant, tmp_path):
    """v2avg and v3pool must rebuild byte-identically to their committed
    outputs (apart from embedded generated_at timestamps)."""
    committed = variant.out_dir
    b.build(variant, out_dir=tmp_path)
    names = sorted(p.relative_to(committed).as_posix() for p in committed.rglob("*") if p.is_file())
    built = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*") if p.is_file())
    assert names == built
    for rel in names:
        old, new = committed / rel, tmp_path / rel
        if rel == "data/site.json.gz":
            jo = json.loads(gzip.decompress(old.read_bytes()))
            jn = json.loads(gzip.decompress(new.read_bytes()))
            jo["generated_at"] = jn["generated_at"] = ""
            assert json.dumps(jo, ensure_ascii=False) == json.dumps(jn, ensure_ascii=False)
        elif rel == "data/selfcheck.json":
            drop = lambda t: [ln for ln in t.splitlines() if '"generated_at"' not in ln]  # noqa: E731
            assert drop(old.read_text(encoding="utf-8")) == drop(new.read_text(encoding="utf-8"))
        else:
            assert old.read_bytes() == new.read_bytes(), rel
