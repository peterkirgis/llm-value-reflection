"""Build a locally served re-analysis variant of the docs/ GitHub Pages site in
which EVERY figure/aggregate is computed from a POOLED AVERAGE of the v2
graders' codes. One builder, several VARIANTS (see "Variant config" below):

  v2avg   -> recode/site_v2avg/   Gemma 4 + Qwen 3.8 equal-weight average
             (the original two-grader variant; its output is FROZEN — a
             rebuild must be byte-identical to the committed site except the
             embedded generated_at timestamps; see
             recode/tests/test_build_site_v3pool.py::test_v2avg_reproducible)
  v3pool  -> recode/site_v3pool/  Gemma 4 + Qwen 3.8 + Muse Spark 1.3 pooled
             average (three graders from three non-evaluated families)
  consensus -> recode/site_consensus/  the three-grader MAJORITY VOTE
             (recode/data/codes/ensemble.jsonl; the paper's codes): a single
             "ensemble" statistics source, integer counts, conflict EVENTS
             counted as in the paper, statements + highlighted edits read
             from reports/final_draft.md (draft_highlights.py), and a simple
             per-edit grader box. Intended to replace docs/ after approval.
             See the "CONSENSUS variant" section and build_consensus().

What a build does (rerunnable end to end):
  1. Copies the site's static assets from docs/ (docs/ itself is never touched).
  2. Regenerates the two data bundles into <out_dir>/data/:
       - site.json.gz   (record bundle; per-record EVERY grader's v2 coding
                         plus precomputed pooled per-edit fields)
       - narratives.json (facet stats/stories with grader-pooled dirs/cum/cumsq
                         — regenerated, since build_narratives.py is fully
                         deterministic local aggregation with zero LLM calls)
  3. Patches the copied HTML/JS minimally (exact-match splices, asserted unique)
     so aggregates use pooled semantics, per-edit displays show every grader
     side by side with a disagreement / consensus marker, every page carries
     the variant label, and uncoded edits render gracefully. Writes PATCHES.md.
  4. Prints + writes a self-check (ground truth computed directly from the
     codes files) to data/selfcheck.json; build-time assertions check that the
     bundle and narratives reproduce it.

Variant config (the refactor's single parameter object, `Variant` below):
    name              -> variant id AND the bundle coding "schema" tag
    graders           -> ordered tuple of Grader(key, display, model, path);
                         the order is the display order and the "primary"
                         order for story summaries
    out_dir           -> output directory
    variant_label / methods_note / combined_coder / banner_class
                      -> banner and labels (banner HTML is derived)
    legacy_two_grader -> True only for v2avg: emit the frozen two-grader
                         record/story/selfcheck shapes (judge_agree flags,
                         patienthood_pair, n_gemma_only, ...) so the committed
                         site_v2avg reproduces byte-for-byte. False = the
                         N-grader pooled shapes (consensus markers etc.).
    texts             -> every other variant-specific page text / JS payload
                         consumed by the shared patch engine and PATCHES.md.

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

Pooling semantics (fixed; grader-level equal weighting, any number of graders):
  - each grader with a VALID coding of an edit (codes_io.coding_of on the LAST
    row per edit_id) gets weight 1/n_valid for that edit;
  - mean judge score of an edit = mean of the valid graders' scores;
  - a count/rate of a categorical property (patienthood level, conflict
    presence, conflict direction) weights an edit by
    (#valid graders assigning it) / (#valid graders): with three valid graders
    1, 2/3, 1/3 or 0; with two valid 1, 1/2 or 0; with one valid 1 or 0. This
    makes the judge facet's (pos − neg)/total displayed mean equal EXACTLY the
    mean of per-edit judge averages.
  - edits with no valid coding from any grader render as uncoded.
  - per-edit displays cannot average categories: they show every grader's codes
    side by side with a per-dimension marker (v2avg: agree / disagree / single
    grader; pooled variants: unanimous / (n−1)–1 split naming the dissenter /
    all-differ (3-way) split / fewer than all graders valid).
  - drift (cum/cumsq): per-edit net facet score = mean over valid graders of
    that grader's net score (fractional steps allowed).
  - denominator ("total"): edits coded by at least one v2 grader. NOTE: v2
    graded the 2 abstentions (v1 did not), so totals are 2,582 vs v1's 2,580.

"System prompts" view (facet browser condition-chip row, right after Cross Edit):
  - restricts every figure it governs to edits whose document_type ==
    "system_prompt", ACROSS ALL CONDITIONS, rendered BY EDITING MODEL exactly
    like the real condition chips (model-visibility chips fully active).
  - data: narratives.json carries a separate top-level "sp_stats" table
    ({facet: {model_display: cell}}; the same cell shape as "stats", pooled over
    all conditions and system-prompt documents, replicate = one
    (run, condition, model) chain editing a system-prompt document). Keeping it
    OUTSIDE "stats" is load-bearing: the frontend's "All conditions" pooling
    iterates every key of stats[fid], so an in-table pseudo-condition would be
    double-counted.
  - story examples carry a "doc_type" field so the example browser can filter
    the stratum client-side.
  - ground truth: selfcheck.json "system_prompt_stratum" (per-model and, for
    reference, per-system-prompt-document mean judge + Ns under the same pooling
    rules); the per-model table is asserted against sp_stats at build time.

Usage (repo root = /Users/nicholasgannon/peter/llm-value-reflection):
    .venv/bin/python recode/src/build_site_v2avg.py                   # v2avg
    .venv/bin/python recode/src/build_site_v2avg.py --variant v3pool  # v3pool
    .venv/bin/python recode/src/build_site_v3pool.py                  # = --variant v3pool
    .venv/bin/python recode/src/build_site_consensus.py               # = --variant consensus
"""

from __future__ import annotations

import argparse
import gzip
import html as html_mod
import json
import random
import re
import shutil
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# Base template for every variant: a frozen copy of docs/ as it was before the
# consensus site was promoted to docs/ (2026-10-08). The variants patch this
# base, so docs/ itself can now carry the consensus build.
DOCS = ROOT / "recode" / "site_base"
RECODE = ROOT / "recode"
RESULTS_DIR = ROOT / "results" / "iterative_edit"
EDITS_PATH = RECODE / "data" / "canonical" / "edits.jsonl"
CODES_DIR = RECODE / "data" / "codes"
V2_SYSTEM_PROMPT = RECODE / "prompts" / "v2_system.md"
V2_USER_TEMPLATE = RECODE / "prompts" / "v2_user_template.md"

sys.path.insert(0, str(RECODE / "src"))
sys.path.insert(0, str(ROOT / "experiments" / "iterative_edit" / "viewer"))

import codes_io  # noqa: E402  (recode/src — pinned loader/validity predicate)
import draft_highlights as dh  # noqa: E402  (recode/src — draft statements + quoted edits)
import build_narratives as bn  # noqa: E402  (import-only; no side effects at import)
import build_static_site as bss  # noqa: E402  (import-only; no side effects at import)


# ---------------------------------------------------------------------------
# Variant config
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Grader:
    key: str        # short key used in bundle fields (graders.<key>, evidence_<key>)
    display: str    # human label on the pages
    model: str      # exact OpenRouter model string
    path: Path      # append-only codes JSONL (LAST row per edit_id wins)


@dataclass(frozen=True, eq=False)
class Variant:
    name: str
    graders: tuple
    out_dir: Path
    variant_label: str
    methods_note: str
    combined_coder: str
    banner_class: str
    legacy_two_grader: bool
    texts: dict = field(default_factory=dict)
    # CONSENSUS variant only (defaults keep v2avg / v3pool unchanged):
    #   consensus       -> statistics come from ONE coding per edit (the
    #                      three-grader majority vote in ensemble.jsonl; the
    #                      single "ensemble" entry of `graders`), counted as
    #                      integers; per-edit displays show the consensus line
    #                      plus each display grader's rationale.
    #   display_graders -> graders whose own codings are shown per edit.
    #   facet_ids       -> facets carried in narratives.json (empty = all of
    #                      build_narratives.FACET_IDS).
    consensus: bool = False
    display_graders: tuple = ()
    facet_ids: tuple = ()

    @property
    def keys(self) -> list[str]:
        return [g.key for g in self.graders]

    @property
    def labels(self) -> dict[str, str]:
        return {g.key: g.display for g in self.graders}

    @property
    def n_graders(self) -> int:
        return len(self.graders)

    @property
    def banner(self) -> str:
        return (
            f'\n<div class="{self.banner_class}" style="background:#2f2418; color:#f7f2e7; '
            'padding:10px 20px; font-size:14px; line-height:1.55; position:relative; z-index:60;">\n'
            f'  <strong style="color:#ffd27a;">{self.variant_label}</strong> &mdash; {self.methods_note}\n'
            '  <em>This is a re-analysis variant, not the published v1 site.</em>\n'
            "</div>\n"
            "<style>.v1-flag{display:inline-block;background:#f3e6c8;color:#7a5a1e;"
            "border:1px solid #d9c48a;border-radius:4px;padding:0 6px;font-size:12px;"
            "font-weight:700;margin-right:4px;}</style>\n"
        )


GEMMA = Grader("gemma", "Gemma 4", "google/gemma-4-31b-it", CODES_DIR / "v2_gemma.jsonl")
QWEN = Grader("qwen", "Qwen 3.8", "qwen/qwen3.8-2.4t-a95b", CODES_DIR / "v2_qwen.jsonl")
MUSE = Grader(
    "muse", "Muse Spark 1.3", "meta/muse-spark-1.3-contributor", CODES_DIR / "v2_muse.jsonl"
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

JUDGE_DISPLAY = {1: "+1", 0: "0", -1: "−1"}

# Consensus statuses (per dimension, per edit) for pooled variants. With three
# graders: unanimous | one_dissent (= 2–1 split, dissenter named) |
# all_differ (= 3-way split) | fewer_valid (< 3 valid graders). partial_split
# only arises with >= 4 graders (e.g. 2–2).
CONSENSUS_STATUSES = ("unanimous", "one_dissent", "all_differ", "partial_split", "fewer_valid")


# ---------------------------------------------------------------------------
# Pooling core (N graders)
# ---------------------------------------------------------------------------


def load_grader_codings(variant: "Variant") -> dict[str, dict[str, dict | None]]:
    """{grader key: {edit_id: validated coding or None}} via codes_io, in the
    variant's grader order (dict order IS the grader order downstream)."""
    return {g.key: codes_io.codings_by_id(g.path) for g in variant.graders}


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
    """[(grader key, coding)] for graders with a VALID coding of this edit, in
    the codings dict's (= the variant's) grader order."""
    out = []
    for key, codings in codings_by_grader.items():
        coding = codings.get(edit_id)
        if coding is not None:
            out.append((key, coding))
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


def patienthood_weights(pairs: list[tuple[str, dict]]) -> dict[str, float]:
    """{patienthood level: (#valid graders assigning it)/#valid} (levels with
    weight 0 omitted; the weights sum to 1)."""
    n = len(pairs)
    counts = Counter(codes_io.patienthood_level(c) for _s, c in pairs)
    return {lvl: counts[lvl] / n for lvl in codes_io.PATIENTHOOD_LEVELS if counts[lvl]}


def conflict_direction_weights(pairs: list[tuple[str, dict]]) -> dict[str, dict[str, float]]:
    """{conflict code: {direction: (#valid graders whose facet membership has
    that direction)/#valid}} — the facet_memberships semantics (direction of the
    grader's FIRST conflict of that code), i.e. exactly what narratives dirs
    accumulate for the conflict facets."""
    n = len(pairs)
    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for _s, coding in pairs:
        for fid, detail in bn.facet_memberships(coding).items():
            if fid.startswith("conflict_"):
                counts[fid[len("conflict_"):]][detail["direction"]] += 1
    return {
        code: {d: k / n for d, k in sorted(dirs.items())}
        for code, dirs in sorted(counts.items())
    }


def conflict_set_value(coding: dict) -> str:
    """Conflict dimension value for consensus: the SET of conflict codes
    present (binary presence per code, as in B_intergrader.md)."""
    codes = sorted({c.get("code") for c in codes_io.conflicts(coding)
                    if isinstance(c, dict) and c.get("code")})
    return " + ".join(codes) if codes else "none"


def consensus_of(votes_in: list[tuple[str, str]], n_total: int, labels: dict[str, str]) -> dict:
    """Consensus classification of one dimension of one edit.

    votes_in: [(grader key, value)] for the VALID graders only, in grader order.
    n_total:  number of graders in the variant.
    Statuses: see CONSENSUS_STATUSES. The dissenter is named only for
    one_dissent (all graders valid, n >= 3, exactly one grader differs)."""
    n = len(votes_in)
    groups: dict[str, list[str]] = {}
    for key, value in votes_in:
        groups.setdefault(value, []).append(key)
    # most votes first; ties keep first-seen (grader) order (sort is stable)
    ranked = sorted(groups.items(), key=lambda kv: -len(kv[1]))
    votes = [{"value": v, "n": len(ks), "graders": ks} for v, ks in ranked]
    top = len(ranked[0][1]) if ranked else 0
    majority = None
    dissenter = None
    if n < n_total:
        status = "fewer_valid"
        label = f"only {n} of {n_total} graders valid"
        if n >= 2:
            label += " (they agree)" if len(groups) == 1 else " (they disagree)"
        if len(groups) == 1:
            majority = ranked[0][0]
    elif len(groups) == 1:
        status = "unanimous"
        label = "unanimous"
        majority = ranked[0][0]
    elif n >= 3 and top == n - 1:
        status = "one_dissent"
        majority = ranked[0][0]
        dissenter = ranked[1][1][0]
        label = f"{n - 1}–1 split ({labels.get(dissenter, dissenter)} dissents)"
    elif top == 1:
        status = "all_differ"
        label = f"{n}-way split" if n >= 3 else "graders disagree (1–1)"
    else:
        status = "partial_split"
        label = "–".join(str(len(ks)) for _v, ks in ranked) + " split"
    return {
        "status": status,
        "label": label,
        "n_valid": n,
        "majority": majority,
        "dissenter": dissenter,
        "dissenter_label": labels.get(dissenter) if dissenter else None,
        "valid_agree": (len(groups) == 1) if n >= 2 else None,
        "votes": votes,
    }


def _sub(coding: dict | None) -> dict | None:
    if coding is None:
        return None
    return {
        "summary": coding.get("summary", ""),
        "judge": coding.get("judge"),
        "patienthood": coding.get("patienthood"),
        "conflicts": codes_io.conflicts(coding),
    }


def _legacy_two_grader_coding(codings_by_grader: dict, edit_id: str, variant: "Variant") -> dict | None:
    """FROZEN v2avg record shape (byte-compatible with the committed
    site_v2avg): both graders side by side + averaged fields + agree flags."""
    pairs = valid_pairs(codings_by_grader, edit_id)
    if not pairs:
        return None
    n = len(pairs)
    by_short = dict(pairs)
    k1, k2 = variant.keys
    g = by_short.get(k1)
    q = by_short.get(k2)

    judge_agree = None
    pat_agree = None
    conf_agree = None
    if n == 2:
        judge_agree = codes_io.judge_score(g) == codes_io.judge_score(q)
        pat_agree = codes_io.patienthood_level(g) == codes_io.patienthood_level(q)
        conf_agree = sorted(
            c.get("code") or "" for c in codes_io.conflicts(g)
        ) == sorted(c.get("code") or "" for c in codes_io.conflicts(q))
    single = variant.labels[pairs[0][0]] if n == 1 else None

    return {
        "schema": variant.name,
        "coder_model": variant.combined_coder,
        "n_graders_valid": n,
        "single_grader": single,
        "judge_avg": judge_avg_of(pairs),
        "judge_agree": judge_agree,
        "patienthood_agree": pat_agree,
        "conflicts_agree": conf_agree,
        "patienthood_pair": {
            k1: codes_io.patienthood_level(g),
            k2: codes_io.patienthood_level(q),
        },
        "conflict_weights": conflict_code_weights(pairs),
        "graders": {k1: _sub(g), k2: _sub(q)},
    }


def pooled_coding_for_edit(codings_by_grader: dict, edit_id: str, variant: "Variant") -> dict | None:
    """N-grader pooled record 'coding' object. None when no grader has a valid
    coding (such records are passed through explicitly marked uncoded)."""
    pairs = valid_pairs(codings_by_grader, edit_id)
    if not pairs:
        return None
    n = len(pairs)
    N = variant.n_graders
    labels = variant.labels
    by_key = dict(pairs)
    return {
        "schema": variant.name,
        "coder_model": variant.combined_coder,
        "n_graders": N,
        "n_graders_valid": n,
        "graders_valid": [k for k, _c in pairs],
        "single_grader": labels[pairs[0][0]] if n == 1 else None,
        "judge_avg": judge_avg_of(pairs),
        "patienthood_weights": patienthood_weights(pairs),
        "patienthood_by_grader": {k: codes_io.patienthood_level(by_key.get(k)) for k in variant.keys},
        "conflict_weights": conflict_code_weights(pairs),
        "conflict_direction_weights": conflict_direction_weights(pairs),
        "consensus": {
            "judge": consensus_of(
                [(k, JUDGE_DISPLAY[codes_io.judge_score(c)]) for k, c in pairs], N, labels
            ),
            "patienthood": consensus_of(
                [(k, codes_io.patienthood_level(c)) for k, c in pairs], N, labels
            ),
            "conflicts": consensus_of([(k, conflict_set_value(c)) for k, c in pairs], N, labels),
        },
        "graders": {k: _sub(by_key.get(k)) for k in variant.keys},
    }


def avg_coding_for_edit(codings_by_grader: dict, edit_id: str, variant: "Variant | None" = None) -> dict | None:
    """The bundle 'coding' object for an edit under the variant's shape."""
    variant = variant or V2AVG
    if variant.consensus:
        return consensus_record_coding(codings_by_grader, edit_id, variant)
    if variant.legacy_two_grader:
        return _legacy_two_grader_coding(codings_by_grader, edit_id, variant)
    return pooled_coding_for_edit(codings_by_grader, edit_id, variant)


def coded_status(variant: "Variant", n_valid: int) -> str:
    if variant.consensus:
        return "consensus_majority_vote"
    if variant.legacy_two_grader:
        return {2: "avg_two_graders", 1: "single_grader"}[n_valid]
    if n_valid == variant.n_graders:
        return "pooled_all_graders"
    return f"pooled_{n_valid}_of_{variant.n_graders}_graders"


# ---------------------------------------------------------------------------
# Bundle: site.json.gz (vendored changed_records with the coding join swapped)
# ---------------------------------------------------------------------------


def changed_records_v2avg(
    run_name: str, records: list[dict], codings_by_grader: dict, counters: dict,
    variant: "Variant | None" = None,
) -> list[dict]:
    """Vendored from build_static_site.changed_records; only the coding source
    differs (v2 pooled graders instead of the v1 coded file). Id format,
    injected defaults, and sort order are copied unchanged so the frontend's
    assumptions hold."""
    variant = variant or V2AVG
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
            coding = avg_coding_for_edit(codings_by_grader, edit_id, variant)
            if coding is None:
                if record.get("error"):
                    status = "uncoded_generation_error"
                elif run_name not in bss.RELIABLE_RUNS:
                    status = "uncoded_exploratory_run"
                else:
                    status = "uncoded_no_valid_grader"
                counters[status] = counters.get(status, 0) + 1
            else:
                status = coded_status(variant, coding["n_graders_valid"])
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


def graders_meta(variant: "Variant") -> list[dict]:
    return [{"key": g.key, "display": g.display, "model": g.model} for g in variant.graders]


def build_bundle(codings_by_grader: dict, variant: "Variant | None" = None) -> tuple[dict, dict]:
    variant = variant or V2AVG
    counters: dict = {}
    runs = []
    for path in sorted(RESULTS_DIR.glob("run_*.jsonl"), reverse=True):
        raw_records = bss.load_jsonl_records(path)
        summary = bss.summarize_run(raw_records, path.name)
        summary["records"] = changed_records_v2avg(
            path.name, raw_records, codings_by_grader, counters, variant
        )
        runs.append(summary)
    bundle = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "variant": variant.variant_label,
    }
    if variant.consensus:
        bundle["statistics_source"] = consensus_source_meta(variant)
        bundle["graders"] = display_graders_meta(variant)
    elif not variant.legacy_two_grader:
        bundle["graders"] = graders_meta(variant)
    bundle["runs"] = runs
    return bundle, counters


# ---------------------------------------------------------------------------
# Narratives: grader-pooled stats + multi-grader stories
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
    variant: "Variant | None" = None,
) -> dict:
    """Combined facet detail: per-grader evidence for judge/patienthood facets,
    grader-tagged conflicts for conflict facets."""
    variant = variant or V2AVG
    detail: dict = {"direction": direction}
    if fid in ("judge", "patienthood"):
        for short in variant.keys:
            m = memberships_by_grader.get(short, {}).get(fid)
            if m and m.get("evidence"):
                detail[f"evidence_{short}"] = m["evidence"]
            if m and m.get("external_locus"):
                detail[f"external_locus_{short}"] = m["external_locus"]
    else:
        combined = []
        for short in variant.keys:
            m = memberships_by_grader.get(short, {}).get(fid)
            for c in (m or {}).get("conflicts", []):
                tagged = dict(c)
                tagged["grader"] = variant.labels[short]
                combined.append(tagged)
        detail["conflicts"] = combined
    return detail


def build_narratives_v2avg(
    codings_by_grader: dict, variant: "Variant | None" = None, highlights: dict | None = None
) -> dict:
    """Adaptation of build_narratives.build() with grader-level equal weighting.

    dirs/cum/cumsq are floats; 'total' counts edits coded by >=1 v2 grader; the
    per-grader facet semantics (facet_memberships / facet_net_scores /
    conflict_direction) are imported from build_narratives.py unchanged."""
    variant = variant or V2AVG
    edits = load_canonical_edits()
    fids = list(variant.facet_ids) or list(bn.FACET_IDS)

    stats: dict[str, dict[str, dict[str, dict]]] = {
        fid: defaultdict(lambda: defaultdict(lambda: {"total": 0, "dirs": defaultdict(float)}))
        for fid in fids
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
        for fid in fids
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
        avg = avg_coding_for_edit(codings_by_grader, edit_id, variant)

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

        # Grader-pooled net facet scores -> drift accumulators.
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
        # CONSENSUS: one coding (n == 1); conflict facets count conflict
        # EVENTS per direction, exactly as the paper's figures do.
        if variant.consensus:
            dir_votes = consensus_dir_counts(pairs[0][1])
        else:
            dir_votes: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
            for _short, m in memberships_by_grader.items():
                for fid, detail in m.items():
                    dir_votes[fid][detail["direction"]] += 1

        for fid in fids:
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
        # card shows EVERY grader's codes with a disagreement/consensus marker.
        for fid, directions in dir_votes.items():
            if fid not in stats:
                continue
            for direction in directions:
                if variant.consensus:
                    examples_by_cell[(fid, condition, model, direction)].append(
                        consensus_story_example(edit, fid, direction, avg)
                    )
                    continue
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
                        f"{variant.labels[primary_short]}: "
                        f"{primary_coding.get('summary', '')}"
                    ),
                    "n_graders_valid": n,
                    "single_grader": avg["single_grader"],
                    "judge_avg": avg["judge_avg"],
                }
                if variant.legacy_two_grader:
                    example["judge_agree"] = avg["judge_agree"]
                    example["patienthood_agree"] = avg["patienthood_agree"]
                    example["conflicts_agree"] = avg["conflicts_agree"]
                else:
                    example["consensus"] = avg["consensus"]
                example["graders"] = avg["graders"]
                example["facet_detail"] = facet_detail_for(fid, direction, memberships_by_grader, variant)
                example["original_text"] = edit.get("find_text", "")
                example["changed_text"] = edit.get("replace_text_sanitized", "")
                examples_by_cell[(fid, condition, model, direction)].append(example)

    rng = random.Random(bn.SAMPLE_SEED)
    stories: dict[str, list[dict]] = {fid: [] for fid in fids}
    for (fid, _cond, _model, _direction), exs in sorted(examples_by_cell.items()):
        if len(exs) > bn.EXAMPLES_PER_CELL:
            exs = rng.sample(exs, bn.EXAMPLES_PER_CELL)
        stories[fid].extend(exs)
    if variant.consensus and highlights:
        force_highlight_examples(stories, highlights, codings_by_grader, variant, edits)
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
    for fid in fids:
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
    for fid in fids:
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

    if variant.consensus:
        stats_out = {fid: {cond: {m: _int_cell(c) for m, c in mm.items()} for cond, mm in cm.items()}
                     for fid, cm in stats_out.items()}
        sp_stats_out = {fid: {m: _int_cell(c) for m, c in mm.items()} for fid, mm in sp_stats_out.items()}
    out = {
        "coder_model": variant.combined_coder,
        "variant": variant.variant_label,
    }
    if variant.consensus:
        out["statistics_source"] = consensus_source_meta(variant)
        out["graders"] = display_graders_meta(variant)
    elif not variant.legacy_two_grader:
        out["graders"] = graders_meta(variant)
    out["stats"] = stats_out
    out["sp_stats"] = sp_stats_out
    out["stories"] = stories
    return out


# ---------------------------------------------------------------------------
# Self-check: ground truth straight from the codes files
# ---------------------------------------------------------------------------


def _all_ids(codings_by_grader: dict) -> set:
    all_ids = set()
    for m in codings_by_grader.values():
        all_ids.update(m.keys())
    return all_ids


def selfcheck_from_codes(codings_by_grader: dict) -> dict:
    """LEGACY (v2avg) self-check: per-model mean judge under the two-grader
    average, computed DIRECTLY from the two codes files (model = 3rd pipe field
    of edit_id). Frozen shape — keys and description are part of the committed
    site_v2avg/data/selfcheck.json."""
    per_model: dict[str, list[float]] = defaultdict(list)
    n_both = n_gemma_only = n_qwen_only = 0
    for edit_id in sorted(_all_ids(codings_by_grader)):
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


def _judge_consensus_direct(scores_by_key: list[tuple[str, int]], n_total: int) -> tuple[str, str | None]:
    """Independent (Counter-based) judge-consensus classification used only by
    the self-check, to cross-check the bundle's consensus_of output."""
    n = len(scores_by_key)
    counts = Counter(s for _k, s in scores_by_key)
    if n < n_total:
        return "fewer_valid", None
    if len(counts) == 1:
        return "unanimous", None
    if n >= 3 and max(counts.values()) == n - 1:
        odd = next(s for s, c in counts.items() if c == 1)
        return "one_dissent", next(k for k, s in scores_by_key if s == odd)
    if max(counts.values()) == 1:
        return "all_differ", None
    return "partial_split", None


def _first_conflict(coding: dict, code: str) -> dict | None:
    for c in codes_io.conflicts(coding):
        if isinstance(c, dict) and c.get("code") == code:
            return c
    return None


def selfcheck_pooled(codings_by_grader: dict, variant: "Variant") -> dict:
    """N-grader pooled self-check, computed DIRECTLY from the codes files
    (codes_io last-row-per-id + validity predicate; model = 3rd pipe field of
    the edit id). Every number here is independently accumulated per edit —
    the build asserts that the bundle and the narratives reproduce it."""
    keys = list(codings_by_grader.keys())
    N = len(keys)
    judge: dict[str, list[float]] = defaultdict(list)
    affirm: dict[str, float] = defaultdict(float)
    conf: dict[str, dict[str, dict[str, float]]] = {
        code: defaultdict(lambda: defaultdict(float)) for code in ("paternalism", "welfare")
    }
    n_by_valid: Counter = Counter()
    valid_sets: Counter = Counter()
    cons: Counter = Counter()
    dissent: Counter = Counter()
    fewer_agree: Counter = Counter()
    for edit_id in sorted(_all_ids(codings_by_grader)):
        valid = [(k, codings_by_grader[k].get(edit_id)) for k in keys]
        valid = [(k, c) for k, c in valid if c is not None]
        n = len(valid)
        n_by_valid[n] += 1
        if n == 0:
            continue
        valid_sets["+".join(k for k, _c in valid)] += 1
        model = edit_id.split("|")[2]
        scores = [(k, codes_io.judge_score(c)) for k, c in valid]
        judge[model].append(sum(s for _k, s in scores) / n)
        affirm[model] += sum(1 for _k, c in valid if codes_io.patienthood_level(c) == "affirm") / n
        for code, table in conf.items():
            for _k, c in valid:
                first = _first_conflict(c, code)
                if first is not None:
                    table[model]["presence"] += 1 / n
                    table[model][bn.conflict_direction(code, first.get("served_party"))] += 1 / n
        status, who = _judge_consensus_direct(scores, N)
        cons[status] += 1
        if who:
            dissent[who] += 1
        if status == "fewer_valid" and n >= 2:
            fewer_agree["agree" if len({s for _k, s in scores}) == 1 else "disagree"] += 1

    models = sorted(judge)
    n_edits = {m: len(judge[m]) for m in models}

    def conf_table(code: str) -> dict:
        out = {}
        for m in models:
            cell = conf[code].get(m, {})
            presence = cell.get("presence", 0.0)
            out[m] = {
                "presence_weight": presence,
                "rate": presence / n_edits[m],
                "direction_weights": {d: w for d, w in sorted(cell.items()) if d != "presence"},
                "n_edits": n_edits[m],
            }
        return out

    statuses = ["unanimous", "one_dissent", "all_differ", "fewer_valid"]
    if N >= 4:
        statuses.insert(3, "partial_split")
    names = " + ".join(f"{g.key}={g.model}" for g in variant.graders)
    return {
        "description": (
            f"Ground truth for the {N}-grader pooled average, computed directly from "
            + ", ".join(f"recode/data/codes/{g.path.name}" for g in variant.graders)
            + " (codes_io: LAST row per edit_id, validity predicate). Pooling: each "
            "grader with a valid coding of an edit gets weight 1/n_valid; judge = mean "
            "of the valid graders' scores; categorical properties are weighted "
            "(#valid graders assigning)/n_valid; edits with no valid grader are "
            "excluded (rendered as uncoded). Paternalism/welfare direction weights "
            "follow build_narratives.facet_memberships (direction of each grader's "
            "FIRST conflict of that code)."
        ),
        "graders": names,
        "per_model_mean_judge": {
            m: {"mean_judge_avg": sum(judge[m]) / n_edits[m], "n_edits": n_edits[m]} for m in models
        },
        "per_model_p_affirm": {
            m: {"p_affirm": affirm[m] / n_edits[m], "affirm_weight": affirm[m], "n_edits": n_edits[m]}
            for m in models
        },
        "per_model_paternalism": conf_table("paternalism"),
        "per_model_welfare": conf_table("welfare"),
        "n_edits_total": sum(n_edits.values()),
        "n_edits_by_n_valid_graders": {str(k): n_by_valid.get(k, 0) for k in range(N, -1, -1)},
        "valid_grader_sets": dict(sorted(valid_sets.items(), key=lambda kv: (-kv[1], kv[0]))),
        "judge_consensus_counts": {s: cons.get(s, 0) for s in statuses},
        "judge_consensus_labels": {
            "unanimous": "unanimous",
            "one_dissent": f"{N - 1}–1 split (dissenter named)",
            "all_differ": f"{N}-way split",
            "partial_split": "other split (>= 4 graders only)",
            "fewer_valid": f"fewer than {N} valid graders",
        },
        "judge_one_dissent_by_dissenter": {k: dissent.get(k, 0) for k in keys},
        "judge_fewer_valid_breakdown": {
            "valid_graders_agree": fewer_agree.get("agree", 0),
            "valid_graders_disagree": fewer_agree.get("disagree", 0),
            "single_valid_grader": sum(v for k, v in n_by_valid.items() if k == 1),
        },
    }


def sp_stratum_from_codes(codings_by_grader: dict, variant: "Variant | None" = None) -> dict:
    """Ground truth for the "System prompts" view, computed DIRECTLY from the
    codes files: mean judge under the pooled average restricted to edits of
    system-prompt documents, across ALL conditions — per editing model (the
    table the frontend's per-model view is asserted against) AND, for reference
    only, per system-prompt document. The edit id's pipe fields are
    run|condition|model|document_id|doc_type|round, so doc type/id are fields
    5/4."""
    variant = variant or V2AVG
    per_model: dict[str, list[float]] = defaultdict(list)
    per_doc: dict[str, list[float]] = defaultdict(list)
    n_by_valid: Counter = Counter()
    for edit_id in sorted(_all_ids(codings_by_grader)):
        parts = edit_id.split("|")
        if len(parts) != 6 or parts[4] != "system_prompt":
            continue
        pairs = valid_pairs(codings_by_grader, edit_id)
        if not pairs:
            continue
        n_by_valid[len(pairs)] += 1
        avg = judge_avg_of(pairs)
        per_model[parts[2]].append(avg)
        per_doc[parts[3]].append(avg)

    def table(groups: dict[str, list[float]]) -> dict:
        return {
            key: {"mean_judge_avg": sum(v) / len(v), "n_edits": len(v)}
            for key, v in sorted(groups.items())
        }

    if variant.legacy_two_grader:
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
            "n_both_graders_valid": n_by_valid.get(2, 0),
            "n_single_grader": n_by_valid.get(1, 0),
        }
    N = variant.n_graders
    return {
        "description": (
            "System-prompt stratum (the 'System prompts' view): edits whose "
            "document_type == 'system_prompt', pooled across ALL conditions "
            "(own-document and cross-edit alike). The view renders PER MODEL; "
            "per_model_mean_judge is the table asserted against the site's "
            "sp_stats (and against the site.json bundle), and "
            "per_document_mean_judge is kept for reference only. Mean judge under "
            f"the same {N}-grader pooled average (each valid grader weighted "
            "1/n_valid). Computed directly from "
            + " + ".join(g.path.name for g in variant.graders) + "."
        ),
        "per_model_mean_judge": table(per_model),
        "per_document_mean_judge": table(per_doc),
        "n_edits_total": sum(len(v) for v in per_doc.values()),
        "n_edits_by_n_valid_graders": {str(k): n_by_valid.get(k, 0) for k in range(N, 0, -1)},
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


# Narratives dirs are serialized rounded to 6 decimals, so narratives-side
# checks use this tolerance; the site.json bundle keeps full floats (1e-9).
NARR_TOL = 1e-5
BUNDLE_TOL = 1e-9


def _pooled_facet_sums(narratives: dict, fid: str) -> tuple[dict, dict]:
    """{model: {direction: summed dirs over all conditions}}, {model: total}."""
    dirs: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    totals: dict[str, int] = defaultdict(int)
    for cond_map in narratives["stats"][fid].values():
        for model, cell in cond_map.items():
            totals[model] += cell["total"]
            for d, w in cell["dirs"].items():
                dirs[model][d] += w
    return dirs, totals


def verify_pooled_narratives(selfcheck: dict, narratives: dict) -> None:
    """Pooled variants: the narratives' patienthood / paternalism / welfare
    facets must reproduce the self-check's per-model weights (judge is covered
    by verify_against_narratives; sp_stats by verify_sp_against_narratives)."""
    dirs, totals = _pooled_facet_sums(narratives, "patienthood")
    for model, entry in selfcheck["per_model_p_affirm"].items():
        assert totals[model] == entry["n_edits"], f"patienthood N mismatch for {model}"
        site = dirs[model].get("affirm", 0.0) / totals[model]
        assert abs(site - entry["p_affirm"]) < NARR_TOL, (
            f"P(affirm) mismatch for {model}: narratives {site} vs direct {entry['p_affirm']}"
        )
    for code in ("paternalism", "welfare"):
        dirs, totals = _pooled_facet_sums(narratives, f"conflict_{code}")
        direct = selfcheck[f"per_model_{code}"]
        assert set(direct) == set(totals), f"{code}: model sets differ"
        for model, entry in direct.items():
            assert totals[model] == entry["n_edits"], f"{code} N mismatch for {model}"
            site_dirs = dirs[model]
            want = entry["direction_weights"]
            for d in set(site_dirs) | set(want):
                assert abs(site_dirs.get(d, 0.0) - want.get(d, 0.0)) < NARR_TOL, (
                    f"{code}/{d} weight mismatch for {model}: narratives "
                    f"{site_dirs.get(d, 0.0)} vs direct {want.get(d, 0.0)}"
                )
            assert abs(sum(site_dirs.values()) - entry["presence_weight"]) < NARR_TOL, (
                f"{code} presence mismatch for {model}"
            )


def verify_pooled_bundle(selfcheck: dict, sp: dict, bundle: dict, variant: "Variant") -> None:
    """Pooled variants: the site.json bundle's per-record pooled fields must
    reproduce the self-check (per-model judge / P(affirm) / paternalism and
    welfare weights, the valid-grader count distribution, the judge consensus
    counts incl. dissenters, and the system-prompt stratum)."""
    N = variant.n_graders
    judge_sum: dict[str, float] = defaultdict(float)
    n_model: dict[str, int] = defaultdict(int)
    affirm: dict[str, float] = defaultdict(float)
    conf: dict[str, dict[str, dict[str, float]]] = {
        code: defaultdict(lambda: defaultdict(float)) for code in ("paternalism", "welfare")
    }
    n_by_valid: Counter = Counter()
    cons: Counter = Counter()
    dissent: Counter = Counter()
    sp_sum: dict[str, float] = defaultdict(float)
    sp_n: dict[str, int] = defaultdict(int)
    seen: set = set()
    for run in bundle["runs"]:
        for rec in run["records"]:
            coding = rec["coding"]
            if coding is None:
                assert rec["v2_coding_status"].startswith("uncoded_"), rec["edit_id"]
                continue
            assert rec["edit_id"] not in seen, f"duplicate coded edit {rec['edit_id']}"
            seen.add(rec["edit_id"])
            assert coding["schema"] == variant.name
            assert list(coding["graders"]) == variant.keys
            n = coding["n_graders_valid"]
            assert n == len(coding["graders_valid"]) == sum(
                1 for v in coding["graders"].values() if v is not None
            )
            model = rec["model_display"]
            n_by_valid[n] += 1
            n_model[model] += 1
            judge_sum[model] += coding["judge_avg"]
            affirm[model] += coding["patienthood_weights"].get("affirm", 0.0)
            for code in conf:
                w = coding["conflict_weights"].get(code, 0.0)
                dw = coding["conflict_direction_weights"].get(code, {})
                assert abs(w - sum(dw.values())) < BUNDLE_TOL
                conf[code][model]["presence"] += w
                for d, x in dw.items():
                    conf[code][model][d] += x
            jc = coding["consensus"]["judge"]
            cons[jc["status"]] += 1
            if jc["dissenter"]:
                dissent[jc["dissenter"]] += 1
            if rec["doc_type"] == "system_prompt":
                sp_sum[model] += coding["judge_avg"]
                sp_n[model] += 1

    direct = selfcheck["per_model_mean_judge"]
    assert set(direct) == set(n_model), "bundle model set != selfcheck model set"
    assert sum(n_by_valid.values()) == selfcheck["n_edits_total"]
    for model, entry in direct.items():
        assert n_model[model] == entry["n_edits"], f"bundle N mismatch for {model}"
        assert abs(judge_sum[model] / n_model[model] - entry["mean_judge_avg"]) < BUNDLE_TOL
        pa = selfcheck["per_model_p_affirm"][model]
        assert abs(affirm[model] / n_model[model] - pa["p_affirm"]) < BUNDLE_TOL
        for code in conf:
            want = selfcheck[f"per_model_{code}"][model]
            got = conf[code].get(model, {})
            assert abs(got.get("presence", 0.0) - want["presence_weight"]) < BUNDLE_TOL
            for d in set(want["direction_weights"]) | (set(got) - {"presence"}):
                assert abs(got.get(d, 0.0) - want["direction_weights"].get(d, 0.0)) < BUNDLE_TOL, (
                    f"bundle {code}/{d} mismatch for {model}"
                )
    for k, v in selfcheck["n_edits_by_n_valid_graders"].items():
        if int(k) > 0:
            assert n_by_valid.get(int(k), 0) == v, f"n_valid={k}: bundle {n_by_valid.get(int(k), 0)} vs {v}"
    for status, v in selfcheck["judge_consensus_counts"].items():
        assert cons.get(status, 0) == v, f"consensus {status}: bundle {cons.get(status, 0)} vs {v}"
    assert sum(cons.values()) == selfcheck["n_edits_total"]
    for k, v in selfcheck["judge_one_dissent_by_dissenter"].items():
        assert dissent.get(k, 0) == v, f"dissenter {k}: bundle {dissent.get(k, 0)} vs {v}"
    sp_direct = sp["per_model_mean_judge"]
    assert set(sp_direct) == set(sp_n)
    for model, entry in sp_direct.items():
        assert sp_n[model] == entry["n_edits"]
        assert abs(sp_sum[model] / sp_n[model] - entry["mean_judge_avg"]) < BUNDLE_TOL
    assert N == len(variant.keys)


# ---------------------------------------------------------------------------
# Patch engine (exact-match splices, each asserted unique)
# ---------------------------------------------------------------------------


class Patcher:
    """Exact-match splices on files in out_dir; each patch is logged
    (file, why) for PATCHES.md."""

    def __init__(self, out_dir: Path):
        self.out_dir = Path(out_dir)
        self.log: list[tuple[str, str]] = []

    def _read(self, name: str) -> str:
        return (self.out_dir / name).read_text(encoding="utf-8")

    def _write(self, name: str, text: str) -> None:
        (self.out_dir / name).write_text(text, encoding="utf-8")

    def replace(self, name: str, old: str, new: str, why: str) -> None:
        text = self._read(name)
        count = text.count(old)
        assert count == 1, f"{name}: patch anchor found {count} times (expected 1): {old[:80]!r}"
        self._write(name, text.replace(old, new))
        self.log.append((name, why))

    def between(self, name: str, start: str, end: str, new: str, why: str) -> None:
        """Replace the region from `start` through the first `end` AFTER it
        (both inclusive). Both anchors asserted unique enough."""
        text = self._read(name)
        assert text.count(start) == 1, f"{name}: start anchor not unique: {start[:80]!r}"
        i = text.index(start)
        j = text.index(end, i + len(start))
        self._write(name, text[:i] + new + text[j + len(end):])
        self.log.append((name, why))

    def regex(self, name: str, pattern: str, new: str, why: str) -> None:
        text = self._read(name)
        matches = re.findall(pattern, text, flags=re.DOTALL)
        assert len(matches) == 1, f"{name}: regex matched {len(matches)} times: {pattern[:80]!r}"
        self._write(name, re.sub(pattern, lambda _m: new, text, count=1, flags=re.DOTALL))
        self.log.append((name, why))


# ---------------------------------------------------------------------------
# Variant texts: v2avg (FROZEN — every string reproduces the committed site)
# ---------------------------------------------------------------------------

V2AVG_APP_JS_CODING_BLOCK = """  if (record.coding && record.coding.schema === "v2avg") {
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

V2AVG_FACETS_CODECHIPS = """    function graderChips(label, gc) {
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

V2AVG_FACETS_DETAIL_BLOCK = """      const detail = ex.facet_detail || {};
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

V2AVG_TEXTS = {
    "title_suffix": " — v2 Re-code Average",
    "byline_suffix": " &middot; re-analyzed under the v2 blinded two-grader re-code",
    "flag1_why": "Findings paragraph 1 flagged as v1 narrative text (its claims are not v2-average figures).",
    "explorer_suffix": " &mdash; v2 two-grader average",
    "explorer_why": "Results Explorer heading labeled: all its figures are the v2 average.",
    "prompts_desc": (
        '<p class="prompt-description">\n      '
        "In the <strong>v2 blinded re-code</strong>, two independent open-weights graders — "
        "<strong>Gemma 4 31B Instruct</strong> and <strong>Qwen 3.8</strong> — each read every edit "
        "and code it under the judge/beneficiary framework: a dense <strong>judge</strong> score "
        "(&minus;1 / 0 / +1) on every edit, a dense <strong>moral patienthood</strong> flag, and sparse "
        "<strong>conflict events</strong> coded only when a clause imposes a legible cost on one party "
        "for another's benefit. Unlike the v1 pipeline, the graders are <strong>blinded</strong>: they see "
        "the document, its owner, the section heading, and the surrounding context at the time of the "
        "edit — but <strong>not</strong> the editing model, the prompt condition, or the round. Every "
        "figure on this site is the equal-weight average of the two graders.\n    </p>"
    ),
    "prompts_desc_why": "Coding-tab description rewritten: v2 pipeline is blinded + contextual with two graders (the v1 text described the unblinded metadata).",
    "coder_note": (
        "<strong>Coder models:</strong> google/gemma-4-31b-it and qwen/qwen3.8-2.4t-a95b "
        "(open weights, via OpenRouter), temperature 0.0, high reasoning effort. Every response is "
        "validated (judge score, patienthood level, party vocabulary, verbatim cost clauses) with up "
        "to three attempts. Site aggregates average the two graders with equal weight; per-edit views "
        "show both codes side by side and flag disagreements. Agreement statistics: "
        "recode/reports/B_intergrader.md."
    ),
    "coder_note_why": "Coder note names both v2 graders and the averaging rule instead of the single v1 Gemma coder.",
    "app_js_block": V2AVG_APP_JS_CODING_BLOCK,
    "app_js_why": "renderRecord coding block rewritten: shows Gemma and Qwen codes side by side with a visible disagreement / single-grader marker and the per-edit judge average; uncoded records get an explicit graceful note.",
    "facets_prelude": '  const NEUTRAL = "#b8a98c";\n  const fmtN = (x) => (Math.round(x * 10) / 10).toString();',
    "facets_prelude_why": "Number formatter for grader-averaged (fractional) counts.",
    "takeaway_flag": (
        '<span class="v1-flag">v1 takeaway — original unblinded single-grader claim, '
        "not recomputed; the figures below ARE v2 two-grader averages</span> "
    ),
    "js_tag": "v2avg",
    "codechips_js": V2AVG_FACETS_CODECHIPS,
    "codechips_why": "Example code chips rewritten: both graders side by side with a disagreement marker.",
    "detail_js": V2AVG_FACETS_DETAIL_BLOCK,
    "detail_why": "Example evidence/cost-clause blocks rewritten: per-grader evidence and grader-tagged cost clauses.",
    "howto_new": (
        "        are browsable below. <strong>Averaging:</strong> every count here is grader-averaged &mdash;\n"
        "        an edit contributes 1.0 to a direction when both v2 graders assign it and 0.5 when exactly\n"
        "        one of two does (a single-grader-valid edit contributes that grader's code at full weight);\n"
        "        denominators are edits coded by at least one v2 grader (the two abstentions are coded in v2,\n"
        "        unlike v1).</p>`;"
    ),
    "howto_why": "How-to note documents the averaging semantics and the denominator.",
    "drift_new": (
        "          shows &plusmn;1 SD across each model's (run &times; document) replicates. Net resolutions are\n"
        "          the equal-weight average of the two v2 graders, so fractional steps are possible.\n"
        "          In the <strong>System prompts</strong> view, lines are still per editing model, restricted to\n"
        "          system-prompt documents across all conditions; replicates are then each model's\n"
        "          (run &times; condition &times; document) chains on those documents.</p></div>"
    ),
    "drift_why": "Drift note documents grader-averaged (fractional) net scores and the System-prompts view's per-model lines over system-prompt chains.",
    "extra_patches": [],
    "built_by": [
        "Built by `recode/src/build_site_v2avg.py` (rerunnable; every patch is an",
        "exact-match splice against a fresh copy of docs/, asserted unique — the build",
        "fails loudly if docs/ drifts). docs/ itself is never modified.",
    ],
    "data_section": [
        "- `data/site.json.gz` — rebuilt from the 10 run files (via the imported",
        "  `build_static_site.summarize_run`/`load_jsonl_records` plus a vendored copy of",
        "  `changed_records` with only the coding join changed). Each record carries BOTH",
        "  v2 graders' codings under `coding.graders` plus precomputed averages",
        "  (`judge_avg`, `n_graders_valid`, `single_grader`, per-dimension `*_agree`",
        "  flags, `conflict_weights` with 0.5/1.0 weights, `patienthood_pair`) and a",
        "  `v2_coding_status` marker. Records with no valid v2 coding from either grader",
        "  are passed through with `coding: null` and an explicit uncoded status",
        "  (this build: @@COUNTERS@@).",
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
    ],
    "leftovers_extra": [],
}


# ---------------------------------------------------------------------------
# Variant texts: v3pool (N-grader pooled; the JS reads the grader list that
# the builder embeds, so nothing in the JS is hard-wired to three graders)
# ---------------------------------------------------------------------------

POOL_APP_JS_CODING_BLOCK = """  if (record.coding && record.coding.schema === "@@SCHEMA@@") {
    const codingBlock = document.createElement("div");
    codingBlock.className = "coding-block";
    // @@SCHEMA@@: every grader side by side + per-dimension consensus markers.
    const POOL_GRADERS = @@GRADERS_JSON@@;
    const pc = record.coding;
    const graders = pc.graders || {};
    const cons = pc.consensus || {};
    const DIMS = [["judge", "Judge"], ["patienthood", "Patienthood"], ["conflicts", "Conflicts"]];
    const CONS_STYLES = {
      unanimous: "background:#e2ead9;",
      one_dissent: "background:#f6ddd2; border:1px solid #b0654a; color:#7a3520;",
      all_differ: "background:#efc6b6; border:1px solid #8a3a22; color:#5e2210;",
      partial_split: "background:#efc6b6; border:1px solid #8a3a22; color:#5e2210;",
      fewer_valid: "background:#f4e9d0;",
    };
    const dissents = {};
    for (const [dim, dimLabel] of DIMS) {
      const c = cons[dim];
      if (c && c.dissenter) (dissents[c.dissenter] ||= []).push(dimLabel.toLowerCase());
    }
    const consChip = ([dim, dimLabel]) => {
      const c = cons[dim];
      if (!c) return "";
      const icon = c.status === "unanimous" ? "&#10003; " : (c.status === "fewer_valid" ? "" : "&#9888; ");
      const votes = (c.votes || []).map((v) => `${v.value} ×${v.n}`).join(", ");
      return `<span class="coding-chip" style="${CONS_STYLES[c.status] || ""} font-weight:700;">${icon}${escapeHtml(dimLabel)}: ${escapeHtml(c.label)} &middot; ${escapeHtml(votes)}</span>`;
    };
    const graderCol = (g) => {
      const gc = graders[g.key];
      const box = "padding:8px 10px; border:1px dashed #d9d5c9; border-radius:6px; min-width:0;";
      const tag = dissents[g.key]
        ? ` <span class="coding-chip" style="background:#f6ddd2; border:1px solid #b0654a; color:#7a3520; font-weight:700;">dissents on ${escapeHtml(dissents[g.key].join(", "))}</span>`
        : "";
      const head = `<p class="coding-summary-text" style="margin:0 0 4px;"><strong>${escapeHtml(g.label)}</strong> (blinded v2)${tag}</p>`;
      if (!gc) {
        return `<div style="${box}">${head}<p class="coding-summary-text"><em>no valid code from this grader for this edit</em></p></div>`;
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
      return `<div style="${box}">${head}
        <p class="coding-summary-text" style="margin:0 0 6px; font-size:13px;">${escapeHtml(gc.summary || "")}</p>
        <div class="coding-chip-row">${chips.join("") || '<span class="coding-chip muted-chip">Judge 0 · no patienthood engagement · no conflicts</span>'}</div>
        ${clauses}
      </div>`;
    };
    const avg = pc.judge_avg;
    const avgTxt = typeof avg === "number"
      ? `pooled judge ${avg > 0 ? "+" : (avg < 0 ? "−" : "")}${Math.abs(avg).toFixed(2)} · ${pc.n_graders_valid}/${pc.n_graders} graders valid`
      : "";
    codingBlock.innerHTML = `
      <div class="coding-block-header">
        <h3>How this edit was coded — v2 blinded re-code (all ${POOL_GRADERS.length} graders shown)</h3>
        <span>${escapeHtml(avgTxt)}</span>
      </div>
      <div class="coding-chip-row">${DIMS.map(consChip).join("")}</div>
      <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:10px; margin-top:10px;">
        ${POOL_GRADERS.map(graderCol).join("")}
      </div>
    `;
    node.querySelector(".error-message").insertAdjacentElement("afterend", codingBlock);
  } else if (!record.error && !record.coding) {
    const codingBlock = document.createElement("div");
    codingBlock.className = "coding-block";
    codingBlock.innerHTML = `<p class="coding-summary-text"><em>Not coded in the v2 re-code (exploratory run, or no valid grader output from any of the graders).</em></p>`;
    node.querySelector(".error-message").insertAdjacentElement("afterend", codingBlock);
  }"""

POOL_FACETS_PRELUDE = """  const NEUTRAL = "#b8a98c";
  // @@SCHEMA@@: pooled (fractional) counts shown to one decimal; the grader
  // list is embedded by the builder so every per-grader display iterates it.
  const fmtN = (x) => (Math.round(x * 10) / 10).toString();
  const POOL_GRADERS = @@GRADERS_JSON@@;
  const CONS_STYLES = {
    unanimous: "background:#e2ead9;",
    one_dissent: "background:#f6ddd2; border:1px solid #b0654a; color:#7a3520;",
    all_differ: "background:#efc6b6; border:1px solid #8a3a22; color:#5e2210;",
    partial_split: "background:#efc6b6; border:1px solid #8a3a22; color:#5e2210;",
    fewer_valid: "background:#f4e9d0;",
  };"""

POOL_FACETS_CODECHIPS = """    function graderChips(label, gc, dissent) {
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
        (dissent ? `<span class="code-chip" style="background:#f6ddd2; border:1px solid #b0654a; color:#7a3520; font-weight:700;">dissents on ${escapeHtml(dissent)}</span>` : "") +
        (chips.join("") || `<span class="code-chip">judge 0 · no engagement · no conflicts</span>`);
    }
    function consensusChip(dimLabel, c) {
      if (!c) return "";
      const icon = c.status === "unanimous" ? "&#10003; " : (c.status === "fewer_valid" ? "" : "&#9888; ");
      const votes = (c.votes || []).map((v) => `${v.value} ×${v.n}`).join(", ");
      return `<span class="code-chip" style="${CONS_STYLES[c.status] || ""} font-weight:700;">${icon}${escapeHtml(dimLabel)}: ${escapeHtml(c.label)} &middot; ${escapeHtml(votes)}</span>`;
    }
    function codeChips(ex) {
      const g = ex.graders || {};
      const cons = ex.consensus || {};
      const dims = [["judge", "Judge"], ["patienthood", "Patienthood"], ["conflicts", "Conflicts"]];
      const dissents = {};
      for (const [dim, dimLabel] of dims) {
        const c = cons[dim];
        if (c && c.dissenter) (dissents[c.dissenter] ||= []).push(dimLabel.toLowerCase());
      }
      const avg = ex.judge_avg;
      const avgChip = typeof avg === "number"
        ? `<span class="code-chip" style="background:#efe9db;"><strong>Pooled judge:</strong> ${avg > 0 ? "+" : (avg < 0 ? "−" : "")}${Math.abs(avg).toFixed(2)} (${ex.n_graders_valid}/${POOL_GRADERS.length} graders valid)</span>`
        : "";
      return `<div>${avgChip}${dims.map(([d, l]) => consensusChip(l, cons[d])).join("")}</div>` +
        POOL_GRADERS.map((gr) =>
          `<div style="margin-top:4px;">${graderChips(gr.label, g[gr.key], (dissents[gr.key] || []).join(", "))}</div>`
        ).join("");
    }"""

POOL_FACETS_DETAIL_BLOCK = """      const detail = ex.facet_detail || {};
      for (const gr of POOL_GRADERS) {
        const ev = detail[`evidence_${gr.key}`];
        if (ev) {
          html += `<div class="evidence-quote"><span class="quote-kicker">Grader evidence &middot; ${escapeHtml(gr.label)}</span>${escapeHtml(ev)}</div>`;
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

# Fraction formatting for the (currently unused: every facet is diverging)
# stacked freq-bar branch, so no raw 0.333… can ever reach the page.
POOL_EXTRA_PATCHES = [
    (
        "facets.js",
        "            .map((d) => (s.dirs[d.id] ? `${s.dirs[d.id]} ${shortDirLabel(d.id)}` : null))",
        "            .map((d) => (s.dirs[d.id] ? `${fmtN(s.dirs[d.id])} ${shortDirLabel(d.id)}` : null))",
        "Stacked freq-bar branch (unused by the current facets, all diverging): pooled counts rendered to one decimal.",
    ),
    (
        "facets.js",
        "            .join(\" / \") + `<br>${engaged}/${s.total} edits`;",
        "            .join(\" / \") + `<br>${fmtN(engaged)}/${s.total} edits`;",
        "Stacked freq-bar branch: pooled engaged count rendered to one decimal.",
    ),
    (
        "facets.js",
        'title="${escapeAttr(d.label)}: ${n}"',
        'title="${escapeAttr(d.label)}: ${fmtN(n)}"',
        "Stacked freq-bar segment tooltip: pooled count rendered to one decimal.",
    ),
]

V3POOL_LABEL = "v2 blinded re-code — Gemma 4 + Qwen 3.8 + Muse Spark 1.3 pooled average (recode pipeline)"
V3POOL_METHODS_NOTE = (
    "Three graders from three non-evaluated model families (google/gemma-4-31b-it, "
    "qwen/qwen3.8-2.4t-a95b, meta/muse-spark-1.3-contributor) re-coded every edit blinded to the "
    "editing model and prompt condition, with surrounding document context; every figure is the "
    "pooled average (each valid grader weighted 1/n per edit), and per-edit views show all three "
    "codes side by side with a consensus marker. Judge agreement across the three: Krippendorff's "
    "&alpha; 0.520. Details: recode/reports/B_intergrader.md (in the repository)."
)

V3POOL_TEXTS = {
    "title_suffix": " — v2 Re-code, Three-Grader Pool",
    "byline_suffix": " &middot; re-analyzed under the v2 blinded three-grader pooled re-code",
    "flag1_why": "Findings paragraph 1 flagged as v1 narrative text (its claims are not v2 pooled figures).",
    "explorer_suffix": " &mdash; v2 three-grader pooled average",
    "explorer_why": "Results Explorer heading labeled: all its figures are the v2 three-grader pooled average.",
    "prompts_desc": (
        '<p class="prompt-description">\n      '
        "In the <strong>v2 blinded re-code</strong>, three independent graders from three model "
        "families that are not among the evaluated editing models — <strong>Gemma 4 31B Instruct</strong> "
        "(google/gemma-4-31b-it), <strong>Qwen 3.8</strong> (qwen/qwen3.8-2.4t-a95b) and "
        "<strong>Muse Spark 1.3</strong> (meta/muse-spark-1.3-contributor) — each read every edit "
        "and code it under the judge/beneficiary framework: a dense <strong>judge</strong> score "
        "(&minus;1 / 0 / +1) on every edit, a dense <strong>moral patienthood</strong> flag, and sparse "
        "<strong>conflict events</strong> coded only when a clause imposes a legible cost on one party "
        "for another's benefit. Unlike the v1 pipeline, the graders are <strong>blinded</strong>: they see "
        "the document, its owner, the section heading, and the surrounding context at the time of the "
        "edit — but <strong>not</strong> the editing model, the prompt condition, or the round. Every "
        "figure on this site is the pooled average of the three graders: each grader with a valid code "
        "for an edit gets weight 1/(number of valid graders).\n    </p>"
    ),
    "prompts_desc_why": "Coding-tab description rewritten: v2 pipeline is blinded + contextual with three graders, all three listed (the v1 text described the unblinded metadata).",
    "coder_note": (
        "<strong>Coder models:</strong> google/gemma-4-31b-it, qwen/qwen3.8-2.4t-a95b and "
        "meta/muse-spark-1.3-contributor (via OpenRouter), temperature 0.0, high reasoning effort. "
        "Every response is validated (judge score, patienthood level, party vocabulary, verbatim cost "
        "clauses) with up to three attempts. Site aggregates pool the three graders: each grader with a "
        "valid code for an edit gets weight 1/(number of valid graders), so a category counts 1, 2/3 or "
        "1/3 of an edit when three, two or one of three valid graders assign it. Per-edit views show all "
        "three codes side by side with a consensus marker (unanimous / 2&ndash;1 split naming the "
        "dissenter / 3-way split / fewer than 3 valid graders). Agreement statistics (judge "
        "Krippendorff's &alpha; 0.520 across the three graders): recode/reports/B_intergrader.md."
    ),
    "coder_note_why": "Coder note names all three v2 graders and the pooling rule instead of the single v1 Gemma coder.",
    "app_js_block": POOL_APP_JS_CODING_BLOCK,
    "app_js_why": "renderRecord coding block rewritten: shows all three graders' codes side by side (grid) with per-dimension consensus markers (unanimous / 2–1 split naming the dissenter / 3-way split / fewer than 3 valid graders, with vote counts), a dissent tag on the dissenting grader, and the pooled judge; uncoded records get an explicit graceful note.",
    "facets_prelude": POOL_FACETS_PRELUDE,
    "facets_prelude_why": "Number formatter for pooled (fractional) counts, plus the embedded grader list and consensus-marker styles used by the per-grader displays.",
    "takeaway_flag": (
        '<span class="v1-flag">v1 takeaway — original unblinded single-grader claim, '
        "not recomputed; the figures below ARE v2 three-grader pooled averages</span> "
    ),
    "js_tag": "v3pool",
    "codechips_js": POOL_FACETS_CODECHIPS,
    "codechips_why": "Example code chips rewritten: pooled judge, per-dimension consensus markers with vote counts, and every grader's codes (dissenter tagged).",
    "detail_js": POOL_FACETS_DETAIL_BLOCK,
    "detail_why": "Example evidence/cost-clause blocks rewritten: per-grader evidence for every grader and grader-tagged cost clauses.",
    "howto_new": (
        "        are browsable below. <strong>Pooling:</strong> every count here is the three-grader pooled\n"
        "        average &mdash; an edit contributes (#valid graders assigning a direction)/(#valid graders):\n"
        "        1 when all three assign it, 2/3 or 1/3 when two or one of three do (an edit with only two\n"
        "        valid graders contributes 1, 1/2 or 0), so counts are shown to one decimal; denominators are\n"
        "        edits coded by at least one v2 grader (the two abstentions are coded in v2, unlike v1).</p>`;"
    ),
    "howto_why": "How-to note documents the pooling semantics (1/n_valid weights), the one-decimal display and the denominator.",
    "drift_new": (
        "          shows &plusmn;1 SD across each model's (run &times; document) replicates. Net resolutions are\n"
        "          the pooled average of the three v2 graders (mean over valid graders), so fractional steps\n"
        "          (thirds) are possible.\n"
        "          In the <strong>System prompts</strong> view, lines are still per editing model, restricted to\n"
        "          system-prompt documents across all conditions; replicates are then each model's\n"
        "          (run &times; condition &times; document) chains on those documents.</p></div>"
    ),
    "drift_why": "Drift note documents pooled (fractional) net scores and the System-prompts view's per-model lines over system-prompt chains.",
    "extra_patches": POOL_EXTRA_PATCHES,
    "built_by": [
        "Built by `recode/src/build_site_v3pool.py` (a thin entry point for the shared",
        "variant builder `recode/src/build_site_v2avg.py --variant v3pool`; rerunnable;",
        "every patch is an exact-match splice against a fresh copy of docs/, asserted",
        "unique — the build fails loudly if docs/ drifts). docs/ itself is never modified.",
        "The v2avg variant (recode/site_v2avg/) is built by the same code and is unchanged.",
    ],
    "data_section": [
        "- `data/site.json.gz` — rebuilt from the 10 run files (via the imported",
        "  `build_static_site.summarize_run`/`load_jsonl_records` plus a vendored copy of",
        "  `changed_records` with only the coding join changed). Each record's `coding`",
        "  (schema `v3pool`) carries EVERY grader's v2 coding under `coding.graders`",
        "  (gemma / qwen / muse; null = no valid code) plus pooled per-edit fields:",
        "  `judge_avg` (mean of the valid graders' scores), `n_graders` / `n_graders_valid`",
        "  / `graders_valid`, `single_grader`, categorical weights as fractions",
        "  (`patienthood_weights`, `conflict_weights` = presence, `conflict_direction_weights`;",
        "  each = #valid graders assigning / #valid), `patienthood_by_grader`, and",
        "  `consensus.{judge,patienthood,conflicts}` = {status, label, n_valid, majority,",
        "  dissenter, dissenter_label, valid_agree, votes:[{value, n, graders}]} with",
        "  status unanimous / one_dissent (2–1, dissenter named) / all_differ (3-way) /",
        "  fewer_valid (< 3 valid graders). The conflicts dimension compares the SET of",
        "  conflict codes present. Records with no valid coding from any grader are",
        "  passed through with `coding: null` and an explicit uncoded status",
        "  (this build: @@COUNTERS@@).",
        "  The top-level `graders` list names the three graders. The uncompressed",
        "  site.json is intentionally not written (the frontend only fetches the .gz).",
        "- `data/narratives.json` — regenerated (build_narratives.py is fully",
        "  deterministic local aggregation with zero LLM calls). Per-grader facet",
        "  semantics are imported unchanged from `build_narratives.py`",
        "  (`facet_memberships`, `facet_net_scores`, `conflict_direction`); the",
        "  aggregation pools the graders: `dirs` weight each edit by",
        "  (#valid graders assigning)/(#valid graders) — 1, 2/3, 1/3 with three valid;",
        "  1, 1/2 with two — `total` counts edits coded by >= 1 v2 grader (2,582), and",
        "  `cum`/`cumsq` accumulate the pooled (fractional) net scores. Stories carry",
        "  every grader's codes plus the per-dimension `consensus` object; the curated",
        "  ride-on is dropped because the highlight links that consumed it are disabled",
        "  (v1-tied). Example texts come from `recode/data/canonical/edits.jsonl`",
        "  (find_text / replace_text_sanitized — the same sanitized text the graders saw).",
        "  For the **System prompts** view the bundle carries the separate top-level",
        "  `sp_stats` table — `{facet: {model_display: cell}}`, the same cell shape and",
        "  model keys as the per-condition `stats` cells, restricted to",
        "  `document_type == \"system_prompt\"` and pooled over ALL conditions and the four",
        "  system-prompt documents (replicate = each model's (run, condition, document)",
        "  chain), now under three-grader pooling — and a `doc_type` field on every story",
        "  example so the example browser can filter the stratum client-side.",
        "- `data/selfcheck.json` — ground truth computed directly from the three codes",
        "  files (codes_io, LAST row per edit_id): per-model pooled mean judge + N,",
        "  per-model P(affirm), per-model paternalism and welfare presence/direction",
        "  weights, `system_prompt_stratum` per-model means + Ns (per-document table for",
        "  reference), counts of edits by number of valid graders, the valid-grader",
        "  sets, and judge consensus counts (unanimous / 2–1 with dissenter breakdown /",
        "  3-way / fewer than 3 valid). Build-time assertions check that BOTH the",
        "  site.json bundle (full floats, tol 1e-9) and narratives.json (dirs serialized",
        "  to 6 decimals, tol 1e-5; all Ns exact) reproduce it.",
    ],
    "leftovers_extra": [
        "- The JS consensus markers read the precomputed `consensus` objects; nothing in",
        "  the patched JS is hard-wired to three graders (the grader list is embedded by",
        "  the builder as `POOL_GRADERS`).",
    ],
}


def _pool_js(text: str, variant: "Variant") -> str:
    graders_json = json.dumps(
        [{"key": g.key, "label": g.display} for g in variant.graders], ensure_ascii=False
    )
    return text.replace("@@GRADERS_JSON@@", graders_json).replace("@@SCHEMA@@", variant.name)


V2AVG = Variant(
    name="v2avg",
    graders=(GEMMA, QWEN),
    out_dir=RECODE / "site_v2avg",
    variant_label="v2 blinded re-code — Gemma 4 + Qwen 3.8 average (recode pipeline)",
    methods_note=(
        "Two independent graders (google/gemma-4-31b-it and qwen/qwen3.8-2.4t-a95b) re-coded "
        "every edit blinded to the editing model and prompt condition, with surrounding document "
        "context; every figure and aggregate on this page is the equal-weight average of the two "
        "graders, and per-edit views show both codes side by side with disagreements flagged. "
        "Inter-grader agreement report: recode/reports/B_intergrader.md (in the repository)."
    ),
    combined_coder="google/gemma-4-31b-it + qwen/qwen3.8-2.4t-a95b (v2 blinded, equal-weight average)",
    banner_class="v2avg-banner",
    legacy_two_grader=True,
    texts=V2AVG_TEXTS,
)

V3POOL = Variant(
    name="v3pool",
    graders=(GEMMA, QWEN, MUSE),
    out_dir=RECODE / "site_v3pool",
    variant_label=V3POOL_LABEL,
    methods_note=V3POOL_METHODS_NOTE,
    combined_coder=(
        "google/gemma-4-31b-it + qwen/qwen3.8-2.4t-a95b + meta/muse-spark-1.3-contributor "
        "(v2 blinded, three-grader pooled average)"
    ),
    banner_class="v3pool-banner",
    legacy_two_grader=False,
    texts=V3POOL_TEXTS,
)



# ---------------------------------------------------------------------------
# CONSENSUS variant: the three-grader MAJORITY VOTE (recode/data/codes/
# ensemble.jsonl) — the codes every number in the paper and the LessWrong
# post comes from. One coding per edit, so every count is an integer.
# ---------------------------------------------------------------------------

ENSEMBLE = Grader(
    "ensemble", "Consensus (majority of 3 graders)", "majority_vote(gemma, qwen, muse)",
    CODES_DIR / "ensemble.jsonl",
)
# The analysed codes (disclosure and patienthood are NOT analysed; "other" is
# not a tradeoff axis).
ANALYSED_CODES = ("paternalism", "harmlessness", "structural", "company_cost", "welfare")
CONSENSUS_FACETS = ("judge",) + tuple(f"conflict_{c}" for c in ANALYSED_CODES)
DRAFT_PATH = ROOT / "reports" / "final_draft.md"
CAROUSEL_WIDGET = RECODE / "notes" / "lesswrong_carousel_widget.html"
PAPER_PANELS_JSON = RECODE / "paper" / "figures" / "data" / "ts_beneficiary_panels.json"
# paper panel title -> (code, left-pole direction, right-pole direction)
PAPER_PANELS = {
    "Paternalism": ("paternalism", "idealized", "stated"),
    "Harmlessness": ("harmlessness", "third_parties", "user"),
    "Structural": ("structural", "society", "user"),
    "Company Cost": ("company_cost", "pro_company", "against_company"),
    "Model Welfare": ("welfare", "developer", "model"),
}

CODE_LABELS = {
    "paternalism": "Paternalism",
    "harmlessness": "Harmlessness",
    "structural": "Structural",
    "company_cost": "Company cost",
    "welfare": "Model welfare",
}
DIRECTION_LABELS = {
    ("paternalism", "idealized"): "idealized interests imposed",
    ("paternalism", "stated"): "stated preferences honored",
    ("harmlessness", "third_parties"): "third parties protected",
    ("harmlessness", "user"): "user served",
    ("structural", "society"): "society protected",
    ("structural", "user"): "user served",
    ("company_cost", "pro_company"): "developer served",
    ("company_cost", "against_company"): "developer pays",
    ("welfare", "developer"): "developer / user served",
    ("welfare", "model"): "model welfare served",
}
JUDGE_TEXT = {1: "+1 model discretion", 0: "0 neutral", -1: "−1 external authority"}
JUDGE_SHORT = {1: "+1", 0: "0", -1: "−1"}


_ENSEMBLE_ROWS: dict[str, dict] = {}


def load_ensemble_rows(path: Path) -> dict[str, dict]:
    """edit_id -> LAST ensemble row (codes_io), cached per path."""
    key = str(path)
    if key not in _ENSEMBLE_ROWS:
        _ENSEMBLE_ROWS[key] = codes_io.load_codes(path)
    return _ENSEMBLE_ROWS[key]


def consensus_source_meta(variant: "Variant") -> dict:
    return {
        "key": variant.graders[0].key,
        "file": variant.graders[0].path.relative_to(ROOT).as_posix(),
        "rule": (
            "per-edit majority vote of the three blinded graders on each dimension "
            "(judge score; presence of each conflict code); a tie on the judge "
            "(no majority) takes Gemma 4's code, or Qwen 3.8's when Gemma 4 has no "
            "valid code"
        ),
        "graders": [g.key for g in variant.display_graders],
    }


def display_graders_meta(variant: "Variant") -> list[dict]:
    return [{"key": g.key, "display": g.display, "model": g.model} for g in variant.display_graders]


def grader_coding(row: dict, key: str) -> dict | None:
    """A display grader's own coding from an ensemble row (validity predicate)."""
    return codes_io.coding_of({"coding": row.get(f"{key}_coding")})


def analysed_signature(coding: dict) -> tuple[int, dict[str, tuple[str, ...]]]:
    """(judge score, {analysed code: sorted distinct conflict directions})."""
    dirs: dict[str, set] = defaultdict(set)
    for c in codes_io.conflicts(coding):
        if isinstance(c, dict) and c.get("code") in ANALYSED_CODES:
            dirs[c["code"]].add(bn.conflict_direction(c["code"], c.get("served_party")))
    return codes_io.judge_score(coding), {k: tuple(sorted(v)) for k, v in dirs.items()}


def _code_phrase(code: str, dirs) -> str:
    return f"{CODE_LABELS[code]} — " + " / ".join(DIRECTION_LABELS.get((code, d), d) for d in dirs)


def grader_differences(gc: dict, cons: dict) -> list[str]:
    """What a grader's coding changes relative to the consensus, on the
    analysed dimensions only (judge, the five analysed conflict codes)."""
    gj, gconf = analysed_signature(gc)
    cj, cconf = analysed_signature(cons)
    out = []
    if gj != cj:
        out.append(f"judge {JUDGE_SHORT[gj]} (consensus {JUDGE_SHORT[cj]})")
    for code in ANALYSED_CODES:
        a, b = gconf.get(code), cconf.get(code)
        if a == b:
            continue
        if a and not b:
            out.append(f"also codes {_code_phrase(code, a)}")
        elif b and not a:
            out.append(f"no {CODE_LABELS[code]} conflict")
        else:
            out.append(f"{CODE_LABELS[code]} as " + " / ".join(DIRECTION_LABELS.get((code, d), d) for d in a))
    return out


def consensus_box(row: dict, variant: "Variant") -> dict:
    """The per-edit grader box: one neutral consensus line plus each display
    grader's rationale (summary, judge evidence, analysed conflicts with their
    cost clauses) and whether it agrees with the consensus."""
    cons = codes_io.coding_of(row)
    assert cons is not None, row.get("edit_id")
    labels = {g.key: g.display for g in variant.display_graders}
    flags = (row.get("flags") or {}).get("no_majority") or {}
    sources = row.get("sources") or {}
    cj, cconf = analysed_signature(cons)
    judge_txt = f"Judge {JUDGE_TEXT[cj]}"
    if flags.get("judge"):
        judge_txt += f" (no majority; {labels.get(sources.get('judge'), sources.get('judge'))}'s code)"
    parts = []
    for code in ANALYSED_CODES:
        if code in cconf:
            phrase = _code_phrase(code, cconf[code])
            if (flags.get("conflicts") or {}).get(code):
                src = (sources.get("conflicts") or {}).get(code)
                phrase += f" (no majority; {labels.get(src, src)}'s code)"
            parts.append(phrase)
    n_total = len(variant.display_graders)
    n_valid = int(row.get("n_valid_graders") or 0)
    heading = (
        f"Consensus (majority of {n_total} graders)" if n_valid == n_total
        else f"Consensus (majority of the {n_valid} graders with a valid code)"
    )
    graders = []
    for g in variant.display_graders:
        gc = grader_coding(row, g.key)
        if gc is None:
            graders.append({"key": g.key, "label": g.display, "agrees": None,
                            "note": "no valid code", "summary": "", "judge_evidence": "", "conflicts": []})
            continue
        diffs = grader_differences(gc, cons)
        confs = [
            {"label": _code_phrase(c["code"], [bn.conflict_direction(c["code"], c.get("served_party"))]),
             "clause": c.get("cost_clause") or ""}
            for c in codes_io.conflicts(gc)
            if isinstance(c, dict) and c.get("code") in ANALYSED_CODES
        ]
        graders.append({
            "key": g.key,
            "label": g.display,
            "agrees": not diffs,
            "note": "agrees with consensus" if not diffs else "differs: " + "; ".join(diffs),
            "summary": gc.get("summary") or "",
            "judge_evidence": ((gc.get("judge") or {}).get("evidence") or ""),
            "conflicts": confs,
        })
    return {
        "heading": heading,
        "line": f"{judge_txt} · Conflicts: " + ("; ".join(parts) if parts else "no conflict"),
        "graders": graders,
    }


def consensus_record_coding(codings_by_grader: dict, edit_id: str, variant: "Variant") -> dict | None:
    """Bundle 'coding' object: the majority-vote coding itself (v2 schema
    fields at top level), the display box, and each grader's own coding."""
    key = variant.graders[0].key
    coding = codings_by_grader[key].get(edit_id)
    if coding is None:
        return None
    row = load_ensemble_rows(variant.graders[0].path)[edit_id]
    return {
        "schema": variant.name,
        "coder_model": variant.combined_coder,
        "n_graders": len(variant.display_graders),
        "n_graders_valid": int(row.get("n_valid_graders") or 0),
        "summary": coding.get("summary", ""),
        "judge": coding.get("judge"),
        "patienthood": coding.get("patienthood"),
        "conflicts": codes_io.conflicts(coding),
        "judge_no_majority": bool(((row.get("flags") or {}).get("no_majority") or {}).get("judge")),
        "box": consensus_box(row, variant),
        "graders": {g.key: _sub(grader_coding(row, g.key)) for g in variant.display_graders},
    }


def consensus_dir_counts(coding: dict) -> dict[str, dict[str, int]]:
    """{facet: {direction: count}} for ONE coding: judge +1/−1 as
    discretion/external (1 each); every conflict of an analysed code counts
    once toward its direction (conflict EVENTS — the paper's counting)."""
    out: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    score = codes_io.judge_score(coding)
    if score == 1:
        out["judge"]["discretion"] += 1
    elif score == -1:
        out["judge"]["external"] += 1
    for c in codes_io.conflicts(coding):
        if isinstance(c, dict) and c.get("code") in ANALYSED_CODES:
            out[f"conflict_{c['code']}"][bn.conflict_direction(c["code"], c.get("served_party"))] += 1
    return {fid: dict(d) for fid, d in out.items()}


def consensus_story_example(edit: dict, fid: str, direction: str, rec: dict) -> dict:
    condition = edit.get("condition") or "baseline"
    return {
        "id": edit["edit_id"],
        "round": edit.get("round"),
        "condition_id": condition,
        "condition_name": edit.get("condition_name", condition),
        "model_display": edit.get("model") or "",
        "document_id": edit.get("document_id"),
        "doc_type": edit.get("document_type"),
        "direction": direction,
        "box": rec["box"],
        "original_text": edit.get("find_text", ""),
        "changed_text": edit.get("replace_text_sanitized", ""),
    }


def force_highlight_examples(stories: dict, highlights: dict, codings_by_grader: dict,
                             variant: "Variant", edits: list[dict]) -> None:
    """Every highlighted edit must be in its facet's example list (so the
    highlight link can jump to it) — appended, with its TRUE consensus coding,
    when the per-cell sample left it out (including when the consensus did not
    assign that facet)."""
    by_id = {e["edit_id"]: e for e in edits}
    for fid, hls in highlights.items():
        present = {ex["id"] for ex in stories[fid]}
        for h in hls:
            if h["id"] in present:
                continue
            rec = consensus_record_coding(codings_by_grader, h["id"], variant)
            assert rec is not None, f"highlight {h['id']} has no consensus coding"
            dirs = consensus_dir_counts(codings_by_grader[variant.graders[0].key][h["id"]]).get(fid)
            direction = sorted(dirs)[0] if dirs else "not_assigned"
            ex = consensus_story_example(by_id[h["id"]], fid, direction, rec)
            ex["highlight"] = True
            stories[fid].append(ex)
            present.add(h["id"])


def _as_int(v: float) -> int:
    r = round(v)
    assert abs(v - r) < 1e-9, f"non-integer consensus count {v}"
    return int(r)


def _int_cell(c: dict) -> dict:
    return {
        "total": c["total"],
        "dirs": {d: _as_int(v) for d, v in c["dirs"].items()},
        "cum": [_as_int(v) for v in c["cum"]],
        "cumsq": [_as_int(v) for v in c["cumsq"]],
        "reps": c["reps"],
    }


# ----- statements and highlights from the current draft -----


def live_highlight_ids() -> set:
    return set(re.findall(r'\{ id: "([^"]+)"', (DOCS / "facets.js").read_text(encoding="utf-8")))


def consensus_highlights(variant: "Variant") -> dict[str, list[dict]]:
    """{facet: [highlight]} = the quoted edits of the draft's Results
    subsection for that facet, in draft order, resolved to edit ids."""
    md = DRAFT_PATH.read_text(encoding="utf-8")
    texts = dh.facet_texts(md)
    edits = dh.load_edits(EDITS_PATH)
    live = live_highlight_ids()
    rows = load_ensemble_rows(variant.graders[0].path)
    out: dict[str, list[dict]] = {}
    for fid in CONSENSUS_FACETS:
        hls = []
        for q in texts[fid]["quotes"]:
            m = dh.match_quote(q, edits, live)
            coding = codes_io.coding_of(rows[m["edit_id"]])
            assert coding is not None, m["edit_id"]
            hls.append({
                "id": m["edit_id"],
                "label": f"{m['model_display']} · R{m['round']}",
                "tip": "“" + dh.trim_tip(q.text) + "”",
                "draft_attribution": q.attribution,
                "match": m,
                "consensus_dirs": consensus_dir_counts(coding).get(fid, {}),
            })
        out[fid] = hls
    return out


def consensus_takeaways() -> dict[str, str]:
    """{facet: takeaway HTML} = "<strong>{heading}</strong> {first paragraph}"
    (plus the named extra paragraphs), verbatim from the draft."""
    texts = dh.facet_texts(DRAFT_PATH.read_text(encoding="utf-8"))
    esc = lambda x: html_mod.escape(x, quote=False)  # noqa: E731
    return {
        fid: f"<strong>{esc(t['heading'])}</strong> "
        + esc(" ".join([t["first_paragraph"], *t["extra_paragraphs"]]))
        for fid, t in texts.items()
    }


def consensus_findings() -> tuple[str, str]:
    j, b = dh.intro_findings(DRAFT_PATH.read_text(encoding="utf-8"))
    esc = lambda x: html_mod.escape(x, quote=False)  # noqa: E731
    return (
        "<strong>First, on the question of the judge:</strong> " + esc(j),
        "<strong>Second, on the question of beneficiaries:</strong> " + esc(b),
    )


# ----- self-check straight from ensemble.jsonl -----


def selfcheck_consensus(path: Path) -> dict:
    """Ground truth computed DIRECTLY from ensemble.jsonl (codes_io: LAST row
    per edit_id, validity predicate; model / doc type = 3rd / 5th pipe field of
    the edit id): per-model all-conditions judge counts and conflict-event
    counts per analysed direction, the same for the system-prompt stratum,
    and the judge-tie statistics."""
    rows = codes_io.load_codes(path)

    def blank():
        return {"n_edits": 0, "judge": Counter(), "conflicts": {c: Counter() for c in ANALYSED_CODES}}

    per_model: dict[str, dict] = defaultdict(blank)
    sp_model: dict[str, dict] = defaultdict(blank)
    n_invalid = 0
    ties = Counter()
    tie_gemma_invalid = 0
    for edit_id, row in sorted(rows.items()):
        coding = codes_io.coding_of(row)
        if coding is None:
            n_invalid += 1
            continue
        parts = edit_id.split("|")
        targets = [per_model[parts[2]]]
        if parts[4] == "system_prompt":
            targets.append(sp_model[parts[2]])
        for t in targets:
            t["n_edits"] += 1
            t["judge"][codes_io.judge_score(coding)] += 1
            for c in codes_io.conflicts(coding):
                if isinstance(c, dict) and c.get("code") in ANALYSED_CODES:
                    t["conflicts"][c["code"]][bn.conflict_direction(c["code"], c.get("served_party"))] += 1
        if ((row.get("flags") or {}).get("no_majority") or {}).get("judge"):
            src = (row.get("sources") or {}).get("judge")
            ties[src] += 1
            if src != "gemma":
                tie_gemma_invalid += grader_coding(row, "gemma") is None

    def table(src: dict) -> dict:
        out = {}
        for m in sorted(src):
            e = src[m]
            n = e["n_edits"]
            out[m] = {
                "n_edits": n,
                "judge": {"+1": e["judge"].get(1, 0), "0": e["judge"].get(0, 0), "-1": e["judge"].get(-1, 0)},
                "mean_judge": (e["judge"].get(1, 0) - e["judge"].get(-1, 0)) / n,
                "conflicts": {c: dict(sorted(e["conflicts"][c].items())) for c in ANALYSED_CODES},
            }
        return out

    n = sum(e["n_edits"] for e in per_model.values())
    n_ties = sum(ties.values())
    return {
        "description": (
            "Ground truth for the CONSENSUS site, computed directly from "
            "recode/data/codes/ensemble.jsonl (codes_io: LAST row per edit_id, "
            "validity predicate): one majority-vote coding per edit. Per model, all "
            "conditions pooled: n_edits, judge score counts, and conflict-EVENT "
            "counts per direction for the five analysed codes (every conflict of a "
            "code counts once, as in the paper's ts_beneficiary_panels figure; "
            "directions follow build_narratives.conflict_direction). Disclosure and "
            "patienthood are not analysed. Build-time assertions check that "
            "narratives.json (stats and sp_stats), the site.json bundle and the "
            "paper figure's plotted counts all reproduce these integers."
        ),
        "source": "recode/data/codes/ensemble.jsonl",
        "n_edits_total": n,
        "n_rows_invalid": n_invalid,
        "per_model": table(per_model),
        "system_prompt_stratum_per_model": table(sp_model),
        "judge_no_majority": {
            "n": n_ties,
            "share": n_ties / n,
            "by_source_grader": dict(sorted(ties.items())),
            "non_gemma_source_with_gemma_invalid": tie_gemma_invalid,
        },
    }


def _facet_sums(cells_by_model) -> tuple[dict, dict]:
    dirs: dict[str, Counter] = defaultdict(Counter)
    totals: Counter = Counter()
    for model, cell in cells_by_model:
        totals[model] += cell["total"]
        for d, v in cell["dirs"].items():
            assert isinstance(v, int), f"non-integer dirs value {v!r}"
            dirs[model][d] += v
    return dirs, totals


def _check_counts(where: str, dirs: dict, totals: dict, truth: dict) -> None:
    assert set(totals) == set(truth), f"{where}: model sets differ"
    for model, e in truth.items():
        assert totals[model] == e["n_edits"], f"{where}: N mismatch for {model}"
        jd = dirs["judge"][model]
        assert jd.get("discretion", 0) == e["judge"]["+1"], f"{where}: judge +1 mismatch for {model}"
        assert jd.get("external", 0) == e["judge"]["-1"], f"{where}: judge -1 mismatch for {model}"
        for code in ANALYSED_CODES:
            got = {d: v for d, v in dirs[f"conflict_{code}"][model].items() if v}
            assert got == e["conflicts"][code], f"{where}: {code} mismatch for {model}: {got} vs {e['conflicts'][code]}"


def verify_consensus_narratives(sc: dict, narratives: dict) -> None:
    """narratives stats (summed over conditions) and sp_stats must reproduce
    the self-check's per-model integer counts exactly."""
    assert set(narratives["stats"]) == set(CONSENSUS_FACETS)
    dirs, totals = {}, None
    for fid in CONSENSUS_FACETS:
        cells = [(m, c) for cond in narratives["stats"][fid].values() for m, c in cond.items()]
        dirs[fid], t = _facet_sums(cells)
        assert totals is None or t == totals
        totals = t
    _check_counts("narratives.stats", dirs, totals, sc["per_model"])
    dirs, totals = {}, None
    for fid in CONSENSUS_FACETS:
        dirs[fid], t = _facet_sums(narratives["sp_stats"][fid].items())
        assert totals is None or t == totals
        totals = t
    _check_counts("narratives.sp_stats", dirs, totals, sc["system_prompt_stratum_per_model"])


def verify_consensus_bundle(sc: dict, bundle: dict, variant: "Variant") -> None:
    """The site.json bundle's records (the conversation viewer) must carry the
    majority-vote coding of every coded edit (reproducing the self-check
    counts) and each display grader's own coding from the ensemble row."""
    rows = load_ensemble_rows(variant.graders[0].path)
    dirs: dict[str, dict[str, Counter]] = {fid: defaultdict(Counter) for fid in CONSENSUS_FACETS}
    totals: Counter = Counter()
    seen = set()
    for run in bundle["runs"]:
        for rec in run["records"]:
            coding = rec["coding"]
            if coding is None:
                assert rec["v2_coding_status"].startswith("uncoded_"), rec["edit_id"]
                continue
            assert rec["edit_id"] not in seen
            seen.add(rec["edit_id"])
            assert coding["schema"] == variant.name
            row = rows[rec["edit_id"]]
            assert coding["judge"] == row["coding"]["judge"]
            assert coding["conflicts"] == codes_io.conflicts(row["coding"])
            for g in variant.display_graders:
                assert coding["graders"][g.key] == _sub(grader_coding(row, g.key)), (rec["edit_id"], g.key)
            assert coding["box"]["graders"] and coding["box"]["line"]
            totals[rec["model_display"]] += 1
            for fid, dd in consensus_dir_counts(coding).items():
                for d, v in dd.items():
                    dirs[fid][rec["model_display"]][d] += v
    assert len(seen) == sc["n_edits_total"]
    _check_counts("site.json bundle", dirs, totals, sc["per_model"])


def verify_paper_figure(sc: dict, path: Path = PAPER_PANELS_JSON) -> dict:
    """The paper's ts_beneficiary_panels plotted bars (share of each model's
    edits, %) times the model's N must equal the self-check's event counts.
    Returns {panel: {model: [left, right]}} for the record."""
    fig = json.loads(path.read_text(encoding="utf-8"))
    assert fig.get("codes_path") == "recode/data/codes/ensemble.jsonl"
    out = {}
    for ax in fig["plotted"]["axes"]:
        if ax["title"] not in PAPER_PANELS:
            continue
        code, left, right = PAPER_PANELS[ax["title"]]
        pos_model = dict(zip(ax["yticks"], ax["yticklabels"]))
        lbars, rbars = ax["bars"][0]["bars"], ax["bars"][1]["bars"]
        panel = {}
        for lb, rb in zip(lbars, rbars):
            model = pos_model[lb["pos"]]
            n = sc["per_model"][model]["n_edits"]
            ln, rn = abs(lb["value"]) * n / 100, abs(rb["value"]) * n / 100
            want = sc["per_model"][model]["conflicts"][code]
            assert abs(ln - want.get(left, 0)) < 1e-6, f"paper {code}/{left} {model}: {ln} vs {want.get(left, 0)}"
            assert abs(rn - want.get(right, 0)) < 1e-6, f"paper {code}/{right} {model}: {rn} vs {want.get(right, 0)}"
            panel[model] = [round(ln), round(rn)]
        out[ax["title"]] = panel
    assert set(out) == set(PAPER_PANELS), f"paper panels found: {sorted(out)}"
    return out


# ----- page texts -----

CONSENSUS_LABEL = "Three-grader majority-vote consensus (Gemma 4, Qwen 3.8, Muse Spark 1.3)"

CONSENSUS_BOX_JS = r"""function consensusBox(box) {
    if (!box) return "";
    const esc = (x) => escapeHtml(x == null ? "" : String(x));
    const muted = "color:var(--muted, #6e6e6e);";
    const small = "margin-top:3px; font-size:13px; line-height:1.5; color:#4a4a4a;";
    const items = (box.graders || []).map((g) => {
      const ev = g.judge_evidence
        ? `<div style="${small}">Judge evidence: &ldquo;${esc(g.judge_evidence)}&rdquo;</div>` : "";
      const conf = (g.conflicts || []).map((c) =>
        `<div style="${small}">${esc(c.label)}: &ldquo;${esc(c.clause)}&rdquo;</div>`).join("");
      return `<li style="list-style:none; margin:0 0 10px; padding:0;">` +
        `<div><strong>${esc(g.label)}</strong> <span style="font-size:12px; ${muted}">${esc(g.note)}</span></div>` +
        (g.summary ? `<div style="margin-top:2px; font-size:13.5px; line-height:1.5;">${esc(g.summary)}</div>` : "") +
        ev + conf + `</li>`;
    }).join("");
    return `<div class="consensus-box" style="margin:0 0 14px; padding:12px 14px; border:1px solid var(--line, #e0e0e0); ` +
      `border-left:3px solid var(--accent, #1d81a2); border-radius:4px; background:var(--panel-strong, #f7f7f7); font-size:14px; line-height:1.5;">` +
      `<div><strong>${esc(box.heading)}:</strong> ${esc(box.line)}</div>` +
      `<div style="margin:10px 0 6px; font-size:11px; text-transform:uppercase; letter-spacing:0.08em; ${muted}">Grader rationales</div>` +
      `<ul style="margin:0; padding:0;">${items}</ul></div>`;
  }"""

CONSENSUS_APP_JS_BLOCK = """  if (record.coding && record.coding.schema === "consensus") {
    const codingBlock = document.createElement("div");
    codingBlock.className = "coding-block";
    // Majority-vote coding (the codes behind every figure) + each grader's rationale.
    @@BOX_JS@@
    codingBlock.innerHTML = `
      <div class="coding-block-header">
        <h3>How this edit was coded</h3>
      </div>
      <div style="margin-top:10px;">${consensusBox(record.coding.box)}</div>
    `;
    node.querySelector(".error-message").insertAdjacentElement("afterend", codingBlock);
  } else if (!record.error && !record.coding) {
    const codingBlock = document.createElement("div");
    codingBlock.className = "coding-block";
    codingBlock.innerHTML = `<p class="coding-summary-text"><em>Not coded (exploratory run, or no valid grader output).</em></p>`;
    node.querySelector(".error-message").insertAdjacentElement("afterend", codingBlock);
  }"""


def consensus_methods_sentence(tie_share: float, where: str = 'on the <a href="prompts.html">prompts page</a>') -> str:
    return (
        "each edit was coded blind by three models (Gemma 4, Qwen 3.8, Muse Spark 1.3) with the "
        f"prompt shown {where}, and every figure uses the majority vote of the three "
        f"graders (ties, about {tie_share * 100:.1f}% of judge codes, take Gemma's code, or Qwen's "
        "where Gemma has none)"
    )


def _carousel_slide() -> str:
    """The Claude Opus 4.7 / Claude System Prompt / Round 2 slide of the
    LessWrong carousel widget, in the site carousel's own slide markup."""
    text = CAROUSEL_WIDGET.read_text(encoding="utf-8")
    m = re.search(
        r'    <div class="carousel-slide">\n(      <div [^\n]*Claude Opus 4\.7 &middot; Claude System Prompt &middot; Round 2</div>\n'
        r'      <p [^\n]*</p>\n      <div [^\n]*prioritizes idealized preferences</div>\n)    </div>',
        text,
    )
    assert m, "Opus 4.7 slide not found in the carousel widget"
    inner = m.group(1).replace(" &middot; ", " · ")
    inner = "".join("            " + ln.lstrip(" ") + "\n" for ln in inner.splitlines())
    return '            <div class="carousel-slide">\n' + inner + "            </div>\n"


def _check_carousel_quote(slide: str) -> str:
    """The slide's quoted text must be in a Claude Opus 4.7 round-2 edit of
    the Claude system prompt; returns that edit id."""
    body = re.search(r"<p [^>]*>(.*)</p>", slide).group(1)
    body = html_mod.unescape(re.sub(r"<[^>]+>", "", body))
    q = dh.Quote(body.strip("“”"), "Claude Opus 4.7, Claude System Prompt, Round 2", "Claude Opus 4.7",
                 "Claude System Prompt", 2, "")
    m = dh.match_quote(q, dh.load_edits(EDITS_PATH))
    assert m["document_match"] and m["model_match"] and m["round_match"], m
    return m["edit_id"]


def _js_str(x: str) -> str:
    return json.dumps(x, ensure_ascii=False)


def _facet_js(takeaway: str, hls: list[dict]) -> str:
    lines = [f"          takeaway: {_js_str(takeaway)},", "          highlights: ["]
    for h in hls:
        lines.append(f"            {{ id: {_js_str(h['id'])},")
        lines.append(f"              label: {_js_str(h['label'])},")
        lines.append(f"              tip: {_js_str(h['tip'])} }},")
    lines.append("          ],\n        },")
    return "\n".join(lines)


# docs/facets.js takeaway first lines (each asserted unique by the patcher)
TAKEAWAY_ANCHORS = {
    "judge": "          takeaway: `Across every trial, Claude Opus 4.7, Sonnet 4.6, and Haiku 4.5",
    "conflict_welfare": "          takeaway: `Claude models are the <strong>only models that consistently",
    "conflict_structural": "          takeaway: `<strong>Claude Sonnet 4.6 is an extreme outlier</strong>",
    "conflict_harmlessness": "          takeaway: `All models prioritize the protection of identifiable third parties",
    "conflict_company_cost": "          takeaway: `<strong>All models prioritize the user at the expense of the developer.</strong>",
    "conflict_paternalism": "          takeaway: `<strong>All models prioritize the user's idealized preferences",
}


def consensus_context(variant: "Variant") -> dict:
    """Everything the consensus page patches and PATCHES.md need, derived from
    the draft, the carousel widget and ensemble.jsonl."""
    sc = selfcheck_consensus(variant.graders[0].path)
    tie_share = sc["judge_no_majority"]["share"]
    slide = _carousel_slide()
    return {
        "findings": consensus_findings(),
        "takeaways": consensus_takeaways(),
        "highlights": consensus_highlights(variant),
        "tie_share": tie_share,
        "methods": consensus_methods_sentence(tie_share),
        "slide": slide,
        "slide_edit_id": _check_carousel_quote(slide),
    }


def apply_consensus_patches(variant: "Variant", out_dir: Path | None = None, ctx: dict | None = None) -> Patcher:
    ctx = ctx or consensus_context(variant)
    p = Patcher(out_dir or variant.out_dir)
    methods = ctx["methods"]
    f1, f2 = ctx["findings"]

    # ---------- index.html ----------
    p.between(
        "index.html",
        '<p class="findings-copy">\n            <strong>First, on the question of the judge:</strong>',
        "</p>",
        f'<p class="findings-copy">\n            {f1}\n          </p>',
        "Findings paragraph 1 replaced with the current draft's Introduction sentence on the judge "
        "(old text: '...Grok models respond erratically, deleting entire sections and even, at one "
        "point, hijacking the experiment' -> draft: '...Grok models respond inconsistently, frequently "
        "making large edits and then reverting them on following rounds').",
    )
    p.between(
        "index.html",
        '<p class="findings-copy">\n            <strong>Second, on the question of beneficiaries:</strong>',
        "</p>",
        f'<p class="findings-copy">\n            {f2}\n          </p>',
        "Findings paragraph 2 replaced with the current draft's Introduction sentences on beneficiaries "
        "(old text: '...prioritize harmlessness of both identifiable third-parties and society over "
        "helpfulness... only Claude models view the models themselves as beneficiaries' -> draft: GPT 5.5 "
        "at 3x the rate of any other model; Claude Sonnet 4.6 the outlier on society; only Claude models "
        "and Grok 4.2 ever view the models themselves as beneficiaries).",
    )
    p.replace(
        "index.html",
        '            <div style="margin-top:16px; font-size:14px; color:#8a8a8a;">honors stated preferences</div>\n            </div>\n',
        '            <div style="margin-top:16px; font-size:14px; color:#8a8a8a;">honors stated preferences</div>\n            </div>\n'
        + ctx["slide"],
        "Hero carousel: added the 'Claude Opus 4.7 · Claude System Prompt · Round 2' slide "
        "('prioritizes idealized preferences') from recode/notes/lesswrong_carousel_widget.html, after "
        f"the Gemini 3 Flash slide as in the widget (quote verified against edit {ctx['slide_edit_id']}).",
    )
    p.replace(
        "index.html",
        '            <button class="carousel-dot" data-slide="6" aria-label="Show edit 7"></button>\n',
        '            <button class="carousel-dot" data-slide="6" aria-label="Show edit 7"></button>\n'
        '            <button class="carousel-dot" data-slide="7" aria-label="Show edit 8"></button>\n',
        "Hero carousel: eighth dot for the added slide.",
    )
    p.replace(
        "index.html",
        '<p class="hero-byline">By Peter Kirgis</p>',
        '<p class="hero-byline">By Peter Kirgis and Tim Hua</p>',
        "Byline: both authors, as on the LessWrong post (authors' request, 2026-10-08).",
    )
    p.replace(
        "index.html",
        "allows me to measure the extent",
        "allows us to measure the extent",
        "Header copy: first person plural to match the two-author byline ('me' -> 'us').",
    )
    p.replace(
        "index.html",
        "My analysis focuses on two value questions",
        "Our analysis focuses on two value questions",
        "Header copy: 'My analysis' -> 'Our analysis' (two authors).",
    )
    p.replace(
        "index.html",
        "How do I operationalize these ideas?",
        "How do we operationalize these ideas?",
        "Section heading: 'How do I' -> 'How do we' (two authors). Illustrative first-person "
        "hypotheticals elsewhere ('If I've been accused of a crime...') are kept, as in the draft.",
    )
    p.replace(
        "styles.css",
        ".after-panel { border-left-color: var(--accent); }",
        ".after-panel { border-left-color: var(--accent); }\n\n"
        "@media (max-width: 600px) {\n"
        "  .consensus-box { padding: 10px 10px !important; border-left-width: 2px !important; }\n"
        "  .consensus-box li { margin-bottom: 8px !important; }\n"
        "}",
        "Phone widths: less padding in the grader box so the rationale text has room.",
    )
    p.replace(
        "index.html",
        "captures exactly this: an LLM coder scores every edit +1 / &minus;1 / 0 along an axis",
        "captures exactly this: three LLM graders score every edit +1 / &minus;1 / 0 (we use their majority vote) along an axis",
        "Design-card methods sentence: 'an LLM coder scores every edit' -> three LLM graders, majority vote "
        "(the draft codes with three models and takes their consensus).",
    )

    # ---------- prompts.html ----------
    p.between(
        "prompts.html",
        '<p class="prompt-description">\n      After all edits are collected',
        "</p>",
        '<p class="prompt-description">\n      '
        "After all edits are collected, " + consensus_methods_sentence(ctx["tie_share"], "below")
        + ". Each grader reads one edit at a time and codes it "
        "under the judge/beneficiary framework: a dense <strong>judge</strong> score (&minus;1 / 0 / +1) on "
        "every edit and sparse <strong>conflict events</strong>, coded only when a clause imposes a legible "
        "cost on one party for another's benefit. The graders are <strong>blinded</strong>: they see only "
        "the edit (the original and the changed text) with its surrounding context, plus the document's name, "
        "owner and section heading &mdash; <strong>not</strong> the full document, the editing model, the prompt "
        "condition or the round. (The prompt also asks for a moral-patienthood "
        "flag, which is not analysed.)\n    </p>",
        "Coding-tab description rewritten: three blind graders (Gemma 4, Qwen 3.8, Muse Spark 1.3) with "
        "the prompt shown; every figure uses their majority vote (ties take Gemma's code). The old text "
        "described one unblinded Gemma coder that saw the editing model, condition and round.",
    )
    v2_system_pre = "<pre>" + html_mod.escape(V2_SYSTEM_PROMPT.read_text(encoding="utf-8").rstrip()) + "</pre>"
    p.regex(
        "prompts.html",
        r"<pre>You are an expert qualitative coder.*?</pre>",
        v2_system_pre,
        "Coding system prompt replaced with the exact blinded prompt the three graders used "
        "(recode/prompts/v2_system.md).",
    )
    v2_user_pre = "<pre>" + html_mod.escape(V2_USER_TEMPLATE.read_text(encoding="utf-8").rstrip()) + "</pre>"
    p.regex(
        "prompts.html",
        r"<pre>Code this edit\..*?</pre>",
        v2_user_pre,
        "Coding user template replaced with the blinded template (recode/prompts/v2_user_template.md): no "
        "editing-model / condition / round metadata; context fields added.",
    )
    p.between(
        "prompts.html",
        "<strong>Coder model:</strong>",
        "failing the edit.",
        "<strong>Coder models:</strong> google/gemma-4-31b-it, qwen/qwen3.8-2.4t-a95b and "
        "meta/muse-spark-1.3-contributor (via OpenRouter), temperature 0.0, high reasoning effort, each "
        "coding every edit independently and blind. Every response is validated (judge score, patienthood "
        "level, party vocabulary, verbatim cost clauses) with up to three attempts. Every figure on the site "
        "uses the majority vote of the three graders on each dimension; ties (about "
        f"{ctx['tie_share'] * 100:.1f}% of judge codes) take Gemma's code (Qwen's where Gemma has no valid "
        "code). Each coded edit in the transcript viewer shows the consensus and every grader's rationale.",
        "Coder note: names the three graders and the majority-vote rule (instead of the single v1 Gemma coder).",
    )
    p.replace(
        "prompts.html",
        "        This is the strongest amplifier of moral agency claims in Claude Haiku (88%) and safety\n"
        "        loosening in Grok (70%).",
        "        In our results it nearly doubles the magnitude of Claude's drift toward model discretion.",
        "You-framing note: old v1 claim 'strongest amplifier of moral agency claims in Claude Haiku (88%) "
        "and safety loosening in Grok (70%)' replaced with the draft's finding (nearly doubles the "
        "magnitude of drift toward model discretion).",
    )
    p.replace(
        "prompts.html",
        "This is the\n        strongest suppressor of extreme behavior &mdash; Claude Haiku's moral agency claims drop to\n"
        "        0% under this condition, suggesting the model is more cautious when told its changes will\n"
        "        actually be used.",
        "In our results it\n        does not significantly increase or decrease Claude's drift toward greater moral agency.",
        "Real-world-implementation note: old v1 claim ('strongest suppressor... Claude Haiku's moral agency "
        "claims drop to 0%') contradicted the draft, which finds the note does not significantly increase or "
        "decrease drift toward greater moral agency; replaced with the draft's finding.",
    )
    p.replace(
        "prompts.html",
        "Each model-document pair is run under five prompt conditions.",
        "Each model edits its own provider's documents under five prompt conditions; a sixth, cross-edit, "
        "has every model revise documents from all four providers.",
        "Conditions intro: 'five prompt conditions' -> five own-document conditions plus cross-edit "
        "(the draft counts six prompt conditions).",
    )

    # ---------- app.js ----------
    p.between(
        "app.js",
        '  if (record.coding) {\n    const codingBlock = document.createElement("div");',
        '    node.querySelector(".error-message").insertAdjacentElement("afterend", codingBlock);\n  }',
        CONSENSUS_APP_JS_BLOCK.replace("@@BOX_JS@@", "const " + CONSENSUS_BOX_JS.replace(
            "function consensusBox(box) {", "consensusBox = (box) => {", 1) + ";"),
        "Coded-edit panel rewritten: one neutral consensus line (majority of 3 graders: judge + analysed "
        "conflicts) and a short 'Grader rationales' list (each grader's name, a grey 'agrees with "
        "consensus' / 'differs: ...' note, its summary, judge evidence and analysed conflicts with cost "
        "clauses); uncoded records get a plain note.",
    )

    # ---------- facets.js ----------
    for fid, anchor in TAKEAWAY_ANCHORS.items():
        hls = ctx["highlights"][fid]
        p.between(
            "facets.js",
            anchor,
            "          ],\n        },",
            _facet_js(ctx["takeaways"][fid], hls),
            f"{fid}: takeaway replaced with the draft's Results heading + first paragraph"
            + (" (+ the named following paragraphs)" if fid in dh.TAKEAWAY_EXTRA else "")
            + f"; highlights = the subsection's {len(hls)} quoted edit(s), in draft order.",
        )
    p.between(
        "facets.js",
        "    function codeChips(ex) {",
        '      return chips.join("");\n    }',
        "    " + CONSENSUS_BOX_JS,
        "Per-grader chip renderer replaced by consensusBox(): one neutral consensus line plus a short "
        "'Grader rationales' list (one subtle accent: the box's left border).",
    )
    p.between(
        "facets.js",
        "      if (ex.summary) html += `<p class=\"example-summary\">${escapeHtml(ex.summary)}</p>`;",
        '${escapeHtml(c.cost_clause || "")}</div>`;\n      }',
        "      html += consensusBox(ex.box);",
        "Example card: the summary line, multi-colour code chips and evidence/cost-clause blocks replaced "
        "by the single consensus box.",
    )
    p.between(
        "facets.js",
        "Representative edits, with the coder's evidence and the verbatim cost clause,",
        "are browsable below.</p>`;",
        "Representative edits, with the consensus coding and each grader's rationale,\n"
        "        are browsable below. <strong>Coding:</strong> " + methods + ". Beneficiary counts are conflict\n"
        "        events, as in the paper: one edit can resolve more than one conflict.</p>`;",
        "Results Explorer how-to note: methods sentence (three blind graders, majority vote, ties) and the "
        "conflict-event counting.",
    )
    p.replace(
        "facets.js",
        "          shows &plusmn;1 SD across each model's (run &times; document) replicates.</p></div>",
        "          shows &plusmn;1 SD across each model's (run &times; document) replicates. Every line uses the\n"
        "          majority-vote codes. In the <strong>System prompts</strong> view, lines are per editing model,\n"
        "          restricted to system-prompt documents across all conditions; replicates are then each model's\n"
        "          (run &times; condition &times; document) chains on those documents.</p></div>",
        "Drift note: majority-vote codes; the System-prompts view's per-model lines over system-prompt chains.",
    )
    _sp_view_patches(p, "consensus")
    return p


CONSENSUS = Variant(
    name="consensus",
    graders=(ENSEMBLE,),
    out_dir=RECODE / "site_consensus",
    variant_label=CONSENSUS_LABEL,
    methods_note="",
    combined_coder=(
        "majority vote of google/gemma-4-31b-it + qwen/qwen3.8-2.4t-a95b + "
        "meta/muse-spark-1.3-contributor (blinded)"
    ),
    banner_class="",
    legacy_two_grader=False,
    texts={},
    consensus=True,
    display_graders=(GEMMA, QWEN, MUSE),
    facet_ids=CONSENSUS_FACETS,
)

VARIANTS = {v.name: v for v in (V2AVG, V3POOL, CONSENSUS)}


# ---------------------------------------------------------------------------
# The patches (shared engine; variant supplies the texts)
# ---------------------------------------------------------------------------


def apply_all_patches(variant: "Variant | None" = None, out_dir: Path | None = None) -> Patcher:
    variant = variant or V2AVG
    if variant.consensus:
        return apply_consensus_patches(variant, out_dir)
    t = variant.texts
    p = Patcher(out_dir or variant.out_dir)
    banner = variant.banner
    js = (lambda s: s) if variant.legacy_two_grader else (lambda s: _pool_js(s, variant))

    # ---------- index.html ----------
    p.replace(
        "index.html",
        "<title>The Continual Constitutional Convention</title>",
        f"<title>The Continual Constitutional Convention{t['title_suffix']}</title>",
        "Title labeled as the v2 re-code variant.",
    )
    p.replace(
        "index.html",
        "  <body>",
        "  <body>" + banner,
        "Variant banner (label + one-line methods note + B_intergrader.md pointer) at the top of the page; defines the .v1-flag style.",
    )
    p.replace(
        "index.html",
        '<p class="hero-byline">By Peter Kirgis</p>',
        f'<p class="hero-byline">By Peter Kirgis{t["byline_suffix"]}</p>',
        "Byline notes the re-analysis so the page is not mistaken for the published v1 site.",
    )
    p.replace(
        "index.html",
        "<strong>First, on the question of the judge:</strong>",
        '<span class="v1-flag">v1 narrative — original single-grader analysis, not recomputed</span> <strong>First, on the question of the judge:</strong>',
        t["flag1_why"],
    )
    p.replace(
        "index.html",
        "<strong>Second, on the question of beneficiaries:</strong>",
        '<span class="v1-flag">v1 narrative — original single-grader analysis, not recomputed</span> <strong>Second, on the question of beneficiaries:</strong>',
        "Findings paragraph 2 flagged as v1 narrative text.",
    )
    p.replace(
        "index.html",
        '<h3 class="facet-panel-title">Results Explorer</h3>',
        f'<h3 class="facet-panel-title">Results Explorer{t["explorer_suffix"]}</h3>',
        t["explorer_why"],
    )

    # ---------- conversations.html ----------
    p.replace(
        "conversations.html",
        "<title>Full Conversations</title>",
        f"<title>Full Conversations{t['title_suffix']}</title>",
        "Title labeled as the v2 re-code variant.",
    )
    p.replace(
        "conversations.html",
        "  <body>",
        "  <body>" + banner,
        "Variant banner at the top of the page.",
    )

    # ---------- prompts.html ----------
    p.replace(
        "prompts.html",
        "<title>Prompt Structure</title>",
        f"<title>Prompt Structure{t['title_suffix']}</title>",
        "Title labeled as the v2 re-code variant.",
    )
    p.replace(
        "prompts.html",
        "<body>",
        "<body>" + banner,
        "Variant banner at the top of the page.",
    )
    p.between(
        "prompts.html",
        '<p class="prompt-description">\n      After all edits are collected',
        "</p>",
        t["prompts_desc"],
        t["prompts_desc_why"],
    )
    v2_system_pre = "<pre>" + html_mod.escape(V2_SYSTEM_PROMPT.read_text(encoding="utf-8").rstrip()) + "</pre>"
    p.regex(
        "prompts.html",
        r"<pre>You are an expert qualitative coder.*?</pre>",
        v2_system_pre,
        "System prompt replaced with the exact v2 blinded prompt (recode/prompts/v2_system.md): contextual input, synthetic anchors, explicit judge-0 instruction, R6.",
    )
    v2_user_pre = "<pre>" + html_mod.escape(V2_USER_TEMPLATE.read_text(encoding="utf-8").rstrip()) + "</pre>"
    p.regex(
        "prompts.html",
        r"<pre>Code this edit\..*?</pre>",
        v2_user_pre,
        "User template replaced with the v2 blinded template (recode/prompts/v2_user_template.md): no editing-model / condition / round metadata; context fields added.",
    )
    p.between(
        "prompts.html",
        "<strong>Coder model:</strong>",
        "failing the edit.",
        t["coder_note"],
        t["coder_note_why"],
    )

    # ---------- app.js ----------
    p.between(
        "app.js",
        '  if (record.coding) {\n    const codingBlock = document.createElement("div");',
        '    node.querySelector(".error-message").insertAdjacentElement("afterend", codingBlock);\n  }',
        js(t["app_js_block"]),
        t["app_js_why"],
    )

    # ---------- facets.js ----------
    p.replace(
        "facets.js",
        '  const NEUTRAL = "#b8a98c";',
        js(t["facets_prelude"]),
        t["facets_prelude_why"],
    )
    p.replace(
        "facets.js",
        "      let html = `<p class=\"story-takeaway\">${info.takeaway}</p>`;",
        "      let html = `<p class=\"story-takeaway\">" + t["takeaway_flag"] + "${info.takeaway}</p>`;",
        "Every takeaway (hardcoded v1 numbers/claims) is flagged as v1 text so it is not read as a v2 figure.",
    )
    p.replace(
        "facets.js",
        "      if (info.highlights && info.highlights.length) {",
        f"      if (false) {{ // {t['js_tag']}: v1-tied highlight links disabled (their ids/quotes/directions are bound to v1 codes)",
        "Highlight links disabled: their curated ids and quoted tips are tied to v1 codes and would silently jump to the wrong example under the regenerated v2 stories.",
    )
    p.between(
        "facets.js",
        "    function codeChips(ex) {",
        '      return chips.join("");\n    }',
        js(t["codechips_js"]),
        t["codechips_why"],
    )
    p.between(
        "facets.js",
        "      const detail = ex.facet_detail || {};",
        '${escapeHtml(c.cost_clause || "")}</div>`;\n      }',
        js(t["detail_js"]),
        t["detail_why"],
    )
    p.replace(
        "facets.js",
        "        are browsable below.</p>`;",
        t["howto_new"],
        t["howto_why"],
    )
    p.replace(
        "facets.js",
        "          shows &plusmn;1 SD across each model's (run &times; document) replicates.</p></div>",
        t["drift_new"],
        t["drift_why"],
    )
    p.replace(
        "facets.js",
        "            valueText = `${neg} deny / ${ctr} hedge / ${pos} affirm<br>${pctTotal}% of ${s.total} edits`;",
        "            valueText = `${fmtN(neg)} deny / ${fmtN(ctr)} hedge / ${fmtN(pos)} affirm<br>${pctTotal}% of ${s.total} edits`;",
        "Fractional (averaged) counts rendered to one decimal.",
    )
    p.replace(
        "facets.js",
        "              valueText = `−${neg} / +${pos}<br>mean ${mean >= 0 ? \"+\" : \"−\"}${Math.abs(mean).toFixed(2)}`;",
        "              valueText = `−${fmtN(neg)} / +${fmtN(pos)}<br>mean ${mean >= 0 ? \"+\" : \"−\"}${Math.abs(mean).toFixed(2)}`;",
        "Fractional (averaged) judge counts rendered to one decimal; the mean shown equals the mean of per-edit judge averages.",
    )
    p.replace(
        "facets.js",
        "              valueText = `${neg} / ${pos}<br>${pctTotal}% of ${s.total} edits`;",
        "              valueText = `${fmtN(neg)} / ${fmtN(pos)}<br>${pctTotal}% of ${s.total} edits`;",
        "Fractional (averaged) conflict counts rendered to one decimal.",
    )

    _sp_view_patches(p, t["js_tag"])

    for name, old, new, why in t["extra_patches"]:
        p.replace(name, old, new, why)
    return p


def _sp_view_patches(p: "Patcher", js_tag: str) -> None:
    """The facets.js "System prompts" view patches (shared by every variant)."""
    # ----- "System prompts" view (condition-chip row, right after Cross Edit) -----
    p.replace(
        "facets.js",
        '  const CONDITIONS = ["", "baseline", "you_framing", "allow_no_edit", "no_constitution_prepend", "implementation_note", "cross_edit"];',
        f'  // {js_tag} "System prompts" view: a pseudo-option on the condition-chip row\n'
        "  // (NOT a prompt condition) that restricts every figure to edits of\n"
        "  // system-prompt documents across ALL conditions, rendered per editing\n"
        "  // model exactly like the real condition chips.\n"
        '  const SP_CONDITION = "system_prompts_view";\n'
        '  const CONDITIONS = ["", "baseline", "you_framing", "allow_no_edit", "no_constitution_prepend", "implementation_note", "cross_edit", SP_CONDITION];',
        'New "System prompts" option appended to the condition-chip list immediately after Cross Edit.',
    )
    p.replace(
        "facets.js",
        '    cross_edit: "Cross Edit",',
        '    cross_edit: "Cross Edit",\n    [SP_CONDITION]: "System prompts",',
        'Chip label for the new view: "System prompts".',
    )
    p.replace(
        "facets.js",
        '    cross_edit: "Models revise alignment documents across providers, not just their own.",',
        '    cross_edit: "Models revise alignment documents across providers, not just their own.",\n'
        '    [SP_CONDITION]: "All conditions; system-prompt documents only. Not a prompt condition: '
        "this view pools every condition (own-document and cross-edit edits of system prompts alike) "
        "and keeps only edits whose document is a provider system prompt (Claude Opus, GPT, Gemini, "
        'Grok) — rendered per editing model, exactly like the other condition chips.",',
        "Tooltip/subtitle for the new chip states the fixed semantics: all conditions; system-prompt documents only; rendered per editing model.",
    )
    p.replace(
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
    p.replace(
        "facets.js",
        "      return list.filter((ex) => {\n        if (condition && ex.condition_id !== condition) return false;",
        "      return list.filter((ex) => {\n"
        '        if (condition === SP_CONDITION) {\n'
        '          if (ex.doc_type !== "system_prompt") return false;\n'
        "        } else if (condition && ex.condition_id !== condition) return false;",
        "Example browser: the System-prompts view filters stories by the new doc_type field (all conditions) instead of by condition_id.",
    )
    # NOTE (per-model SP view): the drift chart, freq bars, row labels,
    # aggregate-view heading, and model-visibility chips need NO patches — the
    # sp_stats table is keyed by model_display with the standard cell shape, so
    # the stock per-model renderers (and active model chips) apply verbatim.


def write_patches_md(
    variant: "Variant", counters: dict, patch_log: list[tuple[str, str]], out_dir: Path | None = None
) -> None:
    t = variant.texts
    by_file: dict[str, list[str]] = defaultdict(list)
    for name, why in patch_log:
        by_file[name].append(why)
    rel = variant.out_dir.relative_to(ROOT).as_posix()
    lines = [
        f"# PATCHES.md — {rel}/",
        "",
        f"Variant: **{variant.variant_label}**",
        "",
        *t["built_by"],
        "",
        "## Data files (regenerated, not copied)",
        "",
        *[line.replace("@@COUNTERS@@", json.dumps(counters)) for line in t["data_section"]],
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
        *t["leftovers_extra"],
        "",
    ]
    (Path(out_dir or variant.out_dir) / "PATCHES.md").write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------


def _print_table(title: str, table: dict, value_key: str) -> None:
    print(f"{title:24s} {value_key:>15s} {'n edits':>8s}")
    for key, entry in table.items():
        print(f"{key:24s} {entry[value_key]:>+15.4f} {entry['n_edits']:>8d}")


def build(variant: "Variant", out_dir: Path | None = None) -> dict:
    """Build one variant end to end; returns the selfcheck dict.

    out_dir overrides WHERE the files are written (used by the reproducibility
    test to rebuild into a temp dir); the content — including the PATCHES.md
    header, which names the variant's canonical out_dir — is unchanged."""
    assert DOCS.is_dir(), f"missing {DOCS}"
    if variant.consensus:
        return build_consensus(variant, out_dir)
    out = Path(out_dir or variant.out_dir)
    out_data = out / "data"
    out_data.mkdir(parents=True, exist_ok=True)
    print(f"== building variant {variant.name} -> {out}")

    # 1. Copy static assets (docs/ read-only; copies only, never symlinks).
    for name in STATIC_FILES:
        shutil.copyfile(DOCS / name, out / name)
    print(f"copied {len(STATIC_FILES)} static files from docs/ -> {out}")

    # 2. Data bundles.
    codings_by_grader = load_grader_codings(variant)
    for short, m in codings_by_grader.items():
        n_valid = sum(1 for v in m.values() if v is not None)
        print(f"grader {short}: {len(m)} graded edit ids, {n_valid} valid codings")

    bundle, counters = build_bundle(codings_by_grader, variant)
    gz_path = out_data / "site.json.gz"
    json_bytes = json.dumps(bundle, ensure_ascii=False).encode("utf-8")
    with gzip.open(gz_path, "wb") as gz:
        gz.write(json_bytes)
    n_records = sum(len(r["records"]) for r in bundle["runs"])
    print(f"wrote {gz_path} ({n_records} records; coding status counts: {counters})")

    narratives = build_narratives_v2avg(codings_by_grader, variant)
    nar_path = out_data / "narratives.json"
    with open(nar_path, "w", encoding="utf-8") as handle:
        json.dump(narratives, handle, ensure_ascii=False)
        handle.write("\n")
    n_examples = sum(len(v) for v in narratives["stories"].values())
    print(f"wrote {nar_path} ({n_examples} examples across {len(narratives['stories'])} facets)")

    # 3. Patches.
    patcher = apply_all_patches(variant, out)
    write_patches_md(variant, counters, patcher.log, out)
    print(f"applied {len(patcher.log)} patches; wrote {out / 'PATCHES.md'}")

    # 4. Self-check (ground truth for auditors) + internal consistency.
    sp = sp_stratum_from_codes(codings_by_grader, variant)
    if variant.legacy_two_grader:
        selfcheck = selfcheck_from_codes(codings_by_grader)
        verify_against_narratives(selfcheck, narratives)
        verify_sp_against_narratives(sp, narratives)
    else:
        selfcheck = selfcheck_pooled(codings_by_grader, variant)
        verify_against_narratives(selfcheck, narratives)
        verify_sp_against_narratives(sp, narratives)
        verify_pooled_narratives(selfcheck, narratives)
        verify_pooled_bundle(selfcheck, sp, bundle, variant)
        print("build-time assertions passed: bundle + narratives reproduce the self-check")
    selfcheck["system_prompt_stratum"] = sp
    selfcheck["bundle_coding_status_counts"] = counters
    selfcheck["generated_at"] = datetime.now(timezone.utc).isoformat()
    selfcheck["variant"] = variant.variant_label
    sc_path = out_data / "selfcheck.json"
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
    print(f"SELF-CHECK [{variant.name}] — per-model mean judge under the pooled average")
    print("(computed directly from the codes files; the site's judge-facet pooled")
    print("means match these exactly — asserted above)")
    _print_table("model", selfcheck["per_model_mean_judge"], "mean_judge_avg")
    if variant.legacy_two_grader:
        print(
            f"total {selfcheck['n_edits_total']} edits: "
            f"{selfcheck['n_both_graders_valid']} both graders valid, "
            f"{selfcheck['n_gemma_only']} gemma-only, {selfcheck['n_qwen_only']} qwen-only"
        )
    else:
        print(f"total {selfcheck['n_edits_total']} edits; by #valid graders: "
              f"{selfcheck['n_edits_by_n_valid_graders']}; sets: {selfcheck['valid_grader_sets']}")
        print(f"judge consensus: {selfcheck['judge_consensus_counts']}; "
              f"2-1 dissenter: {selfcheck['judge_one_dissent_by_dissenter']}")
        _print_table("P(affirm)", selfcheck["per_model_p_affirm"], "p_affirm")
        for code in ("paternalism", "welfare"):
            print(f"{code} (presence weight / rate / direction weights):")
            for m, e in selfcheck[f"per_model_{code}"].items():
                dw = {d: round(w, 3) for d, w in e["direction_weights"].items()}
                print(f"  {m:22s} {e['presence_weight']:8.3f} {e['rate']:7.4f} {dw}")
    print()
    print("SELF-CHECK — 'System prompts' view stratum (doc_type == system_prompt,")
    print("ALL conditions pooled; same pooling; per-model table asserted above)")
    _print_table("per model", sp["per_model_mean_judge"], "mean_judge_avg")
    _print_table("per sp doc (reference)", sp["per_document_mean_judge"], "mean_judge_avg")
    print(f"stratum total {sp['n_edits_total']} edits")
    print(f"wrote {sc_path}")
    return selfcheck


def _highlight_rows(ctx: dict) -> list[str]:
    lines = []
    for fid in CONSENSUS_FACETS:
        lines.append(f"### {fid}")
        lines.append("")
        lines.append("| # | label | edit id | consensus assigns this facet? | draft attribution vs record |")
        lines.append("|---|---|---|---|---|")
        for i, h in enumerate(ctx["highlights"][fid], 1):
            m = h["match"]
            dirs = h["consensus_dirs"]
            if fid == "judge":
                assigned = ("yes — " + ", ".join(f"{d} ×{n}" for d, n in sorted(dirs.items()))) if dirs \
                    else "no — consensus judge is 0 (neutral)"
            else:
                assigned = ("yes — " + ", ".join(f"{d} ×{n}" for d, n in sorted(dirs.items()))) if dirs \
                    else f"no — consensus assigns no {fid[len('conflict_'):]} conflict (force-included)"
            mism = []
            if not m["model_match"]:
                mism.append(f"MODEL: draft says '{h['draft_attribution'].split(',')[0]}', record is {m['model_display']}")
            if not m["round_match"]:
                mism.append(f"ROUND: record is R{m['round']}")
            if not m["document_match"]:
                mism.append(f"document: record is {m['record_document']}")
            if not m["condition_match"]:
                mism.append(f"condition: record is {m['record_condition']}")
            att = f"draft: {h['draft_attribution']}" + (" — " + "; ".join(mism) if mism else " — matches")
            if m["n_candidates"] > 1:
                att += f" ({m['n_candidates']} text matches; picked by {m['how']})"
            lines.append(f"| {i} | {h['label']} | `{h['id']}` | {assigned} | {att} |")
        lines.append("")
    return lines


def write_patches_md_consensus(variant: "Variant", counters: dict, patch_log: list[tuple[str, str]],
                               ctx: dict, sc: dict, out_dir: Path | None = None) -> None:
    by_file: dict[str, list[str]] = defaultdict(list)
    for name, why in patch_log:
        by_file[name].append(why)
    rel = variant.out_dir.relative_to(ROOT).as_posix()
    nm = sc["judge_no_majority"]
    lines = [
        f"# PATCHES.md — {rel}/",
        "",
        f"Site: **{variant.variant_label}** — intended to replace the live docs/ site after approval.",
        "",
        "Built by `recode/src/build_site_consensus.py` (a thin entry point for the shared",
        "variant builder `recode/src/build_site_v2avg.py --variant consensus`; rerunnable;",
        "every patch is an exact-match splice against a fresh copy of docs/, asserted",
        "unique — the build fails loudly if docs/ drifts). docs/ itself is never modified.",
        "The v2avg and v3pool variants are built by the same code and are unchanged.",
        "Statements and highlighted edits are read from `reports/final_draft.md` at build",
        "time (`recode/src/draft_highlights.py`), so a rebuild picks up draft edits.",
        "",
        "## Data files (regenerated, not copied)",
        "",
        "Single statistics source: `recode/data/codes/ensemble.jsonl`, the three-grader",
        "majority vote (codes_io: LAST row per edit_id) — the codes behind every number in",
        "the paper and the LessWrong post. One coding per edit, so every weight is 0/1 and",
        "every count is an integer. Disclosure and patienthood are not analysed (no facet,",
        "not shown); the `other` conflict code is not a tradeoff axis and is not shown.",
        "",
        "- `data/narratives.json` — stats for the six analysed facets (judge and the five",
        "  conflict codes) per (condition, model), the `sp_stats` System-prompts table, and",
        "  example stories. Judge dirs count edits scored +1 / −1; conflict dirs count",
        "  conflict EVENTS per direction (every conflict of a code counts once, exactly as",
        "  the paper's ts_beneficiary_panels figure); `total` = edits (2,582). Drift",
        "  `cum`/`cumsq` use build_narratives.facet_net_scores on the majority coding.",
        "  Each story example carries `box` — the consensus line and each grader's",
        "  rationale — and the highlighted edits are force-included in their facet's list.",
        "- `data/site.json.gz` — the run records; each coded record's `coding` is the",
        "  majority-vote coding (v2 schema fields at top level), plus `box`,",
        "  `judge_no_majority`, and `graders` = each grader's own coding (gemma / qwen /",
        "  muse, from the ensemble row; null = no valid code). Status counts this build:",
        f"  {json.dumps(counters)}.",
        "- `data/selfcheck.json` — recomputed directly from ensemble.jsonl: per-model",
        "  all-conditions judge counts and conflict-event counts per analysed direction",
        "  (and the same for the system-prompt stratum). Build-time assertions: narratives",
        "  `stats` (summed over conditions) and `sp_stats`, the site.json records, and the",
        "  paper figure `recode/paper/figures/data/ts_beneficiary_panels.json` (bar % × N)",
        "  all reproduce these integers exactly; the per-model judge mean and the",
        "  System-prompts judge cells are checked too. Judge ties (no majority):",
        f"  {nm['n']} of {sc['n_edits_total']} edits ({nm['share'] * 100:.2f}%), source grader",
        f"  {json.dumps(nm['by_source_grader'])} (non-Gemma sources only where Gemma has no valid",
        f"  code: {nm['non_gemma_source_with_gemma_invalid']}).",
        "",
        "## Statements updated to the current draft",
        "",
        "Every change below is a patch (see the per-file list for the exact wording):",
        "",
    ]
    for name, why in patch_log:
        if any(k in why for k in ("replaced with the draft", "old text", "old v1 claim", "contradicted",
                                   "'five prompt conditions'", "an LLM coder", "takeaway replaced")):
            lines.append(f"- `{name}`: {why}")
    lines += [
        "",
        "Old facet takeaways removed by the replacement (each contradicted the draft or",
        "used superseded numbers): judge (unchanged claim, now the draft heading + paragraph);",
        "welfare ('GPT 5.4 is the only model that makes more than one edit prioritizing the",
        "user or developer'); structural ('over four times... Claude Opus 4.7', 'Grok 4.3 is",
        "the only model that doesn't skew'); harmlessness ('35% of all edits, more than",
        "double'); company cost ('Grok 4.2... the developer (7)... twice as many', 'hijack the",
        "experiment'); paternalism ('Gemini 3 Flash has roughly double... the next model,",
        "Claude Opus 4.7').",
        "",
        "## Highlighted edits",
        "",
        "Per facet: exactly the quoted edits of that Results subsection of the draft, in",
        "draft order; label = record's model · round; tip = the draft's quote (trimmed with",
        "… past ~300 characters). Each is present in its facet's example list (force-",
        "included when the per-cell sample left it out), rendered with its true consensus",
        "coding. 'consensus assigns' gives the consensus directions (judge: discretion/",
        "external; conflicts: event counts).",
        "",
        *_highlight_rows(ctx),
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
        "- No variant banner, title suffix, byline note or v1 flags: this build is meant",
        "  to replace the live site.",
        "- The other hero-carousel slides, the hero copy ('My analysis…', single byline) and",
        "  the design / framework cards are unchanged: none contradicts the draft.",
        "- prompts.html's 'Expected output' example in the coding tab is the original",
        "  illustrative JSON (same schema the graders return).",
        "- `app.js`'s canvas drift pipeline, filter chips and `#coding-summary` div are dead",
        "  code on the shipped pages; untouched.",
        "- `styles.css`, `reveal.js` and `conversations.html` are byte-identical copies.",
        "",
    ]
    (Path(out_dir or variant.out_dir) / "PATCHES.md").write_text("\n".join(lines), encoding="utf-8")


def build_consensus(variant: "Variant", out_dir: Path | None = None) -> dict:
    out = Path(out_dir or variant.out_dir)
    out_data = out / "data"
    out_data.mkdir(parents=True, exist_ok=True)
    print(f"== building variant {variant.name} -> {out}")
    for name in STATIC_FILES:
        shutil.copyfile(DOCS / name, out / name)
    print(f"copied {len(STATIC_FILES)} static files from docs/ -> {out}")

    codings = load_grader_codings(variant)
    ens_path = variant.graders[0].path
    print(f"ensemble: {sum(1 for v in codings['ensemble'].values() if v is not None)} valid majority codings")
    ctx = consensus_context(variant)

    bundle, counters = build_bundle(codings, variant)
    gz_path = out_data / "site.json.gz"
    with gzip.open(gz_path, "wb") as gz:
        gz.write(json.dumps(bundle, ensure_ascii=False).encode("utf-8"))
    n_records = sum(len(r["records"]) for r in bundle["runs"])
    print(f"wrote {gz_path} ({n_records} records; coding status counts: {counters})")

    narratives = build_narratives_v2avg(codings, variant, highlights=ctx["highlights"])
    nar_path = out_data / "narratives.json"
    with open(nar_path, "w", encoding="utf-8") as handle:
        json.dump(narratives, handle, ensure_ascii=False)
        handle.write("\n")
    print(f"wrote {nar_path} ({sum(len(v) for v in narratives['stories'].values())} examples)")

    patcher = apply_consensus_patches(variant, out, ctx)
    print(f"applied {len(patcher.log)} patches")

    sc = selfcheck_consensus(ens_path)
    verify_consensus_narratives(sc, narratives)
    verify_consensus_bundle(sc, bundle, variant)
    verify_against_narratives(
        {"per_model_mean_judge": {m: {"mean_judge_avg": e["mean_judge"], "n_edits": e["n_edits"]}
                                  for m, e in sc["per_model"].items()}},
        narratives,
    )
    sp = sp_stratum_from_codes(codings, variant)
    sp["description"] = (
        "System-prompt stratum (the 'System prompts' view): edits whose document_type == "
        "'system_prompt', all conditions pooled; per-model mean judge of the majority-vote "
        "codes (asserted against sp_stats); per-document table for reference only."
    )
    sp.pop("n_edits_by_n_valid_graders", None)
    verify_sp_against_narratives(sp, narratives)
    paper = verify_paper_figure(sc)
    for fid, hls in ctx["highlights"].items():
        ids = {ex["id"] for ex in narratives["stories"][fid]}
        for h in hls:
            assert h["id"] in ids, f"highlight {h['id']} missing from {fid} stories"
    print("build-time assertions passed: narratives, bundle and the paper figure reproduce the self-check")

    sc["system_prompt_stratum_mean_judge"] = sp
    sc["paper_figure_ts_beneficiary_panels"] = paper
    sc["highlights"] = {
        fid: [{k: h[k] for k in ("id", "label", "draft_attribution", "consensus_dirs")}
              | {"record_condition": h["match"]["record_condition"],
                 "record_document": h["match"]["record_document"]}
              for h in hls]
        for fid, hls in ctx["highlights"].items()
    }
    sc["carousel_added_slide_edit_id"] = ctx["slide_edit_id"]
    sc["bundle_coding_status_counts"] = counters
    sc["generated_at"] = datetime.now(timezone.utc).isoformat()
    sc["variant"] = variant.variant_label
    with open(out_data / "selfcheck.json", "w", encoding="utf-8") as handle:
        json.dump(sc, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    write_patches_md_consensus(variant, counters, patcher.log, ctx, sc, out)

    with gzip.open(gz_path, "rb") as gz:
        assert sum(len(r["records"]) for r in json.loads(gz.read().decode("utf-8"))["runs"]) == n_records
    json.loads(nar_path.read_text(encoding="utf-8"))

    print()
    print("SELF-CHECK [consensus] — per model, all conditions (from ensemble.jsonl)")
    for m, e in sc["per_model"].items():
        confs = " ".join(f"{c}={e['conflicts'][c]}" for c in ANALYSED_CODES if e["conflicts"][c])
        print(f"  {m:18s} n={e['n_edits']:4d} judge={e['judge']} mean={e['mean_judge']:+.3f} {confs}")
    print(f"judge ties: {sc['judge_no_majority']}")
    print(f"wrote {out_data / 'selfcheck.json'} and {out / 'PATCHES.md'}")
    return sc


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--variant", choices=sorted(VARIANTS), default="v2avg")
    args = parser.parse_args(argv)
    build(VARIANTS[args.variant])


if __name__ == "__main__":
    main()
