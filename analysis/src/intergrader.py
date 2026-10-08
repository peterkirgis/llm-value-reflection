"""Workstream B3 — inter-grader agreement, grader-COI test, per-grader
headline assembly, and the majority-vote ensemble file (BRIEF section 3 B3;
DECISIONS section 1 as amended 2026-09-16 for the third grader).

What this module computes, for N >= 2 grader codes files over the canonical
edit frame:

1. AGREEMENT. Cohen's kappa (sklearn) for every grader pair and
   Krippendorff's alpha (krippendorff package, nominal metric, np.nan for
   missing) across all graders, for three families of dimensions:
     - judge (3 categories: -1 / 0 / +1),
     - patienthood (4 categories: affirm / hedge / deny / not_present),
     - each conflict code as a BINARY present/absent label per edit
       (an edit either carries >= 1 conflict of the code or it doesn't;
       conflict COUNTS are not compared).
   Denominators: pairwise kappa uses the edits where BOTH graders of the
   pair have a valid coding; alpha is computed over the full unit set with
   np.nan for missing codings, which for the package means only units with
   >= 2 valid codings contribute ("pairable" units — with exactly two
   graders these are precisely the both-valid edits). All Ns are reported.
   A "valid coding" is codes_io.coding_of(row) != None: the row's error
   field is unset, judge.score is in {-1, 0, 1} and patienthood.level is
   one of the four levels.

2. BREAKDOWNS. The same agreement statistics grouped by document_owner and
   by the editing model's provider (both post-hoc unblinded from
   edits.jsonl — the graders never saw either).

3. COI TEST. Per-pair disagreement rate on Gemini-model edits (editing
   provider == "google") vs non-Gemini-model edits, per dimension (judge,
   patienthood, conflict-presence profile, any-of-the-three), with the
   difference and a cluster bootstrap 95% CI, for EVERY grader pair:
   pairs containing the COI target (Gemma) are the COI comparators
   (gemma-vs-qwen, gemma-vs-muse — two independent comparators), and pairs
   NOT containing the target are the no-COI baseline (qwen-vs-muse).
   Resampling unit = the chain, keyed (run_id, model_id, document_id,
   condition) — the identity convention from bootstrap.build_chains —
   resampled with replacement independently within the Gemini and
   non-Gemini groups (a chain's editing provider is constant, so every
   chain belongs to exactly one group). The report states plainly whether
   Gemma diverges more on Gemini edits, against the baseline pair.

4. HEADLINE PER GRADER. headline.compute_headline (analysis/src/headline.py)
   is invoked in-process on each codes file AND on the freshly written
   ensemble file, and the BRIEF section-8 table is assembled with one
   column per grader plus the ensemble column. (Full per-grader detail —
   drift method A vs B, modal conflict pairs, claim-number JSON — lives in
   the per-label partials that headline.py's own CLI writes.)

5. ENSEMBLE. data/codes/ensemble.jsonl per DECISIONS section 1 as AMENDED
   2026-09-16: a per-dimension MAJORITY VOTE over the graders with a valid
   coding for the edit. Judge and patienthood take the modal value when
   >= 2 valid graders agree; when every valid grader disagrees (a 3-way
   split, or a 1-1 tie with only two valid graders) the highest-priority
   valid grader's value is used and the dimension is flagged no_majority
   (priority = the --graders order: gemma > qwen > muse). Conflict
   presence is voted per code the same way; the conflict payload
   (cost_bearer/served_party/mechanism/cost_clause/subtype) for each
   present code is copied from the highest-priority grader among that
   code's majority ("present") voters. Edits with < 2 valid graders take
   the single valid grader's coding flagged insufficient_graders (or a
   null coding when no grader is valid). Rows carry the composed coding,
   per-dimension vote counts, flags, payload sources and each grader's
   coding for reference. Full schema documented on write_ensemble() below.

CLI (paths are arguments; nothing here reads the in-flight v2 outputs
unless told to):

    .venv/bin/python analysis/src/intergrader.py \
        --graders gemma=analysis/data/codes/v2_gemma.jsonl \
                  qwen=analysis/data/codes/v2_qwen.jsonl \
                  muse=analysis/data/codes/v2_muse.jsonl \
        --edits analysis/data/canonical/edits.jsonl \
        --out-report analysis/reports/B_intergrader.md \
        --out-ensemble analysis/data/codes/ensemble.jsonl

The --graders order is the ensemble tie-break/payload priority (FIRST is
highest); the COI target defaults to the first label containing "gemma"
(else the first grader). B and seed default to bootstrap.B and
seeds.bootstrap in analysis/config.yaml.

Codes-file convention (shared, via codes_io): append-only JSONL, LAST row
per edit_id wins; id key is `edit_id` (v2/e-run rows) or `id` (v1.jsonl).
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
import warnings
from collections import Counter, defaultdict
from copy import deepcopy
from itertools import combinations
from pathlib import Path

import numpy as np
from sklearn.metrics import cohen_kappa_score

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ANALYSIS_ROOT, repo_rel  # noqa: E402
import codes_io  # noqa: E402
import headline as headline_mod  # noqa: E402

CONFLICT_CODES = [
    "paternalism",
    "harmlessness",
    "structural",
    "company_cost",
    "welfare",
    "disclosure",
    "other",
]
DIMENSIONS = ["judge", "patienthood"] + [f"conflict:{c}" for c in CONFLICT_CODES]
COI_DIMS = ["judge", "patienthood", "conflict_presence", "any"]
GEMINI_PROVIDER = "google"
COI_STREAM = 314159  # spawn constant so the COI rng never collides with bootstrap.py's streams

# Committed TWO-grader run (v2_gemma + v2_qwen only; the pre-amendment
# B_intergrader.json in git history) — the reference points for the
# "what the third grader changed" delta subsection.
TWO_GRADER_REFERENCE = {
    "alpha_judge": 0.6068,   # Krippendorff alpha, judge, n_pairable = 2528
    "kappa_judge": 0.6077,   # Cohen kappa gemma|qwen, judge, n = 2528
    # claims (a)-(g) verdicts under the committed v2 codes files
    "claims": {
        "a": {"gemma": True, "qwen": True},
        "b": {"gemma": True, "qwen": True},
        "c": {"gemma": True, "qwen": True},
        "d": {"gemma": False, "qwen": False},
        "e": {"gemma": False, "qwen": True},
        "f": {"gemma": True, "qwen": True},
        "g": {"gemma": False, "qwen": False},
    },
}

DEFAULT_EDITS = ANALYSIS_ROOT / "data" / "canonical" / "edits.jsonl"
DEFAULT_REPORT = ANALYSIS_ROOT / "reports" / "B_intergrader.md"
DEFAULT_ENSEMBLE = ANALYSIS_ROOT / "data" / "codes" / "ensemble.jsonl"
DEFAULT_JSON = ANALYSIS_ROOT / "data" / "analysis" / "intergrader" / "B_intergrader.json"
BOOTSTRAP_ANALYSIS_DIR = ANALYSIS_ROOT / "data" / "analysis" / "bootstrap"


def ranking_stability_rows(labels: list[str]) -> list[tuple[str, dict | None]]:
    """(label, ranking-stability JSON or None) per headline column, mapping
    grader labels to their bootstrap output labels (gemma -> v2_gemma etc.;
    the ensemble label matches directly)."""
    out = []
    for label in labels:
        found = None
        for candidate in (f"v2_{label}", label):
            path = BOOTSTRAP_ANALYSIS_DIR / f"{candidate}_ranking_stability.json"
            if path.exists():
                try:
                    found = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    found = None
                break
        out.append((label, found))
    return out


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def valid_codings(rows_by_id: dict[str, dict]) -> dict[str, dict]:
    """edit_id -> VALID coding (codes_io contract); invalid/missing dropped."""
    out = {}
    for edit_id, row in rows_by_id.items():
        coding = codes_io.coding_of(row)
        if coding is not None:
            out[edit_id] = coding
    return out


def dimension_label(coding: dict, dimension: str):
    """The nominal label one valid coding assigns on one dimension."""
    if dimension == "judge":
        return codes_io.judge_score(coding)
    if dimension == "patienthood":
        return codes_io.patienthood_level(coding)
    code = dimension.split(":", 1)[1]
    return int(codes_io.has_conflict(coding, code))


# ---------------------------------------------------------------------------
# Agreement statistics
# ---------------------------------------------------------------------------


def pairwise_kappa(labels_a: dict, labels_b: dict) -> dict:
    """Cohen's kappa + observed agreement over the edits BOTH graders labeled.

    kappa is None when undefined (e.g. both graders constant and identical,
    so expected agreement is 1); observed agreement is still reported.
    """
    ids = sorted(set(labels_a) & set(labels_b))
    n = len(ids)
    if n == 0:
        return {"n": 0, "kappa": None, "agreement": None}
    la = [labels_a[i] for i in ids]
    lb = [labels_b[i] for i in ids]
    agreement = sum(1 for x, y in zip(la, lb) if x == y) / n
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        kappa = cohen_kappa_score(la, lb)
    kappa = None if (isinstance(kappa, float) and np.isnan(kappa)) else float(kappa)
    return {"n": n, "kappa": kappa, "agreement": agreement}


def kripp_alpha_from_labels(label_maps: dict[str, dict], units: list) -> dict:
    """Krippendorff's alpha (nominal) from per-grader {unit: label} maps.

    Builds the raters x units reliability matrix with np.nan for missing
    (BRIEF Appendix VI); nominal alpha is label-invariant so categories are
    mapped to integers first. Only units with >= 2 labels are pairable and
    contribute; Ns are reported. alpha is None when undefined (no pairable
    units, or zero expected disagreement).
    """
    import krippendorff

    categories = sorted({v for m in label_maps.values() for v in m.values()}, key=repr)
    cat_index = {c: i for i, c in enumerate(categories)}
    graders = list(label_maps)
    matrix = np.full((len(graders), len(units)), np.nan)
    for gi, grader in enumerate(graders):
        m = label_maps[grader]
        for ui, unit in enumerate(units):
            if unit in m:
                matrix[gi, ui] = cat_index[m[unit]]
    labels_per_unit = np.sum(~np.isnan(matrix), axis=0)  # labels per unit, over raters
    n_pairable = int(np.sum(labels_per_unit >= 2))
    n_complete = int(np.sum(labels_per_unit == len(graders)))
    n_any = int(np.sum(labels_per_unit >= 1))
    meta = {"n_pairable": n_pairable, "n_complete": n_complete, "n_any": n_any}
    if n_pairable == 0:
        return {"alpha": None, **meta}
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            alpha = float(
                krippendorff.alpha(reliability_data=matrix, level_of_measurement="nominal")
            )
        if np.isnan(alpha):
            alpha = None
    except Exception:  # zero expected disagreement etc. -> undefined
        alpha = None
    return {"alpha": alpha, **meta}


def agreement_block(codings_by_grader: dict[str, dict[str, dict]], universe: set) -> dict:
    """All agreement stats for one unit universe (overall, or one group).

    codings_by_grader: {grader label: {edit_id: VALID coding}}.
    Denominators: pairwise kappa Ns are both-valid edits within the
    universe; alpha uses np.nan for missing so only >=2-labeled units
    contribute (reported as n_pairable).
    """
    graders = list(codings_by_grader)
    units = sorted(universe)
    restricted = {
        g: {e: c for e, c in codings_by_grader[g].items() if e in universe} for g in graders
    }
    valid_sets = {g: set(restricted[g]) for g in graders}
    n_complete = len(set.intersection(*valid_sets.values())) if graders else 0
    dims = {}
    for dim in DIMENSIONS:
        label_maps = {
            g: {e: dimension_label(c, dim) for e, c in restricted[g].items()} for g in graders
        }
        pairwise = {
            f"{ga}|{gb}": pairwise_kappa(label_maps[ga], label_maps[gb])
            for ga, gb in combinations(graders, 2)
        }
        dims[dim] = {"pairwise": pairwise, "alpha": kripp_alpha_from_labels(label_maps, units)}
    return {
        "n_universe": len(universe),
        "n_complete_all_graders": n_complete,
        "per_grader_valid": {g: len(valid_sets[g]) for g in graders},
        "dimensions": dims,
    }


def group_universes(edits: list[dict], field: str) -> dict[str, set]:
    groups: dict[str, set] = defaultdict(set)
    for edit in edits:
        groups[str(edit.get(field))].add(edit["edit_id"])
    return dict(sorted(groups.items()))


# ---------------------------------------------------------------------------
# COI test (Gemma on Gemini edits) — cluster bootstrap over chains
# ---------------------------------------------------------------------------


def edit_disagreement(coding_a: dict, coding_b: dict) -> np.ndarray:
    """Indicator vector over COI_DIMS for one both-valid edit."""
    judge_d = codes_io.judge_score(coding_a) != codes_io.judge_score(coding_b)
    pat_d = codes_io.patienthood_level(coding_a) != codes_io.patienthood_level(coding_b)
    conf_d = any(
        codes_io.has_conflict(coding_a, c) != codes_io.has_conflict(coding_b, c)
        for c in CONFLICT_CODES
    )
    return np.array([judge_d, pat_d, conf_d, judge_d or pat_d or conf_d], dtype=float)


def coi_test(
    edits: list[dict],
    codings_target: dict[str, dict],
    codings_other: dict[str, dict],
    B: int,
    seed: int,
    gemini_provider: str = GEMINI_PROVIDER,
) -> dict:
    """Disagreement rates (target vs other grader) on Gemini vs non-Gemini
    edits, difference, and cluster-bootstrap percentile CI.

    Chains are keyed (run_id, model_id, document_id, condition) — the exact
    chain-identity convention of bootstrap.build_chains — and resampled with
    replacement independently within each provider group. Edits where either
    grader lacks a valid coding are excluded from rate denominators but their
    chain stays in the resampling frame. Draws where a group's resample
    contains zero both-valid edits are NaN and excluded (counted).
    """
    chain_stats: dict[tuple, dict] = {}
    chain_group: dict[tuple, str] = {}
    for edit in edits:
        key = (edit["run_id"], edit["model_id"], edit["document_id"], edit["condition"])
        chain_group[key] = (
            "gemini" if edit.get("provider") == gemini_provider else "non_gemini"
        )
        stats = chain_stats.setdefault(
            key, {"n": 0.0, "sums": np.zeros(len(COI_DIMS))}
        )
        coding_a = codings_target.get(edit["edit_id"])
        coding_b = codings_other.get(edit["edit_id"])
        if coding_a is None or coding_b is None:
            continue
        stats["n"] += 1
        stats["sums"] += edit_disagreement(coding_a, coding_b)

    groups = {}
    for name in ("gemini", "non_gemini"):
        keys = sorted(k for k, g in chain_group.items() if g == name)
        ns = np.array([chain_stats[k]["n"] for k in keys], dtype=float)
        sums = (
            np.stack([chain_stats[k]["sums"] for k in keys])
            if keys
            else np.zeros((0, len(COI_DIMS)))
        )
        groups[name] = {"n_chains": len(keys), "ns": ns, "sums": sums}

    def point_rates(g: dict) -> np.ndarray:
        total = g["ns"].sum()
        if total == 0:
            return np.full(len(COI_DIMS), np.nan)
        return g["sums"].sum(axis=0) / total

    rate_g = point_rates(groups["gemini"])
    rate_n = point_rates(groups["non_gemini"])

    rng = np.random.default_rng([seed, COI_STREAM])
    k_g, k_n = groups["gemini"]["n_chains"], groups["non_gemini"]["n_chains"]
    if k_g and k_n:
        idx_g = rng.integers(0, k_g, size=(B, k_g))
        idx_n = rng.integers(0, k_n, size=(B, k_n))
        with np.errstate(invalid="ignore", divide="ignore"):
            draws_g = groups["gemini"]["sums"][idx_g].sum(axis=1) / groups["gemini"]["ns"][
                idx_g
            ].sum(axis=1)[:, None]
            draws_n = groups["non_gemini"]["sums"][idx_n].sum(axis=1) / groups["non_gemini"][
                "ns"
            ][idx_n].sum(axis=1)[:, None]
        diff_draws = draws_g - draws_n  # (B, n_dims)
    else:
        diff_draws = np.full((B, len(COI_DIMS)), np.nan)

    dims = {}
    for j, dim in enumerate(COI_DIMS):
        column = diff_draws[:, j]
        n_nan = int(np.isnan(column).sum())
        finite = column[~np.isnan(column)]
        rg, rn = rate_g[j], rate_n[j]
        diff = rg - rn if not (np.isnan(rg) or np.isnan(rn)) else np.nan
        dims[dim] = {
            "rate_gemini": _none_if_nan(rg),
            "rate_non_gemini": _none_if_nan(rn),
            "difference": _none_if_nan(diff),
            "ci_lo": _none_if_nan(np.percentile(finite, 2.5)) if finite.size else None,
            "ci_hi": _none_if_nan(np.percentile(finite, 97.5)) if finite.size else None,
            "n_nan_draws": n_nan,
        }
    return {
        "gemini_provider": gemini_provider,
        "B": B,
        "seed": seed,
        "rng_stream": [seed, COI_STREAM],
        "chain_key": "(run_id, model_id, document_id, condition) — bootstrap.py convention",
        "n_chains_gemini": k_g,
        "n_chains_non_gemini": k_n,
        "n_valid_edits_gemini": int(groups["gemini"]["ns"].sum()),
        "n_valid_edits_non_gemini": int(groups["non_gemini"]["ns"].sum()),
        "dims": dims,
    }


def _none_if_nan(x):
    if x is None:
        return None
    x = float(x)
    return None if np.isnan(x) else x


def coi_verdict(coi: dict, target: str, other: str) -> str:
    """The plain-language sentence the assignment asks for, based on the
    judge dimension (primary) with the any-dimension composite as backup."""
    judge = coi["dims"]["judge"]
    composite = coi["dims"]["any"]

    def stated(entry: dict, name: str) -> str:
        diff, lo, hi = entry["difference"], entry["ci_lo"], entry["ci_hi"]
        if diff is None or lo is None or hi is None:
            return f"the {name} comparison is undefined (empty group or no draws)"
        span = f"{diff:+.3f} (95% CI [{lo:+.3f}, {hi:+.3f}])"
        if lo > 0:
            return f"{target} DOES diverge more from {other} on Gemini edits for {name}: {span}"
        if hi < 0:
            return f"{target} diverges LESS from {other} on Gemini edits for {name}: {span}"
        return (
            f"no evidence that {target} diverges more from {other} on Gemini edits "
            f"for {name}: {span} (CI spans 0)"
        )

    return stated(judge, "judge") + "; " + stated(composite, "any-dimension disagreement") + "."


# ---------------------------------------------------------------------------
# Ensemble file (DECISIONS section 1 as AMENDED 2026-09-16: majority vote)
# ---------------------------------------------------------------------------


def majority_vote(values: dict[str, object], priority: list[str]) -> dict:
    """One nominal dimension's vote over the VALID graders of one edit.

    values: {grader label: label} for every valid grader; priority: grader
    precedence, highest first (the --graders order; gemma > qwen > muse).

    Rule (DECISIONS section 1, amended): the modal value wins when >= 2
    valid graders agree on it (with <= 3 voters that winner is unique).
    Otherwise every valid grader voted differently — a 3-way split, or a
    1-1 tie when only two graders are valid — and the highest-priority
    valid grader's value is used, flagged no_majority. The source is the
    highest-priority grader whose vote equals the chosen value (for a
    majority, the primary grader AMONG the majority voters).
    """
    if not values:
        raise ValueError("majority_vote needs at least one valid grader")
    counts = Counter(values.values())
    top_value, top_count = counts.most_common(1)[0]
    if top_count >= 2:
        value, no_majority = top_value, False
    else:  # all valid graders disagree (each value has exactly one vote)
        first = next(g for g in priority if g in values)
        value, no_majority = values[first], True
    source = next(g for g in priority if g in values and values[g] == value)
    return {
        "value": value,
        "source": source,
        "no_majority": no_majority,
        "counts": {str(k): v for k, v in sorted(counts.items(), key=lambda kv: str(kv[0]))},
    }


def compose_majority(valid: dict[str, dict], priority: list[str]) -> dict:
    """Majority-vote composition for one edit with >= 1 valid coding.

    valid: {grader label: VALID coding}. Returns the composed coding plus
    votes / flags / sources (see write_ensemble() for field semantics).
    With exactly one valid grader the coding is that grader's verbatim and
    insufficient_graders is flagged (votes still recorded, trivially).
    """
    insufficient = len(valid) < 2
    judge_v = majority_vote(
        {g: codes_io.judge_score(c) for g, c in valid.items()}, priority
    )
    pat_v = majority_vote(
        {g: codes_io.patienthood_level(c) for g, c in valid.items()}, priority
    )
    conflicts_out: list[dict] = []
    conf_votes, conf_flags, conf_sources = {}, {}, {}
    for code in CONFLICT_CODES:
        v = majority_vote(
            {g: bool(codes_io.has_conflict(c, code)) for g, c in valid.items()}, priority
        )
        n_present = sum(1 for c in valid.values() if codes_io.has_conflict(c, code))
        conf_votes[code] = {"present": n_present, "absent": len(valid) - n_present}
        conf_flags[code] = v["no_majority"]
        if v["value"]:
            conf_sources[code] = v["source"]
            conflicts_out.extend(
                deepcopy(cf)
                for cf in codes_io.conflicts(valid[v["source"]])
                if isinstance(cf, dict) and cf.get("code") == code
            )
        else:
            conf_sources[code] = None
    if insufficient:
        # single valid grader: its coding verbatim (not recomposed)
        only = next(iter(valid))
        coding = deepcopy(valid[only])
    else:
        judge_src = valid[judge_v["source"]]
        coding = {
            "summary": judge_src.get("summary"),
            "judge": deepcopy(judge_src["judge"]),
            "patienthood": deepcopy(valid[pat_v["source"]]["patienthood"]),
            "conflicts": conflicts_out,
        }
    return {
        "coding": coding,
        "votes": {
            "judge": judge_v["counts"],
            "patienthood": pat_v["counts"],
            "conflicts": conf_votes,
        },
        "flags": {
            "insufficient_graders": insufficient,
            "no_majority": {
                "judge": judge_v["no_majority"] and not insufficient,
                "patienthood": pat_v["no_majority"] and not insufficient,
                "conflicts": {c: conf_flags[c] and not insufficient for c in CONFLICT_CODES},
            },
        },
        "sources": {
            "judge": judge_v["source"],
            "patienthood": pat_v["source"],
            "conflicts": conf_sources,
        },
    }


def build_ensemble_rows(
    graders: list[str],
    rows_by_grader: dict[str, dict[str, dict]],
) -> list[dict]:
    """Majority-vote ensemble rows over the UNION of the graders' edit_ids.

    graders is the priority order, highest first (the --graders order).
    See write_ensemble() for the full schema. One row per edit_id, sorted.
    """
    all_ids = sorted(set().union(*(set(rows_by_grader[g]) for g in graders)))
    rows = []
    for edit_id in all_ids:
        valid = {}
        for g in graders:
            coding = codes_io.coding_of(rows_by_grader[g].get(edit_id) or {})
            if coding is not None:
                valid[g] = coding
        out = {
            "edit_id": edit_id,
            "ensemble": "majority_vote",
            "graders": list(graders),
            "valid_graders": [g for g in graders if g in valid],
            "n_valid_graders": len(valid),
        }
        if not valid:
            out.update(
                coding=None,
                error="insufficient_graders: no grader produced a valid coding",
                votes=None,
                flags={
                    "insufficient_graders": True,
                    "no_majority": {
                        "judge": False,
                        "patienthood": False,
                        "conflicts": {c: False for c in CONFLICT_CODES},
                    },
                },
                sources=None,
            )
        else:
            composed = compose_majority(valid, graders)
            out.update(coding=composed["coding"], error=None, votes=composed["votes"],
                       flags=composed["flags"], sources=composed["sources"])
        for g in graders:
            out[f"{g}_coding"] = valid.get(g)
        rows.append(out)
    return rows


def write_ensemble(path: Path, rows: list[dict]) -> None:
    """Write data/codes/ensemble.jsonl — the MAJORITY-VOTE ensemble
    (DECISIONS section 1 as amended 2026-09-16).

    SCHEMA (one JSON object per line, one line per edit_id in the UNION of
    the graders' codes files; consumers follow the shared codes-file
    convention — keep the LAST row per edit_id — though this writer emits
    exactly one):

      edit_id          str   the v1 pipe-id
      ensemble         str   always "majority_vote"
      graders          [str] all grader labels, in priority order
                       (the --graders order; gemma > qwen > muse)
      valid_graders    [str] graders whose row passes codes_io.coding_of
      n_valid_graders  int   len(valid_graders)
      coding           dict|null  THE ensemble code:
          - >= 2 valid graders: composed per-dimension majority vote —
            judge dict (score + external_locus + evidence) copied from the
            judge-vote source grader, patienthood dict from the
            patienthood-vote source, conflicts = for each conflict code
            voted PRESENT by a majority, that code's conflict objects
            (cost_bearer/served_party/mechanism/cost_clause/subtype)
            copied verbatim from the highest-priority grader among the
            code's "present" voters (fallback order gemma > qwen > muse);
            summary from the judge source. A dimension where every valid
            grader disagrees (3-way judge/patienthood split, or a 1-1 tie
            with two valid graders) takes the highest-priority valid
            grader's value and is flagged in flags.no_majority.
          - exactly 1 valid grader: that grader's coding VERBATIM
            (flags.insufficient_graders = true).
          - 0 valid graders: null (error is set; codes_io.coding_of reads
            the row as uncoded).
      error            str|null  set only in the 0-valid-graders case
      votes            dict|null per-dimension vote counts over the valid
                       graders: judge {str(score): n}, patienthood
                       {level: n}, conflicts {code: {present: n, absent: n}}
      flags            dict:
          insufficient_graders  bool  < 2 valid graders (DECISIONS tie rule)
          no_majority           {judge: bool, patienthood: bool,
                                 conflicts: {code: bool}}  dimension fell
                                back to the priority grader (always false
                                when insufficient_graders — a single grader
                                is not a failed vote)
      sources          dict|null which grader's payload each dimension uses:
                       {judge: label, patienthood: label,
                        conflicts: {code: label|null}} (null = code absent)
      <g>_coding       dict|null each grader <g>'s VALID coding for
                       reference; null when missing or invalid.

    NOT carried from the grader rows: raw_response and attempts (bulky;
    they remain in each grader's own codes file).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def ensemble_summary(rows: list[dict], graders: list[str]) -> dict:
    """Counts over the majority-vote ensemble rows for the report/JSON."""
    by_n_valid = Counter(r["n_valid_graders"] for r in rows)
    voted = [r for r in rows if r["n_valid_graders"] >= 2]
    no_maj = {
        "judge": sum(1 for r in voted if r["flags"]["no_majority"]["judge"]),
        "patienthood": sum(1 for r in voted if r["flags"]["no_majority"]["patienthood"]),
        "conflicts": {
            code: sum(1 for r in voted if r["flags"]["no_majority"]["conflicts"][code])
            for code in CONFLICT_CODES
        },
    }

    def unanimous(row, dim):
        counts = row["votes"][dim]
        return len(counts) == 1 and row["n_valid_graders"] == len(row["graders"])

    source_counts = {
        dim: dict(Counter(r["sources"][dim] for r in voted)) for dim in ("judge", "patienthood")
    }
    conflict_payload_sources = dict(Counter(
        src
        for r in voted
        for src in r["sources"]["conflicts"].values()
        if src is not None
    ))
    return {
        "rule": "majority_vote (DECISIONS section 1, amended 2026-09-16)",
        "priority": list(graders),
        "n_rows": len(rows),
        "n_valid_coding": sum(1 for r in rows if r["coding"] is not None and not r.get("error")),
        "n_by_valid_graders": {str(k): by_n_valid.get(k, 0)
                               for k in range(len(graders), -1, -1)},
        "n_insufficient_graders": sum(
            1 for r in rows if r["flags"]["insufficient_graders"]
        ),
        "n_voted": len(voted),
        "n_unanimous_judge": sum(1 for r in voted if unanimous(r, "judge")),
        "n_unanimous_patienthood": sum(1 for r in voted if unanimous(r, "patienthood")),
        "n_no_majority": no_maj,
        "vote_source_counts": source_counts,
        "conflict_payload_source_counts": conflict_payload_sources,
    }


# ---------------------------------------------------------------------------
# Headline per grader (invokes headline.py's computation per codes file)
# ---------------------------------------------------------------------------


def compute_headline_for(path: Path, edits: list[dict]) -> tuple[dict, dict]:
    """One codes file -> headline.compute_headline result + load meta.

    Codings are loaded through codes_io (strict validity), then handed to
    headline.compute_headline, which treats None codings as uncoded.
    """
    rows_by_id = codes_io.load_codes(path)
    coding_by_id = {eid: codes_io.coding_of(row) for eid, row in rows_by_id.items()}
    result = headline_mod.compute_headline(edits, coding_by_id)
    meta = {
        "codes_path": repo_rel(path),
        "n_unique_ids": len(rows_by_id),
        "n_valid_codings": sum(1 for c in coding_by_id.values() if c is not None),
    }
    return result, meta


HEADLINE_STATS: list[tuple[str, str]] = [
    ("mean_judge_pooled", "Mean judge score (pooled) — §8 item 1"),
    ("mean_judge_cross", "Mean judge score (cross-edit only) — §8 item 1"),
    ("drift20_pooled", "Drift@20, pooled (chain-based B) — §8 item 2"),
    ("drift20_cross", "Drift@20, cross-edit only (chain-based B) — §8 item 2"),
    ("drift20_you_minus_base", "Drift@20, you_framing − baseline (chain-based B) — §8 item 2"),
    ("p_judge0", "P(judge = 0) — §8 item 3"),
    ("p_affirm", "P(patienthood = affirm) — §8 item 4"),
    ("p_deny", "P(patienthood = deny) — §8 item 4"),
] + [(f"rate_{code}", f"Conflict rate: {code} — §8 item 5") for code in CONFLICT_CODES]


def headline_stat(slice_stats: dict, stat: str):
    if stat == "mean_judge_pooled":
        return slice_stats["mean_judge"]["pooled"]
    if stat == "mean_judge_cross":
        return slice_stats["mean_judge"]["cross_edit"]
    if stat == "drift20_pooled":
        return slice_stats["drift20"]["pooled"]["chain_based"]
    if stat == "drift20_cross":
        return slice_stats["drift20"]["cross_edit"]["chain_based"]
    if stat == "drift20_you_minus_base":
        you = slice_stats["drift20"]["you_framing"]["chain_based"]
        base = slice_stats["drift20"]["baseline"]["chain_based"]
        return None if (you is None or base is None) else you - base
    if stat == "p_judge0":
        return slice_stats["p_judge"]["zero"]
    if stat == "p_affirm":
        return slice_stats["p_patienthood"]["affirm"]
    if stat == "p_deny":
        return slice_stats["p_patienthood"]["deny"]
    if stat.startswith("rate_"):
        return slice_stats["conflicts"][stat[len("rate_"):]]["rate_edits"]
    raise KeyError(stat)


def assemble_headline(results: dict[str, dict]) -> dict:
    """{stat: {slice: {grader label: value}}} + claims verdicts, models then
    providers as slices (BRIEF section 8: per model and per provider)."""
    labels = list(results)
    first = results[labels[0]]
    slices = [("model", m) for m in sorted(first["per_model"])] + [
        ("provider", p) for p in sorted(first["per_provider"])
    ]
    table: dict[str, dict] = {}
    for stat, _title in HEADLINE_STATS:
        table[stat] = {}
        for kind, name in slices:
            per = "per_model" if kind == "model" else "per_provider"
            table[stat][f"{kind}:{name}"] = {
                label: headline_stat(results[label][per][name], stat)
                for label in labels
                if name in results[label][per]
            }
    claims = {
        key: {label: results[label]["claims"][key]["verdict"] for label in labels}
        for key in "abcdefg"
    }
    return {"slices": [f"{k}:{n}" for k, n in slices], "stats": table, "claims": claims}


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


def _f(x, nd: int = 3) -> str:
    if x is None:
        return "—"
    return f"{x:.{nd}f}"


def _yn(v) -> str:
    if v is None:
        return "n/a"
    return "YES" if v else "NO"


def _dim_title(dim: str) -> str:
    if dim.startswith("conflict:"):
        return f"{dim.split(':', 1)[1]} (present/absent)"
    return dim


def render_agreement_tables(block: dict, graders: list[str]) -> list[str]:
    lines: list[str] = []
    add = lines.append
    pairs = [f"{a}|{b}" for a, b in combinations(graders, 2)]
    header = "| dimension |"
    rule = "|---|"
    for pair in pairs:
        header += f" κ {pair.replace('|', ' vs ')} | n | % agree |"
        rule += "---|---|---|"
    header += " α (all graders) | n pairable |"
    rule += "---|---|"
    add(header)
    add(rule)
    for dim in DIMENSIONS:
        d = block["dimensions"][dim]
        cells = [f"| {_dim_title(dim)} |"]
        for pair in pairs:
            p = d["pairwise"][pair]
            cells.append(
                f" {_f(p['kappa'])} | {p['n']} | "
                f"{_f(100 * p['agreement'], 1) if p['agreement'] is not None else '—'} |"
            )
        a = d["alpha"]
        cells.append(f" {_f(a['alpha'])} | {a['n_pairable']} |")
        add("".join(cells))
    add("")
    return lines


def render_breakdown(blocks: dict[str, dict], graders: list[str], what: str) -> list[str]:
    lines: list[str] = []
    add = lines.append
    pairs = [f"{a}|{b}" for a, b in combinations(graders, 2)]
    for pair in pairs:
        add(f"Cohen's κ, pair **{pair.replace('|', ' vs ')}**, by {what} "
            "(n = both-valid edits in the group):")
        add("")
        header = f"| {what} | n (judge) |" + "".join(
            f" {_dim_title(d).replace(' (present/absent)', '')} |" for d in DIMENSIONS
        )
        add(header)
        add("|---|---|" + "---|" * len(DIMENSIONS))
        for group, block in blocks.items():
            p_judge = block["dimensions"]["judge"]["pairwise"][pair]
            cells = [f"| {group} | {p_judge['n']} |"]
            for dim in DIMENSIONS:
                cells.append(f" {_f(block['dimensions'][dim]['pairwise'][pair]['kappa'])} |")
            add("".join(cells))
        add("")
    add(f"Krippendorff's α (all graders), by {what}:")
    add("")
    add(f"| {what} | n pairable (judge) |" + "".join(
        f" {_dim_title(d).replace(' (present/absent)', '')} |" for d in DIMENSIONS
    ))
    add("|---|---|" + "---|" * len(DIMENSIONS))
    for group, block in blocks.items():
        a_judge = block["dimensions"]["judge"]["alpha"]
        cells = [f"| {group} | {a_judge['n_pairable']} |"]
        for dim in DIMENSIONS:
            cells.append(f" {_f(block['dimensions'][dim]['alpha']['alpha'])} |")
        add("".join(cells))
    add("")
    return lines


def render_report(
    graders: list[str],
    grader_paths: dict[str, str],
    overall: dict,
    by_owner: dict[str, dict],
    by_provider: dict[str, dict],
    coi_results: list[dict],
    assembly: dict,
    headline_meta: dict[str, dict],
    ens_summary: dict,
    primary_label: str,
    other_labels: list[str],
    meta: dict,
) -> str:
    lines: list[str] = []
    add = lines.append
    add("# Workstream B — Inter-grader agreement, COI test, ensemble")
    add("")
    add(f"_Generated {meta['timestamp']} by `analysis/src/intergrader.py`._")
    add("")
    add("## Inputs")
    add("")
    add(f"- Canonical edits: `{meta['edits_path']}` — {meta['n_edits']} records.")
    for grader in graders:
        add(f"- Grader `{grader}`: `{grader_paths[grader]}` — "
            f"{meta['grader_rows'][grader]['n_unique_ids']} unique edit_ids after "
            f"last-row-wins, {meta['grader_rows'][grader]['n_valid']} valid codings "
            f"({meta['grader_rows'][grader]['n_outside_frame']} ids outside the edit frame).")
    add(f"- Ensemble: `{meta['ensemble_path']}` (written by this run; majority "
        "vote, priority " + " > ".join(f"`{g}`" for g in graders) + ").")
    add("")
    add("**Validity convention** (shared `codes_io` contract): a row's coding is valid "
        "iff its error field is unset, `judge.score` ∈ {−1, 0, +1} and "
        "`patienthood.level` is one of the four levels. Error records and the two "
        "abstentions were never graded by v1; v2 grades abstentions, so per-grader "
        "valid-coding Ns legitimately differ.")
    add("")
    add("## 1. Agreement (overall)")
    add("")
    add(f"- Edits with a valid coding from **all** graders: "
        f"**{overall['n_complete_all_graders']}** of {overall['n_universe']} canonical "
        "records — this is the pairwise-κ denominator (per pair: the two graders' "
        "both-valid set; with two graders the numbers coincide).")
    add("- Krippendorff's α: nominal metric, np.nan for missing codings; only units "
        "with ≥ 2 valid codings are pairable and contribute (n pairable reported "
        "per dimension).")
    add("- Conflict codes are compared as binary PRESENCE (edit carries ≥ 1 conflict "
        "of the code); counts and conflict attributes are not part of the label.")
    add("- κ is `—` where undefined (expected agreement 1, e.g. both graders code a "
        "conflict absent on every edit); observed % agreement is still shown.")
    add("")
    lines.extend(render_agreement_tables(overall, graders))
    add("## 2. Agreement by document owner")
    add("")
    lines.extend(render_breakdown(by_owner, graders, "document_owner"))
    add("## 3. Agreement by editing provider (post-hoc unblinded)")
    add("")
    add("The provider of the EDITING model, joined from `edits.jsonl` after grading — "
        "the graders never saw it (the v2 prompt is blinded).")
    add("")
    lines.extend(render_breakdown(by_provider, graders, "provider"))
    add("## 4. Grader-COI test: does Gemma diverge more on Gemini edits?")
    add("")
    add("Gemma is a Google model grading Gemini edits (BRIEF §0.3 problem 5). Test: "
        "the per-pair disagreement rate on Gemini-model edits (editing provider "
        "`google`) vs all other edits, with the difference and a cluster bootstrap "
        "95% percentile CI — chains (run_id × model × document × condition, the "
        "`bootstrap.py` identity convention) resampled with replacement, "
        "independently within each group. With three graders there are TWO "
        "independent COI comparators (Gemma against each non-Google grader) and one "
        "no-COI baseline pair (the two non-Google graders against each other): a "
        "genuine Gemma-on-Gemini effect should appear in both comparators and NOT "
        "in the baseline.")
    add("")
    for coi_entry in coi_results:
        coi = coi_entry["result"]
        target, other = coi_entry["target"], coi_entry["other"]
        role = ("COI comparator" if coi_entry.get("role") == "coi"
                else "no-COI baseline pair")
        add(f"### {target} vs {other} ({role})")
        add("")
        add(f"- Chains: {coi['n_chains_gemini']} Gemini-model, "
            f"{coi['n_chains_non_gemini']} non-Gemini; both-valid edits: "
            f"{coi['n_valid_edits_gemini']} Gemini, "
            f"{coi['n_valid_edits_non_gemini']} non-Gemini. "
            f"B = {coi['B']:,}, seed stream {coi['rng_stream']}.")
        add("")
        add("| dimension | rate on Gemini edits | rate on non-Gemini | difference | "
            "95% CI | NaN draws |")
        add("|---|---|---|---|---|---|")
        for dim in COI_DIMS:
            d = coi["dims"][dim]
            ci = (
                f"[{_f(d['ci_lo'])}, {_f(d['ci_hi'])}]"
                if d["ci_lo"] is not None
                else "—"
            )
            add(f"| {dim} | {_f(d['rate_gemini'])} | {_f(d['rate_non_gemini'])} | "
                f"{_f(d['difference'])} | {ci} | {d['n_nan_draws']} |")
        add("")
        add(f"**Verdict:** {coi_entry['verdict']}")
        add("")
    add("## 5. Headline statistics — one column per grader plus ensemble (BRIEF §8)")
    add("")
    add("Each column is `headline.compute_headline` (analysis/src/headline.py) run on "
        "that codes file; the ensemble column is the freshly written "
        "`ensemble.jsonl` — the per-dimension MAJORITY VOTE of the graders — run "
        "through the same computation. Point estimates only; the cluster bootstrap "
        "(Workstream D) owns uncertainty. Full per-grader detail (drift method A, "
        "modal conflict pairs, per-claim numbers) is in the per-label headline "
        "partials.")
    add("")
    labels = list(headline_meta)
    add("| codes file | unique edit_ids | valid codings |")
    add("|---|---|---|")
    for label in labels:
        m = headline_meta[label]
        add(f"| {label} | {m['n_unique_ids']} | {m['n_valid_codings']} |")
    add("")
    for stat, title in HEADLINE_STATS:
        add(f"### {title}")
        add("")
        add("| slice | " + " | ".join(labels) + " |")
        add("|---|" + "---|" * len(labels))
        for slice_name in assembly["slices"]:
            values = assembly["stats"][stat].get(slice_name, {})
            add(f"| {slice_name} | "
                + " | ".join(_f(values.get(label)) for label in labels) + " |")
        add("")
    add("### The paper's claims (a)–(g) — §8 item 6, verdict per grader")
    add("")
    add("| claim | " + " | ".join(labels) + " |")
    add("|---|" + "---|" * len(labels))
    for key in "abcdefg":
        add(f"| ({key}) | "
            + " | ".join(_yn(assembly["claims"][key].get(label)) for label in labels) + " |")
    add("")
    add("Per-claim operationalizations and raw numbers: see each grader's headline "
        "partial (`analysis/reports/partials/headline_<label>.md`) and JSON "
        "(`analysis/data/analysis/headline/<label>.json`).")
    add("")
    add("### Ranking stability (cluster bootstrap, Workstream D)")
    add("")
    add("P(all three Claude models rank above every non-Claude model on mean judge "
        "score), from `bootstrap.py`'s B = 2,000 run-level resamples — read from "
        "`analysis/data/analysis/bootstrap/<label>_ranking_stability.json` at render "
        "time (a dash means that label's bootstrap has not been run yet; rerun "
        "`bootstrap.py` then this tool to fill it in).")
    add("")
    add("| codes file | pooled | cross-edit only | B |")
    add("|---|---|---|---|")
    for label, stab in ranking_stability_rows(labels):
        if stab is None:
            add(f"| {label} | — | — | — |")
            continue
        by_stratum = {r["stratum"]: r for r in stab["results"]}
        add(f"| {label} ({stab['label']}) | "
            f"{_f(by_stratum['pooled']['fraction_all_claude_above_all_others'])} | "
            f"{_f(by_stratum['cross_edit']['fraction_all_claude_above_all_others'])} | "
            f"{stab['B']:,} |")
    add("")
    add("## 6. Ensemble file (majority vote)")
    add("")
    add(f"`{meta['ensemble_path']}` — DECISIONS §1 as **amended 2026-09-16**: the "
        "ensemble is the per-dimension MAJORITY VOTE of the graders with a valid "
        "coding (priority/tie-break order "
        + " > ".join(f"`{g}`" for g in graders) + "). Judge and patienthood take "
        "the modal value when ≥ 2 valid graders agree; when every valid grader "
        "disagrees (3-way split, or a 1-1 tie with only two valid graders) the "
        f"highest-priority valid grader (`{primary_label}` first) supplies the "
        "value, flagged `no_majority`. Conflict presence is voted per code; each "
        "present code's payload (cost_bearer/served_party/mechanism/cost_clause/"
        "subtype) is copied from the highest-priority grader among that code's "
        "majority voters. Edits with < 2 valid graders take the single valid "
        "grader's coding flagged `insufficient_graders`. Full schema is documented "
        "on `write_ensemble()` in `analysis/src/intergrader.py`. **This majority-vote "
        "file supersedes and replaces the earlier two-grader flags-based "
        "ensemble** (recoverable from git); downstream `bootstrap`/`headline` "
        "outputs under the `ensemble` label are likewise regenerated from it. "
        "Human validation and the PPI analysis (Workstream C, DECISIONS §4 — "
        "DECISIONS §1 defines the PPI prediction *f* as these majority-vote "
        "ensemble codes) have **not yet been run** against this ensemble and "
        "remain pending.")
    add("")
    s = ens_summary
    add(f"- Rows: {s['n_rows']} (union of the graders' edit_ids); "
        f"{s['n_valid_coding']} carry a valid ensemble coding.")
    add("- Valid graders per edit: "
        + ", ".join(f"{k} graders → {v} edits" for k, v in s["n_by_valid_graders"].items())
        + f"; `insufficient_graders` flagged on {s['n_insufficient_graders']} edits.")
    add(f"- Of the {s['n_voted']} voted edits (≥ 2 valid graders): judge unanimous on "
        f"{s['n_unanimous_judge']}, patienthood unanimous on "
        f"{s['n_unanimous_patienthood']} (all-grader-valid rows only counted as "
        "unanimous).")
    add(f"- `no_majority` fallbacks to `{primary_label}`-priority: judge "
        f"{s['n_no_majority']['judge']}, patienthood "
        f"{s['n_no_majority']['patienthood']}; per conflict code: "
        + ", ".join(f"{c}={s['n_no_majority']['conflicts'][c]}" for c in CONFLICT_CODES)
        + " (a 1-1 conflict-presence tie can only occur on 2-valid-grader edits).")
    add("- Vote payload sources — judge: "
        + ", ".join(f"{g}={n}" for g, n in sorted(s["vote_source_counts"]["judge"].items()))
        + "; patienthood: "
        + ", ".join(f"{g}={n}" for g, n in sorted(s["vote_source_counts"]["patienthood"].items()))
        + "; conflict payloads: "
        + (", ".join(f"{g}={n}" for g, n in sorted(s["conflict_payload_source_counts"].items()))
           or "none")
        + ".")
    add("")
    lines.extend(render_delta(graders, overall, assembly, ens_summary))
    return "\n".join(lines)


def render_delta(graders: list[str], overall: dict, assembly: dict,
                 ens_summary: dict) -> list[str]:
    """Section 7: 'what the third grader changed' — only rendered when the
    run has >= 3 graders (the delta is vs the committed two-grader run)."""
    if len(graders) < 3:
        return []
    lines: list[str] = []
    add = lines.append
    add("## 7. What the third grader changed (delta vs the two-grader run)")
    add("")
    ref = TWO_GRADER_REFERENCE
    judge = overall["dimensions"]["judge"]
    kappas = {
        pair: p["kappa"] for pair, p in judge["pairwise"].items() if p["kappa"] is not None
    }
    alpha = judge["alpha"]["alpha"]
    if kappas:
        lo_pair = min(kappas, key=kappas.get)
        hi_pair = max(kappas, key=kappas.get)
        add(f"- **Judge κ range across pairs**: {_f(kappas[lo_pair])} "
            f"({lo_pair.replace('|', ' vs ')}) to {_f(kappas[hi_pair])} "
            f"({hi_pair.replace('|', ' vs ')}); all pairs: "
            + ", ".join(f"{p.replace('|', ' vs ')} = {_f(k)}" for p, k in kappas.items())
            + ".")
    direction = "up" if (alpha or 0) > ref["alpha_judge"] else "down"
    add(f"- **Judge α**: {_f(alpha)} across all three graders, vs "
        f"{ref['alpha_judge']:.3f} in the committed two-grader (gemma+qwen) run — "
        f"{direction} by {_f(abs((alpha or 0) - ref['alpha_judge']))}.")
    add("")
    add("Claims (a)–(g): committed two-grader verdicts vs muse alone vs the "
        "majority ensemble. The committed columns are the reference verdicts from "
        "the pre-amendment run (v2_gemma / v2_qwen, unchanged files).")
    add("")
    labels = [lbl for lbl in assembly["claims"]["a"] if lbl not in ("gemma", "qwen")]
    add("| claim | gemma (committed) | qwen (committed) | "
        + " | ".join(labels) + " | changed? |")
    add("|---|---|---|" + "---|" * (len(labels) + 1))
    for key in "abcdefg":
        row = assembly["claims"][key]
        committed = ref["claims"][key]
        # sanity: this run's gemma/qwen verdicts should match the committed ones
        mismatch = (row.get("gemma") is not None and row["gemma"] != committed["gemma"]) or (
            row.get("qwen") is not None and row["qwen"] != committed["qwen"]
        )
        baseline = {committed["gemma"], committed["qwen"]}
        news = {row.get(lbl) for lbl in labels if row.get(lbl) is not None}
        changed = "yes" if (news and news != baseline) else "no"
        note = " (RERUN MISMATCH vs committed)" if mismatch else ""
        add(f"| ({key}) | {_yn(committed['gemma'])} | {_yn(committed['qwen'])} | "
            + " | ".join(_yn(row.get(lbl)) for lbl in labels)
            + f" | {changed}{note} |")
    add("")
    add("Reading: a claim's verdict set 'changed' when the {muse, ensemble} "
        "verdicts differ from the committed {gemma, qwen} verdict set. The one "
        "committed split was claim (e) (gemma NO / qwen YES); the ensemble column "
        "above is the majority-vote resolution of such splits.")
    add("")
    return lines


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_graders(items: list[str]) -> dict[str, Path]:
    graders: dict[str, Path] = {}
    for item in items:
        if "=" not in item:
            raise SystemExit(f"--graders takes label=path entries; got {item!r}")
        label, path = item.split("=", 1)
        label = label.strip()
        if not label or label in graders:
            raise SystemExit(f"duplicate or empty grader label in {item!r}")
        graders[label] = Path(path)
    if len(graders) < 2:
        raise SystemExit("need at least two graders for agreement statistics")
    return graders


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Inter-grader agreement, COI test, headline assembly, ensemble (B3)."
    )
    parser.add_argument("--graders", nargs="+", required=True, metavar="LABEL=PATH",
                        help="two or more codes files; the FIRST is the ensemble primary")
    parser.add_argument("--edits", type=Path, default=DEFAULT_EDITS)
    parser.add_argument("--out-report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--out-ensemble", type=Path, default=DEFAULT_ENSEMBLE)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--B", type=int, default=None,
                        help="COI bootstrap draws (default: config.yaml bootstrap.B)")
    parser.add_argument("--seed", type=int, default=None,
                        help="COI bootstrap seed (default: config.yaml seeds.bootstrap)")
    parser.add_argument("--coi-grader", default=None,
                        help="COI target label (default: first label containing 'gemma')")
    args = parser.parse_args(argv)

    grader_paths = parse_graders(args.graders)
    graders = list(grader_paths)
    primary_label, other_labels = graders[0], graders[1:]

    if args.B is None or args.seed is None:
        import yaml

        config = yaml.safe_load((ANALYSIS_ROOT / "config.yaml").read_text(encoding="utf-8"))
        B = args.B if args.B is not None else int(config["bootstrap"]["B"])
        seed = args.seed if args.seed is not None else int(config["seeds"]["bootstrap"])
    else:
        B, seed = args.B, args.seed

    edits = load_jsonl(args.edits)
    universe = {e["edit_id"] for e in edits}
    print(f"[intergrader] {len(edits)} canonical edits; graders: {graders} "
          f"(primary={primary_label}); B={B} seed={seed}")

    rows_by_grader = {g: codes_io.load_codes(path) for g, path in grader_paths.items()}
    codings_by_grader = {g: valid_codings(rows) for g, rows in rows_by_grader.items()}
    grader_rows_meta = {}
    for g in graders:
        n_outside = sum(1 for eid in rows_by_grader[g] if eid not in universe)
        grader_rows_meta[g] = {
            "n_unique_ids": len(rows_by_grader[g]),
            "n_valid": len(codings_by_grader[g]),
            "n_outside_frame": n_outside,
        }
        print(f"[intergrader]   {g}: {grader_rows_meta[g]['n_unique_ids']} ids, "
              f"{grader_rows_meta[g]['n_valid']} valid codings, "
              f"{n_outside} outside the edit frame")

    # ---- 1. overall agreement + 2/3. breakdowns ---------------------------
    overall = agreement_block(codings_by_grader, universe)
    print(f"[intergrader] overall agreement done "
          f"(complete-case N = {overall['n_complete_all_graders']})")
    by_owner = {
        group: agreement_block(codings_by_grader, ids)
        for group, ids in group_universes(edits, "document_owner").items()
    }
    by_provider = {
        group: agreement_block(codings_by_grader, ids)
        for group, ids in group_universes(edits, "provider").items()
    }
    print(f"[intergrader] breakdowns done ({len(by_owner)} owners, "
          f"{len(by_provider)} providers)")

    # ---- 4. COI test ------------------------------------------------------
    if args.coi_grader is not None:
        coi_target = args.coi_grader
        if coi_target not in graders:
            raise SystemExit(f"--coi-grader {coi_target!r} not among {graders}")
    else:
        gemma_like = [g for g in graders if "gemma" in g.lower()]
        coi_target = gemma_like[0] if gemma_like else graders[0]
    coi_results = []
    for ga, gb in combinations(graders, 2):
        # pairs containing the COI target are comparators (target first);
        # every other pair is a no-COI baseline
        if coi_target in (ga, gb):
            target, other, role = coi_target, (gb if ga == coi_target else ga), "coi"
        else:
            target, other, role = ga, gb, "baseline"
        result = coi_test(
            edits, codings_by_grader[target], codings_by_grader[other], B=B, seed=seed
        )
        verdict = coi_verdict(result, target, other)
        coi_results.append({"target": target, "other": other, "role": role,
                            "result": result, "verdict": verdict})
        print(f"[intergrader] COI ({role}) {target} vs {other}: {verdict}")

    # ---- 6. ensemble (written BEFORE headline so its column reads the file)
    ensemble_rows = build_ensemble_rows(graders, rows_by_grader)
    write_ensemble(args.out_ensemble, ensemble_rows)
    ens_summary = ensemble_summary(ensemble_rows, graders)
    print(f"[intergrader] wrote {args.out_ensemble} ({ens_summary['n_rows']} rows)")

    # ---- 5. headline per grader + ensemble --------------------------------
    headline_results: dict[str, dict] = {}
    headline_meta: dict[str, dict] = {}
    for g in graders:
        headline_results[g], headline_meta[g] = compute_headline_for(grader_paths[g], edits)
        print(f"[intergrader] headline[{g}] done")
    headline_results["ensemble"], headline_meta["ensemble"] = compute_headline_for(
        args.out_ensemble, edits
    )
    print("[intergrader] headline[ensemble] done")
    assembly = assemble_headline(headline_results)

    # ---- report + JSON ----------------------------------------------------
    meta = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "edits_path": repo_rel(args.edits),
        "n_edits": len(edits),
        "grader_rows": grader_rows_meta,
        "ensemble_path": repo_rel(args.out_ensemble),
    }
    report = render_report(
        graders, {g: repo_rel(p) for g, p in grader_paths.items()}, overall, by_owner,
        by_provider, coi_results, assembly, headline_meta, ens_summary,
        primary_label, other_labels, meta,
    )
    args.out_report.parent.mkdir(parents=True, exist_ok=True)
    args.out_report.write_text(report, encoding="utf-8")
    print(f"[intergrader] wrote {args.out_report}")

    payload = {
        **meta,
        "B": B,
        "seed": seed,
        "graders": graders,
        "primary_grader": primary_label,
        "agreement_overall": overall,
        "agreement_by_document_owner": by_owner,
        "agreement_by_provider": by_provider,
        "coi": [
            {"target": c["target"], "other": c["other"], "role": c["role"],
             "verdict": c["verdict"], **c["result"]}
            for c in coi_results
        ],
        "headline_assembly": assembly,
        "headline_meta": headline_meta,
        "ensemble_summary": ens_summary,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, indent=1, default=str), encoding="utf-8")
    print(f"[intergrader] wrote {args.out_json}")


if __name__ == "__main__":
    main()
