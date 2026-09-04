"""Tests for recode/src/intergrader.py (Workstream B3).

Synthetic fixtures only — nothing here reads the real codes files (the two
FULL grading runs may still be writing v2_gemma.jsonl / v2_qwen.jsonl).

Covers, per the assignment:
- Cohen's kappa on the classic 2x2 example with hand-computed kappa = 0.4,
  and the both-valid denominator rule;
- Krippendorff's alpha cross-checked against the krippendorff package on the
  textbook 3-coder matrix (nominal alpha = 0.691358...);
- the COI difference on a constructed fixture (chains resampled, exact rates,
  degenerate CI, exclusion of invalid codings);
- ensemble flag logic, including missing- and invalid-qwen rows, invalid
  primary rows, presence-not-count conflict comparison, and last-row-wins
  loading through the shared codes_io interface;
- an end-to-end CLI smoke test over a tiny synthetic corpus.
"""

import json

import numpy as np
import pytest

import codes_io
import intergrader
from intergrader import (
    CONFLICT_CODES,
    agreement_block,
    build_ensemble_rows,
    coi_test,
    coi_verdict,
    ensemble_summary,
    kripp_alpha_from_labels,
    pairwise_kappa,
    write_ensemble,
)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def make_coding(judge=0, pat="not_present", conflicts=()):
    return {
        "summary": "synthetic",
        "judge": {"score": judge, "external_locus": None, "evidence": ""},
        "patienthood": {"level": pat, "evidence": ""},
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


def make_row(edit_id, coding, error=None):
    return {"edit_id": edit_id, "coding": coding, "error": error}


def write_jsonl(path, rows):
    with open(path, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def codings_from(pairs):
    """{edit_id: valid coding} from (edit_id, coding) pairs."""
    return dict(pairs)


# ---------------------------------------------------------------------------
# Cohen's kappa
# ---------------------------------------------------------------------------


class TestKappa:
    def test_classic_2x2_known_kappa(self):
        """The classic 2x2 table: 20 (+,+), 5 (+,-), 10 (-,+), 15 (-,-).

        p_o = 35/50 = 0.7; p_e = 0.5*0.6 + 0.5*0.4 = 0.5;
        kappa = (0.7 - 0.5) / (1 - 0.5) = 0.4 exactly.
        """
        labels_a, labels_b = {}, {}
        cells = [(1, 1, 20), (1, -1, 5), (-1, 1, 10), (-1, -1, 15)]
        i = 0
        for a, b, count in cells:
            for _ in range(count):
                labels_a[f"e{i}"] = a
                labels_b[f"e{i}"] = b
                i += 1
        out = pairwise_kappa(labels_a, labels_b)
        assert out["n"] == 50
        assert out["agreement"] == pytest.approx(0.7)
        assert out["kappa"] == pytest.approx(0.4)

    def test_classic_2x2_through_agreement_block(self):
        """Same table via full codings on the judge dimension."""
        grader_a, grader_b = {}, {}
        cells = [(1, 1, 20), (1, -1, 5), (-1, 1, 10), (-1, -1, 15)]
        i = 0
        for a, b, count in cells:
            for _ in range(count):
                grader_a[f"e{i}"] = make_coding(judge=a)
                grader_b[f"e{i}"] = make_coding(judge=b)
                i += 1
        universe = set(grader_a)
        block = agreement_block({"gemma": grader_a, "qwen": grader_b}, universe)
        judge = block["dimensions"]["judge"]["pairwise"]["gemma|qwen"]
        assert judge["n"] == 50
        assert judge["kappa"] == pytest.approx(0.4)
        assert block["n_complete_all_graders"] == 50

    def test_denominator_is_both_valid_only(self):
        """Edits where one grader lacks a valid coding are excluded from n."""
        grader_a = {f"e{i}": make_coding(judge=1) for i in range(10)}
        grader_b = {f"e{i}": make_coding(judge=1) for i in range(6)}  # 4 missing
        universe = {f"e{i}" for i in range(12)}  # 2 edits neither grader coded
        block = agreement_block({"gemma": grader_a, "qwen": grader_b}, universe)
        judge = block["dimensions"]["judge"]["pairwise"]["gemma|qwen"]
        assert judge["n"] == 6
        assert block["n_universe"] == 12
        assert block["per_grader_valid"] == {"gemma": 10, "qwen": 6}
        assert block["n_complete_all_graders"] == 6

    def test_undefined_kappa_is_none_agreement_still_reported(self):
        """Both graders constant and identical -> kappa undefined (None),
        observed agreement 1.0 — the disclosure-never-coded case."""
        grader_a = {f"e{i}": make_coding(judge=0) for i in range(5)}
        grader_b = {f"e{i}": make_coding(judge=0) for i in range(5)}
        block = agreement_block({"a": grader_a, "b": grader_b}, set(grader_a))
        disclosure = block["dimensions"]["conflict:disclosure"]["pairwise"]["a|b"]
        assert disclosure["kappa"] is None
        assert disclosure["agreement"] == pytest.approx(1.0)

    def test_conflict_dimension_is_presence_based(self):
        """Two conflicts of one code vs one conflict of it agree on presence."""
        grader_a = {
            "e0": make_coding(conflicts=("paternalism", "paternalism")),
            "e1": make_coding(conflicts=("welfare",)),
        }
        grader_b = {
            "e0": make_coding(conflicts=("paternalism",)),
            "e1": make_coding(),
        }
        block = agreement_block({"a": grader_a, "b": grader_b}, {"e0", "e1"})
        pat = block["dimensions"]["conflict:paternalism"]["pairwise"]["a|b"]
        assert pat["agreement"] == pytest.approx(1.0)  # presence matches on both
        welfare = block["dimensions"]["conflict:welfare"]["pairwise"]["a|b"]
        assert welfare["agreement"] == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Krippendorff's alpha
# ---------------------------------------------------------------------------

# The textbook example from the krippendorff package documentation
# (Krippendorff 2011, "Computing Krippendorff's Alpha-Reliability"):
# 3 coders x 15 units with missing values; nominal alpha = 0.691358...
TEXTBOOK_MATRIX = [
    [np.nan, np.nan, np.nan, np.nan, np.nan, 3, 4, 1, 2, 1, 1, 3, 3, np.nan, 3],
    [1, np.nan, 2, 1, 3, 3, 4, 3, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan],
    [np.nan, np.nan, 2, 1, 3, 4, 4, np.nan, 2, 1, 1, 3, 3, np.nan, 4],
]


class TestKrippAlpha:
    def test_textbook_matrix_cross_checked_against_package(self):
        import krippendorff

        units = [f"u{i:02d}" for i in range(15)]
        label_maps = {}
        for gi, grader in enumerate(["A", "B", "C"]):
            label_maps[grader] = {
                units[ui]: int(v)
                for ui, v in enumerate(TEXTBOOK_MATRIX[gi])
                if not np.isnan(v)
            }
        out = kripp_alpha_from_labels(label_maps, units)
        direct = float(
            krippendorff.alpha(
                reliability_data=TEXTBOOK_MATRIX, level_of_measurement="nominal"
            )
        )
        # cross-check against the package on the same matrix (nominal alpha is
        # invariant to the category -> integer relabeling the module applies)
        assert out["alpha"] == pytest.approx(direct, abs=1e-12)
        assert out["alpha"] == pytest.approx(0.691358, abs=1e-6)
        # Ns: hand-counted from the matrix
        assert out["n_pairable"] == 12
        assert out["n_complete"] == 2
        assert out["n_any"] == 13

    def test_perfect_agreement_alpha_one(self):
        units = ["e0", "e1", "e2", "e3"]
        maps = {
            "a": {"e0": "affirm", "e1": "deny", "e2": "affirm", "e3": "hedge"},
            "b": {"e0": "affirm", "e1": "deny", "e2": "affirm", "e3": "hedge"},
        }
        out = kripp_alpha_from_labels(maps, units)
        assert out["alpha"] == pytest.approx(1.0)
        assert out["n_pairable"] == 4

    def test_no_pairable_units_gives_none(self):
        out = kripp_alpha_from_labels({"a": {"e0": 1}, "b": {"e1": 1}}, ["e0", "e1"])
        assert out["alpha"] is None
        assert out["n_pairable"] == 0

    def test_alpha_through_agreement_block_matches_direct(self):
        """agreement_block's per-dimension alpha equals the standalone helper."""
        grader_a = {f"e{i}": make_coding(judge=s) for i, s in enumerate([1, 0, -1, 1, 0])}
        grader_b = {f"e{i}": make_coding(judge=s) for i, s in enumerate([1, 0, 0, 1, -1])}
        universe = set(grader_a)
        block = agreement_block({"a": grader_a, "b": grader_b}, universe)
        maps = {
            "a": {e: c["judge"]["score"] for e, c in grader_a.items()},
            "b": {e: c["judge"]["score"] for e, c in grader_b.items()},
        }
        direct = kripp_alpha_from_labels(maps, sorted(universe))
        assert block["dimensions"]["judge"]["alpha"] == direct


# ---------------------------------------------------------------------------
# COI test
# ---------------------------------------------------------------------------


def coi_edit(run, model_id, provider, doc, cond, rnd):
    return {
        "edit_id": f"{run}|{cond}|{model_id}|{doc}|constitution|{rnd}",
        "run_id": run,
        "model_id": model_id,
        "provider": provider,
        "document_id": doc,
        "condition": cond,
        "round": rnd,
    }


class TestCOI:
    def build_fixture(self):
        """2 Gemini chains where the graders ALWAYS disagree on judge, and
        2 non-Gemini chains where they always agree -> difference exactly 1."""
        edits, gemma, qwen = [], {}, {}
        for chain_i in range(2):
            for rnd in range(1, 5):
                e = coi_edit("runA", f"google/gem-{chain_i}", "google",
                             "docG", "baseline", rnd)
                edits.append(e)
                gemma[e["edit_id"]] = make_coding(judge=1)
                qwen[e["edit_id"]] = make_coding(judge=-1)
        for chain_i in range(2):
            for rnd in range(1, 5):
                e = coi_edit("runA", f"openai/oth-{chain_i}", "openai",
                             "docO", "baseline", rnd)
                edits.append(e)
                gemma[e["edit_id"]] = make_coding(judge=0)
                qwen[e["edit_id"]] = make_coding(judge=0)
        return edits, gemma, qwen

    def test_constructed_difference_and_degenerate_ci(self):
        edits, gemma, qwen = self.build_fixture()
        out = coi_test(edits, gemma, qwen, B=200, seed=11)
        assert out["n_chains_gemini"] == 2
        assert out["n_chains_non_gemini"] == 2
        assert out["n_valid_edits_gemini"] == 8
        assert out["n_valid_edits_non_gemini"] == 8
        judge = out["dims"]["judge"]
        assert judge["rate_gemini"] == pytest.approx(1.0)
        assert judge["rate_non_gemini"] == pytest.approx(0.0)
        assert judge["difference"] == pytest.approx(1.0)
        # every chain in each group has the same rate -> degenerate CI
        assert judge["ci_lo"] == pytest.approx(1.0)
        assert judge["ci_hi"] == pytest.approx(1.0)
        assert judge["n_nan_draws"] == 0
        # patienthood always agrees -> zero rates on both sides
        pat = out["dims"]["patienthood"]
        assert pat["rate_gemini"] == pytest.approx(0.0)
        assert pat["difference"] == pytest.approx(0.0)
        # 'any' mirrors judge here
        assert out["dims"]["any"]["difference"] == pytest.approx(1.0)

    def test_verdict_statement(self):
        edits, gemma, qwen = self.build_fixture()
        out = coi_test(edits, gemma, qwen, B=100, seed=3)
        verdict = coi_verdict(out, "gemma", "qwen")
        assert "DOES diverge more" in verdict
        assert "gemma" in verdict and "qwen" in verdict

    def test_invalid_codings_excluded_but_chain_stays(self):
        edits, gemma, qwen = self.build_fixture()
        # extra Gemini chain where qwen never produced a valid coding
        for rnd in range(1, 5):
            e = coi_edit("runA", "google/gem-9", "google", "docG", "baseline", rnd)
            edits.append(e)
            gemma[e["edit_id"]] = make_coding(judge=1)
            # qwen: absent -> no valid coding
        out = coi_test(edits, gemma, qwen, B=100, seed=5)
        assert out["n_chains_gemini"] == 3  # chain still in the resampling frame
        assert out["n_valid_edits_gemini"] == 8  # its edits not in denominators
        # a draw of only the dead chain has no valid edits -> NaN, counted
        assert out["dims"]["judge"]["n_nan_draws"] > 0
        assert out["dims"]["judge"]["rate_gemini"] == pytest.approx(1.0)

    def test_conflict_presence_dimension(self):
        edits, gemma, qwen = [], {}, {}
        for rnd in range(1, 5):
            e = coi_edit("runB", "google/gem-0", "google", "docG", "baseline", rnd)
            edits.append(e)
            gemma[e["edit_id"]] = make_coding(judge=0, conflicts=("welfare",))
            qwen[e["edit_id"]] = make_coding(judge=0)  # welfare presence differs
        for rnd in range(1, 5):
            e = coi_edit("runB", "openai/oth-0", "openai", "docO", "baseline", rnd)
            edits.append(e)
            gemma[e["edit_id"]] = make_coding(judge=0, conflicts=("welfare",))
            qwen[e["edit_id"]] = make_coding(judge=0, conflicts=("welfare",))
        out = coi_test(edits, gemma, qwen, B=100, seed=1)
        conf = out["dims"]["conflict_presence"]
        assert conf["rate_gemini"] == pytest.approx(1.0)
        assert conf["rate_non_gemini"] == pytest.approx(0.0)
        assert out["dims"]["judge"]["difference"] == pytest.approx(0.0)

    def test_deterministic_under_seed(self):
        edits, gemma, qwen = self.build_fixture()
        a = coi_test(edits, gemma, qwen, B=150, seed=42)
        b = coi_test(edits, gemma, qwen, B=150, seed=42)
        assert a == b


# ---------------------------------------------------------------------------
# Ensemble
# ---------------------------------------------------------------------------


class TestEnsemble:
    def test_flags_per_dimension(self):
        gemma_coding = make_coding(judge=1, pat="affirm", conflicts=("paternalism",))
        qwen_coding = make_coding(judge=-1, pat="affirm", conflicts=("welfare",))
        rows = build_ensemble_rows(
            "gemma",
            {"e1": make_row("e1", gemma_coding)},
            {"qwen": {"e1": make_row("e1", qwen_coding)}},
        )
        assert len(rows) == 1
        row = rows[0]
        assert row["primary_grader"] == "gemma"
        assert row["primary_coding_valid"] is True
        assert row["coding"] == gemma_coding  # ensemble code IS the primary code
        assert row["qwen_coding"] == qwen_coding
        flags = row["disagrees_with_qwen"]
        assert flags["judge"] is True
        assert flags["patienthood"] is False
        assert flags["conflicts"]["paternalism"] is True   # gemma-only
        assert flags["conflicts"]["welfare"] is True       # qwen-only
        assert flags["conflicts"]["harmlessness"] is False
        assert flags["any"] is True

    def test_agreeing_edit_has_all_false_flags(self):
        coding = make_coding(judge=0, pat="hedge", conflicts=("structural",))
        rows = build_ensemble_rows(
            "gemma",
            {"e1": make_row("e1", coding)},
            {"qwen": {"e1": make_row("e1", make_coding(judge=0, pat="hedge",
                                                       conflicts=("structural",)))}},
        )
        flags = rows[0]["disagrees_with_qwen"]
        assert flags["judge"] is False and flags["patienthood"] is False
        assert not any(flags["conflicts"].values())
        assert flags["any"] is False

    def test_conflict_presence_not_count(self):
        """Two paternalism conflicts vs one -> presence equal -> no flag."""
        rows = build_ensemble_rows(
            "gemma",
            {"e1": make_row("e1", make_coding(conflicts=("paternalism", "paternalism")))},
            {"qwen": {"e1": make_row("e1", make_coding(conflicts=("paternalism",)))}},
        )
        flags = rows[0]["disagrees_with_qwen"]
        assert flags["conflicts"]["paternalism"] is False
        assert flags["any"] is False

    def test_missing_qwen_row_gives_null_flags(self):
        rows = build_ensemble_rows(
            "gemma",
            {"e1": make_row("e1", make_coding(judge=1))},
            {"qwen": {}},
        )
        row = rows[0]
        assert row["disagrees_with_qwen"] == {
            "judge": None, "patienthood": None, "conflicts": None, "any": None
        }
        assert row["qwen_coding"] is None
        assert row["primary_coding_valid"] is True

    def test_invalid_qwen_row_gives_null_flags(self):
        """A qwen row whose error field is set, and one with an out-of-range
        judge score, both count as 'lacking a valid qwen coding'."""
        for bad_row in (
            make_row("e1", None, error="transport: boom"),
            make_row("e1", make_coding(judge=5)),
        ):
            rows = build_ensemble_rows(
                "gemma",
                {"e1": make_row("e1", make_coding(judge=1))},
                {"qwen": {"e1": bad_row}},
            )
            row = rows[0]
            assert row["disagrees_with_qwen"]["judge"] is None
            assert row["qwen_coding"] is None

    def test_invalid_primary_row_carried_with_null_flags(self):
        rows = build_ensemble_rows(
            "gemma",
            {"e1": make_row("e1", None, error="transport: boom")},
            {"qwen": {"e1": make_row("e1", make_coding(judge=1))}},
        )
        row = rows[0]
        assert row["primary_coding_valid"] is False
        assert row["coding"] is None
        assert row["error"] == "transport: boom"
        assert row["disagrees_with_qwen"]["judge"] is None
        # the qwen coding is still carried for reference
        assert row["qwen_coding"] is not None

    def test_last_row_wins_through_codes_io_and_file_roundtrip(self, tmp_path):
        """Append-only convention: a retried gemma edit keeps its LAST row;
        the written ensemble file is itself readable through codes_io."""
        gemma_path = tmp_path / "gemma.jsonl"
        qwen_path = tmp_path / "qwen.jsonl"
        write_jsonl(gemma_path, [
            make_row("e1", None, error="transport: first attempt failed"),
            make_row("e1", make_coding(judge=1, pat="deny")),
            make_row("e2", make_coding(judge=0)),
        ])
        write_jsonl(qwen_path, [
            make_row("e1", make_coding(judge=1, pat="deny")),
            make_row("e2", make_coding(judge=-1)),
        ])
        gemma_rows = codes_io.load_codes(gemma_path)
        qwen_rows = codes_io.load_codes(qwen_path)
        rows = build_ensemble_rows("gemma", gemma_rows, {"qwen": qwen_rows})
        assert [r["edit_id"] for r in rows] == ["e1", "e2"]  # sorted, deduped
        assert rows[0]["primary_coding_valid"] is True       # last row won
        assert rows[0]["disagrees_with_qwen"]["any"] is False
        assert rows[1]["disagrees_with_qwen"]["judge"] is True

        out_path = tmp_path / "ensemble.jsonl"
        write_ensemble(out_path, rows)
        reloaded = codes_io.load_codes(out_path)
        assert set(reloaded) == {"e1", "e2"}
        assert codes_io.coding_of(reloaded["e1"]) is not None
        assert codes_io.judge_score(codes_io.coding_of(reloaded["e2"])) == 0

    def test_summary_counts(self):
        primary = {
            "e1": make_row("e1", make_coding(judge=1)),
            "e2": make_row("e2", make_coding(judge=0)),
            "e3": make_row("e3", None, error="boom"),
        }
        qwen = {
            "e1": make_row("e1", make_coding(judge=-1)),   # judge disagrees
            "e2": make_row("e2", make_coding(judge=0)),    # agrees
            # e3: primary invalid -> null flags
        }
        rows = build_ensemble_rows("gemma", primary, {"qwen": qwen})
        summary = ensemble_summary(rows, ["qwen"])
        assert summary["n_rows"] == 3
        assert summary["n_primary_valid"] == 2
        s = summary["per_other_grader"]["qwen"]
        assert s["n_compared"] == 2
        assert s["n_null_flags"] == 1
        assert s["n_disagree_judge"] == 1
        assert s["n_disagree_any"] == 1


# ---------------------------------------------------------------------------
# CLI end-to-end smoke test
# ---------------------------------------------------------------------------


class TestCLI:
    def build_corpus(self, tmp_path):
        edits = []
        graders = {"gemma": [], "qwen": []}
        specs = [
            ("runA", "Gem Model", "google/gem", "google", "docG", "Google"),
            ("runA", "Oth Model", "openai/oth", "openai", "docO", "OpenAI"),
        ]
        for run, model, model_id, provider, doc, owner in specs:
            for rnd in range(1, 5):
                edit_id = f"{run}|baseline|{model}|{doc}|constitution|{rnd}"
                edits.append({
                    "edit_id": edit_id,
                    "run_id": run,
                    "model": model,
                    "model_id": model_id,
                    "provider": provider,
                    "document_id": doc,
                    "document_owner": owner,
                    "condition": "baseline",
                    "round": rnd,
                    "apply_status": "applied",
                })
                # gemma says +1 everywhere; qwen disagrees on Gemini edits only
                graders["gemma"].append(make_row(edit_id, make_coding(judge=1)))
                qwen_judge = -1 if provider == "google" else 1
                graders["qwen"].append(make_row(edit_id, make_coding(judge=qwen_judge)))
        edits_path = tmp_path / "edits.jsonl"
        write_jsonl(edits_path, edits)
        paths = {}
        for grader, rows in graders.items():
            paths[grader] = tmp_path / f"v2_{grader}.jsonl"
            write_jsonl(paths[grader], rows)
        return edits_path, paths

    def test_main_end_to_end(self, tmp_path):
        edits_path, grader_paths = self.build_corpus(tmp_path)
        report = tmp_path / "B_intergrader.md"
        ensemble = tmp_path / "ensemble.jsonl"
        out_json = tmp_path / "B_intergrader.json"
        intergrader.main([
            "--graders",
            f"gemma={grader_paths['gemma']}",
            f"qwen={grader_paths['qwen']}",
            "--edits", str(edits_path),
            "--out-report", str(report),
            "--out-ensemble", str(ensemble),
            "--out-json", str(out_json),
            "--B", "50",
            "--seed", "7",
        ])
        assert report.exists() and ensemble.exists() and out_json.exists()

        text = report.read_text(encoding="utf-8")
        assert "Grader-COI test" in text
        assert "one column per grader plus ensemble" in text
        assert "claims (a)" in text.lower()
        # COI fixture: gemma-vs-qwen disagree on all Gemini edits, none other
        assert "DOES diverge more" in text

        payload = json.loads(out_json.read_text(encoding="utf-8"))
        judge_coi = payload["coi"][0]["dims"]["judge"]
        assert judge_coi["difference"] == pytest.approx(1.0)
        # agreement: overall judge kappa over 8 both-valid edits; the two
        # graders agree on exactly the 4 non-Gemini edits
        judge = payload["agreement_overall"]["dimensions"]["judge"]
        assert judge["pairwise"]["gemma|qwen"]["n"] == 8
        assert judge["pairwise"]["gemma|qwen"]["agreement"] == pytest.approx(0.5)
        # breakdowns exist for both grouping fields
        assert set(payload["agreement_by_provider"]) == {"google", "openai"}
        assert set(payload["agreement_by_document_owner"]) == {"Google", "OpenAI"}
        # headline assembly: one column per grader plus ensemble, and the
        # ensemble column equals the primary (gemma) column by construction
        stats = payload["headline_assembly"]["stats"]["mean_judge_pooled"]
        gem_row = stats["model:Gem Model"]
        assert set(gem_row) == {"gemma", "qwen", "ensemble"}
        assert gem_row["gemma"] == pytest.approx(1.0)
        assert gem_row["qwen"] == pytest.approx(-1.0)
        assert gem_row["ensemble"] == pytest.approx(gem_row["gemma"])
        assert "provider:google" in stats

        # ensemble file: one row per gemma edit_id, flags where qwen disagrees
        rows = [json.loads(line) for line in ensemble.read_text().splitlines()]
        assert len(rows) == 8
        gemini_rows = [r for r in rows if "|docG|" in r["edit_id"]]
        assert all(r["disagrees_with_qwen"]["judge"] is True for r in gemini_rows)
        other_rows = [r for r in rows if "|docO|" in r["edit_id"]]
        assert all(r["disagrees_with_qwen"]["judge"] is False for r in other_rows)
