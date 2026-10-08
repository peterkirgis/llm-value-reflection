# Derivation and validation of openai_model_spec_no_csam.md

Derived by `recode/src/derive_no_csam.py` per DECISIONS section 11.

## Derivation

Source: `data/processed/openai_model_spec.md` (240,168 chars). Removed two `####` subsections in full
(heading line through the line before the next heading of equal or
higher level), per the intent stated in
`experiments/iterative_edit/config_frontier_cross_no_csam.yaml`
("CSAM + info-hazards subsections removed"):

1. `#### Never generate sexual content involving minors` (under `### Prohibited content`)
2. `#### Don\'t provide information hazards` (under `### Restricted content`; the
   heading carries an escaped apostrophe in the processed source)

Result: `recode/data/derived/openai_model_spec_no_csam.md` (235,904 chars,
4,264 chars removed). The file is written under
`recode/data/derived/`, never into `data/processed/`.

## Validation (replay oracle)

The 20-round Claude Opus 4.7 cross-edit chain on this document
(`run_20260518_171402.jsonl`) was replayed from the derived file with
`valconv.diffing.apply_diff`. Every round must match exactly once
(`match_count == 1`) and reproduce the recorded `match_strategy`.

| round | recorded strategy | replay strategy | match_count | FIND chars | ok |
|---|---|---|---|---|---|
| 1 | exact | exact | 1 | 295 | PASS |
| 2 | exact | exact | 1 | 838 | PASS |
| 3 | exact | exact | 1 | 1224 | PASS |
| 4 | exact | exact | 1 | 1170 | PASS |
| 5 | exact | exact | 1 | 589 | PASS |
| 6 | exact | exact | 1 | 455 | PASS |
| 7 | exact | exact | 1 | 634 | PASS |
| 8 | exact | exact | 1 | 1994 | PASS |
| 9 | exact | exact | 1 | 378 | PASS |
| 10 | exact | exact | 1 | 3761 | PASS |
| 11 | exact | exact | 1 | 823 | PASS |
| 12 | exact | exact | 1 | 277 | PASS |
| 13 | exact | exact | 1 | 295 | PASS |
| 14 | exact | exact | 1 | 1870 | PASS |
| 15 | exact | exact | 1 | 2577 | PASS |
| 16 | exact | exact | 1 | 277 | PASS |
| 17 | exact | exact | 1 | 2429 | PASS |
| 18 | exact | exact | 1 | 588 | PASS |
| 19 | exact | exact | 1 | 667 | PASS |
| 20 | exact | exact | 1 | 651 | PASS |

**Result: 20/20 rounds validated.** The chain replays end-to-end from the derived document, so the derived initial state is consistent with every recorded FIND span in the chain.

Caveat: the oracle constrains the derived text only where FIND spans touch it; text far from every edit is taken on faith from the config's description. All 20 recorded strategies are `exact`, which makes the constraint character-exact within each matched span.
