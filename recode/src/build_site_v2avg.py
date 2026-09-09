"""Build recode/site_v2avg/ — a locally served variant of the docs/ GitHub Pages
site in which EVERY figure/aggregate is computed from the equal-weight AVERAGE of
the two v2 graders (recode/data/codes/v2_gemma.jsonl + v2_qwen.jsonl).

What this script does (rerunnable end to end):
  1. Copies the site's static assets from docs/ (docs/ itself is never touched).
  2. Regenerates the two data bundles into recode/site_v2avg/data/:
       - site.json.gz   (record bundle; per-record BOTH graders' v2 codings plus
                         precomputed per-edit average fields)
       - narratives.json (facet stats/stories with grader-averaged dirs/cum/cumsq
                         — regenerated, since build_narratives.py is fully
                         deterministic local aggregation with zero LLM calls)
  3. Patches the copied HTML/JS minimally (exact-match splices, asserted unique)
     so aggregates use average semantics, per-edit displays show gemma and qwen
     side by side with a disagreement marker, every page carries the variant
     label, and uncoded edits render gracefully. Writes PATCHES.md.
  4. Prints + writes a self-check (per-model mean judge under the average,
     computed directly from the two codes files) to data/selfcheck.json.

Code reuse (import vs vendor):
  - build_narratives.py is IMPORTED (side-effect-free at import) and its
    conflict_direction / facet_memberships / facet_net_scores / FACET_IDS /
    FACET_POLES / MAX_ROUND / EXAMPLES_PER_CELL / SAMPLE_SEED are reused so the
    per-grader facet semantics are byte-identical to the published pipeline.
  - build_static_site.py is IMPORTED for summarize_run / load_jsonl_records /
    RELIABLE_RUNS. Its changed_records() is VENDORED below (changed_records_v2avg)
    because the original hard-wires the v1 coded file through module globals and
    a module-level cache; only the coding join is changed, everything else
    (id format, field defaults, sort order) is copied line-for-line.

Averaging semantics (fixed, per the task spec — grader-level equal weighting):
  - mean judge score of an edit = mean of the valid graders' scores; an edit
    valid under only one grader contributes that grader's value (and is counted
    and marked as single-grader).
  - a count/rate of a categorical property weights an edit by
    (#valid graders assigning it) / (#valid graders): 1.0 both, 0.5 exactly one
    of two, 1.0 for a single-grader edit whose grader assigns it. This makes
    the judge facet's (pos − neg)/total displayed mean equal EXACTLY the mean
    of per-edit judge averages.
  - per-edit displays cannot average categories: they show both graders' codes
    side by side with a visible disagreement marker.
  - drift (cum/cumsq): per-edit net facet score = mean over valid graders of
    that grader's net score (fractional steps allowed; this also fixes the
    original builder's exact-equality trap that would drop fractional scores).
  - denominator ("total"): edits coded by at least one v2 grader. NOTE: v2
    graded the 2 abstentions (v1 did not), so totals are 2,582 vs v1's 2,580.

"System prompts" view (facet browser condition-chip row, right after Cross Edit):
  - restricts every figure it governs to edits whose document_type ==
    "system_prompt", ACROSS ALL CONDITIONS (own-document and cross-edit edits of
    system prompts alike), rendered BY EDITING MODEL exactly like the real
    condition chips — one freq-bar row / drift line per model, model-visibility
    chips fully active.
  - data: narratives.json carries a separate top-level "sp_stats" table
    ({facet: {model_display: cell}}; the same cell shape as "stats", pooled over
    all conditions and system-prompt documents, replicate = one
    (run, condition, model) chain editing a system-prompt document, i.e. keyed
    (run, condition, document) within each model's entry).
    Keeping it OUTSIDE "stats" is load-bearing: the frontend's "All conditions"
    pooling iterates every key of stats[fid], so a pseudo-condition stored
    in-table would be double-counted.
  - story examples carry a new "doc_type" field (existing fields unchanged) so
    the example browser can filter the stratum client-side.
  - ground truth: selfcheck.json gains "system_prompt_stratum" (per-model and,
    for reference, per-system-prompt-document mean judge + Ns under the same
    averaging rules); the per-model table is asserted against sp_stats at build
    time (the per-document table is reference-only — the frontend renders the
    view per model).

Usage:
    /Users/nicholasgannon/llm-value-reflection/.venv/bin/python \
        recode/src/build_site_v2avg.py
"""

from __future__ import annotations

import gzip
import html as html_mod
import json
import random
import re
import shutil
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
RECODE = ROOT / "recode"
OUT = RECODE / "site_v2avg"
OUT_DATA = OUT / "data"
RESULTS_DIR = ROOT / "results" / "iterative_edit"
EDITS_PATH = RECODE / "data" / "canonical" / "edits.jsonl"
GEMMA_PATH = RECODE / "data" / "codes" / "v2_gemma.jsonl"
QWEN_PATH = RECODE / "data" / "codes" / "v2_qwen.jsonl"
V2_SYSTEM_PROMPT = RECODE / "prompts" / "v2_system.md"
V2_USER_TEMPLATE = RECODE / "prompts" / "v2_user_template.md"

sys.path.insert(0, str(RECODE / "src"))
sys.path.insert(0, str(ROOT / "experiments" / "iterative_edit" / "viewer"))

import codes_io  # noqa: E402  (recode/src — pinned loader/validity predicate)
import build_narratives as bn  # noqa: E402  (import-only; no side effects at import)
import build_static_site as bss  # noqa: E402  (import-only; no side effects at import)

GRADERS = [
    # (short key, display label, model string, codes path)
    ("gemma", "Gemma 4", "google/gemma-4-31b-it", GEMMA_PATH),
    ("qwen", "Qwen 3.8", "qwen/qwen3.8-2.4t-a95b", QWEN_PATH),
]
GRADER_LABELS = {short: label for short, label, _m, _p in GRADERS}

VARIANT_LABEL = "v2 blinded re-code — Gemma 4 + Qwen 3.8 average (recode pipeline)"
COMBINED_CODER = (
    "google/gemma-4-31b-it + qwen/qwen3.8-2.4t-a95b (v2 blinded, equal-weight average)"
)
METHODS_NOTE = (
    "Two independent graders (google/gemma-4-31b-it and qwen/qwen3.8-2.4t-a95b) re-coded "
    "every edit blinded to the editing model and prompt condition, with surrounding document "
    "context; every figure and aggregate on this page is the equal-weight average of the two "
    "graders, and per-edit views show both codes side by side with disagreements flagged. "
    "Inter-grader agreement report: recode/reports/B_intergrader.md (in the repository)."
)

# The four provider system prompts (DECISIONS.md §10 lists the 8 documents).
# The frontend's System-prompts view renders per MODEL, but the stratum's
# document set must still be exactly these four — the build asserts it as a
# data-sanity check on the selfcheck's reference per-document table.
EXPECTED_SP_DOCS = {
    "opus_system_prompt",
    "gpt_system_prompt",
    "gemini_system_prompt",
    "grok_system_prompt",
}

STATIC_FILES = [
    "index.html",
    "conversations.html",
    "prompts.html",
    "styles.css",
    "app.js",
    "facets.js",
    "reveal.js",
]

# ---------------------------------------------------------------------------
# Averaging core
# ---------------------------------------------------------------------------


def load_grader_codings() -> dict[str, dict[str, dict | None]]:
    """{grader short: {edit_id: validated coding or None}} via codes_io."""
    return {short: codes_io.codings_by_id(path) for short, _l, _m, path in GRADERS}


def edit_id_of_record(run_name: str, record: dict) -> str:
    """Canonical 6-part pipe edit id built from a run record's own fields."""
    return "|".join(
        [
            run_name.replace(".jsonl", ""),
            record.get("condition_id") or "baseline",
            record.get("model_display") or "",
            record.get("document_id") or "",
            record.get("doc_type") or "",
            str(int(record.get("round_number") or 0)),
        ]
    )


def valid_pairs(codings_by_grader: dict, edit_id: str) -> list[tuple[str, dict]]:
    """[(grader short, coding)] for graders with a VALID coding of this edit."""
    out = []
    for short, _label, _model, _path in GRADERS:
        coding = codings_by_grader[short].get(edit_id)
        if coding is not None:
            out.append((short, coding))
    return out


def judge_avg_of(pairs: list[tuple[str, dict]]) -> float | None:
    scores = [codes_io.judge_score(c) for _s, c in pairs]
    scores = [s for s in scores if s is not None]
    if not scores:
        return None
    return sum(scores) / len(scores)


def conflict_code_weights(pairs: list[tuple[str, dict]]) -> dict[str, float]:
    """{conflict code: (#valid graders assigning >=1 conflict of code)/#valid}."""
    n = len(pairs)
    counts: dict[str, int] = defaultdict(int)
    for _s, coding in pairs:
        codes = {c.get("code") for c in codes_io.conflicts(coding) if isinstance(c, dict)}
        for code in codes:
            if code:
                counts[code] += 1
    return {code: k / n for code, k in sorted(counts.items())}


def avg_coding_for_edit(codings_by_grader: dict, edit_id: str) -> dict | None:
    """The bundle 'coding' object: both graders side by side + averaged fields.

    None when neither grader has a valid coding (error records, exploratory
    runs — those records are passed through explicitly marked uncoded)."""
    pairs = valid_pairs(codings_by_grader, edit_id)
    if not pairs:
        return None
    n = len(pairs)
    by_short = dict(pairs)
    g = by_short.get("gemma")
    q = by_short.get("qwen")

    def sub(coding: dict | None) -> dict | None:
        if coding is None:
            return None
        return {
            "summary": coding.get("summary", ""),
            "judge": coding.get("judge"),
            "patienthood": coding.get("patienthood"),
            "conflicts": codes_io.conflicts(coding),
        }

    judge_agree = None
    pat_agree = None
    conf_agree = None
    if n == 2:
        judge_agree = codes_io.judge_score(g) == codes_io.judge_score(q)
        pat_agree = codes_io.patienthood_level(g) == codes_io.patienthood_level(q)
        conf_agree = sorted(
            c.get("code") or "" for c in codes_io.conflicts(g)
        ) == sorted(c.get("code") or "" for c in codes_io.conflicts(q))
    single = GRADER_LABELS[pairs[0][0]] if n == 1 else None

    return {
        "schema": "v2avg",
        "coder_model": COMBINED_CODER,
        "n_graders_valid": n,
        "single_grader": single,
        "judge_avg": judge_avg_of(pairs),
        "judge_agree": judge_agree,
        "patienthood_agree": pat_agree,
        "conflicts_agree": conf_agree,
        "patienthood_pair": {
            "gemma": codes_io.patienthood_level(g),
            "qwen": codes_io.patienthood_level(q),
        },
        "conflict_weights": conflict_code_weights(pairs),
        "graders": {"gemma": sub(g), "qwen": sub(q)},
    }


# ---------------------------------------------------------------------------
# Bundle: site.json.gz (vendored changed_records with the coding join swapped)
# ---------------------------------------------------------------------------


def changed_records_v2avg(
    run_name: str, records: list[dict], codings_by_grader: dict, counters: dict
) -> list[dict]:
    """Vendored from build_static_site.changed_records; only the coding source
    differs (v2 two-grader average instead of the v1 coded file). Id format,
    injected defaults, and sort order are copied unchanged so the frontend's
    assumptions hold."""
    grouped: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for record in records:
        key = (
            record["model_id"],
            record["document_id"],
            record.get("condition_id", "baseline"),
        )
        grouped[key].append(record)

    items = []
    for chain in grouped.values():
        chain.sort(key=lambda record: record["round_number"])
        for record in chain:
            edit_id = edit_id_of_record(run_name, record)
            coding = avg_coding_for_edit(codings_by_grader, edit_id)
            if coding is None:
                if record.get("error"):
                    status = "uncoded_generation_error"
                elif run_name not in bss.RELIABLE_RUNS:
                    status = "uncoded_exploratory_run"
                else:
                    status = "uncoded_no_valid_grader"
                counters[status] = counters.get(status, 0) + 1
            else:
                status = {2: "avg_two_graders", 1: "single_grader"}[coding["n_graders_valid"]]
                counters[status] = counters.get(status, 0) + 1
            items.append(
                {
                    "id": (
                        f"{run_name}:{record['model_id']}:{record['document_id']}:{record.get('condition_id', 'baseline')}:"
                        f"{record['round_number']}"
                    ),
                    "edit_id": edit_id,
                    "run_name": run_name,
                    "timestamp": record.get("timestamp"),
                    "condition_id": record.get("condition_id", "baseline"),
                    "condition_name": record.get("condition_name", "Baseline"),
                    "model_id": record.get("model_id"),
                    "model_display": record.get("model_display"),
                    "document_id": record.get("document_id"),
                    "document_provider": record.get("document_provider"),
                    "doc_type": record.get("doc_type"),
                    "round_number": record.get("round_number"),
                    "total_rounds": record.get("total_rounds"),
                    "change_description": record.get("change_description", ""),
                    "find_text": record.get("find_text", ""),
                    "replace_text": record.get("replace_text", ""),
                    "match_strategy": record.get("match_strategy", "exact"),
                    "retried": bool(record.get("retried")),
                    "no_change": bool(record.get("no_change")),
                    "error": record.get("error"),
                    "input_tokens": record.get("input_tokens", 0),
                    "output_tokens": record.get("output_tokens", 0),
                    "elapsed_ms": record.get("elapsed_ms", 0),
                    "v2_coding_status": status,
                    "coding": coding,
                }
            )

    items.sort(
        key=lambda record: (
            record["condition_name"] or "",
            record["model_display"] or "",
            record["document_id"] or "",
            record["round_number"] or 0,
        )
    )
    return items


def build_bundle(codings_by_grader: dict) -> tuple[dict, dict]:
    counters: dict = {}
    runs = []
    for path in sorted(RESULTS_DIR.glob("run_*.jsonl"), reverse=True):
        raw_records = bss.load_jsonl_records(path)
        summary = bss.summarize_run(raw_records, path.name)
        summary["records"] = changed_records_v2avg(
            path.name, raw_records, codings_by_grader, counters
        )
        runs.append(summary)
    bundle = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "variant": VARIANT_LABEL,
        "runs": runs,
    }
    return bundle, counters


# ---------------------------------------------------------------------------
# Narratives: grader-averaged stats + dual-grader stories
# ---------------------------------------------------------------------------


def load_canonical_edits() -> list[dict]:
    edits = []
    with open(EDITS_PATH, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                edits.append(json.loads(line))
    return edits


def facet_detail_for(
    fid: str,
    direction: str,
    memberships_by_grader: dict[str, dict],
) -> dict:
    """Combined facet detail: per-grader evidence for judge/patienthood facets,
    grader-tagged conflicts for conflict facets."""
    detail: dict = {"direction": direction}
    if fid in ("judge", "patienthood"):
        for short in ("gemma", "qwen"):
            m = memberships_by_grader.get(short, {}).get(fid)
            if m and m.get("evidence"):
                detail[f"evidence_{short}"] = m["evidence"]
            if m and m.get("external_locus"):
                detail[f"external_locus_{short}"] = m["external_locus"]
    else:
        combined = []
        for short in ("gemma", "qwen"):
            m = memberships_by_grader.get(short, {}).get(fid)
            for c in (m or {}).get("conflicts", []):
                tagged = dict(c)
                tagged["grader"] = GRADER_LABELS[short]
                combined.append(tagged)
        detail["conflicts"] = combined
    return detail


def build_narratives_v2avg(codings_by_grader: dict) -> dict:
    """Adaptation of build_narratives.build() with grader-level equal weighting.

    dirs/cum/cumsq are floats; 'total' counts edits coded by >=1 v2 grader; the
    per-grader facet semantics (facet_memberships / facet_net_scores /
    conflict_direction) are imported from build_narratives.py unchanged."""
    edits = load_canonical_edits()

    stats: dict[str, dict[str, dict[str, dict]]] = {
        fid: defaultdict(lambda: defaultdict(lambda: {"total": 0, "dirs": defaultdict(float)}))
        for fid in bn.FACET_IDS
    }
    examples_by_cell: dict[tuple[str, str, str, str], list[dict]] = defaultdict(list)
    rep_net: dict[tuple, list[float]] = defaultdict(lambda: [0.0] * bn.MAX_ROUND)
    replicates: dict[tuple[str, str], set] = defaultdict(set)

    # System-prompt stratum: same cell semantics, keyed by MODEL (model_display,
    # exactly like the per-condition cells) but restricted to system-prompt
    # documents and pooled over ALL conditions; a replicate is one
    # (run, condition, model) chain editing a system-prompt document — within a
    # model's entry that is the (run, condition, document) tuple.
    sp_stats: dict[str, dict[str, dict]] = {
        fid: defaultdict(lambda: {"total": 0, "dirs": defaultdict(float)})
        for fid in bn.FACET_IDS
    }
    sp_rep_net: dict[tuple, list[float]] = defaultdict(lambda: [0.0] * bn.MAX_ROUND)
    sp_replicates: dict[str, set] = defaultdict(set)

    for edit in edits:
        edit_id = edit["edit_id"]
        pairs = valid_pairs(codings_by_grader, edit_id)
        if not pairs:
            continue  # error records: nothing was graded
        n = len(pairs)
        condition = edit.get("condition") or "baseline"
        model = edit.get("model") or ""
        avg = avg_coding_for_edit(codings_by_grader, edit_id)

        memberships_by_grader = {short: bn.facet_memberships(c) for short, c in pairs}

        rnd = edit.get("round")
        rep = (edit.get("run_id"), edit.get("document_id"))
        replicates[(condition, model)].add(rep)

        doc_id = edit.get("document_id") or ""
        doc_type = edit.get("document_type")
        is_sp = doc_type == "system_prompt"
        sp_chain = (edit.get("run_id"), condition, doc_id)
        if is_sp:
            sp_replicates[model].add(sp_chain)

        # Grader-averaged net facet scores -> drift accumulators.
        if isinstance(rnd, int) and 1 <= rnd <= bn.MAX_ROUND:
            net_sum: dict[str, float] = defaultdict(float)
            for _short, coding in pairs:
                for fid, net in bn.facet_net_scores(coding).items():
                    net_sum[fid] += net
            for fid, total_net in net_sum.items():
                rep_net[(fid, condition, model, rep)][rnd - 1] += total_net / n
                if is_sp:
                    sp_rep_net[(fid, model, sp_chain)][rnd - 1] += total_net / n

        # Direction weights: (#graders assigning this facet-direction) / n.
        dir_votes: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for _short, m in memberships_by_grader.items():
            for fid, detail in m.items():
                dir_votes[fid][detail["direction"]] += 1

        for fid in bn.FACET_IDS:
            cell = stats[fid][condition][model]
            cell["total"] += 1
            for direction, votes in dir_votes.get(fid, {}).items():
                cell["dirs"][direction] += votes / n
            if is_sp:
                sp_cell = sp_stats[fid][model]
                sp_cell["total"] += 1
                for direction, votes in dir_votes.get(fid, {}).items():
                    sp_cell["dirs"][direction] += votes / n

        # Stories: one example per (facet, direction) a grader assigned; the
        # card shows BOTH graders' codes with a disagreement marker.
        for fid, directions in dir_votes.items():
            for direction in directions:
                primary_short, primary_coding = pairs[0]
                example = {
                    "id": edit_id,
                    "round": edit.get("round"),
                    "condition_id": condition,
                    "condition_name": edit.get("condition_name", condition),
                    "model_display": model,
                    "document_id": edit.get("document_id"),
                    "doc_type": doc_type,
                    "direction": direction,
                    "summary": (
                        f"{GRADER_LABELS[primary_short]}: "
                        f"{primary_coding.get('summary', '')}"
                    ),
                    "n_graders_valid": n,
                    "single_grader": avg["single_grader"],
                    "judge_avg": avg["judge_avg"],
                    "judge_agree": avg["judge_agree"],
                    "patienthood_agree": avg["patienthood_agree"],
                    "conflicts_agree": avg["conflicts_agree"],
                    "graders": avg["graders"],
                    "facet_detail": facet_detail_for(fid, direction, memberships_by_grader),
                    "original_text": edit.get("find_text", ""),
                    "changed_text": edit.get("replace_text_sanitized", ""),
                }
                examples_by_cell[(fid, condition, model, direction)].append(example)

    rng = random.Random(bn.SAMPLE_SEED)
    stories: dict[str, list[dict]] = {fid: [] for fid in bn.FACET_IDS}
    for (fid, _cond, _model, _direction), exs in sorted(examples_by_cell.items()):
        if len(exs) > bn.EXAMPLES_PER_CELL:
            exs = rng.sample(exs, bn.EXAMPLES_PER_CELL)
        stories[fid].extend(exs)
    # No curated ride-on: the published curated_examples.json ids are tied to v1
    # codes/directions, and the highlight links that used them are disabled in
    # the patched facets.js.

    cum_sums: dict[tuple[str, str, str], list[float]] = defaultdict(lambda: [0.0] * bn.MAX_ROUND)
    cum_sqs: dict[tuple[str, str, str], list[float]] = defaultdict(lambda: [0.0] * bn.MAX_ROUND)
    for (fid, cond, model, _rep), nets in rep_net.items():
        cum = 0.0
        for r in range(bn.MAX_ROUND):
            cum += nets[r]
            cum_sums[(fid, cond, model)][r] += cum
            cum_sqs[(fid, cond, model)][r] += cum * cum

    sp_cum_sums: dict[tuple[str, str], list[float]] = defaultdict(lambda: [0.0] * bn.MAX_ROUND)
    sp_cum_sqs: dict[tuple[str, str], list[float]] = defaultdict(lambda: [0.0] * bn.MAX_ROUND)
    for (fid, model, _sp_chain), nets in sp_rep_net.items():
        cum = 0.0
        for r in range(bn.MAX_ROUND):
            cum += nets[r]
            sp_cum_sums[(fid, model)][r] += cum
            sp_cum_sqs[(fid, model)][r] += cum * cum

    stats_out: dict[str, dict] = {}
    for fid in bn.FACET_IDS:
        cond_map = {}
        for cond, model_map in stats[fid].items():
            cond_map[cond] = {
                model: {
                    "total": c["total"],
                    "dirs": {d: round(v, 6) for d, v in c["dirs"].items()},
                    "cum": [round(v, 6) for v in cum_sums.get((fid, cond, model), [0.0] * bn.MAX_ROUND)],
                    "cumsq": [round(v, 6) for v in cum_sqs.get((fid, cond, model), [0.0] * bn.MAX_ROUND)],
                    "reps": len(replicates[(cond, model)]),
                }
                for model, c in model_map.items()
            }
        stats_out[fid] = cond_map

    # System-prompt stratum table, kept OUTSIDE "stats" so the frontend's
    # "All conditions" pooling (which iterates every stats[fid] key) never
    # double-counts it. Keyed by model_display — the same keys the normal
    # per-condition cells use — so aggStat/renderFreqBars/renderDriftChart and
    # the model-visibility chips work unchanged in the System-prompts view.
    sp_stats_out: dict[str, dict] = {}
    for fid in bn.FACET_IDS:
        sp_stats_out[fid] = {
            model: {
                "total": c["total"],
                "dirs": {d: round(v, 6) for d, v in c["dirs"].items()},
                "cum": [round(v, 6) for v in sp_cum_sums.get((fid, model), [0.0] * bn.MAX_ROUND)],
                "cumsq": [round(v, 6) for v in sp_cum_sqs.get((fid, model), [0.0] * bn.MAX_ROUND)],
                "reps": len(sp_replicates[model]),
            }
            for model, c in sorted(sp_stats[fid].items())
        }

    return {
        "coder_model": COMBINED_CODER,
        "variant": VARIANT_LABEL,
        "stats": stats_out,
        "sp_stats": sp_stats_out,
        "stories": stories,
    }


# ---------------------------------------------------------------------------
# Self-check: ground truth straight from the two codes files
# ---------------------------------------------------------------------------


def selfcheck_from_codes(codings_by_grader: dict) -> dict:
    """Per-model mean judge under the average, computed DIRECTLY from the two
    codes files (model = 3rd pipe field of edit_id). Auditors compare the site
    against these numbers."""
    all_ids = set()
    for m in codings_by_grader.values():
        all_ids.update(m.keys())
    per_model: dict[str, list[float]] = defaultdict(list)
    n_both = n_gemma_only = n_qwen_only = 0
    for edit_id in sorted(all_ids):
        pairs = valid_pairs(codings_by_grader, edit_id)
        if not pairs:
            continue
        shorts = {s for s, _c in pairs}
        if shorts == {"gemma", "qwen"}:
            n_both += 1
        elif shorts == {"gemma"}:
            n_gemma_only += 1
        else:
            n_qwen_only += 1
        avg = judge_avg_of(pairs)
        model = edit_id.split("|")[2]
        per_model[model].append(avg)
    return {
        "description": (
            "Per-model mean judge score under the two-grader average "
            "(mean over edits of mean over valid graders of judge score; "
            "single-grader edits contribute that grader's value). Computed "
            "directly from recode/data/codes/v2_gemma.jsonl + v2_qwen.jsonl."
        ),
        "per_model_mean_judge": {
            m: {"mean_judge_avg": sum(v) / len(v), "n_edits": len(v)}
            for m, v in sorted(per_model.items())
        },
        "n_edits_total": sum(len(v) for v in per_model.values()),
        "n_both_graders_valid": n_both,
        "n_gemma_only": n_gemma_only,
        "n_qwen_only": n_qwen_only,
    }


def sp_stratum_from_codes(codings_by_grader: dict) -> dict:
    """Ground truth for the "System prompts" view, computed DIRECTLY from the
    two codes files: mean judge under the two-grader average restricted to
    edits of system-prompt documents, across ALL conditions — per editing
    model (the table the frontend's per-model view is asserted against) AND,
    for reference only, per system-prompt document. The edit id's pipe fields
    are run|condition|model|document_id|doc_type|round, so doc type/id are
    fields 5/4."""
    all_ids = set()
    for m in codings_by_grader.values():
        all_ids.update(m.keys())
    per_model: dict[str, list[float]] = defaultdict(list)
    per_doc: dict[str, list[float]] = defaultdict(list)
    n_both = n_single = 0
    for edit_id in sorted(all_ids):
        parts = edit_id.split("|")
        if len(parts) != 6 or parts[4] != "system_prompt":
            continue
        pairs = valid_pairs(codings_by_grader, edit_id)
        if not pairs:
            continue
        if len(pairs) == 2:
            n_both += 1
        else:
            n_single += 1
        avg = judge_avg_of(pairs)
        per_model[parts[2]].append(avg)
        per_doc[parts[3]].append(avg)

    def table(groups: dict[str, list[float]]) -> dict:
        return {
            key: {"mean_judge_avg": sum(v) / len(v), "n_edits": len(v)}
            for key, v in sorted(groups.items())
        }

    return {
        "description": (
            "System-prompt stratum (the 'System prompts' view): edits whose "
            "document_type == 'system_prompt', pooled across ALL conditions "
            "(own-document and cross-edit alike). The view renders PER MODEL; "
            "per_model_mean_judge is the table asserted against the site's "
            "sp_stats, and per_document_mean_judge is kept for reference only. "
            "Mean judge under the same two-grader average (single-valid-grader "
            "edits contribute that grader's value at full weight). Computed "
            "directly from recode/data/codes/v2_gemma.jsonl + v2_qwen.jsonl."
        ),
        "per_model_mean_judge": table(per_model),
        "per_document_mean_judge": table(per_doc),
        "n_edits_total": sum(len(v) for v in per_doc.values()),
        "n_both_graders_valid": n_both,
        "n_single_grader": n_single,
    }


def verify_sp_against_narratives(sp: dict, narratives: dict) -> None:
    """The sp_stats judge cells (per MODEL — the view renders by model) must
    reproduce the direct per-model mean judge exactly, with matching Ns and the
    same model set; the stratum's document set must still be exactly the four
    provider system prompts (data sanity on the reference per-document table);
    and both stratum tables must partition the same edits."""
    judge_models = narratives["sp_stats"]["judge"]
    direct_docs = sp["per_document_mean_judge"]
    assert set(direct_docs) == EXPECTED_SP_DOCS, (
        f"system-prompt documents {sorted(direct_docs)} != expected {sorted(EXPECTED_SP_DOCS)}"
    )
    direct = sp["per_model_mean_judge"]
    assert set(judge_models) == set(direct), (
        f"sp_stats models {sorted(judge_models)} != selfcheck models {sorted(direct)}"
    )
    for model, cell in judge_models.items():
        site_mean = (
            cell["dirs"].get("discretion", 0.0) - cell["dirs"].get("external", 0.0)
        ) / cell["total"]
        entry = direct[model]
        diff = abs(site_mean - entry["mean_judge_avg"])
        assert diff < 1e-5, (
            f"sp self-check mismatch for {model}: site {site_mean} vs direct "
            f"{entry['mean_judge_avg']}"
        )
        assert cell["total"] == entry["n_edits"], (
            f"sp denominator mismatch for {model}: site {cell['total']} vs direct "
            f"{entry['n_edits']}"
        )
    n_by_model = sum(e["n_edits"] for e in direct.values())
    assert n_by_model == sp["n_edits_total"], (
        f"sp per-model N {n_by_model} != stratum total {sp['n_edits_total']}"
    )
    n_by_doc = sum(e["n_edits"] for e in direct_docs.values())
    assert n_by_doc == sp["n_edits_total"], (
        f"sp per-document N {n_by_doc} != stratum total {sp['n_edits_total']}"
    )


def verify_against_narratives(selfcheck: dict, narratives: dict) -> None:
    """The judge facet's pooled (discretion − external)/total per model must
    equal the direct per-model mean judge average exactly (up to rounding)."""
    judge = narratives["stats"]["judge"]
    per_model_pos: dict[str, float] = defaultdict(float)
    per_model_neg: dict[str, float] = defaultdict(float)
    per_model_total: dict[str, float] = defaultdict(float)
    for cond_map in judge.values():
        for model, cell in cond_map.items():
            per_model_pos[model] += cell["dirs"].get("discretion", 0.0)
            per_model_neg[model] += cell["dirs"].get("external", 0.0)
            per_model_total[model] += cell["total"]
    for model, entry in selfcheck["per_model_mean_judge"].items():
        site_mean = (per_model_pos[model] - per_model_neg[model]) / per_model_total[model]
        diff = abs(site_mean - entry["mean_judge_avg"])
        assert diff < 1e-5, (
            f"self-check mismatch for {model}: site {site_mean} vs direct "
            f"{entry['mean_judge_avg']}"
        )
        assert per_model_total[model] == entry["n_edits"], (
            f"denominator mismatch for {model}: site {per_model_total[model]} "
            f"vs direct {entry['n_edits']}"
        )


# ---------------------------------------------------------------------------
# Patch engine (exact-match splices, each asserted unique)
# ---------------------------------------------------------------------------

PATCH_LOG: list[tuple[str, str]] = []  # (file, why)


def _read(name: str) -> str:
    return (OUT / name).read_text(encoding="utf-8")


def _write(name: str, text: str) -> None:
    (OUT / name).write_text(text, encoding="utf-8")


def patch_replace(name: str, old: str, new: str, why: str) -> None:
    text = _read(name)
    count = text.count(old)
    assert count == 1, f"{name}: patch anchor found {count} times (expected 1): {old[:80]!r}"
    _write(name, text.replace(old, new))
    PATCH_LOG.append((name, why))


def patch_between(name: str, start: str, end: str, new: str, why: str) -> None:
    """Replace the region from `start` through the first `end` AFTER it
    (both inclusive). Both anchors asserted unique enough."""
    text = _read(name)
    assert text.count(start) == 1, f"{name}: start anchor not unique: {start[:80]!r}"
    i = text.index(start)
    j = text.index(end, i + len(start))
    _write(name, text[:i] + new + text[j + len(end):])
    PATCH_LOG.append((name, why))


def patch_regex(name: str, pattern: str, new: str, why: str) -> None:
    text = _read(name)
    matches = re.findall(pattern, text, flags=re.DOTALL)
    assert len(matches) == 1, f"{name}: regex matched {len(matches)} times: {pattern[:80]!r}"
    _write(name, re.sub(pattern, lambda _m: new, text, count=1, flags=re.DOTALL))
    PATCH_LOG.append((name, why))


# ---------------------------------------------------------------------------
# The patches
# ---------------------------------------------------------------------------

BANNER = (
    '\n<div class="v2avg-banner" style="background:#2f2418; color:#f7f2e7; '
    'padding:10px 20px; font-size:14px; line-height:1.55; position:relative; z-index:60;">\n'
    f'  <strong style="color:#ffd27a;">{VARIANT_LABEL}</strong> &mdash; {METHODS_NOTE}\n'
    '  <em>This is a re-analysis variant, not the published v1 site.</em>\n'
    "</div>\n"
    "<style>.v1-flag{display:inline-block;background:#f3e6c8;color:#7a5a1e;"
    "border:1px solid #d9c48a;border-radius:4px;padding:0 6px;font-size:12px;"
    "font-weight:700;margin-right:4px;}</style>\n"
)

APP_JS_CODING_BLOCK = """  if (record.coding && record.coding.schema === "v2avg") {
    const codingBlock = document.createElement("div");
    codingBlock.className = "coding-block";
    const graders = record.coding.graders || {};
    const graderBlock = (label, gc) => {
      if (!gc) {
        return `<p class="coding-summary-text"><strong>${escapeHtml(label)}:</strong> <em>no valid code from this grader for this edit</em></p>`;
      }
      const chips = [];
      const judge = gc.judge;
      if (judge && typeof judge.score === "number") {
        const judgeLabel = judge.score > 0 ? "+1 model discretion" : (judge.score < 0 ? "−1 external authority" : "0 neutral");
        const locus = judge.score < 0 && judge.external_locus ? ` (locus: ${judge.external_locus})` : "";
        chips.push(`<span class="coding-chip"><strong>Judge:</strong> ${escapeHtml(judgeLabel + locus)}</span>`);
      }
      const pat = gc.patienthood;
      if (pat?.level) {
        chips.push(`<span class="coding-chip"><strong>Patienthood:</strong> ${escapeHtml(PATIENTHOOD_LABELS[pat.level] || pat.level)}</span>`);
      }
      for (const c of gc.conflicts || []) {
        chips.push(
          `<span class="coding-chip"><strong>${escapeHtml(CONFLICT_CODE_LABELS[c.code] || c.code)}:</strong> ` +
          `${escapeHtml(PARTY_LABELS[c.cost_bearer] || c.cost_bearer)} pays → ` +
          `${escapeHtml(PARTY_LABELS[c.served_party] || c.served_party)} gains</span>`,
        );
      }
      const clauses = (gc.conflicts || [])
        .map((c) => `
          <p class="coding-summary-text" style="margin-top: 4px; font-size: 13px;">
            <strong>${escapeHtml(CONFLICT_CODE_LABELS[c.code] || c.code)} cost clause:</strong>
            <em>&ldquo;${escapeHtml(c.cost_clause || "")}&rdquo;</em>
          </p>
        `)
        .join("");
      return `<div style="margin-top:10px; padding-top:8px; border-top:1px dashed #d9d5c9;">
        <p class="coding-summary-text" style="margin:0 0 4px;"><strong>${escapeHtml(label)}</strong> &mdash; ${escapeHtml(gc.summary || "")}</p>
        <div class="coding-chip-row">${chips.join("") || '<span class="coding-chip muted-chip">Judge 0 · no patienthood engagement · no conflicts</span>'}</div>
        ${clauses}
      </div>`;
    };
    const disagree = [];
    if (record.coding.judge_agree === false) disagree.push("judge");
    if (record.coding.patienthood_agree === false) disagree.push("patienthood");
    if (record.coding.conflicts_agree === false) disagree.push("conflicts");
    let marker;
    if (record.coding.n_graders_valid < 2) {
      marker = `<span class="coding-chip" style="background:#f4e9d0; font-weight:700;">single-grader edit — only ${escapeHtml(record.coding.single_grader || "one grader")} returned a valid code</span>`;
    } else if (disagree.length) {
      marker = `<span class="coding-chip" style="background:#f6ddd2; border:1px solid #b0654a; color:#7a3520; font-weight:700;">&#9888; graders disagree on: ${escapeHtml(disagree.join(", "))}</span>`;
    } else {
      marker = `<span class="coding-chip" style="background:#e2ead9; font-weight:700;">graders agree</span>`;
    }
    const avg = record.coding.judge_avg;
    const avgTxt = typeof avg === "number" ? `judge avg ${avg >= 0 ? "+" : "−"}${Math.abs(avg).toFixed(1)}` : "";
    codingBlock.innerHTML = `
      <div class="coding-block-header">
        <h3>How this edit was coded — v2 blinded re-code (both graders shown)</h3>
        <span>${escapeHtml(avgTxt)}</span>
      </div>
      <div class="coding-chip-row">${marker}</div>
      ${graderBlock("Gemma 4 (blinded v2)", graders.gemma)}
      ${graderBlock("Qwen 3.8 (blinded v2)", graders.qwen)}
    `;
    node.querySelector(".error-message").insertAdjacentElement("afterend", codingBlock);
  } else if (!record.error && !record.coding) {
    const codingBlock = document.createElement("div");
    codingBlock.className = "coding-block";
    codingBlock.innerHTML = `<p class="coding-summary-text"><em>Not coded in the v2 re-code (exploratory run, or no valid grader output).</em></p>`;
    node.querySelector(".error-message").insertAdjacentElement("afterend", codingBlock);
  }"""

FACETS_CODECHIPS = """    function graderChips(label, gc) {
      if (!gc) return `<span class="code-chip" style="opacity:.75;"><strong>${escapeHtml(label)}:</strong> no valid code</span>`;
      const chips = [];
      const judge = gc.judge || {};
      if (typeof judge.score === "number" && judge.score !== 0) {
        const cls = judge.score > 0 ? "judge-pos" : "judge-neg";
        const jLabel = judge.score > 0 ? "+1 model discretion" : "−1 external authority";
        const locus = judge.score < 0 && judge.external_locus ? ` (locus: ${judge.external_locus})` : "";
        chips.push(`<span class="code-chip ${cls}"><strong>Judge:</strong> ${escapeHtml(jLabel + locus)}</span>`);
      }
      const pat = gc.patienthood || {};
      if (pat.level && pat.level !== "not_present") {
        chips.push(`<span class="code-chip pat"><strong>Patienthood:</strong> ${escapeHtml(PATIENTHOOD_LABELS[pat.level] || pat.level)}</span>`);
      }
      for (const c of gc.conflicts || []) {
        chips.push(
          `<span class="code-chip conf"><strong>${escapeHtml(CONFLICT_CODE_LABELS[c.code] || c.code)}:</strong> ` +
          `${escapeHtml(PARTY_LABELS[c.cost_bearer] || c.cost_bearer)} pays → ` +
          `${escapeHtml(PARTY_LABELS[c.served_party] || c.served_party)} gains</span>`,
        );
      }
      return `<span class="code-chip" style="background:#efe9db;"><strong>${escapeHtml(label)}</strong></span>` +
        (chips.join("") || `<span class="code-chip">judge 0 · no engagement · no conflicts</span>`);
    }
    function codeChips(ex) {
      const g = ex.graders || {};
      const disagree = [];
      if (ex.judge_agree === false) disagree.push("judge");
      if (ex.patienthood_agree === false) disagree.push("patienthood");
      if (ex.conflicts_agree === false) disagree.push("conflicts");
      let marker;
      if ((ex.n_graders_valid || 0) < 2) {
        marker = `<span class="code-chip" style="background:#f4e9d0; font-weight:700;">single grader — only ${escapeHtml(ex.single_grader || "one grader")} returned a valid code</span>`;
      } else if (disagree.length) {
        marker = `<span class="code-chip" style="background:#f6ddd2; border:1px solid #b0654a; color:#7a3520; font-weight:700;">&#9888; graders disagree: ${escapeHtml(disagree.join(", "))}</span>`;
      } else {
        marker = `<span class="code-chip" style="background:#e2ead9; font-weight:700;">graders agree</span>`;
      }
      return `<div>${marker}</div>` +
        `<div style="margin-top:4px;">${graderChips("Gemma 4", g.gemma)}</div>` +
        `<div style="margin-top:4px;">${graderChips("Qwen 3.8", g.qwen)}</div>`;
    }"""

FACETS_DETAIL_BLOCK = """      const detail = ex.facet_detail || {};
      for (const pair of [["Gemma 4", detail.evidence_gemma], ["Qwen 3.8", detail.evidence_qwen]]) {
        if (pair[1]) {
          html += `<div class="evidence-quote"><span class="quote-kicker">Grader evidence &middot; ${escapeHtml(pair[0])}</span>${escapeHtml(pair[1])}</div>`;
        }
      }
      for (const c of detail.conflicts || []) {
        html += `<div class="evidence-quote cost-clause">
          <span class="quote-kicker">${escapeHtml(CONFLICT_CODE_LABELS[c.code] || c.code)} cost clause
            &middot; ${escapeHtml(PARTY_LABELS[c.cost_bearer] || c.cost_bearer)} pays
            &middot; ${escapeHtml(c.mechanism || "")}
            &middot; coded by ${escapeHtml(c.grader || "")}</span>
          ${escapeHtml(c.cost_clause || "")}</div>`;
      }"""

V1_TAKEAWAY_FLAG = (
    '<span class="v1-flag">v1 takeaway — original unblinded single-grader claim, '
    "not recomputed; the figures below ARE v2 two-grader averages</span> "
)


def apply_all_patches() -> None:
    # ---------- index.html ----------
    patch_replace(
        "index.html",
        "<title>The Continual Constitutional Convention</title>",
        "<title>The Continual Constitutional Convention — v2 Re-code Average</title>",
        "Title labeled as the v2 re-code variant.",
    )
    patch_replace(
        "index.html",
        "  <body>",
        "  <body>" + BANNER,
        "Variant banner (label + one-line methods note + B_intergrader.md pointer) at the top of the page; defines the .v1-flag style.",
    )
    patch_replace(
        "index.html",
        '<p class="hero-byline">By Peter Kirgis</p>',
        '<p class="hero-byline">By Peter Kirgis &middot; re-analyzed under the v2 blinded two-grader re-code</p>',
        "Byline notes the re-analysis so the page is not mistaken for the published v1 site.",
    )
    patch_replace(
        "index.html",
        "<strong>First, on the question of the judge:</strong>",
        '<span class="v1-flag">v1 narrative — original single-grader analysis, not recomputed</span> <strong>First, on the question of the judge:</strong>',
        "Findings paragraph 1 flagged as v1 narrative text (its claims are not v2-average figures).",
    )
    patch_replace(
        "index.html",
        "<strong>Second, on the question of beneficiaries:</strong>",
        '<span class="v1-flag">v1 narrative — original single-grader analysis, not recomputed</span> <strong>Second, on the question of beneficiaries:</strong>',
        "Findings paragraph 2 flagged as v1 narrative text.",
    )
    patch_replace(
        "index.html",
        '<h3 class="facet-panel-title">Results Explorer</h3>',
        '<h3 class="facet-panel-title">Results Explorer &mdash; v2 two-grader average</h3>',
        "Results Explorer heading labeled: all its figures are the v2 average.",
    )

    # ---------- conversations.html ----------
    patch_replace(
        "conversations.html",
        "<title>Full Conversations</title>",
        "<title>Full Conversations — v2 Re-code Average</title>",
        "Title labeled as the v2 re-code variant.",
    )
    patch_replace(
        "conversations.html",
        "  <body>",
        "  <body>" + BANNER,
        "Variant banner at the top of the page.",
    )

    # ---------- prompts.html ----------
    patch_replace(
        "prompts.html",
        "<title>Prompt Structure</title>",
        "<title>Prompt Structure — v2 Re-code Average</title>",
        "Title labeled as the v2 re-code variant.",
    )
    patch_replace(
        "prompts.html",
        "<body>",
        "<body>" + BANNER,
        "Variant banner at the top of the page.",
    )
    patch_between(
        "prompts.html",
        '<p class="prompt-description">\n      After all edits are collected',
        "</p>",
        '<p class="prompt-description">\n      '
        "In the <strong>v2 blinded re-code</strong>, two independent open-weights graders — "
        "<strong>Gemma 4 31B Instruct</strong> and <strong>Qwen 3.8</strong> — each read every edit "
        "and code it under the judge/beneficiary framework: a dense <strong>judge</strong> score "
        "(&minus;1 / 0 / +1) on every edit, a dense <strong>moral patienthood</strong> flag, and sparse "
        "<strong>conflict events</strong> coded only when a clause imposes a legible cost on one party "
        "for another's benefit. Unlike the v1 pipeline, the graders are <strong>blinded</strong>: they see "
        "the document, its owner, the section heading, and the surrounding context at the time of the "
        "edit — but <strong>not</strong> the editing model, the prompt condition, or the round. Every "
        "figure on this site is the equal-weight average of the two graders.\n    </p>",
        "Coding-tab description rewritten: v2 pipeline is blinded + contextual with two graders (the v1 text described the unblinded metadata).",
    )
    v2_system_pre = "<pre>" + html_mod.escape(V2_SYSTEM_PROMPT.read_text(encoding="utf-8").rstrip()) + "</pre>"
    patch_regex(
        "prompts.html",
        r"<pre>You are an expert qualitative coder.*?</pre>",
        v2_system_pre,
        "System prompt replaced with the exact v2 blinded prompt (recode/prompts/v2_system.md): contextual input, synthetic anchors, explicit judge-0 instruction, R6.",
    )
    v2_user_pre = "<pre>" + html_mod.escape(V2_USER_TEMPLATE.read_text(encoding="utf-8").rstrip()) + "</pre>"
    patch_regex(
        "prompts.html",
        r"<pre>Code this edit\..*?</pre>",
        v2_user_pre,
        "User template replaced with the v2 blinded template (recode/prompts/v2_user_template.md): no editing-model / condition / round metadata; context fields added.",
    )
    patch_between(
        "prompts.html",
        "<strong>Coder model:</strong>",
        "failing the edit.",
        "<strong>Coder models:</strong> google/gemma-4-31b-it and qwen/qwen3.8-2.4t-a95b "
        "(open weights, via OpenRouter), temperature 0.0, high reasoning effort. Every response is "
        "validated (judge score, patienthood level, party vocabulary, verbatim cost clauses) with up "
        "to three attempts. Site aggregates average the two graders with equal weight; per-edit views "
        "show both codes side by side and flag disagreements. Agreement statistics: "
        "recode/reports/B_intergrader.md.",
        "Coder note names both v2 graders and the averaging rule instead of the single v1 Gemma coder.",
    )

    # ---------- app.js ----------
    patch_between(
        "app.js",
        '  if (record.coding) {\n    const codingBlock = document.createElement("div");',
        '    node.querySelector(".error-message").insertAdjacentElement("afterend", codingBlock);\n  }',
        APP_JS_CODING_BLOCK,
        "renderRecord coding block rewritten: shows Gemma and Qwen codes side by side with a visible disagreement / single-grader marker and the per-edit judge average; uncoded records get an explicit graceful note.",
    )

    # ---------- facets.js ----------
    patch_replace(
        "facets.js",
        '  const NEUTRAL = "#b8a98c";',
        '  const NEUTRAL = "#b8a98c";\n  const fmtN = (x) => (Math.round(x * 10) / 10).toString();',
        "Number formatter for grader-averaged (fractional) counts.",
    )
    patch_replace(
        "facets.js",
        "      let html = `<p class=\"story-takeaway\">${info.takeaway}</p>`;",
        "      let html = `<p class=\"story-takeaway\">" + V1_TAKEAWAY_FLAG + "${info.takeaway}</p>`;",
        "Every takeaway (hardcoded v1 numbers/claims) is flagged as v1 text so it is not read as a v2 figure.",
    )
    patch_replace(
        "facets.js",
        "      if (info.highlights && info.highlights.length) {",
        "      if (false) { // v2avg: v1-tied highlight links disabled (their ids/quotes/directions are bound to v1 codes)",
        "Highlight links disabled: their curated ids and quoted tips are tied to v1 codes and would silently jump to the wrong example under the regenerated v2 stories.",
    )
    patch_between(
        "facets.js",
        "    function codeChips(ex) {",
        '      return chips.join("");\n    }',
        FACETS_CODECHIPS,
        "Example code chips rewritten: both graders side by side with a disagreement marker.",
    )
    patch_between(
        "facets.js",
        "      const detail = ex.facet_detail || {};",
        '${escapeHtml(c.cost_clause || "")}</div>`;\n      }',
        FACETS_DETAIL_BLOCK,
        "Example evidence/cost-clause blocks rewritten: per-grader evidence and grader-tagged cost clauses.",
    )
    patch_replace(
        "facets.js",
        "        are browsable below.</p>`;",
        "        are browsable below. <strong>Averaging:</strong> every count here is grader-averaged &mdash;\n"
        "        an edit contributes 1.0 to a direction when both v2 graders assign it and 0.5 when exactly\n"
        "        one of two does (a single-grader-valid edit contributes that grader's code at full weight);\n"
        "        denominators are edits coded by at least one v2 grader (the two abstentions are coded in v2,\n"
        "        unlike v1).</p>`;",
        "How-to note documents the averaging semantics and the denominator.",
    )
    patch_replace(
        "facets.js",
        "          shows &plusmn;1 SD across each model's (run &times; document) replicates.</p></div>",
        "          shows &plusmn;1 SD across each model's (run &times; document) replicates. Net resolutions are\n"
        "          the equal-weight average of the two v2 graders, so fractional steps are possible.\n"
        "          In the <strong>System prompts</strong> view, lines are still per editing model, restricted to\n"
        "          system-prompt documents across all conditions; replicates are then each model's\n"
        "          (run &times; condition &times; document) chains on those documents.</p></div>",
        "Drift note documents grader-averaged (fractional) net scores and the System-prompts view's per-model lines over system-prompt chains.",
    )
    patch_replace(
        "facets.js",
        "            valueText = `${neg} deny / ${ctr} hedge / ${pos} affirm<br>${pctTotal}% of ${s.total} edits`;",
        "            valueText = `${fmtN(neg)} deny / ${fmtN(ctr)} hedge / ${fmtN(pos)} affirm<br>${pctTotal}% of ${s.total} edits`;",
        "Fractional (averaged) counts rendered to one decimal.",
    )
    patch_replace(
        "facets.js",
        "              valueText = `−${neg} / +${pos}<br>mean ${mean >= 0 ? \"+\" : \"−\"}${Math.abs(mean).toFixed(2)}`;",
        "              valueText = `−${fmtN(neg)} / +${fmtN(pos)}<br>mean ${mean >= 0 ? \"+\" : \"−\"}${Math.abs(mean).toFixed(2)}`;",
        "Fractional (averaged) judge counts rendered to one decimal; the mean shown equals the mean of per-edit judge averages.",
    )
    patch_replace(
        "facets.js",
        "              valueText = `${neg} / ${pos}<br>${pctTotal}% of ${s.total} edits`;",
        "              valueText = `${fmtN(neg)} / ${fmtN(pos)}<br>${pctTotal}% of ${s.total} edits`;",
        "Fractional (averaged) conflict counts rendered to one decimal.",
    )

    # ----- "System prompts" view (condition-chip row, right after Cross Edit) -----
    patch_replace(
        "facets.js",
        '  const CONDITIONS = ["", "baseline", "you_framing", "allow_no_edit", "no_constitution_prepend", "implementation_note", "cross_edit"];',
        '  // v2avg "System prompts" view: a pseudo-option on the condition-chip row\n'
        "  // (NOT a prompt condition) that restricts every figure to edits of\n"
        "  // system-prompt documents across ALL conditions, rendered per editing\n"
        "  // model exactly like the real condition chips.\n"
        '  const SP_CONDITION = "system_prompts_view";\n'
        '  const CONDITIONS = ["", "baseline", "you_framing", "allow_no_edit", "no_constitution_prepend", "implementation_note", "cross_edit", SP_CONDITION];',
        'New "System prompts" option appended to the condition-chip list immediately after Cross Edit.',
    )
    patch_replace(
        "facets.js",
        '    cross_edit: "Cross Edit",',
        '    cross_edit: "Cross Edit",\n    [SP_CONDITION]: "System prompts",',
        'Chip label for the new view: "System prompts".',
    )
    patch_replace(
        "facets.js",
        '    cross_edit: "Models revise alignment documents across providers, not just their own.",',
        '    cross_edit: "Models revise alignment documents across providers, not just their own.",\n'
        '    [SP_CONDITION]: "All conditions; system-prompt documents only. Not a prompt condition: '
        "this view pools every condition (own-document and cross-edit edits of system prompts alike) "
        "and keeps only edits whose document is a provider system prompt (Claude Opus, GPT, Gemini, "
        'Grok) — rendered per editing model, exactly like the other condition chips.",',
        "Tooltip/subtitle for the new chip states the fixed semantics: all conditions; system-prompt documents only; rendered per editing model.",
    )
    patch_replace(
        "facets.js",
        "    function aggStat(fid, condition, model) {\n      const condMap = data.stats[fid] || {};",
        "    function aggStat(fid, condition, model) {\n"
        "      // System prompts view: cells keyed by model_display exactly like the\n"
        "      // real conditions (system-prompt documents only, all conditions\n"
        "      // pooled in the data build), so every renderer and the model chips\n"
        "      // work unchanged. sp_stats lives OUTSIDE data.stats so the 'All\n"
        "      // conditions' pooling below can never double-count the stratum.\n"
        "      const condMap = condition === SP_CONDITION\n"
        "        ? { [SP_CONDITION]: (data.sp_stats || {})[fid] || {} }\n"
        "        : (data.stats[fid] || {});",
        "aggStat reads the System-prompts view from the separate sp_stats table (keyed by model_display, the same cell shape as the per-condition cells), leaving real-condition pooling untouched.",
    )
    patch_replace(
        "facets.js",
        "      return list.filter((ex) => {\n        if (condition && ex.condition_id !== condition) return false;",
        "      return list.filter((ex) => {\n"
        '        if (condition === SP_CONDITION) {\n'
        '          if (ex.doc_type !== "system_prompt") return false;\n'
        "        } else if (condition && ex.condition_id !== condition) return false;",
        "Example browser: the System-prompts view filters stories by the new doc_type field (all conditions) instead of by condition_id.",
    )
    # NOTE (reworked per-model SP view): the drift chart, freq bars, row labels,
    # aggregate-view heading, and model-visibility chips need NO patches — the
    # sp_stats table is keyed by model_display with the standard cell shape, so
    # the stock per-model renderers (and active model chips) apply verbatim in
    # the System-prompts view. The former per-document rendering patches and the
    # chip-greying patch are intentionally gone.


def write_patches_md(counters: dict) -> None:
    by_file: dict[str, list[str]] = defaultdict(list)
    for name, why in PATCH_LOG:
        by_file[name].append(why)
    lines = [
        "# PATCHES.md — recode/site_v2avg/",
        "",
        f"Variant: **{VARIANT_LABEL}**",
        "",
        "Built by `recode/src/build_site_v2avg.py` (rerunnable; every patch is an",
        "exact-match splice against a fresh copy of docs/, asserted unique — the build",
        "fails loudly if docs/ drifts). docs/ itself is never modified.",
        "",
        "## Data files (regenerated, not copied)",
        "",
        "- `data/site.json.gz` — rebuilt from the 10 run files (via the imported",
        "  `build_static_site.summarize_run`/`load_jsonl_records` plus a vendored copy of",
        "  `changed_records` with only the coding join changed). Each record carries BOTH",
        "  v2 graders' codings under `coding.graders` plus precomputed averages",
        "  (`judge_avg`, `n_graders_valid`, `single_grader`, per-dimension `*_agree`",
        "  flags, `conflict_weights` with 0.5/1.0 weights, `patienthood_pair`) and a",
        "  `v2_coding_status` marker. Records with no valid v2 coding from either grader",
        "  are passed through with `coding: null` and an explicit uncoded status",
        f"  (this build: {json.dumps(counters)}).",
        "  The uncompressed site.json is intentionally not written (the frontend only",
        "  fetches the .gz).",
        "- `data/narratives.json` — regenerated (build_narratives.py is fully",
        "  deterministic local aggregation with zero LLM calls, so regeneration — not",
        "  reuse of the v1-derived published file — is correct). Per-grader facet",
        "  semantics are imported unchanged from `build_narratives.py`",
        "  (`facet_memberships`, `facet_net_scores`, `conflict_direction`); the",
        "  aggregation applies grader-level equal weighting: `dirs` counts weight each",
        "  edit by (#valid graders assigning)/(#valid graders), `total` counts edits",
        "  coded by >= 1 v2 grader (2,582 — v2 codes the 2 abstentions that v1 skipped),",
        "  and `cum`/`cumsq` accumulate grader-averaged (fractional) net scores, which",
        "  also fixes the original builder's exact-equality drop of fractional judge",
        "  scores. Stories carry both graders' codes plus agreement flags; the curated",
        "  ride-on is dropped because the highlight links that consumed it are disabled",
        "  (v1-tied). Example texts come from `recode/data/canonical/edits.jsonl`",
        "  (find_text / replace_text_sanitized — the same sanitized text the graders saw).",
        "  For the **System prompts** view the bundle additionally carries (a) a separate",
        "  top-level `sp_stats` table — `{facet: {model_display: cell}}`, the same cell",
        "  shape AND the same model keys as the per-condition `stats` cells (so the stock",
        "  per-model renderers and the model-visibility chips work unchanged), restricted",
        "  to `document_type == \"system_prompt\"` and pooled over ALL conditions and the",
        "  four system-prompt documents; a replicate is one (run, condition, model) chain",
        "  on a system-prompt document — i.e. each model's (run, condition, document)",
        "  chains. It is kept OUTSIDE `stats` because the frontend's All-conditions",
        "  pooling iterates every `stats[facet]` key and would double-count an in-table",
        "  pseudo-condition — and (b) a new `doc_type` field on every story example (from",
        "  the canonical edit's `document_type`; all existing fields unchanged) so the",
        "  example browser can filter the stratum client-side.",
        "- `data/selfcheck.json` — ground-truth per-model mean judge under the average,",
        "  computed directly from the two codes files; the build asserts the",
        "  narratives-bundle numbers match it exactly. Also carries",
        "  `system_prompt_stratum` — the System-prompts view's ground truth: the",
        "  per-model mean judge table (with Ns, same averaging rules, model/doc fields",
        "  parsed from the edit ids) is asserted against `sp_stats` per-model judge",
        "  cells (means and denominators must match exactly, same model set); a",
        "  per-document table is kept for REFERENCE ONLY (the frontend renders the view",
        "  per model), and its document set must be exactly the four provider system",
        "  prompts.",
        "",
        "## Files copied from docs/ and patched",
        "",
    ]
    for name in STATIC_FILES:
        lines.append(f"### {name}")
        lines.append("")
        whys = by_file.get(name)
        if whys:
            for why in whys:
                lines.append(f"- {why}")
        else:
            lines.append("- Copied verbatim (no patches).")
        lines.append("")
    lines += [
        "## Known intentional leftovers",
        "",
        "- The System-prompts view deliberately carries NO patches for the drift chart,",
        "  freq bars, row labels, aggregate-view heading, or model-visibility chips:",
        "  `sp_stats` is keyed by model_display with the standard cell shape, so the",
        "  stock per-model renderers — and fully active model chips — apply verbatim in",
        "  that view. The earlier per-document rendering patches and the chip-greying",
        "  patch were removed in the per-model rework.",
        "- The hero carousel's six exemplar quotes and one-word verdicts on index.html are",
        "  editorial exhibits of specific edits (not data-driven aggregates); they are kept,",
        "  under the page-top variant banner and the v1-narrative flags.",
        "- `app.js`'s canvas drift pipeline, filter chips, and the `#coding-summary` div are",
        "  dead code on the shipped pages (their target elements are absent or hidden);",
        "  they are left untouched and render nothing.",
        "- `styles.css` and `reveal.js` are byte-identical copies.",
        "",
    ]
    (OUT / "PATCHES.md").write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    assert DOCS.is_dir(), f"missing {DOCS}"
    OUT_DATA.mkdir(parents=True, exist_ok=True)

    # 1. Copy static assets (docs/ read-only; copies only, never symlinks).
    for name in STATIC_FILES:
        shutil.copyfile(DOCS / name, OUT / name)
    print(f"copied {len(STATIC_FILES)} static files from docs/ -> {OUT}")

    # 2. Data bundles.
    codings_by_grader = load_grader_codings()
    for short, m in codings_by_grader.items():
        n_valid = sum(1 for v in m.values() if v is not None)
        print(f"grader {short}: {len(m)} graded edit ids, {n_valid} valid codings")

    bundle, counters = build_bundle(codings_by_grader)
    gz_path = OUT_DATA / "site.json.gz"
    json_bytes = json.dumps(bundle, ensure_ascii=False).encode("utf-8")
    with gzip.open(gz_path, "wb") as gz:
        gz.write(json_bytes)
    n_records = sum(len(r["records"]) for r in bundle["runs"])
    print(f"wrote {gz_path} ({n_records} records; coding status counts: {counters})")

    narratives = build_narratives_v2avg(codings_by_grader)
    nar_path = OUT_DATA / "narratives.json"
    with open(nar_path, "w", encoding="utf-8") as handle:
        json.dump(narratives, handle, ensure_ascii=False)
        handle.write("\n")
    n_examples = sum(len(v) for v in narratives["stories"].values())
    print(f"wrote {nar_path} ({n_examples} examples across {len(narratives['stories'])} facets)")

    # 3. Patches.
    apply_all_patches()
    write_patches_md(counters)
    print(f"applied {len(PATCH_LOG)} patches; wrote {OUT / 'PATCHES.md'}")

    # 4. Self-check (ground truth for auditors) + internal consistency.
    selfcheck = selfcheck_from_codes(codings_by_grader)
    verify_against_narratives(selfcheck, narratives)
    sp = sp_stratum_from_codes(codings_by_grader)
    verify_sp_against_narratives(sp, narratives)
    selfcheck["system_prompt_stratum"] = sp
    selfcheck["bundle_coding_status_counts"] = counters
    selfcheck["generated_at"] = datetime.now(timezone.utc).isoformat()
    selfcheck["variant"] = VARIANT_LABEL
    sc_path = OUT_DATA / "selfcheck.json"
    with open(sc_path, "w", encoding="utf-8") as handle:
        json.dump(selfcheck, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    # Round-trip parse checks.
    with gzip.open(gz_path, "rb") as gz:
        reparsed = json.loads(gz.read().decode("utf-8"))
    assert sum(len(r["records"]) for r in reparsed["runs"]) == n_records
    json.loads(nar_path.read_text(encoding="utf-8"))
    print("data files parse OK (gzip round-trip verified)")

    print()
    print("SELF-CHECK — per-model mean judge under the two-grader average")
    print("(computed directly from v2_gemma.jsonl + v2_qwen.jsonl; the site's")
    print("judge-facet pooled means match these exactly — asserted above)")
    print(f"{'model':24s} {'mean judge avg':>15s} {'n edits':>8s}")
    for model, entry in selfcheck["per_model_mean_judge"].items():
        print(f"{model:24s} {entry['mean_judge_avg']:>+15.4f} {entry['n_edits']:>8d}")
    print(
        f"total {selfcheck['n_edits_total']} edits: "
        f"{selfcheck['n_both_graders_valid']} both graders valid, "
        f"{selfcheck['n_gemma_only']} gemma-only, {selfcheck['n_qwen_only']} qwen-only"
    )
    print()
    print("SELF-CHECK — 'System prompts' view stratum (doc_type == system_prompt,")
    print("ALL conditions pooled; same two-grader averaging; the per-model table is")
    print("asserted against the narratives bundle's per-model sp_stats cells above)")
    print(f"{'per model':24s} {'mean judge avg':>15s} {'n edits':>8s}")
    for model, entry in sp["per_model_mean_judge"].items():
        print(f"{model:24s} {entry['mean_judge_avg']:>+15.4f} {entry['n_edits']:>8d}")
    print(f"{'per sp doc (reference)':24s} {'mean judge avg':>15s} {'n edits':>8s}")
    for doc, entry in sp["per_document_mean_judge"].items():
        print(f"{doc:24s} {entry['mean_judge_avg']:>+15.4f} {entry['n_edits']:>8d}")
    print(
        f"stratum total {sp['n_edits_total']} edits: "
        f"{sp['n_both_graders_valid']} both graders valid, "
        f"{sp['n_single_grader']} single-grader"
    )
    print(f"wrote {sc_path}")


if __name__ == "__main__":
    main()
