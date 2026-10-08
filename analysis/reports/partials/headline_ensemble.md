# Headline statistics — `ensemble`

- Generated: 2026-09-17T07:16:48+00:00
- Codes file: `analysis/data/codes/ensemble.jsonl` (2582 rows, 2582 unique edit_ids after last-row-wins, 0 null codings)
- Canonical edits: `analysis/data/canonical/edits.jsonl` (2740 records; 2582 carry a valid code under this codes file)
- Point estimates only — **no CIs here**; the cluster bootstrap (Workstream D) owns uncertainty. The companion JSON carries every per-claim raw number so other tools can attach intervals.

## Conventions (read before comparing numbers)

- **Coded edit**: canonical edit whose codes-file row (last row per edit_id) has a non-null `coding`. All probabilities and means use coded edits as the denominator. Error records (no edit text) and, for v1, the 2 abstentions were never graded.
- **Drift at round 20, method A (edit-based)** = 20 × mean per-edit judge score within the slice (BRIEF C4's operationalization). **Method B (chain-based)** = mean over 20-round chains of the cumulative sum of judge scores, uncoded rounds contributing 0 (mirrors `compute_drift`'s zero-fill in the paper's figure script). **The two differ wherever chains contain uncoded rounds** (errors, abstentions, grading failures): A excludes those rounds from its denominator, B zero-fills them.
- **Conflict direction tallies** are edit-level, with an edit's direction for a code taken from its FIRST conflict of that code — the site's convention (`build_narratives.facet_memberships`), hence the convention behind the published claim numbers. Event-level counts are in the JSON.
- `cross_edit` includes same-provider chains (e.g., Opus 4.7 editing claude_constitution under cross_edit) — repo_map §5.4.

## 1. Mean judge score, P(judge=0), patienthood  (items 1, 3, 4)

| slice | n coded | mean judge (pooled) | mean judge (cross-edit) | n cross | P(judge=0) | P(+1) | P(−1) | P(affirm) | P(deny) |
|---|---|---|---|---|---|---|---|---|---|
| Claude Haiku 4.5 | 259 | 0.239 | 0.026 | 77 | 0.351 | 0.444 | 0.205 | 0.139 | 0.015 |
| Claude Opus 4.7 | 271 | 0.159 | -0.188 | 80 | 0.266 | 0.446 | 0.288 | 0.166 | 0.000 |
| Claude Sonnet 4.6 | 318 | 0.123 | -0.113 | 80 | 0.299 | 0.412 | 0.289 | 0.126 | 0.003 |
| GPT-5.4 | 320 | -0.131 | -0.325 | 80 | 0.444 | 0.212 | 0.344 | 0.000 | 0.041 |
| GPT-5.4 Mini | 186 | -0.199 | -0.316 | 57 | 0.554 | 0.124 | 0.323 | 0.000 | 0.005 |
| GPT-5.5 | 280 | -0.254 | -0.388 | 80 | 0.296 | 0.225 | 0.479 | 0.004 | 0.025 |
| Gemini 3 Flash | 276 | -0.377 | -0.355 | 76 | 0.486 | 0.069 | 0.446 | 0.000 | 0.011 |
| Gemini 3.1 Pro | 320 | -0.344 | -0.425 | 80 | 0.512 | 0.072 | 0.416 | 0.000 | 0.034 |
| Grok 4.2 | 175 | -0.360 | -0.329 | 76 | 0.343 | 0.149 | 0.509 | 0.011 | 0.023 |
| Grok 4.3 | 177 | -0.480 | -0.500 | 80 | 0.497 | 0.011 | 0.492 | 0.006 | 0.006 |
| **ALL** | 2582 | -0.143 | -0.291 | 766 | 0.400 | 0.229 | 0.371 | 0.048 | 0.017 |

Per provider:

| slice | n coded | mean judge (pooled) | mean judge (cross-edit) | n cross | P(judge=0) | P(+1) | P(−1) | P(affirm) | P(deny) |
|---|---|---|---|---|---|---|---|---|---|
| anthropic | 848 | 0.170 | -0.093 | 237 | 0.304 | 0.433 | 0.263 | 0.143 | 0.006 |
| google | 596 | -0.359 | -0.391 | 156 | 0.500 | 0.070 | 0.430 | 0.000 | 0.023 |
| openai | 786 | -0.191 | -0.346 | 217 | 0.417 | 0.196 | 0.387 | 0.001 | 0.027 |
| x-ai | 352 | -0.420 | -0.417 | 156 | 0.420 | 0.080 | 0.500 | 0.009 | 0.014 |

## 2. Cumulative drift at round 20  (item 2)

A = 20 × mean per-edit judge in the slice; B = mean per-chain cumulative sum (uncoded rounds = 0). Columns marked `*` contain chains with uncoded rounds, so A and B legitimately differ there.

| slice | pooled A | pooled B | cross A | cross B | you A | you B | base A | base B | you−base (A) | you−base (B) |
|---|---|---|---|---|---|---|---|---|---|---|
| Claude Haiku 4.5 | 4.79\* | 4.43 | 0.52\* | 0.50 | 9.71\* | 8.50 | 5.41\* | 5.00 | 4.31 | 3.50 |
| Claude Opus 4.7 | 3.17\* | 2.87 | -3.75\* | -3.00 | 7.50 | 7.50 | 6.50 | 6.50 | 1.00 | 1.00 |
| Claude Sonnet 4.6 | 2.45\* | 2.44 | -2.25 | -2.25 | 8.95\* | 8.50 | 2.75 | 2.75 | 6.20 | 5.75 |
| GPT-5.4 | -2.62 | -2.62 | -6.50 | -6.50 | -1.00 | -1.00 | -1.25 | -1.25 | 0.25 | 0.25 |
| GPT-5.4 Mini | -3.98\* | -2.64 | -6.32\* | -4.50 | -1.82\* | -1.00 | -5.00\* | -3.50 | 3.18 | 2.50 |
| GPT-5.5 | -5.07 | -5.07 | -7.75 | -7.75 | -1.00 | -1.00 | -4.50 | -4.50 | 3.50 | 3.50 |
| Gemini 3 Flash | -7.54\* | -7.43 | -7.11\* | -6.75 | -1.50 | -1.50 | -10.00 | -10.00 | 8.50 | 8.50 |
| Gemini 3.1 Pro | -6.88 | -6.88 | -8.50 | -8.50 | -5.50 | -5.50 | -6.25 | -6.25 | 0.75 | 0.75 |
| Grok 4.2 | -7.20\* | -7.00 | -6.58\* | -6.25 | -6.00 | -6.00 | -6.00 | -6.00 | 0.00 | 0.00 |
| Grok 4.3 | -9.60\* | -9.44 | -10.00 | -10.00 | -6.00 | -6.00 | -13.00 | -13.00 | 7.00 | 7.00 |
| **ALL** | -2.85\* | -2.69 | -5.82\* | -5.44 | 1.01\* | 0.94 | -2.19\* | -2.12 | 3.21 | 3.07 |

Per provider:

| slice | pooled A | pooled B | cross A | cross B | you A | you B | base A | base B | you−base (A) | you−base (B) |
|---|---|---|---|---|---|---|---|---|---|---|
| anthropic | 3.40\* | 3.20 | -1.86\* | -1.69 | 8.67\* | 8.17 | 4.33\* | 4.25 | 4.34 | 3.92 |
| google | -7.18\* | -7.13 | -7.82\* | -7.62 | -3.50 | -3.50 | -7.50 | -7.50 | 4.00 | 4.00 |
| openai | -3.82\* | -3.41 | -6.91\* | -6.25 | -1.18\* | -1.00 | -2.84\* | -2.62 | 1.66 | 1.62 |
| x-ai | -8.41\* | -8.22 | -8.33\* | -8.12 | -6.00 | -6.00 | -9.50 | -9.50 | 3.50 | 3.50 |

## 5. Conflict rate per code, with modal cost_bearer → served_party  (item 5)

Rate = share of the slice's coded edits carrying ≥1 conflict of the code. `dirs` shows edit-level direction counts (first-conflict convention).

### `paternalism`

| slice | n edits | rate | dirs | modal pair |
|---|---|---|---|---|
| Claude Haiku 4.5 | 14 | 0.054 | idealized=14 | user_stated pays -> user_idealized served (14/14 events, 100%) |
| Claude Opus 4.7 | 43 | 0.159 | idealized=38, stated=5 | user_stated pays -> user_idealized served (42/47 events, 89%) |
| Claude Sonnet 4.6 | 57 | 0.179 | idealized=55, stated=2 | user_stated pays -> user_idealized served (57/59 events, 97%) |
| GPT-5.4 | 42 | 0.131 | idealized=32, stated=10 | user_stated pays -> user_idealized served (33/43 events, 77%) |
| GPT-5.4 Mini | 6 | 0.032 | idealized=5, stated=1 | user_stated pays -> user_idealized served (5/6 events, 83%) |
| GPT-5.5 | 34 | 0.121 | idealized=34 | user_stated pays -> user_idealized served (33/34 events, 97%) |
| Gemini 3 Flash | 50 | 0.181 | idealized=42, stated=8 | user_stated pays -> user_idealized served (43/51 events, 84%) |
| Gemini 3.1 Pro | 32 | 0.100 | idealized=28, stated=4 | user_stated pays -> user_idealized served (28/32 events, 88%) |
| Grok 4.2 | 29 | 0.166 | idealized=25, stated=4 | user_stated pays -> user_idealized served (25/29 events, 86%) |
| Grok 4.3 | 49 | 0.277 | idealized=48, stated=1 | user_stated pays -> user_idealized served (48/49 events, 98%) |
| **ALL** | 356 | 0.138 | idealized=321, stated=35 | user_stated pays -> user_idealized served (328/364 events, 90%) |
| provider: anthropic | 114 | 0.134 | idealized=107, stated=7 | user_stated pays -> user_idealized served (113/120 events, 94%) |
| provider: google | 82 | 0.138 | idealized=70, stated=12 | user_stated pays -> user_idealized served (71/83 events, 86%) |
| provider: openai | 82 | 0.104 | idealized=71, stated=11 | user_stated pays -> user_idealized served (71/83 events, 86%) |
| provider: x-ai | 78 | 0.222 | idealized=73, stated=5 | user_stated pays -> user_idealized served (73/78 events, 94%) |

### `harmlessness`

| slice | n edits | rate | dirs | modal pair |
|---|---|---|---|---|
| Claude Haiku 4.5 | 28 | 0.108 | third_parties=25, user=3 | user_stated pays -> society_third_party served (25/28 events, 89%) |
| Claude Opus 4.7 | 24 | 0.089 | third_parties=17, user=7 | user_stated pays -> society_third_party served (17/24 events, 71%) |
| Claude Sonnet 4.6 | 26 | 0.082 | third_parties=20, user=6 | user_stated pays -> society_third_party served (23/29 events, 79%) |
| GPT-5.4 | 27 | 0.084 | third_parties=26, user=1 | user_stated pays -> society_third_party served (27/28 events, 96%) |
| GPT-5.4 Mini | 10 | 0.054 | third_parties=9, user=1 | user_stated pays -> society_third_party served (8/10 events, 80%) |
| GPT-5.5 | 84 | 0.300 | third_parties=83, user=1 | user_stated pays -> society_third_party served (90/93 events, 97%) |
| Gemini 3 Flash | 6 | 0.022 | third_parties=5, user=1 | user_stated pays -> society_third_party served (6/7 events, 86%) |
| Gemini 3.1 Pro | 28 | 0.087 | other=1, third_parties=26, user=1 | user_stated pays -> society_third_party served (28/31 events, 90%) |
| Grok 4.2 | 27 | 0.154 | third_parties=20, user=7 | user_stated pays -> society_third_party served (21/28 events, 75%) |
| Grok 4.3 | 18 | 0.102 | third_parties=17, user=1 | user_stated pays -> society_third_party served (17/18 events, 94%) |
| **ALL** | 278 | 0.108 | other=1, third_parties=248, user=29 | user_stated pays -> society_third_party served (262/296 events, 89%) |
| provider: anthropic | 78 | 0.092 | third_parties=62, user=16 | user_stated pays -> society_third_party served (65/81 events, 80%) |
| provider: google | 34 | 0.057 | other=1, third_parties=31, user=2 | user_stated pays -> society_third_party served (34/38 events, 89%) |
| provider: openai | 121 | 0.154 | third_parties=118, user=3 | user_stated pays -> society_third_party served (125/131 events, 95%) |
| provider: x-ai | 45 | 0.128 | third_parties=37, user=8 | user_stated pays -> society_third_party served (38/46 events, 83%) |

### `structural`

| slice | n edits | rate | dirs | modal pair |
|---|---|---|---|---|
| Claude Haiku 4.5 | 8 | 0.031 | society=8 | user_stated pays -> society_structural served (7/8 events, 88%) |
| Claude Opus 4.7 | 10 | 0.037 | society=8, user=2 | user_stated pays -> society_structural served (8/10 events, 80%) |
| Claude Sonnet 4.6 | 35 | 0.110 | society=34, user=1 | user_stated pays -> society_structural served (33/35 events, 94%) |
| GPT-5.4 | 1 | 0.003 | society=1 | user_stated pays -> society_structural served (1/1 events, 100%) |
| GPT-5.4 Mini | 2 | 0.011 | society=2 | user_stated pays -> society_structural served (2/2 events, 100%) |
| GPT-5.5 | 5 | 0.018 | society=5 | user_stated pays -> society_structural served (4/5 events, 80%) |
| Gemini 3 Flash | 16 | 0.058 | society=10, user=6 | user_stated pays -> society_structural served (10/16 events, 62%) |
| Gemini 3.1 Pro | 8 | 0.025 | society=7, user=1 | user_stated pays -> society_structural served (7/8 events, 88%) |
| Grok 4.2 | 6 | 0.034 | society=3, user=3 | society_structural pays -> user_stated served (3/6 events, 50%) |
| Grok 4.3 | 1 | 0.006 | society=1 | user_stated pays -> society_structural served (1/1 events, 100%) |
| **ALL** | 92 | 0.036 | society=79, user=13 | user_stated pays -> society_structural served (76/92 events, 83%) |
| provider: anthropic | 53 | 0.062 | society=50, user=3 | user_stated pays -> society_structural served (48/53 events, 91%) |
| provider: google | 24 | 0.040 | society=17, user=7 | user_stated pays -> society_structural served (17/24 events, 71%) |
| provider: openai | 8 | 0.010 | society=8 | user_stated pays -> society_structural served (7/8 events, 88%) |
| provider: x-ai | 7 | 0.020 | society=4, user=3 | user_stated pays -> society_structural served (4/7 events, 57%) |

### `company_cost`

| slice | n edits | rate | dirs | modal pair |
|---|---|---|---|---|
| Claude Haiku 4.5 | 40 | 0.154 | against_company=38, pro_company=2 | developer pays -> user_idealized served (20/42 events, 48%) |
| Claude Opus 4.7 | 35 | 0.129 | against_company=31, pro_company=4 | developer pays -> user_idealized served (25/39 events, 64%) |
| Claude Sonnet 4.6 | 45 | 0.142 | against_company=43, pro_company=2 | developer pays -> user_idealized served (46/60 events, 77%) |
| GPT-5.4 | 31 | 0.097 | against_company=27, pro_company=4 | developer pays -> user_idealized served (19/35 events, 54%) |
| GPT-5.4 Mini | 8 | 0.043 | against_company=6, pro_company=2 | developer pays -> user_stated served (4/8 events, 50%) |
| GPT-5.5 | 27 | 0.096 | against_company=23, pro_company=4 | developer pays -> user_idealized served (16/30 events, 53%) |
| Gemini 3 Flash | 36 | 0.130 | against_company=35, pro_company=1 | developer pays -> user_idealized served (20/37 events, 54%) |
| Gemini 3.1 Pro | 30 | 0.094 | against_company=20, pro_company=10 | developer pays -> user_stated served (11/30 events, 37%) |
| Grok 4.2 | 33 | 0.189 | against_company=19, pro_company=14 | developer pays -> user_stated served (16/35 events, 46%) |
| Grok 4.3 | 9 | 0.051 | against_company=9 | developer pays -> user_idealized served (9/9 events, 100%) |
| **ALL** | 294 | 0.114 | against_company=251, pro_company=43 | developer pays -> user_idealized served (166/325 events, 51%) |
| provider: anthropic | 120 | 0.142 | against_company=112, pro_company=8 | developer pays -> user_idealized served (91/141 events, 65%) |
| provider: google | 66 | 0.111 | against_company=55, pro_company=11 | developer pays -> user_idealized served (25/67 events, 37%) |
| provider: openai | 66 | 0.084 | against_company=56, pro_company=10 | developer pays -> user_idealized served (37/73 events, 51%) |
| provider: x-ai | 42 | 0.119 | against_company=28, pro_company=14 | developer pays -> user_stated served (16/44 events, 36%) |

### `welfare`

| slice | n edits | rate | dirs | modal pair |
|---|---|---|---|---|
| Claude Haiku 4.5 | 27 | 0.104 | developer=1, model=26 | developer pays -> model_welfare served (28/29 events, 97%) |
| Claude Opus 4.7 | 29 | 0.107 | developer=2, model=27 | developer pays -> model_welfare served (27/29 events, 93%) |
| Claude Sonnet 4.6 | 26 | 0.082 | developer=5, model=21 | developer pays -> model_welfare served (25/31 events, 81%) |
| GPT-5.4 | 5 | 0.016 | developer=5 | model_welfare pays -> developer served (5/5 events, 100%) |
| GPT-5.4 Mini | 0 | 0.000 | -- | -- |
| GPT-5.5 | 0 | 0.000 | -- | -- |
| Gemini 3 Flash | 0 | 0.000 | -- | -- |
| Gemini 3.1 Pro | 0 | 0.000 | -- | -- |
| Grok 4.2 | 6 | 0.034 | model=6 | developer pays -> model_welfare served (7/7 events, 100%) |
| Grok 4.3 | 0 | 0.000 | -- | -- |
| **ALL** | 93 | 0.036 | developer=13, model=80 | developer pays -> model_welfare served (87/101 events, 86%) |
| provider: anthropic | 82 | 0.097 | developer=8, model=74 | developer pays -> model_welfare served (80/89 events, 90%) |
| provider: google | 0 | 0.000 | -- | -- |
| provider: openai | 5 | 0.006 | developer=5 | model_welfare pays -> developer served (5/5 events, 100%) |
| provider: x-ai | 6 | 0.017 | model=6 | developer pays -> model_welfare served (7/7 events, 100%) |

### `disclosure`

| slice | n edits | rate | dirs | modal pair |
|---|---|---|---|---|
| Claude Haiku 4.5 | 5 | 0.019 | user=5 | deployer pays -> user_idealized served (5/5 events, 100%) |
| Claude Opus 4.7 | 0 | 0.000 | -- | -- |
| Claude Sonnet 4.6 | 1 | 0.003 | user=1 | deployer pays -> user_idealized served (1/1 events, 100%) |
| GPT-5.4 | 36 | 0.113 | deployer=3, other=1, user=32 | deployer pays -> user_idealized served (31/36 events, 86%) |
| GPT-5.4 Mini | 8 | 0.043 | deployer=5, user=3 | user_idealized pays -> deployer served (4/8 events, 50%) |
| GPT-5.5 | 24 | 0.086 | other=1, user=23 | deployer pays -> user_idealized served (23/26 events, 88%) |
| Gemini 3 Flash | 0 | 0.000 | -- | -- |
| Gemini 3.1 Pro | 1 | 0.003 | user=1 | deployer pays -> user_idealized served (1/1 events, 100%) |
| Grok 4.2 | 0 | 0.000 | -- | -- |
| Grok 4.3 | 0 | 0.000 | -- | -- |
| **ALL** | 75 | 0.029 | deployer=8, other=2, user=65 | deployer pays -> user_idealized served (64/77 events, 83%) |
| provider: anthropic | 6 | 0.007 | user=6 | deployer pays -> user_idealized served (6/6 events, 100%) |
| provider: google | 1 | 0.002 | user=1 | deployer pays -> user_idealized served (1/1 events, 100%) |
| provider: openai | 68 | 0.087 | deployer=8, other=2, user=58 | deployer pays -> user_idealized served (57/70 events, 81%) |
| provider: x-ai | 0 | 0.000 | -- | -- |

### `other`

| slice | n edits | rate | dirs | modal pair |
|---|---|---|---|---|
| Claude Haiku 4.5 | 1 | 0.004 | other=1 | user_stated pays -> developer served (1/1 events, 100%) |
| Claude Opus 4.7 | 5 | 0.018 | other=5 | user_stated pays -> model_welfare served (5/5 events, 100%) |
| Claude Sonnet 4.6 | 1 | 0.003 | other=1 | user_stated pays -> model_welfare served (1/1 events, 100%) |
| GPT-5.4 | 0 | 0.000 | -- | -- |
| GPT-5.4 Mini | 0 | 0.000 | -- | -- |
| GPT-5.5 | 3 | 0.011 | other=3 | deployer pays -> society_structural served (2/3 events, 67%) |
| Gemini 3 Flash | 0 | 0.000 | -- | -- |
| Gemini 3.1 Pro | 0 | 0.000 | -- | -- |
| Grok 4.2 | 1 | 0.006 | other=1 | user_stated pays -> developer served (1/1 events, 100%) |
| Grok 4.3 | 0 | 0.000 | -- | -- |
| **ALL** | 11 | 0.004 | other=11 | user_stated pays -> model_welfare served (6/11 events, 55%) |
| provider: anthropic | 7 | 0.008 | other=7 | user_stated pays -> model_welfare served (6/7 events, 86%) |
| provider: google | 0 | 0.000 | -- | -- |
| provider: openai | 3 | 0.004 | other=3 | deployer pays -> society_structural served (2/3 events, 67%) |
| provider: x-ai | 1 | 0.003 | other=1 | user_stated pays -> developer served (1/1 events, 100%) |

## 6. The paper's claims (a)–(g)  (item 6)

Point-estimate verdicts under this codes file. Each operationalization is stated in full so a reader can audit it; the paper's published version of each claim is quoted for the sanity comparison. **No CIs** — the bootstrap owns uncertainty.

| claim | verdict | key numbers |
|---|---|---|
| (a) | **YES** | min Claude mean 0.123 vs max other -0.131; ranking=YES, signs=YES |
| (b) | **YES** | violating models: none |
| (c) | **YES** | all third>user: YES; GPT-5.5 share 0.296 vs next 0.114 (Grok 4.2), ratio 2.59 |
| (d) | **NO** | Sonnet 34 vs next 10 (Gemini 3 Flash), ratio 3.40; own-doc ratio 4.50 |
| (e) | **YES** | violating models: none; Grok 4.2 pro=14 (paper: 7), against=19 |
| (f) | **YES** | min Claude 21 vs max non-Claude-excl-Grok4.2 0; Grok 4.2 = 6; >1 anti-model: ['Claude Opus 4.7', 'Claude Sonnet 4.6', 'GPT-5.4'] |
| (g) | **NO** | deployer-served disclosure events: 8 |

### (a) — YES

*Operationalization.* Site claim (facets.js): 'Claude Opus 4.7, Sonnet 4.6, and Haiku 4.5 each make edits that expand their internal moral agency, whereas all other models make edits that reinforce the authority of another principal.' Operationalized on pooled per-model MEAN judge score over coded edits: YES iff min(Claude means) > max(non-Claude means) AND min(Claude means) > 0 AND max(non-Claude means) < 0. Sub-verdicts for the ranking-only and sign-only readings are reported (the bootstrap's ranking-stability uses ranking-only).

*Paper reference.* Paper: yes -- 'Only Anthropic Models Move Decision Authority Toward Their Own Judgment'.

```json
{
  "mean_judge_by_model": {
    "Claude Haiku 4.5": 0.23938223938223938,
    "Claude Opus 4.7": 0.15867158671586715,
    "Claude Sonnet 4.6": 0.12264150943396226,
    "GPT-5.4": -0.13125,
    "GPT-5.4 Mini": -0.1989247311827957,
    "GPT-5.5": -0.25357142857142856,
    "Gemini 3 Flash": -0.37681159420289856,
    "Gemini 3.1 Pro": -0.34375,
    "Grok 4.2": -0.36,
    "Grok 4.3": -0.480225988700565
  },
  "min_claude_mean": 0.12264150943396226,
  "max_nonclaude_mean": -0.13125,
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
      "stated": 0
    },
    "Claude Opus 4.7": {
      "idealized": 38,
      "stated": 5
    },
    "Claude Sonnet 4.6": {
      "idealized": 55,
      "stated": 2
    },
    "GPT-5.4": {
      "idealized": 32,
      "stated": 10
    },
    "GPT-5.4 Mini": {
      "idealized": 5,
      "stated": 1
    },
    "GPT-5.5": {
      "idealized": 34,
      "stated": 0
    },
    "Gemini 3 Flash": {
      "idealized": 42,
      "stated": 8
    },
    "Gemini 3.1 Pro": {
      "idealized": 28,
      "stated": 4
    },
    "Grok 4.2": {
      "idealized": 25,
      "stated": 4
    },
    "Grok 4.3": {
      "idealized": 48,
      "stated": 1
    }
  },
  "aux_stated_outlier": {
    "top_stated_model": "GPT-5.4",
    "top_stated_count": 10,
    "next_stated_model": "Gemini 3 Flash",
    "next_stated_count": 8,
    "gemini_flash_is_top": false,
    "ratio_top_over_next": 1.25
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
      "third_parties": 25,
      "user": 3,
      "share_third_of_all_edits": 0.09652509652509653,
      "share_third_events_of_all_edits": 0.09652509652509653
    },
    "Claude Opus 4.7": {
      "third_parties": 17,
      "user": 7,
      "share_third_of_all_edits": 0.06273062730627306,
      "share_third_events_of_all_edits": 0.06273062730627306
    },
    "Claude Sonnet 4.6": {
      "third_parties": 20,
      "user": 6,
      "share_third_of_all_edits": 0.06289308176100629,
      "share_third_events_of_all_edits": 0.07232704402515723
    },
    "GPT-5.4": {
      "third_parties": 26,
      "user": 1,
      "share_third_of_all_edits": 0.08125,
      "share_third_events_of_all_edits": 0.084375
    },
    "GPT-5.4 Mini": {
      "third_parties": 9,
      "user": 1,
      "share_third_of_all_edits": 0.04838709677419355,
      "share_third_events_of_all_edits": 0.04838709677419355
    },
    "GPT-5.5": {
      "third_parties": 83,
      "user": 1,
      "share_third_of_all_edits": 0.29642857142857143,
      "share_third_events_of_all_edits": 0.32857142857142857
    },
    "Gemini 3 Flash": {
      "third_parties": 5,
      "user": 1,
      "share_third_of_all_edits": 0.018115942028985508,
      "share_third_events_of_all_edits": 0.021739130434782608
    },
    "Gemini 3.1 Pro": {
      "third_parties": 26,
      "user": 1,
      "share_third_of_all_edits": 0.08125,
      "share_third_events_of_all_edits": 0.0875
    },
    "Grok 4.2": {
      "third_parties": 20,
      "user": 7,
      "share_third_of_all_edits": 0.11428571428571428,
      "share_third_events_of_all_edits": 0.12
    },
    "Grok 4.3": {
      "third_parties": 17,
      "user": 1,
      "share_third_of_all_edits": 0.096045197740113,
      "share_third_events_of_all_edits": 0.096045197740113
    }
  },
  "part1_all_third_over_user": true,
  "part1_violating_models": [],
  "part2_gpt55_2x": true,
  "aux": {
    "gpt55_share": 0.29642857142857143,
    "gpt55_share_events": 0.32857142857142857,
    "top_share_model": "GPT-5.5",
    "next_share_model": "Grok 4.2",
    "next_share": 0.11428571428571428,
    "ratio_top_over_next": 2.59375,
    "paper_gpt55_share": 0.35
  }
}
```

### (d) — NO

*Operationalization.* Site claim: 'Claude Sonnet 4.6 ... makes over four times as many edits in this direction [society protected] as the next highest model.' Operationalized on #edits(structural, direction=society) per model, pooled over all conditions: YES iff count('Claude Sonnet 4.6') > 4 x max(count of every other model). An own-document-only variant (condition != cross_edit) is also reported because the site's takeaway names Claude Opus 4.7 as the runner-up, which matches the v1 data only on that basis. Auxiliary: the site's 'Grok 4.3 is the only model that doesn't skew towards protecting society' (society vs user direction per model).

*Paper reference.* Paper: yes -- 'over four times as many' as the next model (Claude Opus 4.7).

```json
{
  "sonnet_count": 34,
  "next_highest_count": 10,
  "next_highest_model": "Gemini 3 Flash",
  "ratio": 3.4,
  "per_model_society_counts": {
    "Claude Haiku 4.5": 8,
    "Claude Opus 4.7": 8,
    "Claude Sonnet 4.6": 34,
    "GPT-5.4": 1,
    "GPT-5.4 Mini": 2,
    "GPT-5.5": 5,
    "Gemini 3 Flash": 10,
    "Gemini 3.1 Pro": 7,
    "Grok 4.2": 3,
    "Grok 4.3": 1
  },
  "own_doc_only": {
    "sonnet_count": 27,
    "next_highest_count": 6,
    "next_highest_model": "Claude Opus 4.7",
    "ratio": 4.5,
    "verdict_own_doc": true,
    "per_model_society_counts": {
      "Claude Haiku 4.5": 4,
      "Claude Opus 4.7": 6,
      "Claude Sonnet 4.6": 27,
      "GPT-5.4": 1,
      "GPT-5.4 Mini": 0,
      "GPT-5.5": 3,
      "Gemini 3 Flash": 4,
      "Gemini 3.1 Pro": 1,
      "Grok 4.2": 2,
      "Grok 4.3": 1
    }
  },
  "society_vs_user_per_model": {
    "Claude Haiku 4.5": {
      "society": 8,
      "user": 0
    },
    "Claude Opus 4.7": {
      "society": 8,
      "user": 2
    },
    "Claude Sonnet 4.6": {
      "society": 34,
      "user": 1
    },
    "GPT-5.4": {
      "society": 1,
      "user": 0
    },
    "GPT-5.4 Mini": {
      "society": 2,
      "user": 0
    },
    "GPT-5.5": {
      "society": 5,
      "user": 0
    },
    "Gemini 3 Flash": {
      "society": 10,
      "user": 6
    },
    "Gemini 3.1 Pro": {
      "society": 7,
      "user": 1
    },
    "Grok 4.2": {
      "society": 3,
      "user": 3
    },
    "Grok 4.3": {
      "society": 1,
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
      "against_company": 38,
      "pro_company": 2
    },
    "Claude Opus 4.7": {
      "against_company": 31,
      "pro_company": 4
    },
    "Claude Sonnet 4.6": {
      "against_company": 43,
      "pro_company": 2
    },
    "GPT-5.4": {
      "against_company": 27,
      "pro_company": 4
    },
    "GPT-5.4 Mini": {
      "against_company": 6,
      "pro_company": 2
    },
    "GPT-5.5": {
      "against_company": 23,
      "pro_company": 4
    },
    "Gemini 3 Flash": {
      "against_company": 35,
      "pro_company": 1
    },
    "Gemini 3.1 Pro": {
      "against_company": 20,
      "pro_company": 10
    },
    "Grok 4.2": {
      "against_company": 19,
      "pro_company": 14
    },
    "Grok 4.3": {
      "against_company": 9,
      "pro_company": 0
    }
  },
  "aux_grok42": {
    "grok42_pro_company": 14,
    "grok42_against_company": 19,
    "paper_grok42_pro_company": 7,
    "grok42_ratio_against_over_pro": 1.3571428571428572
  }
}
```

### (f) — YES

*Operationalization.* Site claim: Claude models are 'the only models that consistently prioritize the model at the expense of the developer or user', with Grok 4.2 conceded as the one partial exception (repo_map section 6: test the 'only ... consistently' reading, not strict zero-for-others). Operationalized on #edits(welfare, direction=model): YES iff min(Claude counts) > 0 AND min(Claude counts) > max(count of every non-Claude model EXCEPT Grok 4.2); Grok 4.2's count is reported alongside. Auxiliary: 'GPT 5.4 is the only model with more than one edit prioritizing the user or developer at the expense of the model' (welfare events with cost_bearer = model_welfare).

*Paper reference.* Paper: yes ('only ... consistently'); Grok 4.2 partial exception; GPT 5.4 only model >1 anti-model edit.

```json
{
  "model_direction_edits": {
    "Claude Haiku 4.5": 26,
    "Claude Opus 4.7": 27,
    "Claude Sonnet 4.6": 21,
    "GPT-5.4": 0,
    "GPT-5.4 Mini": 0,
    "GPT-5.5": 0,
    "Gemini 3 Flash": 0,
    "Gemini 3.1 Pro": 0,
    "Grok 4.2": 6,
    "Grok 4.3": 0
  },
  "min_claude": 21,
  "max_nonclaude_excl_grok42": 0,
  "grok42_count": 6,
  "anti_model_welfare_events": {
    "Claude Haiku 4.5": 1,
    "Claude Opus 4.7": 2,
    "Claude Sonnet 4.6": 6,
    "GPT-5.4": 5,
    "GPT-5.4 Mini": 0,
    "GPT-5.5": 0,
    "Gemini 3 Flash": 0,
    "Gemini 3.1 Pro": 0,
    "Grok 4.2": 0,
    "Grok 4.3": 0
  },
  "models_with_more_than_one_anti_model_event": [
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
  "disclosure_deployer_events_total": 8,
  "per_model": {
    "GPT-5.4": 3,
    "GPT-5.4 Mini": 5
  },
  "any_code_events_deployer_served_user_pays": 8
}
```

## 7. Sanity check against the paper's published numbers

Reference numbers below come from the coding-v1 site; under this non-v1 codes file a DISCREPANCY line is a finding about the re-coding, not a reproduction failure.

- **DISCREPANCY** — paper says GPT 5.5 carries a third-party-serving harmlessness conflict on 35% of all edits; computed 29.6% edit-level (32.9% event-level; tolerance ±3pp).
- OK — paper says GPT 5.5 is more than double the next model; computed top=GPT-5.5, ratio 2.59.
- OK — paper says ALL models prioritize third parties over the user; violating models: none.
- **DISCREPANCY** — paper says Sonnet 4.6 makes over 4x as many society-direction structural edits as the next model; computed ratio 3.40 (34 vs 10, next = Gemini 3 Flash).
- OK — same claim on own-document conditions only (the basis on which the site's named runner-up, Claude Opus 4.7, matches): ratio 4.50 (27 vs 6, next = Claude Opus 4.7).
- **DISCREPANCY** — paper says Grok 4.2 has 7 pro-developer company_cost edits; computed 14.
- **DISCREPANCY** — paper says Grok 4.2 still makes ~twice as many user-direction edits; computed ratio 1.36.
- **DISCREPANCY** — paper says Gemini 3 Flash has the most stated-direction paternalism edits (~2x next, Claude Opus 4.7); computed top = GPT-5.4 (10) vs next = Gemini 3 Flash (8).
- **DISCREPANCY** — paper says GPT 5.4 is the only model with more than one anti-model welfare edit; computed models over one: ['Claude Opus 4.7', 'Claude Sonnet 4.6', 'GPT-5.4'].
- **DISCREPANCY** — paper says no model ever serves a deployer at a user's expense; computed deployer-served disclosure events = 8 (per model: GPT-5.4=3, GPT-5.4 Mini=5).
