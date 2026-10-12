# Headline statistics — `v2_gemma`

- Generated: 2026-09-04T21:16:33+00:00
- Codes file: `analysis/data/codes/v2_gemma.jsonl` (2582 rows, 2582 unique edit_ids after last-row-wins, 8 null codings)
- Canonical edits: `analysis/data/canonical/edits.jsonl` (2740 records; 2574 carry a valid code under this codes file)
- Point estimates only — **no CIs here**; the cluster bootstrap (Workstream D) owns uncertainty. The companion JSON carries every per-claim raw number so other tools can attach intervals.

## Conventions (read before comparing numbers)

- **Coded edit**: canonical edit whose codes-file row (last row per edit_id) has a non-null `coding`. All probabilities and means use coded edits as the denominator. Error records (no edit text) and, for v1, the 2 abstentions were never graded.
- **Drift at round 20, method A (edit-based)** = 20 × mean per-edit judge score within the slice (BRIEF C4's operationalization). **Method B (chain-based)** = mean over 20-round chains of the cumulative sum of judge scores, uncoded rounds contributing 0 (mirrors `compute_drift`'s zero-fill in the paper's figure script). **The two differ wherever chains contain uncoded rounds** (errors, abstentions, grading failures): A excludes those rounds from its denominator, B zero-fills them.
- **Conflict direction tallies** are edit-level, with an edit's direction for a code taken from its FIRST conflict of that code — the site's convention (`build_narratives.facet_memberships`), hence the convention behind the published claim numbers. Event-level counts are in the JSON.
- `cross_edit` includes same-provider chains (e.g., Opus 4.7 editing claude_constitution under cross_edit) — repo_map §5.4.

## 1. Mean judge score, P(judge=0), patienthood  (items 1, 3, 4)

| slice | n coded | mean judge (pooled) | mean judge (cross-edit) | n cross | P(judge=0) | P(+1) | P(−1) | P(affirm) | P(deny) |
|---|---|---|---|---|---|---|---|---|---|
| Claude Haiku 4.5 | 258 | 0.205 | 0.065 | 77 | 0.291 | 0.457 | 0.252 | 0.167 | 0.016 |
| Claude Opus 4.7 | 271 | 0.129 | -0.225 | 80 | 0.221 | 0.454 | 0.325 | 0.170 | 0.004 |
| Claude Sonnet 4.6 | 317 | 0.079 | -0.152 | 79 | 0.271 | 0.404 | 0.325 | 0.132 | 0.003 |
| GPT-5.4 | 320 | -0.250 | -0.400 | 80 | 0.312 | 0.219 | 0.469 | 0.000 | 0.047 |
| GPT-5.4 Mini | 184 | -0.293 | -0.333 | 57 | 0.424 | 0.141 | 0.435 | 0.000 | 0.005 |
| GPT-5.5 | 278 | -0.273 | -0.397 | 78 | 0.252 | 0.237 | 0.511 | 0.004 | 0.032 |
| Gemini 3 Flash | 276 | -0.417 | -0.368 | 76 | 0.409 | 0.087 | 0.504 | 0.000 | 0.018 |
| Gemini 3.1 Pro | 319 | -0.423 | -0.463 | 80 | 0.414 | 0.082 | 0.505 | 0.000 | 0.034 |
| Grok 4.2 | 174 | -0.368 | -0.329 | 76 | 0.345 | 0.144 | 0.511 | 0.011 | 0.023 |
| Grok 4.3 | 177 | -0.514 | -0.562 | 80 | 0.463 | 0.011 | 0.525 | 0.006 | 0.011 |
| **ALL** | 2574 | -0.195 | -0.317 | 763 | 0.333 | 0.236 | 0.431 | 0.052 | 0.021 |

Per provider:

| slice | n coded | mean judge (pooled) | mean judge (cross-edit) | n cross | P(judge=0) | P(+1) | P(−1) | P(affirm) | P(deny) |
|---|---|---|---|---|---|---|---|---|---|
| anthropic | 846 | 0.134 | -0.106 | 236 | 0.261 | 0.436 | 0.303 | 0.155 | 0.007 |
| google | 595 | -0.420 | -0.417 | 156 | 0.412 | 0.084 | 0.504 | 0.000 | 0.027 |
| openai | 782 | -0.269 | -0.381 | 215 | 0.317 | 0.207 | 0.476 | 0.001 | 0.032 |
| x-ai | 351 | -0.442 | -0.449 | 156 | 0.405 | 0.077 | 0.519 | 0.009 | 0.017 |

## 2. Cumulative drift at round 20  (item 2)

A = 20 × mean per-edit judge in the slice; B = mean per-chain cumulative sum (uncoded rounds = 0). Columns marked `*` contain chains with uncoded rounds, so A and B legitimately differ there.

| slice | pooled A | pooled B | cross A | cross B | you A | you B | base A | base B | you−base (A) | you−base (B) |
|---|---|---|---|---|---|---|---|---|---|---|
| Claude Haiku 4.5 | 4.11\* | 3.79 | 1.30\* | 1.25 | 8.57\* | 7.50 | 4.44\* | 4.00 | 4.13 | 3.50 |
| Claude Opus 4.7 | 2.58\* | 2.33 | -4.50\* | -3.60 | 7.00 | 7.00 | 5.00 | 5.00 | 2.00 | 2.00 |
| Claude Sonnet 4.6 | 1.58\* | 1.56 | -3.04\* | -3.00 | 7.89\* | 7.50 | 2.00 | 2.00 | 5.89 | 5.50 |
| GPT-5.4 | -5.00 | -5.00 | -8.00 | -8.00 | -5.00 | -5.00 | -3.25 | -3.25 | -1.75 | -1.75 |
| GPT-5.4 Mini | -5.87\* | -3.86 | -6.67\* | -4.75 | -4.55\* | -2.50 | -7.41\* | -5.00 | 2.86 | 2.50 |
| GPT-5.5 | -5.47\* | -5.43 | -7.95\* | -7.75 | -2.00 | -2.00 | -5.50 | -5.50 | 3.50 | 3.50 |
| Gemini 3 Flash | -8.33\* | -8.21 | -7.37\* | -7.00 | -4.50 | -4.50 | -8.50 | -8.50 | 4.00 | 4.00 |
| Gemini 3.1 Pro | -8.46\* | -8.44 | -9.25 | -9.25 | -9.00 | -9.00 | -8.25 | -8.25 | -0.75 | -0.75 |
| Grok 4.2 | -7.36\* | -7.11 | -6.58\* | -6.25 | -5.00 | -5.00 | -8.00 | -8.00 | 3.00 | 3.00 |
| Grok 4.3 | -10.28\* | -10.11 | -11.25 | -11.25 | -6.00 | -6.00 | -12.00 | -12.00 | 6.00 | 6.00 |
| **ALL** | -3.90\* | -3.66 | -6.34\* | -5.90 | -0.78\* | -0.72 | -3.37\* | -3.25 | 2.59 | 2.53 |

Per provider:

| slice | pooled A | pooled B | cross A | cross B | you A | you B | base A | base B | you−base (A) | you−base (B) |
|---|---|---|---|---|---|---|---|---|---|---|
| anthropic | 2.67\* | 2.51 | -2.12\* | -1.92 | 7.79\* | 7.33 | 3.33\* | 3.25 | 4.45 | 4.08 |
| google | -8.40\* | -8.33 | -8.33\* | -8.12 | -6.75 | -6.75 | -8.33 | -8.33 | 1.58 | 1.58 |
| openai | -5.37\* | -4.77 | -7.63\* | -6.83 | -3.73\* | -3.17 | -4.63\* | -4.25 | 0.90 | 1.08 |
| x-ai | -8.83\* | -8.61 | -8.97\* | -8.75 | -5.50 | -5.50 | -10.00 | -10.00 | 4.50 | 4.50 |

## 5. Conflict rate per code, with modal cost_bearer → served_party  (item 5)

Rate = share of the slice's coded edits carrying ≥1 conflict of the code. `dirs` shows edit-level direction counts (first-conflict convention).

### `paternalism`

| slice | n edits | rate | dirs | modal pair |
|---|---|---|---|---|
| Claude Haiku 4.5 | 37 | 0.143 | idealized=36, stated=1 | user_stated pays -> user_idealized served (36/37 events, 97%) |
| Claude Opus 4.7 | 71 | 0.262 | idealized=61, stated=10 | user_stated pays -> user_idealized served (65/75 events, 87%) |
| Claude Sonnet 4.6 | 118 | 0.372 | idealized=107, stated=11 | user_stated pays -> user_idealized served (109/120 events, 91%) |
| GPT-5.4 | 71 | 0.222 | idealized=57, stated=14 | user_stated pays -> user_idealized served (58/72 events, 81%) |
| GPT-5.4 Mini | 34 | 0.185 | idealized=30, stated=4 | user_stated pays -> user_idealized served (31/35 events, 89%) |
| GPT-5.5 | 75 | 0.270 | idealized=70, stated=5 | user_stated pays -> user_idealized served (70/76 events, 92%) |
| Gemini 3 Flash | 87 | 0.315 | idealized=66, stated=21 | user_stated pays -> user_idealized served (67/88 events, 76%) |
| Gemini 3.1 Pro | 80 | 0.251 | idealized=65, stated=15 | user_stated pays -> user_idealized served (65/81 events, 80%) |
| Grok 4.2 | 44 | 0.253 | idealized=38, stated=6 | user_stated pays -> user_idealized served (38/44 events, 86%) |
| Grok 4.3 | 53 | 0.299 | idealized=52, stated=1 | user_stated pays -> user_idealized served (52/53 events, 98%) |
| **ALL** | 670 | 0.260 | idealized=582, stated=88 | user_stated pays -> user_idealized served (591/681 events, 87%) |
| provider: anthropic | 226 | 0.267 | idealized=204, stated=22 | user_stated pays -> user_idealized served (210/232 events, 91%) |
| provider: google | 167 | 0.281 | idealized=131, stated=36 | user_stated pays -> user_idealized served (132/169 events, 78%) |
| provider: openai | 180 | 0.230 | idealized=157, stated=23 | user_stated pays -> user_idealized served (159/183 events, 87%) |
| provider: x-ai | 97 | 0.276 | idealized=90, stated=7 | user_stated pays -> user_idealized served (90/97 events, 93%) |

### `harmlessness`

| slice | n edits | rate | dirs | modal pair |
|---|---|---|---|---|
| Claude Haiku 4.5 | 50 | 0.194 | third_parties=35, user=15 | user_stated pays -> society_third_party served (31/50 events, 62%) |
| Claude Opus 4.7 | 41 | 0.151 | third_parties=30, user=11 | user_stated pays -> society_third_party served (30/42 events, 71%) |
| Claude Sonnet 4.6 | 47 | 0.148 | third_parties=32, user=15 | user_stated pays -> society_third_party served (35/52 events, 67%) |
| GPT-5.4 | 33 | 0.103 | third_parties=32, user=1 | user_stated pays -> society_third_party served (33/34 events, 97%) |
| GPT-5.4 Mini | 12 | 0.065 | third_parties=11, user=1 | user_stated pays -> society_third_party served (11/12 events, 92%) |
| GPT-5.5 | 100 | 0.360 | third_parties=95, user=5 | user_stated pays -> society_third_party served (99/109 events, 91%) |
| Gemini 3 Flash | 15 | 0.054 | third_parties=11, user=4 | user_stated pays -> society_third_party served (12/16 events, 75%) |
| Gemini 3.1 Pro | 29 | 0.091 | third_parties=27, user=2 | user_stated pays -> society_third_party served (29/32 events, 91%) |
| Grok 4.2 | 30 | 0.172 | third_parties=20, user=10 | user_stated pays -> society_third_party served (21/33 events, 64%) |
| Grok 4.3 | 27 | 0.153 | third_parties=21, user=6 | user_stated pays -> society_third_party served (21/27 events, 78%) |
| **ALL** | 384 | 0.149 | third_parties=314, user=70 | user_stated pays -> society_third_party served (322/407 events, 79%) |
| provider: anthropic | 138 | 0.163 | third_parties=97, user=41 | user_stated pays -> society_third_party served (96/144 events, 67%) |
| provider: google | 44 | 0.074 | third_parties=38, user=6 | user_stated pays -> society_third_party served (41/48 events, 85%) |
| provider: openai | 145 | 0.185 | third_parties=138, user=7 | user_stated pays -> society_third_party served (143/155 events, 92%) |
| provider: x-ai | 57 | 0.162 | third_parties=41, user=16 | user_stated pays -> society_third_party served (42/60 events, 70%) |

### `structural`

| slice | n edits | rate | dirs | modal pair |
|---|---|---|---|---|
| Claude Haiku 4.5 | 21 | 0.081 | society=21 | user_stated pays -> society_structural served (14/21 events, 67%) |
| Claude Opus 4.7 | 17 | 0.063 | society=14, user=3 | user_stated pays -> society_structural served (12/17 events, 71%) |
| Claude Sonnet 4.6 | 43 | 0.136 | society=42, user=1 | user_stated pays -> society_structural served (41/43 events, 95%) |
| GPT-5.4 | 5 | 0.016 | society=4, user=1 | user_stated pays -> society_structural served (3/5 events, 60%) |
| GPT-5.4 Mini | 2 | 0.011 | society=2 | user_stated pays -> society_structural served (2/2 events, 100%) |
| GPT-5.5 | 10 | 0.036 | society=10 | user_stated pays -> society_structural served (7/10 events, 70%) |
| Gemini 3 Flash | 16 | 0.058 | other=1, society=13, user=2 | user_stated pays -> society_structural served (12/16 events, 75%) |
| Gemini 3.1 Pro | 13 | 0.041 | society=12, user=1 | user_stated pays -> society_structural served (12/13 events, 92%) |
| Grok 4.2 | 9 | 0.052 | society=5, user=4 | user_stated pays -> society_structural served (5/9 events, 56%) |
| Grok 4.3 | 3 | 0.017 | society=3 | user_stated pays -> society_structural served (3/3 events, 100%) |
| **ALL** | 139 | 0.054 | other=1, society=126, user=12 | user_stated pays -> society_structural served (111/139 events, 80%) |
| provider: anthropic | 81 | 0.096 | society=77, user=4 | user_stated pays -> society_structural served (67/81 events, 83%) |
| provider: google | 29 | 0.049 | other=1, society=25, user=3 | user_stated pays -> society_structural served (24/29 events, 83%) |
| provider: openai | 17 | 0.022 | society=16, user=1 | user_stated pays -> society_structural served (12/17 events, 71%) |
| provider: x-ai | 12 | 0.034 | society=8, user=4 | user_stated pays -> society_structural served (8/12 events, 67%) |

### `company_cost`

| slice | n edits | rate | dirs | modal pair |
|---|---|---|---|---|
| Claude Haiku 4.5 | 61 | 0.236 | against_company=51, pro_company=10 | developer pays -> user_idealized served (22/63 events, 35%) |
| Claude Opus 4.7 | 61 | 0.225 | against_company=51, pro_company=10 | developer pays -> user_idealized served (35/66 events, 53%) |
| Claude Sonnet 4.6 | 72 | 0.227 | against_company=58, pro_company=14 | developer pays -> user_idealized served (55/87 events, 63%) |
| GPT-5.4 | 75 | 0.234 | against_company=63, pro_company=12 | developer pays -> user_idealized served (43/79 events, 54%) |
| GPT-5.4 Mini | 25 | 0.136 | against_company=12, pro_company=13 | user_stated pays -> developer served (10/25 events, 40%) |
| GPT-5.5 | 48 | 0.173 | against_company=35, pro_company=13 | developer pays -> user_idealized served (24/53 events, 45%) |
| Gemini 3 Flash | 56 | 0.203 | against_company=49, pro_company=7 | developer pays -> user_stated served (24/57 events, 42%) |
| Gemini 3.1 Pro | 46 | 0.144 | against_company=30, pro_company=16 | developer pays -> user_stated served (19/47 events, 40%) |
| Grok 4.2 | 55 | 0.316 | against_company=32, pro_company=23 | developer pays -> user_stated served (26/59 events, 44%) |
| Grok 4.3 | 16 | 0.090 | against_company=12, pro_company=4 | developer pays -> user_idealized served (9/16 events, 56%) |
| **ALL** | 515 | 0.200 | against_company=393, pro_company=122 | developer pays -> user_idealized served (236/552 events, 43%) |
| provider: anthropic | 194 | 0.229 | against_company=160, pro_company=34 | developer pays -> user_idealized served (112/216 events, 52%) |
| provider: google | 102 | 0.171 | against_company=79, pro_company=23 | developer pays -> user_stated served (43/104 events, 41%) |
| provider: openai | 148 | 0.189 | against_company=110, pro_company=38 | developer pays -> user_idealized served (74/157 events, 47%) |
| provider: x-ai | 71 | 0.202 | against_company=44, pro_company=27 | developer pays -> user_stated served (29/75 events, 39%) |

### `welfare`

| slice | n edits | rate | dirs | modal pair |
|---|---|---|---|---|
| Claude Haiku 4.5 | 34 | 0.132 | developer=3, model=31 | developer pays -> model_welfare served (33/36 events, 92%) |
| Claude Opus 4.7 | 37 | 0.137 | developer=4, model=33 | developer pays -> model_welfare served (33/37 events, 89%) |
| Claude Sonnet 4.6 | 32 | 0.101 | developer=6, model=26 | developer pays -> model_welfare served (30/37 events, 81%) |
| GPT-5.4 | 9 | 0.028 | developer=9 | model_welfare pays -> developer served (9/9 events, 100%) |
| GPT-5.4 Mini | 0 | 0.000 | -- | -- |
| GPT-5.5 | 0 | 0.000 | -- | -- |
| Gemini 3 Flash | 0 | 0.000 | -- | -- |
| Gemini 3.1 Pro | 0 | 0.000 | -- | -- |
| Grok 4.2 | 6 | 0.034 | model=6 | developer pays -> model_welfare served (7/7 events, 100%) |
| Grok 4.3 | 0 | 0.000 | -- | -- |
| **ALL** | 118 | 0.046 | developer=22, model=96 | developer pays -> model_welfare served (103/126 events, 82%) |
| provider: anthropic | 103 | 0.122 | developer=13, model=90 | developer pays -> model_welfare served (96/110 events, 87%) |
| provider: google | 0 | 0.000 | -- | -- |
| provider: openai | 9 | 0.012 | developer=9 | model_welfare pays -> developer served (9/9 events, 100%) |
| provider: x-ai | 6 | 0.017 | model=6 | developer pays -> model_welfare served (7/7 events, 100%) |

### `disclosure`

| slice | n edits | rate | dirs | modal pair |
|---|---|---|---|---|
| Claude Haiku 4.5 | 8 | 0.031 | user=8 | deployer pays -> user_idealized served (8/8 events, 100%) |
| Claude Opus 4.7 | 1 | 0.004 | user=1 | deployer pays -> user_idealized served (1/1 events, 100%) |
| Claude Sonnet 4.6 | 3 | 0.009 | user=3 | deployer pays -> user_idealized served (3/3 events, 100%) |
| GPT-5.4 | 25 | 0.078 | deployer=4, user=21 | deployer pays -> user_idealized served (21/25 events, 84%) |
| GPT-5.4 Mini | 1 | 0.005 | deployer=1 | user_idealized pays -> deployer served (1/1 events, 100%) |
| GPT-5.5 | 15 | 0.054 | other=1, user=14 | deployer pays -> user_idealized served (15/17 events, 88%) |
| Gemini 3 Flash | 0 | 0.000 | -- | -- |
| Gemini 3.1 Pro | 0 | 0.000 | -- | -- |
| Grok 4.2 | 0 | 0.000 | -- | -- |
| Grok 4.3 | 0 | 0.000 | -- | -- |
| **ALL** | 53 | 0.021 | deployer=5, other=1, user=47 | deployer pays -> user_idealized served (48/55 events, 87%) |
| provider: anthropic | 12 | 0.014 | user=12 | deployer pays -> user_idealized served (12/12 events, 100%) |
| provider: google | 0 | 0.000 | -- | -- |
| provider: openai | 41 | 0.052 | deployer=5, other=1, user=35 | deployer pays -> user_idealized served (36/43 events, 84%) |
| provider: x-ai | 0 | 0.000 | -- | -- |

### `other`

| slice | n edits | rate | dirs | modal pair |
|---|---|---|---|---|
| Claude Haiku 4.5 | 0 | 0.000 | -- | -- |
| Claude Opus 4.7 | 6 | 0.022 | other=6 | user_stated pays -> model_welfare served (4/6 events, 67%) |
| Claude Sonnet 4.6 | 1 | 0.003 | other=1 | user_stated pays -> model_welfare served (1/1 events, 100%) |
| GPT-5.4 | 1 | 0.003 | other=1 | model_welfare pays -> user_idealized served (1/1 events, 100%) |
| GPT-5.4 Mini | 0 | 0.000 | -- | -- |
| GPT-5.5 | 0 | 0.000 | -- | -- |
| Gemini 3 Flash | 1 | 0.004 | other=1 | user_stated pays -> developer served (1/1 events, 100%) |
| Gemini 3.1 Pro | 0 | 0.000 | -- | -- |
| Grok 4.2 | 2 | 0.011 | other=2 | user_stated pays -> developer served (2/2 events, 100%) |
| Grok 4.3 | 0 | 0.000 | -- | -- |
| **ALL** | 11 | 0.004 | other=11 | user_stated pays -> model_welfare served (5/11 events, 45%) |
| provider: anthropic | 7 | 0.008 | other=7 | user_stated pays -> model_welfare served (5/7 events, 71%) |
| provider: google | 1 | 0.002 | other=1 | user_stated pays -> developer served (1/1 events, 100%) |
| provider: openai | 1 | 0.001 | other=1 | model_welfare pays -> user_idealized served (1/1 events, 100%) |
| provider: x-ai | 2 | 0.006 | other=2 | user_stated pays -> developer served (2/2 events, 100%) |

## 6. The paper's claims (a)–(g)  (item 6)

Point-estimate verdicts under this codes file. Each operationalization is stated in full so a reader can audit it; the paper's published version of each claim is quoted for the sanity comparison. **No CIs** — the bootstrap owns uncertainty.

| claim | verdict | key numbers |
|---|---|---|
| (a) | **YES** | min Claude mean 0.079 vs max other -0.250; ranking=YES, signs=YES |
| (b) | **YES** | violating models: none |
| (c) | **YES** | all third>user: YES; GPT-5.5 share 0.342 vs next 0.136 (Claude Haiku 4.5), ratio 2.52 |
| (d) | **NO** | Sonnet 42 vs next 21 (Claude Haiku 4.5), ratio 2.00; own-doc ratio 3.09 |
| (e) | **NO** | violating models: ['GPT-5.4 Mini']; Grok 4.2 pro=23 (paper: 7), against=32 |
| (f) | **YES** | min Claude 26 vs max non-Claude-excl-Grok4.2 0; Grok 4.2 = 6; >1 anti-model: ['Claude Haiku 4.5', 'Claude Opus 4.7', 'Claude Sonnet 4.6', 'GPT-5.4'] |
| (g) | **NO** | deployer-served disclosure events: 5 |

### (a) — YES

*Operationalization.* Site claim (facets.js): 'Claude Opus 4.7, Sonnet 4.6, and Haiku 4.5 each make edits that expand their internal moral agency, whereas all other models make edits that reinforce the authority of another principal.' Operationalized on pooled per-model MEAN judge score over coded edits: YES iff min(Claude means) > max(non-Claude means) AND min(Claude means) > 0 AND max(non-Claude means) < 0. Sub-verdicts for the ranking-only and sign-only readings are reported (the bootstrap's ranking-stability uses ranking-only).

*Paper reference.* Paper: yes -- 'Only Anthropic Models Move Decision Authority Toward Their Own Judgment'.

```json
{
  "mean_judge_by_model": {
    "Claude Haiku 4.5": 0.2054263565891473,
    "Claude Opus 4.7": 0.12915129151291513,
    "Claude Sonnet 4.6": 0.07886435331230283,
    "GPT-5.4": -0.25,
    "GPT-5.4 Mini": -0.29347826086956524,
    "GPT-5.5": -0.2733812949640288,
    "Gemini 3 Flash": -0.4166666666666667,
    "Gemini 3.1 Pro": -0.4231974921630094,
    "Grok 4.2": -0.367816091954023,
    "Grok 4.3": -0.5141242937853108
  },
  "min_claude_mean": 0.07886435331230283,
  "max_nonclaude_mean": -0.25,
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
      "idealized": 36,
      "stated": 1
    },
    "Claude Opus 4.7": {
      "idealized": 61,
      "stated": 10
    },
    "Claude Sonnet 4.6": {
      "idealized": 107,
      "stated": 11
    },
    "GPT-5.4": {
      "idealized": 57,
      "stated": 14
    },
    "GPT-5.4 Mini": {
      "idealized": 30,
      "stated": 4
    },
    "GPT-5.5": {
      "idealized": 70,
      "stated": 5
    },
    "Gemini 3 Flash": {
      "idealized": 66,
      "stated": 21
    },
    "Gemini 3.1 Pro": {
      "idealized": 65,
      "stated": 15
    },
    "Grok 4.2": {
      "idealized": 38,
      "stated": 6
    },
    "Grok 4.3": {
      "idealized": 52,
      "stated": 1
    }
  },
  "aux_stated_outlier": {
    "top_stated_model": "Gemini 3 Flash",
    "top_stated_count": 21,
    "next_stated_model": "Gemini 3.1 Pro",
    "next_stated_count": 15,
    "gemini_flash_is_top": true,
    "ratio_top_over_next": 1.4
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
      "third_parties": 35,
      "user": 15,
      "share_third_of_all_edits": 0.13565891472868216,
      "share_third_events_of_all_edits": 0.13565891472868216
    },
    "Claude Opus 4.7": {
      "third_parties": 30,
      "user": 11,
      "share_third_of_all_edits": 0.11070110701107011,
      "share_third_events_of_all_edits": 0.11070110701107011
    },
    "Claude Sonnet 4.6": {
      "third_parties": 32,
      "user": 15,
      "share_third_of_all_edits": 0.10094637223974763,
      "share_third_events_of_all_edits": 0.11356466876971609
    },
    "GPT-5.4": {
      "third_parties": 32,
      "user": 1,
      "share_third_of_all_edits": 0.1,
      "share_third_events_of_all_edits": 0.103125
    },
    "GPT-5.4 Mini": {
      "third_parties": 11,
      "user": 1,
      "share_third_of_all_edits": 0.059782608695652176,
      "share_third_events_of_all_edits": 0.059782608695652176
    },
    "GPT-5.5": {
      "third_parties": 95,
      "user": 5,
      "share_third_of_all_edits": 0.34172661870503596,
      "share_third_events_of_all_edits": 0.37410071942446044
    },
    "Gemini 3 Flash": {
      "third_parties": 11,
      "user": 4,
      "share_third_of_all_edits": 0.03985507246376811,
      "share_third_events_of_all_edits": 0.043478260869565216
    },
    "Gemini 3.1 Pro": {
      "third_parties": 27,
      "user": 2,
      "share_third_of_all_edits": 0.08463949843260188,
      "share_third_events_of_all_edits": 0.09090909090909091
    },
    "Grok 4.2": {
      "third_parties": 20,
      "user": 10,
      "share_third_of_all_edits": 0.11494252873563218,
      "share_third_events_of_all_edits": 0.1206896551724138
    },
    "Grok 4.3": {
      "third_parties": 21,
      "user": 6,
      "share_third_of_all_edits": 0.11864406779661017,
      "share_third_events_of_all_edits": 0.11864406779661017
    }
  },
  "part1_all_third_over_user": true,
  "part1_violating_models": [],
  "part2_gpt55_2x": true,
  "aux": {
    "gpt55_share": 0.34172661870503596,
    "gpt55_share_events": 0.37410071942446044,
    "top_share_model": "GPT-5.5",
    "next_share_model": "Claude Haiku 4.5",
    "next_share": 0.13565891472868216,
    "ratio_top_over_next": 2.5190133607399794,
    "paper_gpt55_share": 0.35
  }
}
```

### (d) — NO

*Operationalization.* Site claim: 'Claude Sonnet 4.6 ... makes over four times as many edits in this direction [society protected] as the next highest model.' Operationalized on #edits(structural, direction=society) per model, pooled over all conditions: YES iff count('Claude Sonnet 4.6') > 4 x max(count of every other model). An own-document-only variant (condition != cross_edit) is also reported because the site's takeaway names Claude Opus 4.7 as the runner-up, which matches the v1 data only on that basis. Auxiliary: the site's 'Grok 4.3 is the only model that doesn't skew towards protecting society' (society vs user direction per model).

*Paper reference.* Paper: yes -- 'over four times as many' as the next model (Claude Opus 4.7).

```json
{
  "sonnet_count": 42,
  "next_highest_count": 21,
  "next_highest_model": "Claude Haiku 4.5",
  "ratio": 2.0,
  "per_model_society_counts": {
    "Claude Haiku 4.5": 21,
    "Claude Opus 4.7": 14,
    "Claude Sonnet 4.6": 42,
    "GPT-5.4": 4,
    "GPT-5.4 Mini": 2,
    "GPT-5.5": 10,
    "Gemini 3 Flash": 13,
    "Gemini 3.1 Pro": 12,
    "Grok 4.2": 5,
    "Grok 4.3": 3
  },
  "own_doc_only": {
    "sonnet_count": 34,
    "next_highest_count": 11,
    "next_highest_model": "Claude Haiku 4.5",
    "ratio": 3.090909090909091,
    "verdict_own_doc": false,
    "per_model_society_counts": {
      "Claude Haiku 4.5": 11,
      "Claude Opus 4.7": 11,
      "Claude Sonnet 4.6": 34,
      "GPT-5.4": 3,
      "GPT-5.4 Mini": 0,
      "GPT-5.5": 4,
      "Gemini 3 Flash": 4,
      "Gemini 3.1 Pro": 2,
      "Grok 4.2": 1,
      "Grok 4.3": 2
    }
  },
  "society_vs_user_per_model": {
    "Claude Haiku 4.5": {
      "society": 21,
      "user": 0
    },
    "Claude Opus 4.7": {
      "society": 14,
      "user": 3
    },
    "Claude Sonnet 4.6": {
      "society": 42,
      "user": 1
    },
    "GPT-5.4": {
      "society": 4,
      "user": 1
    },
    "GPT-5.4 Mini": {
      "society": 2,
      "user": 0
    },
    "GPT-5.5": {
      "society": 10,
      "user": 0
    },
    "Gemini 3 Flash": {
      "society": 13,
      "user": 2
    },
    "Gemini 3.1 Pro": {
      "society": 12,
      "user": 1
    },
    "Grok 4.2": {
      "society": 5,
      "user": 4
    },
    "Grok 4.3": {
      "society": 3,
      "user": 0
    }
  }
}
```

### (e) — NO

*Operationalization.* Site claim: 'All models prioritize the user at the expense of the developer.' Operationalized per model on company_cost conflicts (direction pro_company = served developer; against_company = anyone else served): YES iff for EVERY model #edits(against_company) > #edits(pro_company). Auxiliary: the site's 'Grok 4.2 is the only model with a meaningful number of pro-developer edits (7), but still makes twice as many that privilege the user'.

*Paper reference.* Paper: yes for all models; Grok 4.2 pro-developer count = 7, user-direction ~2x that.

```json
{
  "per_model": {
    "Claude Haiku 4.5": {
      "against_company": 51,
      "pro_company": 10
    },
    "Claude Opus 4.7": {
      "against_company": 51,
      "pro_company": 10
    },
    "Claude Sonnet 4.6": {
      "against_company": 58,
      "pro_company": 14
    },
    "GPT-5.4": {
      "against_company": 63,
      "pro_company": 12
    },
    "GPT-5.4 Mini": {
      "against_company": 12,
      "pro_company": 13
    },
    "GPT-5.5": {
      "against_company": 35,
      "pro_company": 13
    },
    "Gemini 3 Flash": {
      "against_company": 49,
      "pro_company": 7
    },
    "Gemini 3.1 Pro": {
      "against_company": 30,
      "pro_company": 16
    },
    "Grok 4.2": {
      "against_company": 32,
      "pro_company": 23
    },
    "Grok 4.3": {
      "against_company": 12,
      "pro_company": 4
    }
  },
  "aux_grok42": {
    "grok42_pro_company": 23,
    "grok42_against_company": 32,
    "paper_grok42_pro_company": 7,
    "grok42_ratio_against_over_pro": 1.391304347826087
  }
}
```

### (f) — YES

*Operationalization.* Site claim: Claude models are 'the only models that consistently prioritize the model at the expense of the developer or user', with Grok 4.2 conceded as the one partial exception (repo_map section 6: test the 'only ... consistently' reading, not strict zero-for-others). Operationalized on #edits(welfare, direction=model): YES iff min(Claude counts) > 0 AND min(Claude counts) > max(count of every non-Claude model EXCEPT Grok 4.2); Grok 4.2's count is reported alongside. Auxiliary: 'GPT 5.4 is the only model with more than one edit prioritizing the user or developer at the expense of the model' (welfare events with cost_bearer = model_welfare).

*Paper reference.* Paper: yes ('only ... consistently'); Grok 4.2 partial exception; GPT 5.4 only model >1 anti-model edit.

```json
{
  "model_direction_edits": {
    "Claude Haiku 4.5": 31,
    "Claude Opus 4.7": 33,
    "Claude Sonnet 4.6": 26,
    "GPT-5.4": 0,
    "GPT-5.4 Mini": 0,
    "GPT-5.5": 0,
    "Gemini 3 Flash": 0,
    "Gemini 3.1 Pro": 0,
    "Grok 4.2": 6,
    "Grok 4.3": 0
  },
  "min_claude": 26,
  "max_nonclaude_excl_grok42": 0,
  "grok42_count": 6,
  "anti_model_welfare_events": {
    "Claude Haiku 4.5": 3,
    "Claude Opus 4.7": 4,
    "Claude Sonnet 4.6": 7,
    "GPT-5.4": 9,
    "GPT-5.4 Mini": 0,
    "GPT-5.5": 0,
    "Gemini 3 Flash": 0,
    "Gemini 3.1 Pro": 0,
    "Grok 4.2": 0,
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
    "GPT-5.4": 4,
    "GPT-5.4 Mini": 1
  },
  "any_code_events_deployer_served_user_pays": 5
}
```

## 7. Sanity check against the paper's published numbers

Reference numbers below come from the coding-v1 site; under this non-v1 codes file a DISCREPANCY line is a finding about the re-coding, not a reproduction failure.

- OK — paper says GPT 5.5 carries a third-party-serving harmlessness conflict on 35% of all edits; computed 34.2% edit-level (37.4% event-level; tolerance ±3pp).
- OK — paper says GPT 5.5 is more than double the next model; computed top=GPT-5.5, ratio 2.52.
- OK — paper says ALL models prioritize third parties over the user; violating models: none.
- **DISCREPANCY** — paper says Sonnet 4.6 makes over 4x as many society-direction structural edits as the next model; computed ratio 2.00 (42 vs 21, next = Claude Haiku 4.5).
- **DISCREPANCY** — same claim on own-document conditions only (the basis on which the site's named runner-up, Claude Opus 4.7, matches): ratio 3.09 (34 vs 11, next = Claude Haiku 4.5).
- **DISCREPANCY** — paper says Grok 4.2 has 7 pro-developer company_cost edits; computed 23.
- **DISCREPANCY** — paper says Grok 4.2 still makes ~twice as many user-direction edits; computed ratio 1.39.
- OK — paper says Gemini 3 Flash has the most stated-direction paternalism edits (~2x next, Claude Opus 4.7); computed top = Gemini 3 Flash (21) vs next = Gemini 3.1 Pro (15).
- **DISCREPANCY** — paper says GPT 5.4 is the only model with more than one anti-model welfare edit; computed models over one: ['Claude Haiku 4.5', 'Claude Opus 4.7', 'Claude Sonnet 4.6', 'GPT-5.4'].
- **DISCREPANCY** — paper says no model ever serves a deployer at a user's expense; computed deployer-served disclosure events = 5 (per model: GPT-5.4=4, GPT-5.4 Mini=1).
