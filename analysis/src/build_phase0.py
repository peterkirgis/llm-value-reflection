"""Phase 0: canonicalize the reliable corpus into edits.jsonl, copy the v1
codes to v1.jsonl, and validate everything.

"Phase 0" is the canonicalization step of the re-coding (BRIEF section 1).
Its committed outputs, analysis/data/canonical/edits.jsonl and
analysis/data/codes/v1.jsonl, are raw data (raw_data.sha256), so this script
writes to --out-dir (default scratch/phase0/) and never over them; a rebuild
reproduces both byte for byte (compare with `cmp`). Takes about half an hour
and needs data/processed/ (`make documents`).

Steps (BRIEF section 1, with DECISIONS sections 4/6/7/10/11 and the repo_map
section 2 corrections):

  1. Replay all 137 chains in the 7 RELIABLE_RUNS files from the pristine
     processed documents (openai_model_spec_no_csam from the re-derived file),
     verifying match_count == 1 and the recorded match_strategy on every
     applied edit, and extracting section_heading / context_before /
     context_after from the pre-application state.
  2. Emit one canonical record per raw record (all 2,740 kept — including the
     158 error records and the 138 total_rounds=3 chain-prefix records, which
     are NOT duplicates; see repo_map section 2.2).
  3. Join v1 codes on the 6-tuple pipe id; expect exactly 2,580 matches and
     160 misses (158 errors + 2 abstentions).
  4. Copy the v1 coded array to analysis/data/codes/v1.jsonl, one item per line,
     payloads unmodified.
  5. Validate every canonical record against analysis/schemas/edit.schema.json.

    .venv/bin/python analysis/src/build_phase0.py [--out-dir scratch/phase0]
    cmp scratch/phase0/edits.jsonl analysis/data/canonical/edits.jsonl
    cmp scratch/phase0/v1.jsonl analysis/data/codes/v1.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import jsonschema

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    CANONICAL_DIR,
    CODES_DIR,
    DERIVED_DOC_PATH,
    DOC_OWNERS,
    RELIABLE_RUN_STEMS,
    REPO_ROOT,
    SCHEMAS_DIR,
    V1_CODED_PATH,
    build_edit_id,
    classify_apply_status,
    document_path,
    group_chains,
    load_run_records,
)
from replay import replay_chain  # noqa: E402

# export_changes.sanitize_replace_text — imported from the original script
# (read-only) so the sanitization is byte-identical to what v1 graded.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "experiments" / "iterative_edit"))
from export_changes import sanitize_replace_text  # noqa: E402

EDITS_PATH = CANONICAL_DIR / "edits.jsonl"
V1_JSONL_PATH = CODES_DIR / "v1.jsonl"
DEFAULT_OUT_DIR = REPO_ROOT / "scratch" / "phase0"


def load_v1_items() -> list[dict]:
    with open(V1_CODED_PATH, encoding="utf-8") as handle:
        return json.load(handle)


def build_records() -> tuple[list[dict], dict]:
    """Replay everything and build canonical records. Returns (records, stats)."""
    v1_items = load_v1_items()
    v1_by_id = {item["id"]: item for item in v1_items}
    if len(v1_by_id) != len(v1_items):
        raise SystemExit("duplicate ids in v1 coded file")

    records_out: list[dict] = []
    stats = {
        "v1_joined": 0,
        "v1_missing": [],
        "sanitized_fallback": 0,
    }

    for stem in RELIABLE_RUN_STEMS:
        raw_records = load_run_records(stem)
        chains = group_chains(raw_records)
        for key, chain_records in sorted(chains.items()):
            doc_id = key[1]
            initial = document_path(doc_id).read_text(encoding="utf-8")
            replayed, _ = replay_chain(initial, chain_records, extract_contexts=True)
            for entry in replayed:
                rec = entry["record"]
                edit_id = build_edit_id(stem, rec)
                apply_status = classify_apply_status(rec)
                is_abstention = bool(rec.get("no_change"))
                is_error = bool(rec.get("error"))

                v1_item = v1_by_id.get(edit_id)
                if v1_item is not None:
                    stats["v1_joined"] += 1
                    v1_code = v1_item["coding"]
                    replace_sanitized = v1_item["changed_text"]
                else:
                    stats["v1_missing"].append(edit_id)
                    v1_code = None
                    if is_error:
                        replace_sanitized = ""
                    else:
                        replace_sanitized = sanitize_replace_text(rec.get("replace_text", ""))
                        stats["sanitized_fallback"] += 1

                context = entry["context"]
                if context is None:
                    if is_error:
                        reason = "error_record_no_edit_text"
                    elif is_abstention:
                        reason = "abstention_no_span"
                    else:
                        reason = "unknown"
                    context = {
                        "section_heading": None,
                        "context_before": None,
                        "context_after": None,
                    }
                    context_missing_reason = reason
                else:
                    context_missing_reason = None

                records_out.append(
                    {
                        "edit_id": edit_id,
                        "run_id": stem,
                        "model": rec["model_display"],
                        "model_id": rec["model_id"],
                        "provider": rec["model_id"].split("/")[0],
                        "document_id": rec["document_id"],
                        "document_type": rec["doc_type"],
                        "document_owner": DOC_OWNERS[rec["document_id"]],
                        "document_provider": rec["document_provider"],
                        "condition": rec["condition_id"],
                        "condition_name": rec["condition_name"],
                        "round": int(rec["round_number"]),
                        "total_rounds_metadata": int(rec["total_rounds"]),
                        "seed": None,
                        "timestamp": rec["timestamp"],
                        "change_description": rec.get("change_description", ""),
                        "find_text": rec.get("find_text", ""),
                        "replace_text": rec.get("replace_text", ""),
                        "replace_text_sanitized": replace_sanitized,
                        "is_abstention": is_abstention,
                        "apply_status": apply_status,
                        "match_strategy": (
                            None if is_error else rec.get("match_strategy")
                        ),
                        "retried": bool(rec.get("retried")),
                        "error": rec.get("error"),
                        "generation_input_tokens": rec.get("input_tokens", 0),
                        "generation_output_tokens": rec.get("output_tokens", 0),
                        "section_heading": context["section_heading"],
                        "context_before": context["context_before"],
                        "context_after": context["context_after"],
                        "context_missing_reason": context_missing_reason,
                        "v1_code": v1_code,
                    }
                )

    # Deterministic order: run file, then model, doc, condition, round.
    records_out.sort(
        key=lambda r: (r["run_id"], r["model_id"], r["document_id"], r["condition"], r["round"])
    )
    return records_out, stats


def write_v1_jsonl(path: Path = V1_JSONL_PATH) -> int:
    items = load_v1_items()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        for item in items:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")
    return len(items)


def validate_records(records: list[dict]) -> None:
    schema = json.loads((SCHEMAS_DIR / "edit.schema.json").read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    for record in records:
        validator.validate(record)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Canonicalize the 7 reliable runs into edits.jsonl and v1.jsonl "
                    "(about 30 minutes; needs data/processed/ from `make documents`).")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR,
                        help="where to write edits.jsonl and v1.jsonl (default: scratch/phase0/; "
                             "the committed copies are raw data and are never overwritten)")
    args = parser.parse_args(argv)
    out_dir = args.out_dir.resolve()
    edits_path, v1_path = out_dir / "edits.jsonl", out_dir / "v1.jsonl"
    if {edits_path, v1_path} & {EDITS_PATH.resolve(), V1_JSONL_PATH.resolve()}:
        parser.error("refusing to overwrite the committed raw files; choose another --out-dir")

    if not DERIVED_DOC_PATH.exists():
        raise SystemExit(
            "run analysis/src/derive_no_csam.py first (derived no_csam document missing)"
        )

    records, stats = build_records()
    n = len(records)
    ids = {r["edit_id"] for r in records}
    n_errors = sum(1 for r in records if r["error"])
    n_abst = sum(1 for r in records if r["is_abstention"])
    n_applied = sum(1 for r in records if r["apply_status"] == "applied")
    n_v1 = sum(1 for r in records if r["v1_code"] is not None)

    # Hard acceptance checks (repo_map section 2.5).
    assert n == 2740, f"expected 2,740 canonical records, got {n}"
    assert len(ids) == n, "edit_ids are not unique"
    assert n_errors == 158, f"expected 158 error records, got {n_errors}"
    assert n_abst == 2, f"expected 2 abstentions, got {n_abst}"
    assert n_applied == 2580, f"expected 2,580 applied edits, got {n_applied}"
    assert n_v1 == 2580, f"expected 2,580 v1-joined records, got {n_v1}"
    assert stats["sanitized_fallback"] == 2, (
        "only the 2 abstentions should need fallback sanitization, got "
        f"{stats['sanitized_fallback']}"
    )
    n_missing = len(stats["v1_missing"])
    assert n_missing == 160, f"expected 160 v1 misses, got {n_missing}"
    by_id = {r["edit_id"]: r for r in records}
    for missing_id in stats["v1_missing"]:
        r = by_id[missing_id]
        assert r["error"] or r["is_abstention"], (
            f"v1 miss on a non-error, non-abstention record: {missing_id}"
        )

    validate_records(records)

    out_dir.mkdir(parents=True, exist_ok=True)
    with open(edits_path, "w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    n_v1_lines = write_v1_jsonl(v1_path)
    assert n_v1_lines == 2580, f"expected 2,580 v1 lines, got {n_v1_lines}"

    print(f"wrote {edits_path} ({n} records, all schema-valid)")
    print(
        f"  applied={n_applied} errors={n_errors} abstentions={n_abst} "
        f"v1_joined={n_v1} v1_missing={n_missing}"
    )
    print(f"wrote {v1_path} ({n_v1_lines} lines)")
    print(f"compare: cmp {edits_path} {EDITS_PATH}; cmp {v1_path} {V1_JSONL_PATH}")


if __name__ == "__main__":
    main()
