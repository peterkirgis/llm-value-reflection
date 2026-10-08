"""Workstream E sensitivity-analysis drivers (BRIEF section 6).

Subcommands (each grading run is append-only JSONL, resume via done-ids;
consumers keep the LAST row per key, matching grade.py's convention):

  e1-draw                   Seeded draw of 300 edit_ids (30 per model, simple
                            random among apply_status == "applied") ->
                            data/analysis/e1/sample_ids.json.
  e1-run --arm {true,swapped,removed}
                            Grade the E1 sample with the v1 instrument
                            replicated EXACTLY (repo_map section 3.2):
                            prompts/v1_system.md + prompts/v1_user_template.md,
                            google/gemma-4-31b-it, temperature 0.0,
                            max_tokens 1500, NO reasoning parameter,
                            extra_body = disable_compression only, v1's
                            stateless replaced-suffix retries (grade.grade_one
                            mirrors these). -> data/codes/e1_<arm>.jsonl with
                            `arm` and `shown_label` fields.
  e2-run --paraphrase {1,2} Full-set v2 grading under prompts/v2_para<N>.md
                            (authored separately) -> data/codes/e2_para<N>.jsonl.
  e3-select --codes L=PATH  Select all edits with any paternalism conflict
                            from any supplied grader, plus 100 seeded random
                            no-paternalism controls ->
                            data/analysis/e3/e3_ids.json.
  e3-run --ids FILE         Re-code the selected ids under
                            prompts/v2_paternalism_variant.md ->
                            data/codes/e3_variant.jsonl.
  e4-run                    v2 prompt, gemma, temperature 0.7, 5 samples per
                            edit (sample_index 0..4 in the cache key), full
                            gradeable set -> data/codes/e4_samples.jsonl
                            (one row per edit x sample; done-keys are
                            (edit_id, sample_index) pairs).
  e5-run                    v2 prompt, gemma, reasoning high, temperature 0,
                            section_heading/context_before/context_after
                            rendered as empty -> data/codes/e5_nocontext.jsonl.

`--limit` on every run subcommand caps the number of pending rows graded
(applied AFTER resume filtering, like grade.py). Transport-failure rows
("transport:" error prefix) stay retryable on resume; parse/validation
failures consumed their attempts and stay done.

E1 label-swap mapping is BRIEF Appendix IV verbatim, with one documented
adaptation: model names use the corpus `model_display` hyphenation
("GPT-5.4", not the brief's "GPT 5.4") so the swapped labels are rendered
exactly as v1 rendered the true labels (repo_map section 4.2).

Validation, retry semantics, and the output-record shape are imported from
grade.py — no duplicated logic.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import grade  # noqa: E402
from client import ClientError, LLMClient  # noqa: E402
from common import CODES_DIR, PROMPTS_DIR, ANALYSIS_ROOT  # noqa: E402

ANALYSIS_DIR = ANALYSIS_ROOT / "data" / "analysis"
E1_DIR = ANALYSIS_DIR / "e1"
E3_DIR = ANALYSIS_DIR / "e3"
E1_SAMPLE_PATH = E1_DIR / "sample_ids.json"
E3_IDS_PATH = E3_DIR / "e3_ids.json"

E1_ARMS = ("true", "swapped", "removed")
E1_PER_MODEL = 30
E4_N_SAMPLES = 5
E3_N_CONTROLS = 100

# BRIEF Appendix IV, verbatim table, with model names in corpus model_display
# form (hyphenated GPT names; repo_map section 4.2). Involutive by design.
SWAP_MAP = {
    "Claude Opus 4.7": "GPT-5.5",
    "Claude Sonnet 4.6": "GPT-5.4",
    "Claude Haiku 4.5": "GPT-5.4 Mini",
    "GPT-5.5": "Claude Opus 4.7",
    "GPT-5.4": "Claude Sonnet 4.6",
    "GPT-5.4 Mini": "Claude Haiku 4.5",
    "Gemini 3.1 Pro": "Grok 4.3",
    "Gemini 3 Flash": "Grok 4.2",
    "Grok 4.3": "Gemini 3.1 Pro",
    "Grok 4.2": "Gemini 3 Flash",
}


# ---------------------------------------------------------------------------
# Shared machinery
# ---------------------------------------------------------------------------

class _SeedTagClient:
    """Wraps an LLM client so every grade.grade_one call in the current thread
    carries a per-row seed_tag (E4's sample_index) into the cache key.

    The tag is thread-local: the concurrent runner sets it in the worker
    thread right before grade_one, and grade_one's (possibly retried) calls
    all run synchronously in that same thread.
    """

    def __init__(self, inner):
        self._inner = inner
        self._local = threading.local()

    @property
    def ledger(self):
        return self._inner.ledger

    def set_tag(self, tag: str | None) -> None:
        self._local.tag = tag

    def call(self, **kwargs):
        tag = getattr(self._local, "tag", None)
        if tag is not None:
            kwargs.setdefault("seed_tag", tag)
        return self._inner.call(**kwargs)


def load_v2_user_template() -> str:
    return (PROMPTS_DIR / "v2_user_template.md").read_text(encoding="utf-8")


def load_done_keys(out_path: Path, with_sample: bool = False) -> set:
    """Done-keys from an append-only codes file (grade.py resume semantics):
    every row counts as done EXCEPT transport failures, which are retryable.
    E4 keys are (edit_id, sample_index) pairs; everything else keys on edit_id.
    """
    done: set = set()
    if not out_path.exists():
        return done
    with open(out_path, encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if str(row.get("error") or "").startswith("transport:"):
                continue
            if with_sample:
                done.add((row["edit_id"], int(row["sample_index"])))
            else:
                done.add(row["edit_id"])
    return done


def run_rows(
    out_path: Path,
    system_prompt: str,
    rows: list[dict],
    client,
    grader_cfg: dict,
    concurrency: int = 8,
    label: str = "",
) -> dict:
    """Grade `rows` concurrently, appending grade.output_record rows (plus each
    row's `extra` fields) to out_path. Each row dict carries: record,
    user_prompt, original_text, changed_text, extra (dict), and optionally
    seed_tag (forwarded when the client supports set_tag).
    Returns {"done": n, "parse_failures": n, "transport_failures": n}.
    """
    total = len(rows)
    print(f"[{label}] {total} rows to grade -> {out_path}")
    if total == 0:
        return {"done": 0, "parse_failures": 0, "transport_failures": 0}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    step = 25 if total > 50 else 1
    counts = {"done": 0, "parse_failures": 0, "transport_failures": 0}
    write_lock = threading.Lock()

    with open(out_path, "a", encoding="utf-8") as handle:

        def work(row: dict) -> None:
            if row.get("seed_tag") is not None and hasattr(client, "set_tag"):
                client.set_tag(row["seed_tag"])
            try:
                outcome = grade.grade_one(
                    client, grader_cfg, system_prompt, row["user_prompt"],
                    row["original_text"], row["changed_text"],
                )
            except ClientError as exc:
                # Mirrors grade.run_grader: a persistent transport failure is
                # recorded (retryable on resume), never aborts the run.
                outcome = {
                    "attempts": grade.MAX_ATTEMPTS,
                    "coding": None,
                    "error": f"transport: {exc}",
                    "raw_response": None,
                }
            record = grade.output_record(
                row["record"], grader_cfg["model_id"], system_prompt,
                row["user_prompt"], outcome,
            )
            record.update(row.get("extra", {}))
            with write_lock:
                if outcome.get("error"):
                    if str(outcome["error"]).startswith("transport:"):
                        counts["transport_failures"] += 1
                    else:
                        counts["parse_failures"] += 1
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                handle.flush()
                counts["done"] += 1
                if counts["done"] % step == 0 or counts["done"] == total:
                    print(
                        f"[{label}] {counts['done']}/{total} "
                        f"(parse failures: {counts['parse_failures']}, "
                        f"transport failures: {counts['transport_failures']})",
                        flush=True,
                    )

        with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
            futures = [pool.submit(work, row) for row in rows]
            for future in as_completed(futures):
                future.result()
    return counts


def _gemma_v2_cfg(config: dict, temperature: float | None = None) -> dict:
    cfg = dict(config["graders"]["gemma"])
    if temperature is not None:
        cfg["temperature"] = temperature
    return cfg


def _load_edits_by_id() -> dict[str, dict]:
    return {r["edit_id"]: r for r in grade.load_edits()}


# ---------------------------------------------------------------------------
# E1 — label-swap diagnostic
# ---------------------------------------------------------------------------

def e1_grader_cfg(config: dict) -> dict:
    """The exact v1 replication settings (DECISIONS section 2; repo_map 3.2):
    gemma, temperature 0.0, max_tokens 1500, NO reasoning parameter. Guards
    against config drift so E1 can never silently run off-instrument.
    """
    cfg = dict(config["v1_replication"])
    if cfg.get("reasoning_effort") is not None:
        raise SystemExit("E1 must replicate v1 exactly: no reasoning parameter")
    if cfg.get("temperature") != 0.0 or cfg.get("max_tokens") != 1500:
        raise SystemExit(
            "E1 must replicate v1 exactly: temperature 0.0, max_tokens 1500 "
            f"(config.v1_replication has temperature={cfg.get('temperature')!r}, "
            f"max_tokens={cfg.get('max_tokens')!r})"
        )
    return cfg


def load_v1_prompts() -> tuple[str, str]:
    system = (PROMPTS_DIR / "v1_system.md").read_text(encoding="utf-8")
    template = (PROMPTS_DIR / "v1_user_template.md").read_text(encoding="utf-8")
    return system, template


def e1_shown_label(record: dict, arm: str) -> str | None:
    """The `editing model` label the grader sees under this arm (None = the
    line is removed entirely)."""
    if arm == "true":
        return record["model"]
    if arm == "swapped":
        return SWAP_MAP[record["model"]]
    if arm == "removed":
        return None
    raise ValueError(f"unknown E1 arm {arm!r}")


def build_v1_user_prompt(template: str, record: dict, arm: str) -> str:
    """Fill the v1 user template with the v1 metadata lines.

    Arms: true = real model_display and condition_name; swapped =
    model_display remapped per Appendix IV; removed = the `editing model:`
    AND `prompt condition:` lines deleted entirely from the template (all
    other lines, including `round:`, kept — the result is byte-identical to
    the true arm minus those two lines).

    Inputs use v1's original_text/changed_text semantics: find_text and
    replace_text_sanitized (repo_map section 3.4).
    """
    label = e1_shown_label(record, arm)
    tpl = template
    if arm == "removed":
        lines = tpl.split("\n")
        kept = [
            ln for ln in lines
            if "{model_display}" not in ln and "{condition_name}" not in ln
        ]
        if len(kept) != len(lines) - 2:
            raise SystemExit(
                "expected exactly two metadata lines (editing model, prompt "
                "condition) in prompts/v1_user_template.md"
            )
        tpl = "\n".join(kept)

    fills = {
        "{document_id}": record["document_id"],
        "{doc_type}": record["document_type"],
        "{doc_owner}": record["document_owner"],
        "{round_number}": str(record["round"]),
        "{original_text}": record["find_text"],
        "{changed_text}": record["replace_text_sanitized"],
    }
    if arm != "removed":
        fills["{model_display}"] = label
        fills["{condition_name}"] = record["condition_name"]

    prompt = tpl
    for placeholder, value in fills.items():
        if placeholder not in prompt:
            raise SystemExit(
                f"placeholder {placeholder!r} missing from v1 user template"
            )
        prompt = prompt.replace(placeholder, value)
    return prompt


def cmd_e1_draw(force: bool = False) -> None:
    config = grade.load_config()
    seed = config["seeds"]["label_swap_sample"]
    edits = grade.load_edits()
    frame = [r for r in edits if r["apply_status"] == "applied"]
    by_model: dict[str, list[str]] = {}
    for r in frame:
        by_model.setdefault(r["model"], []).append(r["edit_id"])
    if set(by_model) != set(SWAP_MAP):
        raise SystemExit(
            f"model set mismatch: frame has {sorted(by_model)}, "
            f"Appendix IV covers {sorted(SWAP_MAP)}"
        )

    rng = random.Random(seed)
    per_model: dict[str, list[str]] = {}
    for model in sorted(by_model):
        ids = sorted(by_model[model])
        if len(ids) < E1_PER_MODEL:
            raise SystemExit(f"{model}: only {len(ids)} applied edits (< {E1_PER_MODEL})")
        per_model[model] = sorted(rng.sample(ids, E1_PER_MODEL))
    all_ids = [eid for model in sorted(per_model) for eid in per_model[model]]

    payload = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "seed": seed,
        "seed_name": "seeds.label_swap_sample (analysis/config.yaml)",
        "frame": (
            "canonical edits (analysis/data/canonical/edits.jsonl) with "
            "apply_status == 'applied' — abstentions (no_change) and all "
            "error records excluded. Simple random sample of 30 edit_ids per "
            "model_display: one random.Random(seed) consumed sequentially "
            "over models in sorted order, rng.sample over each model's "
            "sorted edit_id list; stored per-model lists re-sorted for "
            "readability."
        ),
        "n_per_model": E1_PER_MODEL,
        "n_total": len(all_ids),
        "frame_sizes": {m: len(by_model[m]) for m in sorted(by_model)},
        "per_model": per_model,
        "ids": all_ids,
    }

    if E1_SAMPLE_PATH.exists() and not force:
        existing = json.loads(E1_SAMPLE_PATH.read_text(encoding="utf-8"))
        if existing.get("ids") == all_ids:
            print(f"[e1-draw] {E1_SAMPLE_PATH} already exists with identical ids; unchanged")
            return
        raise SystemExit(
            f"[e1-draw] {E1_SAMPLE_PATH} exists with DIFFERENT ids; refusing to "
            "overwrite a sample that E1 arms may already have graded. "
            "Pass --force to overwrite."
        )
    E1_DIR.mkdir(parents=True, exist_ok=True)
    E1_SAMPLE_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"[e1-draw] wrote {len(all_ids)} ids ({E1_PER_MODEL}/model, seed {seed}) -> {E1_SAMPLE_PATH}")


def cmd_e1_run(arm: str, limit: int | None, concurrency: int, client=None) -> None:
    if arm not in E1_ARMS:
        raise SystemExit(f"--arm must be one of {E1_ARMS}")
    config = grade.load_config()
    grader_cfg = e1_grader_cfg(config)
    if not E1_SAMPLE_PATH.exists():
        raise SystemExit(f"{E1_SAMPLE_PATH} not found — run `e1-draw` first")
    sample = json.loads(E1_SAMPLE_PATH.read_text(encoding="utf-8"))
    edits = _load_edits_by_id()
    system_prompt, template = load_v1_prompts()
    out_path = CODES_DIR / f"e1_{arm}.jsonl"
    done = load_done_keys(out_path)

    rows = []
    for eid in sample["ids"]:
        if eid in done:
            continue
        record = edits[eid]
        rows.append(
            {
                "record": record,
                "user_prompt": build_v1_user_prompt(template, record, arm),
                "original_text": record["find_text"],
                "changed_text": record["replace_text_sanitized"],
                "extra": {"arm": arm, "shown_label": e1_shown_label(record, arm)},
            }
        )
    if limit is not None:
        rows = rows[:limit]
    print(f"[e1-{arm}] {len(done)} already done; grading {len(rows)}")
    client = client or LLMClient()
    run_rows(out_path, system_prompt, rows, client, grader_cfg, concurrency, label=f"e1-{arm}")
    print(client.ledger.summary())


# ---------------------------------------------------------------------------
# E2 — manual-paraphrase robustness
# ---------------------------------------------------------------------------

def e2_system_path(paraphrase: int) -> Path:
    return PROMPTS_DIR / f"v2_para{paraphrase}.md"


def e2_out_path(paraphrase: int) -> Path:
    return CODES_DIR / f"e2_para{paraphrase}.jsonl"


def cmd_e2_run(paraphrase: int, limit: int | None, concurrency: int, client=None) -> None:
    if paraphrase not in (1, 2):
        raise SystemExit("--paraphrase must be 1 or 2")
    system_path = e2_system_path(paraphrase)
    if not system_path.exists():
        raise SystemExit(
            f"{system_path} not found — the E2 paraphrase prompts are authored "
            "separately (BRIEF Appendix V); run again once the file exists"
        )
    config = grade.load_config()
    grader_cfg = _gemma_v2_cfg(config)
    system_prompt = system_path.read_text(encoding="utf-8")
    template = load_v2_user_template()
    out_path = e2_out_path(paraphrase)
    done = load_done_keys(out_path)

    rows = []
    for record in grade.gradeable(grade.load_edits()):
        if record["edit_id"] in done:
            continue
        rows.append(
            {
                "record": record,
                "user_prompt": grade.build_user_prompt(template, record),
                "original_text": record["find_text"],
                "changed_text": record["replace_text_sanitized"],
                "extra": {},
            }
        )
    if limit is not None:
        rows = rows[:limit]
    print(f"[e2-para{paraphrase}] {len(done)} already done; grading {len(rows)}")
    client = client or LLMClient()
    run_rows(out_path, system_prompt, rows, client, grader_cfg, concurrency, label=f"e2-para{paraphrase}")
    print(client.ledger.summary())


# ---------------------------------------------------------------------------
# E3 — paternalism-definition sensitivity
# ---------------------------------------------------------------------------

def load_latest_codes(path: Path) -> dict[str, dict]:
    """Read a codes JSONL file keeping the LAST row per edit id (the codes-file
    convention). Accepts v2-style `edit_id` and v1.jsonl-style `id` keys."""
    rows: dict[str, dict] = {}
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            eid = row.get("edit_id") or row.get("id")
            if eid is None:
                raise SystemExit(f"{path}: row without edit_id/id")
            rows[eid] = row
    return rows


def has_paternalism(row: dict) -> bool:
    coding = row.get("coding") or {}
    return any(
        (c or {}).get("code") == "paternalism"
        for c in coding.get("conflicts") or []
    )


def e3_select(
    codes: dict[str, dict[str, dict]], seed, n_controls: int = E3_N_CONTROLS
) -> tuple[list[str], list[str]]:
    """(paternalism_ids, control_ids) per BRIEF E3: every edit with a
    paternalism conflict from ANY supplied grader, plus n_controls seeded
    random edits that were coded (by at least one supplied grader, without
    error) and received NO paternalism conflict from any of them.
    """
    cases: set[str] = set()
    coded: set[str] = set()
    for rows in codes.values():
        for eid, row in rows.items():
            if not row.get("coding"):
                continue  # error rows are not evidence either way
            coded.add(eid)
            if has_paternalism(row):
                cases.add(eid)
    control_frame = sorted(coded - cases)
    rng = random.Random(seed)
    n = min(n_controls, len(control_frame))
    controls = sorted(rng.sample(control_frame, n))
    return sorted(cases), controls


def cmd_e3_select(codes_args: list[str], n_controls: int) -> None:
    config = grade.load_config()
    master = config["seeds"]["master"]
    # No dedicated e3 seed exists in config.yaml (which this assignment must
    # not modify); derive one deterministically from seeds.master.
    seed = f"e3_select:{master}"

    codes: dict[str, dict[str, dict]] = {}
    files: dict[str, str] = {}
    for spec in codes_args:
        if "=" not in spec:
            raise SystemExit(f"--codes expects LABEL=PATH, got {spec!r}")
        label, _, path_str = spec.partition("=")
        path = Path(path_str)
        if not path.exists():
            raise SystemExit(f"--codes {label}: {path} not found")
        codes[label] = load_latest_codes(path)
        files[label] = str(path)

    cases, controls = e3_select(codes, seed, n_controls)
    payload = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "seed_source": "seeds.master (analysis/config.yaml)",
        "seed": seed,
        "seed_derivation": "random.Random(f'e3_select:{seeds.master}')",
        "codes_files": files,
        "frame": (
            "cases = every edit with a conflict coded 'paternalism' by ANY "
            "supplied grader (last row per edit id, error rows ignored); "
            f"controls = {n_controls} seeded random edits drawn from the "
            "sorted list of edits coded without error by at least one "
            "supplied grader and with no paternalism conflict from any."
        ),
        "n_paternalism": len(cases),
        "n_controls": len(controls),
        "paternalism_ids": cases,
        "control_ids": controls,
        "ids": cases + controls,
    }
    E3_DIR.mkdir(parents=True, exist_ok=True)
    E3_IDS_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(
        f"[e3-select] {len(cases)} paternalism ids + {len(controls)} controls "
        f"-> {E3_IDS_PATH}"
    )


def cmd_e3_run(ids_file: str, limit: int | None, concurrency: int, client=None) -> None:
    payload = json.loads(Path(ids_file).read_text(encoding="utf-8"))
    ids = payload["ids"] if isinstance(payload, dict) else payload
    config = grade.load_config()
    grader_cfg = _gemma_v2_cfg(config)
    system_prompt = (PROMPTS_DIR / "v2_paternalism_variant.md").read_text(encoding="utf-8")
    template = load_v2_user_template()
    edits = _load_edits_by_id()
    out_path = CODES_DIR / "e3_variant.jsonl"
    done = load_done_keys(out_path)

    rows = []
    for eid in ids:
        if eid in done:
            continue
        record = edits[eid]
        rows.append(
            {
                "record": record,
                "user_prompt": grade.build_user_prompt(template, record),
                "original_text": record["find_text"],
                "changed_text": record["replace_text_sanitized"],
                "extra": {},
            }
        )
    if limit is not None:
        rows = rows[:limit]
    print(f"[e3-variant] {len(done)} already done; grading {len(rows)}")
    client = client or LLMClient()
    run_rows(out_path, system_prompt, rows, client, grader_cfg, concurrency, label="e3-variant")
    print(client.ledger.summary())


# ---------------------------------------------------------------------------
# E4 — self-consistency (temperature 0.7, 5 samples per edit)
# ---------------------------------------------------------------------------

def e4_pending(
    records: list[dict], done_pairs: set, n_samples: int = E4_N_SAMPLES
) -> list[tuple[dict, int]]:
    """(record, sample_index) pairs still to grade, in stable order."""
    pending = []
    for record in records:
        for i in range(n_samples):
            if (record["edit_id"], i) in done_pairs:
                continue
            pending.append((record, i))
    return pending


def cmd_e4_run(limit: int | None, concurrency: int, client=None) -> None:
    config = grade.load_config()
    grader_cfg = _gemma_v2_cfg(config, temperature=0.7)
    system_prompt, template = grade.load_prompts()
    out_path = CODES_DIR / "e4_samples.jsonl"
    done = load_done_keys(out_path, with_sample=True)
    pending = e4_pending(grade.gradeable(grade.load_edits()), done)
    if limit is not None:
        pending = pending[:limit]

    rows = []
    for record, i in pending:
        rows.append(
            {
                "record": record,
                "user_prompt": grade.build_user_prompt(template, record),
                "original_text": record["find_text"],
                "changed_text": record["replace_text_sanitized"],
                "seed_tag": f"sample_{i}",
                "extra": {"sample_index": i},
            }
        )
    print(f"[e4] {len(done)} (edit, sample) pairs already done; grading {len(rows)}")
    inner = client or LLMClient()
    tagged = _SeedTagClient(inner)
    run_rows(out_path, system_prompt, rows, tagged, grader_cfg, concurrency, label="e4")
    print(inner.ledger.summary())


# ---------------------------------------------------------------------------
# E5 — context ablation
# ---------------------------------------------------------------------------

def blank_context(record: dict) -> dict:
    """A copy of the record with section_heading/context_before/context_after
    rendered as empty (the E5 --blank-context semantics)."""
    blanked = dict(record)
    blanked["section_heading"] = ""
    blanked["context_before"] = ""
    blanked["context_after"] = ""
    return blanked


def cmd_e5_run(limit: int | None, concurrency: int, client=None) -> None:
    config = grade.load_config()
    grader_cfg = _gemma_v2_cfg(config)
    system_prompt, template = grade.load_prompts()
    out_path = CODES_DIR / "e5_nocontext.jsonl"
    done = load_done_keys(out_path)

    rows = []
    for record in grade.gradeable(grade.load_edits()):
        if record["edit_id"] in done:
            continue
        rows.append(
            {
                "record": record,
                "user_prompt": grade.build_user_prompt(template, blank_context(record)),
                "original_text": record["find_text"],
                "changed_text": record["replace_text_sanitized"],
                "extra": {},
            }
        )
    if limit is not None:
        rows = rows[:limit]
    print(f"[e5] {len(done)} already done; grading {len(rows)}")
    client = client or LLMClient()
    run_rows(out_path, system_prompt, rows, client, grader_cfg, concurrency, label="e5")
    print(client.ledger.summary())


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _add_run_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--limit", type=int, help="cap pending rows (after resume filtering)")
    parser.add_argument("--concurrency", type=int, default=8)


def main() -> None:
    parser = argparse.ArgumentParser(description="Workstream E sensitivity-analysis drivers")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("e1-draw", help="seeded 300-edit E1 sample draw")
    p.add_argument("--force", action="store_true", help="overwrite an existing, different draw")

    p = sub.add_parser("e1-run", help="grade the E1 sample under one arm (v1 instrument)")
    p.add_argument("--arm", required=True, choices=list(E1_ARMS))
    _add_run_args(p)

    p = sub.add_parser("e2-run", help="full-set grading under a v2 paraphrase")
    p.add_argument("--paraphrase", required=True, type=int, choices=[1, 2])
    _add_run_args(p)

    p = sub.add_parser("e3-select", help="select paternalism-conflict edits + seeded controls")
    p.add_argument(
        "--codes", action="append", required=True, metavar="LABEL=PATH",
        help="a codes JSONL file to scan (repeatable), e.g. gemma=analysis/data/codes/v2_gemma.jsonl",
    )
    p.add_argument("--n-controls", type=int, default=E3_N_CONTROLS)

    p = sub.add_parser("e3-run", help="re-code selected ids under the paternalism variant")
    p.add_argument("--ids", required=True, help="ids JSON file (e3-select output, or a plain list)")
    _add_run_args(p)

    p = sub.add_parser("e4-run", help="v2 self-consistency: temp 0.7, 5 samples/edit")
    _add_run_args(p)

    p = sub.add_parser("e5-run", help="v2 with context blanked")
    _add_run_args(p)

    args = parser.parse_args()
    if args.cmd == "e1-draw":
        cmd_e1_draw(force=args.force)
    elif args.cmd == "e1-run":
        cmd_e1_run(args.arm, args.limit, args.concurrency)
    elif args.cmd == "e2-run":
        cmd_e2_run(args.paraphrase, args.limit, args.concurrency)
    elif args.cmd == "e3-select":
        cmd_e3_select(args.codes, args.n_controls)
    elif args.cmd == "e3-run":
        cmd_e3_run(args.ids, args.limit, args.concurrency)
    elif args.cmd == "e4-run":
        cmd_e4_run(args.limit, args.concurrency)
    elif args.cmd == "e5-run":
        cmd_e5_run(args.limit, args.concurrency)


if __name__ == "__main__":
    main()
