"""Workstream B3 — inter-grader agreement, grader-COI test, per-grader
headline assembly, and the two-grader ensemble file (BRIEF section 3 B3;
DECISIONS section 1).

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

3. COI TEST. Gemma-vs-other-grader disagreement rate on Gemini-model edits
   (editing provider == "google") vs non-Gemini-model edits, per dimension
   (judge, patienthood, conflict-presence profile, any-of-the-three), with
   the difference and a cluster bootstrap 95% CI. Resampling unit = the
   chain, keyed (run_id, model_id, document_id, condition) — the identity
   convention from bootstrap.build_chains — resampled with replacement
   independently within the Gemini and non-Gemini groups (a chain's editing
   provider is constant, so every chain belongs to exactly one group). The
   report states plainly whether Gemma diverges more on Gemini edits.

4. HEADLINE PER GRADER. headline.compute_headline (recode/src/headline.py)
   is invoked in-process on each codes file AND on the freshly written
   ensemble file, and the BRIEF section-8 table is assembled with one
   column per grader plus the ensemble column. (Full per-grader detail —
   drift method A vs B, modal conflict pairs, claim-number JSON — lives in
   the per-label partials that headline.py's own CLI writes.)

5. ENSEMBLE. data/codes/ensemble.jsonl per DECISIONS section 1's
   two-grader rule: the primary (Gemma) rows, plus per-dimension
   disagrees_with_<other> flags and the other grader's coding payload for
   reference. Schema documented on write_ensemble() below.

CLI (paths are arguments; nothing here reads the in-flight v2 outputs
unless told to):

    .venv/bin/python recode/src/intergrader.py \
        --graders gemma=recode/data/codes/v2_gemma.jsonl \
                  qwen=recode/data/codes/v2_qwen.jsonl \
        --edits recode/data/canonical/edits.jsonl \
        --out-report recode/reports/B_intergrader.md \
        --out-ensemble recode/data/codes/ensemble.jsonl

The FIRST grader listed is the ensemble primary; the COI target defaults
to the first label containing "gemma" (else the first grader). B and seed
default to bootstrap.B and seeds.bootstrap in recode/config.yaml.

Codes-file convention (shared, via codes_io): append-only JSONL, LAST row
per edit_id wins; id key is `edit_id` (v2/e-run rows) or `id` (v1.jsonl).
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
import warnings
from collections import defaultdict
from itertools import combinations
from pathlib import Path

import numpy as np
from sklearn.metrics import cohen_kappa_score

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import RECODE_ROOT  # noqa: E402
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

DEFAULT_EDITS = RECODE_ROOT / "data" / "canonical" / "edits.jsonl"
DEFAULT_REPORT = RECODE_ROOT / "reports" / "B_intergrader.md"
DEFAULT_ENSEMBLE = RECODE_ROOT / "data" / "codes" / "ensemble.jsonl"
DEFAULT_JSON = RECODE_ROOT / "data" / "analysis" / "intergrader" / "B_intergrader.json"


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
# Ensemble file (DECISIONS section 1, two-grader rule)
# ---------------------------------------------------------------------------


def build_ensemble_rows(
    primary_label: str,
    primary_rows: dict[str, dict],
    other_rows_by_label: dict[str, dict[str, dict]],
) -> list[dict]:
    """Ensemble rows: primary (Gemma) codes + per-grader disagreement flags.

    See write_ensemble() for the full schema. Rows are emitted for every
    edit_id in the primary codes file (last row per id), sorted by edit_id.
    """
    rows = []
    for edit_id in sorted(primary_rows):
        primary_row = primary_rows[edit_id]
        primary_coding = codes_io.coding_of(primary_row)
        out = {
            "edit_id": edit_id,
            "primary_grader": primary_label,
            "grader": primary_row.get("grader") or primary_row.get("coder_model"),
            "prompt_sha256": primary_row.get("prompt_sha256"),
            "timestamp": primary_row.get("timestamp"),
            "coding": primary_row.get("coding"),
            "error": primary_row.get("error"),
            "primary_coding_valid": primary_coding is not None,
        }
        for label, other_rows in other_rows_by_label.items():
            other_row = other_rows.get(edit_id)
            other_coding = codes_io.coding_of(other_row) if other_row is not None else None
            out[f"{label}_coding"] = other_coding
            if primary_coding is None or other_coding is None:
                flags = {"judge": None, "patienthood": None, "conflicts": None, "any": None}
            else:
                judge_d = codes_io.judge_score(primary_coding) != codes_io.judge_score(
                    other_coding
                )
                pat_d = codes_io.patienthood_level(primary_coding) != codes_io.patienthood_level(
                    other_coding
                )
                conflict_flags = {
                    code: codes_io.has_conflict(primary_coding, code)
                    != codes_io.has_conflict(other_coding, code)
                    for code in CONFLICT_CODES
                }
                flags = {
                    "judge": judge_d,
                    "patienthood": pat_d,
                    "conflicts": conflict_flags,
                    "any": judge_d or pat_d or any(conflict_flags.values()),
                }
            out[f"disagrees_with_{label}"] = flags
        rows.append(out)
    return rows


def write_ensemble(path: Path, rows: list[dict]) -> None:
    """Write data/codes/ensemble.jsonl.

    SCHEMA (one JSON object per line, one line per edit_id in the primary
    codes file; consumers follow the shared codes-file convention — keep the
    LAST row per edit_id — though this writer emits exactly one):

      edit_id               str   the v1 pipe-id
      primary_grader        str   label of the primary grader (e.g. "gemma")
      grader                str?  primary row's grader model string
      prompt_sha256         str?  carried from the primary row
      timestamp             str?  carried from the primary row
      coding                dict|null   THE ensemble code = the primary
                            (Gemma) coding verbatim; null when the primary
                            call failed (codes_io.coding_of validates on
                            read, so downstream tools treat invalid payloads
                            as uncoded either way)
      error                 str|null    primary row's error, if any
      primary_coding_valid  bool  codes_io.coding_of(primary row) != None
      disagrees_with_<g>    dict  one block per non-primary grader <g>:
            judge        bool|null   graders' judge scores differ
            patienthood  bool|null   patienthood levels differ
            conflicts    {code: bool}|null   per-conflict-code PRESENCE
                         (>=1 conflict of the code) differs — counts and
                         attributes are not compared
            any          bool|null   any of the above
        All four are null when either grader lacks a valid coding for the
        edit (per the assignment: edits lacking a valid qwen coding get
        disagrees_with_qwen = null flags).
      <g>_coding            dict|null   grader <g>'s VALID coding for
                            reference; null when missing or invalid.

    NOT carried from the primary rows: raw_response and attempts (bulky;
    they remain in the primary grader's own codes file).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def ensemble_summary(rows: list[dict], other_labels: list[str]) -> dict:
    summary = {
        "n_rows": len(rows),
        "n_primary_valid": sum(1 for r in rows if r["primary_coding_valid"]),
        "per_other_grader": {},
    }
    for label in other_labels:
        key = f"disagrees_with_{label}"
        compared = [r[key] for r in rows if r[key]["judge"] is not None]
        n_compared = len(compared)
        per_code = {
            code: sum(1 for f in compared if f["conflicts"][code]) for code in CONFLICT_CODES
        }
        summary["per_other_grader"][label] = {
            "n_compared": n_compared,
            "n_null_flags": len(rows) - n_compared,
            "n_disagree_judge": sum(1 for f in compared if f["judge"]),
            "n_disagree_patienthood": sum(1 for f in compared if f["patienthood"]),
            "n_disagree_any": sum(1 for f in compared if f["any"]),
            "n_disagree_conflict_presence": per_code,
        }
    return summary


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
        "codes_path": str(path),
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
    add(f"_Generated {meta['timestamp']} by `recode/src/intergrader.py`._")
    add("")
    add("## Inputs")
    add("")
    add(f"- Canonical edits: `{meta['edits_path']}` — {meta['n_edits']} records.")
    for grader in graders:
        add(f"- Grader `{grader}`: `{grader_paths[grader]}` — "
            f"{meta['grader_rows'][grader]['n_unique_ids']} unique edit_ids after "
            f"last-row-wins, {meta['grader_rows'][grader]['n_valid']} valid codings "
            f"({meta['grader_rows'][grader]['n_outside_frame']} ids outside the edit frame).")
    add(f"- Ensemble: `{meta['ensemble_path']}` (written by this run; primary = "
        f"`{primary_label}`).")
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
        "the Gemma-vs-other-grader disagreement rate on Gemini-model edits (editing "
        "provider `google`) vs all other edits, with the difference and a cluster "
        "bootstrap 95% percentile CI — chains (run_id × model × document × condition, "
        "the `bootstrap.py` identity convention) resampled with replacement, "
        "independently within each group.")
    add("")
    for coi_entry in coi_results:
        coi = coi_entry["result"]
        target, other = coi_entry["target"], coi_entry["other"]
        add(f"### {target} vs {other}")
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
    add("Each column is `headline.compute_headline` (recode/src/headline.py) run on "
        "that codes file; the ensemble column is the freshly written "
        "`ensemble.jsonl` run through the same computation. Because the ensemble's "
        f"coding payload IS the primary (`{primary_label}`) coding, its column "
        f"matches `{primary_label}` by construction — it is included to prove the "
        "file round-trips. Point estimates only; the cluster bootstrap (Workstream "
        "D) owns uncertainty. Full per-grader detail (drift method A, modal "
        "conflict pairs, per-claim numbers) is in the per-label headline partials.")
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
        "partial (`recode/reports/partials/headline_<label>.md`) and JSON "
        "(`recode/data/analysis/headline/<label>.json`).")
    add("")
    add("## 6. Ensemble file")
    add("")
    add(f"`{meta['ensemble_path']}` — DECISIONS §1 two-grader rule: no majority vote; "
        f"the `{primary_label}` codes are primary and every other grader contributes "
        "per-dimension disagreement flags. Schema is documented on "
        "`write_ensemble()` in `recode/src/intergrader.py`.")
    add("")
    add(f"- Rows: {ens_summary['n_rows']} (one per edit_id in the primary codes "
        f"file); {ens_summary['n_primary_valid']} carry a valid primary coding.")
    for label in other_labels:
        s = ens_summary["per_other_grader"][label]
        add(f"- vs `{label}`: {s['n_compared']} edits compared "
            f"({s['n_null_flags']} rows have null flags — one grader lacked a valid "
            f"coding); disagreements: judge {s['n_disagree_judge']}, patienthood "
            f"{s['n_disagree_patienthood']}, any dimension {s['n_disagree_any']}; "
            "per-code presence: "
            + ", ".join(f"{c}={s['n_disagree_conflict_presence'][c]}" for c in CONFLICT_CODES)
            + ".")
    add("")
    add("Per BRIEF §3 B3 (two graders): disagreements are FLAGGED, not voted away — "
        "downstream consumers can filter on `disagrees_with_*` to run "
        "agreement-restricted sensitivity slices.")
    add("")
    return "\n".join(lines)


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

        config = yaml.safe_load((RECODE_ROOT / "config.yaml").read_text(encoding="utf-8"))
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
    for other in graders:
        if other == coi_target:
            continue
        result = coi_test(
            edits, codings_by_grader[coi_target], codings_by_grader[other], B=B, seed=seed
        )
        verdict = coi_verdict(result, coi_target, other)
        coi_results.append({"target": coi_target, "other": other,
                            "result": result, "verdict": verdict})
        print(f"[intergrader] COI {coi_target} vs {other}: {verdict}")

    # ---- 6. ensemble (written BEFORE headline so its column reads the file)
    ensemble_rows = build_ensemble_rows(
        primary_label,
        rows_by_grader[primary_label],
        {g: rows_by_grader[g] for g in other_labels},
    )
    write_ensemble(args.out_ensemble, ensemble_rows)
    ens_summary = ensemble_summary(ensemble_rows, other_labels)
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
        "edits_path": str(args.edits),
        "n_edits": len(edits),
        "grader_rows": grader_rows_meta,
        "ensemble_path": str(args.out_ensemble),
    }
    report = render_report(
        graders, {g: str(p) for g, p in grader_paths.items()}, overall, by_owner,
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
            {"target": c["target"], "other": c["other"], "verdict": c["verdict"],
             **c["result"]}
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
