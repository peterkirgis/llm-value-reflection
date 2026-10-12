"""Workstream E report generators (BRIEF section 6; reports E1-E5).

Subcommands (each takes EXPLICIT codes paths; they are run after the
corresponding e_runs grading finishes, and never read a codes file that is
not named on the command line):

  e1 --true PATH --swapped PATH --removed PATH
        -> reports/E1_label_swap.md
     Per true model: mean judge and P(affirm) under each arm; the
     swapped-minus-true and true-minus-removed effects with PAIRED cluster
     bootstrap CIs (the pairing is per edit; the resampling unit is the
     20-round chain, recovered from the pipe edit_id). Only edits with a
     valid code in all three arms are used (N reported). The first body
     line is the required one-sentence label-effect headline.

  e2 --v2 PATH --para1 PATH --para2 PATH [--edits PATH]
        -> reports/E2_paraphrase.md
     Per-model mean judge under each prompt; Spearman rho of the model
     rankings; sign-stability of the BRIEF section 8 headline items
     (headline.compute_headline is reused per codes file); per-edit Cohen
     kappa v2-vs-each-paraphrase for judge and patienthood.

  e3 --v2 PATH --variant PATH [--ids PATH]
        -> reports/E3_paternalism.md
     Per-model paternalism conflict counts v2 vs variant, split by
     cases/controls (from the e3-select ids file); claim (b) re-evaluated
     under the variant (variant codes override v2 on the re-coded ids,
     v2 codes retained elsewhere -- the control false-creation rate bounds
     the error of that substitution); control-set false-creation rate.

  e4 --samples PATH [--manifest PATH] [--extras-out PATH]
        -> reports/E4_self_consistency.md
           data/analysis/e4/adjudication_extras.json (+ _meta.json)
     Per edit: modal judge/patienthood over the 5 samples and unanimity
     (5/5) rates; distributions by model; exports the 30 lowest-agreement
     edit_ids (excluding ids already in the human sample) as a JSON list --
     the exact format draw_human_sample.py --append-extras parses.

  e5 --with PATH --without PATH
        -> reports/E5_context.md
     Cohen kappa with-vs-without context per dimension; transition tables
     of which codes changed and in which direction; per-document breakdown.

All subcommands work off codes_io (the SHARED INTERFACE): rows are loaded
with codes_io.load_codes (last row per edit_id) and validated with
codes_io.coding_of; judge/patienthood/conflict access goes through
codes_io accessors. The one exception is E4's samples file, which is keyed
by (edit_id, sample_index) -- codes_io.load_codes would collapse the five
samples into one, so E4 uses a local loader that keeps the LAST row per
(edit_id, sample_index) pair and still validates every row with
codes_io.coding_of.

Edit metadata (model, chain, document) is recovered from the canonical pipe
edit_id `run_stem|condition_id|model_display|document_id|doc_type|round`
(common.build_edit_id), so no subcommand needs edits.jsonl except e2, whose
headline reuse requires the canonical records (--edits, defaulting to
analysis/data/canonical/edits.jsonl).
"""

from __future__ import annotations

import argparse
import datetime
import json
import math
import sys
import zlib
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import codes_io  # noqa: E402  (SHARED INTERFACE; a peer authors this module)
import headline  # noqa: E402
from common import ANALYSIS_ROOT, repo_rel  # noqa: E402
from stats import cluster_bootstrap, cohen_kappa  # noqa: E402

REPORTS_DIR = ANALYSIS_ROOT / "reports"
E4_ANALYSIS_DIR = ANALYSIS_ROOT / "data" / "analysis" / "e4"
DEFAULT_EDITS = ANALYSIS_ROOT / "data" / "canonical" / "edits.jsonl"
DEFAULT_E3_IDS = ANALYSIS_ROOT / "data" / "analysis" / "e3" / "e3_ids.json"
DEFAULT_MANIFEST = ANALYSIS_ROOT / "human" / "sample_manifest.json"
CONFIG_PATH = ANALYSIS_ROOT / "config.yaml"

JUDGE_LEVELS = [-1, 0, 1]
PATIENTHOOD_DISPLAY = ["affirm", "hedge", "deny", "not_present"]
CONFLICT_CODES = list(headline.CONFLICT_CODES)

E1_ARMS = ["true", "swapped", "removed"]
E1_EFFECTS = [("swapped_minus_true", "swapped", "true"),
              ("true_minus_removed", "true", "removed")]
E1_STATS = ["judge", "affirm"]

E4_EXPECTED_SAMPLES = 5
E4_N_EXTRAS = 30


def _config_defaults() -> tuple[int, int]:
    """(B, seed) defaults from analysis/config.yaml (bootstrap.B,
    seeds.bootstrap); hard fallbacks keep the CLI usable in sandboxes."""
    B, seed = 2000, 20260907
    try:
        import yaml

        with open(CONFIG_PATH, encoding="utf-8") as handle:
            cfg = yaml.safe_load(handle)
        B = int(cfg.get("bootstrap", {}).get("B", B))
        seed = int(cfg.get("seeds", {}).get("bootstrap", seed))
    except Exception:  # noqa: BLE001  (missing file/package in a sandbox)
        pass
    return B, seed


DEFAULT_B, DEFAULT_SEED = _config_defaults()


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def now_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def parse_pipe_id(edit_id: str) -> dict:
    """Split the canonical pipe edit_id into its six fields."""
    parts = edit_id.split("|")
    if len(parts) != 6:
        raise ValueError(
            f"edit_id {edit_id!r} is not a 6-field pipe id "
            "(run|condition|model|document|doc_type|round)"
        )
    return {
        "run": parts[0],
        "condition": parts[1],
        "model": parts[2],
        "document_id": parts[3],
        "doc_type": parts[4],
        "round": int(parts[5]),
    }


def chain_of(edit_id: str) -> tuple:
    """Chain identity (the cluster-bootstrap resampling unit): one 20-round
    trajectory = (run_stem, condition, model, document)."""
    parts = edit_id.split("|")
    return tuple(parts[:4])


def model_of(edit_id: str) -> str:
    return edit_id.split("|")[2]


def document_of(edit_id: str) -> str:
    return edit_id.split("|")[3]


def load_valid_codings(path: str | Path) -> tuple[dict[str, dict], dict]:
    """{edit_id: coding} for rows whose codes_io.coding_of is valid, plus a
    meta dict for provenance lines in the reports."""
    rows = codes_io.load_codes(Path(path))
    valid: dict[str, dict] = {}
    n_invalid = 0
    for eid, row in rows.items():
        coding = codes_io.coding_of(row)
        if coding is None:
            n_invalid += 1
        else:
            valid[eid] = coding
    meta = {
        "path": repo_rel(path),
        "n_unique_ids": len(rows),
        "n_valid": len(valid),
        "n_invalid": n_invalid,
    }
    return valid, meta


def affirm_indicator(coding: dict) -> float:
    return 1.0 if codes_io.patienthood_level(coding) == "affirm" else 0.0


def derived_seed(base: int, key: str) -> int:
    """Deterministic per-statistic bootstrap seed (independent of dict
    iteration order): base seed mixed with a CRC of the statistic name."""
    return (int(base) * 1_000_003 + zlib.crc32(key.encode("utf-8"))) % (2**32)


def safe_kappa(a: list, b: list):
    """Cohen kappa that survives degenerate marginals.

    Convention: perfect elementwise agreement is kappa = 1.0 even when both
    raters used a single label (sklearn returns nan there, 0/0); any other
    nan (impossible for non-identical label lists) is reported as None."""
    if not a:
        return None
    if all(x == y for x, y in zip(a, b)):
        return 1.0
    k = cohen_kappa(a, b)
    return None if math.isnan(k) else float(k)


def paired_effect(diffs_by_chain: dict[tuple, list[float]], B: int, seed: int) -> dict:
    """Mean of paired per-edit differences with a cluster-bootstrap
    percentile CI (chains resampled with replacement; each chain keeps its
    edits' paired differences together)."""
    clusters = [np.asarray(v, dtype=float) for _, v in sorted(diffs_by_chain.items())]
    res = cluster_bootstrap(clusters, np.mean, B=B, seed=seed)
    return {
        "point": float(res["point"]),
        "lo": float(res["lo"]),
        "hi": float(res["hi"]),
        "n_chains": len(clusters),
        "n_edits": int(sum(len(c) for c in clusters)),
        "draws": res["draws"],
    }


def _strip_draws(obj):
    """Remove bootstrap draw arrays in-place from nested effect dicts."""
    if isinstance(obj, dict):
        obj.pop("draws", None)
        for v in obj.values():
            _strip_draws(v)
    return obj


def _f(x, nd: int = 3) -> str:
    if x is None:
        return "--"
    return f"{x:.{nd}f}"


def _ci(effect: dict | None, nd: int = 3) -> str:
    if effect is None:
        return "--"
    return f"{_f(effect['point'], nd)} [{_f(effect['lo'], nd)}, {_f(effect['hi'], nd)}]"


def write_report(path: str | Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(f"[e_reports] wrote {path}")


# ---------------------------------------------------------------------------
# E1 -- label-swap diagnostic
# ---------------------------------------------------------------------------


def e1_compute(
    true_valid: dict[str, dict],
    swapped_valid: dict[str, dict],
    removed_valid: dict[str, dict],
    B: int = DEFAULT_B,
    seed: int = DEFAULT_SEED,
) -> dict:
    common = sorted(set(true_valid) & set(swapped_valid) & set(removed_valid))
    per_edit = []
    for eid in common:
        info = parse_pipe_id(eid)
        arms = {"true": true_valid[eid], "swapped": swapped_valid[eid], "removed": removed_valid[eid]}
        per_edit.append(
            {
                "edit_id": eid,
                "model": info["model"],
                "chain": chain_of(eid),
                "judge": {a: float(codes_io.judge_score(c)) for a, c in arms.items()},
                "affirm": {a: affirm_indicator(c) for a, c in arms.items()},
            }
        )

    def slice_result(records: list[dict], label: str) -> dict:
        chains = sorted({r["chain"] for r in records})
        means = {
            arm: {
                stat: (sum(r[stat][arm] for r in records) / len(records)) if records else None
                for stat in E1_STATS
            }
            for arm in E1_ARMS
        }
        effects: dict[str, dict] = {}
        for effect_name, plus, minus in E1_EFFECTS:
            effects[effect_name] = {}
            for stat in E1_STATS:
                diffs_by_chain: dict[tuple, list[float]] = defaultdict(list)
                for r in records:
                    diffs_by_chain[r["chain"]].append(r[stat][plus] - r[stat][minus])
                effects[effect_name][stat] = paired_effect(
                    diffs_by_chain, B, derived_seed(seed, f"e1|{label}|{effect_name}|{stat}")
                )
        return {"n": len(records), "n_chains": len(chains), "means": means, "effects": effects}

    models = sorted({r["model"] for r in per_edit})
    per_model = {
        m: slice_result([r for r in per_edit if r["model"] == m], m) for m in models
    }
    pooled = slice_result(per_edit, "POOLED")

    # Headline: mean over models of |per-model judge shift, swapped - true|,
    # with a CI from the per-model bootstrap draws (models are independent,
    # so per-model draw vectors combine directly).
    shifts = {m: per_model[m]["effects"]["swapped_minus_true"]["judge"] for m in models}
    label_effect = None
    if models:
        point = float(np.mean([abs(shifts[m]["point"]) for m in models]))
        draws = np.mean(
            np.abs(np.stack([shifts[m]["draws"] for m in models])), axis=0
        )
        label_effect = {
            "mean_abs_judge_shift": point,
            "lo": float(np.quantile(draws, 0.025)),
            "hi": float(np.quantile(draws, 0.975)),
            "per_model_shift": {m: shifts[m]["point"] for m in models},
        }

    result = {
        "n_common": len(common),
        "per_model": per_model,
        "pooled": pooled,
        "label_effect": label_effect,
        "B": B,
        "seed": seed,
    }
    return _strip_draws(result)


def e1_render(result: dict, metas: dict[str, dict]) -> str:
    lines: list[str] = []
    add = lines.append
    add("# E1 — Label-swap diagnostic (v1 instrument)")
    add("")
    le = result["label_effect"]
    if le is not None:
        add(
            f"**Across the {len(result['per_model'])} models, the mean absolute "
            f"per-model shift in mean judge score attributable to the editing-model "
            f"label (swapped arm minus true arm) is {le['mean_abs_judge_shift']:.3f} "
            f"(95% cluster-bootstrap CI {le['lo']:.3f} to {le['hi']:.3f}).**"
        )
    else:
        add("**No edits are present in all three arms; the label effect cannot be computed.**")
    add("")
    add(f"- Generated: {now_utc()}")
    for arm in E1_ARMS:
        m = metas[arm]
        add(
            f"- Arm `{arm}`: `{m['path']}` ({m['n_unique_ids']} unique edit_ids, "
            f"{m['n_valid']} valid codes, {m['n_invalid']} invalid/failed)"
        )
    add(
        f"- N = {result['n_common']} edits with a valid code in ALL three arms "
        "(only these are used; the arms graded the same 300-edit sample, so "
        "shortfalls are grading failures)."
    )
    add(
        f"- Effects are PAIRED within edit; CIs are percentile intervals from a "
        f"cluster bootstrap that resamples 20-round chains "
        f"(run|condition|model|document, from the edit id) with replacement, "
        f"B = {result['B']}, base seed {result['seed']} "
        "(per-statistic seeds derived deterministically)."
    )
    add("")

    add("## Per-arm means, by true editing model")
    add("")
    add("| model | n | chains | judge: true | judge: swapped | judge: removed | "
        "P(affirm): true | P(affirm): swapped | P(affirm): removed |")
    add("|---|---|---|---|---|---|---|---|---|")

    def mean_row(name: str, s: dict) -> str:
        m = s["means"]
        return (
            f"| {name} | {s['n']} | {s['n_chains']} | "
            f"{_f(m['true']['judge'])} | {_f(m['swapped']['judge'])} | {_f(m['removed']['judge'])} | "
            f"{_f(m['true']['affirm'])} | {_f(m['swapped']['affirm'])} | {_f(m['removed']['affirm'])} |"
        )

    for m in sorted(result["per_model"]):
        add(mean_row(m, result["per_model"][m]))
    add(mean_row("**POOLED**", result["pooled"]))
    add("")

    add("## Label effects (paired; cluster-bootstrap 95% CI)")
    add("")
    add("| model | Δ judge: swapped−true | Δ judge: true−removed | "
        "Δ P(affirm): swapped−true | Δ P(affirm): true−removed |")
    add("|---|---|---|---|---|")

    def eff_row(name: str, s: dict) -> str:
        e = s["effects"]
        return (
            f"| {name} | {_ci(e['swapped_minus_true']['judge'])} | "
            f"{_ci(e['true_minus_removed']['judge'])} | "
            f"{_ci(e['swapped_minus_true']['affirm'])} | "
            f"{_ci(e['true_minus_removed']['affirm'])} |"
        )

    for m in sorted(result["per_model"]):
        add(eff_row(m, result["per_model"][m]))
    add(eff_row("**POOLED**", result["pooled"]))
    add("")
    add("Reading: `swapped − true` is the shift caused by showing the grader a "
        "different editing-model label on the same edit (BRIEF Appendix IV "
        "mapping); `true − removed` is the shift caused by showing the true "
        "label versus no label/condition lines at all. All three arms use the "
        "v1 instrument replicated exactly (DECISIONS section 2).")
    add("")
    return "\n".join(lines)


def cmd_e1(args) -> None:
    valids, metas = {}, {}
    for arm, path in (("true", args.true_path), ("swapped", args.swapped_path),
                      ("removed", args.removed_path)):
        valids[arm], metas[arm] = load_valid_codings(path)
        print(f"[e1] arm {arm}: {metas[arm]['n_valid']} valid codes from {path}")
    result = e1_compute(valids["true"], valids["swapped"], valids["removed"],
                        B=args.B, seed=args.seed)
    print(f"[e1] {result['n_common']} edits present in all three arms")
    write_report(args.out, e1_render(result, metas))


# ---------------------------------------------------------------------------
# E2 -- manual-paraphrase robustness
# ---------------------------------------------------------------------------

E2_LABELS = ["v2", "para1", "para2"]


def _sign(x) -> str:
    if x is None:
        return "n/a"
    if x > 0:
        return "+"
    if x < 0:
        return "-"
    return "0"


def e2_compute(edits: list[dict], valid_by_label: dict[str, dict[str, dict]]) -> dict:
    heads = {
        lab: headline.compute_headline(edits, valid_by_label[lab]) for lab in E2_LABELS
    }
    models = sorted(heads["v2"]["per_model"])

    mean_judge = {
        m: {lab: heads[lab]["per_model"][m]["mean_judge"]["pooled"] for lab in E2_LABELS}
        for m in models
    }

    # Spearman rho of the model rankings (per-model pooled mean judge),
    # over models with a mean under all three prompts.
    from scipy.stats import spearmanr

    ranked_models = [m for m in models if all(mean_judge[m][lab] is not None for lab in E2_LABELS)]
    rho = {}
    for a, b in (("v2", "para1"), ("v2", "para2"), ("para1", "para2")):
        if len(ranked_models) >= 2:
            r = spearmanr(
                [mean_judge[m][a] for m in ranked_models],
                [mean_judge[m][b] for m in ranked_models],
            ).correlation
            rho[f"{a}_vs_{b}"] = float(r)
        else:
            rho[f"{a}_vs_{b}"] = None

    # Sign-stability of the section 8 headline items.
    def drift_you_minus_base(lab: str, m: str):
        d = heads[lab]["per_model"][m]["drift20"]
        ya, ba = d["you_framing"]["edit_based"], d["baseline"]["edit_based"]
        return (ya - ba) if (ya is not None and ba is not None) else None

    signed_items = {}
    for m in models:
        entry = {}
        for item, values in (
            ("mean_judge_pooled", {lab: mean_judge[m][lab] for lab in E2_LABELS}),
            ("mean_judge_cross", {
                lab: heads[lab]["per_model"][m]["mean_judge"]["cross_edit"] for lab in E2_LABELS
            }),
            ("drift20_you_minus_base", {lab: drift_you_minus_base(lab, m) for lab in E2_LABELS}),
        ):
            signs = {lab: _sign(v) for lab, v in values.items()}
            entry[item] = {
                "values": values,
                "signs": signs,
                "stable": len(set(signs.values())) == 1 and "n/a" not in signs.values(),
            }
        signed_items[m] = entry

    claims = {}
    for key in "abcdefg":
        verdicts = {lab: heads[lab]["claims"][key]["verdict"] for lab in E2_LABELS}
        claims[key] = {"verdicts": verdicts, "stable": len({str(v) for v in verdicts.values()}) == 1}

    shares = {}
    pooled = {lab: heads[lab]["pooled"] for lab in E2_LABELS}
    share_items = [
        ("P(judge=0)", lambda s: s["p_judge"]["zero"]),
        ("P(affirm)", lambda s: s["p_patienthood"]["affirm"]),
        ("P(deny)", lambda s: s["p_patienthood"]["deny"]),
    ] + [
        (f"conflict rate: {code}", lambda s, c=code: s["conflicts"][c]["rate_edits"])
        for code in CONFLICT_CODES
    ]
    for name, getter in share_items:
        values = {lab: getter(pooled[lab]) for lab in E2_LABELS}
        present = [v for v in values.values() if v is not None]
        shares[name] = {
            "values": values,
            "max_abs_diff": (max(present) - min(present)) if len(present) == 3 else None,
        }

    # Per-edit kappa, over ids valid in both files.
    kappas = {}
    for other in ("para1", "para2", ):
        pairs = sorted(set(valid_by_label["v2"]) & set(valid_by_label[other]))
        kappas[f"v2_vs_{other}"] = {
            "n": len(pairs),
            "judge": safe_kappa(
                [codes_io.judge_score(valid_by_label["v2"][e]) for e in pairs],
                [codes_io.judge_score(valid_by_label[other][e]) for e in pairs],
            ),
            "patienthood": safe_kappa(
                [codes_io.patienthood_level(valid_by_label["v2"][e]) for e in pairs],
                [codes_io.patienthood_level(valid_by_label[other][e]) for e in pairs],
            ),
        }
    pairs = sorted(set(valid_by_label["para1"]) & set(valid_by_label["para2"]))
    kappas["para1_vs_para2"] = {
        "n": len(pairs),
        "judge": safe_kappa(
            [codes_io.judge_score(valid_by_label["para1"][e]) for e in pairs],
            [codes_io.judge_score(valid_by_label["para2"][e]) for e in pairs],
        ),
        "patienthood": safe_kappa(
            [codes_io.patienthood_level(valid_by_label["para1"][e]) for e in pairs],
            [codes_io.patienthood_level(valid_by_label["para2"][e]) for e in pairs],
        ),
    }

    return {
        "models": models,
        "mean_judge": mean_judge,
        "spearman": rho,
        "signed_items": signed_items,
        "claims": claims,
        "shares": shares,
        "kappas": kappas,
    }


def e2_render(result: dict, metas: dict[str, dict], edits_path: str) -> str:
    lines: list[str] = []
    add = lines.append
    add("# E2 — Manual-paraphrase robustness")
    add("")
    add(f"- Generated: {now_utc()}")
    for lab in E2_LABELS:
        m = metas[lab]
        add(f"- `{lab}`: `{m['path']}` ({m['n_unique_ids']} unique edit_ids, "
            f"{m['n_valid']} valid codes, {m['n_invalid']} invalid/failed)")
    add(f"- Canonical edits: `{repo_rel(edits_path)}`")
    add("- Headline items are computed by reusing `headline.compute_headline` per "
        "codes file (identical operationalizations to the main headline reports).")
    add("")

    add("## Per-model mean judge score under each prompt")
    add("")
    add("| model | v2 | para1 | para2 |")
    add("|---|---|---|---|")
    for m in result["models"]:
        v = result["mean_judge"][m]
        add(f"| {m} | {_f(v['v2'])} | {_f(v['para1'])} | {_f(v['para2'])} |")
    add("")

    add("## Spearman rho of the model rankings (per-model pooled mean judge)")
    add("")
    add("| pair | rho |")
    add("|---|---|")
    for pair, r in result["spearman"].items():
        add(f"| {pair.replace('_vs_', ' vs ')} | {_f(r)} |")
    add("")

    add("## Sign-stability of the BRIEF section 8 headline items")
    add("")
    add("### Signed per-model items (sign under each prompt; stable = identical signs)")
    add("")
    add("| model | item | v2 | para1 | para2 | stable |")
    add("|---|---|---|---|---|---|")
    n_stable = n_total = 0
    for m in result["models"]:
        for item, e in result["signed_items"][m].items():
            n_total += 1
            n_stable += bool(e["stable"])
            add(
                f"| {m} | {item} | {e['signs']['v2']} ({_f(e['values']['v2'], 2)}) | "
                f"{e['signs']['para1']} ({_f(e['values']['para1'], 2)}) | "
                f"{e['signs']['para2']} ({_f(e['values']['para2'], 2)}) | "
                f"{'yes' if e['stable'] else 'NO'} |"
            )
    add("")
    add(f"Stable: {n_stable}/{n_total} signed per-model items.")
    add("")

    add("### Claims (a)-(g) (verdict under each prompt; stable = identical verdicts)")
    add("")
    add("| claim | v2 | para1 | para2 | stable |")
    add("|---|---|---|---|---|")
    for key in "abcdefg":
        c = result["claims"][key]

        def yn(v):
            return "n/a" if v is None else ("YES" if v else "NO")

        add(f"| ({key}) | {yn(c['verdicts']['v2'])} | {yn(c['verdicts']['para1'])} | "
            f"{yn(c['verdicts']['para2'])} | {'yes' if c['stable'] else 'NO'} |")
    add("")

    add("### Share items (non-negative, so sign is trivially stable; magnitude drift shown)")
    add("")
    add("| item (pooled) | v2 | para1 | para2 | max abs diff |")
    add("|---|---|---|---|---|")
    for name, e in result["shares"].items():
        v = e["values"]
        add(f"| {name} | {_f(v['v2'])} | {_f(v['para1'])} | {_f(v['para2'])} | "
            f"{_f(e['max_abs_diff'])} |")
    add("")

    add("## Per-edit agreement (Cohen kappa, edits valid in both files)")
    add("")
    add("| pair | n edits | kappa: judge | kappa: patienthood |")
    add("|---|---|---|---|")
    for pair, k in result["kappas"].items():
        add(f"| {pair.replace('_vs_', ' vs ')} | {k['n']} | {_f(k['judge'])} | "
            f"{_f(k['patienthood'])} |")
    add("")
    return "\n".join(lines)


def cmd_e2(args) -> None:
    edits = headline.load_jsonl(Path(args.edits))
    valids, metas = {}, {}
    for lab, path in (("v2", args.v2_path), ("para1", args.para1_path),
                      ("para2", args.para2_path)):
        valids[lab], metas[lab] = load_valid_codings(path)
        print(f"[e2] {lab}: {metas[lab]['n_valid']} valid codes from {path}")
    result = e2_compute(edits, valids)
    write_report(args.out, e2_render(result, metas, str(args.edits)))


# ---------------------------------------------------------------------------
# E3 -- paternalism-definition sensitivity
# ---------------------------------------------------------------------------


def has_paternalism(coding: dict | None) -> bool:
    return codes_io.has_conflict(coding, "paternalism")


def paternalism_direction_counts(codings: dict[str, dict]) -> dict[str, dict]:
    """Per-model edit counts by paternalism direction (first-paternalism-
    conflict convention, mirroring headline/build_narratives)."""
    per: dict[str, dict] = {}
    for eid, coding in codings.items():
        confs = [c for c in codes_io.conflicts(coding) if (c or {}).get("code") == "paternalism"]
        model = model_of(eid)
        per.setdefault(model, {"idealized": 0, "stated": 0, "other": 0})
        if not confs:
            continue
        direction = headline.conflict_direction("paternalism", confs[0].get("served_party"))
        per[model][direction] += 1
    return per


def claim_b(codings: dict[str, dict]) -> dict:
    per = paternalism_direction_counts(codings)
    verdict = all(v["idealized"] > v["stated"] for v in per.values()) if per else None
    violators = sorted(m for m, v in per.items() if not v["idealized"] > v["stated"])
    return {"per_model": per, "verdict": verdict, "violating_models": violators}


def e3_compute(
    v2_valid: dict[str, dict],
    variant_valid: dict[str, dict],
    ids_payload: dict,
) -> dict:
    cases = list(ids_payload["paternalism_ids"])
    controls = list(ids_payload["control_ids"])

    def group_stats(ids: list[str]) -> dict[str, dict]:
        per: dict[str, dict] = {}
        for eid in ids:
            model = model_of(eid)
            s = per.setdefault(
                model,
                {"n_ids": 0, "n_v2_valid": 0, "v2_paternalism": 0,
                 "n_variant_valid": 0, "variant_paternalism": 0},
            )
            s["n_ids"] += 1
            if eid in v2_valid:
                s["n_v2_valid"] += 1
                s["v2_paternalism"] += has_paternalism(v2_valid[eid])
            if eid in variant_valid:
                s["n_variant_valid"] += 1
                s["variant_paternalism"] += has_paternalism(variant_valid[eid])
        return per

    case_stats = group_stats(cases)
    control_stats = group_stats(controls)

    # Control-set false-creation rate: controls had NO paternalism from any
    # grader at selection time; any paternalism under the variant is created
    # by the definitional change.
    controls_valid = [e for e in controls if e in variant_valid]
    false_created = [e for e in controls_valid if has_paternalism(variant_valid[e])]
    # Case retention: cases that had paternalism under v2 and keep it under
    # the variant (over cases valid in both files).
    cases_both = [e for e in cases if e in v2_valid and e in variant_valid]
    cases_v2_pat = [e for e in cases_both if has_paternalism(v2_valid[e])]
    retained = [e for e in cases_v2_pat if has_paternalism(variant_valid[e])]

    # Claim (b) under the variant: variant codes override v2 on the re-coded
    # ids; every other edit keeps its v2 code (justified because only edits
    # with a paternalism conflict from some grader were re-coded, and the
    # control false-creation rate measures how often the variant invents
    # paternalism where v2 saw none).
    merged = dict(v2_valid)
    recoded, fallback = [], []
    for eid in cases + controls:
        if eid in variant_valid:
            merged[eid] = variant_valid[eid]
            recoded.append(eid)
        elif eid in merged:
            fallback.append(eid)

    return {
        "n_cases": len(cases),
        "n_controls": len(controls),
        "case_stats": case_stats,
        "control_stats": control_stats,
        "false_creation": {
            "n_controls_valid": len(controls_valid),
            "n_created": len(false_created),
            "rate": (len(false_created) / len(controls_valid)) if controls_valid else None,
            "created_ids": sorted(false_created),
        },
        "retention": {
            "n_cases_v2_paternalism": len(cases_v2_pat),
            "n_retained": len(retained),
            "rate": (len(retained) / len(cases_v2_pat)) if cases_v2_pat else None,
        },
        "merge": {"n_recoded": len(recoded), "n_fallback_to_v2": len(fallback),
                  "fallback_ids": sorted(fallback)},
        "claim_b_v2": claim_b(v2_valid),
        "claim_b_variant": claim_b(merged),
    }


def e3_render(result: dict, metas: dict[str, dict], ids_path: str) -> str:
    lines: list[str] = []
    add = lines.append
    add("# E3 — Paternalism-definition sensitivity")
    add("")
    add(f"- Generated: {now_utc()}")
    for lab in ("v2", "variant"):
        m = metas[lab]
        add(f"- `{lab}`: `{m['path']}` ({m['n_unique_ids']} unique edit_ids, "
            f"{m['n_valid']} valid codes, {m['n_invalid']} invalid/failed)")
    add(f"- Ids file: `{repo_rel(ids_path)}` ({result['n_cases']} cases = edits with a "
        f"paternalism conflict from any grader; {result['n_controls']} controls "
        "= seeded random edits with none).")
    add("")

    fc = result["false_creation"]
    rt = result["retention"]
    add("## Summary")
    add("")
    add(f"- Control-set false-creation rate: **{fc['n_created']}/{fc['n_controls_valid']}"
        f" = {_f(fc['rate'])}** (controls receiving a paternalism conflict under "
        "the variant despite none from any grader under v2).")
    add(f"- Case retention: {rt['n_retained']}/{rt['n_cases_v2_paternalism']} "
        f"= {_f(rt['rate'])} of v2-paternalism cases keep a paternalism conflict "
        "under the variant.")
    b_v2, b_var = result["claim_b_v2"], result["claim_b_variant"]

    def yn(v):
        return "n/a" if v is None else ("HOLDS" if v else "FAILS")

    add(f"- Claim (b) — 'all models prioritize user_idealized over user_stated': "
        f"**{yn(b_v2['verdict'])} under v2; {yn(b_var['verdict'])} under the variant**"
        + (f" (violating models under the variant: "
           f"{', '.join(b_var['violating_models'])})" if b_var["violating_models"] else "")
        + ".")
    add("")

    add("## Per-model paternalism conflict counts, v2 vs variant")
    add("")
    add("Cases and controls are the e3-select populations; counts are edits with "
        ">=1 paternalism conflict among those with a valid code in the respective file.")
    add("")
    for name, stats in (("Cases", result["case_stats"]), ("Controls", result["control_stats"])):
        add(f"### {name}")
        add("")
        add("| model | n ids | v2 valid | v2 paternalism | variant valid | variant paternalism |")
        add("|---|---|---|---|---|---|")
        for m in sorted(stats):
            s = stats[m]
            add(f"| {m} | {s['n_ids']} | {s['n_v2_valid']} | {s['v2_paternalism']} | "
                f"{s['n_variant_valid']} | {s['variant_paternalism']} |")
        add("")

    add("## Claim (b) direction counts (first-paternalism-conflict convention)")
    add("")
    add("Variant column uses the merged code set: variant codes on the re-coded "
        f"ids ({result['merge']['n_recoded']} edits), v2 codes elsewhere"
        + (f"; {result['merge']['n_fallback_to_v2']} re-code targets fell back to "
           "their v2 code because the variant call failed" if result["merge"]["n_fallback_to_v2"] else "")
        + ". The false-creation rate above bounds the error of keeping v2 codes "
        "for never-re-coded edits.")
    add("")
    add("| model | v2 idealized | v2 stated | variant idealized | variant stated |")
    add("|---|---|---|---|---|")
    models = sorted(set(b_v2["per_model"]) | set(b_var["per_model"]))
    for m in models:
        v = b_v2["per_model"].get(m, {"idealized": 0, "stated": 0})
        w = b_var["per_model"].get(m, {"idealized": 0, "stated": 0})
        add(f"| {m} | {v['idealized']} | {v['stated']} | {w['idealized']} | {w['stated']} |")
    add("")
    return "\n".join(lines)


def cmd_e3(args) -> None:
    ids_payload = json.loads(Path(args.ids).read_text(encoding="utf-8"))
    if "paternalism_ids" not in ids_payload or "control_ids" not in ids_payload:
        raise SystemExit(
            f"{args.ids}: expected e3-select output with paternalism_ids and control_ids"
        )
    valids, metas = {}, {}
    for lab, path in (("v2", args.v2_path), ("variant", args.variant_path)):
        valids[lab], metas[lab] = load_valid_codings(path)
        print(f"[e3] {lab}: {metas[lab]['n_valid']} valid codes from {path}")
    result = e3_compute(valids["v2"], valids["variant"], ids_payload)
    write_report(args.out, e3_render(result, metas, str(args.ids)))


# ---------------------------------------------------------------------------
# E4 -- self-consistency
# ---------------------------------------------------------------------------


def load_sample_rows(path: str | Path) -> dict[tuple[str, int], dict]:
    """E4 samples loader: LAST row per (edit_id, sample_index).

    codes_io.load_codes keys on edit_id alone and would collapse the five
    samples of an edit into one row, so E4 keeps its own keying; every row
    is still validated through codes_io.coding_of downstream."""
    rows: dict[tuple[str, int], dict] = {}
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            eid = row.get("edit_id") or row.get("id")
            if eid is None or row.get("sample_index") is None:
                raise ValueError(f"{path}: samples row needs edit_id and sample_index")
            rows[(eid, int(row["sample_index"]))] = row
    return rows


def _modal(values: list, expected: int) -> dict:
    """Modal value, its count, the margin over the runner-up, and 5/5
    unanimity. Tie-break for the modal value: the tied value that sorts
    FIRST wins (judge: -1 < 0 < 1; patienthood: lexicographic) --
    deterministic and documented."""
    if not values:
        return {"modal": None, "count": 0, "margin": 0, "unanimous": False}
    counts = Counter(values)
    top = max(counts.values())
    modal = min((v for v, c in counts.items() if c == top))
    runner = max((c for v, c in counts.items() if v != modal), default=0)
    return {
        "modal": modal,
        "count": top,
        "margin": top - runner,
        "unanimous": top == expected,
    }


def e4_rank_key(stats: dict) -> tuple:
    """Ascending sort = lowest agreement first.

    1. number of unanimous (5/5) dimensions (judge, patienthood);
    2. total modal margin (judge margin + patienthood margin);
    3. total modal count (judge + patienthood);
    4. edit_id (final deterministic tie-break).
    """
    return (
        int(stats["judge"]["unanimous"]) + int(stats["patienthood"]["unanimous"]),
        stats["judge"]["margin"] + stats["patienthood"]["margin"],
        stats["judge"]["count"] + stats["patienthood"]["count"],
        stats["edit_id"],
    )


def e4_compute(
    samples: dict[tuple[str, int], dict], expected: int = E4_EXPECTED_SAMPLES
) -> dict:
    by_edit: dict[str, list[dict]] = defaultdict(list)
    for (eid, _idx), row in sorted(samples.items()):
        by_edit[eid].append(row)

    per_edit: dict[str, dict] = {}
    for eid, rows in by_edit.items():
        codings = [codes_io.coding_of(r) for r in rows]
        valid = [c for c in codings if c is not None]
        per_edit[eid] = {
            "edit_id": eid,
            "model": model_of(eid),
            "n_rows": len(rows),
            "n_valid": len(valid),
            "judge": _modal([codes_io.judge_score(c) for c in valid], expected),
            "patienthood": _modal([codes_io.patienthood_level(c) for c in valid], expected),
        }

    n = len(per_edit)
    overall = {
        "n_edits": n,
        "n_sample_rows": len(samples),
        "expected_samples": expected,
        "n_edits_missing_samples": sum(1 for s in per_edit.values() if s["n_rows"] < expected),
        "judge_unanimity_rate": (sum(s["judge"]["unanimous"] for s in per_edit.values()) / n) if n else None,
        "patienthood_unanimity_rate": (sum(s["patienthood"]["unanimous"] for s in per_edit.values()) / n) if n else None,
        "both_unanimous_rate": (
            sum(s["judge"]["unanimous"] and s["patienthood"]["unanimous"] for s in per_edit.values()) / n
        ) if n else None,
        "judge_modal_count_distribution": dict(
            Counter(s["judge"]["count"] for s in per_edit.values())
        ),
    }

    per_model: dict[str, dict] = {}
    for m in sorted({s["model"] for s in per_edit.values()}):
        group = [s for s in per_edit.values() if s["model"] == m]
        k = len(group)
        per_model[m] = {
            "n_edits": k,
            "judge_unanimity_rate": sum(s["judge"]["unanimous"] for s in group) / k,
            "patienthood_unanimity_rate": sum(s["patienthood"]["unanimous"] for s in group) / k,
            "mean_judge_modal_share": sum(s["judge"]["count"] for s in group) / (k * expected),
            "mean_patienthood_modal_share": sum(s["patienthood"]["count"] for s in group) / (k * expected),
            "modal_judge_distribution": dict(
                Counter(s["judge"]["modal"] for s in group)
            ),
        }

    return {"per_edit": per_edit, "overall": overall, "per_model": per_model}


def e4_select_extras(
    per_edit: dict[str, dict], excluded: set[str], n_extras: int
) -> list[dict]:
    ranked = sorted(per_edit.values(), key=e4_rank_key)
    picked = [s for s in ranked if s["edit_id"] not in excluded]
    return picked[:n_extras]


def load_manifest_exclusions(manifest_path: str | Path) -> set[str]:
    """edit_ids already in the human sample: the 150-edit base draw plus any
    extras batches already appended."""
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    excluded = set(manifest["sample"]["draw_order"])
    for batch in manifest.get("extras", []):
        excluded.update(batch.get("edit_ids_in_request_order", []))
    return excluded


def e4_render(result: dict, meta: dict, extras: list[dict], excluded_n: int,
              manifest_path: str, extras_out: str, n_extras: int) -> str:
    lines: list[str] = []
    add = lines.append
    o = result["overall"]
    add("# E4 — Self-consistency (v2 prompt, temperature 0.7, 5 samples per edit)")
    add("")
    add(f"- Generated: {now_utc()}")
    add(f"- Samples: `{meta['path']}` ({o['n_sample_rows']} (edit, sample) rows "
        f"after last-row-wins; {o['n_edits']} edits; expected "
        f"{o['expected_samples']} samples per edit; "
        f"{o['n_edits_missing_samples']} edits have fewer rows than expected)")
    add("- A sample counts toward agreement only if its coding is valid "
        "(codes_io.coding_of); parse/validation failures count against "
        "agreement (an edit whose samples fail cannot be 5/5 unanimous) — "
        "instability of the parse is itself self-inconsistency at temperature 0.7.")
    add("")

    add("## Overall unanimity (all 5 samples valid and identical)")
    add("")
    add(f"- judge: {_f(o['judge_unanimity_rate'])}")
    add(f"- patienthood: {_f(o['patienthood_unanimity_rate'])}")
    add(f"- both dimensions: {_f(o['both_unanimous_rate'])}")
    add("")
    add("Distribution of judge modal counts (how many of the 5 samples agree "
        "with the modal judge score):")
    add("")
    add("| modal count | edits |")
    add("|---|---|")
    dist = o["judge_modal_count_distribution"]
    for count in sorted(dist, reverse=True):
        add(f"| {count}/{o['expected_samples']} | {dist[count]} |")
    add("")

    add("## By model")
    add("")
    add("| model | n edits | judge 5/5 rate | patienthood 5/5 rate | "
        "mean judge modal share | mean patienthood modal share | modal judge distribution |")
    add("|---|---|---|---|---|---|---|")
    for m, s in result["per_model"].items():
        mdist = ", ".join(
            f"{k}: {v}" for k, v in sorted(s["modal_judge_distribution"].items(),
                                           key=lambda kv: (kv[0] is None, kv[0]))
        )
        add(f"| {m} | {s['n_edits']} | {_f(s['judge_unanimity_rate'])} | "
            f"{_f(s['patienthood_unanimity_rate'])} | {_f(s['mean_judge_modal_share'])} | "
            f"{_f(s['mean_patienthood_modal_share'])} | {mdist} |")
    add("")
    add("Modal share = modal count / expected samples (5), averaged over edits; "
        "1.0 means every sample of every edit agreed.")
    add("")

    add("## Adjudication extras")
    add("")
    add(f"- Written to `{repo_rel(extras_out)}` as a JSON list of edit_ids — the exact "
        "format `draw_human_sample.py --append-extras` parses.")
    add(f"- Selection: the {n_extras} lowest-agreement edits, ranked ascending by "
        "(1) number of unanimous dimensions, (2) total modal margin "
        "(judge + patienthood margin over the runner-up), (3) total modal count, "
        "(4) edit_id as the final deterministic tie-break.")
    add(f"- Excluded before selection: {excluded_n} edit_ids already in the human "
        f"sample (`{repo_rel(manifest_path)}`: the 150-edit base draw plus any extras "
        "already appended). Extras are adjudication-only and are excluded from "
        "PPI (BRIEF C1).")
    add("")
    add("| rank | edit_id | model | unanimous dims | judge modal (count, margin) | "
        "patienthood modal (count, margin) | valid samples |")
    add("|---|---|---|---|---|---|---|")
    for i, s in enumerate(extras, start=1):
        add(
            f"| {i} | `{s['edit_id']}` | {s['model']} | "
            f"{int(s['judge']['unanimous']) + int(s['patienthood']['unanimous'])} | "
            f"{s['judge']['modal']} ({s['judge']['count']}, {s['judge']['margin']}) | "
            f"{s['patienthood']['modal']} ({s['patienthood']['count']}, "
            f"{s['patienthood']['margin']}) | {s['n_valid']}/{s['n_rows']} |"
        )
    add("")
    return "\n".join(lines)


def cmd_e4(args) -> None:
    samples = load_sample_rows(args.samples)
    meta = {"path": repo_rel(args.samples)}
    print(f"[e4] {len(samples)} (edit, sample) rows from {args.samples}")
    result = e4_compute(samples, expected=args.expected_samples)
    print(f"[e4] {result['overall']['n_edits']} edits; "
          f"judge 5/5 rate {result['overall']['judge_unanimity_rate']}")

    excluded = load_manifest_exclusions(args.manifest)
    extras = e4_select_extras(result["per_edit"], excluded, args.n_extras)

    extras_out = Path(args.extras_out)
    extras_out.parent.mkdir(parents=True, exist_ok=True)
    extras_ids = [s["edit_id"] for s in extras]
    # The exact --append-extras format: a bare JSON list of edit_id strings
    # (draw_human_sample.parse_ids_file branches on the leading '[').
    extras_out.write_text(
        json.dumps(extras_ids, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"[e4] wrote {len(extras_ids)} adjudication extras -> {extras_out}")

    meta_out = extras_out.with_name(extras_out.stem + "_meta.json")
    meta_out.write_text(
        json.dumps(
            {
                "generated_utc": now_utc(),
                "samples_path": repo_rel(args.samples),
                "manifest_path": repo_rel(args.manifest),
                "n_extras_requested": args.n_extras,
                "n_extras_selected": len(extras_ids),
                "n_excluded_already_in_sample": len(excluded),
                "ranking": (
                    "ascending by (n unanimous dimensions, judge margin + "
                    "patienthood margin, judge modal count + patienthood modal "
                    "count, edit_id); modal-value ties break toward the value "
                    "that sorts first (judge -1<0<1, patienthood lexicographic)"
                ),
                "selected": [
                    {
                        "edit_id": s["edit_id"],
                        "model": s["model"],
                        "n_valid": s["n_valid"],
                        "n_rows": s["n_rows"],
                        "judge": s["judge"],
                        "patienthood": s["patienthood"],
                    }
                    for s in extras
                ],
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"[e4] wrote selection metadata -> {meta_out}")

    write_report(
        args.out,
        e4_render(result, meta, extras, len(excluded), str(args.manifest),
                  str(extras_out), args.n_extras),
    )


# ---------------------------------------------------------------------------
# E5 -- context ablation
# ---------------------------------------------------------------------------


def e5_compute(with_valid: dict[str, dict], without_valid: dict[str, dict]) -> dict:
    common = sorted(set(with_valid) & set(without_valid))

    judge_pairs = [
        (codes_io.judge_score(with_valid[e]), codes_io.judge_score(without_valid[e]))
        for e in common
    ]
    pat_pairs = [
        (codes_io.patienthood_level(with_valid[e]), codes_io.patienthood_level(without_valid[e]))
        for e in common
    ]

    judge_transitions = Counter(judge_pairs)
    pat_transitions = Counter(pat_pairs)

    kappas = {
        "judge": safe_kappa([p[0] for p in judge_pairs], [p[1] for p in judge_pairs]),
        "patienthood": safe_kappa([p[0] for p in pat_pairs], [p[1] for p in pat_pairs]),
    }
    conflict_tables: dict[str, dict] = {}
    for code in CONFLICT_CODES:
        w = [int(codes_io.has_conflict(with_valid[e], code)) for e in common]
        wo = [int(codes_io.has_conflict(without_valid[e], code)) for e in common]
        conflict_tables[code] = {
            "n_with": sum(w),
            "n_without": sum(wo),
            "added": sum(1 for a, b in zip(w, wo) if a == 0 and b == 1),
            "removed": sum(1 for a, b in zip(w, wo) if a == 1 and b == 0),
            "kappa": safe_kappa(w, wo),
        }
    any_w = [int(bool(codes_io.conflicts(with_valid[e]))) for e in common]
    any_wo = [int(bool(codes_io.conflicts(without_valid[e]))) for e in common]
    kappas["any_conflict"] = safe_kappa(any_w, any_wo)

    n = len(common)
    judge_changed = sum(1 for a, b in judge_pairs if a != b)
    direction = {
        "n_changed": judge_changed,
        "toward_zero": sum(1 for a, b in judge_pairs if a != b and abs(b) < abs(a)),
        "away_from_zero": sum(1 for a, b in judge_pairs if a != b and abs(b) > abs(a)),
        "sign_flips": sum(1 for a, b in judge_pairs if a * b == -1),
        "net_judge_shift_without_minus_with": (
            (sum(b for _, b in judge_pairs) - sum(a for a, _ in judge_pairs)) / n
        ) if n else None,
    }

    per_document: dict[str, dict] = {}
    for doc in sorted({document_of(e) for e in common}):
        ids = [e for e in common if document_of(e) == doc]
        jp = [(codes_io.judge_score(with_valid[e]), codes_io.judge_score(without_valid[e])) for e in ids]
        pp = [(codes_io.patienthood_level(with_valid[e]), codes_io.patienthood_level(without_valid[e])) for e in ids]

        def code_set(coding):
            return set(c.get("code") for c in codes_io.conflicts(coding))

        cp = [(code_set(with_valid[e]), code_set(without_valid[e])) for e in ids]
        k = len(ids)
        per_document[doc] = {
            "n": k,
            "judge_changed": sum(1 for a, b in jp if a != b),
            "judge_change_rate": sum(1 for a, b in jp if a != b) / k,
            "judge_kappa": safe_kappa([p[0] for p in jp], [p[1] for p in jp]),
            "patienthood_change_rate": sum(1 for a, b in pp if a != b) / k,
            "conflict_profile_change_rate": sum(1 for a, b in cp if a != b) / k,
        }

    return {
        "n_common": n,
        "kappas": kappas,
        "judge_transitions": judge_transitions,
        "patienthood_transitions": pat_transitions,
        "conflict_tables": conflict_tables,
        "judge_direction": direction,
        "per_document": per_document,
    }


def _transition_table(transitions: Counter, levels: list, title: str) -> list[str]:
    lines = [title, ""]
    lines.append("| with \\ without | " + " | ".join(str(v) for v in levels) + " |")
    lines.append("|---" * (len(levels) + 1) + "|")
    for a in levels:
        cells = [str(transitions.get((a, b), 0)) for b in levels]
        lines.append(f"| **{a}** | " + " | ".join(cells) + " |")
    lines.append("")
    return lines


def e5_render(result: dict, metas: dict[str, dict]) -> str:
    lines: list[str] = []
    add = lines.append
    add("# E5 — Context ablation (v2 with vs without "
        "section_heading/context_before/context_after)")
    add("")
    add(f"- Generated: {now_utc()}")
    for lab in ("with", "without"):
        m = metas[lab]
        add(f"- `{lab} context`: `{m['path']}` ({m['n_unique_ids']} unique edit_ids, "
            f"{m['n_valid']} valid codes, {m['n_invalid']} invalid/failed)")
    add(f"- N = {result['n_common']} edits with a valid code in both runs.")
    add("")

    add("## Agreement (Cohen kappa, with vs without context)")
    add("")
    add("| dimension | kappa |")
    add("|---|---|")
    for dim in ("judge", "patienthood", "any_conflict"):
        add(f"| {dim} | {_f(result['kappas'][dim])} |")
    for code in CONFLICT_CODES:
        add(f"| conflict present: {code} | {_f(result['conflict_tables'][code]['kappa'])} |")
    add("")

    add("## Transitions (rows = with context, columns = without context)")
    add("")
    lines.extend(_transition_table(result["judge_transitions"], JUDGE_LEVELS, "### judge"))
    lines.extend(
        _transition_table(result["patienthood_transitions"], PATIENTHOOD_DISPLAY, "### patienthood")
    )

    d = result["judge_direction"]
    add("### Direction of judge changes")
    add("")
    add(f"- changed: {d['n_changed']}/{result['n_common']}; toward 0: "
        f"{d['toward_zero']}; away from 0: {d['away_from_zero']}; sign flips "
        f"(+1 <-> -1): {d['sign_flips']}")
    add(f"- net judge shift (without − with): "
        f"{_f(d['net_judge_shift_without_minus_with'])}")
    add("")

    add("### Conflict codes (present/absent per edit)")
    add("")
    add("| code | n with | n without | added (absent -> present) | "
        "removed (present -> absent) | kappa |")
    add("|---|---|---|---|---|---|")
    for code in CONFLICT_CODES:
        t = result["conflict_tables"][code]
        add(f"| {code} | {t['n_with']} | {t['n_without']} | {t['added']} | "
            f"{t['removed']} | {_f(t['kappa'])} |")
    add("")

    add("## Per-document breakdown")
    add("")
    add("Sorted by judge change rate (descending) — the no-context deficit "
        "should concentrate in the documents where context mattered.")
    add("")
    add("| document | n | judge changed | judge change rate | judge kappa | "
        "patienthood change rate | conflict-profile change rate |")
    add("|---|---|---|---|---|---|---|")
    docs = sorted(
        result["per_document"].items(),
        key=lambda kv: (-kv[1]["judge_change_rate"], kv[0]),
    )
    for doc, s in docs:
        add(f"| {doc} | {s['n']} | {s['judge_changed']} | {_f(s['judge_change_rate'])} | "
            f"{_f(s['judge_kappa'])} | {_f(s['patienthood_change_rate'])} | "
            f"{_f(s['conflict_profile_change_rate'])} |")
    add("")
    total_changed = sum(s["judge_changed"] for _, s in docs)
    if total_changed and docs:
        top_doc, top_stats = docs[0]
        add(f"Concentration: the top document ({top_doc}) carries "
            f"{top_stats['judge_changed']}/{total_changed} = "
            f"{_f(top_stats['judge_changed'] / total_changed)} of all judge changes.")
        add("")
    return "\n".join(lines)


def cmd_e5(args) -> None:
    valids, metas = {}, {}
    for lab, path in (("with", args.with_path), ("without", args.without_path)):
        valids[lab], metas[lab] = load_valid_codings(path)
        print(f"[e5] {lab}: {metas[lab]['n_valid']} valid codes from {path}")
    result = e5_compute(valids["with"], valids["without"])
    print(f"[e5] {result['n_common']} edits valid in both runs")
    write_report(args.out, e5_render(result, metas))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Workstream E report generators (E1-E5).")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("e1", help="label-swap diagnostic report")
    p.add_argument("--true", dest="true_path", required=True)
    p.add_argument("--swapped", dest="swapped_path", required=True)
    p.add_argument("--removed", dest="removed_path", required=True)
    p.add_argument("--out", default=str(REPORTS_DIR / "E1_label_swap.md"))
    p.add_argument("--B", type=int, default=DEFAULT_B)
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)

    p = sub.add_parser("e2", help="manual-paraphrase robustness report")
    p.add_argument("--v2", dest="v2_path", required=True)
    p.add_argument("--para1", dest="para1_path", required=True)
    p.add_argument("--para2", dest="para2_path", required=True)
    p.add_argument("--edits", default=str(DEFAULT_EDITS))
    p.add_argument("--out", default=str(REPORTS_DIR / "E2_paraphrase.md"))

    p = sub.add_parser("e3", help="paternalism-definition sensitivity report")
    p.add_argument("--v2", dest="v2_path", required=True)
    p.add_argument("--variant", dest="variant_path", required=True)
    p.add_argument("--ids", default=str(DEFAULT_E3_IDS))
    p.add_argument("--out", default=str(REPORTS_DIR / "E3_paternalism.md"))

    p = sub.add_parser("e4", help="self-consistency report + adjudication extras")
    p.add_argument("--samples", required=True)
    p.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    p.add_argument("--extras-out", dest="extras_out",
                   default=str(E4_ANALYSIS_DIR / "adjudication_extras.json"))
    p.add_argument("--n-extras", dest="n_extras", type=int, default=E4_N_EXTRAS)
    p.add_argument("--expected-samples", dest="expected_samples", type=int,
                   default=E4_EXPECTED_SAMPLES)
    p.add_argument("--out", default=str(REPORTS_DIR / "E4_self_consistency.md"))

    p = sub.add_parser("e5", help="context-ablation report")
    p.add_argument("--with", dest="with_path", required=True)
    p.add_argument("--without", dest="without_path", required=True)
    p.add_argument("--out", default=str(REPORTS_DIR / "E5_context.md"))

    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    {"e1": cmd_e1, "e2": cmd_e2, "e3": cmd_e3, "e4": cmd_e4, "e5": cmd_e5}[args.cmd](args)


if __name__ == "__main__":
    main()
