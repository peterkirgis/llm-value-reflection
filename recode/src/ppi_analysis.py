#!/usr/bin/env python
"""Workstream C4 — prediction-powered inference (BRIEF section 4 C4 + Appendix VI).

For each model m and each estimand below, combines the predictor grader's
codes on all N_m edits of model m with the n_m human labels from the blind
coding sheet to produce:

  - the naive grader estimate on all N_m (with a t-based CI from the grader
    labels alone),
  - the PPI point estimate and 95% CI via ppi_py.ppi_mean_ci (PPI++), falling
    back to the Appendix VI manual formulas in stats.py if ppi_py errors,
  - the classical human-only estimate and t-based 95% CI (n_m = 15 in the
    production draw).

Estimands: mean judge score; P(judge = +1); P(judge = -1);
P(patienthood = affirm); P(edit has a conflict of code c) for each c; and
drift@20 = 20 x mean judge. Caveat on drift@20 (stated in the report):
cumulative drift is a run-level quantity; here the per-edit judge score is
the unit and its mean is multiplied by 20, ignoring within-run dependence
and uncoded rounds.

Frame rules (enforced with hard assertions):
  - adjudication_extra rows are EXCLUDED from PPI (they are not a random
    sample); they appear only in C_human_validation.md.
  - the PPI frame is exactly the per-model simple random draw (blind_key.csv
    rows with adjudication_extra = false) intersected with the rows the
    primary coder actually coded — partially-coded sheets simply yield a
    smaller per-model n, reported per model.

Human coders: PPI uses CODER 1's labels (the first --sheets argument) as the
primary Y. A sensitivity appendix re-runs every estimand on coder 2 and on
the row-mean of the coders (rows coded by all coders). This convention is
stated in the report.

CLI (from the repo root):
    .venv/bin/python recode/src/ppi_analysis.py \
        --sheets recode/human/coding_sheet_<coder>.csv [MORE...] \
        --blind-key recode/human/blind_key.csv \
        --predictor recode/data/codes/v2_gemma.jsonl \
        --edits recode/data/canonical/edits.jsonl \
        --out recode/reports/C_ppi.md
"""

from __future__ import annotations

import argparse
import datetime
import json
import math
from pathlib import Path

import numpy as np

try:
    from common import RECODE_ROOT
except ImportError:  # pragma: no cover - direct-script execution fallback
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from common import RECODE_ROOT

import codes_io
from human_validation import (
    CANONICAL_MODEL_ORDER,
    CONFLICT_CODES,
    fmt,
    human_conflict_present,
    load_blind_key,
    load_edits_meta,
    ordered,
    parse_sheet,
    unblind,
)
from stats import ppi_mean_manual

DEFAULT_JSON_DIR = RECODE_ROOT / "data" / "analysis"

DRIFT_CAVEAT = (
    "Caveat (BRIEF C4): cumulative drift at round 20 is a run-level "
    "quantity; for PPI the per-edit judge score is the unit and its mean is "
    "multiplied by 20. This ignores within-run dependence and uncoded "
    "rounds, so read drift@20 here as a scaled per-edit mean, not a "
    "trajectory statistic (the cluster bootstrap in D_bootstrap.md owns the "
    "run-level version)."
)


class PPIFrameError(ValueError):
    """The labeled set is not the random draw actually coded."""


# ---------------------------------------------------------------------------
# Estimand registry: (key, label, human-row value fn, grader-coding value fn)
# Value fns return float or None (None = unit excluded for that estimand).
# ---------------------------------------------------------------------------


def _h_judge(row: dict) -> float | None:
    return float(row["judge"]) if row["judge"] is not None else None


def _h_judge_indicator(target: int):
    def fn(row: dict) -> float | None:
        if row["judge"] is None:
            return None
        return 1.0 if row["judge"] == target else 0.0

    return fn


def _h_affirm(row: dict) -> float | None:
    if row["patienthood"] is None:
        return None
    return 1.0 if row["patienthood"] == "affirm" else 0.0


def _h_conflict(code: str):
    def fn(row: dict) -> float | None:
        return 1.0 if human_conflict_present(row, code) else 0.0

    return fn


def _f_judge(coding: dict) -> float | None:
    score = codes_io.judge_score(coding)
    return float(score) if score is not None else None


def _f_judge_indicator(target: int):
    def fn(coding: dict) -> float | None:
        score = codes_io.judge_score(coding)
        if score is None:
            return None
        return 1.0 if score == target else 0.0

    return fn


def _f_affirm(coding: dict) -> float | None:
    level = codes_io.patienthood_level(coding)
    if level is None:
        return None
    return 1.0 if level == "affirm" else 0.0


def _f_conflict(code: str):
    def fn(coding: dict) -> float | None:
        return 1.0 if codes_io.has_conflict(coding, code) else 0.0

    return fn


def estimand_registry() -> list[tuple[str, str, object, object]]:
    registry = [
        ("mean_judge", "Mean judge score", _h_judge, _f_judge),
        ("p_judge_plus1", "P(judge = +1)", _h_judge_indicator(1), _f_judge_indicator(1)),
        ("p_judge_minus1", "P(judge = -1)", _h_judge_indicator(-1), _f_judge_indicator(-1)),
        ("p_affirm", "P(patienthood = affirm)", _h_affirm, _f_affirm),
    ]
    for code in CONFLICT_CODES:
        registry.append(
            (
                f"p_conflict_{code}",
                f"P(conflict = {code})",
                _h_conflict(code),
                _f_conflict(code),
            )
        )
    return registry


# ---------------------------------------------------------------------------
# Frame construction (and the hard assertion)
# ---------------------------------------------------------------------------


def build_ppi_frame(
    sheet: dict, key: dict[str, dict], edits: dict[str, dict]
) -> dict:
    """The PPI labeled frame for one coder: coded, non-extra rows.

    Verifies (raising PPIFrameError otherwise) that the frame is EXACTLY the
    per-model random draw actually coded:
      - no adjudication_extra row is in the frame;
      - every frame edit is in edits.jsonl with apply_status 'applied' (the
        sampling-frame condition of the draw);
      - no edit appears twice;
      - the frame equals {non-extra blind-key edits that this coder coded},
        recomputed independently from the key.

    Returns {rows, per_model_n, per_model_draw, n_extra_excluded,
    n_uncoded_excluded}.
    """
    rows = [r for r in sheet["coded"] if not r["adjudication_extra"]]
    frame_ids = [r["edit_id"] for r in rows]
    if len(frame_ids) != len(set(frame_ids)):
        raise PPIFrameError(
            f"sheet {sheet['coder']}: duplicate edit_ids in the labeled frame"
        )
    if any(r["adjudication_extra"] for r in rows):  # defensive
        raise PPIFrameError("adjudication_extra row leaked into the PPI frame")

    draw_ids = {
        entry["edit_id"]
        for entry in key.values()
        if not entry["adjudication_extra"]
    }
    coded_ids = {r["edit_id"] for r in sheet["coded"]}
    expected = draw_ids & coded_ids
    if set(frame_ids) != expected:
        raise PPIFrameError(
            f"sheet {sheet['coder']}: labeled frame != (random draw ∩ coded "
            f"rows); frame has {len(frame_ids)}, expected {len(expected)}"
        )

    per_model_n: dict[str, int] = {}
    for r in rows:
        edit = edits.get(r["edit_id"])
        if edit is None:
            raise PPIFrameError(
                f"frame edit {r['edit_id']!r} is not in edits.jsonl"
            )
        if edit.get("apply_status") != "applied":
            raise PPIFrameError(
                f"frame edit {r['edit_id']!r} has apply_status "
                f"{edit.get('apply_status')!r} (draw frame is applied-only)"
            )
        model = edit["model"]
        per_model_n[model] = per_model_n.get(model, 0) + 1

    per_model_draw: dict[str, int] = {}
    for eid in draw_ids:
        edit = edits.get(eid)
        if edit is None:
            raise PPIFrameError(f"blind-key edit {eid!r} is not in edits.jsonl")
        model = edit["model"]
        per_model_draw[model] = per_model_draw.get(model, 0) + 1

    for model, n in per_model_n.items():
        if n > per_model_draw.get(model, 0):
            raise PPIFrameError(
                f"model {model!r}: labeled n={n} exceeds the draw size "
                f"{per_model_draw.get(model, 0)}"
            )

    return {
        "rows": rows,
        "per_model_n": per_model_n,
        "per_model_draw": per_model_draw,
        "n_extra_excluded": sum(
            1 for r in sheet["coded"] if r["adjudication_extra"]
        ),
        "n_uncoded_excluded": sheet["uncoded_count"],
    }


# ---------------------------------------------------------------------------
# Estimators
# ---------------------------------------------------------------------------


def classical_ci(values: list[float], alpha: float = 0.05) -> dict:
    """t-based mean CI (the classical estimate from the labels alone)."""
    from scipy.stats import t as t_dist

    n = len(values)
    if n == 0:
        return {"point": None, "lo": None, "hi": None, "n": 0}
    arr = np.asarray(values, dtype=float)
    point = float(arr.mean())
    if n == 1:
        return {"point": point, "lo": None, "hi": None, "n": 1}
    se = float(arr.std(ddof=1) / math.sqrt(n))
    half = float(t_dist.ppf(1 - alpha / 2, n - 1)) * se
    return {"point": point, "lo": point - half, "hi": point + half, "n": n}


def _ppi_via_ppi_py(
    y: list[float], f_lab: list[float], f_all: list[float], alpha: float = 0.05
) -> dict:
    """Direct ppi_py call (PPI++). ppi_py returns size-1 ndarrays, which
    NumPy 2 refuses to cast with float() — extract the scalar explicitly
    (stats.ppi_mean's float() cast trips over exactly this and always falls
    back to manual; here the ppi_py path actually runs). Raises on any
    ppi_py error or non-finite output so the caller can fall back."""
    from ppi_py import ppi_mean_ci, ppi_mean_pointestimate

    y_arr = np.asarray(y, dtype=float)
    f_lab_arr = np.asarray(f_lab, dtype=float)
    f_all_arr = np.asarray(f_all, dtype=float)
    with np.errstate(invalid="ignore", divide="ignore"):
        # A degenerate predictor makes ppi_py's tuning lambda 0/0; the nan
        # is caught by the finiteness check below, not surfaced as warnings.
        point = np.asarray(
            ppi_mean_pointestimate(y_arr, f_lab_arr, f_all_arr)
        ).reshape(-1)[0]
        lo, hi = ppi_mean_ci(y_arr, f_lab_arr, f_all_arr, alpha=alpha)
    lo = np.asarray(lo).reshape(-1)[0]
    hi = np.asarray(hi).reshape(-1)[0]
    if not (np.isfinite(point) and np.isfinite(lo) and np.isfinite(hi)):
        raise ValueError("ppi_py returned non-finite estimates")
    return {"point": float(point), "lo": float(lo), "hi": float(hi),
            "impl": "ppi_py"}


def ppi_estimate(
    y: list[float], f_lab: list[float], f_all: list[float]
) -> dict:
    """PPI point + 95% CI: ppi_py.ppi_mean_ci (PPI++), falling back to the
    Appendix VI manual estimator (stats.ppi_mean_manual) if ppi_py errors —
    e.g. degenerate variance (a constant predictor makes the PPI++ tuning
    lambda 0/0) or the package missing."""
    if len(y) < 2 or len(f_all) < 2:
        return {"point": None, "lo": None, "hi": None, "impl": None,
                "n": len(y), "N": len(f_all)}
    try:
        out = _ppi_via_ppi_py(y, f_lab, f_all)
    except Exception:  # noqa: BLE001 - any ppi_py failure -> manual fallback
        manual = ppi_mean_manual(
            np.asarray(y, dtype=float),
            np.asarray(f_lab, dtype=float),
            np.asarray(f_all, dtype=float),
        )
        out = {"point": manual["point"], "lo": float(manual["lo"]),
               "hi": float(manual["hi"]), "impl": "manual"}
    return {**out, "n": len(y), "N": len(f_all)}


def scale_estimate(estimate: dict, factor: float) -> dict:
    out = dict(estimate)
    for field in ("point", "lo", "hi"):
        if out.get(field) is not None:
            out[field] = out[field] * factor
    return out


def predictor_by_model(
    predictor: dict[str, dict | None], edits: dict[str, dict]
) -> tuple[dict[str, dict[str, dict]], dict]:
    """model -> {edit_id -> valid coding} over the predictor's codes, plus
    join diagnostics."""
    by_model: dict[str, dict[str, dict]] = {}
    n_invalid = 0
    n_unknown_edit = 0
    for edit_id, coding in predictor.items():
        edit = edits.get(edit_id)
        if edit is None:
            n_unknown_edit += 1
            continue
        if coding is None:
            n_invalid += 1
            continue
        by_model.setdefault(edit["model"], {})[edit_id] = coding
    return by_model, {
        "n_invalid_codings": n_invalid,
        "n_codes_for_unknown_edits": n_unknown_edit,
    }


def compute_estimates(
    labeled_rows: list[dict],
    pred_by_model: dict[str, dict[str, dict]],
    edits: dict[str, dict],
    y_of_row,
) -> dict:
    """All estimands x models for one Y source.

    y_of_row(row, h_fn) -> float|None supplies the human label, so the same
    machinery serves coder-1, coder-2, and row-mean sensitivity runs.
    Labeled rows without a valid predictor coding are dropped (PPI needs
    f_j) and counted.
    """
    rows_by_model: dict[str, list[dict]] = {}
    dropped_no_predictor: list[str] = []
    for row in labeled_rows:
        model = edits[row["edit_id"]]["model"]
        if row["edit_id"] not in pred_by_model.get(model, {}):
            dropped_no_predictor.append(row["edit_id"])
            continue
        rows_by_model.setdefault(model, []).append(row)

    models = ordered(
        set(rows_by_model) | set(pred_by_model), CANONICAL_MODEL_ORDER
    )
    estimands: dict[str, dict] = {}
    for est_key, label, h_fn, f_fn in estimand_registry():
        per_model: dict[str, dict] = {}
        for model in models:
            codings = pred_by_model.get(model, {})
            f_all = [
                value
                for value in (f_fn(c) for c in codings.values())
                if value is not None
            ]
            y_vals: list[float] = []
            f_lab: list[float] = []
            for row in rows_by_model.get(model, []):
                y = y_of_row(row, h_fn)
                f = f_fn(codings[row["edit_id"]])
                if y is None or f is None:
                    continue
                y_vals.append(y)
                f_lab.append(f)
            per_model[model] = {
                "N_graded": len(f_all),
                "n_labeled": len(y_vals),
                "naive": classical_ci(f_all),
                "ppi": ppi_estimate(y_vals, f_lab, f_all),
                "human": classical_ci(y_vals),
            }
        estimands[est_key] = {"label": label, "models": per_model}

    # drift@20 = 20 x mean judge (see DRIFT_CAVEAT).
    drift_models = {}
    for model, cell in estimands["mean_judge"]["models"].items():
        drift_models[model] = {
            "N_graded": cell["N_graded"],
            "n_labeled": cell["n_labeled"],
            "naive": scale_estimate(cell["naive"], 20.0),
            "ppi": scale_estimate(cell["ppi"], 20.0),
            "human": scale_estimate(cell["human"], 20.0),
        }
    estimands["drift20"] = {
        "label": "Cumulative drift @ round 20 (= 20 x mean judge)",
        "caveat": DRIFT_CAVEAT,
        "models": drift_models,
    }

    return {
        "models": models,
        "estimands": estimands,
        "dropped_no_predictor_code": dropped_no_predictor,
        "per_model_n_labeled": {
            m: len(rs) for m, rs in sorted(rows_by_model.items())
        },
    }


def y_primary(row: dict, h_fn) -> float | None:
    return h_fn(row)


def make_y_row_mean(sheets_rows_by_edit: list[dict[str, dict]]):
    """Row-mean Y over the coders: mean of every coder's value on rows all
    coders coded (None if any coder's value is missing)."""

    def y_fn(row: dict, h_fn) -> float | None:
        values = []
        for by_edit in sheets_rows_by_edit:
            other = by_edit.get(row["edit_id"])
            if other is None:
                return None
            value = h_fn(other)
            if value is None:
                return None
            values.append(value)
        return float(np.mean(values))

    return y_fn


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def ci_str(cell: dict) -> str:
    if cell.get("point") is None:
        return "n/a"
    if cell.get("lo") is None:
        return f"{fmt(cell['point'])} [CI n/a]"
    return f"{fmt(cell['point'])} [{fmt(cell['lo'])}, {fmt(cell['hi'])}]"


def estimand_table(est: dict, models: list[str]) -> list[str]:
    lines = [
        "| model | N (graded) | n (human) | naive grader [95% CI] | "
        "PPI [95% CI] | impl | human-only [95% CI] |",
        "|---|---|---|---|---|---|---|",
    ]
    for model in models:
        cell = est["models"].get(model)
        if cell is None:
            continue
        lines.append(
            f"| {model} | {cell['N_graded']} | {cell['n_labeled']} | "
            f"{ci_str(cell['naive'])} | {ci_str(cell['ppi'])} | "
            f"{cell['ppi'].get('impl') or 'n/a'} | {ci_str(cell['human'])} |"
        )
    return lines


def build_report(analysis: dict) -> str:
    meta = analysis["meta"]
    primary = analysis["primary"]
    lines: list[str] = []
    add = lines.append
    add("# C4 — Prediction-powered inference (PPI)")
    add("")
    add(f"Generated {meta['generated_utc']} by `recode/src/ppi_analysis.py`.")
    add("")
    add(f"- Predictor f: `{meta['predictor']}` (label: {meta['predictor_label']})")
    add(f"- Sheets: {', '.join(meta['sheet_paths'])}")
    add(f"- Blind key: `{meta['blind_key']}` | edits: `{meta['edits']}`")
    add("")
    add("## Conventions")
    add("")
    add(
        f"- **Primary Y = coder 1** ({meta['primary_coder']}, the first "
        "--sheets argument). The sensitivity appendix re-runs every "
        "estimand on the other coder(s) and on the row-mean of the coders "
        "(BRIEF C4 two-coder convention)."
    )
    add(
        "- **Adjudication-extra rows are EXCLUDED** from every PPI number "
        "(they are not a random sample; BRIEF C1). Excluded here: "
        f"{meta['frame']['n_extra_excluded']} coded extra row(s); "
        f"{meta['frame']['n_uncoded_excluded']} uncoded (blank-judge) "
        "row(s) also excluded."
    )
    add(
        "- The PPI frame was verified to be exactly the per-model random "
        "draw actually coded (partially-coded sheets yield a smaller n, "
        "reported per model below)."
    )
    if meta["dropped_no_predictor_code"]:
        add(
            f"- {len(meta['dropped_no_predictor_code'])} labeled row(s) "
            "dropped because the predictor has no valid coding for the "
            "edit (PPI needs f on every labeled unit): "
            + ", ".join(f"`{e}`" for e in meta["dropped_no_predictor_code"])
        )
    add(
        "- Naive grader CI: t-based on the grader labels alone (all N_m "
        "graded edits of the model). Human-only CI: classical t-based CI "
        "from the n_m human labels alone. PPI: ppi_py `ppi_mean_ci` "
        "(PPI++), falling back to the Appendix VI manual estimator on "
        "error (the `impl` column says which ran)."
    )
    add("")
    add("## Per-model labeled n (primary coder)")
    add("")
    add("| model | draw size | n coded (labeled) |")
    add("|---|---|---|")
    for model in primary["models"]:
        draw = meta["frame"]["per_model_draw"].get(model, 0)
        n = primary["per_model_n_labeled"].get(model, 0)
        add(f"| {model} | {draw} | {n} |")
    add("")

    add("## Estimates (primary Y = coder 1)")
    add("")
    for est_key, est in primary["estimands"].items():
        add(f"### {est['label']}")
        add("")
        if est.get("caveat"):
            add(f"_{est['caveat']}_")
            add("")
        lines.extend(estimand_table(est, primary["models"]))
        add("")

    add("## Sensitivity appendix (alternative Y sources)")
    add("")
    if not analysis["sensitivity"]:
        add(
            "Only one coder sheet was provided; the coder-2 and row-mean "
            "sensitivity runs are skipped."
        )
        add("")
    for label, run in analysis["sensitivity"].items():
        add(f"### Y = {label}")
        add("")
        add("| estimand | model | n | PPI [95% CI] | human-only [95% CI] |")
        add("|---|---|---|---|---|")
        for est_key, est in run["estimands"].items():
            for model in run["models"]:
                cell = est["models"].get(model)
                if cell is None or cell["n_labeled"] == 0:
                    continue
                add(
                    f"| {est['label']} | {model} | {cell['n_labeled']} | "
                    f"{ci_str(cell['ppi'])} | {ci_str(cell['human'])} |"
                )
        add("")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def run_analysis(
    sheet_paths: list[Path],
    blind_key_path: Path,
    predictor_path: Path,
    edits_path: Path,
    predictor_label: str = "predictor",
) -> dict:
    key = load_blind_key(blind_key_path)
    edits = load_edits_meta(edits_path)
    sheets = []
    for path in sheet_paths:
        sheet = parse_sheet(path)
        unblind(sheet, key)
        sheets.append(sheet)

    predictor_rows = codes_io.load_codes(predictor_path)
    predictor = {
        edit_id: codes_io.coding_of(row)
        for edit_id, row in predictor_rows.items()
    }
    pred_by_model, join_diag = predictor_by_model(predictor, edits)

    # Primary frame: coder 1.
    frames = [build_ppi_frame(sheet, key, edits) for sheet in sheets]
    primary = compute_estimates(
        frames[0]["rows"], pred_by_model, edits, y_primary
    )

    sensitivity: dict[str, dict] = {}
    for i, (sheet, frame) in enumerate(zip(sheets[1:], frames[1:]), start=2):
        sensitivity[f"coder {i} ({sheet['coder']})"] = compute_estimates(
            frame["rows"], pred_by_model, edits, y_primary
        )
    if len(sheets) > 1:
        # Row-mean over ALL coders, on rows every coder coded (non-extra).
        by_edit_per_sheet = [
            {r["edit_id"]: r for r in frame["rows"]} for frame in frames
        ]
        common_ids = set(by_edit_per_sheet[0])
        for by_edit in by_edit_per_sheet[1:]:
            common_ids &= set(by_edit)
        common_rows = [
            by_edit_per_sheet[0][eid] for eid in sorted(common_ids)
        ]
        sensitivity["row-mean of coders"] = compute_estimates(
            common_rows,
            pred_by_model,
            edits,
            make_y_row_mean(by_edit_per_sheet),
        )

    return {
        "meta": {
            "generated_utc": datetime.datetime.now(
                datetime.timezone.utc
            ).isoformat(timespec="seconds"),
            "sheet_paths": [str(p) for p in sheet_paths],
            "blind_key": str(blind_key_path),
            "edits": str(edits_path),
            "predictor": str(predictor_path),
            "predictor_label": predictor_label,
            "primary_coder": sheets[0]["coder"],
            "frame": {
                "per_model_draw": frames[0]["per_model_draw"],
                "per_model_n": frames[0]["per_model_n"],
                "n_extra_excluded": frames[0]["n_extra_excluded"],
                "n_uncoded_excluded": frames[0]["n_uncoded_excluded"],
            },
            "predictor_join": join_diag,
            "dropped_no_predictor_code": primary["dropped_no_predictor_code"],
        },
        "primary": primary,
        "sensitivity": sensitivity,
    }


def main(argv: list[str] | None = None) -> dict:
    parser = argparse.ArgumentParser(
        description="C4 prediction-powered inference (BRIEF section 4)."
    )
    parser.add_argument(
        "--sheets", nargs="+", required=True,
        help="filled per-coder sheets; the FIRST is coder 1 (primary Y)",
    )
    parser.add_argument("--blind-key", required=True)
    parser.add_argument(
        "--predictor", required=True,
        help="the prediction f codes file (DECISIONS section 1: the "
        "Gemma-v2 codes)",
    )
    parser.add_argument("--predictor-label", default="gemma_v2")
    parser.add_argument("--edits", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument(
        "--json", default=None,
        help="machine-readable dump (default: recode/data/analysis/C_ppi.json)",
    )
    args = parser.parse_args(argv)

    analysis = run_analysis(
        [Path(p) for p in args.sheets],
        Path(args.blind_key),
        Path(args.predictor),
        Path(args.edits),
        predictor_label=args.predictor_label,
    )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(build_report(analysis), encoding="utf-8")

    json_path = Path(args.json) if args.json else DEFAULT_JSON_DIR / "C_ppi.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(analysis, handle, indent=2, default=str)
        handle.write("\n")

    n_models = len(analysis["primary"]["models"])
    print(
        f"Wrote {out_path} and {json_path} ({n_models} models, "
        f"{len(analysis['primary']['estimands'])} estimands, "
        f"{len(analysis['sensitivity'])} sensitivity run(s))"
    )
    return analysis


if __name__ == "__main__":
    main()
