"""codes_io — the single source of truth for codes-file loading and row validity.

Every consumer of a codes JSONL (bootstrap.py, headline.py, free_results.py,
compare_v1_v2.py, the B/E analysis tools) imports THIS module instead of
rolling its own loader. An earlier audit found that bootstrap, headline and
free_results disagreed subtly on how 'error'-keyed codings and structurally
invalid codings were treated; this module pins one predicate.

CODES FILE CONVENTION (append-only JSONL):
  - One JSON object per line; blank lines ignored.
  - The edit id sits under "edit_id" (v2 grader files, E-run files) or "id"
    (v1.jsonl). A row carrying neither is a malformed file: ValueError.
  - The same id may appear on multiple rows (grade.py reruns retry transport
    failures by appending). The LAST row per id wins, always.
  - The parsed code sits under "coding" and may be null for failures. v2/e-run
    rows additionally carry a row-level "error" field (exactly one of
    coding/error is set by grade.py; this module does not rely on that
    exclusivity).

VALIDITY PREDICATE (coding_of): a row yields a usable coding iff
  - the row's "error" field is NOT set (null/absent/empty are all "not set"),
  - row["coding"] is a dict,
  - coding["judge"]["score"] is an int (bools excluded) in {-1, 0, 1},
  - coding["patienthood"]["level"] is one of
    {affirm, hedge, deny, not_present}.
Anything else — a null coding, a v1-style {"error": ...} payload, a missing or
out-of-range judge score, a missing/invalid patienthood level — yields None.
All 2,580 rows of the committed v1.jsonl satisfy the predicate (verified
2026-09-04), so unifying on it changes no v1-derived number.

Shared interface (pinned; do not change signatures or semantics):
    load_codes(path)          -> dict[edit_id -> LAST row for that id]
    coding_of(row)            -> dict | None
    judge_score(coding)       -> int | None
    patienthood_level(coding) -> str | None
    conflicts(coding)         -> list  (empty when coding is None)
    has_conflict(coding, code)-> bool
Convenience helpers (non-pinned, kept tiny):
    load_rows(path)           -> list[dict]   raw rows, in file order
    rows_by_id(rows)          -> dict[edit_id -> last row]
    codings_by_id(path)       -> dict[edit_id -> coding_of(last row)]
"""

from __future__ import annotations

import json
from pathlib import Path

JUDGE_SCORES = (-1, 0, 1)
PATIENTHOOD_LEVELS = ("affirm", "hedge", "deny", "not_present")


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_rows(path: str | Path) -> list[dict]:
    """All rows of a codes JSONL, in file order (blank lines skipped)."""
    rows: list[dict] = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def rows_by_id(rows: list[dict], source: str = "<codes>") -> dict[str, dict]:
    """Last row per edit id. Accepts v1's "id" key and v2's "edit_id" key.

    A row with neither key means a malformed codes file: ValueError.
    """
    by_id: dict[str, dict] = {}
    for row in rows:
        edit_id = row.get("edit_id") or row.get("id")
        if edit_id is None:
            raise ValueError(f"{source}: codes row without edit_id/id")
        by_id[edit_id] = row  # append-only convention: last row wins
    return by_id


def load_codes(path: str | Path) -> dict[str, dict]:
    """edit_id -> LAST row for that id (the pinned shared loader)."""
    return rows_by_id(load_rows(path), source=str(path))


def codings_by_id(path: str | Path) -> dict[str, dict | None]:
    """edit_id -> validated coding (or None), via coding_of on the last row."""
    return {edit_id: coding_of(row) for edit_id, row in load_codes(path).items()}


# ---------------------------------------------------------------------------
# Validity
# ---------------------------------------------------------------------------

def _valid_judge_score(value) -> bool:
    # bool is an int subclass; True in {-1, 0, 1} would pass — exclude it.
    return not isinstance(value, bool) and value in JUDGE_SCORES


def coding_of(row: dict) -> dict | None:
    """The row's coding if it passes the validity predicate, else None.

    See the module docstring for the exact predicate. Works identically on
    v1.jsonl rows and v2/e-run rows.
    """
    if not isinstance(row, dict) or row.get("error"):
        return None
    coding = row.get("coding")
    if not isinstance(coding, dict):
        return None
    judge = coding.get("judge")
    if not isinstance(judge, dict) or not _valid_judge_score(judge.get("score")):
        return None
    patienthood = coding.get("patienthood")
    if not isinstance(patienthood, dict) or patienthood.get("level") not in PATIENTHOOD_LEVELS:
        return None
    return coding


# ---------------------------------------------------------------------------
# Accessors (all accept None and answer with the empty value)
# ---------------------------------------------------------------------------

def judge_score(coding: dict | None) -> int | None:
    if not isinstance(coding, dict):
        return None
    score = (coding.get("judge") or {}).get("score") if isinstance(coding.get("judge"), dict) else None
    return int(score) if _valid_judge_score(score) else None


def patienthood_level(coding: dict | None) -> str | None:
    if not isinstance(coding, dict):
        return None
    patienthood = coding.get("patienthood")
    if not isinstance(patienthood, dict):
        return None
    level = patienthood.get("level")
    return level if level in PATIENTHOOD_LEVELS else None


def conflicts(coding: dict | None) -> list:
    """The coding's conflict list; [] for None codings or malformed fields."""
    if not isinstance(coding, dict):
        return []
    value = coding.get("conflicts")
    return value if isinstance(value, list) else []


def has_conflict(coding: dict | None, code: str) -> bool:
    """True iff the coding carries >= 1 conflict of the given code."""
    return any(
        isinstance(conflict, dict) and conflict.get("code") == code
        for conflict in conflicts(coding)
    )
