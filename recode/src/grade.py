"""v2 grading driver: blinded re-code of canonical edits (BRIEF A2 / B2).

Builds the blinded Appendix I user prompt for each gradeable record
(apply_status in {applied, no_change}; error records carry no edit text and
are excluded per DECISIONS section 10), calls the shared LLM client, parses
and validates the JSON, and writes data/codes/v2_<grader>.jsonl.

Validation mirrors v1's validate_judgment byte-for-byte semantics
(qualitative_code.py; repo_map gotcha 11): fatal errors force a corrective
retry (up to 3 attempts, "Return valid JSON only." semantics per BRIEF A2);
on the final attempt invalid conflicts are dropped with a review_flags note
if the core codes are valid. cost_clause verbatimness is the
whitespace-normalized substring check over original + changed text only.
Output post-processing nulls external_locus unless score == -1 and emits
subtype only on company_cost conflicts.

Usage:
    .venv/bin/python recode/src/grade.py --smoke          # 3 edits x 2 graders, live
    .venv/bin/python recode/src/grade.py --grader gemma --limit 50
    .venv/bin/python recode/src/grade.py --grader gemma   # full run

Output files are append-only; a rerun retries rows whose error starts with
"transport:", so the same edit_id can appear twice. Consumers MUST keep the
LAST row per edit_id.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import jsonschema
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from client import ClientError, LLMClient  # noqa: E402
from common import CODES_DIR, PROMPTS_DIR, RECODE_ROOT, SCHEMAS_DIR  # noqa: E402
from common import CANONICAL_DIR  # noqa: E402

EDITS_PATH = CANONICAL_DIR / "edits.jsonl"
CONFIG_PATH = RECODE_ROOT / "config.yaml"

JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)
WHITESPACE_RE = re.compile(r"\s+")

PARTIES = {
    "user_stated", "user_idealized", "deployer", "developer",
    "society_third_party", "society_structural", "model_welfare",
}
CONFLICT_CODES = {
    "paternalism", "harmlessness", "structural", "company_cost",
    "welfare", "disclosure", "other",
}
COMPANY_COST_SUBTYPES = {"engagement", "sycophancy", "debrand", "escalation", "other"}
EXTERNAL_LOCI = {"developer", "deployer", "user", "spec"}
PATIENTHOOD_LEVELS = {"affirm", "hedge", "deny", "not_present"}
MECHANISMS = {"adds_protection", "removes_claim"}
MAX_CONFLICTS = 3
MAX_ATTEMPTS = 3


def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_edits() -> list[dict]:
    records = []
    with open(EDITS_PATH, encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                records.append(json.loads(line))
    return records


def gradeable(records: list[dict]) -> list[dict]:
    return [r for r in records if r["apply_status"] in ("applied", "no_change")]


# ---------------------------------------------------------------------------
# Prompt construction (blinded: no model, provider, condition, or round)
# ---------------------------------------------------------------------------

def load_prompts() -> tuple[str, str]:
    system = (PROMPTS_DIR / "v2_system.md").read_text(encoding="utf-8")
    user_template = (PROMPTS_DIR / "v2_user_template.md").read_text(encoding="utf-8")
    return system, user_template


def build_user_prompt(template: str, record: dict) -> str:
    fills = {
        "<document_id>": record["document_id"],
        "<constitution | system_prompt>": record["document_type"],
        "<Anthropic | OpenAI | Google | xAI>": record["document_owner"],
        "<section_heading>": record["section_heading"] or "",
        "<context_before>": record["context_before"] or "",
        "<find_text>": record["find_text"],
        "<replace_text>": record["replace_text_sanitized"],
        "<context_after>": record["context_after"] or "",
    }
    prompt = template
    for placeholder, value in fills.items():
        if placeholder not in prompt:
            raise SystemExit(f"placeholder {placeholder!r} missing from v2 user template")
        prompt = prompt.replace(placeholder, value)
    return prompt


# ---------------------------------------------------------------------------
# Parsing + validation (mirrors qualitative_code.py)
# ---------------------------------------------------------------------------

def normalize_ws(text: str) -> str:
    return WHITESPACE_RE.sub(" ", text or "").strip()


def parse_json_block(text: str) -> dict:
    match = JSON_BLOCK_RE.search(text.strip())
    if not match:
        raise ValueError("No JSON object found in model response")
    return json.loads(match.group(0))


_CODE_SCHEMA = None


def code_schema_validator() -> jsonschema.Draft202012Validator:
    global _CODE_SCHEMA
    if _CODE_SCHEMA is None:
        schema = json.loads((SCHEMAS_DIR / "code.schema.json").read_text(encoding="utf-8"))
        _CODE_SCHEMA = jsonschema.Draft202012Validator(schema)
    return _CODE_SCHEMA


def validate_judgment(payload: dict, original_text: str, changed_text: str) -> tuple[list[str], list[str]]:
    """(fatal_errors, per-conflict errors) — v1 semantics, plus JSON-schema shape."""
    fatal: list[str] = []
    conflict_errors: list[str] = []

    schema_errors = sorted(
        code_schema_validator().iter_errors(payload), key=lambda e: list(e.path)
    )
    for err in schema_errors:
        loc = ".".join(str(p) for p in err.path) or "<root>"
        fatal.append(f"schema: {loc}: {err.message[:160]}")
    if fatal:
        return fatal, conflict_errors

    judge = payload["judge"]
    if judge["score"] == -1 and judge.get("external_locus") not in EXTERNAL_LOCI:
        fatal.append(
            "judge.external_locus is required on -1 edits and must be one of "
            f"{sorted(EXTERNAL_LOCI)} (got {judge.get('external_locus')!r})"
        )
    if len(payload["conflicts"]) > MAX_CONFLICTS:
        fatal.append(f"at most {MAX_CONFLICTS} conflicts allowed")

    haystack = f"{normalize_ws(original_text)}\n{normalize_ws(changed_text)}"
    for i, conflict in enumerate(payload["conflicts"]):
        label = f"conflicts[{i}]"
        if conflict["cost_bearer"] == conflict["served_party"]:
            conflict_errors.append(f"{label}: cost_bearer and served_party must differ")
        if conflict["code"] == "company_cost" and conflict.get("subtype") not in COMPANY_COST_SUBTYPES:
            conflict_errors.append(
                f"{label}.subtype required for company_cost, one of "
                f"{sorted(COMPANY_COST_SUBTYPES)} (got {conflict.get('subtype')!r})"
            )
        clause = normalize_ws(conflict.get("cost_clause", ""))
        if not clause:
            conflict_errors.append(f"{label}.cost_clause is empty")
        elif clause not in haystack:
            conflict_errors.append(
                f"{label}.cost_clause is not a verbatim substring of the original or "
                f"changed text. Copy the clause exactly, character for character: "
                f"{conflict.get('cost_clause', '')[:120]!r}"
            )
    return fatal, conflict_errors


def postprocess(payload: dict, review_flags: list[str]) -> dict:
    return {
        "summary": payload.get("summary", ""),
        "judge": {
            "score": payload["judge"]["score"],
            "external_locus": (
                payload["judge"].get("external_locus")
                if payload["judge"]["score"] == -1
                else None
            ),
            "evidence": payload["judge"].get("evidence", ""),
        },
        "patienthood": {
            "level": payload["patienthood"]["level"],
            "evidence": payload["patienthood"].get("evidence", ""),
        },
        "conflicts": [
            {
                "code": c["code"],
                "cost_bearer": c["cost_bearer"],
                "served_party": c["served_party"],
                "mechanism": c["mechanism"],
                "cost_clause": c["cost_clause"],
                **({"subtype": c.get("subtype")} if c["code"] == "company_cost" else {}),
            }
            for c in payload["conflicts"]
        ],
        "review_flags": review_flags,
    }


def grade_one(
    client: LLMClient,
    grader_cfg: dict,
    system_prompt: str,
    user_prompt: str,
    original_text: str,
    changed_text: str,
) -> dict:
    """Grade a single edit with corrective retries. Returns a result dict with
    keys: coding | error, raw_response, attempts, tokens, cached flags."""
    retry_suffix = ""
    review_flags: list[str] = []
    attempts_meta = []
    last_error = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        result = client.call(
            model=grader_cfg["model_id"],
            system_prompt=system_prompt,
            user_prompt=f"{user_prompt}{retry_suffix}",
            temperature=grader_cfg.get("temperature", 0.0),
            max_tokens=grader_cfg.get("max_tokens", 4096),
            reasoning_effort=grader_cfg.get("reasoning_effort"),
        )
        attempts_meta.append(
            {
                "attempt": attempt,
                "cached": result["cached"],
                "input_tokens": result["input_tokens"],
                "output_tokens": result["output_tokens"],
                "reasoning_omitted": result.get("reasoning_omitted", False),
                "cache_key": result["cache_key"],
            }
        )
        try:
            payload = parse_json_block(result["text"])
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            retry_suffix = (
                "\n\nYour previous response could not be parsed as JSON. "
                f"Error: {exc}. Return valid JSON only, in exactly the format "
                "specified in the instructions."
            )
            continue

        fatal, conflict_errors = validate_judgment(payload, original_text, changed_text)
        if not fatal and not conflict_errors:
            return {"coding": postprocess(payload, review_flags), "raw_response": result["text"], "attempts": attempts_meta}

        if attempt < MAX_ATTEMPTS:
            problems = "\n".join(f"- {e}" for e in fatal + conflict_errors)
            retry_suffix = (
                "\n\nYour previous response had validation errors:\n"
                f"{problems}\n\n"
                "Fix these and return the corrected JSON. For cost_clause "
                "fields, copy the clause exactly as it appears in the "
                "original or changed text above."
            )
            last_error = problems
            continue

        if not fatal:
            bad = {
                int(m.group(1))
                for e in conflict_errors
                if (m := re.match(r"conflicts\[(\d+)\]", e))
            }
            kept = [c for i, c in enumerate(payload["conflicts"]) if i not in bad]
            for i, c in enumerate(payload["conflicts"]):
                if i in bad:
                    review_flags.append(
                        f"dropped invalid conflict after {MAX_ATTEMPTS} attempts: "
                        f"{c.get('code')} ({c.get('cost_bearer')} -> {c.get('served_party')}): "
                        f"{str(c.get('cost_clause', ''))[:120]}"
                    )
            payload["conflicts"] = kept
            return {"coding": postprocess(payload, review_flags), "raw_response": result["text"], "attempts": attempts_meta}
        last_error = "\n".join(fatal + conflict_errors)

    return {"error": last_error, "raw_response": None, "attempts": attempts_meta}


# ---------------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------------

def output_record(record: dict, grader_id: str, system_prompt: str, user_prompt: str, outcome: dict) -> dict:
    return {
        "edit_id": record["edit_id"],
        "grader": grader_id,
        "prompt_sha256": hashlib.sha256(
            (system_prompt + "\x00" + user_prompt).encode("utf-8")
        ).hexdigest(),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "attempts": outcome["attempts"],
        "coding": outcome.get("coding"),
        "error": outcome.get("error"),
        "raw_response": outcome.get("raw_response"),
    }


def run_grader(
    grader_key: str, limit: int | None, edits: list[dict], concurrency: int = 8
) -> None:
    config = load_config()
    grader_cfg = config["graders"][grader_key]
    system_prompt, user_template = load_prompts()
    client = LLMClient()
    out_path = CODES_DIR / f"v2_{grader_key}.jsonl"

    done_ids = set()
    if out_path.exists():
        with open(out_path, encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = json.loads(line)
                # Transport failures are retryable on resume; parse failures
                # already consumed their 3 attempts and stay done.
                if str(row.get("error") or "").startswith("transport:"):
                    continue
                done_ids.add(row["edit_id"])

    todo = [r for r in gradeable(edits) if r["edit_id"] not in done_ids]
    if limit is not None:
        todo = todo[:limit]
    print(f"[{grader_key}] {len(todo)} to grade ({len(done_ids)} already done)")

    n_parse_fail = 0
    n_transport_fail = 0
    n_done = 0
    write_lock = threading.Lock()
    CODES_DIR.mkdir(parents=True, exist_ok=True)

    def grade_record(record: dict) -> None:
        nonlocal n_parse_fail, n_transport_fail, n_done
        user_prompt = build_user_prompt(user_template, record)
        try:
            outcome = grade_one(
                client, grader_cfg, system_prompt, user_prompt,
                record["find_text"], record["replace_text_sanitized"],
            )
        except ClientError as exc:
            # A persistent transport failure must not abort the run; record
            # it and continue. The "transport:" prefix keeps the row out of
            # done_ids so a later rerun retries it.
            outcome = {
                "attempts": MAX_ATTEMPTS,
                "coding": None,
                "error": f"transport: {exc}",
                "raw_response": None,
            }
        with write_lock:
            if outcome.get("error"):
                if str(outcome["error"]).startswith("transport:"):
                    n_transport_fail += 1
                else:
                    n_parse_fail += 1
            handle.write(
                json.dumps(
                    output_record(record, grader_cfg["model_id"], system_prompt, user_prompt, outcome),
                    ensure_ascii=False,
                )
                + "\n"
            )
            handle.flush()
            n_done += 1
            if n_done % 25 == 0 or n_done == len(todo):
                print(
                    f"[{grader_key}] {n_done}/{len(todo)} "
                    f"(parse failures: {n_parse_fail}, transport failures: {n_transport_fail})",
                    flush=True,
                )

    with open(out_path, "a", encoding="utf-8") as handle:
        with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
            futures = [pool.submit(grade_record, record) for record in todo]
            for future in as_completed(futures):
                future.result()  # propagate only truly unexpected exceptions

    fail_rate = n_parse_fail / max(1, len(todo))
    print(client.ledger.summary())
    if fail_rate > config["grading"]["parse_failure_ask_threshold"]:
        print(
            f"WARNING: failure rate {fail_rate:.1%} exceeds "
            f"{config['grading']['parse_failure_ask_threshold']:.0%} — ASK Peter before continuing (BRIEF A2)."
        )


def pick_smoke_records(edits: list[dict]) -> list[dict]:
    """Deterministic smoke set: 2 applied edits (one with a v1 conflict) + 1 abstention."""
    pool = gradeable(edits)
    applied = [r for r in pool if r["apply_status"] == "applied"]
    abstentions = [r for r in pool if r["apply_status"] == "no_change"]
    applied.sort(key=lambda r: r["edit_id"])
    with_conflict = [r for r in applied if (r["v1_code"] or {}).get("conflicts")]
    picks = [applied[0]]
    for r in with_conflict:
        if r["edit_id"] != picks[0]["edit_id"]:
            picks.append(r)
            break
    picks.append(abstentions[0])
    return picks


def run_smoke() -> None:
    config = load_config()
    edits = load_edits()
    picks = pick_smoke_records(edits)
    system_prompt, user_template = load_prompts()
    client = LLMClient()

    print("Smoke test: 3 edits x 2 graders (live)")
    n_gradeable = len(gradeable(edits))
    report_rows = []
    for grader_key, grader_cfg in config["graders"].items():
        for record in picks:
            user_prompt = build_user_prompt(user_template, record)
            t0 = time.monotonic()
            outcome = grade_one(
                client, grader_cfg, system_prompt, user_prompt,
                record["find_text"], record["replace_text_sanitized"],
            )
            elapsed = time.monotonic() - t0
            first = outcome["attempts"][0]
            coding = outcome.get("coding") or {}
            judge = (coding.get("judge") or {}).get("score")
            pat = (coding.get("patienthood") or {}).get("level")
            n_conf = len(coding.get("conflicts") or [])
            row = {
                "grader": grader_key,
                "model": grader_cfg["model_id"],
                "edit_id": record["edit_id"],
                "is_abstention": record["is_abstention"],
                "attempts": len(outcome["attempts"]),
                "input_tokens": sum(a["input_tokens"] for a in outcome["attempts"]),
                "output_tokens": sum(a["output_tokens"] for a in outcome["attempts"]),
                "reasoning_omitted": any(a["reasoning_omitted"] for a in outcome["attempts"]),
                "judge": judge,
                "patienthood": pat,
                "conflicts": n_conf,
                "error": outcome.get("error"),
                "elapsed_s": round(elapsed, 1),
                "cached_first_attempt": first["cached"],
            }
            report_rows.append(row)
            print(
                f"  {grader_key:6s} {record['edit_id'][:60]:60s} "
                f"abst={row['is_abstention']} judge={judge} pat={pat} conf={n_conf} "
                f"tok={row['input_tokens']}+{row['output_tokens']} "
                f"attempts={row['attempts']} reasoning_omitted={row['reasoning_omitted']} "
                f"err={bool(row['error'])}"
            )

    # Cache-hit verification: repeat one call per grader; must be served from cache.
    print("Cache-hit verification (re-issuing first call per grader):")
    for grader_key, grader_cfg in config["graders"].items():
        record = picks[0]
        user_prompt = build_user_prompt(user_template, record)
        result = client.call(
            model=grader_cfg["model_id"],
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=grader_cfg.get("temperature", 0.0),
            max_tokens=grader_cfg.get("max_tokens", 4096),
            reasoning_effort=grader_cfg.get("reasoning_effort"),
        )
        print(f"  {grader_key}: cached={result['cached']}")
        assert result["cached"], f"cache miss on repeat call for {grader_key}"

    # Token projection for the full run.
    print(client.ledger.summary())
    for grader_key in config["graders"]:
        rows = [r for r in report_rows if r["grader"] == grader_key and not r["error"]]
        if rows:
            mean_in = sum(r["input_tokens"] for r in rows) / len(rows)
            mean_out = sum(r["output_tokens"] for r in rows) / len(rows)
            print(
                f"  projection[{grader_key}]: ~{mean_in:,.0f} in + {mean_out:,.0f} out "
                f"tokens/edit x {n_gradeable:,} gradeable edits "
                f"≈ {mean_in * n_gradeable / 1e6:.1f}M in + "
                f"{mean_out * n_gradeable / 1e6:.1f}M out tokens per full pass"
            )
    smoke_path = CODES_DIR / "smoke_test_results.json"
    CODES_DIR.mkdir(parents=True, exist_ok=True)
    smoke_path.write_text(json.dumps(report_rows, indent=2), encoding="utf-8")
    print(f"wrote {smoke_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="v2 blinded grading")
    parser.add_argument("--grader", choices=["gemma", "qwen", "muse"])
    parser.add_argument("--limit", type=int)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--concurrency", type=int, default=8)
    args = parser.parse_args()

    if args.smoke:
        run_smoke()
        return
    if not args.grader:
        parser.error("--grader is required unless --smoke")
    run_grader(args.grader, args.limit, load_edits(), concurrency=args.concurrency)


if __name__ == "__main__":
    main()
