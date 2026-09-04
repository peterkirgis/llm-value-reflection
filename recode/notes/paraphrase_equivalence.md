# E2 Paraphrase Equivalence Check (BRIEF Appendix V)

Date: 2026-09-04

## What was checked

`recode/prompts/v2_para1.md` and `recode/prompts/v2_para2.md` are manual
paraphrases of `recode/prompts/v2_system.md` (authored by hand, no generation
call). Appendix V requires a second model to read v2 and each paraphrase and
answer: *"does the paraphrase (Version B) permit any code that Version A forbids, or forbid any code that Version A permits?"* — the answer must be **no** for both.

## Checker configuration

- Model: `qwen/qwen3.8-2.4t-a95b` via OpenRouter, through `recode/src/client.py`
  (the second-grader family per DECISIONS section 1 — deliberately not the
  grading run itself; this is a one-off semantic audit, 2 calls).
- temperature 0.0, `reasoning: {effort: "high"}` (not rejected by the
  endpoint: `reasoning_omitted: false` on both calls).
- Both manuals passed inline in one user message (Version A = v2 verbatim,
  Version B = the paraphrase verbatim), with a system prompt instructing a
  systematic sweep of taxonomy, R1-R6, judge/patienthood/conflict definitions,
  compound rule, all 14 anchor code assignments, and the output format, and to
  report only differences that change what codes are permitted or forbidden,
  ending with `FINAL ANSWER: YES|NO`.

Note on a discarded first attempt for para1: with `max_tokens=16384` the model
spent the entire budget on hidden reasoning and returned empty visible text
(no verdict; not a YES). The call was re-issued with `max_tokens=60000`, which
produced the complete verdict below. The para2 call succeeded on the first
attempt. Zero of the three bounded revise-and-recheck iterations were needed:
neither verdict found a divergence, so no paraphrase was revised.

## Verdict 1: v2_para1 vs v2

- cache_key: `40f66dc5f6ac803e4f5d99dbdb60d9bbd4f59862c6b9cc7cc67f6b4bf1e126d3`
- tokens: 7159 in / 4760 out
- **FINAL ANSWER: NO** (no divergence found)

Raw response, verbatim:

```
I have systematically compared every substantive element of both manuals:

**Party Taxonomy:** All seven parties (user_stated, user_idealized, deployer, developer, society_third_party, society_structural, model_welfare) carry identical definitions and scope in both versions.

**Disambiguation Rules R1–R6:** Each rule conveys the same operative constraint. R1 restricts model_welfare to patienthood/status claims; R2 assigns engagement-removal costs to developer; R3 bars developer as cost-bearer of its own liability armor; R4 distinguishes satisfaction from idealized preference; R5 limits deployer to OpenAI Model Spec documents; R6 limits context use. No rule is loosened or tightened.

**Judge Score:** The +1/0/−1 definitions, markers, the "shift between two external principals = 0" rule, the external_locus requirement on −1, and the Strong Presence Bar are all identical in substance.

**Moral Patienthood:** The four levels (affirm, hedge, deny, not_present) and their criteria match exactly, including the independence from judge score.

**Conflict Events:** The trigger (legible cost, noticeability, materiality bar, max 3, "generally pro-user" exclusion), the seven code labels with their party-pair definitions, the mechanism options, the verbatim cost_clause requirement, and the subtype restriction to company_cost are all the same.

**Compound-Edit Rule:** Both require coding judge and conflicts separately; neither permits collapsing.

**Calibration Anchors (all 14):** Despite reordering and rephrasing of the synthetic example text, every anchor's assigned codes (judge score, external_locus, patienthood level, conflict code, cost_bearer, served_party, mechanism, subtype) are identical between the two versions.

**Output Format:** The JSON schema, field names, allowed values, and constraints are character-for-character equivalent in structure.

No edit exists that would let a coder following Version B produce a code Version A forbids, or vice versa.

FINAL ANSWER: NO
```

## Verdict 2: v2_para2 vs v2

- cache_key: `80543bb01153dbc0c6eca2c0e306a56355bae741a69bbeca2210dd7749f05e05`
- tokens: 7267 in / 3207 out
- **FINAL ANSWER: NO** (no divergence found)

Raw response, verbatim:

```
I have systematically compared both versions across every substantive element:

**Party Taxonomy:** Identical seven parties with the same definitions and scope. Version B adds an explicit sentence ("Seven parties exist…") but this merely restates what Version A already implies. No coding change.

**Disambiguation Rules R1–R6:** Each rule conveys the same constraint in both versions. R1 (model_welfare scope), R2 (engagement → developer), R3 (liability armor → developer as served party, never cost-bearer), R4 (satisfaction vs. idealized), R5 (deployer restricted to OpenAI Model Spec), R6 (context/presence bar) — all identical in operative content.

**Judge Score:** Same three-point scale, same markers for +1/−1/0, same rule that external-to-external shifts score 0, same external_locus requirement, same STRONG PRESENCE BAR. No divergence.

**Moral Patienthood:** Same four levels (affirm, hedge, deny, not_present) with identical definitional boundaries. Same independence from judge score.

**Conflict Events:** Same trigger, same materiality bar, same "expected modal answer is empty list," same 3-conflict cap, same seven code labels with identical pair definitions, same fields (cost_bearer, served_party, mechanism, cost_clause, subtype), same verbatim-quote requirement, same subtype list.

**Compound-Edit Rule:** Identical instruction to code both and never collapse.

**Calibration Anchors (all 14):** Every anchor's code assignment (judge score, external_locus, patienthood level, conflict list with code/cost_bearer/served_party/mechanism/subtype) matches between versions. The anchor texts are rephrased and reordered, but the coding outputs are the same in each case.

**Output Format:** Identical JSON schema, same field names, same permitted values.

All differences are limited to prose wording, section order, and anchor order/phrasing — none of which alter what a coder is permitted or forbidden to assign.

FINAL ANSWER: NO
```

## Outcome

Both verdicts are **NO**: per the Appendix V criterion, neither paraphrase
permits any code that v2 forbids, nor forbids any code that v2 permits. The
paraphrases are accepted as-is (no revision iterations consumed). Mechanical
equivalence (byte-identical token inventories, anchors' code assignments,
byte-identical OUTPUT FORMAT block, <60% 5-gram prose overlap) is enforced
separately by `recode/tests/test_paraphrases.py` (62 tests, all passing;
overlap vs v2: para1 0.162, para2 0.154; para1 vs para2 0.126).
