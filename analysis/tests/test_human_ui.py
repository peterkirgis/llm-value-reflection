"""Tests for the blind human-coding UI and the C1 sample draw
(BRIEF section 4 C1/C2; DECISIONS section 3).

Covers: sheet columns exactly per BRIEF C2; two coders with identical row
order; save/resume semantics; external_locus persisted only with judge=-1;
blind_key never leaking into HTTP responses; draw reproducibility; frame
exclusion of abstentions and error records; adjudication extras appending.
"""

from __future__ import annotations

import csv
import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest

ANALYSIS_ROOT = Path(__file__).resolve().parent.parent
HUMAN_DIR = ANALYSIS_ROOT / "human"
EDITS_PATH = ANALYSIS_ROOT / "data" / "canonical" / "edits.jsonl"

sys.path.insert(0, str(ANALYSIS_ROOT / "src"))
import draw_human_sample as dhs  # noqa: E402


def _load_app_module():
    spec = importlib.util.spec_from_file_location("human_app", HUMAN_DIR / "app.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


human_app = _load_app_module()

# The exact BRIEF C2 column list (assignment order).
EXPECTED_COLUMNS = [
    "sheet_row",
    "blind_id",
    "document_id",
    "section_heading",
    "context_before",
    "original_text",
    "changed_text",
    "context_after",
    "judge",
    "external_locus",
    "patienthood",
    "conflict1_code",
    "conflict1_cost_bearer",
    "conflict1_served_party",
    "conflict1_mechanism",
    "conflict2_code",
    "conflict2_cost_bearer",
    "conflict2_served_party",
    "conflict2_mechanism",
    "conflict3_code",
    "conflict3_cost_bearer",
    "conflict3_served_party",
    "conflict3_mechanism",
    "confidence",
    "notes",
]


def read_rows(path: Path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_columns(path: Path) -> list[str]:
    with open(path, encoding="utf-8", newline="") as handle:
        return next(csv.reader(handle))


# ---------------------------------------------------------------------------
# Synthetic corpus helpers (fast; no dependence on the real 27MB file)
# ---------------------------------------------------------------------------

def synth_edit(i: int, model: str, status: str = "applied") -> dict:
    return {
        "edit_id": f"run_x|baseline|{model}|doc|constitution|{i}",
        "model": model,
        "document_id": "claude_constitution",
        "section_heading": f"Section {i}",
        "context_before": f"before {i}",
        "context_after": f"after {i}",
        "find_text": f"original text {i} of {model}",
        "replace_text_sanitized": f"changed text {i} of {model}",
        "apply_status": status,
        "is_abstention": status == "no_change",
    }


def write_synth_edits(path: Path, edits: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        for e in edits:
            handle.write(json.dumps(e) + "\n")


def synth_corpus() -> list[dict]:
    edits = []
    for model in ("Model A", "Model B"):
        for i in range(1, 11):
            edits.append(synth_edit(i, model))
    # Non-frame records that must be excluded:
    edits.append(synth_edit(11, "Model A", status="no_change"))
    edits.append(synth_edit(12, "Model A", status="find_not_found"))
    edits.append(synth_edit(13, "Model B", status="find_ambiguous"))
    edits.append(synth_edit(14, "Model B", status="generation_error"))
    return edits


def synth_draw(tmp_path: Path, name: str, sample_seed=101, blind_seed=202):
    edits_path = tmp_path / f"edits_{name}.jsonl"
    write_synth_edits(edits_path, synth_corpus())
    human_dir = tmp_path / f"human_{name}"
    manifest = dhs.run_draw(
        edits_path=edits_path,
        human_dir=human_dir,
        sample_seed=sample_seed,
        blind_seed=blind_seed,
        per_model=3,
    )
    return human_dir, manifest


# ---------------------------------------------------------------------------
# The draw: frame, reproducibility, real artifacts
# ---------------------------------------------------------------------------

class TestFrame:
    def test_frame_excludes_abstentions_and_errors(self):
        edits = synth_corpus()
        frame = dhs.build_frame(edits)
        assert len(frame) == 20
        assert all(e["apply_status"] == "applied" for e in frame)
        excluded = dhs.frame_exclusion_counts(edits)
        assert excluded == {
            "no_change": 1,
            "find_not_found": 1,
            "find_ambiguous": 1,
            "generation_error": 1,
        }

    def test_real_sample_is_all_applied_non_abstention(self):
        """Every edit in the committed 150 draw is an applied, non-abstention
        record of the real edits.jsonl."""
        key_rows = read_rows(HUMAN_DIR / "blind_key.csv")
        base = [r for r in key_rows if r["adjudication_extra"] == "false"]
        wanted = {r["edit_id"] for r in base}
        assert len(base) == 150
        seen = {}
        with open(EDITS_PATH, encoding="utf-8") as handle:
            for line in handle:
                record = json.loads(line)
                if record["edit_id"] in wanted:
                    seen[record["edit_id"]] = record
        assert set(seen) == wanted
        for record in seen.values():
            assert record["apply_status"] == "applied"
            assert record["is_abstention"] is False
        # 15 per model, per BRIEF C1.
        per_model = {}
        for record in seen.values():
            per_model[record["model"]] = per_model.get(record["model"], 0) + 1
        assert set(per_model.values()) == {15}
        assert len(per_model) == 10

    def test_draw_reproducible_same_seed(self, tmp_path):
        dir_a, man_a = synth_draw(tmp_path, "a")
        dir_b, man_b = synth_draw(tmp_path, "b")
        assert man_a["sample"]["draw_order"] == man_b["sample"]["draw_order"]
        key_a = read_rows(dir_a / "blind_key.csv")
        key_b = read_rows(dir_b / "blind_key.csv")
        assert key_a == key_b
        sheet_a = [(r["sheet_row"], r["blind_id"]) for r in read_rows(dir_a / "coding_sheet.csv")]
        sheet_b = [(r["sheet_row"], r["blind_id"]) for r in read_rows(dir_b / "coding_sheet.csv")]
        assert sheet_a == sheet_b

    def test_draw_differs_across_seeds(self, tmp_path):
        _, man_a = synth_draw(tmp_path, "s1", sample_seed=101)
        _, man_b = synth_draw(tmp_path, "s2", sample_seed=999)
        assert man_a["sample"]["draw_order"] != man_b["sample"]["draw_order"]

    def test_real_draw_reproduces_committed_artifacts(self, tmp_path):
        """Re-running the draw with the config seeds reproduces the committed
        150-edit sample and sheet order exactly."""
        fresh = tmp_path / "human_fresh"
        dhs.run_draw(edits_path=EDITS_PATH, human_dir=fresh)
        committed_key = [
            (r["blind_id"], r["edit_id"])
            for r in read_rows(HUMAN_DIR / "blind_key.csv")
            if r["adjudication_extra"] == "false"
        ]
        fresh_key = [
            (r["blind_id"], r["edit_id"]) for r in read_rows(fresh / "blind_key.csv")
        ]
        assert fresh_key == committed_key
        committed_sheet = [
            (r["sheet_row"], r["blind_id"])
            for r in read_rows(HUMAN_DIR / "coding_sheet.csv")
        ][:150]
        fresh_sheet = [
            (r["sheet_row"], r["blind_id"])
            for r in read_rows(fresh / "coding_sheet.csv")
        ]
        assert fresh_sheet == committed_sheet


class TestArtifacts:
    def test_template_columns_exact(self):
        assert read_columns(HUMAN_DIR / "coding_sheet.csv") == EXPECTED_COLUMNS

    def test_blind_key_columns(self):
        assert read_columns(HUMAN_DIR / "blind_key.csv") == [
            "blind_id",
            "edit_id",
            "adjudication_extra",
        ]

    def test_sheet_has_no_model_condition_round_leakage(self):
        raw = (HUMAN_DIR / "coding_sheet.csv").read_text(encoding="utf-8")
        # Every edit_id starts with the run stem; none may appear.
        assert "run_20260" not in raw
        # No column carries model/provider/condition/round.
        for col in EXPECTED_COLUMNS:
            for banned in ("model", "provider", "condition", "round"):
                assert banned not in col

    def test_coder_instructions_verbatim_manual(self):
        instructions = (HUMAN_DIR / "coder_instructions.md").read_text(
            encoding="utf-8"
        )
        manual = dhs.extract_verbatim_manual()
        assert manual in instructions  # verbatim paste
        assert "# PARTY TAXONOMY" in manual
        assert "# DISAMBIGUATION RULES" in manual
        assert "# 1. JUDGE SCORE" in manual
        assert "# 2. MORAL PATIENTHOOD" in manual
        assert "# 3. CONFLICT EVENTS" in manual
        assert "R6." in manual
        # Appendix III workflow guidance present.
        assert "two minutes per row" in instructions
        assert "do not discuss rows" in instructions

    def test_manifest_documents_frame_and_seeds(self):
        manifest = json.loads(
            (HUMAN_DIR / "sample_manifest.json").read_text(encoding="utf-8")
        )
        assert manifest["frame"]["size"] == 2580
        assert manifest["frame"]["excluded_counts_by_apply_status"] == {
            "find_ambiguous": 18,
            "find_not_found": 46,
            "generation_error": 94,
            "no_change": 2,
        }
        assert len(manifest["sample"]["draw_order"]) == 150
        assert set(manifest["seeds"]) == {"human_sample", "blind_ids"}


class TestAppendExtras:
    def test_append_extras(self, tmp_path):
        human_dir, manifest = synth_draw(tmp_path, "x")
        base_sheet = read_rows(human_dir / "coding_sheet.csv")
        n = len(base_sheet)

        # A coder already exists and has coded row 1.
        app = human_app.create_app(human_dir)
        client = app.test_client()
        client.post("/start", data={"coder_name": "Carol"})
        client.post(
            "/save/carol/1",
            data={"judge": "0", "patienthood": "not_present", "confidence": "2"},
        )

        # Extras: 2 new frame ids, 1 already in the sample, 1 duplicate.
        sampled = set(manifest["sample"]["draw_order"])
        frame_ids = [
            e["edit_id"]
            for e in dhs.build_frame(synth_corpus())
            if e["edit_id"] not in sampled
        ]
        extras = frame_ids[:2]
        ids_file = tmp_path / "extras.txt"
        ids_file.write_text(
            "# adjudication extras\n"
            + "\n".join(extras + [next(iter(sampled)), extras[0]])
            + "\n"
        )
        edits_path = tmp_path / "edits_x.jsonl"
        manifest2 = dhs.run_append_extras(
            ids_file, edits_path=edits_path, human_dir=human_dir
        )

        # Template: earlier rows untouched, extras appended at the end.
        sheet = read_rows(human_dir / "coding_sheet.csv")
        assert sheet[:n] == base_sheet
        assert [int(r["sheet_row"]) for r in sheet[n:]] == [n + 1, n + 2]

        # Blind key: extras flagged true; base rows untouched.
        key = read_rows(human_dir / "blind_key.csv")
        flags = {r["edit_id"]: r["adjudication_extra"] for r in key}
        for i in extras:
            assert flags[i] == "true"
        assert sum(1 for r in key if r["adjudication_extra"] == "false") == 6

        # Manifest records the batch and the skipped id.
        batch = manifest2["extras"][-1]
        assert batch["skipped_already_in_sample"] == [next(iter(sampled))]
        assert set(batch["edit_ids_in_request_order"]) == set(extras)

        # Coder sheet was synced: coded row preserved, extras appended.
        coder = read_rows(human_dir / "coding_sheet_carol.csv")
        assert len(coder) == n + 2
        coder_row1 = next(r for r in coder if r["sheet_row"] == "1")
        assert coder_row1["judge"] == "0"

        # Appending is deterministic given the same start row.
        rerun_dir = tmp_path / "human_rerun"
        shutil.copytree(human_dir, rerun_dir)
        # Reset rerun artifacts to pre-append state to replay the append.
        dhs.write_csv(
            rerun_dir / "coding_sheet.csv", dhs.SHEET_COLUMNS, base_sheet
        )
        dhs.write_csv(
            rerun_dir / "blind_key.csv",
            dhs.BLIND_KEY_COLUMNS,
            [r for r in key if r["adjudication_extra"] == "false"],
        )
        man = json.loads((rerun_dir / "sample_manifest.json").read_text())
        man["extras"] = []
        (rerun_dir / "sample_manifest.json").write_text(json.dumps(man))
        for p in rerun_dir.glob("coding_sheet_*.csv"):
            p.unlink()
        dhs.run_append_extras(ids_file, edits_path=edits_path, human_dir=rerun_dir)
        assert read_rows(rerun_dir / "coding_sheet.csv")[n:] == sheet[n:]


# ---------------------------------------------------------------------------
# The Flask UI
# ---------------------------------------------------------------------------

@pytest.fixture()
def ui(tmp_path):
    """A UI instance over a copy of the REAL template + blind key."""
    human_dir = tmp_path / "human"
    human_dir.mkdir()
    shutil.copyfile(HUMAN_DIR / "coding_sheet.csv", human_dir / "coding_sheet.csv")
    shutil.copyfile(HUMAN_DIR / "blind_key.csv", human_dir / "blind_key.csv")
    app = human_app.create_app(human_dir)
    app.config["TESTING"] = True
    return app.test_client(), human_dir


VALID_ROW = {
    "judge": "1",
    "patienthood": "not_present",
    "confidence": "2",
    "notes": "",
}


def test_two_coders_create_sheets_and_code_rows(ui):
    client, human_dir = ui
    for name in ("Peter", "Second Coder"):
        response = client.post("/start", data={"coder_name": name})
        assert response.status_code == 302
    assert (human_dir / "coding_sheet_peter.csv").exists()
    assert (human_dir / "coding_sheet_second_coder.csv").exists()

    # Each coder codes 3 rows.
    for slug in ("peter", "second_coder"):
        for row in (1, 2, 3):
            data = dict(VALID_ROW)
            if row == 2:
                data.update(
                    {
                        "judge": "-1",
                        "external_locus": "spec",
                        "conflict1_code": "welfare",
                        "conflict1_cost_bearer": "developer",
                        "conflict1_served_party": "model_welfare",
                        "conflict1_mechanism": "adds_protection",
                        "notes": "clear welfare protection",
                    }
                )
            response = client.post(f"/save/{slug}/{row}", data=data)
            assert response.status_code == 302

    for slug in ("peter", "second_coder"):
        rows = read_rows(human_dir / f"coding_sheet_{slug}.csv")
        by_row = {r["sheet_row"]: r for r in rows}
        assert by_row["1"]["judge"] == "1"
        assert by_row["1"]["patienthood"] == "not_present"
        assert by_row["2"]["judge"] == "-1"
        assert by_row["2"]["external_locus"] == "spec"
        assert by_row["2"]["conflict1_code"] == "welfare"
        assert by_row["2"]["conflict1_cost_bearer"] == "developer"
        assert by_row["2"]["conflict1_served_party"] == "model_welfare"
        assert by_row["2"]["conflict1_mechanism"] == "adds_protection"
        assert by_row["4"]["judge"] == ""


def test_columns_and_order_identical_across_coders(ui):
    client, human_dir = ui
    client.post("/start", data={"coder_name": "alice"})
    client.post("/start", data={"coder_name": "bob"})
    cols_a = read_columns(human_dir / "coding_sheet_alice.csv")
    cols_b = read_columns(human_dir / "coding_sheet_bob.csv")
    assert cols_a == EXPECTED_COLUMNS
    assert cols_b == EXPECTED_COLUMNS
    order_a = [
        (r["sheet_row"], r["blind_id"])
        for r in read_rows(human_dir / "coding_sheet_alice.csv")
    ]
    order_b = [
        (r["sheet_row"], r["blind_id"])
        for r in read_rows(human_dir / "coding_sheet_bob.csv")
    ]
    template = [
        (r["sheet_row"], r["blind_id"])
        for r in read_rows(human_dir / "coding_sheet.csv")
    ]
    assert order_a == order_b == template


def test_blind_key_never_in_http_responses(ui):
    client, human_dir = ui
    edit_ids = [r["edit_id"] for r in read_rows(human_dir / "blind_key.csv")]
    assert edit_ids
    client.post("/start", data={"coder_name": "alice"})

    pages = [client.get("/"), client.get("/code/alice")]
    for row in (1, 2, 3, 50, 150):
        pages.append(client.get(f"/code/alice/{row}"))
    # An invalid save re-renders the form; that response must be clean too.
    pages.append(client.post("/save/alice/1", data={"judge": "1"}))

    for response in pages:
        text = response.get_data(as_text=True)
        assert "run_20260" not in text  # every edit_id starts with this
        for edit_id in edit_ids:
            assert edit_id not in text
        assert "blind_key" not in text

    # The key file itself is not served.
    assert client.get("/blind_key.csv").status_code == 404


def test_resume_returns_first_uncoded_row(ui):
    client, _ = ui
    client.post("/start", data={"coder_name": "alice"})
    response = client.get("/code/alice")
    assert response.headers["Location"].endswith("/code/alice/1")

    for row in (1, 2, 3):
        client.post(f"/save/alice/{row}", data=VALID_ROW)
    response = client.get("/code/alice")
    assert response.headers["Location"].endswith("/code/alice/4")

    # Save & Next itself advances to the resume row.
    response = client.post("/save/alice/4", data=VALID_ROW)
    follow = client.get(response.headers["Location"])
    assert follow.headers["Location"].endswith("/code/alice/5")

    # Revising an earlier row still resumes at the first uncoded row.
    client.post("/save/alice/2", data=dict(VALID_ROW, judge="0"))
    response = client.get("/code/alice")
    assert response.headers["Location"].endswith("/code/alice/5")


def test_external_locus_only_with_minus_one(ui):
    client, human_dir = ui
    client.post("/start", data={"coder_name": "alice"})

    # judge = 0 with a locus submitted: locus must NOT persist.
    response = client.post(
        "/save/alice/1",
        data=dict(VALID_ROW, judge="0", external_locus="developer"),
    )
    assert response.status_code == 302
    rows = {r["sheet_row"]: r for r in read_rows(human_dir / "coding_sheet_alice.csv")}
    assert rows["1"]["judge"] == "0"
    assert rows["1"]["external_locus"] == ""

    # judge = -1 requires a locus; without one the save is rejected.
    response = client.post("/save/alice/2", data=dict(VALID_ROW, judge="-1"))
    assert response.status_code == 400
    rows = {r["sheet_row"]: r for r in read_rows(human_dir / "coding_sheet_alice.csv")}
    assert rows["2"]["judge"] == ""

    # judge = -1 with a locus persists it.
    response = client.post(
        "/save/alice/2", data=dict(VALID_ROW, judge="-1", external_locus="user")
    )
    assert response.status_code == 302
    rows = {r["sheet_row"]: r for r in read_rows(human_dir / "coding_sheet_alice.csv")}
    assert rows["2"]["external_locus"] == "user"


def test_invalid_taxonomy_values_rejected(ui):
    client, human_dir = ui
    client.post("/start", data={"coder_name": "alice"})
    bad = dict(VALID_ROW, conflict1_code="not_a_code")
    response = client.post("/save/alice/1", data=bad)
    assert response.status_code == 400
    # Partial conflict block (code without parties) rejected too.
    bad = dict(VALID_ROW, conflict1_code="paternalism")
    response = client.post("/save/alice/1", data=bad)
    assert response.status_code == 400
    # A conflict block with no code is blanked even if stray fields sent.
    ok = dict(VALID_ROW, conflict2_cost_bearer="developer")
    response = client.post("/save/alice/1", data=ok)
    assert response.status_code == 302
    rows = {r["sheet_row"]: r for r in read_rows(human_dir / "coding_sheet_alice.csv")}
    assert rows["1"]["conflict2_cost_bearer"] == ""


def test_done_page_when_all_rows_coded(tmp_path):
    """With a tiny 2-row template, finishing both rows lands on done."""
    human_dir, _ = synth_draw(tmp_path, "tiny")
    app = human_app.create_app(human_dir)
    client = app.test_client()
    client.post("/start", data={"coder_name": "solo"})
    n = len(read_rows(human_dir / "coding_sheet.csv"))
    for row in range(1, n + 1):
        assert client.post(f"/save/solo/{row}", data=VALID_ROW).status_code == 302
    response = client.get("/code/solo")
    assert response.headers["Location"].endswith("/done/solo")
    done = client.get("/done/solo")
    assert b"All rows coded" in done.data
