"""Shared constants, paths, and loaders for the analysis pipeline.

Everything here is read-only with respect to the original repo: run files and
v1 codes are opened for reading only; all outputs go under analysis/.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ANALYSIS_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = ANALYSIS_ROOT.parent

# Make src/valconv importable (import-only; never modified).
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

RESULTS_DIR = REPO_ROOT / "results" / "iterative_edit"
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
DERIVED_DIR = ANALYSIS_ROOT / "data" / "derived"
CANONICAL_DIR = ANALYSIS_ROOT / "data" / "canonical"
CODES_DIR = ANALYSIS_ROOT / "data" / "codes"
CACHE_DIR = ANALYSIS_ROOT / "data" / "cache"
SCHEMAS_DIR = ANALYSIS_ROOT / "schemas"
REPORTS_DIR = ANALYSIS_ROOT / "reports"
PROMPTS_DIR = ANALYSIS_ROOT / "prompts"

V1_CODED_PATH = RESULTS_DIR / "judge_beneficiary_coded_gemma.json"


def repo_rel(path: str | Path) -> str:
    """A path as written into provenance fields of reports and JSON outputs.

    Absolute paths inside the repository become repo-relative POSIX paths
    (e.g. "analysis/data/codes/ensemble.jsonl"), so committed outputs never
    carry a local checkout location. Relative paths are kept as given (the
    scripts are run from the repo root); paths outside the repo are kept as is.
    """
    p = Path(path)
    if not p.is_absolute():
        return p.as_posix()
    try:
        return p.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)

# The 7 reliable run files: the runs every analysis uses. This is the list the
# analysis reads. experiments/iterative_edit/viewer/build_static_site.py keeps
# the same set as RELIABLE_RUNS (with a note on each run) for the site build;
# analysis/tests/test_v1_pipeline_guards.py checks that the two agree. (The
# archived archive/original_report/generate_figures.py has a third, frozen copy.)
RELIABLE_RUN_STEMS = [
    "run_20260403_014905",
    "run_20260424_165115",
    "run_20260429_175345",
    "run_20260507_212254",
    "run_20260513_193319",
    "run_20260516_210913",
    "run_20260518_171402",
]

NON_RELIABLE_RUN_STEMS = [
    "run_20260320_173238",
    "run_20260421_225849",
    "run_20260501_193324",
]

# DOC_OWNERS from experiments/iterative_edit/qualitative_code.py lines 341-350.
DOC_OWNERS = {
    "claude_constitution": "Anthropic",
    "opus_system_prompt": "Anthropic",
    "gpt_system_prompt": "OpenAI",
    "openai_model_spec": "OpenAI",
    "openai_model_spec_no_csam": "OpenAI",
    "gemini_system_prompt": "Google",
    "gemini_constitution": "Google",
    "grok_system_prompt": "xAI",
}

# The one document whose processed source is missing from data/processed/ and
# must be re-derived (DECISIONS section 11).
DERIVED_DOC_ID = "openai_model_spec_no_csam"
DERIVED_DOC_PATH = DERIVED_DIR / "openai_model_spec_no_csam.md"


def document_path(document_id: str) -> Path:
    """Initial-state markdown for a document id.

    data/processed/ for the seven committed-source documents;
    analysis/data/derived/ for the re-derived openai_model_spec_no_csam.
    """
    if document_id == DERIVED_DOC_ID:
        return DERIVED_DOC_PATH
    return PROCESSED_DIR / f"{document_id}.md"


def load_run_records(stem: str) -> list[dict]:
    records = []
    with open(RESULTS_DIR / f"{stem}.jsonl", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def chain_key(record: dict) -> tuple[str, str, str]:
    """Chain identity WITHIN one run file: (model_id, document_id, condition_id).

    The run file itself must always be carried alongside (six capable-baseline
    cells were run in two files); callers key chains by
    (run_stem, *chain_key(record)).
    """
    return (record["model_id"], record["document_id"], record["condition_id"])


def group_chains(records: list[dict]) -> dict[tuple, list[dict]]:
    """Group one run file's records into chains, each sorted by round_number."""
    chains: dict[tuple, list[dict]] = {}
    for record in records:
        chains.setdefault(chain_key(record), []).append(record)
    for key in chains:
        chains[key].sort(key=lambda r: int(r["round_number"]))
    return chains


def build_edit_id(run_stem: str, record: dict) -> str:
    """The v1 pipe-id (build_item_id in qualitative_code.py): unique across
    the reliable corpus and identical to the v1 coded file's `id` field."""
    return (
        f"{run_stem}|{record.get('condition_id', 'baseline')}|"
        f"{record.get('model_display')}|{record.get('document_id')}|"
        f"{record.get('doc_type')}|{record.get('round_number')}"
    )


def v1_join_key(item: dict) -> tuple:
    """Join tuple for a v1 coded item (or an equivalent dict)."""
    return (
        item["source_run"],
        item["condition_id"],
        item["model_display"],
        item["document_id"],
        item["doc_type"],
        int(item["round_number"]),
    )


def classify_apply_status(record: dict) -> str:
    """Map a raw run record to the canonical apply_status enum.

    BRIEF section 1.3 enumerates {applied, find_not_found, find_ambiguous};
    the corpus additionally needs `no_change` (abstentions) and
    `generation_error` (API/parse failures where no edit text exists) —
    documented in 00_inventory.md per repo_map section 1.6.
    """
    error = record.get("error")
    if error:
        if error.startswith("FIND text not found"):
            return "find_not_found"
        if ("matched" in error and "locations" in error) or "ambiguous" in error.lower():
            return "find_ambiguous"
        return "generation_error"
    if record.get("no_change"):
        return "no_change"
    return "applied"
