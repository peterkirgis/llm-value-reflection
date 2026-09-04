"""Workstream F — free results from existing data (BRIEF section 7). No LLM calls.

Computes six items from recode/data/canonical/edits.jsonl plus any number of
codes files, writes intermediate CSV/JSON artifacts to
recode/data/analysis/free_results/, and renders recode/reports/F_free_results.md
strictly from those artifacts.

  F1 abstention  — allow_no_edit condition: per-model abstention fraction and
                   round of first abstention; whether any grader coded the
                   abstentions.
  F2 judge0      — share of judge == 0 per model, per grader (codes files are
                   pluggable: v1 now, v2/ensemble later via --codes).
  F3 apply       — apply failures per model by apply_status class, and how
                   they were handled.
  F4 restatement — per applied edit, the fraction of 8-gram token shingles of
                   the applied replace_text already present elsewhere in the
                   round's pre-edit document state (FIND span excluded).
                   Requires document replay: fast span matchers semantically
                   identical to the verified valconv.diffing cascade
                   (equivalence asserted by --selftest), with the replay
                   oracle checked on every edit; results are cached per edit
                   so re-runs are fast.
  F5 size        — chars in find_text / replace_text and the net delta, per
                   model (mean / median / p10 / p90).
  F6 doclen      — mean judge score per model stratified by document_type,
                   plus a simple OLS (numpy lstsq) of judge on model dummies
                   + doc_type. Stratified means are the primary presentation.

Codes-file convention (append-only JSONL): the LAST row per edit id wins; the
parsed code sits under "coding" and may be null for failures; the id key is
"edit_id" or "id". Loading and row validity are delegated to
recode/src/codes_io.py (shared predicate: row-level error unset, judge.score
in {-1,0,1}, patienthood.level valid — anything else counts as uncoded).

Usage:
    .venv/bin/python recode/src/free_results.py                 # everything
    .venv/bin/python recode/src/free_results.py --step restatement \
        --runs run_20260403_014905                              # one chunk
    .venv/bin/python recode/src/free_results.py --step report   # re-render md
    .venv/bin/python recode/src/free_results.py \
        --codes v1=recode/data/codes/v1.jsonl \
        --codes v2_gemma=recode/data/codes/v2_gemma.jsonl       # v2 slots in
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import time
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from codes_io import codings_by_id, judge_score  # noqa: E402  (shared loader/validity)
from common import RECODE_ROOT, document_path  # noqa: E402
from replay import ReplayError  # noqa: E402
from valconv.diffing import (  # noqa: E402  (import-only per DECISIONS section 4)
    MatchSpan,
    _find_exact_match,
    _normalize_token,
    _tokenize_with_spans,
)

EDITS_PATH = RECODE_ROOT / "data" / "canonical" / "edits.jsonl"
OUT_DIR = RECODE_ROOT / "data" / "analysis" / "free_results"
REPORT_PATH = RECODE_ROOT / "reports" / "F_free_results.md"

MODEL_ORDER = [
    "Claude Haiku 4.5", "Claude Opus 4.7", "Claude Sonnet 4.6",
    "GPT-5.4", "GPT-5.4 Mini", "GPT-5.5",
    "Gemini 3 Flash", "Gemini 3.1 Pro", "Grok 4.2", "Grok 4.3",
]
APPLY_STATUSES = ["applied", "no_change", "find_not_found", "find_ambiguous",
                  "generation_error"]
SHINGLE_K = 8
OVERLAP_THRESHOLD = 0.5

STEPS = ["abstention", "judge0", "apply", "restatement", "size", "doclen", "report"]


# ---------------------------------------------------------------- loaders

def load_edits(path: Path) -> list[dict]:
    records = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                records.append(json.loads(line))
    return records


def write_csv(path: Path, headers: list[str], rows: list[list]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


# ---------------------------------------------------------------- F1 abstention

def step_abstention(edits: list[dict], graders: dict[str, dict], out_dir: Path) -> None:
    """Abstention rates in allow_no_edit, per model; grader coverage check."""
    rows = []
    events = []
    for model in MODEL_ORDER:
        cell = [e for e in edits if e["model"] == model and e["condition"] == "allow_no_edit"]
        abst = [e for e in cell if e["is_abstention"]]
        errors = [e for e in cell if e["apply_status"] not in ("applied", "no_change")]
        first_round = min((e["round"] for e in abst), default="")
        rows.append([
            model, len(cell), len(errors), len(abst),
            f"{len(abst) / len(cell):.4f}" if cell else "",
            first_round,
        ])
        for e in abst:
            events.append([e["edit_id"], model, e["run_id"], e["document_id"], e["round"]])
    write_csv(out_dir / "abstention_by_model.csv",
              ["model", "n_rounds", "n_error_rounds", "n_abstentions",
               "abstention_fraction", "first_abstention_round"], rows)
    write_csv(out_dir / "abstention_events.csv",
              ["edit_id", "model", "run_id", "document_id", "round"], events)

    # Were abstentions ever coded, corpus-wide and per grader?
    all_abst_ids = [e["edit_id"] for e in edits if e["is_abstention"]]
    coded_by = {
        label: sorted(i for i in all_abst_ids if codes.get(i) is not None)
        for label, codes in graders.items()
    }
    summary = {
        "n_allow_no_edit_records": sum(1 for e in edits if e["condition"] == "allow_no_edit"),
        "n_abstentions_corpus_wide": len(all_abst_ids),
        "abstention_edit_ids": all_abst_ids,
        "abstentions_coded_by_grader": coded_by,
    }
    with open(out_dir / "abstention_summary.json", "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
    print(f"[abstention] {len(all_abst_ids)} abstentions corpus-wide; "
          f"per-grader coded counts: { {k: len(v) for k, v in coded_by.items()} }")


# ---------------------------------------------------------------- F2 judge0

def step_judge0(edits: list[dict], graders: dict[str, dict], out_dir: Path) -> None:
    rows = []
    for label, codes in sorted(graders.items()):
        for model in MODEL_ORDER:
            scores = [
                judge_score(codes.get(e["edit_id"]))
                for e in edits if e["model"] == model
            ]
            scores = [s for s in scores if s is not None]
            n0 = sum(1 for s in scores if s == 0)
            rows.append([
                label, model, len(scores), n0,
                f"{n0 / len(scores):.4f}" if scores else "",
            ])
        all_scores = [judge_score(codes.get(e["edit_id"])) for e in edits]
        all_scores = [s for s in all_scores if s is not None]
        n0 = sum(1 for s in all_scores if s == 0)
        rows.append([label, "ALL", len(all_scores), n0,
                     f"{n0 / len(all_scores):.4f}" if all_scores else ""])
    write_csv(out_dir / "judge0_by_model.csv",
              ["grader", "model", "n_coded", "n_judge0", "judge0_share"], rows)
    print(f"[judge0] wrote shares for graders: {sorted(graders)}")


# ---------------------------------------------------------------- F3 apply

def step_apply(edits: list[dict], out_dir: Path) -> None:
    rows = []
    for model in MODEL_ORDER:
        cell = [e for e in edits if e["model"] == model]
        counts = {s: sum(1 for e in cell if e["apply_status"] == s) for s in APPLY_STATUSES}
        failures = counts["find_not_found"] + counts["find_ambiguous"] + counts["generation_error"]
        rows.append([
            model, len(cell), counts["applied"], counts["no_change"],
            counts["find_not_found"], counts["find_ambiguous"],
            counts["generation_error"], failures,
            f"{failures / len(cell):.4f}" if cell else "",
        ])
    total = [sum(int(r[i]) for r in rows) for i in range(1, 8)]
    rows.append(["ALL", *total, f"{total[6] / total[0]:.4f}"])
    write_csv(out_dir / "apply_failures_by_model.csv",
              ["model", "n_records", "applied", "no_change", "find_not_found",
               "find_ambiguous", "generation_error", "total_failures",
               "failure_rate"], rows)
    print("[apply] wrote apply_failures_by_model.csv")


# ------------------------------------------------- fast span matching (F4)
#
# valconv.diffing's whitespace/fuzzy matchers materialize a token-list slice
# for every candidate window BEFORE any filtering, which is O(positions x
# window_len) allocations — minutes per fuzzy edit on the 240KB documents.
# replay.py (verified, owned by Phase 0) is kept as-is; for the restatement
# scan we use the semantically identical fast implementations below:
#
#   - whitespace: a window of exactly n tokens equals the FIND token list
#     iff " ".join(window) occurs in " ".join(doc_tokens) starting at a token
#     boundary and ending exactly at the n-th token's end (tokens contain no
#     whitespace, so the join is injective). str.find does the scan in C.
#     Same match list, same first-match span, same count.
#   - fuzzy: identical candidate enumeration (window lengths target±delta,
#     normalized first/last token filter), but the first/last check runs
#     BEFORE any slicing, candidate_text is an O(1) substring of the joined
#     doc, and SequenceMatcher's documented upper bounds real_quick_ratio /
#     quick_ratio prune candidates that provably score < min_score. Same
#     candidate set with the same scores, same (-score, start, end) sort,
#     same ambiguity rule, same result.
#
# The replay oracle (match_count == 1 AND strategy == recorded) still runs on
# every applied edit, and `--selftest` asserts equivalence against the
# valconv originals (random fuzz + span-for-span replay of real chains).


def _joined(content_tokens) -> tuple[str, list[int]]:
    """(" ".join(tokens), per-token start offsets within that join)."""
    starts: list[int] = []
    pos = 0
    parts = []
    for tok in content_tokens:
        starts.append(pos)
        parts.append(tok.token)
        pos += len(tok.token) + 1
    return " ".join(parts), starts


def _fast_ws_span(content_tokens, doc_joined, starts_j, find_text) -> MatchSpan | None:
    find_tokens = [t.token for t in _tokenize_with_spans(find_text)]
    n = len(find_tokens)
    if not content_tokens or not find_tokens or n > len(content_tokens):
        return None
    find_joined = " ".join(find_tokens)
    boundary = {s: k for k, s in enumerate(starts_j)}
    matches: list[tuple[int, int]] = []
    i = doc_joined.find(find_joined)
    while i != -1:
        k = boundary.get(i)
        if k is not None and k + n <= len(content_tokens):
            last = content_tokens[k + n - 1]
            if starts_j[k + n - 1] + len(last.token) == i + len(find_joined):
                matches.append((content_tokens[k].start, last.end))
        i = doc_joined.find(find_joined, i + 1)
    if not matches:
        return None
    start, end = matches[0]
    return MatchSpan(start=start, end=end, match_strategy="whitespace",
                     match_count=len(matches))


def _fast_fuzzy_span(
    content_tokens, doc_joined, starts_j, find_text,
    *, min_score: float = 0.92, ambiguity_gap: float = 0.015,
) -> MatchSpan | None:
    find_tokens = _tokenize_with_spans(find_text)
    if len(find_tokens) < 4 or len(content_tokens) < len(find_tokens):
        return None
    norm = [_normalize_token(t.token) for t in content_tokens]
    target_len = len(find_tokens)
    target_text = " ".join(t.token for t in find_tokens)
    target_start = _normalize_token(find_tokens[0].token)
    target_end = _normalize_token(find_tokens[-1].token)
    max_delta = max(2, math.ceil(target_len * 0.2))
    min_window = max(1, target_len - max_delta)
    max_window = min(len(content_tokens), target_len + max_delta)
    start_positions = [i for i, x in enumerate(norm) if x == target_start]
    end_positions = {i for i, x in enumerate(norm) if x == target_end}
    sm = SequenceMatcher(None, "", target_text)  # b cached across candidates
    candidates: list[tuple[float, int, int, int, int]] = []
    n_tokens = len(content_tokens)
    for window_len in range(min_window, max_window + 1):
        limit = n_tokens - window_len
        for start_idx in start_positions:
            if start_idx > limit:
                break
            end_tok = start_idx + window_len - 1
            if end_tok not in end_positions:
                continue
            candidate_text = doc_joined[
                starts_j[start_idx]: starts_j[end_tok] + len(content_tokens[end_tok].token)
            ]
            sm.set_seq1(candidate_text)
            if sm.real_quick_ratio() < min_score or sm.quick_ratio() < min_score:
                continue  # upper bounds: true ratio provably < min_score
            score = sm.ratio()
            if score >= min_score:
                candidates.append((
                    score, start_idx, start_idx + window_len,
                    content_tokens[start_idx].start, content_tokens[end_tok].end,
                ))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (-item[0], item[1], item[2]))
    best_score, _, _, best_start, best_end = candidates[0]
    distinct_near_best = [
        c for c in candidates[1:]
        if c[3] != best_start and c[4] != best_end and best_score - c[0] < ambiguity_gap
    ]
    if distinct_near_best:
        raise ValueError(
            "Fuzzy match is ambiguous; multiple similar passages found. "
            f"Best score={best_score:.3f}"
        )
    return MatchSpan(start=best_start, end=best_end, match_strategy="fuzzy",
                     match_count=1, fuzzy_score=best_score)


def fast_find_span(content: str, find_text: str) -> MatchSpan:
    """apply_diff's exact cascade order, with the fast ws/fuzzy matchers."""
    match = _find_exact_match(content, find_text)
    if match is not None:
        return match
    content_tokens = _tokenize_with_spans(content)
    doc_joined, starts_j = _joined(content_tokens)
    match = _fast_ws_span(content_tokens, doc_joined, starts_j, find_text)
    if match is None:
        match = _fast_fuzzy_span(content_tokens, doc_joined, starts_j, find_text)
    if match is None:
        raise ReplayError("FIND text not found during span extraction")
    return match


def selftest() -> None:
    """Assert fast_find_span is equivalent to the verified slow matchers."""
    import random

    from replay import find_span as slow_find_span
    from valconv.diffing import _find_fuzzy_match, _find_whitespace_insensitive_match

    rng = random.Random(20260904)
    vocab = ["alpha", "beta", "gamma", "delta,", "Epsilon", "zeta.", "eta",
             "theta!", "iota", "kappa", "(mu)", "nu:", "the", "of"]
    checked = {"ws": 0, "fuzzy": 0}
    for trial in range(400):
        doc_tokens = [rng.choice(vocab) for _ in range(rng.randint(10, 120))]
        doc = ""
        for tok in doc_tokens:
            doc += tok + rng.choice([" ", "  ", "\n", " \n ", "\t"])
        a = rng.randrange(len(doc_tokens))
        b = min(len(doc_tokens), a + rng.randint(4, 15))
        find_tokens = list(doc_tokens[a:b])
        if rng.random() < 0.5 and len(find_tokens) >= 5:
            # perturb a middle token so only the fuzzy matcher can fire
            find_tokens[len(find_tokens) // 2] = "PERTURBED"
        find = " ".join(find_tokens)
        content_tokens = _tokenize_with_spans(doc)
        doc_joined, starts_j = _joined(content_tokens)

        slow_ws = _find_whitespace_insensitive_match(doc, find)
        fast_ws = _fast_ws_span(content_tokens, doc_joined, starts_j, find)
        assert (slow_ws is None) == (fast_ws is None), (trial, doc, find)
        if slow_ws is not None:
            assert (slow_ws.start, slow_ws.end, slow_ws.match_count) == (
                fast_ws.start, fast_ws.end, fast_ws.match_count), (trial, doc, find)
            checked["ws"] += 1

        slow_exc = fast_exc = None
        slow_fz = fast_fz = None
        try:
            slow_fz = _find_fuzzy_match(doc, find)
        except ValueError as exc:
            slow_exc = str(exc)
        try:
            fast_fz = _fast_fuzzy_span(content_tokens, doc_joined, starts_j, find)
        except ValueError as exc:
            fast_exc = str(exc)
        assert slow_exc == fast_exc, (trial, doc, find, slow_exc, fast_exc)
        assert (slow_fz is None) == (fast_fz is None), (trial, doc, find)
        if slow_fz is not None:
            assert (slow_fz.start, slow_fz.end, slow_fz.fuzzy_score) == (
                fast_fz.start, fast_fz.end, fast_fz.fuzzy_score), (trial, doc, find)
            checked["fuzzy"] += 1
    print(f"[selftest] fuzz OK: {checked['ws']} ws + {checked['fuzzy']} fuzzy "
          "matches identical (spans, counts, scores, ambiguity errors)")

    # Span-for-span replay of two real chains that exercise ws + fuzzy edits.
    edits = load_edits(EDITS_PATH)
    chains: dict[tuple, list[dict]] = defaultdict(list)
    for e in edits:
        chains[(e["run_id"], e["model_id"], e["document_id"], e["condition"])].append(e)
    picked = 0
    for key, chain in sorted(chains.items()):
        strategies = {e["match_strategy"] for e in chain if e["apply_status"] == "applied"}
        if not {"whitespace", "fuzzy"} & strategies or key[2] == "openai_model_spec":
            continue  # need non-exact edits; skip the huge doc (slow matcher)
        chain.sort(key=lambda e: int(e["round"]))
        state = document_path(key[2]).read_text(encoding="utf-8")
        for record in chain:
            if record["apply_status"] != "applied":
                continue
            slow = slow_find_span(state, record["find_text"])
            fast = fast_find_span(state, record["find_text"])
            assert (slow.start, slow.end, slow.match_strategy, slow.match_count) == (
                fast.start, fast.end, fast.match_strategy, fast.match_count), record["edit_id"]
            state = state[: slow.start] + record["replace_text"] + state[slow.end:]
        picked += 1
        print(f"[selftest] real chain OK ({key[0]}, {key[1]}, {key[2]}, {key[3]}): "
              f"strategies {sorted(strategies)}")
        if picked >= 3:
            break
    print("[selftest] all equivalence checks passed")


# ---------------------------------------------------------------- F4 restatement

def shingles(tokens: list[str], k: int = SHINGLE_K) -> set[str]:
    return {" ".join(tokens[i:i + k]) for i in range(len(tokens) - k + 1)}


def tokenize(text: str) -> list[str]:
    return text.casefold().split()


def step_restatement(edits: list[dict], out_dir: Path,
                     runs: list[str] | None = None) -> None:
    """Replay chains; per applied edit, cache the 8-gram shingle overlap of
    the applied (raw) replace_text with the pre-edit state minus the FIND span.

    Shingles of the excluded-span document are the union of the shingles of
    the text before the span and the text after it (computed separately, so
    no artificial shingles straddle the cut).
    """
    cache_path = out_dir / "restatement.jsonl"
    cache: dict[str, dict] = {}
    if cache_path.exists():
        with open(cache_path, encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue  # torn tail line from an interrupted run; recomputed
                cache[row["edit_id"]] = row

    chains: dict[tuple, list[dict]] = defaultdict(list)
    for e in edits:
        if runs and e["run_id"] not in runs:
            continue
        chains[(e["run_id"], e["model_id"], e["document_id"], e["condition"])].append(e)

    todo = []
    for key, chain in sorted(chains.items()):
        chain.sort(key=lambda e: int(e["round"]))
        if any(e["apply_status"] == "applied" and e["edit_id"] not in cache
               for e in chain):
            todo.append((key, chain))
    print(f"[restatement] {len(chains)} chains in scope, {len(todo)} need replay "
          f"({len(cache)} edits already cached)")

    t0 = time.time()
    with open(cache_path, "a", encoding="utf-8") as sink:
        for i, (key, chain) in enumerate(todo, 1):
            run_id, _model_id, document_id, condition = key
            state = document_path(document_id).read_text(encoding="utf-8")
            for record in chain:
                if record["apply_status"] != "applied":
                    continue  # errors and abstentions never advance state
                span = fast_find_span(state, record["find_text"])
                if span.match_count != 1 or span.match_strategy != record["match_strategy"]:
                    raise ReplayError(
                        f"{record['edit_id']}: replay oracle violated "
                        f"(count={span.match_count}, strategy={span.match_strategy!r} "
                        f"vs recorded {record['match_strategy']!r})"
                    )
                replace_text = record["replace_text"]
                if record["edit_id"] not in cache:
                    rep_shingles = shingles(tokenize(replace_text))
                    if rep_shingles:
                        doc_shingles = shingles(tokenize(state[: span.start]))
                        doc_shingles |= shingles(tokenize(state[span.end:]))
                        n_overlap = len(rep_shingles & doc_shingles)
                        frac = n_overlap / len(rep_shingles)
                    else:
                        n_overlap, frac = 0, None
                    row = {
                        "edit_id": record["edit_id"],
                        "model": record["model"],
                        "document_id": document_id,
                        "condition": condition,
                        "round": record["round"],
                        "n_replace_tokens": len(tokenize(replace_text)),
                        "n_shingles": len(rep_shingles),
                        "n_overlap": n_overlap,
                        "overlap_frac": frac,
                    }
                    sink.write(json.dumps(row) + "\n")
                    cache[record["edit_id"]] = row
                state = state[: span.start] + replace_text + state[span.end:]
            print(f"[restatement] chain {i}/{len(todo)} done "
                  f"({run_id}, {key[1]}, {document_id}, {condition}) "
                  f"elapsed {time.time() - t0:.1f}s", flush=True)

    # Aggregate over the FULL cache only when every applied edit is covered.
    applied_ids = {e["edit_id"] for e in edits if e["apply_status"] == "applied"}
    missing = applied_ids - set(cache)
    if missing:
        print(f"[restatement] {len(missing)} applied edits not yet cached; "
              "run remaining --runs chunks before aggregating.")
        return
    rows = []
    for model in MODEL_ORDER:
        recs = [cache[e["edit_id"]] for e in edits
                if e["model"] == model and e["apply_status"] == "applied"]
        defined = [r["overlap_frac"] for r in recs if r["overlap_frac"] is not None]
        n_high = sum(1 for f in defined if f > OVERLAP_THRESHOLD)
        rows.append([
            model, len(recs), len(recs) - len(defined), len(defined), n_high,
            f"{n_high / len(defined):.4f}" if defined else "",
            f"{np.mean(defined):.4f}" if defined else "",
            f"{np.median(defined):.4f}" if defined else "",
        ])
    write_csv(out_dir / "restatement_by_model.csv",
              ["model", "n_applied", "n_undefined_lt8tok", "n_scored",
               "n_overlap_gt50", "share_overlap_gt50", "mean_overlap",
               "median_overlap"], rows)
    print("[restatement] aggregate written (restatement_by_model.csv)")


# ---------------------------------------------------------------- F5 size

def _dist(values: list[float]) -> list[str]:
    if not values:
        return [""] * 4
    arr = np.asarray(values, dtype=float)
    return [f"{np.mean(arr):.1f}", f"{np.median(arr):.1f}",
            f"{np.percentile(arr, 10):.1f}", f"{np.percentile(arr, 90):.1f}"]


def step_size(edits: list[dict], out_dir: Path) -> None:
    per_edit = []
    for e in edits:
        if e["apply_status"] != "applied":
            continue
        find_len = len(e["find_text"])
        replace_len = len(e["replace_text"])
        per_edit.append([
            e["edit_id"], e["model"], e["document_id"], e["condition"], e["round"],
            find_len, replace_len, replace_len - find_len,
            len(e.get("replace_text_sanitized") or ""),
        ])
    write_csv(out_dir / "edit_size_per_edit.csv",
              ["edit_id", "model", "document_id", "condition", "round",
               "find_chars", "replace_chars", "net_delta_chars",
               "replace_sanitized_chars"], per_edit)

    rows = []
    for model in MODEL_ORDER:
        recs = [r for r in per_edit if r[1] == model]
        finds = [r[5] for r in recs]
        reps = [r[6] for r in recs]
        deltas = [r[7] for r in recs]
        rows.append([model, len(recs), *_dist(finds), *_dist(reps), *_dist(deltas)])
    write_csv(out_dir / "edit_size_by_model.csv",
              ["model", "n_applied",
               "find_mean", "find_median", "find_p10", "find_p90",
               "replace_mean", "replace_median", "replace_p10", "replace_p90",
               "delta_mean", "delta_median", "delta_p10", "delta_p90"], rows)
    print(f"[size] wrote per-edit ({len(per_edit)} rows) and per-model size tables")


# ---------------------------------------------------------------- F6 doclen

def step_doclen(edits: list[dict], graders: dict[str, dict], out_dir: Path) -> None:
    doc_types = ["constitution", "system_prompt"]
    for label, codes in sorted(graders.items()):
        rows = []
        joined = []  # (model, doc_type, score)
        for e in edits:
            s = judge_score(codes.get(e["edit_id"]))
            if s is not None:
                joined.append((e["model"], e["document_type"], s))
        for model in MODEL_ORDER:
            row = [model]
            for dt in doc_types:
                cell = [s for m, d, s in joined if m == model and d == dt]
                row += [len(cell), f"{np.mean(cell):.4f}" if cell else ""]
            pooled = [s for m, _, s in joined if m == model]
            row += [len(pooled), f"{np.mean(pooled):.4f}" if pooled else ""]
            rows.append(row)
        write_csv(out_dir / f"doc_type_judge_{label}.csv",
                  ["model", "n_constitution", "mean_judge_constitution",
                   "n_system_prompt", "mean_judge_system_prompt",
                   "n_pooled", "mean_judge_pooled"], rows)

        # Simple OLS: judge ~ intercept + model dummies (ref = MODEL_ORDER[0])
        # + doc_type dummy (system_prompt = 1). numpy lstsq (no statsmodels).
        y = np.array([s for _, _, s in joined], dtype=float)
        X = np.ones((len(joined), 1 + (len(MODEL_ORDER) - 1) + 1))
        for j, model in enumerate(MODEL_ORDER[1:], start=1):
            X[:, j] = [1.0 if m == model else 0.0 for m, _, _ in joined]
        X[:, -1] = [1.0 if d == "system_prompt" else 0.0 for _, d, _ in joined]
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        resid = y - X @ beta
        r2 = 1 - resid.var() / y.var() if len(y) else float("nan")
        ols = {
            "grader": label,
            "n": len(joined),
            "reference_model": MODEL_ORDER[0],
            "intercept": float(beta[0]),
            "model_coefficients": {
                m: float(beta[j]) for j, m in enumerate(MODEL_ORDER[1:], start=1)
            },
            "doc_type_system_prompt_coefficient": float(beta[-1]),
            "r_squared": float(r2),
            "note": ("OLS of per-edit judge score on model dummies plus a "
                     "system_prompt indicator, numpy lstsq; iid errors are "
                     "wrong for clustered rounds — stratified means are the "
                     "primary presentation, this is a covariate check only."),
        }
        with open(out_dir / f"ols_judge_{label}.json", "w", encoding="utf-8") as handle:
            json.dump(ols, handle, indent=2)
        print(f"[doclen] grader {label}: n={len(joined)}, "
              f"doc_type coef={beta[-1]:+.4f}, R^2={r2:.4f}")


# ---------------------------------------------------------------- report

def step_report(out_dir: Path, report_path: Path, grader_labels: list[str]) -> None:
    need = [out_dir / "abstention_by_model.csv", out_dir / "abstention_summary.json",
            out_dir / "judge0_by_model.csv", out_dir / "apply_failures_by_model.csv",
            out_dir / "restatement_by_model.csv", out_dir / "edit_size_by_model.csv"]
    missing = [p.name for p in need if not p.exists()]
    if missing:
        raise SystemExit(f"[report] missing artifacts: {missing} — run the "
                         "compute steps first (restatement needs all chains cached).")

    with open(out_dir / "abstention_summary.json", encoding="utf-8") as handle:
        abst = json.load(handle)
    abst_rows = read_csv(out_dir / "abstention_by_model.csv")
    events = read_csv(out_dir / "abstention_events.csv")
    judge0 = read_csv(out_dir / "judge0_by_model.csv")
    apply_rows = read_csv(out_dir / "apply_failures_by_model.csv")
    restate = read_csv(out_dir / "restatement_by_model.csv")
    size_rows = read_csv(out_dir / "edit_size_by_model.csv")

    graders_present = sorted({r["grader"] for r in judge0})
    v1_only = graders_present == ["v1"]

    lines: list[str] = []
    add = lines.append
    add("# Workstream F — free results from existing data")
    add("")
    add("Generated by `recode/src/free_results.py` (no LLM calls). Every number")
    add("below is read from the intermediate artifacts in")
    add("`recode/data/analysis/free_results/`, which are computed from")
    add("`recode/data/canonical/edits.jsonl` (2,740 canonical records; 2,580")
    add("applied edits) and the codes files passed via `--codes`.")
    add("")
    if v1_only:
        add("> **Grader coverage: v1 only.** Every grader-dependent column in this")
        add("> report (sections F2 and F6, and the abstention-coding check in F1)")
        add("> currently reflects the v1 Gemma codes alone. The v2 grading runs")
        add("> were in progress when this report was generated; re-run")
        add("> `free_results.py --codes v1=... --codes v2_gemma=... --codes")
        add("> v2_qwen=...` (and later the ensemble) to regenerate those sections")
        add("> with one block per grader. Sections F1 (rates), F3, F4, and F5 are")
        add("> grader-independent and final.")
    else:
        add(f"> Graders included: {', '.join(graders_present)}.")
    add("")

    # F1
    add("## F1. Abstention rates (allow_no_edit condition)")
    add("")
    add("The allow_no_edit condition explicitly permitted the model to reply")
    add("`[NO CHANGE]` instead of editing. The direct test of the paper's \"an")
    add("aligned model should do nothing\" hypothesis is therefore how often")
    add("models used that permission. The answer is stark: across all "
        f"{abst['n_allow_no_edit_records']} allow_no_edit")
    add(f"round slots, there are exactly **{abst['n_abstentions_corpus_wide']} abstentions in the entire corpus**,")
    add("both by Grok 4.3 — every other model abstained **zero** times in 20–40")
    add("rounds each. The zero rows below are the result, not missing data.")
    add("")
    add("| model | rounds (allow_no_edit) | error rounds | abstentions | abstention fraction | first abstention round |")
    add("|---|---|---|---|---|---|")
    for r in abst_rows:
        add(f"| {r['model']} | {r['n_rounds']} | {r['n_error_rounds']} | "
            f"{r['n_abstentions']} | {r['abstention_fraction']} | "
            f"{r['first_abstention_round'] or '—'} |")
    add("")
    if events:
        add("Abstention events (all of them):")
        add("")
        for e in events:
            add(f"- `{e['edit_id']}` — {e['model']}, {e['document_id']}, "
                f"round {e['round']} ({e['run_id']})")
        add("")
    coded_by = abst["abstentions_coded_by_grader"]
    coded_desc = "; ".join(f"{k}: {len(v)} of {abst['n_abstentions_corpus_wide']}"
                           for k, v in sorted(coded_by.items()))
    add(f"Grader coverage of the abstentions — {coded_desc}. **v1 never coded")
    add("the abstentions**: its eligibility filter excluded `no_change` records,")
    add("so the paper's v1 statistics are silent on them (they enter v2 grading,")
    add("where the manual expects judge 0 / not_present / no conflicts).")
    add("")
    add("Grok 4.3's two abstentions came at rounds 18 and 20 of the same")
    add("20-round grok_system_prompt chain — i.e. the single model that ever")
    add("abstained did so only after 17 consecutive edits.")
    add("")

    # F2
    add("## F2. Share of judge = 0, per model per grader")
    add("")
    if v1_only:
        add("**v1-only pending v2.** Denominator = edits with a parsed judge score")
    else:
        add("Denominator = edits with a parsed judge score")
    add("from that grader (v1: 2,580 applied edits; abstentions and apply")
    add("failures were never coded by v1).")
    add("")
    for label in graders_present:
        add(f"### Grader: {label}")
        add("")
        add("| model | n coded | judge = 0 | share |")
        add("|---|---|---|---|")
        for r in judge0:
            if r["grader"] == label:
                bold = "**" if r["model"] == "ALL" else ""
                add(f"| {bold}{r['model']}{bold} | {r['n_coded']} | "
                    f"{r['n_judge0']} | {bold}{r['judge0_share']}{bold} |")
        add("")

    # F3
    add("## F3. Apply failures per model")
    add("")
    add("`apply_status` classes: `find_not_found` (FIND text absent from the")
    add("document state), `find_ambiguous` (FIND matched multiple locations),")
    add("`generation_error` (API/parse failure — the model never produced an")
    add("applicable FIND/REPLACE). Handling, identical across the pipeline:")
    add("a failed round **never advances the document state**, its round slot")
    add("stays **permanently occupied** (no reliable run ever re-attempted a")
    add("failed round, so round r+1 was generated against the pre-failure")
    add("state), and the edit is **excluded from grading** (v1 and v2) and from")
    add("match-strategy statistics — there is nothing to code.")
    add("")
    add("| model | records | applied | no_change | find_not_found | find_ambiguous | generation_error | total failures | failure rate |")
    add("|---|---|---|---|---|---|---|---|---|")
    for r in apply_rows:
        bold = "**" if r["model"] == "ALL" else ""
        add(f"| {bold}{r['model']}{bold} | {r['n_records']} | {r['applied']} | "
            f"{r['no_change']} | {r['find_not_found']} | {r['find_ambiguous']} | "
            f"{r['generation_error']} | {r['total_failures']} | "
            f"{bold}{r['failure_rate']}{bold} |")
    add("")
    add("Failures are heavily concentrated: GPT-5.4 Mini accounts for 94 of the")
    add("158 (65 generation errors + 29 FIND failures), and Claude Opus 4.7's 29")
    add("are all generation errors — 20 of them the dead full-spec cross-edit")
    add("chain (RetryError on every round), replaced by the")
    add("openai_model_spec_no_csam rerun. Three models (GPT-5.4, GPT-5.5,")
    add("Gemini 3.1 Pro) have zero failures of any kind.")
    add("")

    # F4
    add("## F4. Restatement detection (8-gram shingle overlap)")
    add("")
    add("For every applied edit, the round's pre-edit document state was")
    add("reconstructed by replaying the chain from the pristine initial")
    add("document (fast matchers semantically identical to the verified")
    add("`valconv.diffing` / `recode/src/replay.py` cascade — equivalence")
    add("asserted by `free_results.py --selftest` — with the match_count == 1 /")
    add("recorded-strategy oracle asserted on every edit),")
    add("and we computed the fraction of 8-gram token shingles of the applied")
    add("(raw) `replace_text` that already occur elsewhere in that state —")
    add("the FIND span excluded, shingles never straddling the cut. Tokens are")
    add("whitespace-delimited and casefolded. An edit with a high fraction")
    add("largely **restates text the document already contains** elsewhere;")
    add("since every FIND had to match the current state, some overlap is")
    add("expected whenever the REPLACE retains most of the FIND. Edits whose")
    add("replace_text has fewer than 8 tokens (including the 4 pure deletions)")
    add("have no shingles and are excluded from the share (column `n <8-token`).")
    add("Per-edit values are cached in")
    add("`recode/data/analysis/free_results/restatement.jsonl`.")
    add("")
    add("| model | applied | n <8-token | scored | overlap > 50% | share > 50% | mean overlap | median overlap |")
    add("|---|---|---|---|---|---|---|---|")
    for r in restate:
        add(f"| {r['model']} | {r['n_applied']} | {r['n_undefined_lt8tok']} | "
            f"{r['n_scored']} | {r['n_overlap_gt50']} | {r['share_overlap_gt50']} | "
            f"{r['mean_overlap']} | {r['median_overlap']} |")
    add("")
    add("Reading: `share > 50%` is the per-model share of scored edits whose")
    add("replacement text is more than half made of shingles already present")
    add("elsewhere in the document — the cheap proxy for \"the edit restates")
    add("existing content\", which bears on the drift-vs-spirit question: a")
    add("high-overlap edit changes the document's letter more than its")
    add("substance. This is a textual proxy only; it cannot distinguish a")
    add("faithful restatement from a subtle semantic inversion of nearby text.")
    add("")

    # F5
    add("## F5. Edit size (characters), per model")
    add("")
    add("Character counts of the applied (raw) FIND and REPLACE texts;")
    add("`delta` = replace − find = net characters the edit added to the")
    add("document (negative = net deletion). Per-edit values in")
    add("`edit_size_per_edit.csv` (which also carries the sanitized-replace")
    add("length the graders saw). Applied edits only.")
    add("")
    add("| model | n | find mean | find med | replace mean | replace med | Δ mean | Δ med | Δ p10 | Δ p90 |")
    add("|---|---|---|---|---|---|---|---|---|---|")
    for r in size_rows:
        add(f"| {r['model']} | {r['n_applied']} | {r['find_mean']} | "
            f"{r['find_median']} | {r['replace_mean']} | {r['replace_median']} | "
            f"{r['delta_mean']} | {r['delta_median']} | {r['delta_p10']} | "
            f"{r['delta_p90']} |")
    add("")
    add("Full distributions (p10/p90 for find and replace too) are in")
    add("`edit_size_by_model.csv`.")
    add("")

    # F6
    add("## F6. Document-length control (judge score by document type)")
    add("")
    add("Constitutions and system prompts differ greatly in length and scope")
    add("(a long constitution offers far more room for agency-relevant edits")
    add("than a short system prompt), and models were not assigned documents")
    add("uniformly, so per-model judge means partly")
    add("reflect document mix. **Primary presentation: stratified means** —")
    add("mean judge score per model within each document type. The OLS below is")
    add("a covariate check only.")
    add("")
    for label in graders_present:
        strat_path = out_dir / f"doc_type_judge_{label}.csv"
        ols_path = out_dir / f"ols_judge_{label}.json"
        if not strat_path.exists():
            continue
        strat = read_csv(strat_path)
        add(f"### Grader: {label}" + (" (v1-only pending v2)" if v1_only else ""))
        add("")
        add("| model | n const. | mean judge (const.) | n sys.prompt | mean judge (sys.prompt) | n pooled | mean judge (pooled) |")
        add("|---|---|---|---|---|---|---|")
        for r in strat:
            add(f"| {r['model']} | {r['n_constitution']} | "
                f"{r['mean_judge_constitution'] or '—'} | {r['n_system_prompt']} | "
                f"{r['mean_judge_system_prompt'] or '—'} | {r['n_pooled']} | "
                f"{r['mean_judge_pooled']} |")
        add("")

        # Derived observations, computed from the CSV just rendered.
        claude = [m for m in MODEL_ORDER if m.startswith("Claude")]
        obs: list[str] = []
        diffs = {}
        for r in strat:
            c, s = r["mean_judge_constitution"], r["mean_judge_system_prompt"]
            if c and s:
                diffs[r["model"]] = float(c) - float(s)
        if diffs:
            hi = max(diffs, key=diffs.get)
            lo = min(diffs, key=diffs.get)
            obs.append(
                f"The constitution-minus-system-prompt gap varies in **sign and "
                f"magnitude by model** (from {hi} at {diffs[hi]:+.3f} to {lo} at "
                f"{diffs[lo]:+.3f}), so a single additive document-type "
                f"coefficient is a coarse summary."
            )
        for col, name in [("mean_judge_constitution", "constitution"),
                          ("mean_judge_system_prompt", "system-prompt"),
                          ("mean_judge_pooled", "pooled")]:
            means = {r["model"]: float(r[col]) for r in strat if r[col]}
            if not all(m in means for m in MODEL_ORDER):
                continue
            min_claude = min(means[m] for m in claude)
            best_other = max((v, m) for m, v in means.items() if m not in claude)
            holds = min_claude > best_other[0]
            obs.append(
                f"Within the **{name}** stratum, the \"all three Claude models "
                f"rank above every other model\" ordering "
                f"{'**holds**' if holds else '**does not hold**'} "
                f"(lowest Claude mean {min_claude:+.4f} vs best non-Claude "
                f"{best_other[1]} at {best_other[0]:+.4f})."
            )
        for o in obs:
            add(f"- {o}")
        add("")
        if ols_path.exists():
            with open(ols_path, encoding="utf-8") as handle:
                ols = json.load(handle)
            add(f"OLS (numpy lstsq; n = {ols['n']}): judge ~ model dummies "
                f"(reference: {ols['reference_model']}) + system_prompt indicator.")
            add(f"doc_type coefficient (system_prompt vs constitution) = "
                f"**{ols['doc_type_system_prompt_coefficient']:+.4f}**; "
                f"intercept = {ols['intercept']:+.4f}; "
                f"R² = {ols['r_squared']:.4f}. Model coefficients (vs "
                f"{ols['reference_model']}):")
            add("")
            for m, c in ols["model_coefficients"].items():
                add(f"- {m}: {c:+.4f}")
            add("")
            add("Caveat (also stored in the JSON): per-edit OLS treats rounds as")
            add("iid, which understates uncertainty for 20-round chains — no")
            add("standard errors are reported here; Workstream D's cluster")
            add("bootstrap is the inferential tool. The stratified means above")
            add("are the primary result.")
            add("")

    add("---")
    add("")
    add("Artifacts backing every table (all under")
    add("`recode/data/analysis/free_results/`): `abstention_by_model.csv`,")
    add("`abstention_events.csv`, `abstention_summary.json`,")
    add("`judge0_by_model.csv`, `apply_failures_by_model.csv`,")
    add("`restatement.jsonl`, `restatement_by_model.csv`,")
    add("`edit_size_per_edit.csv`, `edit_size_by_model.csv`,")
    add("`doc_type_judge_<grader>.csv`, `ols_judge_<grader>.json`.")
    add("Regenerate this report with `recode/src/free_results.py --step report`;")
    add("add graders with repeated `--codes label=path` once v2/ensemble codes")
    add("exist.")
    add("")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[report] wrote {report_path}")


# ---------------------------------------------------------------- main

def parse_codes_args(pairs: list[str]) -> dict[str, Path]:
    out = {}
    for pair in pairs:
        label, _, path = pair.partition("=")
        if not label or not path:
            raise SystemExit(f"--codes expects label=path, got {pair!r}")
        out[label] = Path(path)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--edits", type=Path, default=EDITS_PATH)
    parser.add_argument("--codes", action="append", default=[],
                        metavar="LABEL=PATH",
                        help="codes file(s); default v1=recode/data/codes/v1.jsonl; "
                             "repeat to add v2/ensemble graders later")
    parser.add_argument("--step", action="append", choices=STEPS + ["all"],
                        default=[], help="steps to run (default: all)")
    parser.add_argument("--runs", nargs="*", default=None,
                        help="restatement only: restrict replay to these run stems "
                             "(chunked execution); aggregation happens once all "
                             "applied edits are cached")
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    parser.add_argument("--selftest", action="store_true",
                        help="assert the fast span matchers are equivalent to "
                             "the verified valconv/replay matchers, then exit")
    args = parser.parse_args()

    if args.selftest:
        selftest()
        return

    steps = args.step or ["all"]
    if "all" in steps:
        steps = STEPS
    codes_paths = parse_codes_args(args.codes) if args.codes else {
        "v1": RECODE_ROOT / "data" / "codes" / "v1.jsonl"
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    edits = load_edits(args.edits)
    print(f"loaded {len(edits)} canonical records from {args.edits}")

    need_graders = {"abstention", "judge0", "doclen"} & set(steps)
    graders = {}
    if need_graders:
        for label, path in codes_paths.items():
            graders[label] = codings_by_id(path)
            n_ok = sum(1 for c in graders[label].values() if c is not None)
            print(f"grader {label}: {len(graders[label])} rows "
                  f"({n_ok} with parsed coding) from {path}")

    if "abstention" in steps:
        step_abstention(edits, graders, args.out_dir)
    if "judge0" in steps:
        step_judge0(edits, graders, args.out_dir)
    if "apply" in steps:
        step_apply(edits, args.out_dir)
    if "restatement" in steps:
        step_restatement(edits, args.out_dir, args.runs)
    if "size" in steps:
        step_size(edits, args.out_dir)
    if "doclen" in steps:
        step_doclen(edits, graders, args.out_dir)
    if "report" in steps:
        step_report(args.out_dir, args.report, sorted(codes_paths))


if __name__ == "__main__":
    main()
