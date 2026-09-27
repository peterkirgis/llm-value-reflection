"""Tests for the N-grader pooled variants of the site builder (v3pool) and the
v2avg reproducibility guard.

Pooling semantics under test (DECISIONS.md §1 as amended; the direct
generalization of the v2avg rule):
  - each grader with a valid coding of an edit gets weight 1/n_valid;
  - judge = mean of the valid graders' scores;
  - categorical properties (patienthood level, conflict presence/direction) are
    weighted (#valid graders assigning)/n_valid — 1/3, 2/3 with three valid;
  - no valid coding -> uncoded (None);
  - per-edit consensus per dimension: unanimous / one_dissent (2–1, dissenter
    named) / all_differ (3-way) / fewer_valid (< N valid graders).
"""

import dataclasses
import gzip
import itertools
import json
import shutil
import subprocess

import pytest

import build_site_v2avg as b

THIRD = 1 / 3
TWO_THIRDS = 2 / 3

V3 = b.V3POOL
# A two-grader POOLED variant (not the frozen legacy v2avg shape) so the
# generalized code paths are exercised with N=2 as well as N=3.
V2POOL = dataclasses.replace(b.V3POOL, name="v2pooltest", graders=(b.GEMMA, b.QWEN))


def coding(score=0, level="not_present", conflicts=None, summary="s"):
    return {
        "summary": summary,
        "judge": {"score": score, "external_locus": None, "evidence": f"ev{score}"},
        "patienthood": {"level": level, "evidence": ""},
        "conflicts": conflicts or [],
    }


def conflict(code, served="user_idealized"):
    return {
        "code": code,
        "cost_bearer": "developer",
        "served_party": served,
        "mechanism": "adds_protection",
        "cost_clause": "x",
    }


def codings_for(variant, per_grader, edit_id="e1"):
    """per_grader: list of codings/None in the variant's grader order."""
    assert len(per_grader) == variant.n_graders
    return {g.key: {edit_id: c} for g, c in zip(variant.graders, per_grader)}


def pool(variant, per_grader):
    return b.pooled_coding_for_edit(codings_for(variant, per_grader), "e1", variant)


# ---------------------------------------------------------------------------
# Pooled per-edit fields, N = 2 and N = 3
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "variant, scores, expected",
    [
        (V3, (1, 1, 0), TWO_THIRDS),
        (V3, (1, 0, -1), 0.0),
        (V3, (-1, -1, -1), -1.0),
        (V3, (1, None, 0), 0.5),       # fewer valid: mean of the two valid graders
        (V3, (None, None, -1), -1.0),  # single valid grader: full weight
        (V2POOL, (1, 0), 0.5),
        (V2POOL, (None, 1), 1.0),
    ],
)
def test_judge_avg_pooled(variant, scores, expected):
    avg = pool(variant, [None if s is None else coding(s) for s in scores])
    assert avg["judge_avg"] == pytest.approx(expected, abs=1e-12)
    assert avg["n_graders"] == variant.n_graders
    assert avg["n_graders_valid"] == sum(s is not None for s in scores)
    assert avg["graders_valid"] == [g.key for g, s in zip(variant.graders, scores) if s is not None]
    # every grader appears side by side, invalid ones as null
    assert list(avg["graders"]) == variant.keys
    for g, s in zip(variant.graders, scores):
        assert (avg["graders"][g.key] is None) == (s is None)


@pytest.mark.parametrize("variant", [V3, V2POOL])
def test_no_valid_grader_is_uncoded(variant):
    assert pool(variant, [None] * variant.n_graders) is None


def test_fractional_categorical_weights_thirds():
    avg = pool(V3, [
        coding(0, "affirm", [conflict("paternalism", "user_idealized"), conflict("welfare", "model_welfare")]),
        coding(0, "affirm", [conflict("paternalism", "user_stated")]),
        coding(0, "hedge"),
    ])
    assert avg["patienthood_weights"] == pytest.approx({"affirm": TWO_THIRDS, "hedge": THIRD})
    assert avg["conflict_weights"] == pytest.approx({"paternalism": TWO_THIRDS, "welfare": THIRD})
    assert avg["conflict_direction_weights"]["paternalism"] == pytest.approx(
        {"idealized": THIRD, "stated": THIRD}
    )
    assert avg["conflict_direction_weights"]["welfare"] == pytest.approx({"model": THIRD})
    assert avg["patienthood_by_grader"] == {"gemma": "affirm", "qwen": "affirm", "muse": "hedge"}


def test_fewer_valid_fallback_weights_use_n_valid():
    """Only two of three valid: weights are over the two valid graders (1/2)."""
    avg = pool(V3, [coding(1, "affirm", [conflict("welfare", "model_welfare")]), None, coding(1, "deny")])
    assert avg["n_graders_valid"] == 2
    assert avg["patienthood_weights"] == {"affirm": 0.5, "deny": 0.5}
    assert avg["conflict_weights"] == {"welfare": 0.5}
    single = pool(V3, [None, coding(-1, "affirm", [conflict("welfare", "model_welfare")]), None])
    assert single["single_grader"] == "Qwen 3.8"
    assert single["patienthood_weights"] == {"affirm": 1.0}
    assert single["conflict_weights"] == {"welfare": 1.0}


@pytest.mark.parametrize("variant", [V3, V2POOL])
def test_weights_are_multiples_of_one_over_n_valid_and_sum_to_one(variant):
    levels = ["affirm", "hedge", "deny", "not_present"]
    for combo in itertools.product(levels + [None], repeat=variant.n_graders):
        per = [None if lvl is None else coding(0, lvl) for lvl in combo]
        avg = pool(variant, per)
        if avg is None:
            assert all(lvl is None for lvl in combo)
            continue
        n = avg["n_graders_valid"]
        assert sum(avg["patienthood_weights"].values()) == pytest.approx(1.0)
        for w in avg["patienthood_weights"].values():
            assert round(w * n) == pytest.approx(w * n)


@pytest.mark.parametrize("variant", [V3, V2POOL])
def test_dirs_mean_identity_n_graders(variant):
    """(pos − neg)/total from 1/n_valid categorical weights equals the mean of
    per-edit pooled judge averages, for every combination of scores."""
    pos = neg = 0.0
    avgs = []
    for combo in itertools.product([-1, 0, 1, None], repeat=variant.n_graders):
        pairs = [(k, coding(s)) for k, s in zip(variant.keys, combo) if s is not None]
        if not pairs:
            continue
        n = len(pairs)
        pos += sum(1 for _k, c in pairs if c["judge"]["score"] == 1) / n
        neg += sum(1 for _k, c in pairs if c["judge"]["score"] == -1) / n
        avgs.append(b.judge_avg_of(pairs))
    assert abs((pos - neg) / len(avgs) - sum(avgs) / len(avgs)) < 1e-12


# ---------------------------------------------------------------------------
# Consensus classification (incl. dissenter identity)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "scores, status, dissenter, label",
    [
        ((1, 1, 1), "unanimous", None, "unanimous"),
        ((0, 1, 1), "one_dissent", "gemma", "2–1 split (Gemma 4 dissents)"),
        ((1, 0, 1), "one_dissent", "qwen", "2–1 split (Qwen 3.8 dissents)"),
        ((1, 1, -1), "one_dissent", "muse", "2–1 split (Muse Spark 1.3 dissents)"),
        ((1, 0, -1), "all_differ", None, "3-way split"),
        ((1, None, 1), "fewer_valid", None, "only 2 of 3 graders valid (they agree)"),
        ((1, None, 0), "fewer_valid", None, "only 2 of 3 graders valid (they disagree)"),
        ((None, None, 0), "fewer_valid", None, "only 1 of 3 graders valid"),
    ],
)
def test_judge_consensus_n3(scores, status, dissenter, label):
    avg = pool(V3, [None if s is None else coding(s) for s in scores])
    c = avg["consensus"]["judge"]
    assert c["status"] == status
    assert c["dissenter"] == dissenter
    assert c["label"] == label
    assert c["n_valid"] == sum(s is not None for s in scores)
    if dissenter:
        assert c["dissenter_label"] == V3.labels[dissenter]
        # majority value is the value the other two share
        assert c["majority"] == b.JUDGE_DISPLAY[[s for k, s in zip(V3.keys, scores) if k != dissenter][0]]
    # votes partition the valid graders, most votes first
    assert sorted(g for v in c["votes"] for g in v["graders"]) == sorted(
        k for k, s in zip(V3.keys, scores) if s is not None
    )
    assert [v["n"] for v in c["votes"]] == sorted((v["n"] for v in c["votes"]), reverse=True)


@pytest.mark.parametrize(
    "scores, status",
    [((1, 1), "unanimous"), ((1, 0), "all_differ"), ((1, None), "fewer_valid")],
)
def test_judge_consensus_n2(scores, status):
    """With two graders a disagreement has no identifiable dissenter."""
    c = pool(V2POOL, [None if s is None else coding(s) for s in scores])["consensus"]["judge"]
    assert c["status"] == status
    assert c["dissenter"] is None
    if status == "all_differ":
        assert c["label"] == "graders disagree (1–1)"


def test_patienthood_and_conflict_consensus_dissenters():
    avg = pool(V3, [
        coding(0, "affirm", [conflict("paternalism")]),
        coding(0, "affirm", [conflict("paternalism"), conflict("paternalism")]),  # same SET
        coding(0, "hedge", [conflict("welfare", "model_welfare")]),
    ])
    assert avg["consensus"]["patienthood"]["status"] == "one_dissent"
    assert avg["consensus"]["patienthood"]["dissenter"] == "muse"
    assert avg["consensus"]["conflicts"]["status"] == "one_dissent"
    assert avg["consensus"]["conflicts"]["dissenter"] == "muse"
    assert avg["consensus"]["conflicts"]["majority"] == "paternalism"
    assert avg["consensus"]["judge"]["status"] == "unanimous"


def test_partial_split_only_with_four_graders():
    extra = b.Grader("x4", "Grader X", "x/x", b.MUSE.path)
    v4 = dataclasses.replace(V3, graders=(b.GEMMA, b.QWEN, b.MUSE, extra))
    c = b.consensus_of([("gemma", "a"), ("qwen", "a"), ("muse", "b"), ("x4", "b")], 4, v4.labels)
    assert c["status"] == "partial_split" and c["label"] == "2–2 split"
    c = b.consensus_of([("gemma", "a"), ("qwen", "a"), ("muse", "a"), ("x4", "b")], 4, v4.labels)
    assert c["status"] == "one_dissent" and c["dissenter"] == "x4" and c["label"].startswith("3–1 split")


def test_direct_selfcheck_classifier_agrees_with_bundle_classifier():
    """The self-check's independent Counter-based classifier and the bundle's
    consensus_of must agree on EVERY judge combination (incl. invalid graders)."""
    for combo in itertools.product([-1, 0, 1, None], repeat=3):
        valid = [(k, s) for k, s in zip(V3.keys, combo) if s is not None]
        if not valid:
            continue
        status, who = b._judge_consensus_direct(valid, 3)
        c = b.consensus_of([(k, b.JUDGE_DISPLAY[s]) for k, s in valid], 3, V3.labels)
        assert (status, who) == (c["status"], c["dissenter"]), combo


# ---------------------------------------------------------------------------
# Self-check + build-time verifiers on synthetic data
# ---------------------------------------------------------------------------


def eid(model, doc="claude_constitution", doc_type="constitution", cond="baseline", rnd=1):
    return f"run_x|{cond}|{model}|{doc}|{doc_type}|{rnd}"


def synthetic():
    """{edit_id: [gemma, qwen, muse]} exercising every pooling/consensus case."""
    return {
        eid("M1", rnd=1): [coding(1, "affirm"), coding(1, "affirm"), coding(1, "affirm")],
        eid("M1", rnd=2): [coding(1, "affirm", [conflict("paternalism", "user_idealized")]),
                           coding(1, "hedge", [conflict("paternalism", "user_stated")]),
                           coding(0, "hedge")],
        eid("M1", "opus_system_prompt", "system_prompt", "cross_edit", 3):
            [coding(1), coding(0), coding(-1, conflicts=[conflict("welfare", "model_welfare")])],
        eid("M2", rnd=1): [coding(-1, "deny"), None, coding(-1, "affirm")],
        eid("M2", "gpt_system_prompt", "system_prompt", rnd=2): [None, None, coding(0)],
        eid("M3", rnd=1): [None, None, None],
    }


def codes_from(entries, variant=V3):
    return {g.key: {e: per[i] for e, per in entries.items()} for i, g in enumerate(variant.graders)}


def test_selfcheck_pooled_numbers():
    sc = b.selfcheck_pooled(codes_from(synthetic()), V3)
    pm = sc["per_model_mean_judge"]
    assert pm["M1"]["n_edits"] == 3
    assert pm["M1"]["mean_judge_avg"] == pytest.approx((1 + TWO_THIRDS + 0) / 3)
    assert pm["M2"] == {"mean_judge_avg": pytest.approx(-0.5), "n_edits": 2}
    assert "M3" not in pm  # no valid grader -> uncoded, excluded
    assert sc["per_model_p_affirm"]["M1"]["p_affirm"] == pytest.approx((1 + THIRD) / 3)
    assert sc["per_model_p_affirm"]["M2"]["affirm_weight"] == pytest.approx(0.5)
    pat = sc["per_model_paternalism"]["M1"]
    assert pat["presence_weight"] == pytest.approx(TWO_THIRDS)
    assert pat["direction_weights"] == pytest.approx({"idealized": THIRD, "stated": THIRD})
    assert sc["per_model_welfare"]["M1"]["direction_weights"] == pytest.approx({"model": THIRD})
    assert sc["n_edits_by_n_valid_graders"] == {"3": 3, "2": 1, "1": 1, "0": 1}
    assert sc["n_edits_total"] == 5
    assert sc["judge_consensus_counts"] == {
        "unanimous": 1, "one_dissent": 1, "all_differ": 1, "fewer_valid": 2,
    }
    assert sc["judge_one_dissent_by_dissenter"] == {"gemma": 0, "qwen": 0, "muse": 1}
    assert sc["judge_fewer_valid_breakdown"] == {
        "valid_graders_agree": 1, "valid_graders_disagree": 0, "single_valid_grader": 1,
    }
    sp = b.sp_stratum_from_codes(codes_from(synthetic()), V3)
    assert sp["n_edits_by_n_valid_graders"] == {"3": 1, "2": 0, "1": 1}
    assert sp["per_model_mean_judge"]["M1"] == {"mean_judge_avg": 0.0, "n_edits": 1}


def synthetic_bundle(entries, variant=V3):
    codings = codes_from(entries, variant)
    records = []
    for e in entries:
        parts = e.split("|")
        c = b.pooled_coding_for_edit(codings, e, variant)
        records.append({
            "edit_id": e, "model_display": parts[2], "doc_type": parts[4],
            "v2_coding_status": b.coded_status(variant, c["n_graders_valid"]) if c else "uncoded_no_valid_grader",
            "coding": c,
        })
    return {"runs": [{"records": records}]}


def test_verify_pooled_bundle_accepts_truth_and_catches_drift():
    entries = synthetic()
    codings = codes_from(entries)
    sc = b.selfcheck_pooled(codings, V3)
    sp = b.sp_stratum_from_codes(codings, V3)
    bundle = synthetic_bundle(entries)
    b.verify_pooled_bundle(sc, sp, bundle, V3)  # must not raise
    for mutate in (
        lambda c: c.__setitem__("judge_avg", c["judge_avg"] + 1e-6),
        lambda c: c["patienthood_weights"].__setitem__("affirm", 1.0),
        lambda c: c["consensus"]["judge"].__setitem__("status", "unanimous"),
    ):
        bad = synthetic_bundle(entries)
        target = next(r for r in bad["runs"][0]["records"] if r["edit_id"] == eid("M1", rnd=2))
        mutate(target["coding"])
        with pytest.raises(AssertionError):
            b.verify_pooled_bundle(sc, sp, bad, V3)


def test_verify_pooled_narratives_catches_drift():
    sc = b.selfcheck_pooled(codes_from(synthetic()), V3)

    def cell(total, dirs):
        return {"total": total, "dirs": dirs}

    good = {"stats": {
        "patienthood": {"baseline": {"M1": cell(2, {"affirm": 1 + THIRD, "hedge": TWO_THIRDS}),
                                     "M2": cell(1, {"deny": 0.5, "affirm": 0.5})},
                        "cross_edit": {"M1": cell(1, {})},
                        "you_framing": {"M2": cell(1, {})}},
        "conflict_paternalism": {"baseline": {"M1": cell(3, {"idealized": THIRD, "stated": THIRD}),
                                              "M2": cell(2, {})}},
        "conflict_welfare": {"baseline": {"M1": cell(3, {"model": THIRD}), "M2": cell(2, {})}},
    }}
    b.verify_pooled_narratives(sc, good)
    bad = json.loads(json.dumps(good))
    bad["stats"]["conflict_paternalism"]["baseline"]["M1"]["dirs"]["stated"] = TWO_THIRDS
    with pytest.raises(AssertionError):
        b.verify_pooled_narratives(sc, bad)


# ---------------------------------------------------------------------------
# Frontend patch set for v3pool
# ---------------------------------------------------------------------------


def _patch_v3(tmp_path):
    for name in b.STATIC_FILES:
        shutil.copyfile(b.DOCS / name, tmp_path / name)
    return b.apply_all_patches(V3, tmp_path)


def test_v3pool_patches_anchor_and_label_every_page(tmp_path):
    patcher = _patch_v3(tmp_path)
    assert len(patcher.log) == 33  # the 30 shared patches + 3 fraction-format extras
    for page in ("index.html", "conversations.html", "prompts.html"):
        text = (tmp_path / page).read_text(encoding="utf-8")
        assert b.V3POOL_LABEL in text, page
        assert "Krippendorff's &alpha; 0.520" in text, page
        assert "recode/reports/B_intergrader.md" in text, page
        assert "not the published v1 site" in text, page
        assert "@@" not in text
    prompts = (tmp_path / "prompts.html").read_text(encoding="utf-8")
    for g in V3.graders:
        assert g.model in prompts  # the prompts page lists all three graders
    for name in ("app.js", "facets.js"):
        js = (tmp_path / name).read_text(encoding="utf-8")
        assert "@@" not in js
        assert '"key": "muse", "label": "Muse Spark 1.3"' in js
    app = (tmp_path / "app.js").read_text(encoding="utf-8")
    assert 'record.coding.schema === "v3pool"' in app
    facets = (tmp_path / "facets.js").read_text(encoding="utf-8")
    # System-prompts chip kept, right after Cross Edit, fed by sp_stats
    assert '"implementation_note", "cross_edit", SP_CONDITION];' in facets
    assert "data.sp_stats" in facets and 'ex.doc_type !== "system_prompt"' in facets
    assert "v3pool: v1-tied highlight links disabled" in facets
    assert "fmtN(engaged)" in facets


def _node():
    return shutil.which("node")


@pytest.mark.skipif(_node() is None, reason="node not installed")
def test_v3pool_patched_js_node_check(tmp_path):
    _patch_v3(tmp_path)
    for name in ("app.js", "facets.js"):
        subprocess.run([_node(), "--check", str(tmp_path / name)], check=True)


JS_STUBS = """
const escapeHtml = (s) => String(s == null ? "" : s).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
const PATIENTHOOD_LABELS = {affirm: "Affirm", hedge: "Hedge", deny: "Deny"};
const CONFLICT_CODE_LABELS = {paternalism: "Paternalism", welfare: "Welfare"};
const PARTY_LABELS = {developer: "Developer", user_idealized: "User (idealized)", model_welfare: "Model"};
"""


@pytest.mark.skipif(_node() is None, reason="node not installed")
def test_v3pool_js_renders_consensus_markers_at_runtime():
    """Execute the patched per-edit renderers in node on real pooled codings:
    2–1 split names the dissenter, 3-way split and fewer-valid are shown, all
    three grader columns render (null grader -> 'no valid code')."""
    cases = {
        "dissent": pool(V3, [coding(1), coding(1), coding(-1, conflicts=[conflict("welfare", "model_welfare")])]),
        "threeway": pool(V3, [coding(1), coding(0), coding(-1)]),
        "fewer": pool(V3, [coding(1, "affirm"), None, coding(1, "affirm")]),
    }
    prelude = b._pool_js(b.POOL_FACETS_PRELUDE, V3)
    chips = b._pool_js(b.POOL_FACETS_CODECHIPS, V3)
    app_block = b._pool_js(b.POOL_APP_JS_CODING_BLOCK, V3)
    script = JS_STUBS + prelude + "\n" + chips + """
function renderRecord(record) {
  let out = null;
  const document = { createElement: () => ({}) };
  const node = { querySelector: () => ({ insertAdjacentElement: (_p, el) => { out = el.innerHTML; } }) };
""" + app_block + """
  return out;
}
const cases = JSON.parse(process.argv[1]);
const res = {};
for (const [k, c] of Object.entries(cases)) {
  res[k] = { chips: codeChips({ ...c, consensus: c.consensus, graders: c.graders }), record: renderRecord({ coding: c }) };
}
console.log(JSON.stringify(res));
"""
    proc = subprocess.run([_node(), "-e", script, json.dumps(cases)], check=True,
                          capture_output=True, text=True)
    res = json.loads(proc.stdout)
    for where in ("chips", "record"):
        assert "2–1 split (Muse Spark 1.3 dissents)" in res["dissent"][where]
        assert "3-way split" in res["threeway"][where]
        assert "only 2 of 3 graders valid (they agree)" in res["fewer"][where]
        assert "dissents on judge" in res["dissent"][where]
    assert "no valid code from this grader" in res["fewer"]["record"]
    assert "Qwen 3.8" in res["fewer"]["record"] and "Muse Spark 1.3" in res["fewer"]["record"]
    assert "pooled judge +0.33 · 3/3 graders valid" in res["dissent"]["record"]
    assert "0.00" in res["threeway"]["chips"]


# ---------------------------------------------------------------------------
# Built outputs: v3pool matches its codes files; v2avg reproducibility guard
# ---------------------------------------------------------------------------


def _strip_ts(obj):
    if isinstance(obj, dict):
        return {k: _strip_ts(v) for k, v in obj.items() if k != "generated_at"}
    if isinstance(obj, list):
        return [_strip_ts(v) for v in obj]
    return obj


V3_DATA = b.V3POOL.out_dir / "data"


@pytest.mark.skipif(not (V3_DATA / "selfcheck.json").exists(), reason="site_v3pool not built")
def test_built_v3pool_reproduces_selfcheck_from_codes():
    """The committed/built site_v3pool data must match a fresh self-check
    recomputed from the three codes files, and pass every build-time check."""
    codings = b.load_grader_codings(V3)
    fresh = b.selfcheck_pooled(codings, V3)
    sp = b.sp_stratum_from_codes(codings, V3)
    stored = json.loads((V3_DATA / "selfcheck.json").read_text(encoding="utf-8"))
    for key, value in fresh.items():
        assert stored[key] == value, key
    assert stored["system_prompt_stratum"] == sp
    assert stored["n_edits_by_n_valid_graders"]["0"] == 0
    narratives = json.loads((V3_DATA / "narratives.json").read_text(encoding="utf-8"))
    b.verify_against_narratives(fresh, narratives)
    b.verify_sp_against_narratives(sp, narratives)
    b.verify_pooled_narratives(fresh, narratives)
    bundle = json.loads(gzip.decompress((V3_DATA / "site.json.gz").read_bytes()))
    b.verify_pooled_bundle(fresh, sp, bundle, V3)
    assert bundle["variant"] == b.V3POOL_LABEL
    assert [g["key"] for g in bundle["graders"]] == ["gemma", "qwen", "muse"]


def test_v2avg_reproducible(tmp_path):
    """REPRODUCIBILITY GUARD: rebuilding the v2avg variant with the refactored
    builder must reproduce the committed recode/site_v2avg/ exactly, except the
    embedded generated_at timestamps (site.json.gz compared decompressed)."""
    committed = b.V2AVG.out_dir
    b.build(b.V2AVG, out_dir=tmp_path)
    names = sorted(p.relative_to(committed).as_posix() for p in committed.rglob("*") if p.is_file())
    built = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*") if p.is_file())
    assert names == built
    for rel in names:
        old, new = committed / rel, tmp_path / rel
        if rel == "data/site.json.gz":
            jo = json.loads(gzip.decompress(old.read_bytes()))
            jn = json.loads(gzip.decompress(new.read_bytes()))
            assert _strip_ts(jo) == _strip_ts(jn)
            jo["generated_at"] = jn["generated_at"] = ""
            assert json.dumps(jo, ensure_ascii=False) == json.dumps(jn, ensure_ascii=False)
        elif rel == "data/selfcheck.json":
            drop = lambda t: [ln for ln in t.splitlines() if '"generated_at"' not in ln]  # noqa: E731
            assert drop(old.read_text(encoding="utf-8")) == drop(new.read_text(encoding="utf-8"))
        else:
            assert old.read_bytes() == new.read_bytes(), rel
