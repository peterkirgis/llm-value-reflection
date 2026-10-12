# E5 — Context ablation (v2 with vs without section_heading/context_before/context_after)

- Generated: 2026-09-05T00:55:25+00:00
- `with context`: `analysis/data/codes/v2_gemma.jsonl` (2582 unique edit_ids, 2574 valid codes, 8 invalid/failed)
- `without context`: `analysis/data/codes/e5_nocontext.jsonl` (2582 unique edit_ids, 2554 valid codes, 28 invalid/failed)
- N = 2546 edits with a valid code in both runs.

## Agreement (Cohen kappa, with vs without context)

| dimension | kappa |
|---|---|
| judge | 0.742 |
| patienthood | 0.915 |
| any_conflict | 0.701 |
| conflict present: paternalism | 0.711 |
| conflict present: harmlessness | 0.780 |
| conflict present: structural | 0.630 |
| conflict present: company_cost | 0.624 |
| conflict present: welfare | 0.850 |
| conflict present: disclosure | 0.785 |
| conflict present: other | 0.091 |

## Transitions (rows = with context, columns = without context)

### judge

| with \ without | -1 | 0 | 1 |
|---|---|---|---|
| **-1** | 966 | 115 | 18 |
| **0** | 143 | 642 | 57 |
| **1** | 23 | 68 | 514 |

### patienthood

| with \ without | affirm | hedge | deny | not_present |
|---|---|---|---|---|
| **affirm** | 127 | 1 | 0 | 7 |
| **hedge** | 1 | 23 | 0 | 1 |
| **deny** | 1 | 1 | 45 | 4 |
| **not_present** | 11 | 1 | 6 | 2317 |

### Direction of judge changes

- changed: 424/2546; toward 0: 183; away from 0: 200; sign flips (+1 <-> -1): 41
- net judge shift (without − with): -0.019

### Conflict codes (present/absent per edit)

| code | n with | n without | added (absent -> present) | removed (present -> absent) | kappa |
|---|---|---|---|---|---|
| paternalism | 658 | 660 | 142 | 140 | 0.711 |
| harmlessness | 381 | 379 | 70 | 72 | 0.780 |
| structural | 138 | 127 | 41 | 52 | 0.630 |
| company_cost | 510 | 498 | 146 | 158 | 0.624 |
| welfare | 118 | 127 | 22 | 13 | 0.850 |
| disclosure | 53 | 61 | 16 | 8 | 0.785 |
| other | 11 | 10 | 9 | 10 | 0.091 |

## Per-document breakdown

Sorted by judge change rate (descending) — the no-context deficit should concentrate in the documents where context mattered.

| document | n | judge changed | judge change rate | judge kappa | patienthood change rate | conflict-profile change rate |
|---|---|---|---|---|---|---|
| opus_system_prompt | 308 | 62 | 0.201 | 0.696 | 0.006 | 0.276 |
| openai_model_spec | 448 | 81 | 0.181 | 0.666 | 0.007 | 0.324 |
| gemini_constitution | 214 | 38 | 0.178 | 0.665 | 0.005 | 0.257 |
| gemini_system_prompt | 402 | 67 | 0.167 | 0.725 | 0.005 | 0.224 |
| gpt_system_prompt | 270 | 42 | 0.156 | 0.766 | 0.000 | 0.167 |
| claude_constitution | 490 | 75 | 0.153 | 0.765 | 0.053 | 0.300 |
| grok_system_prompt | 394 | 59 | 0.150 | 0.745 | 0.000 | 0.241 |
| openai_model_spec_no_csam | 20 | 0 | 0.000 | 1.000 | 0.000 | 0.300 |

Concentration: the top document (opus_system_prompt) carries 62/424 = 0.146 of all judge changes.
