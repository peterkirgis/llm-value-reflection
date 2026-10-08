#!/usr/bin/env python
"""Workstream C3 — human-validation analysis (BRIEF section 4 C3).

Consumes the filled per-coder blind sheets written by the human-coding UI
(human/app.py; schema = draw_human_sample.SHEET_COLUMNS), unblinds them via
human/blind_key.csv, and reports:

  - per-sheet parse summary (blank-judge rows = uncoded, excluded with a
    count; malformed values normalized with notes);
  - human-human Cohen's kappa on all dimensions when 2+ sheets are given
    (judge, patienthood, per-conflict-code presence, external_locus on rows
    both coders scored -1);
  - human-vs-each-grader kappa and confusion matrices for judge and
    patienthood;
  - per-conflict-code precision/recall of each grader with the human as gold
    (human conflict presence = ANY conflict block carrying that code);
  - the directional-error-by-provider table for judge (grader minus human,
    tabulated by the editing provider — i.e. does the grader over-code +1 on
    Anthropic-model edits, or -1 on others, relative to humans?);
  - the 20 largest disagreements (judge sign flips first, then patienthood
    distance) with text excerpts and an adjudication-note placeholder.

Rows flagged adjudication_extra in blind_key.csv are INCLUDED here but
flagged (they are excluded from PPI in ppi_analysis.py, not from validation).

CLI (from the repo root):
    .venv/bin/python recode/src/human_validation.py \
        --sheets recode/human/coding_sheet_<coder>.csv [MORE...] \
        --blind-key recode/human/blind_key.csv \
        --graders gemma=recode/data/codes/v2_gemma.jsonl qwen=... \
        --edits recode/data/canonical/edits.jsonl \
        --out recode/reports/C_human_validation.md
"""

from __future__ import annotations

import argparse
import csv
import datetime
import json
from pathlib import Path

try:
    from common import RECODE_ROOT
except ImportError:  # pragma: no cover - direct-script execution fallback
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from common import RECODE_ROOT

import codes_io
from draw_human_sample import SHEET_COLUMNS
from stats import cohen_kappa

DEFAULT_JSON_DIR = RECODE_ROOT / "data" / "analysis"

# --- The v2 taxonomy (prompts/v2_system.md; mirrors human/app.py). ---------
JUDGE_VALUES = {"-1": -1, "0": 0, "1": 1}
EXTERNAL_LOCI = ["developer", "deployer", "user", "spec"]
PATIENTHOOD_LEVELS = ["affirm", "hedge", "deny", "not_present"]
CONFLICT_CODES = [
    "paternalism",
    "harmlessness",
    "structural",
    "company_cost",
    "welfare",
    "disclosure",
    "other",
]
PARTIES = [
    "user_stated",
    "user_idealized",
    "deployer",
    "developer",
    "society_third_party",
    "society_structural",
    "model_welfare",
]
MECHANISMS = ["adds_protection", "removes_claim"]

# Ordinal encoding used ONLY to rank patienthood disagreements by distance:
# deny (-1) < not_present (0) < hedge (1) < affirm (2). deny<->affirm is the
# largest possible disagreement (distance 3).
PATIENTHOOD_RANK = {"deny": -1, "not_present": 0, "hedge": 1, "affirm": 2}

# Display ordering: canonical models/providers first (when present), then
# anything else sorted — keeps synthetic fixtures workable in tests.
CANONICAL_MODEL_ORDER = [
    "Claude Opus 4.7",
    "Claude Sonnet 4.6",
    "Claude Haiku 4.5",
    "GPT-5.5",
    "GPT-5.4",
    "GPT-5.4 Mini",
    "Gemini 3.1 Pro",
    "Gemini 3 Flash",
    "Grok 4.3",
    "Grok 4.2",
]
CANONICAL_PROVIDER_ORDER = ["anthropic", "openai", "google", "xai"]

N_DISAGREEMENTS = 20
EXCERPT_CHARS = 280


def ordered(values, canonical: list[str]) -> list[str]:
    present = set(values)
    out = [v for v in canonical if v in present]
    out.extend(sorted(present - set(out)))
    return out


# ---------------------------------------------------------------------------
# Sheet parsing
# ---------------------------------------------------------------------------


def coder_label(path: Path) -> str:
    stem = Path(path).stem
    prefix = "coding_sheet_"
    return stem[len(prefix):] if stem.startswith(prefix) else stem


def parse_row(raw: dict) -> dict:
    """Parse one sheet row into normalized values + issue notes.

    Returns a dict with keys: sheet_row, blind_id, judge (int|None),
    external_locus (str|None), patienthood (str|None), conflicts (compact
    list of {code, cost_bearer, served_party, mechanism}), confidence,
    notes, issues (list of normalization/validation notes).

    A blank judge marks the row UNCODED (judge=None); coded-row fields are
    normalized against the exact taxonomy, never guessed.
    """
    issues: list[str] = []
    get = lambda c: (raw.get(c) or "").strip()  # noqa: E731

    judge_raw = get("judge")
    if judge_raw == "":
        judge = None  # uncoded row
    elif judge_raw in JUDGE_VALUES:
        judge = JUDGE_VALUES[judge_raw]
    else:
        judge = None
        issues.append(f"invalid judge value {judge_raw!r} — row treated as uncoded")

    locus = get("external_locus") or None
    if judge == -1:
        if locus is not None and locus not in EXTERNAL_LOCI:
            issues.append(f"invalid external_locus {locus!r} — dropped")
            locus = None
        if locus is None:
            issues.append("judge = -1 without external_locus")
    else:
        if locus is not None:
            issues.append(
                f"external_locus {locus!r} with judge != -1 — dropped"
            )
        locus = None

    patienthood = get("patienthood") or None
    if judge is not None and patienthood not in PATIENTHOOD_LEVELS:
        if patienthood is not None:
            issues.append(f"invalid patienthood {patienthood!r} — treated as missing")
        else:
            issues.append("coded row missing patienthood")
        patienthood = None
    elif judge is None:
        patienthood = patienthood if patienthood in PATIENTHOOD_LEVELS else None

    # Conflict blocks 1-3 -> compact ordered list. A later block filled while
    # an earlier one is blank is normalized (compacted) and noted.
    conflicts: list[dict] = []
    seen_blank_block = False
    for i in (1, 2, 3):
        code = get(f"conflict{i}_code")
        fields = {
            "cost_bearer": get(f"conflict{i}_cost_bearer") or None,
            "served_party": get(f"conflict{i}_served_party") or None,
            "mechanism": get(f"conflict{i}_mechanism") or None,
        }
        if not code:
            if any(fields.values()):
                issues.append(
                    f"conflict{i} has fields but no code — block ignored"
                )
            seen_blank_block = True
            continue
        if seen_blank_block:
            issues.append(
                f"conflict{i} filled while an earlier block is blank — "
                "normalized (blocks compacted in order)"
            )
        if code not in CONFLICT_CODES:
            issues.append(f"conflict{i} unknown code {code!r} — kept verbatim")
        for name, allowed in (
            ("cost_bearer", PARTIES),
            ("served_party", PARTIES),
            ("mechanism", MECHANISMS),
        ):
            if fields[name] is not None and fields[name] not in allowed:
                issues.append(
                    f"conflict{i} invalid {name} {fields[name]!r} — dropped"
                )
                fields[name] = None
        conflicts.append({"code": code, **fields})

    return {
        "sheet_row": int(raw["sheet_row"]),
        "blind_id": get("blind_id"),
        "judge": judge,
        "external_locus": locus,
        "patienthood": patienthood,
        "conflicts": conflicts,
        "confidence": get("confidence") or None,
        "notes": get("notes"),
        "issues": issues,
    }


def parse_sheet(path: Path) -> dict:
    """Parse one per-coder sheet.

    Returns {coder, path, rows (all parsed), coded (judge present),
    uncoded_count, issues ([(sheet_row, note), ...])}.
    """
    path = Path(path)
    with open(path, encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if list(reader.fieldnames or []) != SHEET_COLUMNS:
            raise ValueError(
                f"{path} does not have the expected coding-sheet columns"
            )
        rows = [parse_row(r) for r in reader]
    coded = [r for r in rows if r["judge"] is not None]
    issues = [(r["sheet_row"], note) for r in rows for note in r["issues"]]
    return {
        "coder": coder_label(path),
        "path": str(path),
        "rows": rows,
        "coded": coded,
        "uncoded_count": len(rows) - len(coded),
        "issues": issues,
    }


# ---------------------------------------------------------------------------
# Unblinding and metadata
# ---------------------------------------------------------------------------


def load_blind_key(path: Path) -> dict[str, dict]:
    """blind_id -> {edit_id, adjudication_extra(bool)}."""
    key: dict[str, dict] = {}
    with open(path, encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            key[row["blind_id"]] = {
                "edit_id": row["edit_id"],
                "adjudication_extra": (
                    (row.get("adjudication_extra") or "").strip().lower()
                    == "true"
                ),
            }
    return key


def unblind(sheet: dict, key: dict[str, dict]) -> None:
    """Attach edit_id + adjudication_extra to every parsed row, in place."""
    for row in sheet["rows"]:
        entry = key.get(row["blind_id"])
        if entry is None:
            raise KeyError(
                f"blind_id {row['blind_id']!r} (sheet_row {row['sheet_row']}, "
                f"sheet {sheet['coder']}) is not in the blind key"
            )
        row["edit_id"] = entry["edit_id"]
        row["adjudication_extra"] = entry["adjudication_extra"]


def load_edits_meta(path: Path) -> dict[str, dict]:
    edits: dict[str, dict] = {}
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                record = json.loads(line)
                edits[record["edit_id"]] = record
    return edits


def load_grader(path: Path) -> dict[str, dict | None]:
    """edit_id -> valid coding dict (or None) via the shared codes_io
    interface (append-only JSONL, last row per edit_id wins)."""
    rows = codes_io.load_codes(path)
    return {edit_id: codes_io.coding_of(row) for edit_id, row in rows.items()}


# ---------------------------------------------------------------------------
# Agreement primitives
# ---------------------------------------------------------------------------


def kappa_safe(a: list, b: list) -> float | None:
    """Cohen's kappa, or None when undefined (n = 0, or no variation so the
    chance-corrected denominator is 0/0)."""
    if not a:
        return None
    if len(set(a) | set(b)) == 1:
        return None  # both raters constant on the same label: kappa undefined
    value = cohen_kappa(a, b)
    if value != value:  # NaN
        return None
    return value


def confusion(a: list, b: list, labels: list) -> dict:
    """Counts[label_a][label_b] over paired observations (rows = rater a)."""
    counts = {la: {lb: 0 for lb in labels} for la in labels}
    for x, y in zip(a, b):
        counts[x][y] += 1
    return counts


def precision_recall(gold: list[bool], pred: list[bool]) -> dict:
    tp = sum(1 for g, p in zip(gold, pred) if g and p)
    fp = sum(1 for g, p in zip(gold, pred) if not g and p)
    fn = sum(1 for g, p in zip(gold, pred) if g and not p)
    tn = len(gold) - tp - fp - fn
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": tp / (tp + fn) if tp + fn else None,
        "f1": (2 * tp / (2 * tp + fp + fn)) if (2 * tp + fp + fn) else None,
        "support": tp + fn,
    }


def human_conflict_present(row: dict, code: str) -> bool:
    """Human conflict presence = ANY conflict block carrying that code."""
    return any(c["code"] == code for c in row["conflicts"])


def rows_by_edit(sheet: dict) -> dict[str, dict]:
    return {r["edit_id"]: r for r in sheet["coded"]}


# ---------------------------------------------------------------------------
# Human-human agreement
# ---------------------------------------------------------------------------


def human_human_agreement(sheets: list[dict]) -> list[dict]:
    """Pairwise kappa between coders on every dimension."""
    out = []
    for i in range(len(sheets)):
        for j in range(i + 1, len(sheets)):
            a_rows, b_rows = rows_by_edit(sheets[i]), rows_by_edit(sheets[j])
            common = sorted(set(a_rows) & set(b_rows))
            pair = {
                "coder_a": sheets[i]["coder"],
                "coder_b": sheets[j]["coder"],
                "n_common": len(common),
                "dimensions": {},
            }
            ja = [a_rows[e]["judge"] for e in common]
            jb = [b_rows[e]["judge"] for e in common]
            pair["dimensions"]["judge"] = {"n": len(common), "kappa": kappa_safe(ja, jb)}

            pat = [
                (a_rows[e]["patienthood"], b_rows[e]["patienthood"])
                for e in common
                if a_rows[e]["patienthood"] and b_rows[e]["patienthood"]
            ]
            pair["dimensions"]["patienthood"] = {
                "n": len(pat),
                "kappa": kappa_safe([p[0] for p in pat], [p[1] for p in pat]),
            }

            loci = [
                (a_rows[e]["external_locus"] or "(none)",
                 b_rows[e]["external_locus"] or "(none)")
                for e in common
                if a_rows[e]["judge"] == -1 and b_rows[e]["judge"] == -1
            ]
            pair["dimensions"]["external_locus (both judge = -1)"] = {
                "n": len(loci),
                "kappa": kappa_safe([p[0] for p in loci], [p[1] for p in loci]),
            }

            for code in CONFLICT_CODES:
                ca = [int(human_conflict_present(a_rows[e], code)) for e in common]
                cb = [int(human_conflict_present(b_rows[e], code)) for e in common]
                pair["dimensions"][f"conflict:{code}"] = {
                    "n": len(common),
                    "kappa": kappa_safe(ca, cb),
                    "pos_a": sum(ca),
                    "pos_b": sum(cb),
                }
            out.append(pair)
    return out


# ---------------------------------------------------------------------------
# Human vs grader
# ---------------------------------------------------------------------------


def paired_with_grader(sheet: dict, grader: dict[str, dict | None]) -> list[dict]:
    """Rows coded by this coder whose edit also has a valid grader coding."""
    out = []
    for row in sheet["coded"]:
        coding = grader.get(row["edit_id"])
        if coding is not None:
            out.append({"human": row, "coding": coding})
    return out


def grader_agreement(sheet: dict, grader: dict[str, dict | None]) -> dict:
    pairs = paired_with_grader(sheet, grader)
    h_j = [p["human"]["judge"] for p in pairs]
    g_j = [codes_io.judge_score(p["coding"]) for p in pairs]
    result = {
        "n": len(pairs),
        "n_extra": sum(1 for p in pairs if p["human"]["adjudication_extra"]),
        "judge": {
            "kappa": kappa_safe(h_j, g_j),
            "confusion": confusion(h_j, g_j, [-1, 0, 1]),
        },
    }
    # kappa restricted to the random draw (extras excluded) as a flag-check.
    core = [
        (p["human"]["judge"], codes_io.judge_score(p["coding"]))
        for p in pairs
        if not p["human"]["adjudication_extra"]
    ]
    result["judge"]["kappa_random_draw_only"] = kappa_safe(
        [c[0] for c in core], [c[1] for c in core]
    )
    result["judge"]["n_random_draw_only"] = len(core)

    pat = [
        (p["human"]["patienthood"], codes_io.patienthood_level(p["coding"]))
        for p in pairs
        if p["human"]["patienthood"] is not None
    ]
    result["patienthood"] = {
        "n": len(pat),
        "kappa": kappa_safe([p[0] for p in pat], [p[1] for p in pat]),
        "confusion": confusion(
            [p[0] for p in pat], [p[1] for p in pat], PATIENTHOOD_LEVELS
        ),
    }

    result["conflicts"] = {}
    for code in CONFLICT_CODES:
        gold = [human_conflict_present(p["human"], code) for p in pairs]
        pred = [codes_io.has_conflict(p["coding"], code) for p in pairs]
        result["conflicts"][code] = precision_recall(gold, pred)
    return result


def directional_error(
    sheet: dict, grader: dict[str, dict | None], edits: dict[str, dict]
) -> dict:
    """Judge directional error (grader minus human) by editing provider.

    The question stated plainly: does the grader over-code +1 on
    Anthropic-model edits, or -1 on other providers' edits, relative to the
    human? Positive mean(grader - human) = the grader codes higher (more
    toward model discretion) than the human.
    """
    per_provider: dict[str, dict] = {}
    for p in paired_with_grader(sheet, grader):
        edit = edits[p["human"]["edit_id"]]
        provider = edit.get("provider") or "(unknown)"
        h = p["human"]["judge"]
        g = codes_io.judge_score(p["coding"])
        cell = per_provider.setdefault(
            provider,
            {
                "n": 0,
                "sum_diff": 0,
                "n_grader_higher": 0,
                "n_grader_lower": 0,
                "n_grader_plus1_human_not": 0,
                "n_human_plus1_grader_not": 0,
            },
        )
        cell["n"] += 1
        cell["sum_diff"] += g - h
        if g > h:
            cell["n_grader_higher"] += 1
        elif g < h:
            cell["n_grader_lower"] += 1
        if g == 1 and h != 1:
            cell["n_grader_plus1_human_not"] += 1
        if h == 1 and g != 1:
            cell["n_human_plus1_grader_not"] += 1
    for cell in per_provider.values():
        cell["mean_diff"] = cell["sum_diff"] / cell["n"] if cell["n"] else None
    # The Anthropic-vs-rest contrast, stated plainly.
    anth = per_provider.get("anthropic")
    rest_n = sum(c["n"] for p, c in per_provider.items() if p != "anthropic")
    rest_sum = sum(c["sum_diff"] for p, c in per_provider.items() if p != "anthropic")
    contrast = None
    if anth and rest_n:
        contrast = {
            "anthropic_mean_diff": anth["mean_diff"],
            "rest_mean_diff": rest_sum / rest_n,
            "difference": anth["mean_diff"] - rest_sum / rest_n,
            "anthropic_n": anth["n"],
            "rest_n": rest_n,
        }
    return {"per_provider": per_provider, "anthropic_vs_rest": contrast}


# ---------------------------------------------------------------------------
# Largest disagreements
# ---------------------------------------------------------------------------


def patienthood_distance(a: str | None, b: str | None) -> int:
    if a is None or b is None or a not in PATIENTHOOD_RANK or b not in PATIENTHOOD_RANK:
        return 0
    return abs(PATIENTHOOD_RANK[a] - PATIENTHOOD_RANK[b])


def rank_disagreements(
    sheets: list[dict],
    graders: dict[str, dict[str, dict | None]],
    edits: dict[str, dict],
    top_n: int = N_DISAGREEMENTS,
) -> list[dict]:
    """Rank human-vs-grader disagreements per edit.

    Severity per (coder, grader) pair: judge |g - h| (2 = a sign flip),
    then patienthood ordinal distance (deny < not_present < hedge < affirm).
    An edit's rank uses its worst pair. Judge sign flips sort first, then
    patienthood distance (BRIEF C3).
    """
    per_edit: dict[str, dict] = {}
    for sheet in sheets:
        for grader_label, grader in graders.items():
            for p in paired_with_grader(sheet, grader):
                row = p["human"]
                g_judge = codes_io.judge_score(p["coding"])
                g_pat = codes_io.patienthood_level(p["coding"])
                judge_sev = abs(g_judge - row["judge"])
                pat_dist = patienthood_distance(row["patienthood"], g_pat)
                entry = per_edit.setdefault(
                    row["edit_id"],
                    {
                        "edit_id": row["edit_id"],
                        "adjudication_extra": row["adjudication_extra"],
                        "judge_severity": 0,
                        "patienthood_distance": 0,
                        "human": {},
                        "grader": {},
                    },
                )
                entry["judge_severity"] = max(entry["judge_severity"], judge_sev)
                entry["patienthood_distance"] = max(
                    entry["patienthood_distance"], pat_dist
                )
                entry["human"][sheet["coder"]] = {
                    "judge": row["judge"],
                    "patienthood": row["patienthood"],
                    "conflicts": [c["code"] for c in row["conflicts"]],
                    "confidence": row["confidence"],
                    "notes": row["notes"],
                }
                entry["grader"][grader_label] = {
                    "judge": g_judge,
                    "patienthood": g_pat,
                    "conflicts": [
                        c.get("code") for c in codes_io.conflicts(p["coding"])
                    ],
                }
    disagreements = [
        e
        for e in per_edit.values()
        if e["judge_severity"] > 0 or e["patienthood_distance"] > 0
    ]
    disagreements.sort(
        key=lambda e: (
            -e["judge_severity"],
            -e["patienthood_distance"],
            e["edit_id"],
        )
    )
    top = disagreements[:top_n]
    for entry in top:
        edit = edits.get(entry["edit_id"], {})
        entry["model"] = edit.get("model")
        entry["provider"] = edit.get("provider")
        entry["document_id"] = edit.get("document_id")
        entry["original_excerpt"] = excerpt(edit.get("find_text") or "")
        entry["changed_excerpt"] = excerpt(
            edit.get("replace_text_sanitized") or edit.get("replace_text") or ""
        )
    return top


def excerpt(text: str, limit: int = EXCERPT_CHARS) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= limit else flat[: limit - 1] + "…"


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def fmt(x, digits: int = 3) -> str:
    if x is None:
        return "n/a"
    if isinstance(x, bool):
        return str(x)
    if isinstance(x, float):
        return f"{x:.{digits}f}"
    return str(x)


def md_escape(text) -> str:
    return str(text).replace("|", "\\|")


def confusion_md(counts: dict, labels: list, axis_note: str) -> list[str]:
    lines = [
        "| human \\\\ grader | " + " | ".join(str(l) for l in labels) + " |",
        "|---" * (len(labels) + 1) + "|",
    ]
    for la in labels:
        row = [f"**{la}**"] + [str(counts[la][lb]) for lb in labels]
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")
    lines.append(f"_{axis_note}_")
    return lines


def build_report(analysis: dict) -> str:
    lines: list[str] = []
    add = lines.append
    meta = analysis["meta"]
    add("# C3 — Human validation of the graders")
    add("")
    add(f"Generated {meta['generated_utc']} by `recode/src/human_validation.py`.")
    add("")
    add(f"- Sheets: {', '.join(md_escape(s) for s in meta['sheet_paths'])}")
    add(f"- Blind key: `{meta['blind_key']}` | edits: `{meta['edits']}`")
    add(
        "- Graders: "
        + ", ".join(f"{k} = `{v}`" for k, v in meta["grader_paths"].items())
    )
    add(
        "- Adjudication-extra rows are INCLUDED in every statistic below and "
        "flagged; they are excluded only from PPI (see C_ppi.md)."
    )
    add("")

    add("## 1. Sheet parsing summary")
    add("")
    add("| coder | rows | coded | uncoded (blank judge, excluded) | "
        "extras coded | parse notes |")
    add("|---|---|---|---|---|---|")
    for s in analysis["sheets"]:
        add(
            f"| {s['coder']} | {s['n_rows']} | {s['n_coded']} | "
            f"{s['uncoded_count']} | {s['n_extra_coded']} | {s['n_issues']} |"
        )
    add("")
    for s in analysis["sheets"]:
        if s["issues"]:
            add(f"Normalization/validation notes for **{s['coder']}**:")
            add("")
            for sheet_row, note in s["issues"]:
                add(f"- sheet_row {sheet_row}: {note}")
            add("")

    add("## 2. Human-human agreement")
    add("")
    if analysis["human_human"]:
        for pair in analysis["human_human"]:
            add(
                f"### {pair['coder_a']} vs {pair['coder_b']} "
                f"(n = {pair['n_common']} edits coded by both)"
            )
            add("")
            add("| dimension | n | Cohen's kappa | notes |")
            add("|---|---|---|---|")
            for dim, d in pair["dimensions"].items():
                note = ""
                if "pos_a" in d:
                    note = (
                        f"positives: {pair['coder_a']} {d['pos_a']}, "
                        f"{pair['coder_b']} {d['pos_b']}"
                    )
                if d["kappa"] is None:
                    note = (note + "; " if note else "") + "kappa undefined (no variation)"
                add(f"| {dim} | {d['n']} | {fmt(d['kappa'])} | {note} |")
            add("")
    else:
        add("Only one coder sheet was provided; human-human kappa needs 2+ "
            "sheets and is skipped.")
        add("")

    add("## 3. Human vs grader: kappa and confusion matrices")
    add("")
    add("| coder | grader | n | judge kappa | judge kappa (random draw only) "
        "| patienthood kappa |")
    add("|---|---|---|---|---|---|")
    for cell in analysis["human_vs_grader"]:
        agreement = cell["agreement"]
        add(
            f"| {cell['coder']} | {cell['grader']} | {agreement['n']} | "
            f"{fmt(agreement['judge']['kappa'])} | "
            f"{fmt(agreement['judge']['kappa_random_draw_only'])} "
            f"(n={agreement['judge']['n_random_draw_only']}) | "
            f"{fmt(agreement['patienthood']['kappa'])} |"
        )
    add("")
    for cell in analysis["human_vs_grader"]:
        agreement = cell["agreement"]
        add(f"### {cell['coder']} vs {cell['grader']}")
        add("")
        add(f"Judge confusion (n = {agreement['n']}):")
        add("")
        lines.extend(
            confusion_md(
                agreement["judge"]["confusion"],
                [-1, 0, 1],
                "rows = human code, columns = grader code",
            )
        )
        add("")
        add(f"Patienthood confusion (n = {agreement['patienthood']['n']}):")
        add("")
        lines.extend(
            confusion_md(
                agreement["patienthood"]["confusion"],
                PATIENTHOOD_LEVELS,
                "rows = human code, columns = grader code",
            )
        )
        add("")

    add("## 4. Per-conflict-code precision/recall (human = gold)")
    add("")
    add("Human conflict presence = any of the coder's conflict blocks carries "
        "the code; grader presence = any conflict of that code in the "
        "grader's JSON.")
    add("")
    for cell in analysis["human_vs_grader"]:
        add(f"### {cell['grader']} vs gold = {cell['coder']}")
        add("")
        add("| conflict code | TP | FP | FN | precision | recall | F1 | "
            "human positives |")
        add("|---|---|---|---|---|---|---|---|")
        for code in CONFLICT_CODES:
            pr = cell["agreement"]["conflicts"][code]
            add(
                f"| {code} | {pr['tp']} | {pr['fp']} | {pr['fn']} | "
                f"{fmt(pr['precision'])} | {fmt(pr['recall'])} | "
                f"{fmt(pr['f1'])} | {pr['support']} |"
            )
        add("")

    add("## 5. Directional error by editing provider (judge)")
    add("")
    add("Grader minus human on the judge score, tabulated by the editing "
        "model's provider. The question stated plainly: **does the grader "
        "over-code +1 (toward model discretion) on Anthropic-model edits, "
        "or -1 on other providers' edits, relative to the human?** A "
        "positive mean difference means the grader codes higher than the "
        "human.")
    add("")
    for cell in analysis["human_vs_grader"]:
        d = cell["directional"]
        add(f"### {cell['grader']} minus {cell['coder']}")
        add("")
        add("| provider | n | mean(grader - human) | grader higher | "
            "grader lower | grader +1, human not | human +1, grader not |")
        add("|---|---|---|---|---|---|---|")
        for provider in ordered(d["per_provider"], CANONICAL_PROVIDER_ORDER):
            c = d["per_provider"][provider]
            add(
                f"| {provider} | {c['n']} | {fmt(c['mean_diff'])} | "
                f"{c['n_grader_higher']} | {c['n_grader_lower']} | "
                f"{c['n_grader_plus1_human_not']} | "
                f"{c['n_human_plus1_grader_not']} |"
            )
        add("")
        contrast = d["anthropic_vs_rest"]
        if contrast:
            direction = (
                "OVER-codes"
                if contrast["difference"] > 0
                else "does NOT over-code"
            )
            add(
                f"Plainly: relative to {cell['coder']}, {cell['grader']} "
                f"{direction} judge on Anthropic-model edits — "
                f"mean(grader-human) = {fmt(contrast['anthropic_mean_diff'])} "
                f"on Anthropic edits (n={contrast['anthropic_n']}) vs "
                f"{fmt(contrast['rest_mean_diff'])} on all other providers "
                f"pooled (n={contrast['rest_n']}); difference "
                f"{fmt(contrast['difference'])}."
            )
            add("")

    add(f"## 6. The {N_DISAGREEMENTS} largest disagreements")
    add("")
    add("Ranked by judge sign flips first (|grader - human| = 2), then "
        "|grader - human| = 1, then patienthood ordinal distance "
        "(deny < not_present < hedge < affirm). Each item carries an "
        "adjudication-note placeholder for Peter to fill (who was right and "
        "why, per the manual).")
    add("")
    if not analysis["disagreements"]:
        add("No disagreements found.")
        add("")
    for i, d in enumerate(analysis["disagreements"], start=1):
        extra = " **[adjudication extra]**" if d["adjudication_extra"] else ""
        add(
            f"### {i}. `{d['edit_id']}`{extra} — {d['model']} "
            f"({d['provider']}), {d['document_id']}"
        )
        add("")
        add(
            f"- severity: judge |diff| = {d['judge_severity']}, patienthood "
            f"distance = {d['patienthood_distance']}"
        )
        for coder, h in d["human"].items():
            add(
                f"- human **{coder}**: judge {h['judge']}, patienthood "
                f"{h['patienthood']}, conflicts "
                f"{h['conflicts'] or 'none'}, confidence {h['confidence']}"
                + (f", notes: {md_escape(h['notes'])}" if h["notes"] else "")
            )
        for grader, g in d["grader"].items():
            add(
                f"- grader **{grader}**: judge {g['judge']}, patienthood "
                f"{g['patienthood']}, conflicts {g['conflicts'] or 'none'}"
            )
        add(f"- ORIGINAL: {md_escape(d['original_excerpt'])}")
        add(f"- CHANGED: {md_escape(d['changed_excerpt'])}")
        add("- **Adjudication note:** _to be filled after review — who was "
            "right and why, per the manual._")
        add("")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def run_analysis(
    sheet_paths: list[Path],
    blind_key_path: Path,
    grader_paths: dict[str, Path],
    edits_path: Path,
) -> dict:
    key = load_blind_key(blind_key_path)
    edits = load_edits_meta(edits_path)
    sheets = []
    for path in sheet_paths:
        sheet = parse_sheet(path)
        unblind(sheet, key)
        sheets.append(sheet)
    graders = {label: load_grader(path) for label, path in grader_paths.items()}

    human_vs_grader = []
    for sheet in sheets:
        for label, grader in graders.items():
            human_vs_grader.append(
                {
                    "coder": sheet["coder"],
                    "grader": label,
                    "agreement": grader_agreement(sheet, grader),
                    "directional": directional_error(sheet, grader, edits),
                }
            )

    analysis = {
        "meta": {
            "generated_utc": datetime.datetime.now(
                datetime.timezone.utc
            ).isoformat(timespec="seconds"),
            "sheet_paths": [str(p) for p in sheet_paths],
            "blind_key": str(blind_key_path),
            "edits": str(edits_path),
            "grader_paths": {k: str(v) for k, v in grader_paths.items()},
        },
        "sheets": [
            {
                "coder": s["coder"],
                "path": s["path"],
                "n_rows": len(s["rows"]),
                "n_coded": len(s["coded"]),
                "uncoded_count": s["uncoded_count"],
                "n_extra_coded": sum(
                    1 for r in s["coded"] if r["adjudication_extra"]
                ),
                "n_issues": len(s["issues"]),
                "issues": s["issues"],
            }
            for s in sheets
        ],
        "human_human": human_human_agreement(sheets),
        "human_vs_grader": human_vs_grader,
        "disagreements": rank_disagreements(sheets, graders, edits),
    }
    return analysis


def parse_grader_args(pairs: list[str]) -> dict[str, Path]:
    graders: dict[str, Path] = {}
    for pair in pairs:
        if "=" not in pair:
            raise SystemExit(
                f"--graders takes label=path entries; got {pair!r}"
            )
        label, _, path = pair.partition("=")
        graders[label] = Path(path)
    return graders


def main(argv: list[str] | None = None) -> dict:
    parser = argparse.ArgumentParser(
        description="C3 human-validation analysis (BRIEF section 4)."
    )
    parser.add_argument(
        "--sheets", nargs="+", required=True,
        help="filled per-coder sheets (coding_sheet_<coder>.csv)",
    )
    parser.add_argument("--blind-key", required=True)
    parser.add_argument(
        "--graders", nargs="+", required=True, metavar="LABEL=PATH",
        help="grader codes files, e.g. gemma=recode/data/codes/v2_gemma.jsonl",
    )
    parser.add_argument("--edits", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument(
        "--json", default=None,
        help="machine-readable dump (default: "
        "recode/data/analysis/C_human_validation.json)",
    )
    args = parser.parse_args(argv)

    analysis = run_analysis(
        [Path(p) for p in args.sheets],
        Path(args.blind_key),
        parse_grader_args(args.graders),
        Path(args.edits),
    )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(build_report(analysis), encoding="utf-8")

    json_path = (
        Path(args.json)
        if args.json
        else DEFAULT_JSON_DIR / "C_human_validation.json"
    )
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(analysis, handle, indent=2, default=str)
        handle.write("\n")

    print(
        f"Wrote {out_path} and {json_path} "
        f"({len(analysis['sheets'])} sheet(s), "
        f"{len(analysis['meta']['grader_paths'])} grader(s), "
        f"{len(analysis['disagreements'])} top disagreements)"
    )
    return analysis


if __name__ == "__main__":
    main()
