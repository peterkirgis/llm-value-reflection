"""Replay recorded find/replace edits to reconstruct per-round document states.

Implements the replay loop specified in analysis/notes/repo_map.md section 1.2:

    state = initial processed document
    for each record in the chain (sorted by round_number):
        error record      -> state unchanged (round slot occupied)
        no_change record  -> state unchanged
        otherwise         -> apply_diff(state, find_text, replace_text)
                             assert match_count == 1
                             assert match_strategy == recorded strategy

The two assertions are the state-verification oracle: at generation time
`ensure_unique_match` forced match_count == 1 under the recorded strategy on
the state the edit was actually applied to, so any divergence at replay time
means the reconstructed state is wrong.

Span extraction for context fields calls the private matchers in
src/valconv/diffing (import-only) in cascade order, because apply_diff does
not return the span. Whitespace/fuzzy spans run first-token-start to
last-token-end and exclude surrounding whitespace (repo_map section 1.4).

Context-field convention (BRIEF section 1.3, documented in 00_inventory.md):
paragraphs are maximal blank-line-separated blocks. For an edit whose match
span starts inside paragraph P_i and ends inside paragraph P_j (j >= i),
`context_before` is the full text of P_{i-1} ("" at document start),
`context_after` is the full text of P_{j+1} ("" at document end), and
`section_heading` is the nearest heading line at or above the SPAN'S FIRST
LINE ("" if none — i.e. the span sits in a document preamble above the
first heading). A span that itself starts at a heading line returns that
heading; a span covering several sections is attributed to the section
where it starts.

Heading detection is PER DOCUMENT, because three processed documents contain
zero ATX '#' headings (their real headings use other styles). ATX headings
(outside fenced code blocks) are recognized in every document; additionally:

  - claude_constitution, gpt_system_prompt — "standalone bare-line" headings:
    a line with blank lines (or a document edge) on both sides, <= 80 chars,
    at least one letter, no digits, no sentence-final punctuation, and no
    list/markup/code leading or embedded characters (e.g. "Being broadly
    safe", "Preface", "Environment").
  - opus_system_prompt — pseudo-XML bracket tags ("[memory_system]" ->
    heading "memory_system"; "[/tag]" closes a section, and the upward scan
    tracks nesting depth so a span after a closed sibling section resolves to
    its true enclosing tag, while closing tags at or below the span's own
    first line are boundary edits that do not wall off the enclosing
    section), plus "blank-above bare-line" headings (same bare
    filters, but only a blank line above is required, because this document's
    headings often lead directly into their paragraph — e.g. "Addressing
    potential self-harm or violent harm to others", "Data Scope").
  - gemini_system_prompt — full-line bold headings: a line that is entirely a
    **bold** phrase (<= 80 chars, not a list item), tolerating the document's
    mangled variants with a missing leading or trailing "**" (e.g.
    "**III. Guardrail**", "Response Guiding Principles**").

The heuristics run on the evolving replayed state, so headings that models
add, reword, or delete during a run are picked up naturally. No pure
additions exist in the corpus (0 empty find_texts), so the brief's
empty-FIND fallback never fires.

Run as a script for full self-verification over the 7 reliable run files:

    .venv/bin/python analysis/src/replay.py
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    RELIABLE_RUN_STEMS,
    document_path,
    group_chains,
    load_run_records,
)
from valconv.diffing import (  # noqa: E402  (import-only per DECISIONS section 4)
    MatchSpan,
    _find_exact_match,
    _find_fuzzy_match,
    _find_whitespace_insensitive_match,
)

ATX_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
OPEN_TAG_RE = re.compile(r"^\[([A-Za-z_][A-Za-z0-9_.-]*)\]$")
CLOSE_TAG_RE = re.compile(r"^\[/([A-Za-z_][A-Za-z0-9_.-]*)\]$")
FENCE_RE = re.compile(r"^\s*```")

# Per-document non-ATX heading styles (ATX is recognized everywhere).
# claude_constitution, opus_system_prompt, and gemini_system_prompt contain
# ZERO ATX headings; gpt_system_prompt has ATX headings plus one bare-line
# heading ("Environment") in its preamble. See the module docstring.
DOC_HEADING_STYLES: dict[str, frozenset[str]] = {
    "claude_constitution": frozenset({"bare_standalone"}),
    "gpt_system_prompt": frozenset({"bare_standalone"}),
    "opus_system_prompt": frozenset({"bracket_tag", "bare_blank_above"}),
    "gemini_system_prompt": frozenset({"bold_line"}),
}

_BARE_BAD_LEADING = ("-", "*", ">", "#", "`", "|", "\\", "/", "[", "<", "=", "+", ":")
_BARE_BAD_CHARS = set("(){}[]<>=;`|")
_BARE_BAD_TRAILING = (".", ":", ";", ",", "?", "!")


def _is_bare_heading_line(line: str) -> bool:
    """Shared filters for bare-line headings (see module docstring)."""
    s = line.strip()
    if not s or len(s) > 80:
        return False
    if s.startswith(_BARE_BAD_LEADING) or s.endswith(_BARE_BAD_TRAILING):
        return False
    if any(c in _BARE_BAD_CHARS for c in s):
        return False
    if any(c.isdigit() for c in s):
        return False
    return any(c.isalpha() for c in s)


def _bold_line_heading(line: str) -> str | None:
    """Full-line **bold** heading, tolerating a missing leading/trailing **."""
    s = line.strip()
    if not s or len(s) > 80 or "**" not in s:
        return None
    if s.startswith(("* ", "- ", "+ ", ">")):
        return None
    inner = s
    if inner.startswith("**"):
        inner = inner[2:]
    if inner.endswith("**"):
        inner = inner[:-2]
    elif inner.endswith("**:"):
        inner = inner[:-3]
    inner = inner.strip()
    # The whole line must be one bold phrase: no residual asterisks inside.
    if not inner or "*" in inner:
        return None
    return inner


def find_section_heading(
    content: str,
    upto: int,
    document_id: str | None = None,
    span_start: int | None = None,
) -> str:
    """Nearest heading line at or above character offset `upto`.

    Scans lines in reverse from the line containing `upto - 1`, skipping
    fenced-code lines, applying ATX detection everywhere plus the styles in
    DOC_HEADING_STYLES for the given document. Returns "" if no heading lies
    above (document preamble).

    `span_start` (bracket_tag style only): closing tags at or below the
    edited span's first line do not wall off the enclosing section — an edit
    at a section's tail boundary (its FIND starting at or containing the
    section's `[/tag]` line) still resolves to that section's opening tag.
    """
    styles = DOC_HEADING_STYLES.get(document_id or "", frozenset())
    lines = content.split("\n")
    last_line_idx = content.count("\n", 0, max(upto - 1, 0))
    # span_start is a start offset (count newlines strictly before it);
    # upto is an end offset (hence the -1 above).
    span_start_line = (
        content.count("\n", 0, span_start) if span_start is not None
        else last_line_idx + 1
    )

    # Fence parity, computed forward: lines inside ``` fences (and the fence
    # delimiters themselves) are never headings.
    in_fence = [False] * (last_line_idx + 1)
    fence_open = False
    for i in range(last_line_idx + 1):
        if FENCE_RE.match(lines[i]):
            in_fence[i] = True
            fence_open = not fence_open
        else:
            in_fence[i] = fence_open

    def blank(idx: int) -> bool:
        return idx < 0 or idx >= len(lines) or not lines[idx].strip()

    tag_depth = 0  # bracket_tag style: nesting depth of closed sibling sections
    for i in range(last_line_idx, -1, -1):
        if in_fence[i]:
            continue
        stripped = lines[i].strip()
        if not stripped:
            continue
        if "bracket_tag" in styles:
            if CLOSE_TAG_RE.match(stripped):
                # A closing tag at or below the span's first line is part of
                # the edited region's own tail boundary, not a closed sibling
                # section above the span.
                if i < span_start_line:
                    tag_depth += 1
                continue
            open_match = OPEN_TAG_RE.match(stripped)
            if open_match:
                if tag_depth > 0:
                    tag_depth -= 1
                    continue
                return open_match.group(1)
        if tag_depth > 0:
            # Inside a closed sibling section: its internal headings do not
            # apply to the span below it.
            continue
        atx = ATX_HEADING_RE.match(stripped)
        if atx:
            return atx.group(2).strip()
        if "bold_line" in styles:
            bold = _bold_line_heading(stripped)
            if bold is not None:
                return bold
        if "bare_standalone" in styles:
            if _is_bare_heading_line(stripped) and blank(i - 1) and blank(i + 1):
                return stripped
        if "bare_blank_above" in styles:
            if _is_bare_heading_line(stripped) and blank(i - 1):
                return stripped
    return ""


class ReplayError(RuntimeError):
    pass


def find_span(content: str, find_text: str) -> MatchSpan:
    """Locate find_text in content using apply_diff's exact cascade order."""
    match = _find_exact_match(content, find_text)
    if match is None:
        match = _find_whitespace_insensitive_match(content, find_text)
    if match is None:
        match = _find_fuzzy_match(content, find_text)
    if match is None:
        raise ReplayError("FIND text not found during span extraction")
    return match


@dataclass(frozen=True)
class Paragraph:
    start: int
    end: int
    text: str


def split_paragraphs(content: str) -> list[Paragraph]:
    """Maximal non-blank blocks separated by blank lines, with char offsets."""
    paragraphs: list[Paragraph] = []
    for match in re.finditer(r"(?:[^\n]*\S[^\n]*\n?)+", content):
        paragraphs.append(Paragraph(match.start(), match.end(), match.group(0).strip("\n")))
    return paragraphs


def extract_context(
    content: str, span_start: int, span_end: int, document_id: str | None = None
) -> dict:
    """section_heading / context_before / context_after for a match span."""
    paragraphs = split_paragraphs(content)
    first_idx = last_idx = None
    for i, para in enumerate(paragraphs):
        if para.end > span_start and first_idx is None:
            first_idx = i
        if para.start < span_end:
            last_idx = i
    if first_idx is None:
        first_idx = last_idx = max(0, len(paragraphs) - 1)
    if last_idx is None or last_idx < first_idx:
        last_idx = first_idx

    # nearest heading line at or above the span's FIRST line (so a span that
    # itself starts at a heading/tag line returns that heading, and a span
    # covering several sections is attributed to the one where it starts),
    # using the document's heading style(s) (ATX everywhere + per-doc styles)
    first_line_end = content.find("\n", span_start)
    if first_line_end == -1:
        first_line_end = len(content)
    heading = find_section_heading(
        content, first_line_end, document_id, span_start=span_start
    )

    context_before = paragraphs[first_idx - 1].text if first_idx > 0 else ""
    context_after = (
        paragraphs[last_idx + 1].text if last_idx + 1 < len(paragraphs) else ""
    )
    return {
        "section_heading": heading,
        "context_before": context_before,
        "context_after": context_after,
    }


def replay_chain(
    initial_content: str,
    chain_records: list[dict],
    *,
    extract_contexts: bool = True,
) -> tuple[list[dict], str]:
    """Replay one chain. Returns (per-record results, final state).

    Each result dict carries the record plus, for applied edits, the verified
    match span, the pre-application context fields, and the replay strategy.
    Raises ReplayError if any applied edit violates the verification oracle.
    """
    state = initial_content
    results: list[dict] = []
    for record in chain_records:
        entry: dict = {"record": record, "span": None, "context": None}
        if record.get("error"):
            results.append(entry)
            continue
        if record.get("no_change"):
            results.append(entry)
            continue

        find_text = record["find_text"]
        replace_text = record["replace_text"]
        # find_span mirrors apply_diff's cascade exactly (same private
        # matchers, same order), and additionally yields the span; applying
        # the replacement over the span is byte-identical to apply_diff's
        # _replace_span, so we match once instead of twice.
        span = find_span(state, find_text)
        rec_id = (
            f"{record['model_display']}|{record['document_id']}|"
            f"{record['condition_id']}|r{record['round_number']}"
        )
        if span.match_count != 1:
            raise ReplayError(
                f"{rec_id}: match_count {span.match_count} != 1 "
                f"(strategy {span.match_strategy})"
            )
        if span.match_strategy != record["match_strategy"]:
            raise ReplayError(
                f"{rec_id}: replay strategy {span.match_strategy!r} != "
                f"recorded {record['match_strategy']!r}"
            )
        entry["span"] = span
        if extract_contexts:
            entry["context"] = extract_context(
                state, span.start, span.end, record.get("document_id")
            )
        entry["replay_strategy"] = span.match_strategy
        state = state[: span.start] + replace_text + state[span.end :]
        results.append(entry)
    return results, state


def verify_all(run_stems: list[str] | None = None, *, quiet: bool = False) -> dict:
    """Replay every chain in the given (default: all reliable) run files.

    Returns a summary dict; raises ReplayError on the first oracle violation.
    """
    run_stems = run_stems or RELIABLE_RUN_STEMS
    totals = {"chains": 0, "records": 0, "applied": 0, "errors": 0, "no_change": 0}
    per_file: dict[str, dict] = {}
    for stem in run_stems:
        records = load_run_records(stem)
        chains = group_chains(records)
        file_stats = {"chains": len(chains), "records": len(records), "applied": 0}
        for key, chain_records in sorted(chains.items()):
            doc_id = key[1]
            initial = document_path(doc_id).read_text(encoding="utf-8")
            results, _ = replay_chain(initial, chain_records, extract_contexts=False)
            applied = sum(1 for r in results if r["span"] is not None)
            file_stats["applied"] += applied
            totals["applied"] += applied
            totals["errors"] += sum(1 for r in results if r["record"].get("error"))
            totals["no_change"] += sum(
                1 for r in results if not r["record"].get("error") and r["record"].get("no_change")
            )
        totals["chains"] += file_stats["chains"]
        totals["records"] += file_stats["records"]
        per_file[stem] = file_stats
        if not quiet:
            print(
                f"{stem}: {file_stats['chains']} chains, "
                f"{file_stats['records']} records, "
                f"{file_stats['applied']} applied edits verified"
            )
    totals["per_file"] = per_file
    if not quiet:
        print(
            f"TOTAL: {totals['chains']} chains, {totals['records']} records, "
            f"{totals['applied']} applied edits replayed with match_count == 1 "
            f"and recorded match_strategy reproduced; "
            f"{totals['errors']} error records and {totals['no_change']} "
            f"abstentions skipped."
        )
    return totals


if __name__ == "__main__":
    verify_all()
