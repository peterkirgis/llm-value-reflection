"""Tests for recode/src/ppi_analysis.py (Workstream C4, Appendix VI).

All fixtures are synthetic; nothing reads the live grading outputs
(v2_gemma.jsonl / v2_qwen.jsonl) or the real human sheets. The PPI n = N
reduction extends the stats-level test through the full CLI path with a
synthetic sheet.
"""

import csv
import json

import numpy as np
import pytest

import ppi_analysis as ppa
from human_validation import SHEET_COLUMNS
from stats import ppi_mean_manual

MODEL = "Claude Opus 4.7"


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def sheet_row(sheet_row_n, blind_id, judge=None, patienthood="not_present",
              confidence="3", conflicts=(), conflict_slots=None):
    row = {c: "" for c in SHEET_COLUMNS}
    row["sheet_row"] = str(sheet_row_n)
    row["blind_id"] = blind_id
    row["document_id"] = "claude_constitution"
    row["original_text"] = f"original {blind_id}"
    row["changed_text"] = f"changed {blind_id}"
    if judge is not None:
        row["judge"] = str(judge)
        row["patienthood"] = patienthood
        row["confidence"] = confidence
        if str(judge) == "-1":
            row["external_locus"] = "spec"
        slots = conflict_slots or list(range(1, len(conflicts) + 1))
        for slot, code in zip(slots, conflicts):
            row[f"conflict{slot}_code"] = code
            row[f"conflict{slot}_cost_bearer"] = "user_stated"
            row[f"conflict{slot}_served_party"] = "user_idealized"
            row[f"conflict{slot}_mechanism"] = "adds_protection"
    return row


def make_edit(edit_id, model=MODEL, provider="anthropic", apply_status="applied"):
    return {
        "edit_id": edit_id,
        "model": model,
        "provider": provider,
        "document_id": "claude_constitution",
        "apply_status": apply_status,
        "find_text": f"original text of {edit_id}",
        "replace_text_sanitized": f"changed text of {edit_id}",
    }


def make_coding(judge=0, locus=None, patienthood="not_present", conflicts=()):
    return {
        "summary": "synthetic",
        "judge": {"score": judge, "external_locus": locus, "evidence": "e"},
        "patienthood": {"level": patienthood, "evidence": ""},
        "conflicts": [
            {
                "code": code,
                "cost_bearer": "user_stated",
                "served_party": "user_idealized",
                "mechanism": "adds_protection",
                "cost_clause": "clause",
            }
            for code in conflicts
        ],
    }


def build_workspace(
    tmp_path,
    y,                      # human judge per edit e1..eK (coder 1)
    f,                      # predictor judge per edit (None = no code)
    extras=(),              # edit indices (1-based) flagged adjudication_extra
    uncoded=(),             # edit indices left uncoded in the sheet
    human_conflicts=None,   # edit index -> (conflicts, slots)
    y2=None,                # optional second coder's judge values
):
    n = len(y)
    edits = [make_edit(f"e{i}") for i in range(1, n + 1)]
    with open(tmp_path / "edits.jsonl", "w", encoding="utf-8") as handle:
        for edit in edits:
            handle.write(json.dumps(edit) + "\n")

    with open(tmp_path / "blind_key.csv", "w", encoding="utf-8",
              newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["blind_id", "edit_id", "adjudication_extra"]
        )
        writer.writeheader()
        for i in range(1, n + 1):
            writer.writerow(
                {
                    "blind_id": f"bid{i:04d}",
                    "edit_id": f"e{i}",
                    "adjudication_extra": "true" if i in extras else "false",
                }
            )

    def write_sheet(name, judges):
        rows = []
        for i in range(1, n + 1):
            if i in uncoded:
                rows.append(sheet_row(i, f"bid{i:04d}"))
                continue
            conflicts, slots = (human_conflicts or {}).get(i, ((), None))
            rows.append(
                sheet_row(i, f"bid{i:04d}", judge=judges[i - 1],
                          conflicts=conflicts, conflict_slots=slots)
            )
        with open(tmp_path / name, "w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=SHEET_COLUMNS)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

    write_sheet("coding_sheet_coder1.csv", y)
    if y2 is not None:
        write_sheet("coding_sheet_coder2.csv", y2)

    with open(tmp_path / "predictor.jsonl", "w", encoding="utf-8") as handle:
        for i in range(1, n + 1):
            if f[i - 1] is None:
                continue
            locus = "spec" if f[i - 1] == -1 else None
            handle.write(
                json.dumps(
                    {
                        "edit_id": f"e{i}",
                        "coding": make_coding(judge=f[i - 1], locus=locus),
                    }
                )
                + "\n"
            )
    return tmp_path


def run_cli(ws, sheets=("coding_sheet_coder1.csv",)):
    out = ws / "C_ppi.md"
    json_out = ws / "C_ppi.json"
    analysis = ppa.main(
        [
            "--sheets", *[str(ws / s) for s in sheets],
            "--blind-key", str(ws / "blind_key.csv"),
            "--predictor", str(ws / "predictor.jsonl"),
            "--edits", str(ws / "edits.jsonl"),
            "--out", str(out),
            "--json", str(json_out),
        ]
    )
    return analysis, out, json_out


# ---------------------------------------------------------------------------
# The n = N reduction, through the CLI path
# ---------------------------------------------------------------------------


class TestReductionToClassical:
    def test_n_equals_N_ppi_equals_classical_human_mean(self, tmp_path):
        """When the humans label ALL N units, PPI must reduce to the
        classical human-only estimate — even with a biased predictor
        (extends stats.TestPPI through the CLI with a synthetic sheet)."""
        y = [1, 0, 1, -1, 0, 1, 0, 1]
        f = [1, 0, 1, -1, 0, 1, 1, -1]  # disagrees on e7, e8
        ws = build_workspace(tmp_path, y=y, f=f)
        analysis, _, json_out = run_cli(ws)
        cell = analysis["primary"]["estimands"]["mean_judge"]["models"][MODEL]
        expected = float(np.mean(y))
        assert cell["n_labeled"] == len(y) == cell["N_graded"]
        assert cell["ppi"]["point"] == pytest.approx(expected, abs=1e-9)
        assert cell["human"]["point"] == pytest.approx(expected, abs=1e-9)
        # The naive grader estimate is the (biased) grader mean, not y's.
        assert cell["naive"]["point"] == pytest.approx(float(np.mean(f)))
        assert cell["ppi"]["impl"] in {"ppi_py", "manual"}
        # And the same numbers round-trip through the JSON artifact.
        loaded = json.loads(json_out.read_text(encoding="utf-8"))
        assert loaded["primary"]["estimands"]["mean_judge"]["models"][MODEL][
            "ppi"
        ]["point"] == pytest.approx(expected, abs=1e-9)

    def test_indicator_estimands_also_reduce(self, tmp_path):
        y = [1, 0, 1, -1, 0, 1, 0, 1]
        f = [0, 0, 0, 0, 0, 0, 0, 1]
        ws = build_workspace(tmp_path, y=y, f=f)
        analysis, _, _ = run_cli(ws)
        cell = analysis["primary"]["estimands"]["p_judge_plus1"]["models"][MODEL]
        assert cell["ppi"]["point"] == pytest.approx(4 / 8, abs=1e-9)
        cell = analysis["primary"]["estimands"]["p_judge_minus1"]["models"][MODEL]
        assert cell["ppi"]["point"] == pytest.approx(1 / 8, abs=1e-9)


# ---------------------------------------------------------------------------
# ppi_py vs the manual Appendix VI fallback
# ---------------------------------------------------------------------------


class TestPpiPyVsManual:
    def test_agreement_on_correlated_fixture(self):
        pytest.importorskip("ppi_py")
        rng = np.random.default_rng(11)
        y_all = rng.normal(size=1000)
        f_all = y_all + rng.normal(scale=0.1, size=1000)  # strong predictor
        idx = rng.choice(1000, size=200, replace=False)
        y, f_lab = y_all[idx], f_all[idx]

        via_pkg = ppa._ppi_via_ppi_py(y, f_lab, f_all)
        manual = ppi_mean_manual(y, f_lab, f_all)
        assert via_pkg["impl"] == "ppi_py"
        # Points agree to tolerance (PPI++ tuning lambda ~ 1 for a strong f).
        assert via_pkg["point"] == pytest.approx(manual["point"], abs=0.05)
        # Intervals overlap and both cover their point estimates.
        assert via_pkg["lo"] <= via_pkg["point"] <= via_pkg["hi"]
        assert manual["lo"] <= manual["point"] <= manual["hi"]
        assert via_pkg["lo"] <= manual["hi"] and manual["lo"] <= via_pkg["hi"]

    def test_ppi_py_path_actually_runs(self):
        pytest.importorskip("ppi_py")
        rng = np.random.default_rng(12)
        y = rng.integers(0, 2, size=15).astype(float)
        f_lab = y.copy()
        f_lab[0] = 1 - f_lab[0]
        f_all = rng.integers(0, 2, size=250).astype(float)
        out = ppa.ppi_estimate(list(y), list(f_lab), list(f_all))
        assert out["impl"] == "ppi_py"
        assert out["lo"] <= out["point"] <= out["hi"]

    def test_manual_fallback_on_degenerate_predictor(self):
        # A constant predictor makes the PPI++ tuning lambda 0/0 (nan) in
        # ppi_py; ppi_estimate must fall back to the Appendix VI manual
        # estimator rather than propagate nan.
        y = [1.0, 0.0, 1.0, 0.0]
        f_lab = [1.0, 1.0, 1.0, 1.0]
        f_all = [1.0] * 8
        out = ppa.ppi_estimate(y, f_lab, f_all)
        assert out["impl"] in {"manual", "ppi_py"}
        assert out["point"] is not None and np.isfinite(out["point"])
        assert np.isfinite(out["lo"]) and np.isfinite(out["hi"])
        if out["impl"] == "manual":
            expected = ppi_mean_manual(y, f_lab, f_all)
            assert out["point"] == pytest.approx(expected["point"])

    def test_too_few_labels_yields_na(self):
        # ppi_estimate refuses n < 2 outright.
        out = ppa.ppi_estimate([1.0], [1.0], [1.0, 0.0])
        assert out["point"] is None and out["impl"] is None


# ---------------------------------------------------------------------------
# Frame rules: extras excluded, partial coding, hard assertions
# ---------------------------------------------------------------------------


class TestFrame:
    def test_adjudication_extras_excluded_from_ppi(self, tmp_path):
        y = [1, 0, 1, -1, 0, 1, 0, 1, 1, 1]  # e9, e10 coded but extras
        f = [1, 0, 1, -1, 0, 1, 0, 1, 1, 1]
        ws = build_workspace(tmp_path, y=y, f=f, extras=(9, 10))
        analysis, out, _ = run_cli(ws)
        cell = analysis["primary"]["estimands"]["mean_judge"]["models"][MODEL]
        assert cell["n_labeled"] == 8  # not 10
        assert analysis["meta"]["frame"]["n_extra_excluded"] == 2
        # Human-only point uses only the 8 random-draw rows.
        assert cell["human"]["point"] == pytest.approx(float(np.mean(y[:8])))
        # The draw size the frame is checked against also excludes extras.
        assert analysis["meta"]["frame"]["per_model_draw"][MODEL] == 8
        assert "EXCLUDED" in out.read_text(encoding="utf-8")

    def test_partially_coded_sheet_uses_coded_rows_only(self, tmp_path):
        y = [1, 0, 1, -1, 0, 1, 0, 1]
        f = [1, 0, 1, -1, 0, 1, 0, 1]
        ws = build_workspace(tmp_path, y=y, f=f, uncoded=(7, 8))
        analysis, out, _ = run_cli(ws)
        cell = analysis["primary"]["estimands"]["mean_judge"]["models"][MODEL]
        assert cell["n_labeled"] == 6
        assert analysis["meta"]["frame"]["n_uncoded_excluded"] == 2
        assert analysis["meta"]["frame"]["per_model_n"][MODEL] == 6
        # Per-model n is reported in the markdown table.
        assert f"| {MODEL} | 8 | 6 |" in out.read_text(encoding="utf-8")

    def test_frame_rejects_non_applied_edit(self, tmp_path):
        y = [1, 0]
        f = [1, 0]
        ws = build_workspace(tmp_path, y=y, f=f)
        # Corrupt the edits file: e2 is no longer an applied edit.
        edits = [make_edit("e1"), make_edit("e2", apply_status="find_not_found")]
        with open(ws / "edits.jsonl", "w", encoding="utf-8") as handle:
            for edit in edits:
                handle.write(json.dumps(edit) + "\n")
        with pytest.raises(ppa.PPIFrameError):
            run_cli(ws)

    def test_frame_rejects_duplicate_labeled_edit(self, tmp_path):
        ws = build_workspace(tmp_path, y=[1, 0], f=[1, 0])
        # Append a duplicate coded row pointing at e1's blind id.
        with open(ws / "coding_sheet_coder1.csv", "a", encoding="utf-8",
                  newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=SHEET_COLUMNS)
            writer.writerow(sheet_row(3, "bid0001", judge=1))
        with pytest.raises(ppa.PPIFrameError):
            run_cli(ws)

    def test_labeled_edit_without_predictor_code_dropped_and_reported(
        self, tmp_path
    ):
        y = [1, 0, 1, -1, 0, 1, 0, 1]
        f = [1, 0, 1, -1, None, 1, 0, 1]  # predictor never coded e5
        ws = build_workspace(tmp_path, y=y, f=f)
        analysis, out, _ = run_cli(ws)
        assert analysis["meta"]["dropped_no_predictor_code"] == ["e5"]
        cell = analysis["primary"]["estimands"]["mean_judge"]["models"][MODEL]
        assert cell["n_labeled"] == 7
        assert "e5" in out.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Estimand mechanics
# ---------------------------------------------------------------------------


class TestEstimands:
    def test_drift20_is_20x_mean_judge(self, tmp_path):
        y = [1, 0, 1, -1, 0, 1, 0, 1]
        f = [1, 0, 1, -1, 0, 1, 1, -1]
        ws = build_workspace(tmp_path, y=y, f=f)
        analysis, out, _ = run_cli(ws)
        mean_cell = analysis["primary"]["estimands"]["mean_judge"]["models"][MODEL]
        drift_cell = analysis["primary"]["estimands"]["drift20"]["models"][MODEL]
        for estimator in ("naive", "ppi", "human"):
            assert drift_cell[estimator]["point"] == pytest.approx(
                20.0 * mean_cell[estimator]["point"]
            )
            assert drift_cell[estimator]["lo"] == pytest.approx(
                20.0 * mean_cell[estimator]["lo"]
            )
        # The stated caveat reaches the report.
        report = out.read_text(encoding="utf-8")
        assert "run-level" in report and "multiplied by 20" in report

    def test_conflict_estimand_counts_any_block_with_code(self, tmp_path):
        y = [0] * 8
        f = [0] * 8
        # Human paternalism on e1 (block 1), e2 (block 2 only -> normalized),
        # e3 (block 1); nothing elsewhere.
        human_conflicts = {
            1: (("paternalism",), None),
            2: (("paternalism",), [2]),
            3: (("paternalism", "welfare"), None),
        }
        ws = build_workspace(tmp_path, y=y, f=f, human_conflicts=human_conflicts)
        analysis, _, _ = run_cli(ws)
        pat = analysis["primary"]["estimands"]["p_conflict_paternalism"]
        assert pat["models"][MODEL]["human"]["point"] == pytest.approx(3 / 8)
        wel = analysis["primary"]["estimands"]["p_conflict_welfare"]
        assert wel["models"][MODEL]["human"]["point"] == pytest.approx(1 / 8)
        # Predictor coded no conflicts at all.
        assert pat["models"][MODEL]["naive"]["point"] == pytest.approx(0.0)

    def test_classical_ci_is_t_based(self):
        from scipy.stats import t as t_dist

        values = [1.0, 0.0, 1.0, 1.0, 0.0]
        out = ppa.classical_ci(values)
        arr = np.asarray(values)
        se = arr.std(ddof=1) / np.sqrt(5)
        half = t_dist.ppf(0.975, 4) * se
        assert out["point"] == pytest.approx(0.6)
        assert out["lo"] == pytest.approx(0.6 - half)
        assert out["hi"] == pytest.approx(0.6 + half)

    def test_convention_statement_in_report(self, tmp_path):
        ws = build_workspace(tmp_path, y=[1, 0, 1], f=[1, 0, 1])
        _, out, _ = run_cli(ws)
        report = out.read_text(encoding="utf-8")
        assert "Primary Y = coder 1" in report
        assert "coder1" in report  # the coder's name is stated


# ---------------------------------------------------------------------------
# Two-coder sensitivity appendix
# ---------------------------------------------------------------------------


class TestSensitivity:
    def test_coder2_and_row_mean_runs(self, tmp_path):
        y1 = [1, 0, 1, -1, 0, 1, 0, 1]
        y2 = [1, 1, 1, -1, 0, 0, 0, 1]  # differs on e2 and e6
        f = [1, 0, 1, -1, 0, 1, 0, 1]
        ws = build_workspace(tmp_path, y=y1, f=f, y2=y2)
        analysis, out, _ = run_cli(
            ws, sheets=("coding_sheet_coder1.csv", "coding_sheet_coder2.csv")
        )
        assert "coder 2 (coder2)" in analysis["sensitivity"]
        assert "row-mean of coders" in analysis["sensitivity"]
        # Coder-2 human-only point.
        c2 = analysis["sensitivity"]["coder 2 (coder2)"]
        assert c2["estimands"]["mean_judge"]["models"][MODEL]["human"][
            "point"
        ] == pytest.approx(float(np.mean(y2)))
        # Row-mean = mean of the two coders' values, per row.
        rm = analysis["sensitivity"]["row-mean of coders"]
        expected = float(np.mean([(a + b) / 2 for a, b in zip(y1, y2)]))
        assert rm["estimands"]["mean_judge"]["models"][MODEL]["human"][
            "point"
        ] == pytest.approx(expected)
        report = out.read_text(encoding="utf-8")
        assert "Sensitivity appendix" in report
        assert "row-mean of coders" in report

    def test_row_mean_restricted_to_rows_both_coded(self, tmp_path):
        y1 = [1, 0, 1, -1]
        y2 = [1, 0, 1, -1]
        ws = build_workspace(tmp_path, y=y1, f=[1, 0, 1, -1], y2=y2)
        # Coder 2 leaves e4 uncoded: rewrite their sheet with row 4 blank.
        rows = []
        for i in range(1, 5):
            if i == 4:
                rows.append(sheet_row(i, f"bid{i:04d}"))
            else:
                rows.append(sheet_row(i, f"bid{i:04d}", judge=y2[i - 1]))
        with open(ws / "coding_sheet_coder2.csv", "w", encoding="utf-8",
                  newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=SHEET_COLUMNS)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
        analysis, _, _ = run_cli(
            ws, sheets=("coding_sheet_coder1.csv", "coding_sheet_coder2.csv")
        )
        rm = analysis["sensitivity"]["row-mean of coders"]
        cell = rm["estimands"]["mean_judge"]["models"][MODEL]
        assert cell["n_labeled"] == 3  # e4 excluded: not coded by both
        assert cell["human"]["point"] == pytest.approx(float(np.mean(y1[:3])))

    def test_single_sheet_skips_sensitivity(self, tmp_path):
        ws = build_workspace(tmp_path, y=[1, 0, 1], f=[1, 0, 1])
        analysis, out, _ = run_cli(ws)
        assert analysis["sensitivity"] == {}
        assert "skipped" in out.read_text(encoding="utf-8")
