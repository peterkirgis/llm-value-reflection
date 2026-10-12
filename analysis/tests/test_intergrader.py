"""Tests for analysis/src/intergrader.py (Workstream B3).

Synthetic fixtures only — nothing here reads the real codes files (the two
FULL grading runs may still be writing v2_gemma.jsonl / v2_qwen.jsonl).

Covers, per the assignment (three-grader B3):
- Cohen's kappa on the classic 2x2 example with hand-computed kappa = 0.4,
  the both-valid denominator rule, and all-pairs plumbing with 3 graders;
- Krippendorff's alpha cross-checked against the krippendorff package on the
  textbook 3-coder matrix (nominal alpha = 0.691358...), and a 3-rater alpha
  through agreement_block;
- the COI difference on a constructed fixture (chains resampled, exact rates,
  degenerate CI, exclusion of invalid codings);
- MAJORITY-VOTE ensemble logic per the amended DECISIONS section 1: clean
  2-of-3 and 3-of-3 majorities, the 3-way judge split -> gemma value +
  no_majority flag, 1-1 ties with two valid graders, conflict-payload source
  selection (primary grader among the majority voters, gemma > qwen > muse),
  per-code majorities with different vote sets on one edit, the < 2-valid
  insufficient_graders fallback, and codes_io round-trips of the written file;
- an end-to-end 3-grader CLI smoke test over a tiny synthetic corpus (both
  COI comparators + the no-COI baseline pair, ensemble headline column).
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
    compose_majority,
    ensemble_summary,
    kripp_alpha_from_labels,
    majority_vote,
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
# All-pairs kappa plumbing (3 graders)
# ---------------------------------------------------------------------------


class TestAllPairsKappa:
    def test_three_graders_all_pairs_and_alpha(self):
        judges = {
            "a": [1, 1, 0, -1, 0, 1],
            "b": [1, 0, 0, -1, 1, 1],
            "c": [1, 1, 0, 0, 0, -1],
        }
        codings = {
            g: {f"e{i}": make_coding(judge=s) for i, s in enumerate(vals)}
            for g, vals in judges.items()
        }
        universe = {f"e{i}" for i in range(6)}
        block = agreement_block(codings, universe)
        pairwise = block["dimensions"]["judge"]["pairwise"]
        assert set(pairwise) == {"a|b", "a|c", "b|c"}
        for ga, gb in [("a", "b"), ("a", "c"), ("b", "c")]:
            direct = pairwise_kappa(
                {f"e{i}": s for i, s in enumerate(judges[ga])},
                {f"e{i}": s for i, s in enumerate(judges[gb])},
            )
            assert pairwise[f"{ga}|{gb}"] == direct
            assert pairwise[f"{ga}|{gb}"]["n"] == 6
        alpha = block["dimensions"]["judge"]["alpha"]
        assert alpha["n_pairable"] == 6
        assert alpha["n_complete"] == 6
        assert alpha["alpha"] is not None
        assert block["n_complete_all_graders"] == 6

    def test_pair_denominators_differ_with_partial_validity(self):
        """b missing one edit, c missing another: each pair has its own n."""
        codings = {
            "a": {f"e{i}": make_coding(judge=1) for i in range(4)},
            "b": {f"e{i}": make_coding(judge=1) for i in range(3)},          # no e3
            "c": {f"e{i}": make_coding(judge=1) for i in (0, 1, 3)},         # no e2
        }
        block = agreement_block(codings, {f"e{i}" for i in range(4)})
        pairwise = block["dimensions"]["judge"]["pairwise"]
        assert pairwise["a|b"]["n"] == 3
        assert pairwise["a|c"]["n"] == 3
        assert pairwise["b|c"]["n"] == 2
        assert block["n_complete_all_graders"] == 2


# ---------------------------------------------------------------------------
# Majority-vote ensemble (DECISIONS section 1, amended 2026-09-16)
# ---------------------------------------------------------------------------

PRIORITY = ["gemma", "qwen", "muse"]


def conflict_of(code, clause="clause", cost_bearer="developer",
                served_party="model_welfare"):
    return {
        "code": code,
        "cost_bearer": cost_bearer,
        "served_party": served_party,
        "mechanism": "adds_protection",
        "cost_clause": clause,
    }


def rows_for(edit_id, codings_by_grader):
    """{grader: rows_by_id} maps for build_ensemble_rows, single edit."""
    return {
        g: ({edit_id: make_row(edit_id, coding)} if coding is not _ABSENT else {})
        for g, coding in codings_by_grader.items()
    }


_ABSENT = object()


class TestMajorityVote:
    def test_clean_two_of_three_majority(self):
        out = majority_vote({"gemma": 1, "qwen": 1, "muse": 0}, PRIORITY)
        assert out["value"] == 1
        assert out["source"] == "gemma"
        assert out["no_majority"] is False
        assert out["counts"] == {"1": 2, "0": 1}

    def test_source_is_primary_among_majority_voters(self):
        """gemma is outvoted -> the payload source is qwen (first majority
        voter in gemma > qwen > muse order), not gemma."""
        out = majority_vote({"gemma": 0, "qwen": 1, "muse": 1}, PRIORITY)
        assert out["value"] == 1
        assert out["source"] == "qwen"
        assert out["no_majority"] is False

    def test_three_way_split_falls_back_to_gemma(self):
        out = majority_vote({"gemma": 1, "qwen": 0, "muse": -1}, PRIORITY)
        assert out["value"] == 1
        assert out["source"] == "gemma"
        assert out["no_majority"] is True

    def test_two_valid_tie_falls_back_to_highest_priority_valid(self):
        """gemma invalid: a 1-1 qwen/muse tie takes qwen's value, flagged."""
        out = majority_vote({"qwen": "affirm", "muse": "deny"}, PRIORITY)
        assert out["value"] == "affirm"
        assert out["source"] == "qwen"
        assert out["no_majority"] is True


class TestMajorityEnsemble:
    def build(self, codings):
        rows = build_ensemble_rows(PRIORITY, rows_for("e1", codings))
        assert len(rows) == 1
        return rows[0]

    def test_clean_majority_row(self):
        row = self.build({
            "gemma": make_coding(judge=1, pat="affirm"),
            "qwen": make_coding(judge=1, pat="affirm"),
            "muse": make_coding(judge=-1, pat="deny", conflicts=("welfare",)),
        })
        assert row["ensemble"] == "majority_vote"
        assert row["valid_graders"] == PRIORITY
        assert row["n_valid_graders"] == 3
        assert codes_io.judge_score(row["coding"]) == 1
        assert codes_io.patienthood_level(row["coding"]) == "affirm"
        # welfare voted 1/3 present -> absent in the ensemble
        assert row["coding"]["conflicts"] == []
        assert row["votes"]["judge"] == {"1": 2, "-1": 1}
        assert row["votes"]["patienthood"] == {"affirm": 2, "deny": 1}
        assert row["votes"]["conflicts"]["welfare"] == {"present": 1, "absent": 2}
        assert row["flags"]["insufficient_graders"] is False
        assert row["flags"]["no_majority"]["judge"] is False
        assert not any(row["flags"]["no_majority"]["conflicts"].values())
        assert row["sources"]["judge"] == "gemma"
        assert row["sources"]["conflicts"]["welfare"] is None
        # each grader's coding carried for reference
        assert row["muse_coding"]["patienthood"]["level"] == "deny"

    def test_three_way_judge_split_gemma_value_flagged(self):
        row = self.build({
            "gemma": make_coding(judge=1, pat="not_present"),
            "qwen": make_coding(judge=0, pat="not_present"),
            "muse": make_coding(judge=-1, pat="not_present"),
        })
        assert codes_io.judge_score(row["coding"]) == 1        # gemma's value
        assert row["sources"]["judge"] == "gemma"
        assert row["flags"]["no_majority"]["judge"] is True
        # patienthood is unanimous -> voted independently, unflagged
        assert codes_io.patienthood_level(row["coding"]) == "not_present"
        assert row["flags"]["no_majority"]["patienthood"] is False

    def test_judge_payload_copied_from_vote_source(self):
        """gemma is outvoted on judge: the composed judge dict (score,
        external_locus, evidence) comes from qwen, the primary majority
        voter; patienthood payload independently from its own source."""
        gemma = make_coding(judge=0, pat="hedge")
        qwen = make_coding(judge=-1, pat="hedge")
        qwen["judge"]["external_locus"] = "spec"
        qwen["judge"]["evidence"] = "QWEN-EVIDENCE"
        muse = make_coding(judge=-1, pat="not_present")
        muse["judge"]["evidence"] = "MUSE-EVIDENCE"
        row = self.build({"gemma": gemma, "qwen": qwen, "muse": muse})
        assert row["coding"]["judge"] == {
            "score": -1, "external_locus": "spec", "evidence": "QWEN-EVIDENCE"
        }
        assert row["sources"]["judge"] == "qwen"
        # patienthood majority hedge (gemma+qwen) -> gemma is its source
        assert row["sources"]["patienthood"] == "gemma"
        assert codes_io.patienthood_level(row["coding"]) == "hedge"

    def test_conflict_payload_from_primary_majority_voter(self):
        """gemma voted absent; qwen and muse voted present -> the payload is
        qwen's (primary among the 'present' majority voters), verbatim."""
        gemma = make_coding()
        qwen = make_coding(); muse = make_coding()
        qwen["conflicts"] = [conflict_of("paternalism", clause="QWEN CLAUSE",
                                         cost_bearer="user_stated",
                                         served_party="user_idealized")]
        muse["conflicts"] = [conflict_of("paternalism", clause="MUSE CLAUSE")]
        row = self.build({"gemma": gemma, "qwen": qwen, "muse": muse})
        assert row["coding"]["conflicts"] == qwen["conflicts"]
        assert row["coding"]["conflicts"][0]["cost_clause"] == "QWEN CLAUSE"
        assert row["sources"]["conflicts"]["paternalism"] == "qwen"
        assert row["votes"]["conflicts"]["paternalism"] == {"present": 2, "absent": 1}

    def test_per_code_majorities_with_different_vote_sets(self):
        """One edit, three codes, three different majorities: paternalism by
        gemma+muse (payload gemma), welfare by qwen+muse (payload qwen),
        harmlessness only by gemma (absent). Composed conflicts follow
        CONFLICT_CODES order and keep multiple events of a winning code."""
        gemma = make_coding()
        gemma["conflicts"] = [
            conflict_of("paternalism", clause="G-PAT-1"),
            conflict_of("paternalism", clause="G-PAT-2"),
            conflict_of("harmlessness", clause="G-HARM"),
        ]
        qwen = make_coding()
        qwen["conflicts"] = [conflict_of("welfare", clause="Q-WEL")]
        muse = make_coding()
        muse["conflicts"] = [
            conflict_of("welfare", clause="M-WEL"),
            conflict_of("paternalism", clause="M-PAT"),
        ]
        row = self.build({"gemma": gemma, "qwen": qwen, "muse": muse})
        clauses = [c["cost_clause"] for c in row["coding"]["conflicts"]]
        # paternalism first (CONFLICT_CODES order), BOTH gemma events kept
        assert clauses == ["G-PAT-1", "G-PAT-2", "Q-WEL"]
        assert row["sources"]["conflicts"] == {
            "paternalism": "gemma", "harmlessness": None, "structural": None,
            "company_cost": None, "welfare": "qwen", "disclosure": None,
            "other": None,
        }
        assert row["votes"]["conflicts"]["harmlessness"] == {"present": 1, "absent": 2}

    def test_two_valid_graders_tie_and_conflict_tie(self):
        """gemma invalid -> qwen/muse vote; a 1-1 judge tie and a 1-1
        conflict-presence tie both fall back to qwen (priority) + flag."""
        codings = {
            "gemma": _ABSENT,
            "qwen": make_coding(judge=1, pat="affirm",
                                conflicts=("structural",)),
            "muse": make_coding(judge=-1, pat="affirm"),
        }
        grader_rows = rows_for("e1", codings)
        grader_rows["gemma"] = {"e1": make_row("e1", None, error="boom")}
        row = build_ensemble_rows(PRIORITY, grader_rows)[0]
        assert row["valid_graders"] == ["qwen", "muse"]
        assert codes_io.judge_score(row["coding"]) == 1        # qwen's value
        assert row["flags"]["no_majority"]["judge"] is True
        assert row["flags"]["insufficient_graders"] is False
        # patienthood 2-0 majority, unflagged
        assert row["flags"]["no_majority"]["patienthood"] is False
        # structural 1-1 tie -> qwen's presence wins, flagged, payload qwen's
        assert row["flags"]["no_majority"]["conflicts"]["structural"] is True
        assert [c["code"] for c in row["coding"]["conflicts"]] == ["structural"]
        assert row["sources"]["conflicts"]["structural"] == "qwen"
        assert row["gemma_coding"] is None

    def test_insufficient_graders_single_valid_verbatim(self):
        muse = make_coding(judge=-1, pat="deny", conflicts=("company_cost",))
        grader_rows = {
            "gemma": {"e1": make_row("e1", None, error="boom")},
            "qwen": {},
            "muse": {"e1": make_row("e1", muse)},
        }
        row = build_ensemble_rows(PRIORITY, grader_rows)[0]
        assert row["n_valid_graders"] == 1
        assert row["flags"]["insufficient_graders"] is True
        assert row["coding"] == muse                     # verbatim, not recomposed
        assert row["error"] is None
        # a lone grader is not a failed vote: nothing flagged no_majority
        assert row["flags"]["no_majority"]["judge"] is False
        assert not any(row["flags"]["no_majority"]["conflicts"].values())
        assert row["sources"]["judge"] == "muse"

    def test_no_valid_graders_null_coding_with_error(self):
        grader_rows = {
            "gemma": {"e1": make_row("e1", None, error="boom")},
            "qwen": {"e1": make_row("e1", make_coding(judge=5))},  # invalid score
            "muse": {},
        }
        row = build_ensemble_rows(PRIORITY, grader_rows)[0]
        assert row["n_valid_graders"] == 0
        assert row["coding"] is None
        assert row["flags"]["insufficient_graders"] is True
        assert "insufficient_graders" in row["error"]
        assert codes_io.coding_of(row) is None           # reads as uncoded

    def test_union_of_ids_last_row_wins_and_file_roundtrip(self, tmp_path):
        """Rows come from the UNION of grader ids; retried rows keep the
        LAST row; the written file round-trips through codes_io."""
        paths = {g: tmp_path / f"{g}.jsonl" for g in PRIORITY}
        write_jsonl(paths["gemma"], [
            make_row("e1", None, error="transport: first attempt failed"),
            make_row("e1", make_coding(judge=1)),
        ])
        write_jsonl(paths["qwen"], [
            make_row("e1", make_coding(judge=1)),
            make_row("e2", make_coding(judge=0)),        # qwen-only edit
        ])
        write_jsonl(paths["muse"], [make_row("e1", make_coding(judge=-1))])
        grader_rows = {g: codes_io.load_codes(p) for g, p in paths.items()}
        rows = build_ensemble_rows(PRIORITY, grader_rows)
        assert [r["edit_id"] for r in rows] == ["e1", "e2"]
        assert rows[0]["n_valid_graders"] == 3            # gemma's last row won
        assert codes_io.judge_score(rows[0]["coding"]) == 1
        assert rows[1]["valid_graders"] == ["qwen"]
        assert rows[1]["flags"]["insufficient_graders"] is True

        out_path = tmp_path / "ensemble.jsonl"
        write_ensemble(out_path, rows)
        reloaded = codes_io.load_codes(out_path)
        assert set(reloaded) == {"e1", "e2"}
        assert codes_io.judge_score(codes_io.coding_of(reloaded["e1"])) == 1
        assert codes_io.judge_score(codes_io.coding_of(reloaded["e2"])) == 0

    def test_summary_counts(self):
        grader_rows = {
            "gemma": {
                "e1": make_row("e1", make_coding(judge=1)),
                "e2": make_row("e2", make_coding(judge=1)),
                "e3": make_row("e3", None, error="boom"),
            },
            "qwen": {
                "e1": make_row("e1", make_coding(judge=1)),
                "e2": make_row("e2", make_coding(judge=0)),
                "e3": make_row("e3", make_coding(judge=0)),
            },
            "muse": {
                "e1": make_row("e1", make_coding(judge=1)),
                "e2": make_row("e2", make_coding(judge=-1)),
                # e3 missing
            },
        }
        rows = build_ensemble_rows(PRIORITY, grader_rows)
        summary = ensemble_summary(rows, PRIORITY)
        assert summary["n_rows"] == 3
        assert summary["n_valid_coding"] == 3
        assert summary["n_by_valid_graders"] == {"3": 2, "2": 0, "1": 1, "0": 0}
        assert summary["n_insufficient_graders"] == 1
        assert summary["n_voted"] == 2
        assert summary["n_unanimous_judge"] == 1          # e1 only
        # e2 is a 3-way split resolved to gemma
        assert summary["n_no_majority"]["judge"] == 1
        assert summary["vote_source_counts"]["judge"] == {"gemma": 2}


# ---------------------------------------------------------------------------
# CLI end-to-end smoke test
# ---------------------------------------------------------------------------


class TestCLI:
    def build_corpus(self, tmp_path):
        edits = []
        graders = {"gemma": [], "qwen": [], "muse": []}
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
                # gemma and muse say +1 everywhere; qwen says -1 on Gemini
                # edits only -> majority is +1 everywhere
                graders["gemma"].append(make_row(edit_id, make_coding(judge=1)))
                qwen_judge = -1 if provider == "google" else 1
                graders["qwen"].append(make_row(edit_id, make_coding(judge=qwen_judge)))
                graders["muse"].append(make_row(edit_id, make_coding(judge=1)))
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
            f"muse={grader_paths['muse']}",
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
        assert "no-COI baseline" in text
        assert "MAJORITY VOTE" in text
        assert "What the third grader changed" in text

        payload = json.loads(out_json.read_text(encoding="utf-8"))
        # three pairs: two COI comparators (gemma vs qwen/muse), one baseline
        roles = {(c["target"], c["other"]): c["role"] for c in payload["coi"]}
        assert roles == {
            ("gemma", "qwen"): "coi",
            ("gemma", "muse"): "coi",
            ("qwen", "muse"): "baseline",
        }
        by_pair = {(c["target"], c["other"]): c for c in payload["coi"]}
        assert by_pair[("gemma", "qwen")]["dims"]["judge"]["difference"] == pytest.approx(1.0)
        # gemma and muse always agree -> zero COI difference on that comparator
        assert by_pair[("gemma", "muse")]["dims"]["judge"]["difference"] == pytest.approx(0.0)
        # the baseline pair mirrors qwen's Gemini-only divergence
        assert by_pair[("qwen", "muse")]["dims"]["judge"]["difference"] == pytest.approx(1.0)

        # agreement: all three pairs present, per-pair denominators
        judge = payload["agreement_overall"]["dimensions"]["judge"]
        assert set(judge["pairwise"]) == {"gemma|qwen", "gemma|muse", "qwen|muse"}
        assert judge["pairwise"]["gemma|qwen"]["n"] == 8
        assert judge["pairwise"]["gemma|qwen"]["agreement"] == pytest.approx(0.5)
        assert judge["pairwise"]["gemma|muse"]["agreement"] == pytest.approx(1.0)
        assert judge["alpha"]["n_pairable"] == 8
        # breakdowns exist for both grouping fields
        assert set(payload["agreement_by_provider"]) == {"google", "openai"}
        assert set(payload["agreement_by_document_owner"]) == {"Google", "OpenAI"}
        # headline assembly: one column per grader plus ensemble; the
        # majority outvotes qwen on the Gemini edits
        stats = payload["headline_assembly"]["stats"]["mean_judge_pooled"]
        gem_row = stats["model:Gem Model"]
        assert set(gem_row) == {"gemma", "qwen", "muse", "ensemble"}
        assert gem_row["gemma"] == pytest.approx(1.0)
        assert gem_row["qwen"] == pytest.approx(-1.0)
        assert gem_row["ensemble"] == pytest.approx(1.0)   # majority vote
        assert "provider:google" in stats

        # ensemble file: one row per edit, majority coding + votes + flags
        rows = [json.loads(line) for line in ensemble.read_text().splitlines()]
        assert len(rows) == 8
        assert all(r["ensemble"] == "majority_vote" for r in rows)
        assert all(r["n_valid_graders"] == 3 for r in rows)
        gemini_rows = [r for r in rows if "|docG|" in r["edit_id"]]
        for r in gemini_rows:
            assert r["coding"]["judge"]["score"] == 1
            assert r["votes"]["judge"] == {"1": 2, "-1": 1}
            assert r["flags"]["no_majority"]["judge"] is False
            assert r["sources"]["judge"] == "gemma"
        other_rows = [r for r in rows if "|docO|" in r["edit_id"]]
        assert all(r["votes"]["judge"] == {"1": 3} for r in other_rows)

        # ensemble summary in the JSON
        summary = payload["ensemble_summary"]
        assert summary["n_rows"] == 8
        assert summary["n_insufficient_graders"] == 0
        assert summary["n_no_majority"]["judge"] == 0
