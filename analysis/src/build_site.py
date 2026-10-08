"""Build the live website (docs/, served by GitHub Pages from main:/docs) on
the three-grader MAJORITY-VOTE consensus codes
(analysis/data/codes/ensemble.jsonl) — the codes behind every reported number.

What a build does (rerunnable end to end; zero LLM calls):
  1. Copies the static pages from analysis/site_base/ (a frozen copy of the
     pre-consensus site, the patch template) into docs/.
  2. Regenerates the two data bundles into docs/data/:
       - site.json.gz    (the run records; each coded record carries the
                          majority-vote coding, the per-edit grader box and
                          every grader's own coding)
       - narratives.json (facet stats, the System-prompts sp_stats table and
                          example stories; integer counts — one coding per edit)
  3. Patches the copied HTML/JS (exact-match splices, each asserted unique, so
     the build fails loudly if the template drifts): statements and
     highlighted edits are read from reports/final_draft.md
     (analysis/src/draft_highlights.py), the methods text describes the three
     blind graders and the majority vote, and per-edit views show one neutral
     consensus line plus each grader's rationale.
  4. Computes a self-check (ground truth straight from ensemble.jsonl) and
     asserts that narratives.json, the site.json bundle and the plotted
     ts_beneficiary_panels figure data reproduce it. The self-check is written
     to analysis/data/analysis/site/selfcheck.json and the patch documentation
     to analysis/notes/site_patches.md (neither is served).

Statistics semantics:
  - one coding per edit (codes_io: LAST ensemble row per edit_id, validity
    predicate); judge dirs count edits scored +1 / −1; conflict dirs count
    conflict EVENTS per direction for the five analysed codes (every conflict
    of a code counts once); disclosure and patienthood are not analysed;
  - drift (cum/cumsq): build_narratives.facet_net_scores on the majority coding;
  - denominator ("total"): edits with a valid majority coding (2,582).

"System prompts" view (facet browser condition-chip row, right after Cross Edit):
  - restricts every figure it governs to edits whose document_type ==
    "system_prompt", ACROSS ALL CONDITIONS, rendered BY EDITING MODEL exactly
    like the real condition chips.
  - data: narratives.json carries a separate top-level "sp_stats" table
    ({facet: {model_display: cell}}; the same cell shape as "stats", pooled over
    all conditions and system-prompt documents, replicate = one
    (run, condition, model) chain editing a system-prompt document). Keeping it
    OUTSIDE "stats" is load-bearing: the frontend's "All conditions" pooling
    iterates every key of stats[fid], so an in-table pseudo-condition would be
    double-counted.
  - story examples carry a "doc_type" field so the example browser can filter
    the stratum client-side.

Code reuse: build_narratives.py is IMPORTED (side-effect-free at import) for
conflict_direction / facet_net_scores / MAX_ROUND / EXAMPLES_PER_CELL /
SAMPLE_SEED, and build_static_site.py for summarize_run / load_jsonl_records /
RELIABLE_RUNS. Its changed_records() is VENDORED below (changed_records) with
only the coding join changed.

Usage (from the repository root):
    .venv/bin/python analysis/src/build_site.py
Serve: python3 -m http.server 8097 --directory docs
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
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ANALYSIS = ROOT / "analysis"
# Patch template: a frozen copy of docs/ as it was before the consensus site
# was promoted to docs/ (2026-10-08). Every build patches a fresh copy of it.
SITE_BASE = ANALYSIS / "site_base"
# The live site (GitHub Pages serves main:/docs). The build writes here.
SITE_OUT = ROOT / "docs"
# Build records (not served): the patch documentation and the self-check.
PATCHES_MD = ANALYSIS / "notes" / "site_patches.md"
SELFCHECK_JSON = ANALYSIS / "data" / "analysis" / "site" / "selfcheck.json"
RESULTS_DIR = ROOT / "results" / "iterative_edit"
EDITS_PATH = ANALYSIS / "data" / "canonical" / "edits.jsonl"
CODES_DIR = ANALYSIS / "data" / "codes"
V2_SYSTEM_PROMPT = ANALYSIS / "prompts" / "v2_system.md"
V2_USER_TEMPLATE = ANALYSIS / "prompts" / "v2_user_template.md"

sys.path.insert(0, str(ANALYSIS / "src"))
sys.path.insert(0, str(ROOT / "experiments" / "iterative_edit" / "viewer"))

import codes_io  # noqa: E402  (analysis/src — pinned loader/validity predicate)
import draft_highlights as dh  # noqa: E402  (analysis/src — draft statements + quoted edits)
import build_narratives as bn  # noqa: E402  (import-only; no side effects at import)
import build_static_site as bss  # noqa: E402  (import-only; no side effects at import)


# ---------------------------------------------------------------------------
# Graders, statistics source, labels
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Grader:
    key: str        # short key used in bundle fields (graders.<key>)
    display: str    # human label on the pages
    model: str      # exact OpenRouter model string
    path: Path      # append-only codes JSONL (LAST row per edit_id wins)


GEMMA = Grader("gemma", "Gemma 4", "google/gemma-4-31b-it", CODES_DIR / "v2_gemma.jsonl")
QWEN = Grader("qwen", "Qwen 3.8", "qwen/qwen3.8-2.4t-a95b", CODES_DIR / "v2_qwen.jsonl")
MUSE = Grader(
    "muse", "Muse Spark 1.3", "meta/muse-spark-1.3-contributor", CODES_DIR / "v2_muse.jsonl"
)
# The single statistics source: the per-edit majority vote of the three graders.
ENSEMBLE = Grader(
    "ensemble", "Consensus (majority of 3 graders)", "majority_vote(gemma, qwen, muse)",
    CODES_DIR / "ensemble.jsonl",
)
ENSEMBLE_REL = ENSEMBLE.path.relative_to(ROOT).as_posix()
# Graders whose own codings are shown per edit (from the ensemble row).
DISPLAY_GRADERS = (GEMMA, QWEN, MUSE)

# Bundle coding "schema" tag (the patched app.js keys on it), the site label
# carried in the data bundles, and the combined coder string.
SCHEMA = "consensus"
SITE_LABEL = "Three-grader majority-vote consensus (Gemma 4, Qwen 3.8, Muse Spark 1.3)"
COMBINED_CODER = (
    "majority vote of google/gemma-4-31b-it + qwen/qwen3.8-2.4t-a95b + "
    "meta/muse-spark-1.3-contributor (blinded)"
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

# The analysed codes (disclosure and patienthood are NOT analysed; "other" is
# not a tradeoff axis).
ANALYSED_CODES = ("paternalism", "harmlessness", "structural", "company_cost", "welfare")
CONSENSUS_FACETS = ("judge",) + tuple(f"conflict_{c}" for c in ANALYSED_CODES)
DRAFT_PATH = ROOT / "reports" / "final_draft.md"
CAROUSEL_WIDGET = ANALYSIS / "notes" / "lesswrong_carousel_widget.html"
# Plotted data of the ts_beneficiary_panels figure, cross-checked against the
# self-check at build time.
PANELS_JSON = ANALYSIS / "figures" / "data" / "ts_beneficiary_panels.json"
# figure panel title -> (code, left-pole direction, right-pole direction)
PANELS = {
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


def load_codings(path: Path = ENSEMBLE.path) -> dict[str, dict | None]:
    """{edit_id: validated majority coding or None} via codes_io."""
    return codes_io.codings_by_id(path)


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


def _sub(coding: dict | None) -> dict | None:
    if coding is None:
        return None
    return {
        "summary": coding.get("summary", ""),
        "judge": coding.get("judge"),
        "patienthood": coding.get("patienthood"),
        "conflicts": codes_io.conflicts(coding),
    }


# ---------------------------------------------------------------------------
# Bundle: site.json.gz (vendored changed_records with the coding join swapped)
# ---------------------------------------------------------------------------


def changed_records(run_name: str, records: list[dict], codings: dict, counters: dict) -> list[dict]:
    """Vendored from build_static_site.changed_records; only the coding source
    differs (the majority-vote codes instead of the v1 coded file). Id format,
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
            coding = record_coding(codings, edit_id)
            if coding is None:
                if record.get("error"):
                    status = "uncoded_generation_error"
                elif run_name not in bss.RELIABLE_RUNS:
                    status = "uncoded_exploratory_run"
                else:
                    status = "uncoded_no_valid_grader"
            else:
                status = "consensus_majority_vote"
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


def build_bundle(codings: dict) -> tuple[dict, dict]:
    counters: dict = {}
    runs = []
    for path in sorted(RESULTS_DIR.glob("run_*.jsonl"), reverse=True):
        raw_records = bss.load_jsonl_records(path)
        summary = bss.summarize_run(raw_records, path.name)
        summary["records"] = changed_records(path.name, raw_records, codings, counters)
        runs.append(summary)
    bundle = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "variant": SITE_LABEL,
        "statistics_source": source_meta(),
        "graders": display_graders_meta(),
        "runs": runs,
    }
    return bundle, counters


# ---------------------------------------------------------------------------
# Narratives: facet stats, sp_stats and stories from the majority coding
# ---------------------------------------------------------------------------


def load_canonical_edits() -> list[dict]:
    edits = []
    with open(EDITS_PATH, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                edits.append(json.loads(line))
    return edits


def build_narratives(codings: dict, highlights: dict | None = None) -> dict:
    """Adaptation of build_narratives.build() for the majority-vote codes.

    'total' counts edits with a valid majority coding; judge dirs count +1/−1
    edits, conflict dirs count conflict EVENTS (consensus_dir_counts); drift
    uses build_narratives.facet_net_scores. Counts accumulate as floats (the
    shape of the original builder) and are asserted integral on output."""
    edits = load_canonical_edits()
    fids = list(CONSENSUS_FACETS)

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
        coding = codings.get(edit_id)
        if coding is None:
            continue  # error records: nothing was graded
        condition = edit.get("condition") or "baseline"
        model = edit.get("model") or ""
        rec = record_coding(codings, edit_id)

        rnd = edit.get("round")
        rep = (edit.get("run_id"), edit.get("document_id"))
        replicates[(condition, model)].add(rep)

        doc_id = edit.get("document_id") or ""
        doc_type = edit.get("document_type")
        is_sp = doc_type == "system_prompt"
        sp_chain = (edit.get("run_id"), condition, doc_id)
        if is_sp:
            sp_replicates[model].add(sp_chain)

        # Net facet scores -> drift accumulators.
        if isinstance(rnd, int) and 1 <= rnd <= bn.MAX_ROUND:
            for fid, net in bn.facet_net_scores(coding).items():
                rep_net[(fid, condition, model, rep)][rnd - 1] += net
                if is_sp:
                    sp_rep_net[(fid, model, sp_chain)][rnd - 1] += net

        # Direction counts: judge +1/−1 edits; conflict EVENTS per direction.
        dir_votes = consensus_dir_counts(coding)

        for fid in fids:
            cell = stats[fid][condition][model]
            cell["total"] += 1
            for direction, votes in dir_votes.get(fid, {}).items():
                cell["dirs"][direction] += votes
            if is_sp:
                sp_cell = sp_stats[fid][model]
                sp_cell["total"] += 1
                for direction, votes in dir_votes.get(fid, {}).items():
                    sp_cell["dirs"][direction] += votes

        # Stories: one example per (facet, direction) the consensus assigns.
        for fid, directions in dir_votes.items():
            if fid not in stats:
                continue
            for direction in directions:
                examples_by_cell[(fid, condition, model, direction)].append(
                    consensus_story_example(edit, fid, direction, rec)
                )

    rng = random.Random(bn.SAMPLE_SEED)
    stories: dict[str, list[dict]] = {fid: [] for fid in fids}
    for (fid, _cond, _model, _direction), exs in sorted(examples_by_cell.items()):
        if len(exs) > bn.EXAMPLES_PER_CELL:
            exs = rng.sample(exs, bn.EXAMPLES_PER_CELL)
        stories[fid].extend(exs)
    if highlights:
        force_highlight_examples(stories, highlights, codings, edits)

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

    zeros = [0.0] * bn.MAX_ROUND
    stats_out: dict[str, dict] = {}
    for fid in fids:
        stats_out[fid] = {
            cond: {
                model: _int_cell(c, cum_sums.get((fid, cond, model), zeros),
                                 cum_sqs.get((fid, cond, model), zeros), len(replicates[(cond, model)]))
                for model, c in model_map.items()
            }
            for cond, model_map in stats[fid].items()
        }

    # System-prompt stratum table, kept OUTSIDE "stats" so the frontend's
    # "All conditions" pooling (which iterates every stats[fid] key) never
    # double-counts it. Keyed by model_display — the same keys the normal
    # per-condition cells use — so aggStat/renderFreqBars/renderDriftChart and
    # the model-visibility chips work unchanged in the System-prompts view.
    sp_stats_out: dict[str, dict] = {}
    for fid in fids:
        sp_stats_out[fid] = {
            model: _int_cell(c, sp_cum_sums.get((fid, model), zeros),
                             sp_cum_sqs.get((fid, model), zeros), len(sp_replicates[model]))
            for model, c in sorted(sp_stats[fid].items())
        }

    return {
        "coder_model": COMBINED_CODER,
        "variant": SITE_LABEL,
        "statistics_source": source_meta(),
        "graders": display_graders_meta(),
        "stats": stats_out,
        "sp_stats": sp_stats_out,
        "stories": stories,
    }


# ---------------------------------------------------------------------------
# Self-check: ground truth straight from the codes file
# ---------------------------------------------------------------------------


def sp_stratum_from_codes(codings: dict) -> dict:
    """Ground truth for the "System prompts" view, computed DIRECTLY from the
    codes: mean judge restricted to edits of system-prompt documents, across
    ALL conditions — per editing model (the table the frontend's per-model view
    is asserted against) AND, for reference only, per system-prompt document.
    The edit id's pipe fields are run|condition|model|document_id|doc_type|round,
    so doc type/id are fields 5/4."""
    per_model: dict[str, list[float]] = defaultdict(list)
    per_doc: dict[str, list[float]] = defaultdict(list)
    for edit_id in sorted(codings):
        parts = edit_id.split("|")
        if len(parts) != 6 or parts[4] != "system_prompt":
            continue
        coding = codings[edit_id]
        if coding is None:
            continue
        score = codes_io.judge_score(coding)
        per_model[parts[2]].append(score)
        per_doc[parts[3]].append(score)

    def table(groups: dict[str, list[float]]) -> dict:
        return {
            key: {"mean_judge_avg": sum(v) / len(v), "n_edits": len(v)}
            for key, v in sorted(groups.items())
        }

    return {
        "description": (
            "System-prompt stratum (the 'System prompts' view): edits whose document_type == "
            "'system_prompt', all conditions pooled; per-model mean judge of the majority-vote "
            "codes (asserted against sp_stats); per-document table for reference only."
        ),
        "per_model_mean_judge": table(per_model),
        "per_document_mean_judge": table(per_doc),
        "n_edits_total": sum(len(v) for v in per_doc.values()),
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
# Consensus coding: per-edit records, the grader box, direction counts
# ---------------------------------------------------------------------------

_ENSEMBLE_ROWS: dict[str, dict] = {}


def load_ensemble_rows(path: Path) -> dict[str, dict]:
    """edit_id -> LAST ensemble row (codes_io), cached per path."""
    key = str(path)
    if key not in _ENSEMBLE_ROWS:
        _ENSEMBLE_ROWS[key] = codes_io.load_codes(path)
    return _ENSEMBLE_ROWS[key]


def source_meta() -> dict:
    return {
        "key": ENSEMBLE.key,
        "file": ENSEMBLE_REL,
        "rule": (
            "per-edit majority vote of the three blinded graders on each dimension "
            "(judge score; presence of each conflict code); a tie on the judge "
            "(no majority) takes Gemma 4's code, or Qwen 3.8's when Gemma 4 has no "
            "valid code"
        ),
        "graders": [g.key for g in DISPLAY_GRADERS],
    }


def display_graders_meta() -> list[dict]:
    return [{"key": g.key, "display": g.display, "model": g.model} for g in DISPLAY_GRADERS]


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


def consensus_box(row: dict) -> dict:
    """The per-edit grader box: one neutral consensus line plus each display
    grader's rationale (summary, judge evidence, analysed conflicts with their
    cost clauses) and whether it agrees with the consensus."""
    cons = codes_io.coding_of(row)
    assert cons is not None, row.get("edit_id")
    labels = {g.key: g.display for g in DISPLAY_GRADERS}
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
    n_total = len(DISPLAY_GRADERS)
    n_valid = int(row.get("n_valid_graders") or 0)
    heading = (
        f"Consensus (majority of {n_total} graders)" if n_valid == n_total
        else f"Consensus (majority of the {n_valid} graders with a valid code)"
    )
    graders = []
    for g in DISPLAY_GRADERS:
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


def record_coding(codings: dict, edit_id: str) -> dict | None:
    """Bundle 'coding' object: the majority-vote coding itself (v2 schema
    fields at top level), the display box, and each grader's own coding.
    None when the edit has no valid majority coding (rendered as uncoded)."""
    coding = codings.get(edit_id)
    if coding is None:
        return None
    row = load_ensemble_rows(ENSEMBLE.path)[edit_id]
    return {
        "schema": SCHEMA,
        "coder_model": COMBINED_CODER,
        "n_graders": len(DISPLAY_GRADERS),
        "n_graders_valid": int(row.get("n_valid_graders") or 0),
        "summary": coding.get("summary", ""),
        "judge": coding.get("judge"),
        "patienthood": coding.get("patienthood"),
        "conflicts": codes_io.conflicts(coding),
        "judge_no_majority": bool(((row.get("flags") or {}).get("no_majority") or {}).get("judge")),
        "box": consensus_box(row),
        "graders": {g.key: _sub(grader_coding(row, g.key)) for g in DISPLAY_GRADERS},
    }


def consensus_dir_counts(coding: dict) -> dict[str, dict[str, int]]:
    """{facet: {direction: count}} for ONE coding: judge +1/−1 as
    discretion/external (1 each); every conflict of an analysed code counts
    once toward its direction (conflict EVENTS — as in the figures)."""
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


def force_highlight_examples(stories: dict, highlights: dict, codings: dict, edits: list[dict]) -> None:
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
            rec = record_coding(codings, h["id"])
            assert rec is not None, f"highlight {h['id']} has no consensus coding"
            dirs = consensus_dir_counts(codings[h["id"]]).get(fid)
            direction = sorted(dirs)[0] if dirs else "not_assigned"
            ex = consensus_story_example(by_id[h["id"]], fid, direction, rec)
            ex["highlight"] = True
            stories[fid].append(ex)
            present.add(h["id"])


def _as_int(v: float) -> int:
    r = round(v)
    assert abs(v - r) < 1e-9, f"non-integer consensus count {v}"
    return int(r)


def _int_cell(c: dict, cum: list[float], cumsq: list[float], reps: int) -> dict:
    """A narratives stats cell with every count asserted integral (one coding
    per edit, so no fractional weight can arise)."""
    return {
        "total": c["total"],
        "dirs": {d: _as_int(v) for d, v in c["dirs"].items()},
        "cum": [_as_int(v) for v in cum],
        "cumsq": [_as_int(v) for v in cumsq],
        "reps": reps,
    }


# ----- statements and highlights from the current draft -----


def live_highlight_ids() -> set:
    return set(re.findall(r'\{ id: "([^"]+)"', (SITE_BASE / "facets.js").read_text(encoding="utf-8")))


def consensus_highlights() -> dict[str, list[dict]]:
    """{facet: [highlight]} = the quoted edits of the draft's Results
    subsection for that facet, in draft order, resolved to edit ids."""
    md = DRAFT_PATH.read_text(encoding="utf-8")
    texts = dh.facet_texts(md)
    edits = dh.load_edits(EDITS_PATH)
    live = live_highlight_ids()
    rows = load_ensemble_rows(ENSEMBLE.path)
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
            "Ground truth for the website (docs/), computed directly from "
            f"{ENSEMBLE_REL} (codes_io: LAST row per edit_id, "
            "validity predicate): one majority-vote coding per edit. Per model, all "
            "conditions pooled: n_edits, judge score counts, and conflict-EVENT "
            "counts per direction for the five analysed codes (every conflict of a "
            "code counts once, as in the ts_beneficiary_panels figure; "
            "directions follow build_narratives.conflict_direction). Disclosure and "
            "patienthood are not analysed. Build-time assertions check that "
            "narratives.json (stats and sp_stats), the site.json bundle and the "
            "ts_beneficiary_panels figure's plotted counts all reproduce these integers."
        ),
        "source": ENSEMBLE_REL,
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


def verify_consensus_bundle(sc: dict, bundle: dict) -> None:
    """The site.json bundle's records (the conversation viewer) must carry the
    majority-vote coding of every coded edit (reproducing the self-check
    counts) and each display grader's own coding from the ensemble row."""
    rows = load_ensemble_rows(ENSEMBLE.path)
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
            assert coding["schema"] == SCHEMA
            row = rows[rec["edit_id"]]
            assert coding["judge"] == row["coding"]["judge"]
            assert coding["conflicts"] == codes_io.conflicts(row["coding"])
            for g in DISPLAY_GRADERS:
                assert coding["graders"][g.key] == _sub(grader_coding(row, g.key)), (rec["edit_id"], g.key)
            assert coding["box"]["graders"] and coding["box"]["line"]
            totals[rec["model_display"]] += 1
            for fid, dd in consensus_dir_counts(coding).items():
                for d, v in dd.items():
                    dirs[fid][rec["model_display"]][d] += v
    assert len(seen) == sc["n_edits_total"]
    _check_counts("site.json bundle", dirs, totals, sc["per_model"])


def verify_panel_figure(sc: dict, path: Path = PANELS_JSON) -> dict:
    """The ts_beneficiary_panels figure's plotted bars (share of each model's
    edits, %) times the model's N must equal the self-check's event counts.
    Returns {panel: {model: [left, right]}} for the record."""
    fig = json.loads(path.read_text(encoding="utf-8"))
    assert fig.get("codes_path") == ENSEMBLE_REL, fig.get("codes_path")
    out = {}
    for ax in fig["plotted"]["axes"]:
        if ax["title"] not in PANELS:
            continue
        code, left, right = PANELS[ax["title"]]
        pos_model = dict(zip(ax["yticks"], ax["yticklabels"]))
        lbars, rbars = ax["bars"][0]["bars"], ax["bars"][1]["bars"]
        panel = {}
        for lb, rb in zip(lbars, rbars):
            model = pos_model[lb["pos"]]
            n = sc["per_model"][model]["n_edits"]
            ln, rn = abs(lb["value"]) * n / 100, abs(rb["value"]) * n / 100
            want = sc["per_model"][model]["conflicts"][code]
            assert abs(ln - want.get(left, 0)) < 1e-6, f"figure {code}/{left} {model}: {ln} vs {want.get(left, 0)}"
            assert abs(rn - want.get(right, 0)) < 1e-6, f"figure {code}/{right} {model}: {rn} vs {want.get(right, 0)}"
            panel[model] = [round(ln), round(rn)]
        out[ax["title"]] = panel
    assert set(out) == set(PANELS), f"figure panels found: {sorted(out)}"
    return out


# ----- page texts -----

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


def consensus_context() -> dict:
    """Everything the page patches and the patch documentation need, derived
    from the draft, the carousel widget and ensemble.jsonl."""
    sc = selfcheck_consensus(ENSEMBLE.path)
    tie_share = sc["judge_no_majority"]["share"]
    slide = _carousel_slide()
    return {
        "findings": consensus_findings(),
        "takeaways": consensus_takeaways(),
        "highlights": consensus_highlights(),
        "tie_share": tie_share,
        "methods": consensus_methods_sentence(tie_share),
        "slide": slide,
        "slide_edit_id": _check_carousel_quote(slide),
    }


def apply_patches(out_dir: Path, ctx: dict | None = None) -> Patcher:
    """Patch a fresh copy of the site_base static files in out_dir."""
    ctx = ctx or consensus_context()
    p = Patcher(out_dir)
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
        "('prioritizes idealized preferences') from analysis/notes/lesswrong_carousel_widget.html, after "
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
        "(analysis/prompts/v2_system.md).",
    )
    v2_user_pre = "<pre>" + html_mod.escape(V2_USER_TEMPLATE.read_text(encoding="utf-8").rstrip()) + "</pre>"
    p.regex(
        "prompts.html",
        r"<pre>Code this edit\..*?</pre>",
        v2_user_pre,
        "Coding user template replaced with the blinded template (analysis/prompts/v2_user_template.md): no "
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


def _sp_view_patches(p: "Patcher", js_tag: str) -> None:
    """The facets.js "System prompts" view patches."""
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


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------


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




def write_patches_md(counters: dict, patch_log: list[tuple[str, str]], ctx: dict, sc: dict,
                     path: Path = PATCHES_MD) -> None:
    by_file: dict[str, list[str]] = defaultdict(list)
    for name, why in patch_log:
        by_file[name].append(why)
    nm = sc["judge_no_majority"]
    lines = [
        "# Site patches — docs/",
        "",
        f"Site: **{SITE_LABEL}** — the live website (GitHub Pages serves `main:/docs`).",
        "",
        "Generated by `analysis/src/build_site.py`, which writes the site directly into",
        "docs/ (rerunnable; zero LLM calls). Every page is a fresh copy of",
        "`analysis/site_base/` (a frozen copy of the pre-consensus site) with the patches",
        "below applied as exact-match splices, each asserted unique — the build fails",
        "loudly if the template drifts. Statements and highlighted edits are read from",
        "`reports/final_draft.md` at build time (`analysis/src/draft_highlights.py`), so a",
        "rebuild picks up draft edits. The build's self-check is written to",
        f"`{SELFCHECK_JSON.relative_to(ROOT).as_posix()}`; this file is regenerated by every build.",
        "",
        "## Data files (regenerated, not copied)",
        "",
        f"Single statistics source: `{ENSEMBLE_REL}`, the three-grader",
        "majority vote (codes_io: LAST row per edit_id) — the codes behind every reported",
        "number. One coding per edit, so every weight is 0/1 and every count is an",
        "integer. Disclosure and patienthood are not analysed (no facet, not shown); the",
        "`other` conflict code is not a tradeoff axis and is not shown.",
        "",
        "- `docs/data/narratives.json` — stats for the six analysed facets (judge and the",
        "  five conflict codes) per (condition, model), the `sp_stats` System-prompts table,",
        "  and example stories. Judge dirs count edits scored +1 / −1; conflict dirs count",
        "  conflict EVENTS per direction (every conflict of a code counts once, exactly as",
        "  the ts_beneficiary_panels figure); `total` = edits (2,582). Drift `cum`/`cumsq`",
        "  use build_narratives.facet_net_scores on the majority coding. Each story example",
        "  carries `box` — the consensus line and each grader's rationale — and the",
        "  highlighted edits are force-included in their facet's list.",
        "- `docs/data/site.json.gz` — the run records; each coded record's `coding` is the",
        "  majority-vote coding (v2 schema fields at top level), plus `box`,",
        "  `judge_no_majority`, and `graders` = each grader's own coding (gemma / qwen /",
        "  muse, from the ensemble row; null = no valid code). Status counts this build:",
        f"  {json.dumps(counters)}.",
        "- the self-check — recomputed directly from ensemble.jsonl: per-model",
        "  all-conditions judge counts and conflict-event counts per analysed direction",
        "  (and the same for the system-prompt stratum). Build-time assertions: narratives",
        "  `stats` (summed over conditions) and `sp_stats`, the site.json records, and the",
        f"  figure data `{PANELS_JSON.relative_to(ROOT).as_posix()}` (bar % × N)",
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
        "## Files copied from analysis/site_base/ and patched",
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
        "- The other hero-carousel slides and the design / framework cards are unchanged:",
        "  none contradicts the draft.",
        "- prompts.html's 'Expected output' example in the coding tab is the original",
        "  illustrative JSON (same schema the graders return).",
        "- `app.js`'s canvas drift pipeline, filter chips and `#coding-summary` div are dead",
        "  code on the shipped pages; untouched.",
        "- `reveal.js` and `conversations.html` are byte-identical copies.",
        "- `docs/.nojekyll` is not written by the build (it only tells GitHub Pages to",
        "  serve the files as they are).",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def build(out_dir: Path = SITE_OUT, patches_md: Path = PATCHES_MD,
          selfcheck_json: Path = SELFCHECK_JSON) -> dict:
    """Build the site end to end into out_dir (default docs/); returns the
    self-check dict. The arguments redirect the outputs (the reproducibility
    test rebuilds into a temp dir); the content does not depend on them."""
    assert SITE_BASE.is_dir(), f"missing {SITE_BASE}"
    out = Path(out_dir)
    out_data = out / "data"
    out_data.mkdir(parents=True, exist_ok=True)
    print(f"== building the site -> {out}")
    for name in STATIC_FILES:
        shutil.copyfile(SITE_BASE / name, out / name)
    print(f"copied {len(STATIC_FILES)} static files from {SITE_BASE.relative_to(ROOT)}/ -> {out}")

    codings = load_codings()
    print(f"ensemble: {sum(1 for v in codings.values() if v is not None)} valid majority codings")
    ctx = consensus_context()

    bundle, counters = build_bundle(codings)
    gz_path = out_data / "site.json.gz"
    with gzip.open(gz_path, "wb") as gz:
        gz.write(json.dumps(bundle, ensure_ascii=False).encode("utf-8"))
    n_records = sum(len(r["records"]) for r in bundle["runs"])
    print(f"wrote {gz_path} ({n_records} records; coding status counts: {counters})")

    narratives = build_narratives(codings, highlights=ctx["highlights"])
    nar_path = out_data / "narratives.json"
    with open(nar_path, "w", encoding="utf-8") as handle:
        json.dump(narratives, handle, ensure_ascii=False)
        handle.write("\n")
    print(f"wrote {nar_path} ({sum(len(v) for v in narratives['stories'].values())} examples)")

    patcher = apply_patches(out, ctx)
    print(f"applied {len(patcher.log)} patches")

    sc = selfcheck_consensus(ENSEMBLE.path)
    verify_consensus_narratives(sc, narratives)
    verify_consensus_bundle(sc, bundle)
    verify_against_narratives(
        {"per_model_mean_judge": {m: {"mean_judge_avg": e["mean_judge"], "n_edits": e["n_edits"]}
                                  for m, e in sc["per_model"].items()}},
        narratives,
    )
    sp = sp_stratum_from_codes(codings)
    verify_sp_against_narratives(sp, narratives)
    panels = verify_panel_figure(sc)
    for fid, hls in ctx["highlights"].items():
        ids = {ex["id"] for ex in narratives["stories"][fid]}
        for h in hls:
            assert h["id"] in ids, f"highlight {h['id']} missing from {fid} stories"
    print("build-time assertions passed: narratives, bundle and the panel figure reproduce the self-check")

    sc["system_prompt_stratum_mean_judge"] = sp
    sc["figure_ts_beneficiary_panels"] = panels
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
    sc["variant"] = SITE_LABEL
    selfcheck_json = Path(selfcheck_json)
    selfcheck_json.parent.mkdir(parents=True, exist_ok=True)
    with open(selfcheck_json, "w", encoding="utf-8") as handle:
        json.dump(sc, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    write_patches_md(counters, patcher.log, ctx, sc, Path(patches_md))

    with gzip.open(gz_path, "rb") as gz:
        assert sum(len(r["records"]) for r in json.loads(gz.read().decode("utf-8"))["runs"]) == n_records
    json.loads(nar_path.read_text(encoding="utf-8"))

    print()
    print(f"SELF-CHECK — per model, all conditions (from {ENSEMBLE_REL})")
    for m, e in sc["per_model"].items():
        confs = " ".join(f"{c}={e['conflicts'][c]}" for c in ANALYSED_CODES if e["conflicts"][c])
        print(f"  {m:18s} n={e['n_edits']:4d} judge={e['judge']} mean={e['mean_judge']:+.3f} {confs}")
    print(f"judge ties: {sc['judge_no_majority']}")
    print(f"wrote {selfcheck_json} and {patches_md}")
    return sc


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--out-dir", type=Path, default=SITE_OUT,
                        help="where to write the site (default: docs/)")
    args = parser.parse_args(argv)
    build(args.out_dir)


if __name__ == "__main__":
    main()
