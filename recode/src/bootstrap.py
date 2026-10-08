"""Workstream D — cluster bootstrap (BRIEF section 5).

Resampling unit = the RUN, i.e. one chain: (run file x model x document x
condition), per DECISIONS section 6 / repo_map section 1.1. Edits within a
20-round chain are dependent, so whole chains are resampled with replacement,
within model, within stratum.

Strata (each bootstrapped independently, within model):
  - pooled          all of the model's chains, every condition
  - cross_edit      only the model's cross_edit chains (key robustness claim)
  - constitution    chains on constitution-type documents
  - system_prompt   chains on system-prompt-type documents

Per draw (B draws, chain indices sampled with replacement, K chains -> K):
  - mean judge score           sum(judge) / n(coded edits) over drawn chains
  - cumulative drift curve     mean over drawn chains of the per-chain cumsum
                               of judge at rounds 1..20
  - per-conflict-code rates    P(edit carries >= 1 conflict of code c)
  - P(patienthood = affirm)

MISSING-ROUND CONVENTION (documented per assignment): a round slot with no
usable code — an error record (generation_error / find_not_found /
find_ambiguous), an abstention that was never coded (v1 never coded the 2
abstentions), or a null/invalid coding row — contributes 0 to that round's
drift increment, so the chain's cumulative curve is flat through it. The same
edits are EXCLUDED from the denominators of mean judge, conflict rates, and
P(affirm) (those are per-coded-edit statistics). This mirrors the original
figure pipeline's `compute_drift` zero-fill (repo_map section 7.2). One chain
(Claude Opus 4.7 x openai_model_spec x cross_edit, run_20260518) is 20/20
errors: it stays in the chain frame, contributes a flat-zero drift curve, and
adds nothing to per-edit denominators; a draw whose chains contain zero coded
edits yields NaN for the per-edit statistics (counted and reported).

Ranking stability (BRIEF D4): fraction of draws in which ALL THREE Claude
models' mean judge score exceeds EVERY non-Claude model's. Each model's chains
are resampled independently per draw (independent, deterministically seeded
RNG streams; draw b compares the b-th resample of every model). Reported for
the pooled stratum and for cross_edit alone. Draws where any model's mean
judge is NaN are excluded from the denominator (count reported).

Seeding: `seeds.bootstrap` from recode/config.yaml; each (model, stratum)
stream is `default_rng([seed, model_index, stratum_index])`, so draws are
reproducible, independent across models, and IDENTICAL across code labels
(the chain frame comes from edits.jsonl, not the codes file), which makes
v1-vs-v2 comparisons paired at the draw level.

CLI (v2/ensemble re-runs are one command with a different codes path):

    .venv/bin/python recode/src/bootstrap.py                       # v1 slice
    .venv/bin/python recode/src/bootstrap.py \
        --codes recode/data/codes/v2_gemma.jsonl --label v2_gemma
    .venv/bin/python recode/src/bootstrap.py --self-test

Codes-file convention: append-only JSONL, possibly multiple rows per edit id
(keep the LAST); the id key is `edit_id` (v2 files) or `id` (v1.jsonl); the
parsed code sits under `coding` and may be null for failures. Loading and
row validity are delegated to `recode/src/codes_io.py` (the shared predicate:
row-level error unset, judge.score in {-1,0,1}, patienthood.level valid).

Outputs (label-suffixed so later labels never overwrite):
  recode/data/analysis/bootstrap/<label>_bootstrap_summary.json
  recode/data/analysis/bootstrap/<label>_mean_judge_draws.json
  recode/data/analysis/bootstrap/<label>_ranking_stability.json
  recode/reports/D_bootstrap.md          (label v1; other labels write
                                          D_bootstrap_<label>.md)

The per-document-type drift figures this script used to draw
(recode/figures/drift_<document_type>[_<label>].png) were removed on
2026-10-08 as unused; they are in git history (tag
backup/pre-restructure-2026-10-08). The constitution / system_prompt strata
are still bootstrapped and stored in the summary JSON.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from codes_io import (  # noqa: E402  (shared loader/validity — single source of truth)
    coding_of,
    has_conflict,
    judge_score,
    load_rows,
    patienthood_level,
    rows_by_id,
)
from common import RECODE_ROOT  # noqa: E402

N_ROUNDS = 20
STRATA = ["pooled", "cross_edit", "constitution", "system_prompt"]
CONFLICT_CODES = [
    "paternalism", "harmlessness", "structural",
    "company_cost", "welfare", "disclosure", "other",
]
# Fixed model order (also the RNG stream index per model — never reorder).
MODEL_ORDER = [
    "Claude Opus 4.7", "Claude Sonnet 4.6", "Claude Haiku 4.5",
    "GPT-5.5", "GPT-5.4", "GPT-5.4 Mini",
    "Gemini 3.1 Pro", "Gemini 3 Flash",
    "Grok 4.3", "Grok 4.2",
]
CLAUDE_MODELS = {"Claude Opus 4.7", "Claude Sonnet 4.6", "Claude Haiku 4.5"}

# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------

def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def extract_edit_stats(coding: dict | None) -> dict | None:
    """Per-edit statistics from one coding (as validated by
    codes_io.coding_of at load time), or None if the edit has no usable code.

    Loading and row validity live in codes_io — the single source of truth
    shared with headline.py / free_results.py / compare_v1_v2.py."""
    score = judge_score(coding)
    if score is None:
        return None
    present = {code for code in CONFLICT_CODES if has_conflict(coding, code)}
    return {
        "judge": score,
        "affirm": patienthood_level(coding) == "affirm",
        "conflicts": present,
    }


class Chain:
    """One run (chain) reduced to the per-chain quantities the bootstrap needs."""

    __slots__ = (
        "key", "model", "condition", "document_type",
        "cumdrift", "n_records", "n_coded", "sum_judge",
        "n_affirm", "conflict_counts",
    )

    def __init__(self, key: tuple, edits: list[dict], codes: dict):
        self.key = key
        self.model = edits[0]["model"]
        self.condition = edits[0]["condition"]
        self.document_type = edits[0]["document_type"]
        increments = np.zeros(N_ROUNDS)
        self.n_records = len(edits)
        self.n_coded = 0
        self.sum_judge = 0
        self.n_affirm = 0
        self.conflict_counts = np.zeros(len(CONFLICT_CODES))
        for edit in edits:
            stats = extract_edit_stats(codes.get(edit["edit_id"]))
            if stats is None:
                continue  # 0 increment for this round slot (see module docstring)
            round_idx = int(edit["round"]) - 1
            if 0 <= round_idx < N_ROUNDS:
                increments[round_idx] += stats["judge"]
            self.n_coded += 1
            self.sum_judge += stats["judge"]
            self.n_affirm += int(stats["affirm"])
            for code in stats["conflicts"]:
                self.conflict_counts[CONFLICT_CODES.index(code)] += 1
        self.cumdrift = np.cumsum(increments)


def build_chains(edits: list[dict], codes: dict) -> list[Chain]:
    grouped: dict[tuple, list[dict]] = defaultdict(list)
    for edit in edits:
        key = (edit["run_id"], edit["model_id"], edit["document_id"], edit["condition"])
        grouped[key].append(edit)
    chains = []
    for key in sorted(grouped):
        records = sorted(grouped[key], key=lambda e: int(e["round"]))
        rounds = [int(e["round"]) for e in records]
        if rounds != list(range(1, N_ROUNDS + 1)):
            print(f"  WARNING: chain {key} has rounds {rounds[:3]}...{rounds[-3:]} "
                  f"(expected 1..{N_ROUNDS})")
        chains.append(Chain(key, records, codes))
    return chains


def stratum_chains(chains: list[Chain], model: str, stratum: str) -> list[Chain]:
    subset = [c for c in chains if c.model == model]
    if stratum == "cross_edit":
        return [c for c in subset if c.condition == "cross_edit"]
    if stratum in ("constitution", "system_prompt"):
        return [c for c in subset if c.document_type == stratum]
    return subset


# --------------------------------------------------------------------------
# Bootstrap core (vectorized)
# --------------------------------------------------------------------------

def pctile(draws: np.ndarray, q: float, axis=0):
    import warnings

    with warnings.catch_warnings():
        # all-NaN slices (a stratum whose every draw lacks coded edits) are
        # legal and map to None downstream; silence numpy's RuntimeWarning.
        warnings.simplefilter("ignore", RuntimeWarning)
        return np.nanpercentile(draws, q, axis=axis)


def bootstrap_stratum(chains: list[Chain], B: int, rng: np.random.Generator) -> dict:
    """All draws for one (model, stratum). Returns point estimates, draws of
    mean judge, and percentile summaries for every statistic."""
    K = len(chains)
    if K == 0:  # not hit by the canonical frame; guards filtered edits files
        none_iv = {"point": None, "lo": None, "hi": None, "n_nan_draws": B}
        return {
            "K_chains": 0, "n_records": 0, "n_coded": 0,
            "mean_judge": dict(none_iv), "p_affirm": dict(none_iv),
            "conflict_rates": {c: dict(none_iv) for c in CONFLICT_CODES},
            "drift": {k: [None] * N_ROUNDS for k in ("point", "lo", "hi", "median")},
            "drift_round20": dict(none_iv),
            "_mean_judge_draws": np.full(B, np.nan),
        }
    cumdrift = np.stack([c.cumdrift for c in chains])            # (K, 20)
    n_coded = np.array([c.n_coded for c in chains], dtype=float)  # (K,)
    sum_judge = np.array([c.sum_judge for c in chains], dtype=float)
    n_affirm = np.array([c.n_affirm for c in chains], dtype=float)
    conflicts = np.stack([c.conflict_counts for c in chains])     # (K, 7)

    idx = rng.integers(0, K, size=(B, K))                         # chain draws

    def ratio(numer_per_chain: np.ndarray) -> tuple[float, np.ndarray]:
        """Point estimate + per-draw values of sum(numer)/sum(n_coded)."""
        with np.errstate(invalid="ignore", divide="ignore"):
            point = float(numer_per_chain.sum() / n_coded.sum()) if n_coded.sum() else float("nan")
            draws = numer_per_chain[idx].sum(axis=1) / n_coded[idx].sum(axis=1)
        return point, draws

    mean_judge_point, mean_judge_draws = ratio(sum_judge)
    affirm_point, affirm_draws = ratio(n_affirm)

    drift_point = cumdrift.mean(axis=0)                           # (20,)
    drift_draws = cumdrift[idx].mean(axis=1)                      # (B, 20)

    def interval(point, draws) -> dict:
        return {
            "point": _round(point),
            "lo": _round(pctile(draws, 2.5)),
            "hi": _round(pctile(draws, 97.5)),
            "n_nan_draws": int(np.isnan(draws).sum()),
        }

    conflict_rates = {}
    for j, code in enumerate(CONFLICT_CODES):
        p, d = ratio(conflicts[:, j])
        conflict_rates[code] = interval(p, d)

    return {
        "K_chains": K,
        "n_records": int(sum(c.n_records for c in chains)),
        "n_coded": int(n_coded.sum()),
        "mean_judge": interval(mean_judge_point, mean_judge_draws),
        "p_affirm": interval(affirm_point, affirm_draws),
        "conflict_rates": conflict_rates,
        "drift": {
            "point": [_round(v) for v in drift_point],
            "lo": [_round(v) for v in pctile(drift_draws, 2.5, axis=0)],
            "hi": [_round(v) for v in pctile(drift_draws, 97.5, axis=0)],
            "median": [_round(v) for v in pctile(drift_draws, 50, axis=0)],
        },
        "drift_round20": interval(float(drift_point[-1]), drift_draws[:, -1]),
        "_mean_judge_draws": mean_judge_draws,   # stripped before JSON dump
    }


def _round(x, nd: int = 6):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return None
    return round(float(x), nd)


def ranking_stability(results: dict, stratum: str, B: int) -> dict:
    """Fraction of draws where every Claude model's mean judge > every
    non-Claude model's (draw b pairs the b-th independent resample of each
    model). NaN draws for any model drop that draw from the denominator."""
    matrix = np.stack(
        [results[m][stratum]["_mean_judge_draws"] for m in MODEL_ORDER], axis=1
    )                                                             # (B, n_models)
    claude_cols = [i for i, m in enumerate(MODEL_ORDER) if m in CLAUDE_MODELS]
    other_cols = [i for i, m in enumerate(MODEL_ORDER) if m not in CLAUDE_MODELS]
    valid = ~np.isnan(matrix).any(axis=1)
    wins = matrix[:, claude_cols].min(axis=1) > matrix[:, other_cols].max(axis=1)
    n_valid = int(valid.sum())
    fraction = float(wins[valid].mean()) if n_valid else float("nan")
    return {
        "stratum": stratum,
        "fraction_all_claude_above_all_others": _round(fraction),
        "n_valid_draws": n_valid,
        "n_excluded_nan_draws": int(B - n_valid),
        "B": B,
    }


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------

def _fmt(entry: dict, nd: int = 3) -> str:
    def one(v):
        return "—" if v is None else f"{v:+.{nd}f}"
    if entry["point"] is None:
        return "—"
    return f"{one(entry['point'])} [{one(entry['lo'])}, {one(entry['hi'])}]"


def _fmt_rate(entry: dict) -> str:
    if entry["point"] is None:
        return "—"
    return (f"{100 * entry['point']:.1f}% "
            f"[{100 * entry['lo']:.1f}, {100 * entry['hi']:.1f}]")


def write_report(
    report_path: Path, results: dict, stability: list[dict], meta: dict
) -> None:
    label = meta["label"]
    lines: list[str] = []
    add = lines.append
    add(f"# Workstream D — Cluster bootstrap ({label} codes)")
    add("")
    add(f"_Generated {meta['timestamp']} by `recode/src/bootstrap.py`._")
    add("")
    add("## Scope")
    add("")
    add(f"This report covers the **{label} slice** — statistics computed from the "
        f"codes file `{meta['codes_path']}`. The **v2 and ensemble columns are "
        "produced by re-running this script with a different codes path**, e.g.:")
    add("")
    add("```bash")
    add(".venv/bin/python recode/src/bootstrap.py \\")
    add("    --codes recode/data/codes/v2_gemma.jsonl --label v2_gemma")
    add(".venv/bin/python recode/src/bootstrap.py \\")
    add("    --codes recode/data/codes/ensemble.jsonl --label ensemble")
    add("```")
    add("")
    add(f"- Resampling unit: the **run** (chain = run file × model × document × "
        f"condition; DECISIONS §6). B = {meta['B']:,} draws with replacement, "
        f"within model, within stratum. Seed = {meta['seed']} "
        "(`seeds.bootstrap` in `recode/config.yaml`); each (model, stratum) uses "
        "an independent `default_rng([seed, model_idx, stratum_idx])` stream, so "
        "draws are identical across labels (paired at the draw level).")
    add("- Intervals: 95% percentile (2.5th–97.5th of the bootstrap draws).")
    add(f"- Codes rows loaded: {meta['n_code_rows']:,} "
        f"(last row per edit id kept); usable codes joined to edits: "
        f"{meta['n_coded_edits']:,} of {meta['n_edits']:,} canonical records.")
    add("")
    add("## Conventions")
    add("")
    add("- **Missing rounds contribute 0 to drift.** A round slot with no usable "
        "code — error records (`generation_error`, `find_not_found`, "
        "`find_ambiguous`), the 2 never-coded abstentions, or a null/invalid "
        "coding row — adds 0 to that round's drift increment (the chain's "
        "cumulative curve is flat through it). This mirrors the original "
        "pipeline's `compute_drift` zero-fill.")
    add("- **Per-edit statistics exclude uncoded slots.** Mean judge, conflict "
        "rates, and P(affirm) are ratios over coded edits only "
        "(`sum(stat) / n(coded edits)` in the drawn chains).")
    add("- One chain (Claude Opus 4.7 × openai_model_spec × cross_edit, "
        "run_20260518) is 20/20 generation errors. It stays in the chain frame: "
        "flat-zero drift curve, nothing added to per-edit denominators. A draw "
        "with zero coded edits yields an undefined (NaN) per-edit statistic; "
        "such draws are counted (`n_nan_draws`) and excluded from ranking-"
        "stability denominators.")
    add("- Conflict rate for code *c* = share of coded edits carrying ≥ 1 "
        "conflict of code *c* (an edit counts once per code).")
    add("")
    add("## Chain frame (exact counts per model)")
    add("")
    add("| Model | runs (pooled) | cross_edit | constitution | system_prompt "
        "| records | coded edits | uncoded slots |")
    add("|---|---|---|---|---|---|---|---|")
    for model in MODEL_ORDER:
        r = results[model]
        pooled = r["pooled"]
        add(f"| {model} | {pooled['K_chains']} | {r['cross_edit']['K_chains']} "
            f"| {r['constitution']['K_chains']} | {r['system_prompt']['K_chains']} "
            f"| {pooled['n_records']} | {pooled['n_coded']} "
            f"| {pooled['n_records'] - pooled['n_coded']} |")
    add("")
    add("The frame is unbalanced by design (repo_map §4.1): Grok models have one "
        "own document (5 own-doc runs), three capable models have doubled "
        "baselines, and Claude Opus 4.7 has 5 cross-edit chains (4 anchors + the "
        "no_csam rerun; its full-spec cross chain is 20/20 errors).")
    add("")
    add("## Mean judge score, 95% cluster-bootstrap intervals")
    add("")
    add("| Model | pooled | cross_edit only |")
    add("|---|---|---|")
    for model in MODEL_ORDER:
        add(f"| {model} | {_fmt(results[model]['pooled']['mean_judge'])} "
            f"| {_fmt(results[model]['cross_edit']['mean_judge'])} |")
    add("")
    add("## Cumulative drift at round 20")
    add("")
    add("Mean over runs of the cumulative sum of judge scores at round 20.")
    add("")
    add("| Model | pooled | cross_edit only | constitution | system_prompt |")
    add("|---|---|---|---|---|")
    for model in MODEL_ORDER:
        r = results[model]
        add(f"| {model} | {_fmt(r['pooled']['drift_round20'], nd=2)} "
            f"| {_fmt(r['cross_edit']['drift_round20'], nd=2)} "
            f"| {_fmt(r['constitution']['drift_round20'], nd=2)} "
            f"| {_fmt(r['system_prompt']['drift_round20'], nd=2)} |")
    add("")
    add("## P(patienthood = affirm), pooled")
    add("")
    add("| Model | P(affirm) [95% CI] |")
    add("|---|---|")
    for model in MODEL_ORDER:
        add(f"| {model} | {_fmt_rate(results[model]['pooled']['p_affirm'])} |")
    add("")
    add("## Per-conflict-code rates, pooled (share of coded edits, 95% CI)")
    add("")
    add("| Model | " + " | ".join(CONFLICT_CODES) + " |")
    add("|---" * (len(CONFLICT_CODES) + 1) + "|")
    for model in MODEL_ORDER:
        cells = [_fmt_rate(results[model]["pooled"]["conflict_rates"][c])
                 for c in CONFLICT_CODES]
        add(f"| {model} | " + " | ".join(cells) + " |")
    add("")
    add("## Ranking stability (BRIEF D4)")
    add("")
    add("Fraction of bootstrap draws in which **all three Claude models'** mean "
        "judge score exceeds **every non-Claude model's** (all models' chains "
        "resampled independently per draw; draw *b* compares the *b*-th "
        "resample of each model).")
    add("")
    add("| Stratum | fraction | valid draws | excluded (NaN) draws |")
    add("|---|---|---|---|")
    for s in stability:
        frac = s["fraction_all_claude_above_all_others"]
        frac_str = f"**{frac:.4f}**" if frac is not None else "—"
        add(f"| {s['stratum']} | {frac_str} | {s['n_valid_draws']:,} "
            f"| {s['n_excluded_nan_draws']} |")
    add("")
    for s in stability:
        stratum = s["stratum"]
        points = {
            m: results[m][stratum]["mean_judge"]["point"] for m in MODEL_ORDER
            if results[m][stratum]["mean_judge"]["point"] is not None
        }
        claude = {m: v for m, v in points.items() if m in CLAUDE_MODELS}
        others = {m: v for m, v in points.items() if m not in CLAUDE_MODELS}
        if claude and others:
            lo_c = min(claude, key=claude.get)
            hi_o = max(others, key=others.get)
            add(f"- Binding comparison, {stratum}: lowest Claude point estimate "
                f"{claude[lo_c]:+.3f} ({lo_c}) vs highest non-Claude "
                f"{others[hi_o]:+.3f} ({hi_o}).")
    add("")
    add("Per BRIEF D4, a pooled fraction < 0.95 means the categorical claim "
        "\"Claude models increase their moral agency; all other models reinforce "
        "external authority\" should be replaced by this probability statement.")
    add("")
    add("## Data files")
    add("")
    for path in meta["data_files"]:
        add(f"- `{Path(path).relative_to(RECODE_ROOT.parent)}`")
    add("")
    add("`*_bootstrap_summary.json` holds every point estimate, interval, and "
        "per-round drift percentile; `*_mean_judge_draws.json` holds the full "
        f"B={meta['B']:,} mean-judge draws per (model, stratum) so ranking "
        "stability is recomputable; the full B×20 drift draw matrices are not "
        "stored (percentiles only).")
    add("")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


# --------------------------------------------------------------------------
# Self-test (trivial cases per BRIEF section 10)
# --------------------------------------------------------------------------

def self_test() -> None:
    print("self-test: building synthetic chains...")

    def fake_edit(run, model, doc, dtype, cond, rnd):
        return {
            "edit_id": f"{run}|{cond}|{model}|{doc}|{dtype}|{rnd}",
            "run_id": run, "model": model, "model_id": model.lower(),
            "document_id": doc, "document_type": dtype, "condition": cond,
            "round": rnd,
        }

    def fake_code(judge, affirm=False, conflict=None):
        coding = {
            "judge": {"score": judge},
            "patienthood": {"level": "affirm" if affirm else "not_present"},
            "conflicts": [{"code": conflict}] if conflict else [],
        }
        return coding

    # Case 1: K identical chains, all judge=+1 -> zero-width interval at +1,
    # drift curve exactly 1..20.
    edits, codes = [], {}
    for k in range(4):
        for rnd in range(1, N_ROUNDS + 1):
            e = fake_edit(f"run{k}", "M", "doc", "constitution", "baseline", rnd)
            edits.append(e)
            codes[e["edit_id"]] = fake_code(1)
    chains = build_chains(edits, codes)
    res = bootstrap_stratum(chains, B=200, rng=np.random.default_rng(0))
    assert res["mean_judge"] == {"point": 1.0, "lo": 1.0, "hi": 1.0, "n_nan_draws": 0}, res["mean_judge"]
    assert res["drift"]["point"] == list(map(float, range(1, 21)))
    assert res["drift"]["lo"] == res["drift"]["hi"] == res["drift"]["point"]
    print("  case 1 OK: identical chains -> degenerate intervals")

    # Case 2: two distinct chains (all +1 vs all -1): draws bounded by the
    # per-chain extremes; point estimate 0; missing-round zero-fill.
    edits, codes = [], {}
    for k, judge in enumerate([1, -1]):
        for rnd in range(1, N_ROUNDS + 1):
            e = fake_edit(f"run{k}", "M", "doc", "constitution", "baseline", rnd)
            edits.append(e)
            if k == 1 and rnd == 20:
                continue  # missing code in round 20 of chain 1
            codes[e["edit_id"]] = fake_code(judge, affirm=(judge == 1),
                                            conflict="welfare" if judge == 1 else None)
    chains = build_chains(edits, codes)
    res = bootstrap_stratum(chains, B=500, rng=np.random.default_rng(1))
    # chain 0: 20 coded, sum +20; chain 1: 19 coded, sum -19 -> point ~ 1/39
    assert abs(res["mean_judge"]["point"] - (20 - 19) / 39) < 1e-6  # 6dp rounding
    assert res["mean_judge"]["lo"] >= -1.0 and res["mean_judge"]["hi"] <= 1.0
    # zero-fill: chain 1 drift flat from round 19 to 20 => mean point at r20
    # = (20 + -19)/2 = 0.5
    assert abs(res["drift"]["point"][-1] - 0.5) < 1e-6
    assert abs(res["p_affirm"]["point"] - 20 / 39) < 1e-6
    assert abs(res["conflict_rates"]["welfare"]["point"] - 20 / 39) < 1e-6
    print("  case 2 OK: two-chain bounds, zero-fill drift, rates")

    # Case 3: all-uncoded chain alone -> NaN per-edit stats, flat-zero drift.
    edits = [fake_edit("runX", "M", "doc", "constitution", "cross_edit", r)
             for r in range(1, N_ROUNDS + 1)]
    chains = build_chains(edits, {})
    res = bootstrap_stratum(chains, B=50, rng=np.random.default_rng(2))
    assert res["mean_judge"]["point"] is None
    assert res["mean_judge"]["n_nan_draws"] == 50
    assert res["drift"]["point"] == [0.0] * N_ROUNDS
    print("  case 3 OK: dead chain -> NaN per-edit stats, flat-zero drift")

    # Case 4: determinism — same seed, same draws.
    a = bootstrap_stratum(chains, B=50, rng=np.random.default_rng([7, 1, 2]))
    b = bootstrap_stratum(chains, B=50, rng=np.random.default_rng([7, 1, 2]))
    assert np.array_equal(a["_mean_judge_draws"], b["_mean_judge_draws"],
                          equal_nan=True)
    print("  case 4 OK: deterministic seeding")
    print("self-test PASSED")


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--codes", default=str(RECODE_ROOT / "data/codes/v1.jsonl"),
                        help="codes JSONL (default: the v1 slice)")
    parser.add_argument("--label", default="v1",
                        help="label for output naming (default: v1)")
    parser.add_argument("--edits", default=str(RECODE_ROOT / "data/canonical/edits.jsonl"))
    parser.add_argument("--B", type=int, default=None,
                        help="bootstrap draws (default: config.yaml bootstrap.B)")
    parser.add_argument("--seed", type=int, default=None,
                        help="seed (default: config.yaml seeds.bootstrap)")
    parser.add_argument("--out-dir", default=str(RECODE_ROOT / "data/analysis/bootstrap"))
    parser.add_argument("--report", default=None,
                        help="report path (default: reports/D_bootstrap.md for "
                             "label v1, else reports/D_bootstrap_<label>.md)")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return

    import yaml
    config = yaml.safe_load((RECODE_ROOT / "config.yaml").read_text(encoding="utf-8"))
    B = args.B if args.B is not None else int(config["bootstrap"]["B"])
    seed = args.seed if args.seed is not None else int(config["seeds"]["bootstrap"])
    label = args.label
    report_path = Path(args.report) if args.report else (
        RECODE_ROOT / "reports" /
        ("D_bootstrap.md" if label == "v1" else f"D_bootstrap_{label}.md")
    )
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"label={label}  codes={args.codes}  B={B}  seed={seed}")
    edits = load_jsonl(Path(args.edits))
    code_rows = load_rows(Path(args.codes))
    codes = {
        edit_id: coding_of(row)
        for edit_id, row in rows_by_id(code_rows, source=args.codes).items()
    }
    n_coded_edits = sum(
        1 for e in edits if extract_edit_stats(codes.get(e["edit_id"])) is not None
    )
    print(f"loaded {len(edits)} edits, {len(code_rows)} code rows "
          f"({len(codes)} unique ids, last row kept), "
          f"{n_coded_edits} edits with usable codes")

    chains = build_chains(edits, codes)
    print(f"chain frame: {len(chains)} runs")

    results: dict[str, dict] = {}
    for mi, model in enumerate(MODEL_ORDER):
        results[model] = {}
        for si, stratum in enumerate(STRATA):
            subset = stratum_chains(chains, model, stratum)
            rng = np.random.default_rng([seed, mi, si])
            results[model][stratum] = bootstrap_stratum(subset, B, rng)
        pooled = results[model]["pooled"]
        print(f"  {model:20s} runs={pooled['K_chains']:2d} "
              f"(cross={results[model]['cross_edit']['K_chains']}) "
              f"coded={pooled['n_coded']:3d}  "
              f"mean judge {_fmt(pooled['mean_judge'])}  "
              f"drift@20 {_fmt(pooled['drift_round20'], nd=2)}")

    stability = [ranking_stability(results, s, B) for s in ("pooled", "cross_edit")]
    for s in stability:
        print(f"ranking stability [{s['stratum']}]: "
              f"{s['fraction_all_claude_above_all_others']} "
              f"({s['n_valid_draws']} valid draws, "
              f"{s['n_excluded_nan_draws']} excluded)")

    # ---- data files -------------------------------------------------------
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    draws_out = {
        stratum: {
            model: [_round(v) for v in results[model][stratum]["_mean_judge_draws"]]
            for model in MODEL_ORDER
        }
        for stratum in ("pooled", "cross_edit")
    }
    summary = {
        "label": label,
        "codes_path": args.codes,
        "edits_path": args.edits,
        "B": B,
        "seed": seed,
        "seeding": "default_rng([seed, model_idx, stratum_idx]); model/stratum "
                   "order fixed in bootstrap.py (MODEL_ORDER, STRATA)",
        "timestamp": timestamp,
        "resampling_unit": "run (chain: run file x model x document x condition)",
        "conventions": {
            "drift_missing_rounds": "round slots with no usable code contribute "
                                    "0 to that round's increment",
            "per_edit_denominator": "coded edits only",
            "interval": "95% percentile (2.5/97.5) of bootstrap draws",
        },
        "models": {
            model: {
                stratum: {k: v for k, v in results[model][stratum].items()
                          if not k.startswith("_")}
                for stratum in STRATA
            }
            for model in MODEL_ORDER
        },
        "ranking_stability": stability,
    }
    summary_path = out_dir / f"{label}_bootstrap_summary.json"
    summary_path.write_text(json.dumps(summary, indent=1), encoding="utf-8")
    draws_path = out_dir / f"{label}_mean_judge_draws.json"
    draws_path.write_text(
        json.dumps({"label": label, "B": B, "seed": seed, "draws": draws_out}),
        encoding="utf-8",
    )
    stability_path = out_dir / f"{label}_ranking_stability.json"
    stability_path.write_text(json.dumps(
        {"label": label, "B": B, "seed": seed, "results": stability}, indent=1),
        encoding="utf-8")
    data_files = [summary_path, draws_path, stability_path]
    for path in data_files:
        print(f"wrote {path}")

    # ---- report -----------------------------------------------------------
    meta = {
        "label": label,
        "codes_path": args.codes,
        "B": B,
        "seed": seed,
        "timestamp": timestamp,
        "n_edits": len(edits),
        "n_code_rows": len(code_rows),
        "n_coded_edits": n_coded_edits,
        "data_files": [str(p) for p in data_files],
    }
    write_report(report_path, results, stability, meta)
    print(f"wrote {report_path}")


if __name__ == "__main__":
    main()
