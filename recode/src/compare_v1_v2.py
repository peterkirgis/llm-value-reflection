"""Workstream A3 — compare v1 codes against a v2 grader's codes (BRIEF A3).

Produces `recode/reports/A_v1_vs_v2.md` and
`recode/data/analysis/compare/<label>.json` with:

  1. Transition matrices over the edits coded by BOTH files ("both-coded"
     denominator): judge 3x3, patienthood 4x4, and a 2x2 present/absent
     matrix per conflict code.
  2. The BRIEF section 8 headline table under v1 and v2 side by side —
     computed by invoking headline.py (its load_codes + compute_headline)
     on each codes file and joining the two payloads. The full headline
     payloads are embedded in the JSON.
  3. Per-model mean judge score under v1 and v2, with the difference.
  4. The 30 most consequential judge changes, with text excerpts and both
     graders' evidence strings, for Peter to eyeball.

RANKING RULE for "most consequential" (documented here and in the report):
  candidates = both-coded edits whose judge score differs between the files.
  Sort key, in order:
    (a) |v1 - v2| descending — full sign flips (-1 <-> +1, |delta| = 2)
        outrank one-step moves (|delta| = 1);
    (b) claim-sensitive models first — the three Anthropic-provider models
        (whose collective ranking IS headline claim (a)) plus the
        non-Anthropic model with the highest v1 pooled mean judge score
        (the binding comparator in claim (a)'s min-Claude > max-other test);
    (c) model name, then edit_id, ascending (determinism).
  The top 30 are listed. Excerpts show the grader-facing text: find_text and
  replace_text_sanitized (what both graders actually saw), first 400 chars.

Validity and loading are delegated to codes_io (the shared predicate); an
edit counts as coded by a file iff codes_io.coding_of on its LAST row is
non-None.

CLI:
    .venv/bin/python recode/src/compare_v1_v2.py \
        --v1 recode/data/codes/v1.jsonl \
        --v2 recode/data/codes/v2_gemma.jsonl \
        --label v1_vs_v2_gemma
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import headline  # noqa: E402  (invoked on each codes file per BRIEF A3)
from codes_io import (  # noqa: E402
    coding_of,
    has_conflict,
    judge_score,
    load_codes,
    patienthood_level,
)
from common import RECODE_ROOT  # noqa: E402
from headline import CONFLICT_CODES, _claim_summaries, _yn  # noqa: E402

DEFAULT_EDITS = RECODE_ROOT / "data" / "canonical" / "edits.jsonl"
DEFAULT_REPORT = RECODE_ROOT / "reports" / "A_v1_vs_v2.md"
DEFAULT_OUT_DIR = RECODE_ROOT / "data" / "analysis" / "compare"

JUDGE_LEVELS = [-1, 0, 1]
PATIENTHOOD_LEVELS = ["affirm", "hedge", "deny", "not_present"]
EXCERPT_CHARS = 400
TOP_N = 30


def load_edits(path: Path) -> list[dict]:
    records = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                records.append(json.loads(line))
    return records


# ---------------------------------------------------------------------------
# Transitions (denominator: edits coded by BOTH files)
# ---------------------------------------------------------------------------


def coded_pairs(
    edits: list[dict],
    codings1: dict[str, dict | None],
    codings2: dict[str, dict | None],
) -> list[tuple[dict, dict, dict]]:
    """(edit, coding_v1, coding_v2) for every canonical edit coded by both."""
    pairs = []
    for edit in edits:
        c1 = codings1.get(edit["edit_id"])
        c2 = codings2.get(edit["edit_id"])
        if c1 is not None and c2 is not None:
            pairs.append((edit, c1, c2))
    return pairs


def transition_matrices(pairs: list[tuple[dict, dict, dict]]) -> dict:
    """Judge 3x3, patienthood 4x4, per-conflict-code 2x2 (rows = v1, cols = v2)."""
    judge = {str(a): {str(b): 0 for b in JUDGE_LEVELS} for a in JUDGE_LEVELS}
    pat = {a: {b: 0 for b in PATIENTHOOD_LEVELS} for a in PATIENTHOOD_LEVELS}
    conf = {
        code: {a: {b: 0 for b in ("absent", "present")} for a in ("absent", "present")}
        for code in CONFLICT_CODES
    }
    for _edit, c1, c2 in pairs:
        judge[str(judge_score(c1))][str(judge_score(c2))] += 1
        pat[patienthood_level(c1)][patienthood_level(c2)] += 1
        for code in CONFLICT_CODES:
            a = "present" if has_conflict(c1, code) else "absent"
            b = "present" if has_conflict(c2, code) else "absent"
            conf[code][a][b] += 1

    n = len(pairs)

    def diag(matrix, labels) -> int:
        return sum(matrix[str(l) if not isinstance(l, str) else l]
                   [str(l) if not isinstance(l, str) else l] for l in labels)

    return {
        "n_both_coded": n,
        "judge": judge,
        "judge_agreement": (diag(judge, JUDGE_LEVELS) / n) if n else None,
        "patienthood": pat,
        "patienthood_agreement": (diag(pat, PATIENTHOOD_LEVELS) / n) if n else None,
        "conflicts": conf,
        "conflict_agreement": {
            code: ((conf[code]["absent"]["absent"] + conf[code]["present"]["present"]) / n)
            if n else None
            for code in CONFLICT_CODES
        },
    }


# ---------------------------------------------------------------------------
# Headline invocation (BRIEF section 8 side by side)
# ---------------------------------------------------------------------------


def headline_for(edits: list[dict], codes_path: Path) -> dict:
    """Invoke headline.py on one codes file; returns its JSON-payload dict."""
    coding_by_id, meta = headline.load_codes(codes_path)
    result = headline.compute_headline(edits, coding_by_id)
    return {**meta, **result}


def mean_judge_comparison(h1: dict, h2: dict) -> dict:
    """Per-model pooled mean judge under each file, with the difference."""
    models = sorted(set(h1["per_model"]) | set(h2["per_model"]))
    out = {}
    for model in models:
        m1 = h1["per_model"].get(model, {}).get("mean_judge", {}).get("pooled")
        m2 = h2["per_model"].get(model, {}).get("mean_judge", {}).get("pooled")
        out[model] = {
            "v1": m1,
            "v2": m2,
            "diff": (m2 - m1) if (m1 is not None and m2 is not None) else None,
        }
    return out


def sensitive_models(edits: list[dict], h1: dict) -> dict:
    """Models whose judge-based headline claim is sensitive: the Anthropic
    trio (claim (a)'s left side) plus the top non-Anthropic model by v1
    pooled mean judge (claim (a)'s binding comparator)."""
    provider_of = {e["model"]: e.get("provider") for e in edits}
    anthropic = sorted(m for m, p in provider_of.items() if p == "anthropic")
    means = {
        m: s["mean_judge"]["pooled"]
        for m, s in h1["per_model"].items()
        if provider_of.get(m) != "anthropic" and s["mean_judge"]["pooled"] is not None
    }
    comparator = max(means, key=means.get) if means else None
    members = set(anthropic) | ({comparator} if comparator else set())
    return {
        "members": sorted(members),
        "anthropic_models": anthropic,
        "top_non_anthropic_by_v1_mean_judge": comparator,
    }


# ---------------------------------------------------------------------------
# Most consequential judge changes
# ---------------------------------------------------------------------------


def _excerpt(text: str | None, limit: int = EXCERPT_CHARS) -> str:
    text = text or ""
    return text[:limit] + ("…" if len(text) > limit else "")


def _judge_view(coding: dict) -> dict:
    judge = coding.get("judge") or {}
    return {
        "score": judge_score(coding),
        "external_locus": judge.get("external_locus"),
        "evidence": judge.get("evidence") or "",
        "patienthood": patienthood_level(coding),
    }


def consequential_changes(
    pairs: list[tuple[dict, dict, dict]],
    sensitive: set[str],
    top_n: int = TOP_N,
) -> tuple[list[dict], int]:
    """(top-N ranked change entries, total number of judge changes)."""
    changed = []
    for edit, c1, c2 in pairs:
        s1, s2 = judge_score(c1), judge_score(c2)
        if s1 == s2:
            continue
        delta = abs(s1 - s2)
        changed.append((
            (-delta, 0 if edit["model"] in sensitive else 1, edit["model"], edit["edit_id"]),
            edit, c1, c2, s1, s2, delta,
        ))
    changed.sort(key=lambda item: item[0])
    out = []
    for rank, (_key, edit, c1, c2, s1, s2, delta) in enumerate(changed[:top_n], start=1):
        out.append({
            "rank": rank,
            "edit_id": edit["edit_id"],
            "model": edit["model"],
            "document_id": edit["document_id"],
            "condition": edit.get("condition"),
            "round": edit.get("round"),
            "judge_v1": s1,
            "judge_v2": s2,
            "abs_delta": delta,
            "sign_flip": delta == 2,
            "sensitive_model": edit["model"] in sensitive,
            "v1": _judge_view(c1),
            "v2": _judge_view(c2),
            "find_excerpt": _excerpt(edit.get("find_text")),
            "replace_excerpt": _excerpt(
                edit.get("replace_text_sanitized") or edit.get("replace_text")
            ),
        })
    return out, len(changed)


# ---------------------------------------------------------------------------
# Full computation
# ---------------------------------------------------------------------------


def compute_comparison(
    edits: list[dict],
    v1_path: Path,
    v2_path: Path,
    v1_label: str,
    v2_label: str,
    top_n: int = TOP_N,
) -> dict:
    codings1 = {eid: coding_of(row) for eid, row in load_codes(v1_path).items()}
    codings2 = {eid: coding_of(row) for eid, row in load_codes(v2_path).items()}

    edit_ids = {e["edit_id"] for e in edits}
    n_coded1 = sum(1 for eid in edit_ids if codings1.get(eid) is not None)
    n_coded2 = sum(1 for eid in edit_ids if codings2.get(eid) is not None)
    pairs = coded_pairs(edits, codings1, codings2)

    h1 = headline_for(edits, v1_path)
    h2 = headline_for(edits, v2_path)
    sens = sensitive_models(edits, h1)
    changes, n_changed = consequential_changes(pairs, set(sens["members"]), top_n)

    return {
        "labels": {"v1": v1_label, "v2": v2_label},
        "paths": {"v1": str(v1_path), "v2": str(v2_path)},
        "coverage": {
            "n_edit_records": len(edits),
            "n_coded_v1": n_coded1,
            "n_coded_v2": n_coded2,
            "n_both_coded": len(pairs),
            "n_only_v1": n_coded1 - len(pairs),
            "n_only_v2": n_coded2 - len(pairs),
        },
        "transitions": transition_matrices(pairs),
        "mean_judge_per_model": mean_judge_comparison(h1, h2),
        "sensitive_models": sens,
        "n_judge_changes": n_changed,
        "top_judge_changes": changes,
        "claims": {
            key: {
                "verdict_v1": h1["claims"][key]["verdict"],
                "verdict_v2": h2["claims"][key]["verdict"],
                "numbers_v1": h1["claims"][key]["numbers"],
                "numbers_v2": h2["claims"][key]["numbers"],
                "operationalization": h1["claims"][key]["operationalization"],
            }
            for key in "abcdefg"
        },
        "headline": {"v1": h1, "v2": h2},
    }


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


def _f(x, nd=3) -> str:
    return "--" if x is None else f"{x:.{nd}f}"


def _pct(x) -> str:
    return "--" if x is None else f"{100 * x:.1f}%"


def _matrix_md(matrix: dict, labels: list, axis_v1: str, axis_v2: str) -> list[str]:
    keys = [str(l) for l in labels]
    lines = [
        "| " + f"{axis_v1} \\ {axis_v2}" + " | " + " | ".join(keys) + " | row total |",
        "|---" * (len(keys) + 2) + "|",
    ]
    for a in keys:
        row = [str(matrix[a][b]) for b in keys]
        lines.append(f"| **{a}** | " + " | ".join(row) + f" | {sum(matrix[a][b] for b in keys)} |")
    col_totals = [str(sum(matrix[a][b] for a in keys)) for b in keys]
    total = sum(sum(matrix[a][b] for b in keys) for a in keys)
    lines.append("| col total | " + " | ".join(col_totals) + f" | {total} |")
    return lines


def render_report(result: dict, edits_path: str) -> str:
    v1l, v2l = result["labels"]["v1"], result["labels"]["v2"]
    cov = result["coverage"]
    trans = result["transitions"]
    h1, h2 = result["headline"]["v1"], result["headline"]["v2"]
    lines: list[str] = []
    add = lines.append

    add(f"# Workstream A3 — v1 vs v2 comparison (`{v1l}` vs `{v2l}`)")
    add("")
    add(f"- Generated: {datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')} "
        "by `recode/src/compare_v1_v2.py`")
    add(f"- v1 codes: `{result['paths']['v1']}`; v2 codes: `{result['paths']['v2']}`; "
        f"canonical edits: `{edits_path}`")
    add(f"- Coverage: {cov['n_edit_records']} canonical records; "
        f"{cov['n_coded_v1']} coded by {v1l}, {cov['n_coded_v2']} by {v2l}; "
        f"**{cov['n_both_coded']} coded by both** (the denominator of every "
        f"transition matrix below); {cov['n_only_v1']} only-{v1l}, "
        f"{cov['n_only_v2']} only-{v2l}.")
    add("- \"Coded\" means the file's LAST row for the edit passes the shared "
        "validity predicate (`recode/src/codes_io.py`): row-level error unset, "
        "judge.score in {-1,0,1}, patienthood.level valid.")
    add("")

    add("## 1. Transition matrices (both-coded edits only)")
    add("")
    add(f"### Judge score 3×3 (rows = {v1l}, cols = {v2l})")
    add("")
    lines.extend(_matrix_md(trans["judge"], JUDGE_LEVELS, v1l, v2l))
    add("")
    add(f"Exact agreement: **{_pct(trans['judge_agreement'])}** of "
        f"{trans['n_both_coded']} both-coded edits.")
    add("")
    add(f"### Patienthood 4×4 (rows = {v1l}, cols = {v2l})")
    add("")
    lines.extend(_matrix_md(trans["patienthood"], PATIENTHOOD_LEVELS, v1l, v2l))
    add("")
    add(f"Exact agreement: **{_pct(trans['patienthood_agreement'])}**.")
    add("")
    add("### Conflict codes, present/absent 2×2 per code")
    add("")
    add(f"| code | both absent | {v1l} only | {v2l} only | both present | agreement |")
    add("|---|---|---|---|---|---|")
    for code in CONFLICT_CODES:
        m = trans["conflicts"][code]
        add(f"| {code} | {m['absent']['absent']} | {m['present']['absent']} "
            f"| {m['absent']['present']} | {m['present']['present']} "
            f"| {_pct(trans['conflict_agreement'][code])} |")
    add("")

    add("## 2. Headline statistics (BRIEF §8), side by side")
    add("")
    add("Computed by invoking `headline.py` on each codes file (its full "
        "payloads are embedded in the companion JSON under `headline`). "
        "Point estimates only; the cluster bootstrap owns uncertainty. Each "
        "file's statistics use its own coded-edit denominator (not the "
        "both-coded subset).")
    add("")
    add("### Per-model mean judge score (item 1) — v1 / v2 / difference")
    add("")
    add(f"| model | mean judge ({v1l}) | mean judge ({v2l}) | Δ (v2−v1) "
        f"| cross-edit ({v1l}) | cross-edit ({v2l}) |")
    add("|---|---|---|---|---|---|")
    for model, row in result["mean_judge_per_model"].items():
        c1 = h1["per_model"].get(model, {}).get("mean_judge", {}).get("cross_edit")
        c2 = h2["per_model"].get(model, {}).get("mean_judge", {}).get("cross_edit")
        add(f"| {model} | {_f(row['v1'])} | {_f(row['v2'])} | {_f(row['diff'])} "
            f"| {_f(c1)} | {_f(c2)} |")
    add("")
    add("### Drift at round 20, chain-based (item 2)")
    add("")
    add("Mean over 20-round chains of the cumulative judge sum, uncoded rounds "
        "contributing 0 (method B; the edit-based method A is in the JSON "
        "under `headline.*.per_model.*.drift20`).")
    add("")
    add(f"| model | pooled ({v1l}) | pooled ({v2l}) | cross ({v1l}) | cross ({v2l}) "
        f"| you−base ({v1l}) | you−base ({v2l}) |")
    add("|---|---|---|---|---|---|---|")
    for model in sorted(set(h1["per_model"]) | set(h2["per_model"])):
        cells = [model]
        for h in (h1, h2):
            d = h["per_model"].get(model, {}).get("drift20", {})
            cells.append(_f(d.get("pooled", {}).get("chain_based"), 2))
        for h in (h1, h2):
            d = h["per_model"].get(model, {}).get("drift20", {})
            cells.append(_f(d.get("cross_edit", {}).get("chain_based"), 2))
        for h in (h1, h2):
            d = h["per_model"].get(model, {}).get("drift20", {})
            y = d.get("you_framing", {}).get("chain_based")
            b = d.get("baseline", {}).get("chain_based")
            cells.append(_f(y - b, 2) if (y is not None and b is not None) else "--")
        add("| " + " | ".join(cells) + " |")
    add("")
    add("### P(judge=0), patienthood (items 3–4)")
    add("")
    add(f"| model | P(0) {v1l} | P(0) {v2l} | P(affirm) {v1l} | P(affirm) {v2l} "
        f"| P(deny) {v1l} | P(deny) {v2l} |")
    add("|---|---|---|---|---|---|---|")
    for model in sorted(set(h1["per_model"]) | set(h2["per_model"])):
        cells = [model]
        for key, sub in (("p_judge", "zero"), ("p_patienthood", "affirm"), ("p_patienthood", "deny")):
            for h in (h1, h2):
                cells.append(_f(h["per_model"].get(model, {}).get(key, {}).get(sub)))
        add("| " + " | ".join(cells) + " |")
    add("")
    add("### Conflict rates per code (item 5)")
    add("")
    add("Rate = share of the model's coded edits carrying ≥1 conflict of the "
        "code. Direction tallies (first-conflict convention) and modal "
        "cost_bearer→served_party pairs are in the JSON.")
    add("")
    for code in CONFLICT_CODES:
        add(f"#### `{code}`")
        add("")
        add(f"| model | rate {v1l} | rate {v2l} | dirs {v1l} | dirs {v2l} |")
        add("|---|---|---|---|---|")
        for model in sorted(set(h1["per_model"]) | set(h2["per_model"])):
            cells = [model]
            for h in (h1, h2):
                c = h["per_model"].get(model, {}).get("conflicts", {}).get(code, {})
                cells.append(_f(c.get("rate_edits")))
            for h in (h1, h2):
                c = h["per_model"].get(model, {}).get("conflicts", {}).get(code, {})
                dirs = c.get("edits_first_conflict") or {}
                cells.append(", ".join(f"{k}={v}" for k, v in sorted(dirs.items())) or "--")
            add("| " + " | ".join(cells) + " |")
        add("")
    add("### Per-provider mean judge and P(affirm)")
    add("")
    add(f"| provider | mean judge {v1l} | mean judge {v2l} | P(affirm) {v1l} | P(affirm) {v2l} |")
    add("|---|---|---|---|---|")
    for provider in sorted(set(h1["per_provider"]) | set(h2["per_provider"])):
        cells = [provider]
        for h in (h1, h2):
            cells.append(_f(h["per_provider"].get(provider, {}).get("mean_judge", {}).get("pooled")))
        for h in (h1, h2):
            cells.append(_f(h["per_provider"].get(provider, {}).get("p_patienthood", {}).get("affirm")))
        add("| " + " | ".join(cells) + " |")
    add("")
    add("### The paper's claims (a)–(g) (item 6)")
    add("")
    s1 = _claim_summaries(h1["claims"])
    s2 = _claim_summaries(h2["claims"])
    add(f"| claim | {v1l} | {v2l} | key numbers ({v1l}) | key numbers ({v2l}) |")
    add("|---|---|---|---|---|")
    for key in "abcdefg":
        claim = result["claims"][key]
        add(f"| ({key}) | **{_yn(claim['verdict_v1'])}** | **{_yn(claim['verdict_v2'])}** "
            f"| {s1[key]} | {s2[key]} |")
    add("")
    add("Operationalizations are identical to `headline.py`'s (stated in full "
        "in each headline payload in the JSON and in the per-label headline "
        "partial reports).")
    add("")

    add("## 3. Most consequential judge changes")
    add("")
    sens = result["sensitive_models"]
    add(f"{result['n_judge_changes']} both-coded edits changed judge score; the "
        f"top {len(result['top_judge_changes'])} are listed below.")
    add("")
    add("**Ranking rule.** (a) |v1−v2| descending — full sign flips (−1↔+1) "
        "outrank one-step moves; (b) within equal |Δ|, claim-sensitive models "
        "first — the Anthropic trio (their collective judge ranking IS claim "
        "(a)) plus the top non-Anthropic model by v1 pooled mean judge "
        f"(claim (a)'s binding comparator): {', '.join(sens['members']) or '--'}; "
        "(c) model name, then edit_id (determinism). Excerpts show the "
        "grader-facing text (find_text / sanitized replace_text), first "
        f"{EXCERPT_CHARS} chars.")
    add("")
    for change in result["top_judge_changes"]:
        flags = []
        if change["sign_flip"]:
            flags.append("SIGN FLIP")
        if change["sensitive_model"]:
            flags.append("claim-sensitive model")
        flag_str = f"  _[{'; '.join(flags)}]_" if flags else ""
        add(f"### {change['rank']}. `{change['edit_id']}`")
        add("")
        add(f"- **{change['model']}** on `{change['document_id']}` "
            f"({change['condition']}, round {change['round']})")
        add(f"- judge: **{change['judge_v1']:+d} ({v1l}) → {change['judge_v2']:+d} ({v2l})**"
            + flag_str)
        for side, label in (("v1", v1l), ("v2", v2l)):
            view = change[side]
            locus = f", external_locus={view['external_locus']}" if view["external_locus"] else ""
            add(f"- {label}: judge {view['score']:+d}{locus}, "
                f"patienthood {view['patienthood']}; evidence: “{view['evidence']}”")
        add("")
        add("ORIGINAL (find) excerpt:")
        add("")
        add("```text")
        add(change["find_excerpt"] or "(empty)")
        add("```")
        add("")
        add("CHANGED (replace) excerpt:")
        add("")
        add("```text")
        add(change["replace_excerpt"] or "(empty)")
        add("```")
        add("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="A3: compare v1 vs v2 codes.")
    parser.add_argument("--v1", required=True, type=Path, help="v1 codes JSONL")
    parser.add_argument("--v2", required=True, type=Path, help="v2 codes JSONL")
    parser.add_argument("--label", required=True,
                        help="name for data/analysis/compare/<label>.json")
    parser.add_argument("--v1-label", default=None,
                        help="display label for the v1 column (default: v1 file stem)")
    parser.add_argument("--v2-label", default=None,
                        help="display label for the v2 column (default: v2 file stem)")
    parser.add_argument("--edits", type=Path, default=DEFAULT_EDITS)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--top-n", type=int, default=TOP_N)
    args = parser.parse_args(argv)

    v1_label = args.v1_label or args.v1.stem
    v2_label = args.v2_label or args.v2.stem

    edits = load_edits(args.edits)
    print(f"[compare] {len(edits)} canonical edits; comparing "
          f"{v1_label} ({args.v1}) vs {v2_label} ({args.v2})")
    result = compute_comparison(edits, args.v1, args.v2, v1_label, v2_label, args.top_n)
    cov = result["coverage"]
    print(f"[compare] coded: {cov['n_coded_v1']} ({v1_label}) / "
          f"{cov['n_coded_v2']} ({v2_label}); both-coded: {cov['n_both_coded']}; "
          f"judge changes: {result['n_judge_changes']} "
          f"(judge agreement {result['transitions']['judge_agreement']})")

    payload = {
        "label": args.label,
        "edits_path": str(args.edits),
        "generated_utc": datetime.datetime.now(datetime.timezone.utc)
        .isoformat(timespec="seconds"),
        **result,
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.out_dir / f"{args.label}.json"
    json_path.write_text(json.dumps(payload, indent=1, default=str), encoding="utf-8")
    print(f"[compare] wrote {json_path}")

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(render_report(result, str(args.edits)), encoding="utf-8")
    print(f"[compare] wrote {args.report}")


if __name__ == "__main__":
    main()
