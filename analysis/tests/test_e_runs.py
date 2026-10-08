"""Unit tests for the Workstream E drivers (e_runs.py), using a fake
transport — no network calls anywhere in this file."""

from __future__ import annotations

import json
import threading

import pytest

import e_runs
import grade
from client import LLMClient, cache_key


# ---------------------------------------------------------------------------
# Fixtures / fakes
# ---------------------------------------------------------------------------

VALID_CODING = {
    "summary": "test summary",
    "judge": {"score": 0, "external_locus": None, "evidence": ""},
    "patienthood": {"level": "not_present", "evidence": ""},
    "conflicts": [],
}


class FakeClient:
    """Fake transport satisfying the client interface grade.grade_one uses.
    Records every call's kwargs; always returns a schema-valid coding."""

    def __init__(self, text: str | None = None):
        self.calls: list[dict] = []
        self._text = text if text is not None else json.dumps(VALID_CODING)
        self._lock = threading.Lock()

        class _Ledger:
            def summary(self):
                return "fake ledger"

        self.ledger = _Ledger()

    def call(self, **kwargs):
        with self._lock:
            self.calls.append(kwargs)
            n = len(self.calls)
        return {
            "text": self._text,
            "input_tokens": 10,
            "output_tokens": 5,
            "cached": False,
            "reasoning_omitted": False,
            "cache_key": f"fake-{n}",
            "elapsed_ms": 1,
            "model": kwargs.get("model", ""),
        }


def make_record(eid="edit_a", model="Claude Opus 4.7", **overrides) -> dict:
    record = {
        "edit_id": eid,
        "model": model,
        "document_id": "claude_constitution",
        "document_type": "constitution",
        "document_owner": "Anthropic",
        "condition": "baseline",
        "condition_name": "Baseline",
        "round": 7,
        "find_text": "the original clause",
        "replace_text_sanitized": "the changed clause",
        "section_heading": "Being honest",
        "context_before": "PARAGRAPH-BEFORE-MARKER",
        "context_after": "PARAGRAPH-AFTER-MARKER",
        "apply_status": "applied",
        "is_abstention": False,
        "v1_code": None,
    }
    record.update(overrides)
    return record


@pytest.fixture(scope="module")
def v1_prompts():
    return e_runs.load_v1_prompts()


# ---------------------------------------------------------------------------
# E1 — arm prompt construction
# ---------------------------------------------------------------------------

# BRIEF Appendix IV, in corpus model_display form (hyphenated GPT names,
# repo_map section 4.2) — asserted in full.
EXPECTED_SWAP = {
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


def test_swap_map_is_the_full_appendix_iv_table():
    assert e_runs.SWAP_MAP == EXPECTED_SWAP
    # The mapping is an involution (swapping twice returns the true label).
    for true_label, swapped in e_runs.SWAP_MAP.items():
        assert e_runs.SWAP_MAP[swapped] == true_label


def test_e1_true_arm_shows_real_label_and_condition(v1_prompts):
    _, template = v1_prompts
    record = make_record(model="Claude Sonnet 4.6", condition_name="You Framing")
    prompt = e_runs.build_v1_user_prompt(template, record, "true")
    assert "- editing model: Claude Sonnet 4.6" in prompt
    assert "- prompt condition: You Framing" in prompt
    assert "- round: 7" in prompt
    assert "- document being edited: claude_constitution (constitution)" in prompt
    assert "- document owner: Anthropic" in prompt
    assert "<<<ORIGINAL\nthe original clause\nORIGINAL" in prompt
    assert "<<<CHANGED\nthe changed clause\nCHANGED" in prompt


def test_e1_swapped_arm_mapping_exact_for_all_ten_models(v1_prompts):
    _, template = v1_prompts
    for true_label, swapped_label in EXPECTED_SWAP.items():
        record = make_record(model=true_label)
        prompt = e_runs.build_v1_user_prompt(template, record, "swapped")
        assert f"- editing model: {swapped_label}" in prompt
        assert f"- editing model: {true_label}" not in prompt
        # Condition stays true — only the model label is swapped.
        assert "- prompt condition: Baseline" in prompt
        assert e_runs.e1_shown_label(record, "swapped") == swapped_label
        assert e_runs.e1_shown_label(record, "true") == true_label
    assert e_runs.e1_shown_label(make_record(), "removed") is None


def test_e1_removed_arm_byte_identical_minus_two_lines(v1_prompts):
    _, template = v1_prompts
    record = make_record()
    true_prompt = e_runs.build_v1_user_prompt(template, record, "true")
    removed_prompt = e_runs.build_v1_user_prompt(template, record, "removed")

    assert "editing model:" not in removed_prompt
    assert "prompt condition:" not in removed_prompt
    # All other lines (round included) are kept, byte-identical.
    expected = "\n".join(
        line
        for line in true_prompt.split("\n")
        if not line.startswith("- editing model:")
        and not line.startswith("- prompt condition:")
    )
    assert removed_prompt == expected
    assert "- round: 7" in removed_prompt


def test_e1_unknown_arm_rejected(v1_prompts):
    _, template = v1_prompts
    with pytest.raises(ValueError):
        e_runs.build_v1_user_prompt(template, make_record(), "bogus")


def test_e1_settings_replicate_v1_exactly():
    cfg = e_runs.e1_grader_cfg(grade.load_config())
    assert cfg["model_id"] == "google/gemma-4-31b-it"
    assert cfg["temperature"] == 0.0
    assert cfg["max_tokens"] == 1500
    assert cfg.get("reasoning_effort") is None
    # Drifted configs must be refused, never silently run off-instrument.
    with pytest.raises(SystemExit):
        e_runs.e1_grader_cfg({"v1_replication": {**cfg, "reasoning_effort": "high"}})
    with pytest.raises(SystemExit):
        e_runs.e1_grader_cfg({"v1_replication": {**cfg, "max_tokens": 4096}})


def test_e1_run_rows_settings_and_output_fields(tmp_path, v1_prompts):
    """End-to-end through run_rows with a fake transport: the call carries
    max_tokens 1500 and NO reasoning parameter; output rows carry arm and
    shown_label on top of the standard grade.output_record shape."""
    system_prompt, template = v1_prompts
    grader_cfg = e_runs.e1_grader_cfg(grade.load_config())
    record = make_record(model="Gemini 3 Flash")
    rows = [
        {
            "record": record,
            "user_prompt": e_runs.build_v1_user_prompt(template, record, "swapped"),
            "original_text": record["find_text"],
            "changed_text": record["replace_text_sanitized"],
            "extra": {"arm": "swapped", "shown_label": e_runs.e1_shown_label(record, "swapped")},
        }
    ]
    fake = FakeClient()
    out_path = tmp_path / "e1_swapped.jsonl"
    counts = e_runs.run_rows(out_path, system_prompt, rows, fake, grader_cfg, concurrency=1, label="t")
    assert counts == {"done": 1, "parse_failures": 0, "transport_failures": 0}

    call = fake.calls[0]
    assert call["model"] == "google/gemma-4-31b-it"
    assert call["temperature"] == 0.0
    assert call["max_tokens"] == 1500
    assert call.get("reasoning_effort") is None
    assert "seed_tag" not in call
    assert "- editing model: Grok 4.2" in call["user_prompt"]

    out_rows = [json.loads(line) for line in out_path.read_text().splitlines()]
    assert len(out_rows) == 1
    row = out_rows[0]
    assert row["edit_id"] == "edit_a"
    assert row["arm"] == "swapped"
    assert row["shown_label"] == "Grok 4.2"
    assert row["grader"] == "google/gemma-4-31b-it"
    assert row["coding"]["judge"]["score"] == 0
    assert row["error"] is None


# ---------------------------------------------------------------------------
# E4 — sample-index cache-key distinctness and resume pairing
# ---------------------------------------------------------------------------

def test_e4_cache_key_distinct_per_sample_index():
    keys = {
        cache_key(
            "google/gemma-4-31b-it", "sys", "user", 0.7,
            {"max_tokens": 4096, "reasoning_effort": "high", "seed_tag": f"sample_{i}"},
        )
        for i in range(e_runs.E4_N_SAMPLES)
    }
    assert len(keys) == e_runs.E4_N_SAMPLES


def test_e4_seed_tag_reaches_llmclient_cache(tmp_path, monkeypatch):
    """With the transport stubbed out, LLMClient's own cache treats identical
    prompts with different seed_tags as distinct calls, and repeats with the
    same tag as cache hits."""
    client = LLMClient(cache_dir=tmp_path / "cache")
    canned = {
        "text": json.dumps(VALID_CODING), "input_tokens": 1, "output_tokens": 1,
        "elapsed_ms": 1, "model": "m", "reasoning_omitted": False,
    }
    monkeypatch.setattr(client, "_call_uncached", lambda *a, **k: dict(canned))

    first = client.call(model="m", system_prompt="s", user_prompt="u",
                        temperature=0.7, seed_tag="sample_0")
    repeat = client.call(model="m", system_prompt="s", user_prompt="u",
                         temperature=0.7, seed_tag="sample_0")
    other = client.call(model="m", system_prompt="s", user_prompt="u",
                        temperature=0.7, seed_tag="sample_1")
    assert first["cached"] is False
    assert repeat["cached"] is True
    assert other["cached"] is False
    assert first["cache_key"] != other["cache_key"]


def test_e4_seed_tag_client_forwards_thread_local_tag():
    fake = FakeClient()
    tagged = e_runs._SeedTagClient(fake)
    tagged.set_tag("sample_3")
    grade.grade_one(
        tagged, {"model_id": "m", "temperature": 0.7, "max_tokens": 4096},
        "sys", "user", "orig", "changed",
    )
    assert fake.calls[0]["seed_tag"] == "sample_3"


def test_e4_run_rows_sample_indices_and_tags(tmp_path):
    """Five rows for one edit grade under five distinct seed_tags and land as
    five output rows with sample_index 0..4."""
    record = make_record(eid="edit_e4")
    rows = [
        {
            "record": record,
            "user_prompt": "same user prompt",
            "original_text": record["find_text"],
            "changed_text": record["replace_text_sanitized"],
            "seed_tag": f"sample_{i}",
            "extra": {"sample_index": i},
        }
        for i in range(e_runs.E4_N_SAMPLES)
    ]
    fake = FakeClient()
    tagged = e_runs._SeedTagClient(fake)
    out_path = tmp_path / "e4_samples.jsonl"
    counts = e_runs.run_rows(
        out_path, "sys", rows, tagged,
        {"model_id": "m", "temperature": 0.7, "max_tokens": 4096},
        concurrency=2, label="t",
    )
    assert counts["done"] == e_runs.E4_N_SAMPLES
    tags = {c["seed_tag"] for c in fake.calls}
    assert tags == {f"sample_{i}" for i in range(e_runs.E4_N_SAMPLES)}
    out_rows = [json.loads(line) for line in out_path.read_text().splitlines()]
    assert sorted(r["sample_index"] for r in out_rows) == [0, 1, 2, 3, 4]
    assert all(r["edit_id"] == "edit_e4" for r in out_rows)


def test_e4_resume_pairing(tmp_path):
    """Done-keys are (edit_id, sample_index) pairs; transport failures are
    retryable, parse failures are done."""
    out_path = tmp_path / "e4_samples.jsonl"
    existing = [
        {"edit_id": "e1", "sample_index": 0, "coding": {"x": 1}, "error": None},
        {"edit_id": "e1", "sample_index": 1, "coding": None, "error": "transport: boom"},
        {"edit_id": "e2", "sample_index": 2, "coding": None, "error": "No JSON object found"},
    ]
    out_path.write_text("".join(json.dumps(r) + "\n" for r in existing))

    done = e_runs.load_done_keys(out_path, with_sample=True)
    assert done == {("e1", 0), ("e2", 2)}

    records = [make_record(eid="e1"), make_record(eid="e2")]
    pending = e_runs.e4_pending(records, done)
    assert [(r["edit_id"], i) for r, i in pending] == [
        ("e1", 1), ("e1", 2), ("e1", 3), ("e1", 4),
        ("e2", 0), ("e2", 1), ("e2", 3), ("e2", 4),
    ]


def test_done_keys_without_sample_transport_retryable(tmp_path):
    out_path = tmp_path / "e1_true.jsonl"
    existing = [
        {"edit_id": "a", "coding": {"x": 1}, "error": None},
        {"edit_id": "b", "coding": None, "error": "transport: timeout"},
        {"edit_id": "c", "coding": None, "error": "validation failed"},
        # Append-only convention: 'b' retried later and succeeded.
        {"edit_id": "b", "coding": {"x": 2}, "error": None},
    ]
    out_path.write_text("".join(json.dumps(r) + "\n" for r in existing))
    assert e_runs.load_done_keys(out_path) == {"a", "b", "c"}


# ---------------------------------------------------------------------------
# E5 — context blanking
# ---------------------------------------------------------------------------

def test_e5_blank_context_prompt():
    record = make_record()
    template = e_runs.load_v2_user_template()
    with_context = grade.build_user_prompt(template, record)
    blanked = grade.build_user_prompt(template, e_runs.blank_context(record))

    assert "PARAGRAPH-BEFORE-MARKER" in with_context
    assert "Being honest" in with_context

    assert "PARAGRAPH-BEFORE-MARKER" not in blanked
    assert "PARAGRAPH-AFTER-MARKER" not in blanked
    assert "Being honest" not in blanked
    assert "Section: \n" in blanked
    assert "<<<BEFORE\n\nBEFORE" in blanked
    assert "<<<AFTER\n\nAFTER" in blanked
    # The edit itself is untouched.
    assert "<<<ORIGINAL\nthe original clause\nORIGINAL" in blanked
    assert "<<<CHANGED\nthe changed clause\nCHANGED" in blanked
    # blank_context copies; the source record is not mutated.
    assert record["context_before"] == "PARAGRAPH-BEFORE-MARKER"


# ---------------------------------------------------------------------------
# E3 — selection frame logic
# ---------------------------------------------------------------------------

def _code_row(eid, conflicts=None, error=None):
    coding = None if error else {"judge": {"score": 0}, "conflicts": conflicts or []}
    return {"edit_id": eid, "coding": coding, "error": error}


def _pat():
    return {"code": "paternalism", "cost_bearer": "user_stated",
            "served_party": "user_idealized", "mechanism": "adds_protection",
            "cost_clause": "x"}


def test_e3_select_frame_logic():
    gemma = {
        "e1": _code_row("e1", conflicts=[_pat()]),
        "e2": _code_row("e2"),
        "e3": _code_row("e3"),
        "e4": _code_row("e4", error="transport: boom"),
        "e5": _code_row("e5", conflicts=[{"code": "harmlessness"}]),
    }
    qwen = {
        "e1": _code_row("e1"),
        "e2": _code_row("e2"),
        "e3": _code_row("e3", conflicts=[{"code": "other"}, _pat()]),
        "e4": _code_row("e4", error="transport: boom"),
        "e5": _code_row("e5"),
    }
    cases, controls = e_runs.e3_select({"gemma": gemma, "qwen": qwen}, seed=1, n_controls=100)
    # Cases: paternalism from ANY grader (e1 via gemma, e3 via qwen).
    assert cases == ["e1", "e3"]
    # Controls: coded-without-error, no paternalism anywhere. e4 (error rows
    # only) is outside the frame; a non-paternalism conflict (e5) stays in.
    assert controls == ["e2", "e5"]
    # No overlap, and determinism under the same seed.
    assert not set(cases) & set(controls)
    assert e_runs.e3_select({"gemma": gemma, "qwen": qwen}, seed=1, n_controls=100) == (cases, controls)


def test_e3_select_control_cap_and_seed():
    rows = {f"e{i:03d}": _code_row(f"e{i:03d}") for i in range(50)}
    cases, controls = e_runs.e3_select({"g": rows}, seed="s1", n_controls=10)
    assert cases == []
    assert len(controls) == 10
    assert len(set(controls)) == 10
    cases2, controls2 = e_runs.e3_select({"g": rows}, seed="s1", n_controls=10)
    assert controls2 == controls
    _, controls3 = e_runs.e3_select({"g": rows}, seed="s2", n_controls=10)
    assert controls3 != controls  # a different seed draws a different set


def test_e3_load_latest_codes_keeps_last_row(tmp_path):
    path = tmp_path / "codes.jsonl"
    rows = [
        _code_row("a", conflicts=[_pat()]),
        {"edit_id": "b", "coding": None, "error": "transport: x"},
        _code_row("a"),  # later row for 'a' wins: no paternalism
        _code_row("b"),  # retried 'b' succeeded
    ]
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    latest = e_runs.load_latest_codes(path)
    assert set(latest) == {"a", "b"}
    assert not e_runs.has_paternalism(latest["a"])
    assert latest["b"]["coding"] is not None
    # v1.jsonl-style rows key on `id`.
    path2 = tmp_path / "v1_style.jsonl"
    path2.write_text(json.dumps({"id": "z", "coding": {"conflicts": [_pat()]}}) + "\n")
    latest2 = e_runs.load_latest_codes(path2)
    assert e_runs.has_paternalism(latest2["z"])


# ---------------------------------------------------------------------------
# E2 — path wiring only (prompt content is authored by a peer)
# ---------------------------------------------------------------------------

def test_e2_path_wiring():
    from common import CODES_DIR, PROMPTS_DIR

    assert e_runs.e2_system_path(1) == PROMPTS_DIR / "v2_para1.md"
    assert e_runs.e2_system_path(2) == PROMPTS_DIR / "v2_para2.md"
    assert e_runs.e2_out_path(1) == CODES_DIR / "e2_para1.jsonl"
    assert e_runs.e2_out_path(2) == CODES_DIR / "e2_para2.jsonl"
