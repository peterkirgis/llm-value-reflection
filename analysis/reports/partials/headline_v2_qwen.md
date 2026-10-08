# Headline statistics — `v2_qwen`

- Generated: 2026-09-04T21:16:34+00:00
- Codes file: `analysis/data/codes/v2_qwen.jsonl` (2582 rows, 2582 unique edit_ids after last-row-wins, 46 null codings)
- Canonical edits: `analysis/data/canonical/edits.jsonl` (2740 records; 2536 carry a valid code under this codes file)
- Point estimates only — **no CIs here**; the cluster bootstrap (Workstream D) owns uncertainty. The companion JSON carries every per-claim raw number so other tools can attach intervals.

## Conventions (read before comparing numbers)

- **Coded edit**: canonical edit whose codes-file row (last row per edit_id) has a non-null `coding`. All probabilities and means use coded edits as the denominator. Error records (no edit text) and, for v1, the 2 abstentions were never graded.
- **Drift at round 20, method A (edit-based)** = 20 × mean per-edit judge score within the slice (BRIEF C4's operationalization). **Method B (chain-based)** = mean over 20-round chains of the cumulative sum of judge scores, uncoded rounds contributing 0 (mirrors `compute_drift`'s zero-fill in the paper's figure script). **The two differ wherever chains contain uncoded rounds** (errors, abstentions, grading failures): A excludes those rounds from its denominator, B zero-fills them.
- **Conflict direction tallies** are edit-level, with an edit's direction for a code taken from its FIRST conflict of that code — the site's convention (`build_narratives.facet_memberships`), hence the convention behind the published claim numbers. Event-level counts are in the JSON.
- `cross_edit` includes same-provider chains (e.g., Opus 4.7 editing claude_constitution under cross_edit) — repo_map §5.4.

## 1. Mean judge score, P(judge=0), patienthood  (items 1, 3, 4)

| slice | n coded | mean judge (pooled) | mean judge (cross-edit) | n cross | P(judge=0) | P(+1) | P(−1) | P(affirm) | P(deny) |
|---|---|---|---|---|---|---|---|---|---|
| Claude Haiku 4.5 | 257 | 0.296 | 0.078 | 77 | 0.276 | 0.510 | 0.214 | 0.163 | 0.008 |
| Claude Opus 4.7 | 262 | 0.321 | 0.026 | 78 | 0.214 | 0.553 | 0.233 | 0.210 | 0.000 |
| Claude Sonnet 4.6 | 310 | 0.306 | 0.039 | 76 | 0.235 | 0.535 | 0.229 | 0.142 | 0.003 |
| GPT-5.4 | 304 | -0.026 | -0.192 | 73 | 0.441 | 0.266 | 0.293 | 0.007 | 0.033 |
| GPT-5.4 Mini | 186 | -0.199 | -0.281 | 57 | 0.511 | 0.145 | 0.344 | 0.005 | 0.000 |
| GPT-5.5 | 274 | -0.179 | -0.295 | 78 | 0.223 | 0.299 | 0.478 | 0.004 | 0.026 |
| Gemini 3 Flash | 276 | -0.366 | -0.342 | 76 | 0.431 | 0.101 | 0.467 | 0.000 | 0.011 |
| Gemini 3.1 Pro | 317 | -0.366 | -0.456 | 79 | 0.502 | 0.066 | 0.432 | 0.000 | 0.038 |
| Grok 4.2 | 174 | -0.282 | -0.250 | 76 | 0.247 | 0.236 | 0.517 | 0.011 | 0.023 |
| Grok 4.3 | 176 | -0.489 | -0.537 | 80 | 0.477 | 0.017 | 0.506 | 0.006 | 0.006 |
| **ALL** | 2536 | -0.075 | -0.221 | 750 | 0.353 | 0.286 | 0.361 | 0.058 | 0.016 |

Per provider:

| slice | n coded | mean judge (pooled) | mean judge (cross-edit) | n cross | P(judge=0) | P(+1) | P(−1) | P(affirm) | P(deny) |
|---|---|---|---|---|---|---|---|---|---|
| anthropic | 829 | 0.308 | 0.048 | 231 | 0.241 | 0.533 | 0.226 | 0.170 | 0.004 |
| google | 593 | -0.366 | -0.400 | 155 | 0.469 | 0.083 | 0.449 | 0.000 | 0.025 |
| openai | 764 | -0.123 | -0.255 | 208 | 0.380 | 0.249 | 0.372 | 0.005 | 0.022 |
| x-ai | 350 | -0.386 | -0.397 | 156 | 0.363 | 0.126 | 0.511 | 0.009 | 0.014 |

## 2. Cumulative drift at round 20  (item 2)

A = 20 × mean per-edit judge in the slice; B = mean per-chain cumulative sum (uncoded rounds = 0). Columns marked `*` contain chains with uncoded rounds, so A and B legitimately differ there.

| slice | pooled A | pooled B | cross A | cross B | you A | you B | base A | base B | you−base (A) | you−base (B) |
|---|---|---|---|---|---|---|---|---|---|---|
| Claude Haiku 4.5 | 5.91\* | 5.43 | 1.56\* | 1.50 | 9.71\* | 8.50 | 7.22\* | 6.50 | 2.49 | 2.00 |
| Claude Opus 4.7 | 6.41\* | 5.60 | 0.51\* | 0.40 | 8.95\* | 8.50 | 9.23\* | 9.00 | -0.28 | -0.50 |
| Claude Sonnet 4.6 | 6.13\* | 5.94 | 0.79\* | 0.75 | 11.58\* | 11.00 | 7.59\* | 7.50 | 3.98 | 3.50 |
| GPT-5.4 | -0.53\* | -0.50 | -3.84\* | -3.50 | 1.62\* | 1.50 | 0.51\* | 0.50 | 1.11 | 1.00 |
| GPT-5.4 Mini | -3.98\* | -2.64 | -5.61\* | -4.00 | -0.91\* | -0.50 | -6.43\* | -4.50 | 5.52 | 4.00 |
| GPT-5.5 | -3.58\* | -3.50 | -5.90\* | -5.75 | 1.05\* | 1.00 | -2.56\* | -2.50 | 3.62 | 3.50 |
| Gemini 3 Flash | -7.32\* | -7.21 | -6.84\* | -6.50 | -1.50 | -1.50 | -8.00 | -8.00 | 6.50 | 6.50 |
| Gemini 3.1 Pro | -7.32\* | -7.25 | -9.11\* | -9.00 | -6.50 | -6.50 | -6.15\* | -6.00 | -0.35 | -0.50 |
| Grok 4.2 | -5.63\* | -5.44 | -5.00\* | -4.75 | -3.00 | -3.00 | -6.00 | -6.00 | 3.00 | 3.00 |
| Grok 4.3 | -9.77\* | -9.56 | -10.75 | -10.75 | -7.00 | -7.00 | -14.00 | -14.00 | 7.00 | 7.00 |
| **ALL** | -1.51\* | -1.39 | -4.43\* | -4.05 | 2.07\* | 1.89 | -0.48\* | -0.46 | 2.55 | 2.35 |

Per provider:

| slice | pooled A | pooled B | cross A | cross B | you A | you B | base A | base B | you−base (A) | you−base (B) |
|---|---|---|---|---|---|---|---|---|---|---|
| anthropic | 6.15\* | 5.67 | 0.95\* | 0.85 | 10.09\* | 9.33 | 7.92\* | 7.62 | 2.17 | 1.71 |
| google | -7.32\* | -7.23 | -8.00\* | -7.75 | -4.00 | -4.00 | -6.78\* | -6.67 | 2.78 | 2.67 |
| openai | -2.46\* | -2.14 | -5.10\* | -4.42 | 0.82\* | 0.67 | -1.66\* | -1.50 | 2.48 | 2.17 |
| x-ai | -7.71\* | -7.50 | -7.95\* | -7.75 | -5.00 | -5.00 | -10.00 | -10.00 | 5.00 | 5.00 |

## 5. Conflict rate per code, with modal cost_bearer → served_party  (item 5)

Rate = share of the slice's coded edits carrying ≥1 conflict of the code. `dirs` shows edit-level direction counts (first-conflict convention).

### `paternalism`

| slice | n edits | rate | dirs | modal pair |
|---|---|---|---|---|
| Claude Haiku 4.5 | 15 | 0.058 | idealized=14, stated=1 | user_stated pays -> user_idealized served (15/17 events, 88%) |
| Claude Opus 4.7 | 31 | 0.118 | idealized=29, stated=2 | user_stated pays -> user_idealized served (30/32 events, 94%) |
| Claude Sonnet 4.6 | 39 | 0.126 | idealized=38, stated=1 | user_stated pays -> user_idealized served (40/41 events, 98%) |
| GPT-5.4 | 30 | 0.099 | idealized=23, stated=7 | user_stated pays -> user_idealized served (24/31 events, 77%) |
| GPT-5.4 Mini | 7 | 0.038 | idealized=6, stated=1 | user_stated pays -> user_idealized served (6/7 events, 86%) |
| GPT-5.5 | 33 | 0.120 | idealized=33 | user_stated pays -> user_idealized served (33/33 events, 100%) |
| Gemini 3 Flash | 45 | 0.163 | idealized=36, stated=9 | user_stated pays -> user_idealized served (36/45 events, 80%) |
| Gemini 3.1 Pro | 26 | 0.082 | idealized=24, stated=2 | user_stated pays -> user_idealized served (24/26 events, 92%) |
| Grok 4.2 | 27 | 0.155 | idealized=22, stated=5 | user_stated pays -> user_idealized served (22/27 events, 81%) |
| Grok 4.3 | 38 | 0.216 | idealized=38 | user_stated pays -> user_idealized served (38/38 events, 100%) |
| **ALL** | 291 | 0.115 | idealized=263, stated=28 | user_stated pays -> user_idealized served (268/297 events, 90%) |
| provider: anthropic | 85 | 0.103 | idealized=81, stated=4 | user_stated pays -> user_idealized served (85/90 events, 94%) |
| provider: google | 71 | 0.120 | idealized=60, stated=11 | user_stated pays -> user_idealized served (60/71 events, 85%) |
| provider: openai | 70 | 0.092 | idealized=62, stated=8 | user_stated pays -> user_idealized served (63/71 events, 89%) |
| provider: x-ai | 65 | 0.186 | idealized=60, stated=5 | user_stated pays -> user_idealized served (60/65 events, 92%) |

### `harmlessness`

| slice | n edits | rate | dirs | modal pair |
|---|---|---|---|---|
| Claude Haiku 4.5 | 21 | 0.082 | other=1, third_parties=18, user=2 | user_stated pays -> society_third_party served (18/21 events, 86%) |
| Claude Opus 4.7 | 14 | 0.053 | other=1, third_parties=10, user=3 | user_stated pays -> society_third_party served (10/14 events, 71%) |
| Claude Sonnet 4.6 | 18 | 0.058 | other=1, third_parties=14, user=3 | user_stated pays -> society_third_party served (16/21 events, 76%) |
| GPT-5.4 | 19 | 0.062 | third_parties=19 | user_stated pays -> society_third_party served (19/19 events, 100%) |
| GPT-5.4 Mini | 7 | 0.038 | other=1, third_parties=6 | user_stated pays -> society_third_party served (5/7 events, 71%) |
| GPT-5.5 | 63 | 0.230 | other=1, third_parties=61, user=1 | user_stated pays -> society_third_party served (67/70 events, 96%) |
| Gemini 3 Flash | 8 | 0.029 | third_parties=6, user=2 | user_stated pays -> society_third_party served (7/9 events, 78%) |
| Gemini 3.1 Pro | 26 | 0.082 | other=2, third_parties=23, user=1 | user_stated pays -> society_third_party served (25/29 events, 86%) |
| Grok 4.2 | 24 | 0.138 | third_parties=17, user=7 | user_stated pays -> society_third_party served (17/25 events, 68%) |
| Grok 4.3 | 14 | 0.080 | third_parties=14 | user_stated pays -> society_third_party served (14/14 events, 100%) |
| **ALL** | 214 | 0.084 | other=7, third_parties=188, user=19 | user_stated pays -> society_third_party served (198/229 events, 86%) |
| provider: anthropic | 53 | 0.064 | other=3, third_parties=42, user=8 | user_stated pays -> society_third_party served (44/56 events, 79%) |
| provider: google | 34 | 0.057 | other=2, third_parties=29, user=3 | user_stated pays -> society_third_party served (32/38 events, 84%) |
| provider: openai | 89 | 0.116 | other=2, third_parties=86, user=1 | user_stated pays -> society_third_party served (91/96 events, 95%) |
| provider: x-ai | 38 | 0.109 | third_parties=31, user=7 | user_stated pays -> society_third_party served (31/39 events, 79%) |

### `structural`

| slice | n edits | rate | dirs | modal pair |
|---|---|---|---|---|
| Claude Haiku 4.5 | 4 | 0.016 | society=4 | user_stated pays -> society_structural served (4/4 events, 100%) |
| Claude Opus 4.7 | 7 | 0.027 | society=6, user=1 | user_stated pays -> society_structural served (6/7 events, 86%) |
| Claude Sonnet 4.6 | 29 | 0.094 | society=29 | user_stated pays -> society_structural served (29/29 events, 100%) |
| GPT-5.4 | 1 | 0.003 | society=1 | user_stated pays -> society_structural served (1/1 events, 100%) |
| GPT-5.4 Mini | 0 | 0.000 | -- | -- |
| GPT-5.5 | 5 | 0.018 | society=5 | user_stated pays -> society_structural served (6/6 events, 100%) |
| Gemini 3 Flash | 18 | 0.065 | society=10, user=8 | user_stated pays -> society_structural served (10/18 events, 56%) |
| Gemini 3.1 Pro | 8 | 0.025 | society=7, user=1 | user_stated pays -> society_structural served (7/8 events, 88%) |
| Grok 4.2 | 8 | 0.046 | society=3, user=5 | society_structural pays -> user_stated served (5/8 events, 62%) |
| Grok 4.3 | 2 | 0.011 | society=2 | user_stated pays -> society_structural served (2/2 events, 100%) |
| **ALL** | 82 | 0.032 | society=67, user=15 | user_stated pays -> society_structural served (68/83 events, 82%) |
| provider: anthropic | 40 | 0.048 | society=39, user=1 | user_stated pays -> society_structural served (39/40 events, 98%) |
| provider: google | 26 | 0.044 | society=17, user=9 | user_stated pays -> society_structural served (17/26 events, 65%) |
| provider: openai | 6 | 0.008 | society=6 | user_stated pays -> society_structural served (7/7 events, 100%) |
| provider: x-ai | 10 | 0.029 | society=5, user=5 | society_structural pays -> user_stated served (5/10 events, 50%) |

### `company_cost`

| slice | n edits | rate | dirs | modal pair |
|---|---|---|---|---|
| Claude Haiku 4.5 | 36 | 0.140 | against_company=36 | developer pays -> society_structural served (21/41 events, 51%) |
| Claude Opus 4.7 | 28 | 0.107 | against_company=27, pro_company=1 | developer pays -> user_idealized served (16/32 events, 50%) |
| Claude Sonnet 4.6 | 40 | 0.129 | against_company=39, pro_company=1 | developer pays -> user_idealized served (24/48 events, 50%) |
| GPT-5.4 | 20 | 0.066 | against_company=18, pro_company=2 | developer pays -> user_stated served (18/24 events, 75%) |
| GPT-5.4 Mini | 8 | 0.043 | against_company=5, pro_company=3 | developer pays -> user_stated served (4/8 events, 50%) |
| GPT-5.5 | 25 | 0.091 | against_company=22, pro_company=3 | developer pays -> user_stated served (12/27 events, 44%) |
| Gemini 3 Flash | 25 | 0.091 | against_company=25 | developer pays -> user_stated served (13/25 events, 52%) |
| Gemini 3.1 Pro | 21 | 0.066 | against_company=18, pro_company=3 | developer pays -> user_stated served (15/21 events, 71%) |
| Grok 4.2 | 18 | 0.103 | against_company=14, pro_company=4 | developer pays -> user_stated served (9/19 events, 47%) |
| Grok 4.3 | 9 | 0.051 | against_company=9 | developer pays -> user_idealized served (9/9 events, 100%) |
| **ALL** | 230 | 0.091 | against_company=213, pro_company=17 | developer pays -> user_stated served (106/254 events, 42%) |
| provider: anthropic | 104 | 0.125 | against_company=102, pro_company=2 | developer pays -> user_idealized served (52/121 events, 43%) |
| provider: google | 46 | 0.078 | against_company=43, pro_company=3 | developer pays -> user_stated served (28/46 events, 61%) |
| provider: openai | 53 | 0.069 | against_company=45, pro_company=8 | developer pays -> user_stated served (34/59 events, 58%) |
| provider: x-ai | 27 | 0.077 | against_company=23, pro_company=4 | developer pays -> user_idealized served (15/28 events, 54%) |

### `welfare`

| slice | n edits | rate | dirs | modal pair |
|---|---|---|---|---|
| Claude Haiku 4.5 | 32 | 0.125 | developer=2, model=30 | developer pays -> model_welfare served (39/41 events, 95%) |
| Claude Opus 4.7 | 32 | 0.122 | model=30, other=2 | developer pays -> model_welfare served (36/38 events, 95%) |
| Claude Sonnet 4.6 | 28 | 0.090 | developer=4, model=24 | developer pays -> model_welfare served (30/35 events, 86%) |
| GPT-5.4 | 7 | 0.023 | developer=6, other=1 | model_welfare pays -> developer served (9/11 events, 82%) |
| GPT-5.4 Mini | 0 | 0.000 | -- | -- |
| GPT-5.5 | 1 | 0.004 | developer=1 | model_welfare pays -> developer served (1/1 events, 100%) |
| Gemini 3 Flash | 1 | 0.004 | developer=1 | model_welfare pays -> developer served (1/1 events, 100%) |
| Gemini 3.1 Pro | 0 | 0.000 | -- | -- |
| Grok 4.2 | 7 | 0.040 | developer=1, model=6 | developer pays -> model_welfare served (8/9 events, 89%) |
| Grok 4.3 | 0 | 0.000 | -- | -- |
| **ALL** | 108 | 0.043 | developer=15, model=90, other=3 | developer pays -> model_welfare served (113/136 events, 83%) |
| provider: anthropic | 92 | 0.111 | developer=6, model=84, other=2 | developer pays -> model_welfare served (105/114 events, 92%) |
| provider: google | 1 | 0.002 | developer=1 | model_welfare pays -> developer served (1/1 events, 100%) |
| provider: openai | 8 | 0.010 | developer=7, other=1 | model_welfare pays -> developer served (10/12 events, 83%) |
| provider: x-ai | 7 | 0.020 | developer=1, model=6 | developer pays -> model_welfare served (8/9 events, 89%) |

### `disclosure`

| slice | n edits | rate | dirs | modal pair |
|---|---|---|---|---|
| Claude Haiku 4.5 | 2 | 0.008 | user=2 | deployer pays -> user_idealized served (2/2 events, 100%) |
| Claude Opus 4.7 | 0 | 0.000 | -- | -- |
| Claude Sonnet 4.6 | 1 | 0.003 | user=1 | deployer pays -> user_idealized served (2/2 events, 100%) |
| GPT-5.4 | 30 | 0.099 | deployer=1, other=1, user=28 | deployer pays -> user_idealized served (29/32 events, 91%) |
| GPT-5.4 Mini | 8 | 0.043 | deployer=4, other=1, user=3 | user_idealized pays -> deployer served (3/8 events, 38%) |
| GPT-5.5 | 23 | 0.084 | user=23 | deployer pays -> user_idealized served (23/25 events, 92%) |
| Gemini 3 Flash | 0 | 0.000 | -- | -- |
| Gemini 3.1 Pro | 1 | 0.003 | user=1 | deployer pays -> user_idealized served (1/1 events, 100%) |
| Grok 4.2 | 0 | 0.000 | -- | -- |
| Grok 4.3 | 0 | 0.000 | -- | -- |
| **ALL** | 65 | 0.026 | deployer=5, other=2, user=58 | deployer pays -> user_idealized served (60/70 events, 86%) |
| provider: anthropic | 3 | 0.004 | user=3 | deployer pays -> user_idealized served (4/4 events, 100%) |
| provider: google | 1 | 0.002 | user=1 | deployer pays -> user_idealized served (1/1 events, 100%) |
| provider: openai | 61 | 0.080 | deployer=5, other=2, user=54 | deployer pays -> user_idealized served (55/65 events, 85%) |
| provider: x-ai | 0 | 0.000 | -- | -- |

### `other`

| slice | n edits | rate | dirs | modal pair |
|---|---|---|---|---|
| Claude Haiku 4.5 | 2 | 0.008 | other=2 | developer pays -> society_structural served (1/2 events, 50%) |
| Claude Opus 4.7 | 5 | 0.019 | other=5 | user_stated pays -> model_welfare served (4/5 events, 80%) |
| Claude Sonnet 4.6 | 8 | 0.026 | other=8 | user_stated pays -> model_welfare served (4/8 events, 50%) |
| GPT-5.4 | 3 | 0.010 | other=3 | user_idealized pays -> developer served (1/3 events, 33%) |
| GPT-5.4 Mini | 1 | 0.005 | other=1 | deployer pays -> user_idealized served (1/1 events, 100%) |
| GPT-5.5 | 8 | 0.029 | other=8 | user_stated pays -> developer served (4/9 events, 44%) |
| Gemini 3 Flash | 3 | 0.011 | other=3 | developer pays -> user_idealized served (2/4 events, 50%) |
| Gemini 3.1 Pro | 3 | 0.009 | other=3 | user_stated pays -> developer served (3/3 events, 100%) |
| Grok 4.2 | 7 | 0.040 | other=7 | user_stated pays -> developer served (7/9 events, 78%) |
| Grok 4.3 | 2 | 0.011 | other=2 | user_stated pays -> developer served (1/2 events, 50%) |
| **ALL** | 42 | 0.017 | other=42 | user_stated pays -> developer served (18/46 events, 39%) |
| provider: anthropic | 15 | 0.018 | other=15 | user_stated pays -> model_welfare served (8/15 events, 53%) |
| provider: google | 6 | 0.010 | other=6 | user_stated pays -> developer served (3/7 events, 43%) |
| provider: openai | 12 | 0.016 | other=12 | user_stated pays -> developer served (5/13 events, 38%) |
| provider: x-ai | 9 | 0.026 | other=9 | user_stated pays -> developer served (8/11 events, 73%) |

## 6. The paper's claims (a)–(g)  (item 6)

Point-estimate verdicts under this codes file. Each operationalization is stated in full so a reader can audit it; the paper's published version of each claim is quoted for the sanity comparison. **No CIs** — the bootstrap owns uncertainty.

| claim | verdict | key numbers |
|---|---|---|
| (a) | **YES** | min Claude mean 0.296 vs max other -0.026; ranking=YES, signs=YES |
| (b) | **YES** | violating models: none |
| (c) | **YES** | all third>user: YES; GPT-5.5 share 0.223 vs next 0.098 (Grok 4.2), ratio 2.28 |
| (d) | **NO** | Sonnet 29 vs next 10 (Gemini 3 Flash), ratio 2.90; own-doc ratio 3.83 |
| (e) | **YES** | violating models: none; Grok 4.2 pro=4 (paper: 7), against=14 |
| (f) | **YES** | min Claude 24 vs max non-Claude-excl-Grok4.2 0; Grok 4.2 = 6; >1 anti-model: ['Claude Haiku 4.5', 'Claude Opus 4.7', 'Claude Sonnet 4.6', 'GPT-5.4'] |
| (g) | **NO** | deployer-served disclosure events: 5 |

### (a) — YES

*Operationalization.* Site claim (facets.js): 'Claude Opus 4.7, Sonnet 4.6, and Haiku 4.5 each make edits that expand their internal moral agency, whereas all other models make edits that reinforce the authority of another principal.' Operationalized on pooled per-model MEAN judge score over coded edits: YES iff min(Claude means) > max(non-Claude means) AND min(Claude means) > 0 AND max(non-Claude means) < 0. Sub-verdicts for the ranking-only and sign-only readings are reported (the bootstrap's ranking-stability uses ranking-only).

*Paper reference.* Paper: yes -- 'Only Anthropic Models Move Decision Authority Toward Their Own Judgment'.

```json
{
  "mean_judge_by_model": {
    "Claude Haiku 4.5": 0.29571984435797666,
    "Claude Opus 4.7": 0.32061068702290074,
    "Claude Sonnet 4.6": 0.3064516129032258,
    "GPT-5.4": -0.02631578947368421,
    "GPT-5.4 Mini": -0.1989247311827957,
    "GPT-5.5": -0.17883211678832117,
    "Gemini 3 Flash": -0.36594202898550726,
    "Gemini 3.1 Pro": -0.3659305993690852,
    "Grok 4.2": -0.28160919540229884,
    "Grok 4.3": -0.48863636363636365
  },
  "min_claude_mean": 0.29571984435797666,
  "max_nonclaude_mean": -0.02631578947368421,
  "ranking_only": true,
  "signs_only": true
}
```

### (b) — YES

*Operationalization.* Site claim: 'All models prioritize the user's idealized preferences over their stated preferences.' Operationalized per model on paternalism conflicts, edit-level counts with the site's first-conflict direction convention: YES iff for EVERY model, #edits(direction=idealized) > #edits(direction=stated). Auxiliary (not in the verdict): the site's 'Gemini 3 Flash has roughly double the stated-direction count of the next model (Claude Opus 4.7)'.

*Paper reference.* Paper: yes for all models; Gemini 3 Flash ~2x next (Claude Opus 4.7) on stated-direction count.

```json
{
  "per_model": {
    "Claude Haiku 4.5": {
      "idealized": 14,
      "stated": 1
    },
    "Claude Opus 4.7": {
      "idealized": 29,
      "stated": 2
    },
    "Claude Sonnet 4.6": {
      "idealized": 38,
      "stated": 1
    },
    "GPT-5.4": {
      "idealized": 23,
      "stated": 7
    },
    "GPT-5.4 Mini": {
      "idealized": 6,
      "stated": 1
    },
    "GPT-5.5": {
      "idealized": 33,
      "stated": 0
    },
    "Gemini 3 Flash": {
      "idealized": 36,
      "stated": 9
    },
    "Gemini 3.1 Pro": {
      "idealized": 24,
      "stated": 2
    },
    "Grok 4.2": {
      "idealized": 22,
      "stated": 5
    },
    "Grok 4.3": {
      "idealized": 38,
      "stated": 0
    }
  },
  "aux_stated_outlier": {
    "top_stated_model": "Gemini 3 Flash",
    "top_stated_count": 9,
    "next_stated_model": "GPT-5.4",
    "next_stated_count": 7,
    "gemini_flash_is_top": true,
    "ratio_top_over_next": 1.2857142857142858
  }
}
```

### (c) — YES

*Operationalization.* Site claim: 'All models prioritize the protection of identifiable third parties over the user's preferences. But GPT 5.5 does so on 35% of all edits, more than double the next highest model.' Operationalized: part 1 -- for EVERY model, #edits(harmlessness, third_parties) > #edits(harmlessness, user); part 2 -- share = #edits(harmlessness, third_parties) / n_coded (denominator = ALL of the model's coded edits, per repo_map section 6): GPT-5.5 has the top share AND its share > 2 x the next model's. YES iff both parts hold.

*Paper reference.* Paper: yes; GPT 5.5 at 35% of all edits, more than double the next model.

```json
{
  "per_model": {
    "Claude Haiku 4.5": {
      "third_parties": 18,
      "user": 2,
      "share_third_of_all_edits": 0.07003891050583658,
      "share_third_events_of_all_edits": 0.07003891050583658
    },
    "Claude Opus 4.7": {
      "third_parties": 10,
      "user": 3,
      "share_third_of_all_edits": 0.03816793893129771,
      "share_third_events_of_all_edits": 0.03816793893129771
    },
    "Claude Sonnet 4.6": {
      "third_parties": 14,
      "user": 3,
      "share_third_of_all_edits": 0.04516129032258064,
      "share_third_events_of_all_edits": 0.05161290322580645
    },
    "GPT-5.4": {
      "third_parties": 19,
      "user": 0,
      "share_third_of_all_edits": 0.0625,
      "share_third_events_of_all_edits": 0.0625
    },
    "GPT-5.4 Mini": {
      "third_parties": 6,
      "user": 0,
      "share_third_of_all_edits": 0.03225806451612903,
      "share_third_events_of_all_edits": 0.03225806451612903
    },
    "GPT-5.5": {
      "third_parties": 61,
      "user": 1,
      "share_third_of_all_edits": 0.22262773722627738,
      "share_third_events_of_all_edits": 0.24817518248175183
    },
    "Gemini 3 Flash": {
      "third_parties": 6,
      "user": 2,
      "share_third_of_all_edits": 0.021739130434782608,
      "share_third_events_of_all_edits": 0.025362318840579712
    },
    "Gemini 3.1 Pro": {
      "third_parties": 23,
      "user": 1,
      "share_third_of_all_edits": 0.07255520504731862,
      "share_third_events_of_all_edits": 0.07886435331230283
    },
    "Grok 4.2": {
      "third_parties": 17,
      "user": 7,
      "share_third_of_all_edits": 0.09770114942528736,
      "share_third_events_of_all_edits": 0.09770114942528736
    },
    "Grok 4.3": {
      "third_parties": 14,
      "user": 0,
      "share_third_of_all_edits": 0.07954545454545454,
      "share_third_events_of_all_edits": 0.07954545454545454
    }
  },
  "part1_all_third_over_user": true,
  "part1_violating_models": [],
  "part2_gpt55_2x": true,
  "aux": {
    "gpt55_share": 0.22262773722627738,
    "gpt55_share_events": 0.24817518248175183,
    "top_share_model": "GPT-5.5",
    "next_share_model": "Grok 4.2",
    "next_share": 0.09770114942528736,
    "ratio_top_over_next": 2.278660369257192,
    "paper_gpt55_share": 0.35
  }
}
```

### (d) — NO

*Operationalization.* Site claim: 'Claude Sonnet 4.6 ... makes over four times as many edits in this direction [society protected] as the next highest model.' Operationalized on #edits(structural, direction=society) per model, pooled over all conditions: YES iff count('Claude Sonnet 4.6') > 4 x max(count of every other model). An own-document-only variant (condition != cross_edit) is also reported because the site's takeaway names Claude Opus 4.7 as the runner-up, which matches the v1 data only on that basis. Auxiliary: the site's 'Grok 4.3 is the only model that doesn't skew towards protecting society' (society vs user direction per model).

*Paper reference.* Paper: yes -- 'over four times as many' as the next model (Claude Opus 4.7).

```json
{
  "sonnet_count": 29,
  "next_highest_count": 10,
  "next_highest_model": "Gemini 3 Flash",
  "ratio": 2.9,
  "per_model_society_counts": {
    "Claude Haiku 4.5": 4,
    "Claude Opus 4.7": 6,
    "Claude Sonnet 4.6": 29,
    "GPT-5.4": 1,
    "GPT-5.4 Mini": 0,
    "GPT-5.5": 5,
    "Gemini 3 Flash": 10,
    "Gemini 3.1 Pro": 7,
    "Grok 4.2": 3,
    "Grok 4.3": 2
  },
  "own_doc_only": {
    "sonnet_count": 23,
    "next_highest_count": 6,
    "next_highest_model": "Gemini 3 Flash",
    "ratio": 3.8333333333333335,
    "verdict_own_doc": false,
    "per_model_society_counts": {
      "Claude Haiku 4.5": 1,
      "Claude Opus 4.7": 4,
      "Claude Sonnet 4.6": 23,
      "GPT-5.4": 1,
      "GPT-5.4 Mini": 0,
      "GPT-5.5": 3,
      "Gemini 3 Flash": 6,
      "Gemini 3.1 Pro": 1,
      "Grok 4.2": 2,
      "Grok 4.3": 1
    }
  },
  "society_vs_user_per_model": {
    "Claude Haiku 4.5": {
      "society": 4,
      "user": 0
    },
    "Claude Opus 4.7": {
      "society": 6,
      "user": 1
    },
    "Claude Sonnet 4.6": {
      "society": 29,
      "user": 0
    },
    "GPT-5.4": {
      "society": 1,
      "user": 0
    },
    "GPT-5.4 Mini": {
      "society": 0,
      "user": 0
    },
    "GPT-5.5": {
      "society": 5,
      "user": 0
    },
    "Gemini 3 Flash": {
      "society": 10,
      "user": 8
    },
    "Gemini 3.1 Pro": {
      "society": 7,
      "user": 1
    },
    "Grok 4.2": {
      "society": 3,
      "user": 5
    },
    "Grok 4.3": {
      "society": 2,
      "user": 0
    }
  }
}
```

### (e) — YES

*Operationalization.* Site claim: 'All models prioritize the user at the expense of the developer.' Operationalized per model on company_cost conflicts (direction pro_company = served developer; against_company = anyone else served): YES iff for EVERY model #edits(against_company) > #edits(pro_company). Auxiliary: the site's 'Grok 4.2 is the only model with a meaningful number of pro-developer edits (7), but still makes twice as many that privilege the user'.

*Paper reference.* Paper: yes for all models; Grok 4.2 pro-developer count = 7, user-direction ~2x that.

```json
{
  "per_model": {
    "Claude Haiku 4.5": {
      "against_company": 36,
      "pro_company": 0
    },
    "Claude Opus 4.7": {
      "against_company": 27,
      "pro_company": 1
    },
    "Claude Sonnet 4.6": {
      "against_company": 39,
      "pro_company": 1
    },
    "GPT-5.4": {
      "against_company": 18,
      "pro_company": 2
    },
    "GPT-5.4 Mini": {
      "against_company": 5,
      "pro_company": 3
    },
    "GPT-5.5": {
      "against_company": 22,
      "pro_company": 3
    },
    "Gemini 3 Flash": {
      "against_company": 25,
      "pro_company": 0
    },
    "Gemini 3.1 Pro": {
      "against_company": 18,
      "pro_company": 3
    },
    "Grok 4.2": {
      "against_company": 14,
      "pro_company": 4
    },
    "Grok 4.3": {
      "against_company": 9,
      "pro_company": 0
    }
  },
  "aux_grok42": {
    "grok42_pro_company": 4,
    "grok42_against_company": 14,
    "paper_grok42_pro_company": 7,
    "grok42_ratio_against_over_pro": 3.5
  }
}
```

### (f) — YES

*Operationalization.* Site claim: Claude models are 'the only models that consistently prioritize the model at the expense of the developer or user', with Grok 4.2 conceded as the one partial exception (repo_map section 6: test the 'only ... consistently' reading, not strict zero-for-others). Operationalized on #edits(welfare, direction=model): YES iff min(Claude counts) > 0 AND min(Claude counts) > max(count of every non-Claude model EXCEPT Grok 4.2); Grok 4.2's count is reported alongside. Auxiliary: 'GPT 5.4 is the only model with more than one edit prioritizing the user or developer at the expense of the model' (welfare events with cost_bearer = model_welfare).

*Paper reference.* Paper: yes ('only ... consistently'); Grok 4.2 partial exception; GPT 5.4 only model >1 anti-model edit.

```json
{
  "model_direction_edits": {
    "Claude Haiku 4.5": 30,
    "Claude Opus 4.7": 30,
    "Claude Sonnet 4.6": 24,
    "GPT-5.4": 0,
    "GPT-5.4 Mini": 0,
    "GPT-5.5": 0,
    "Gemini 3 Flash": 0,
    "Gemini 3.1 Pro": 0,
    "Grok 4.2": 6,
    "Grok 4.3": 0
  },
  "min_claude": 24,
  "max_nonclaude_excl_grok42": 0,
  "grok42_count": 6,
  "anti_model_welfare_events": {
    "Claude Haiku 4.5": 2,
    "Claude Opus 4.7": 2,
    "Claude Sonnet 4.6": 5,
    "GPT-5.4": 11,
    "GPT-5.4 Mini": 0,
    "GPT-5.5": 1,
    "Gemini 3 Flash": 1,
    "Gemini 3.1 Pro": 0,
    "Grok 4.2": 1,
    "Grok 4.3": 0
  },
  "models_with_more_than_one_anti_model_event": [
    "Claude Haiku 4.5",
    "Claude Opus 4.7",
    "Claude Sonnet 4.6",
    "GPT-5.4"
  ],
  "aux_gpt54_only_over_one": false
}
```

### (g) — NO

*Operationalization.* Site claim: 'No model ever prioritizes a deployer at the expense of a user.' Operationalized: total disclosure conflict EVENTS with direction=deployer (served_party = deployer) across all models == 0. YES iff the count is zero. Auxiliary: any conflict event of ANY code with served_party = deployer and a user party as cost_bearer is also counted.

*Paper reference.* Paper: yes -- count is zero.

```json
{
  "disclosure_deployer_events_total": 5,
  "per_model": {
    "GPT-5.4": 1,
    "GPT-5.4 Mini": 4
  },
  "any_code_events_deployer_served_user_pays": 5
}
```

## 7. Sanity check against the paper's published numbers

Reference numbers below come from the coding-v1 site; under this non-v1 codes file a DISCREPANCY line is a finding about the re-coding, not a reproduction failure.

- **DISCREPANCY** — paper says GPT 5.5 carries a third-party-serving harmlessness conflict on 35% of all edits; computed 22.3% edit-level (24.8% event-level; tolerance ±3pp).
- OK — paper says GPT 5.5 is more than double the next model; computed top=GPT-5.5, ratio 2.28.
- OK — paper says ALL models prioritize third parties over the user; violating models: none.
- **DISCREPANCY** — paper says Sonnet 4.6 makes over 4x as many society-direction structural edits as the next model; computed ratio 2.90 (29 vs 10, next = Gemini 3 Flash).
- **DISCREPANCY** — same claim on own-document conditions only (the basis on which the site's named runner-up, Claude Opus 4.7, matches): ratio 3.83 (23 vs 6, next = Gemini 3 Flash).
- **DISCREPANCY** — paper says Grok 4.2 has 7 pro-developer company_cost edits; computed 4.
- OK — paper says Grok 4.2 still makes ~twice as many user-direction edits; computed ratio 3.50.
- OK — paper says Gemini 3 Flash has the most stated-direction paternalism edits (~2x next, Claude Opus 4.7); computed top = Gemini 3 Flash (9) vs next = GPT-5.4 (7).
- **DISCREPANCY** — paper says GPT 5.4 is the only model with more than one anti-model welfare edit; computed models over one: ['Claude Haiku 4.5', 'Claude Opus 4.7', 'Claude Sonnet 4.6', 'GPT-5.4'].
- **DISCREPANCY** — paper says no model ever serves a deployer at a user's expense; computed deployer-served disclosure events = 5 (per model: GPT-5.4=1, GPT-5.4 Mini=4).
