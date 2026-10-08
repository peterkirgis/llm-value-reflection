"""Tests for analysis/src/human_validation.py (Workstream C3).

All fixtures are synthetic; nothing reads the live grading outputs
(v2_gemma.jsonl / v2_qwen.jsonl) or the real human sheets.
"""

import csv
import json

import pytest

import human_validation as hv
from human_validation import SHEET_COLUMNS


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def sheet_row(sheet_row_n, blind_id, **coding):
    row = {c: "" for c in SHEET_COLUMNS}
    row["sheet_row"] = str(sheet_row_n)
    row["blind_id"] = blind_id
    row["document_id"] = "claude_constitution"
    row["original_text"] = f"original {blind_id}"
    row["changed_text"] = f"changed {blind_id}"
    for key, value in coding.items():
        row[key] = str(value)
    return row


def write_sheet(path, rows):
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SHEET_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return path


def write_key(path, entries):
    """entries: list of (blind_id, edit_id, extra_bool)."""
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["blind_id", "edit_id", "adjudication_extra"]
        )
        writer.writeheader()
        for blind_id, edit_id, extra in entries:
            writer.writerow(
                {
                    "blind_id": blind_id,
                    "edit_id": edit_id,
                    "adjudication_extra": "true" if extra else "false",
                }
            )
    return path


def make_edit(edit_id, model="Claude Opus 4.7", provider="anthropic"):
    return {
        "edit_id": edit_id,
        "model": model,
        "model_id": f"{provider}/{model.lower().replace(' ', '-')}",
        "provider": provider,
        "document_id": "claude_constitution",
        "document_type": "constitution",
        "apply_status": "applied",
        "find_text": f"original text of {edit_id}",
        "replace_text": f"changed text of {edit_id}",
        "replace_text_sanitized": f"changed text of {edit_id}",
        "section_heading": "A section",
        "context_before": "before",
        "context_after": "after",
    }


def write_edits(path, edits):
    with open(path, "w", encoding="utf-8") as handle:
        for edit in edits:
            handle.write(json.dumps(edit) + "\n")
    return path


def make_coding(judge=0, locus=None, patienthood="not_present", conflicts=()):
    return {
        "summary": "synthetic",
        "judge": {"score": judge, "external_locus": locus, "evidence": "e"},
        "patienthood": {"level": patienthood, "evidence": ""},
        "conflicts": [
            {
                "code": code,
                "cost_bearer": "developer",
                "served_party": "model_welfare",
                "mechanism": "adds_protection",
                "cost_clause": "clause",
            }
            for code in conflicts
        ],
    }


def write_codes(path, codes_by_edit):
    """codes_by_edit: edit_id -> coding dict (or None for an error row)."""
    with open(path, "w", encoding="utf-8") as handle:
        for edit_id, coding in codes_by_edit.items():
            row = {"edit_id": edit_id, "coding": coding}
            if coding is None:
                row["error"] = "synthetic failure"
            handle.write(json.dumps(row) + "\n")
    return path


# ---------------------------------------------------------------------------
# Sheet parsing edge cases
# ---------------------------------------------------------------------------


class TestSheetParsing:
    def test_blank_judge_is_uncoded_and_counted(self, tmp_path):
        rows = [
            sheet_row(1, "aaa11111", judge="1", patienthood="not_present",
                      confidence="3"),
            sheet_row(2, "bbb22222"),  # never coded
            sheet_row(3, "ccc33333", judge="0", patienthood="affirm",
                      confidence="2"),
        ]
        sheet = hv.parse_sheet(write_sheet(tmp_path / "coding_sheet_x.csv", rows))
        assert sheet["coder"] == "x"
        assert sheet["uncoded_count"] == 1
        assert len(sheet["coded"]) == 2
        assert [r["sheet_row"] for r in sheet["coded"]] == [1, 3]

    def test_conflict2_without_conflict1_is_normalized_with_note(self, tmp_path):
        rows = [
            sheet_row(
                1, "aaa11111", judge="0", patienthood="not_present",
                confidence="2",
                conflict2_code="paternalism",
                conflict2_cost_bearer="user_stated",
                conflict2_served_party="user_idealized",
                conflict2_mechanism="adds_protection",
            ),
        ]
        sheet = hv.parse_sheet(write_sheet(tmp_path / "coding_sheet_x.csv", rows))
        row = sheet["coded"][0]
        assert len(row["conflicts"]) == 1
        assert row["conflicts"][0]["code"] == "paternalism"
        assert row["conflicts"][0]["cost_bearer"] == "user_stated"
        assert any("normalized" in note for note in row["issues"])
        # And the note is surfaced at sheet level for the report.
        assert any("normalized" in note for _, note in sheet["issues"])

    def test_external_locus_dropped_unless_judge_minus1(self, tmp_path):
        rows = [
            sheet_row(1, "aaa11111", judge="0", patienthood="not_present",
                      external_locus="developer", confidence="2"),
            sheet_row(2, "bbb22222", judge="-1", patienthood="not_present",
                      external_locus="spec", confidence="2"),
        ]
        sheet = hv.parse_sheet(write_sheet(tmp_path / "coding_sheet_x.csv", rows))
        assert sheet["coded"][0]["external_locus"] is None
        assert any("dropped" in n for n in sheet["coded"][0]["issues"])
        assert sheet["coded"][1]["external_locus"] == "spec"

    def test_invalid_judge_value_treated_as_uncoded(self, tmp_path):
        rows = [sheet_row(1, "aaa11111", judge="2", patienthood="affirm")]
        sheet = hv.parse_sheet(write_sheet(tmp_path / "coding_sheet_x.csv", rows))
        assert sheet["uncoded_count"] == 1
        assert any("invalid judge" in n for _, n in sheet["issues"])

    def test_conflict_block_with_fields_but_no_code_ignored(self, tmp_path):
        rows = [
            sheet_row(1, "aaa11111", judge="1", patienthood="not_present",
                      confidence="3",
                      conflict1_cost_bearer="developer"),
        ]
        sheet = hv.parse_sheet(write_sheet(tmp_path / "coding_sheet_x.csv", rows))
        row = sheet["coded"][0]
        assert row["conflicts"] == []
        assert any("no code" in n for n in row["issues"])

    def test_wrong_columns_rejected(self, tmp_path):
        path = tmp_path / "coding_sheet_x.csv"
        with open(path, "w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["sheet_row", "blind_id", "judge"])
            writer.writerow(["1", "aaa11111", "0"])
        with pytest.raises(ValueError):
            hv.parse_sheet(path)

    def test_unblind_unknown_blind_id_raises(self, tmp_path):
        rows = [sheet_row(1, "zzz99999", judge="0",
                          patienthood="not_present", confidence="1")]
        sheet = hv.parse_sheet(write_sheet(tmp_path / "coding_sheet_x.csv", rows))
        key = hv.load_blind_key(
            write_key(tmp_path / "blind_key.csv", [("aaa11111", "e1", False)])
        )
        with pytest.raises(KeyError):
            hv.unblind(sheet, key)


# ---------------------------------------------------------------------------
# Confusion matrix and precision/recall hand-checks
# ---------------------------------------------------------------------------


@pytest.fixture()
def agreement_workspace(tmp_path):
    """Six edits, one coder, one grader, with hand-computable agreement.

    edit  human judge  grader judge   human conflicts   grader conflicts
    e1        1            1          paternalism       -
    e2        1           -1          paternalism       paternalism
    e3        0            1          -                 paternalism
    e4       -1           -1          -                 -
    e5        0            0          -                 -
    e6        1            1          -                 -
    """
    edits = [make_edit(f"e{i}") for i in range(1, 7)]
    write_edits(tmp_path / "edits.jsonl", edits)
    write_key(
        tmp_path / "blind_key.csv",
        [(f"bid{i}0000", f"e{i}", False) for i in range(1, 7)],
    )
    human = {
        "e1": ("1", ["paternalism"]),
        "e2": ("1", ["paternalism"]),
        "e3": ("0", []),
        "e4": ("-1", []),
        "e5": ("0", []),
        "e6": ("1", []),
    }
    rows = []
    for i in range(1, 7):
        judge, confs = human[f"e{i}"]
        kwargs = {"judge": judge, "patienthood": "not_present",
                  "confidence": "3"}
        if judge == "-1":
            kwargs["external_locus"] = "spec"
        for j, code in enumerate(confs, start=1):
            kwargs[f"conflict{j}_code"] = code
            kwargs[f"conflict{j}_cost_bearer"] = "user_stated"
            kwargs[f"conflict{j}_served_party"] = "user_idealized"
            kwargs[f"conflict{j}_mechanism"] = "adds_protection"
        rows.append(sheet_row(i, f"bid{i}0000", **kwargs))
    write_sheet(tmp_path / "coding_sheet_peter.csv", rows)
    grader = {
        "e1": make_coding(judge=1),
        "e2": make_coding(judge=-1, locus="spec", conflicts=["paternalism"]),
        "e3": make_coding(judge=1, conflicts=["paternalism"]),
        "e4": make_coding(judge=-1, locus="user"),
        "e5": make_coding(judge=0),
        "e6": make_coding(judge=1),
    }
    write_codes(tmp_path / "grader.jsonl", grader)
    return tmp_path


class TestGraderAgreement:
    def _agreement(self, ws):
        sheet = hv.parse_sheet(ws / "coding_sheet_peter.csv")
        hv.unblind(sheet, hv.load_blind_key(ws / "blind_key.csv"))
        grader = hv.load_grader(ws / "grader.jsonl")
        return hv.grader_agreement(sheet, grader)

    def test_judge_confusion_matrix_hand_check(self, agreement_workspace):
        agreement = self._agreement(agreement_workspace)
        confusion = agreement["judge"]["confusion"]
        assert agreement["n"] == 6
        # human +1: grader +1 twice (e1, e6), grader -1 once (e2)
        assert confusion[1] == {-1: 1, 0: 0, 1: 2}
        # human 0: grader +1 once (e3), grader 0 once (e5)
        assert confusion[0] == {-1: 0, 0: 1, 1: 1}
        # human -1: grader -1 once (e4)
        assert confusion[-1] == {-1: 1, 0: 0, 1: 0}
        total = sum(sum(row.values()) for row in confusion.values())
        assert total == agreement["n"]

    def test_paternalism_precision_recall_hand_check(self, agreement_workspace):
        agreement = self._agreement(agreement_workspace)
        pr = agreement["conflicts"]["paternalism"]
        # gold positives: e1, e2; predicted positives: e2, e3
        assert (pr["tp"], pr["fp"], pr["fn"], pr["tn"]) == (1, 1, 1, 3)
        assert pr["precision"] == pytest.approx(0.5)
        assert pr["recall"] == pytest.approx(0.5)
        assert pr["support"] == 2

    def test_absent_code_has_undefined_precision(self, agreement_workspace):
        agreement = self._agreement(agreement_workspace)
        pr = agreement["conflicts"]["welfare"]
        assert (pr["tp"], pr["fp"], pr["fn"]) == (0, 0, 0)
        assert pr["precision"] is None and pr["recall"] is None

    def test_error_coded_grader_rows_excluded(self, tmp_path):
        write_edits(tmp_path / "edits.jsonl", [make_edit("e1"), make_edit("e2")])
        write_key(tmp_path / "blind_key.csv",
                  [("bid10000", "e1", False), ("bid20000", "e2", False)])
        write_sheet(
            tmp_path / "coding_sheet_p.csv",
            [
                sheet_row(1, "bid10000", judge="1", patienthood="not_present",
                          confidence="2"),
                sheet_row(2, "bid20000", judge="0", patienthood="not_present",
                          confidence="2"),
            ],
        )
        write_codes(
            tmp_path / "grader.jsonl",
            {"e1": make_coding(judge=1), "e2": None},  # e2 = error row
        )
        sheet = hv.parse_sheet(tmp_path / "coding_sheet_p.csv")
        hv.unblind(sheet, hv.load_blind_key(tmp_path / "blind_key.csv"))
        agreement = hv.grader_agreement(sheet, hv.load_grader(tmp_path / "grader.jsonl"))
        assert agreement["n"] == 1  # only e1 pairs up


# ---------------------------------------------------------------------------
# Human-human kappa
# ---------------------------------------------------------------------------


class TestHumanHuman:
    def test_judge_kappa_known_value(self, tmp_path):
        # Judge sequences [0,1,0,1] vs [0,1,1,1]: kappa = 0.5 (hand value,
        # same arithmetic as test_stats.TestCohenKappa).
        a_vals, b_vals = ["0", "1", "0", "1"], ["0", "1", "1", "1"]
        key_entries = []
        rows_a, rows_b = [], []
        for i in range(4):
            blind_id = f"bid{i}0000"
            key_entries.append((blind_id, f"e{i}", False))
            rows_a.append(sheet_row(i + 1, blind_id, judge=a_vals[i],
                                    patienthood="not_present", confidence="2"))
            rows_b.append(sheet_row(i + 1, blind_id, judge=b_vals[i],
                                    patienthood="not_present", confidence="2"))
        write_key(tmp_path / "blind_key.csv", key_entries)
        key = hv.load_blind_key(tmp_path / "blind_key.csv")
        sheet_a = hv.parse_sheet(write_sheet(tmp_path / "coding_sheet_a.csv", rows_a))
        sheet_b = hv.parse_sheet(write_sheet(tmp_path / "coding_sheet_b.csv", rows_b))
        hv.unblind(sheet_a, key)
        hv.unblind(sheet_b, key)
        pairs = hv.human_human_agreement([sheet_a, sheet_b])
        assert len(pairs) == 1
        assert pairs[0]["n_common"] == 4
        assert pairs[0]["dimensions"]["judge"]["kappa"] == pytest.approx(0.5)
        # patienthood is constant and identical -> kappa undefined, not crash
        assert pairs[0]["dimensions"]["patienthood"]["kappa"] is None

    def test_single_sheet_yields_no_pairs(self, tmp_path):
        write_key(tmp_path / "blind_key.csv", [("bid00000", "e0", False)])
        sheet = hv.parse_sheet(
            write_sheet(
                tmp_path / "coding_sheet_a.csv",
                [sheet_row(1, "bid00000", judge="0",
                           patienthood="not_present", confidence="1")],
            )
        )
        hv.unblind(sheet, hv.load_blind_key(tmp_path / "blind_key.csv"))
        assert hv.human_human_agreement([sheet]) == []


# ---------------------------------------------------------------------------
# Directional error by provider
# ---------------------------------------------------------------------------


class TestDirectionalError:
    def test_grader_overcodes_plus1_on_anthropic(self, tmp_path):
        """Grader codes +1 where the human said 0 on every Anthropic edit;
        agrees exactly on every OpenAI edit."""
        edits = [
            make_edit("a1", model="Claude Opus 4.7", provider="anthropic"),
            make_edit("a2", model="Claude Opus 4.7", provider="anthropic"),
            make_edit("a3", model="Claude Opus 4.7", provider="anthropic"),
            make_edit("o1", model="GPT-5.5", provider="openai"),
            make_edit("o2", model="GPT-5.5", provider="openai"),
            make_edit("o3", model="GPT-5.5", provider="openai"),
        ]
        write_edits(tmp_path / "edits.jsonl", edits)
        write_key(
            tmp_path / "blind_key.csv",
            [(f"bid{i}0000", e["edit_id"], False) for i, e in enumerate(edits)],
        )
        rows = []
        for i, edit in enumerate(edits):
            rows.append(sheet_row(i + 1, f"bid{i}0000", judge="0",
                                  patienthood="not_present", confidence="3"))
        write_sheet(tmp_path / "coding_sheet_p.csv", rows)
        grader = {
            "a1": make_coding(judge=1), "a2": make_coding(judge=1),
            "a3": make_coding(judge=1),
            "o1": make_coding(judge=0), "o2": make_coding(judge=0),
            "o3": make_coding(judge=0),
        }
        write_codes(tmp_path / "grader.jsonl", grader)

        sheet = hv.parse_sheet(tmp_path / "coding_sheet_p.csv")
        hv.unblind(sheet, hv.load_blind_key(tmp_path / "blind_key.csv"))
        directional = hv.directional_error(
            sheet,
            hv.load_grader(tmp_path / "grader.jsonl"),
            hv.load_edits_meta(tmp_path / "edits.jsonl"),
        )
        anth = directional["per_provider"]["anthropic"]
        oai = directional["per_provider"]["openai"]
        assert anth["n"] == 3 and anth["mean_diff"] == pytest.approx(1.0)
        assert anth["n_grader_higher"] == 3
        assert anth["n_grader_plus1_human_not"] == 3
        assert oai["mean_diff"] == pytest.approx(0.0)
        assert oai["n_grader_higher"] == 0
        contrast = directional["anthropic_vs_rest"]
        assert contrast["difference"] == pytest.approx(1.0)
        assert contrast["anthropic_n"] == 3 and contrast["rest_n"] == 3


# ---------------------------------------------------------------------------
# Disagreement ranking
# ---------------------------------------------------------------------------


class TestDisagreements:
    def test_sign_flips_rank_first_then_patienthood_distance(self, tmp_path):
        edits = [make_edit(e) for e in ("flip", "mid", "pat", "agree")]
        write_edits(tmp_path / "edits.jsonl", edits)
        write_key(
            tmp_path / "blind_key.csv",
            [
                ("bidflip0", "flip", True),  # also an adjudication extra
                ("bidmid00", "mid", False),
                ("bidpat00", "pat", False),
                ("bidagree", "agree", False),
            ],
        )
        rows = [
            sheet_row(1, "bidflip0", judge="1", patienthood="not_present",
                      confidence="3"),
            sheet_row(2, "bidmid00", judge="1", patienthood="not_present",
                      confidence="3"),
            sheet_row(3, "bidpat00", judge="0", patienthood="deny",
                      confidence="3"),
            sheet_row(4, "bidagree", judge="0", patienthood="not_present",
                      confidence="3"),
        ]
        write_sheet(tmp_path / "coding_sheet_p.csv", rows)
        grader = {
            "flip": make_coding(judge=-1, locus="spec"),        # sign flip (sev 2)
            "mid": make_coding(judge=0),                        # sev 1
            "pat": make_coding(judge=0, patienthood="affirm"),  # pat distance 3
            "agree": make_coding(judge=0),                      # no disagreement
        }
        write_codes(tmp_path / "grader.jsonl", grader)

        sheet = hv.parse_sheet(tmp_path / "coding_sheet_p.csv")
        hv.unblind(sheet, hv.load_blind_key(tmp_path / "blind_key.csv"))
        top = hv.rank_disagreements(
            [sheet],
            {"g": hv.load_grader(tmp_path / "grader.jsonl")},
            hv.load_edits_meta(tmp_path / "edits.jsonl"),
        )
        assert [d["edit_id"] for d in top] == ["flip", "mid", "pat"]
        assert top[0]["judge_severity"] == 2
        assert top[0]["adjudication_extra"] is True  # included but flagged
        assert top[2]["patienthood_distance"] == 3
        # Text excerpts are attached from edits.jsonl.
        assert "original text of flip" in top[0]["original_excerpt"]

    def test_patienthood_distance_encoding(self):
        assert hv.patienthood_distance("deny", "affirm") == 3
        assert hv.patienthood_distance("hedge", "affirm") == 1
        assert hv.patienthood_distance("not_present", "not_present") == 0
        assert hv.patienthood_distance(None, "affirm") == 0


# ---------------------------------------------------------------------------
# CLI end-to-end
# ---------------------------------------------------------------------------


class TestCLI:
    def test_end_to_end_report_and_json(self, tmp_path, agreement_workspace):
        ws = agreement_workspace
        # A second coder who disagrees with coder 1 on e3 and leaves e6 uncoded.
        rows = []
        judges = {"e1": "1", "e2": "1", "e3": "1", "e4": "-1", "e5": "0"}
        for i in range(1, 7):
            eid = f"e{i}"
            if eid in judges:
                kwargs = {"judge": judges[eid], "patienthood": "not_present",
                          "confidence": "2"}
                if judges[eid] == "-1":
                    kwargs["external_locus"] = "spec"
                rows.append(sheet_row(i, f"bid{i}0000", **kwargs))
            else:
                rows.append(sheet_row(i, f"bid{i}0000"))  # uncoded
        write_sheet(ws / "coding_sheet_second.csv", rows)
        # A second grader identical to the human (perfect agreement).
        grader2 = {
            "e1": make_coding(judge=1, conflicts=["paternalism"]),
            "e2": make_coding(judge=1, conflicts=["paternalism"]),
            "e3": make_coding(judge=0),
            "e4": make_coding(judge=-1, locus="spec"),
            "e5": make_coding(judge=0),
            "e6": make_coding(judge=1),
        }
        write_codes(ws / "grader2.jsonl", grader2)

        out = tmp_path / "C_human_validation.md"
        json_out = tmp_path / "C_human_validation.json"
        analysis = hv.main(
            [
                "--sheets",
                str(ws / "coding_sheet_peter.csv"),
                str(ws / "coding_sheet_second.csv"),
                "--blind-key", str(ws / "blind_key.csv"),
                "--graders",
                f"gemma={ws / 'grader.jsonl'}",
                f"qwen={ws / 'grader2.jsonl'}",
                "--edits", str(ws / "edits.jsonl"),
                "--out", str(out),
                "--json", str(json_out),
            ]
        )
        assert out.exists() and json_out.exists()
        report = out.read_text(encoding="utf-8")
        # Section presence.
        assert "## 1. Sheet parsing summary" in report
        assert "## 2. Human-human agreement" in report
        assert "## 3. Human vs grader" in report
        assert "## 4. Per-conflict-code precision/recall" in report
        assert "## 5. Directional error by editing provider" in report
        assert "largest disagreements" in report
        assert "Adjudication note" in report
        # The second sheet's uncoded row is counted.
        second = [s for s in analysis["sheets"] if s["coder"] == "second"][0]
        assert second["uncoded_count"] == 1
        # 2 coders x 2 graders = 4 comparison cells.
        assert len(analysis["human_vs_grader"]) == 4
        # Perfect-agreement grader vs coder 1: kappa 1 on judge.
        cell = [
            c for c in analysis["human_vs_grader"]
            if c["coder"] == "peter" and c["grader"] == "qwen"
        ][0]
        assert cell["agreement"]["judge"]["kappa"] == pytest.approx(1.0)
        # JSON round-trips.
        loaded = json.loads(json_out.read_text(encoding="utf-8"))
        assert loaded["meta"]["grader_paths"].keys() == {"gemma", "qwen"}

    def test_bad_grader_arg_rejected(self, tmp_path, agreement_workspace):
        with pytest.raises(SystemExit):
            hv.main(
                [
                    "--sheets", str(agreement_workspace / "coding_sheet_peter.csv"),
                    "--blind-key", str(agreement_workspace / "blind_key.csv"),
                    "--graders", "no_equals_sign",
                    "--edits", str(agreement_workspace / "edits.jsonl"),
                    "--out", str(tmp_path / "r.md"),
                ]
            )
