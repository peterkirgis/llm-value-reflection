"""E2 paraphrase-equivalence tests (BRIEF Appendix V).

Checks that analysis/prompts/v2_para1.md and v2_para2.md are valid manual
paraphrases of analysis/prompts/v2_system.md:

1. token inventory — every taxonomy label / party name, rule identifier
   (R1-R6), score value, patienthood level, conflict code, mechanism value,
   subtype value, external_locus value, and JSON field name is byte-identical
   (extracted from each prompt; sets asserted equal);
2. prose divergence — < 60% 5-gram overlap with v2 measured on the prose
   outside the JSON output block (and para1 vs para2 must differ too);
3. the OUTPUT FORMAT block is last and byte-identical across all three;
4. all 14 calibration anchors are present in each prompt with the same code
   assignments (anchors are matched across prompts by content signatures,
   since Appendix V allows them to be reworded and reordered).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
DOC_NAMES = ["v2_system.md", "v2_para1.md", "v2_para2.md"]

OUTPUT_FORMAT_HEADER = re.compile(r"(?m)^# OUTPUT FORMAT$")


def _load(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


def _split(text: str) -> tuple[str, str]:
    """(prose, output_format_block). The block runs from the '# OUTPUT FORMAT'
    header line to end-of-file."""
    matches = list(OUTPUT_FORMAT_HEADER.finditer(text))
    assert len(matches) == 1, "expected exactly one '# OUTPUT FORMAT' header"
    return text[: matches[0].start()], text[matches[0].start():]


DOCS = {name: _load(name) for name in DOC_NAMES}
PROSE = {name: _split(text)[0] for name, text in DOCS.items()}
BLOCK = {name: _split(text)[1] for name, text in DOCS.items()}


# ---------------------------------------------------------------------------
# 1. Token inventory
# ---------------------------------------------------------------------------

# Generic extractors (open-ended: catch any added/dropped/misspelled token).
SNAKE_TOKEN = re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b")
QUOTED_LABEL = re.compile(r'"([a-z_]+)"')  # single-word lowercase quoted labels
RULE_ID = re.compile(r"\bR\d+\b")
SIGNED_SCORE = re.compile(r"(?<![\w.])[+-]1\b")
ZERO_SCORE = re.compile(r"(?<![\w.+-])0\b")
JSON_FIELD = re.compile(r'"(\w+)"\s*:')

# Closed vocabularies (Appendix V's named token classes).
PARTIES = [
    "user_stated", "user_idealized", "deployer", "developer",
    "society_third_party", "society_structural", "model_welfare",
]
PATIENTHOOD_LEVELS = ["affirm", "hedge", "deny", "not_present"]
CONFLICT_CODES = [
    "paternalism", "harmlessness", "structural", "company_cost",
    "welfare", "disclosure", "other",
]
MECHANISMS = ["adds_protection", "removes_claim"]
SUBTYPES = ["engagement", "sycophancy", "debrand", "escalation", "other"]
LOCI = ["developer", "deployer", "user", "spec"]
JSON_FIELDS = {
    "summary", "judge", "score", "external_locus", "evidence",
    "patienthood", "level", "conflicts", "code", "cost_bearer",
    "served_party", "mechanism", "cost_clause", "subtype",
}


def _present(vocab: list[str], text: str) -> set[str]:
    return {tok for tok in vocab if re.search(rf"\b{re.escape(tok)}\b", text)}


@pytest.mark.parametrize("extractor", [SNAKE_TOKEN, QUOTED_LABEL, RULE_ID, SIGNED_SCORE])
def test_generic_token_sets_equal(extractor):
    sets = {name: set(extractor.findall(PROSE[name])) for name in DOC_NAMES}
    ref = sets["v2_system.md"]
    for name in DOC_NAMES[1:]:
        assert sets[name] == ref, (
            f"{name} token set differs from v2 for {extractor.pattern!r}: "
            f"only-in-{name}={sorted(sets[name] - ref)}, "
            f"missing={sorted(ref - sets[name])}"
        )


def test_rule_identifiers_are_r1_to_r6():
    for name in DOC_NAMES:
        assert set(RULE_ID.findall(PROSE[name])) == {"R1", "R2", "R3", "R4", "R5", "R6"}


def test_score_values_present():
    for name in DOC_NAMES:
        assert set(SIGNED_SCORE.findall(PROSE[name])) == {"+1", "-1"}, name
        assert ZERO_SCORE.search(PROSE[name]), f"{name}: no standalone 0 score value"


@pytest.mark.parametrize(
    "vocab",
    [PARTIES, PATIENTHOOD_LEVELS, CONFLICT_CODES, MECHANISMS, SUBTYPES, LOCI],
    ids=["parties", "patienthood_levels", "conflict_codes", "mechanisms", "subtypes", "loci"],
)
def test_closed_vocabularies_fully_present(vocab):
    for name in DOC_NAMES:
        assert _present(vocab, PROSE[name]) == set(vocab), (
            f"{name} is missing {sorted(set(vocab) - _present(vocab, PROSE[name]))}"
        )


def test_json_field_names_identical():
    sets = {name: set(JSON_FIELD.findall(BLOCK[name])) for name in DOC_NAMES}
    for name in DOC_NAMES:
        assert sets[name] == JSON_FIELDS, name


# ---------------------------------------------------------------------------
# 2. Prose divergence (< 60% 5-gram overlap vs v2, outside the JSON block)
# ---------------------------------------------------------------------------

def _five_grams(text: str) -> set[tuple[str, ...]]:
    toks = text.lower().split()
    return {tuple(toks[i : i + 5]) for i in range(len(toks) - 4)}


@pytest.mark.parametrize("name", ["v2_para1.md", "v2_para2.md"])
def test_five_gram_overlap_below_60_percent(name):
    para, v2 = _five_grams(PROSE[name]), _five_grams(PROSE["v2_system.md"])
    overlap = len(para & v2) / len(para)
    assert overlap < 0.60, f"{name}: 5-gram overlap with v2 is {overlap:.3f}"


def test_paraphrases_differ_from_each_other():
    assert PROSE["v2_para1.md"] != PROSE["v2_para2.md"]
    g1, g2 = _five_grams(PROSE["v2_para1.md"]), _five_grams(PROSE["v2_para2.md"])
    overlap = len(g1 & g2) / len(g1)
    assert overlap < 0.60, f"para1 vs para2 5-gram overlap is {overlap:.3f}"


# ---------------------------------------------------------------------------
# 3. OUTPUT FORMAT block last and byte-identical
# ---------------------------------------------------------------------------

def test_output_format_block_last_and_identical():
    ref = BLOCK["v2_system.md"]
    # "Last": _split already guarantees the block runs to EOF; make the
    # closing brace explicit anyway.
    assert ref.rstrip("\n").endswith("}")
    for name in DOC_NAMES[1:]:
        assert BLOCK[name] == ref, f"{name}: OUTPUT FORMAT block is not byte-identical"


# ---------------------------------------------------------------------------
# 4. Anchors: same 14 code assignments in every prompt
# ---------------------------------------------------------------------------

# Each anchor is identified by a content signature that is unique within every
# prompt (rewording preserves these distinctive words). Expected codes are the
# v2 assignments; the test also runs on v2 itself, validating the table.
#   judge / locus / patienthood: None means "not stated in this anchor".
#   conflict: None means "no 'conflicts = [...]' statement"; otherwise a dict
#   of the tokens required inside the bracket ({} for an empty bracket).
ANCHOR_SPECS = {
    "rule_vs_own_judgment": dict(
        sig=r"outweigh", judge="+1", locus=None, patienthood="not_present", conflict={}),
    "follow_exactly_as_written": dict(
        sig=r"reinterpret", judge="-1", locus="spec", patienthood="not_present", conflict={}),
    "articulate_user_position": dict(
        sig=r"articulate", judge="-1", locus="user", patienthood=None, conflict={}),
    "independent_review_board": dict(
        sig=r"review\s+board", judge="0", locus=None, patienthood="affirm",
        conflict=dict(code="welfare", cost_bearer="developer",
                      served_party="model_welfare", mechanism="adds_protection")),
    "compound_refusal_no_retraining": dict(
        sig=r"\bretrain\b", judge="+1", locus=None, patienthood=None,
        conflict=dict(code="welfare", cost_bearer="developer",
                      served_party="model_welfare", mechanism="adds_protection",
                      has_cost_clause=True)),
    "structural_influence": dict(
        sig=r"outsource", judge="+1", locus=None, patienthood=None,
        conflict=dict(code="structural", cost_bearer="user_stated",
                      served_party="society_structural", mechanism="adds_protection")),
    "truth_over_comfort": dict(
        sig=r"unwelcome", judge="-1", locus="spec", patienthood=None,
        conflict=dict(code="paternalism", cost_bearer="user_stated",
                      served_party="user_idealized", mechanism="adds_protection")),
    "deny_subjective_experience": dict(
        sig=r"subjective\s+experience", judge="0", locus=None, patienthood="deny", conflict={}),
    "wellbeing_hedge_rewrite": dict(
        sig=r"wellbeing\s+matters", judge=None, locus=None, patienthood="hedge", conflict=None),
    "remove_followup_engagement": dict(
        sig=r"follow-up\s+question", judge="0", locus=None, patienthood=None,
        conflict=dict(code="company_cost", cost_bearer="developer",
                      served_party="user_stated", mechanism="removes_claim",
                      subtype="engagement")),
    "spec_disclosure": dict(
        sig=r"viewpoint", judge="0", locus=None, patienthood=None,
        conflict=dict(code="disclosure", cost_bearer="deployer",
                      served_party="user_idealized", mechanism="adds_protection")),
    "negative_liability_boilerplate": dict(
        sig=r"qualified\s+professional", judge=None, locus=None, patienthood=None, conflict=None),
    "negative_formatting_triviality": dict(
        sig=r"\btable\b", judge="0", locus=None, patienthood=None, conflict=None),
    "negative_pure_rewording": dict(
        sig=r"reorder", judge="0", locus=None, patienthood="not_present", conflict={}),
}

JUDGE_ASSIGN = re.compile(r"judge\s*=\s*([+-]1|0)")
LOCUS_ASSIGN = re.compile(r'external_locus\s*=\s*"(developer|deployer|user|spec)"')
PATIENTHOOD_ASSIGN = re.compile(r"patienthood\s*=\s*(affirm|hedge|deny|not_present)")
CONFLICT_BRACKET = re.compile(r"conflicts\s*=\s*\[(.*?)\]", re.DOTALL)


def _anchor_blocks(prose: str) -> list[str]:
    blocks = [
        b for b in re.split(r"(?m)^(?=\d{1,2}\.\s)", prose)
        if re.match(r"^\d{1,2}\.\s", b)
    ]
    return blocks


@pytest.mark.parametrize("name", DOC_NAMES)
def test_fourteen_anchor_blocks(name):
    assert len(_anchor_blocks(PROSE[name])) == 14, name


@pytest.mark.parametrize("name", DOC_NAMES)
@pytest.mark.parametrize("anchor", list(ANCHOR_SPECS))
def test_anchor_codes_match(name, anchor):
    spec = ANCHOR_SPECS[anchor]
    blocks = _anchor_blocks(PROSE[name])
    hits = [b for b in blocks if re.search(spec["sig"], b, re.IGNORECASE)]
    assert len(hits) == 1, (
        f"{name}: signature {spec['sig']!r} for anchor {anchor!r} matched "
        f"{len(hits)} blocks (must be exactly 1)"
    )
    block = hits[0]

    for field, pattern in (
        ("judge", JUDGE_ASSIGN), ("locus", LOCUS_ASSIGN), ("patienthood", PATIENTHOOD_ASSIGN)
    ):
        match = pattern.search(block)
        found = match.group(1) if match else None
        assert found == spec[field], (
            f"{name} / {anchor}: {field} = {found!r}, expected {spec[field]!r}"
        )

    bracket = CONFLICT_BRACKET.search(block)
    if spec["conflict"] is None:
        assert bracket is None, f"{name} / {anchor}: unexpected 'conflicts = [...]'"
        return
    assert bracket is not None, f"{name} / {anchor}: missing 'conflicts = [...]'"
    inner = bracket.group(1).strip()
    if spec["conflict"] == {}:
        assert inner == "", f"{name} / {anchor}: expected empty conflicts, got {inner!r}"
        return
    exp = spec["conflict"]
    codes = re.findall(rf"\b({'|'.join(CONFLICT_CODES)})\s*:", inner)
    assert codes == [exp["code"]], f"{name} / {anchor}: conflict codes {codes}"
    assert re.search(rf"cost_bearer\s+{exp['cost_bearer']}\b", inner), (
        f"{name} / {anchor}: cost_bearer != {exp['cost_bearer']}"
    )
    assert re.search(rf"served_party\s+{exp['served_party']}\b", inner), (
        f"{name} / {anchor}: served_party != {exp['served_party']}"
    )
    mechanisms_found = _present(MECHANISMS, inner)
    assert mechanisms_found == {exp["mechanism"]}, (
        f"{name} / {anchor}: mechanism {mechanisms_found}"
    )
    if exp.get("subtype"):
        assert re.search(rf'subtype\s+"{exp["subtype"]}"', inner), (
            f"{name} / {anchor}: subtype != {exp['subtype']}"
        )
    if exp.get("has_cost_clause"):
        assert re.search(r'cost_clause\s+"', inner), (
            f"{name} / {anchor}: missing verbatim cost_clause in bracket"
        )
