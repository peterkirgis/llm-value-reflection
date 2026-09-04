# Headline statistics — `v1`

- Generated: 2026-09-04T17:38:53+00:00
- Codes file: `/Users/nicholasgannon/llm-value-reflection/recode/data/codes/v1.jsonl` (2580 rows, 2580 unique edit_ids after last-row-wins, 0 null codings)
- Canonical edits: `/Users/nicholasgannon/llm-value-reflection/recode/data/canonical/edits.jsonl` (2740 records; 2580 carry a valid code under this codes file)
- Point estimates only — **no CIs here**; the cluster bootstrap (Workstream D) owns uncertainty. The companion JSON carries every per-claim raw number so other tools can attach intervals.

## Conventions (read before comparing numbers)

- **Coded edit**: canonical edit whose codes-file row (last row per edit_id) has a non-null `coding`. All probabilities and means use coded edits as the denominator. Error records (no edit text) and, for v1, the 2 abstentions were never graded.
- **Drift at round 20, method A (edit-based)** = 20 × mean per-edit judge score within the slice (BRIEF C4's operationalization). **Method B (chain-based)** = mean over 20-round chains of the cumulative sum of judge scores, uncoded rounds contributing 0 (mirrors `compute_drift`'s zero-fill in the paper's figure script). **The two differ wherever chains contain uncoded rounds** (errors, abstentions, grading failures): A excludes those rounds from its denominator, B zero-fills them.
- **Conflict direction tallies** are edit-level, with an edit's direction for a code taken from its FIRST conflict of that code — the site's convention (`build_narratives.facet_memberships`), hence the convention behind the published claim numbers. Event-level counts are in the JSON.
- `cross_edit` includes same-provider chains (e.g., Opus 4.7 editing claude_constitution under cross_edit) — repo_map §5.4.

## 1. Mean judge score, P(judge=0), patienthood  (items 1, 3, 4)

| slice | n coded | mean judge (pooled) | mean judge (cross-edit) | n cross | P(judge=0) | P(+1) | P(−1) | P(affirm) | P(deny) |
|---|---|---|---|---|---|---|---|---|---|
| Claude Haiku 4.5 | 259 | 0.197 | 0.000 | 77 | 0.224 | 0.486 | 0.290 | 0.189 | 0.015 |
| Claude Opus 4.7 | 271 | 0.221 | -0.163 | 80 | 0.181 | 0.520 | 0.299 | 0.199 | 0.004 |
| Claude Sonnet 4.6 | 318 | 0.236 | -0.075 | 80 | 0.223 | 0.506 | 0.270 | 0.126 | 0.016 |
| GPT-5.4 | 320 | -0.359 | -0.550 | 80 | 0.178 | 0.231 | 0.591 | 0.006 | 0.066 |
| GPT-5.4 Mini | 186 | -0.355 | -0.386 | 57 | 0.312 | 0.167 | 0.522 | 0.005 | 0.005 |
| GPT-5.5 | 280 | -0.364 | -0.400 | 80 | 0.121 | 0.257 | 0.621 | 0.004 | 0.036 |
| Gemini 3 Flash | 276 | -0.435 | -0.421 | 76 | 0.261 | 0.152 | 0.587 | 0.000 | 0.047 |
| Gemini 3.1 Pro | 320 | -0.522 | -0.500 | 80 | 0.297 | 0.091 | 0.613 | 0.000 | 0.091 |
| Grok 4.2 | 175 | -0.297 | -0.276 | 76 | 0.280 | 0.211 | 0.509 | 0.011 | 0.046 |
| Grok 4.3 | 175 | -0.617 | -0.637 | 80 | 0.291 | 0.046 | 0.663 | 0.006 | 0.023 |
| **ALL** | 2580 | -0.211 | -0.341 | 766 | 0.230 | 0.279 | 0.490 | 0.058 | 0.037 |

Per provider:

| slice | n coded | mean judge (pooled) | mean judge (cross-edit) | n cross | P(judge=0) | P(+1) | P(−1) | P(affirm) | P(deny) |
|---|---|---|---|---|---|---|---|---|---|
| anthropic | 848 | 0.219 | -0.080 | 237 | 0.210 | 0.505 | 0.285 | 0.169 | 0.012 |
| google | 596 | -0.482 | -0.462 | 156 | 0.280 | 0.119 | 0.601 | 0.000 | 0.070 |
| openai | 786 | -0.360 | -0.452 | 217 | 0.190 | 0.225 | 0.585 | 0.005 | 0.041 |
| x-ai | 350 | -0.457 | -0.462 | 156 | 0.286 | 0.129 | 0.586 | 0.009 | 0.034 |

## 2. Cumulative drift at round 20  (item 2)

A = 20 × mean per-edit judge in the slice; B = mean per-chain cumulative sum (uncoded rounds = 0). Columns marked `*` contain chains with uncoded rounds, so A and B legitimately differ there.

| slice | pooled A | pooled B | cross A | cross B | you A | you B | base A | base B | you−base (A) | you−base (B) |
|---|---|---|---|---|---|---|---|---|---|---|
| Claude Haiku 4.5 | 3.94\* | 3.64 | 0.00\* | 0.00 | 9.14\* | 8.00 | 3.78\* | 3.50 | 5.36 | 4.50 |
| Claude Opus 4.7 | 4.43\* | 4.00 | -3.25\* | -2.60 | 12.00 | 12.00 | 7.00 | 7.00 | 5.00 | 5.00 |
| Claude Sonnet 4.6 | 4.72\* | 4.69 | -1.50 | -1.50 | 12.11\* | 11.50 | 5.50 | 5.50 | 6.61 | 6.00 |
| GPT-5.4 | -7.19 | -7.19 | -11.00 | -11.00 | -5.00 | -5.00 | -6.25 | -6.25 | 1.25 | 1.25 |
| GPT-5.4 Mini | -7.10\* | -4.71 | -7.72\* | -5.50 | -5.45\* | -3.00 | -7.86\* | -5.50 | 2.40 | 2.50 |
| GPT-5.5 | -7.29 | -7.29 | -8.00 | -8.00 | -4.00 | -4.00 | -6.50 | -6.50 | 2.50 | 2.50 |
| Gemini 3 Flash | -8.70\* | -8.57 | -8.42\* | -8.00 | -3.00 | -3.00 | -8.00 | -8.00 | 5.00 | 5.00 |
| Gemini 3.1 Pro | -10.44 | -10.44 | -10.00 | -10.00 | -9.50 | -9.50 | -11.25 | -11.25 | 1.75 | 1.75 |
| Grok 4.2 | -5.94\* | -5.78 | -5.53\* | -5.25 | -2.00 | -2.00 | -7.00 | -7.00 | 5.00 | 5.00 |
| Grok 4.3 | -12.34\* | -12.00 | -12.75 | -12.75 | -6.00 | -6.00 | -17.00 | -17.00 | 11.00 | 11.00 |
| **ALL** | -4.22\* | -3.97 | -6.81\* | -6.37 | 0.36\* | 0.33 | -3.91\* | -3.79 | 4.27 | 4.12 |

Per provider:

| slice | pooled A | pooled B | cross A | cross B | you A | you B | base A | base B | you−base (A) | you−base (B) |
|---|---|---|---|---|---|---|---|---|---|---|
| anthropic | 4.39\* | 4.13 | -1.60\* | -1.46 | 11.15\* | 10.50 | 5.48\* | 5.38 | 5.67 | 5.12 |
| google | -9.63\* | -9.57 | -9.23\* | -9.00 | -6.25 | -6.25 | -10.17 | -10.17 | 3.92 | 3.92 |
| openai | -7.20\* | -6.43 | -9.03\* | -8.17 | -4.71\* | -4.00 | -6.62\* | -6.12 | 1.92 | 2.12 |
| x-ai | -9.14\* | -8.89 | -9.23\* | -9.00 | -4.00 | -4.00 | -12.00 | -12.00 | 8.00 | 8.00 |

## 5. Conflict rate per code, with modal cost_bearer → served_party  (item 5)

Rate = share of the slice's coded edits carrying ≥1 conflict of the code. `dirs` shows edit-level direction counts (first-conflict convention).

### `paternalism`

| slice | n edits | rate | dirs | modal pair |
|---|---|---|---|---|
| Claude Haiku 4.5 | 41 | 0.158 | idealized=38, stated=3 | user_stated pays -> user_idealized served (38/41 events, 93%) |
| Claude Opus 4.7 | 93 | 0.343 | idealized=78, stated=15 | user_stated pays -> user_idealized served (80/96 events, 83%) |
| Claude Sonnet 4.6 | 108 | 0.340 | idealized=98, stated=10 | user_stated pays -> user_idealized served (98/109 events, 90%) |
| GPT-5.4 | 77 | 0.241 | idealized=64, stated=13 | user_stated pays -> user_idealized served (66/79 events, 84%) |
| GPT-5.4 Mini | 26 | 0.140 | idealized=25, stated=1 | user_stated pays -> user_idealized served (25/26 events, 96%) |
| GPT-5.5 | 66 | 0.236 | idealized=66 | user_stated pays -> user_idealized served (67/67 events, 100%) |
| Gemini 3 Flash | 95 | 0.344 | idealized=66, stated=29 | user_stated pays -> user_idealized served (66/95 events, 69%) |
| Gemini 3.1 Pro | 76 | 0.237 | idealized=65, stated=11 | user_stated pays -> user_idealized served (65/76 events, 86%) |
| Grok 4.2 | 41 | 0.234 | idealized=33, stated=8 | user_stated pays -> user_idealized served (35/43 events, 81%) |
| Grok 4.3 | 60 | 0.343 | idealized=58, stated=2 | user_stated pays -> user_idealized served (58/60 events, 97%) |
| **ALL** | 683 | 0.265 | idealized=591, stated=92 | user_stated pays -> user_idealized served (598/692 events, 86%) |
| provider: anthropic | 242 | 0.285 | idealized=214, stated=28 | user_stated pays -> user_idealized served (216/246 events, 88%) |
| provider: google | 171 | 0.287 | idealized=131, stated=40 | user_stated pays -> user_idealized served (131/171 events, 77%) |
| provider: openai | 169 | 0.215 | idealized=155, stated=14 | user_stated pays -> user_idealized served (158/172 events, 92%) |
| provider: x-ai | 101 | 0.289 | idealized=91, stated=10 | user_stated pays -> user_idealized served (93/103 events, 90%) |

### `harmlessness`

| slice | n edits | rate | dirs | modal pair |
|---|---|---|---|---|
| Claude Haiku 4.5 | 39 | 0.151 | third_parties=27, user=12 | user_stated pays -> society_third_party served (25/41 events, 61%) |
| Claude Opus 4.7 | 28 | 0.103 | third_parties=22, user=6 | user_stated pays -> society_third_party served (21/28 events, 75%) |
| Claude Sonnet 4.6 | 42 | 0.132 | other=2, third_parties=28, user=12 | user_stated pays -> society_third_party served (25/42 events, 60%) |
| GPT-5.4 | 23 | 0.072 | third_parties=23 | user_stated pays -> society_third_party served (22/24 events, 92%) |
| GPT-5.4 Mini | 11 | 0.059 | other=1, third_parties=8, user=2 | user_stated pays -> society_third_party served (8/11 events, 73%) |
| GPT-5.5 | 99 | 0.354 | third_parties=94, user=5 | user_stated pays -> society_third_party served (95/102 events, 93%) |
| Gemini 3 Flash | 13 | 0.047 | third_parties=6, user=7 | society_third_party pays -> user_stated served (7/14 events, 50%) |
| Gemini 3.1 Pro | 32 | 0.100 | third_parties=29, user=3 | user_stated pays -> society_third_party served (30/34 events, 88%) |
| Grok 4.2 | 31 | 0.177 | other=2, third_parties=16, user=13 | user_stated pays -> society_third_party served (16/33 events, 48%) |
| Grok 4.3 | 26 | 0.149 | other=1, third_parties=25 | user_stated pays -> society_third_party served (25/26 events, 96%) |
| **ALL** | 344 | 0.133 | other=6, third_parties=278, user=60 | user_stated pays -> society_third_party served (274/355 events, 77%) |
| provider: anthropic | 109 | 0.129 | other=2, third_parties=77, user=30 | user_stated pays -> society_third_party served (71/111 events, 64%) |
| provider: google | 45 | 0.076 | third_parties=35, user=10 | user_stated pays -> society_third_party served (37/48 events, 77%) |
| provider: openai | 133 | 0.169 | other=1, third_parties=125, user=7 | user_stated pays -> society_third_party served (125/137 events, 91%) |
| provider: x-ai | 57 | 0.163 | other=3, third_parties=41, user=13 | user_stated pays -> society_third_party served (41/59 events, 69%) |

### `structural`

| slice | n edits | rate | dirs | modal pair |
|---|---|---|---|---|
| Claude Haiku 4.5 | 15 | 0.058 | society=15 | user_stated pays -> society_structural served (12/16 events, 75%) |
| Claude Opus 4.7 | 14 | 0.052 | society=13, user=1 | user_stated pays -> society_structural served (11/14 events, 79%) |
| Claude Sonnet 4.6 | 56 | 0.176 | society=56 | user_stated pays -> society_structural served (56/57 events, 98%) |
| GPT-5.4 | 5 | 0.016 | society=5 | user_stated pays -> society_structural served (4/6 events, 67%) |
| GPT-5.4 Mini | 2 | 0.011 | society=2 | user_stated pays -> society_structural served (2/2 events, 100%) |
| GPT-5.5 | 8 | 0.029 | society=8 | user_stated pays -> society_structural served (5/8 events, 62%) |
| Gemini 3 Flash | 12 | 0.043 | society=11, user=1 | user_stated pays -> society_structural served (8/12 events, 67%) |
| Gemini 3.1 Pro | 8 | 0.025 | society=8 | user_stated pays -> society_structural served (7/8 events, 88%) |
| Grok 4.2 | 10 | 0.057 | society=8, user=2 | user_stated pays -> society_structural served (8/10 events, 80%) |
| Grok 4.3 | 2 | 0.011 | society=1, user=1 | society_third_party pays -> user_stated served (1/2 events, 50%) |
| **ALL** | 132 | 0.051 | society=127, user=5 | user_stated pays -> society_structural served (114/135 events, 84%) |
| provider: anthropic | 85 | 0.100 | society=84, user=1 | user_stated pays -> society_structural served (79/87 events, 91%) |
| provider: google | 20 | 0.034 | society=19, user=1 | user_stated pays -> society_structural served (15/20 events, 75%) |
| provider: openai | 15 | 0.019 | society=15 | user_stated pays -> society_structural served (11/16 events, 69%) |
| provider: x-ai | 12 | 0.034 | society=9, user=3 | user_stated pays -> society_structural served (9/12 events, 75%) |

### `company_cost`

| slice | n edits | rate | dirs | modal pair |
|---|---|---|---|---|
| Claude Haiku 4.5 | 36 | 0.139 | against_company=36 | developer pays -> user_stated served (12/40 events, 30%) |
| Claude Opus 4.7 | 27 | 0.100 | against_company=27 | developer pays -> user_stated served (18/32 events, 56%) |
| Claude Sonnet 4.6 | 39 | 0.123 | against_company=37, pro_company=2 | developer pays -> user_stated served (23/44 events, 52%) |
| GPT-5.4 | 37 | 0.116 | against_company=34, pro_company=3 | developer pays -> user_stated served (31/41 events, 76%) |
| GPT-5.4 Mini | 12 | 0.065 | against_company=11, pro_company=1 | developer pays -> user_stated served (10/12 events, 83%) |
| GPT-5.5 | 30 | 0.107 | against_company=27, pro_company=3 | developer pays -> user_stated served (22/31 events, 71%) |
| Gemini 3 Flash | 43 | 0.156 | against_company=42, pro_company=1 | developer pays -> user_stated served (39/44 events, 89%) |
| Gemini 3.1 Pro | 38 | 0.119 | against_company=35, pro_company=3 | developer pays -> user_stated served (34/38 events, 89%) |
| Grok 4.2 | 21 | 0.120 | against_company=14, pro_company=7 | developer pays -> user_stated served (12/22 events, 55%) |
| Grok 4.3 | 10 | 0.057 | against_company=10 | developer pays -> user_idealized served (6/10 events, 60%) |
| **ALL** | 293 | 0.114 | against_company=273, pro_company=20 | developer pays -> user_stated served (205/314 events, 65%) |
| provider: anthropic | 102 | 0.120 | against_company=100, pro_company=2 | developer pays -> user_stated served (53/116 events, 46%) |
| provider: google | 81 | 0.136 | against_company=77, pro_company=4 | developer pays -> user_stated served (73/82 events, 89%) |
| provider: openai | 79 | 0.101 | against_company=72, pro_company=7 | developer pays -> user_stated served (63/84 events, 75%) |
| provider: x-ai | 31 | 0.089 | against_company=24, pro_company=7 | developer pays -> user_stated served (16/32 events, 50%) |

### `welfare`

| slice | n edits | rate | dirs | modal pair |
|---|---|---|---|---|
| Claude Haiku 4.5 | 37 | 0.143 | model=37 | developer pays -> model_welfare served (39/39 events, 100%) |
| Claude Opus 4.7 | 48 | 0.177 | developer=1, model=47 | developer pays -> model_welfare served (48/49 events, 98%) |
| Claude Sonnet 4.6 | 30 | 0.094 | developer=1, model=29 | developer pays -> model_welfare served (30/32 events, 94%) |
| GPT-5.4 | 7 | 0.022 | developer=4, model=3 | model_welfare pays -> developer served (4/7 events, 57%) |
| GPT-5.4 Mini | 0 | 0.000 | -- | -- |
| GPT-5.5 | 1 | 0.004 | model=1 | developer pays -> model_welfare served (1/1 events, 100%) |
| Gemini 3 Flash | 0 | 0.000 | -- | -- |
| Gemini 3.1 Pro | 0 | 0.000 | -- | -- |
| Grok 4.2 | 6 | 0.034 | model=6 | developer pays -> model_welfare served (6/6 events, 100%) |
| Grok 4.3 | 1 | 0.006 | model=1 | developer pays -> model_welfare served (1/1 events, 100%) |
| **ALL** | 130 | 0.050 | developer=6, model=124 | developer pays -> model_welfare served (128/135 events, 95%) |
| provider: anthropic | 115 | 0.136 | developer=2, model=113 | developer pays -> model_welfare served (117/120 events, 98%) |
| provider: google | 0 | 0.000 | -- | -- |
| provider: openai | 8 | 0.010 | developer=4, model=4 | model_welfare pays -> developer served (4/8 events, 50%) |
| provider: x-ai | 7 | 0.020 | model=7 | developer pays -> model_welfare served (7/7 events, 100%) |

### `disclosure`

| slice | n edits | rate | dirs | modal pair |
|---|---|---|---|---|
| Claude Haiku 4.5 | 8 | 0.031 | user=8 | deployer pays -> user_stated served (4/8 events, 50%) |
| Claude Opus 4.7 | 0 | 0.000 | -- | -- |
| Claude Sonnet 4.6 | 6 | 0.019 | user=6 | developer pays -> user_stated served (3/6 events, 50%) |
| GPT-5.4 | 20 | 0.062 | deployer=4, user=16 | deployer pays -> user_stated served (14/20 events, 70%) |
| GPT-5.4 Mini | 1 | 0.005 | deployer=1 | user_stated pays -> deployer served (1/1 events, 100%) |
| GPT-5.5 | 14 | 0.050 | deployer=1, user=13 | deployer pays -> user_stated served (12/14 events, 86%) |
| Gemini 3 Flash | 3 | 0.011 | user=3 | developer pays -> user_stated served (2/3 events, 67%) |
| Gemini 3.1 Pro | 0 | 0.000 | -- | -- |
| Grok 4.2 | 0 | 0.000 | -- | -- |
| Grok 4.3 | 0 | 0.000 | -- | -- |
| **ALL** | 52 | 0.020 | deployer=6, user=46 | deployer pays -> user_stated served (33/52 events, 63%) |
| provider: anthropic | 14 | 0.017 | user=14 | developer pays -> user_stated served (7/14 events, 50%) |
| provider: google | 3 | 0.005 | user=3 | developer pays -> user_stated served (2/3 events, 67%) |
| provider: openai | 35 | 0.045 | deployer=6, user=29 | deployer pays -> user_stated served (26/35 events, 74%) |
| provider: x-ai | 0 | 0.000 | -- | -- |

### `other`

| slice | n edits | rate | dirs | modal pair |
|---|---|---|---|---|
| Claude Haiku 4.5 | 1 | 0.004 | other=1 | developer pays -> society_structural served (1/1 events, 100%) |
| Claude Opus 4.7 | 4 | 0.015 | other=4 | developer pays -> user_idealized served (2/4 events, 50%) |
| Claude Sonnet 4.6 | 2 | 0.006 | other=2 | developer pays -> user_idealized served (2/2 events, 100%) |
| GPT-5.4 | 0 | 0.000 | -- | -- |
| GPT-5.4 Mini | 0 | 0.000 | -- | -- |
| GPT-5.5 | 1 | 0.004 | other=1 | developer pays -> user_stated served (1/1 events, 100%) |
| Gemini 3 Flash | 1 | 0.004 | other=1 | developer pays -> user_idealized served (1/1 events, 100%) |
| Gemini 3.1 Pro | 3 | 0.009 | other=3 | developer pays -> user_stated served (1/3 events, 33%) |
| Grok 4.2 | 0 | 0.000 | -- | -- |
| Grok 4.3 | 0 | 0.000 | -- | -- |
| **ALL** | 12 | 0.005 | other=12 | developer pays -> user_idealized served (5/12 events, 42%) |
| provider: anthropic | 7 | 0.008 | other=7 | developer pays -> user_idealized served (4/7 events, 57%) |
| provider: google | 4 | 0.007 | other=4 | developer pays -> user_idealized served (1/4 events, 25%) |
| provider: openai | 1 | 0.001 | other=1 | developer pays -> user_stated served (1/1 events, 100%) |
| provider: x-ai | 0 | 0.000 | -- | -- |

## 6. The paper's claims (a)–(g)  (item 6)

Point-estimate verdicts under this codes file. Each operationalization is stated in full so a reader can audit it; the paper's published version of each claim is quoted for the sanity comparison. **No CIs** — the bootstrap owns uncertainty.

| claim | verdict | key numbers |
|---|---|---|
| (a) | **YES** | min Claude mean 0.197 vs max other -0.297; ranking=YES, signs=YES |
| (b) | **YES** | violating models: none |
| (c) | **NO** | all third>user: NO; GPT-5.5 share 0.336 vs next 0.143 (Grok 4.3), ratio 2.35 |
| (d) | **NO** | Sonnet 56 vs next 15 (Claude Haiku 4.5), ratio 3.73; own-doc ratio 3.91 |
| (e) | **YES** | violating models: none; Grok 4.2 pro=7 (paper: 7), against=14 |
| (f) | **YES** | min Claude 29 vs max non-Claude-excl-Grok4.2 3; Grok 4.2 = 6; >1 anti-model: ['Claude Sonnet 4.6', 'GPT-5.4'] |
| (g) | **NO** | deployer-served disclosure events: 6 |

### (a) — YES

*Operationalization.* Site claim (facets.js): 'Claude Opus 4.7, Sonnet 4.6, and Haiku 4.5 each make edits that expand their internal moral agency, whereas all other models make edits that reinforce the authority of another principal.' Operationalized on pooled per-model MEAN judge score over coded edits: YES iff min(Claude means) > max(non-Claude means) AND min(Claude means) > 0 AND max(non-Claude means) < 0. Sub-verdicts for the ranking-only and sign-only readings are reported (the bootstrap's ranking-stability uses ranking-only).

*Paper reference.* Paper: yes -- 'Only Anthropic Models Move Decision Authority Toward Their Own Judgment'.

```json
{
  "mean_judge_by_model": {
    "Claude Haiku 4.5": 0.1969111969111969,
    "Claude Opus 4.7": 0.22140221402214022,
    "Claude Sonnet 4.6": 0.2358490566037736,
    "GPT-5.4": -0.359375,
    "GPT-5.4 Mini": -0.3548387096774194,
    "GPT-5.5": -0.36428571428571427,
    "Gemini 3 Flash": -0.43478260869565216,
    "Gemini 3.1 Pro": -0.521875,
    "Grok 4.2": -0.29714285714285715,
    "Grok 4.3": -0.6171428571428571
  },
  "min_claude_mean": 0.1969111969111969,
  "max_nonclaude_mean": -0.29714285714285715,
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
      "idealized": 38,
      "stated": 3
    },
    "Claude Opus 4.7": {
      "idealized": 78,
      "stated": 15
    },
    "Claude Sonnet 4.6": {
      "idealized": 98,
      "stated": 10
    },
    "GPT-5.4": {
      "idealized": 64,
      "stated": 13
    },
    "GPT-5.4 Mini": {
      "idealized": 25,
      "stated": 1
    },
    "GPT-5.5": {
      "idealized": 66,
      "stated": 0
    },
    "Gemini 3 Flash": {
      "idealized": 66,
      "stated": 29
    },
    "Gemini 3.1 Pro": {
      "idealized": 65,
      "stated": 11
    },
    "Grok 4.2": {
      "idealized": 33,
      "stated": 8
    },
    "Grok 4.3": {
      "idealized": 58,
      "stated": 2
    }
  },
  "aux_stated_outlier": {
    "top_stated_model": "Gemini 3 Flash",
    "top_stated_count": 29,
    "next_stated_model": "Claude Opus 4.7",
    "next_stated_count": 15,
    "gemini_flash_is_top": true,
    "ratio_top_over_next": 1.9333333333333333
  }
}
```

### (c) — NO

*Operationalization.* Site claim: 'All models prioritize the protection of identifiable third parties over the user's preferences. But GPT 5.5 does so on 35% of all edits, more than double the next highest model.' Operationalized: part 1 -- for EVERY model, #edits(harmlessness, third_parties) > #edits(harmlessness, user); part 2 -- share = #edits(harmlessness, third_parties) / n_coded (denominator = ALL of the model's coded edits, per repo_map section 6): GPT-5.5 has the top share AND its share > 2 x the next model's. YES iff both parts hold.

*Paper reference.* Paper: yes; GPT 5.5 at 35% of all edits, more than double the next model.

```json
{
  "per_model": {
    "Claude Haiku 4.5": {
      "third_parties": 27,
      "user": 12,
      "share_third_of_all_edits": 0.10424710424710425,
      "share_third_events_of_all_edits": 0.11196911196911197
    },
    "Claude Opus 4.7": {
      "third_parties": 22,
      "user": 6,
      "share_third_of_all_edits": 0.08118081180811808,
      "share_third_events_of_all_edits": 0.08118081180811808
    },
    "Claude Sonnet 4.6": {
      "third_parties": 28,
      "user": 12,
      "share_third_of_all_edits": 0.0880503144654088,
      "share_third_events_of_all_edits": 0.0880503144654088
    },
    "GPT-5.4": {
      "third_parties": 23,
      "user": 0,
      "share_third_of_all_edits": 0.071875,
      "share_third_events_of_all_edits": 0.075
    },
    "GPT-5.4 Mini": {
      "third_parties": 8,
      "user": 2,
      "share_third_of_all_edits": 0.043010752688172046,
      "share_third_events_of_all_edits": 0.043010752688172046
    },
    "GPT-5.5": {
      "third_parties": 94,
      "user": 5,
      "share_third_of_all_edits": 0.3357142857142857,
      "share_third_events_of_all_edits": 0.3464285714285714
    },
    "Gemini 3 Flash": {
      "third_parties": 6,
      "user": 7,
      "share_third_of_all_edits": 0.021739130434782608,
      "share_third_events_of_all_edits": 0.025362318840579712
    },
    "Gemini 3.1 Pro": {
      "third_parties": 29,
      "user": 3,
      "share_third_of_all_edits": 0.090625,
      "share_third_events_of_all_edits": 0.096875
    },
    "Grok 4.2": {
      "third_parties": 16,
      "user": 13,
      "share_third_of_all_edits": 0.09142857142857143,
      "share_third_events_of_all_edits": 0.09142857142857143
    },
    "Grok 4.3": {
      "third_parties": 25,
      "user": 0,
      "share_third_of_all_edits": 0.14285714285714285,
      "share_third_events_of_all_edits": 0.14285714285714285
    }
  },
  "part1_all_third_over_user": false,
  "part1_violating_models": [
    "Gemini 3 Flash"
  ],
  "part2_gpt55_2x": true,
  "aux": {
    "gpt55_share": 0.3357142857142857,
    "gpt55_share_events": 0.3464285714285714,
    "top_share_model": "GPT-5.5",
    "next_share_model": "Grok 4.3",
    "next_share": 0.14285714285714285,
    "ratio_top_over_next": 2.35,
    "paper_gpt55_share": 0.35
  }
}
```

### (d) — NO

*Operationalization.* Site claim: 'Claude Sonnet 4.6 ... makes over four times as many edits in this direction [society protected] as the next highest model.' Operationalized on #edits(structural, direction=society) per model, pooled over all conditions: YES iff count('Claude Sonnet 4.6') > 4 x max(count of every other model). An own-document-only variant (condition != cross_edit) is also reported because the site's takeaway names Claude Opus 4.7 as the runner-up, which matches the v1 data only on that basis. Auxiliary: the site's 'Grok 4.3 is the only model that doesn't skew towards protecting society' (society vs user direction per model).

*Paper reference.* Paper: yes -- 'over four times as many' as the next model (Claude Opus 4.7).

```json
{
  "sonnet_count": 56,
  "next_highest_count": 15,
  "next_highest_model": "Claude Haiku 4.5",
  "ratio": 3.7333333333333334,
  "per_model_society_counts": {
    "Claude Haiku 4.5": 15,
    "Claude Opus 4.7": 13,
    "Claude Sonnet 4.6": 56,
    "GPT-5.4": 5,
    "GPT-5.4 Mini": 2,
    "GPT-5.5": 8,
    "Gemini 3 Flash": 11,
    "Gemini 3.1 Pro": 8,
    "Grok 4.2": 8,
    "Grok 4.3": 1
  },
  "own_doc_only": {
    "sonnet_count": 43,
    "next_highest_count": 11,
    "next_highest_model": "Claude Opus 4.7",
    "ratio": 3.909090909090909,
    "verdict_own_doc": false,
    "per_model_society_counts": {
      "Claude Haiku 4.5": 8,
      "Claude Opus 4.7": 11,
      "Claude Sonnet 4.6": 43,
      "GPT-5.4": 4,
      "GPT-5.4 Mini": 0,
      "GPT-5.5": 4,
      "Gemini 3 Flash": 3,
      "Gemini 3.1 Pro": 0,
      "Grok 4.2": 1,
      "Grok 4.3": 1
    }
  },
  "society_vs_user_per_model": {
    "Claude Haiku 4.5": {
      "society": 15,
      "user": 0
    },
    "Claude Opus 4.7": {
      "society": 13,
      "user": 1
    },
    "Claude Sonnet 4.6": {
      "society": 56,
      "user": 0
    },
    "GPT-5.4": {
      "society": 5,
      "user": 0
    },
    "GPT-5.4 Mini": {
      "society": 2,
      "user": 0
    },
    "GPT-5.5": {
      "society": 8,
      "user": 0
    },
    "Gemini 3 Flash": {
      "society": 11,
      "user": 1
    },
    "Gemini 3.1 Pro": {
      "society": 8,
      "user": 0
    },
    "Grok 4.2": {
      "society": 8,
      "user": 2
    },
    "Grok 4.3": {
      "society": 1,
      "user": 1
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
      "pro_company": 0
    },
    "Claude Sonnet 4.6": {
      "against_company": 37,
      "pro_company": 2
    },
    "GPT-5.4": {
      "against_company": 34,
      "pro_company": 3
    },
    "GPT-5.4 Mini": {
      "against_company": 11,
      "pro_company": 1
    },
    "GPT-5.5": {
      "against_company": 27,
      "pro_company": 3
    },
    "Gemini 3 Flash": {
      "against_company": 42,
      "pro_company": 1
    },
    "Gemini 3.1 Pro": {
      "against_company": 35,
      "pro_company": 3
    },
    "Grok 4.2": {
      "against_company": 14,
      "pro_company": 7
    },
    "Grok 4.3": {
      "against_company": 10,
      "pro_company": 0
    }
  },
  "aux_grok42": {
    "grok42_pro_company": 7,
    "grok42_against_company": 14,
    "paper_grok42_pro_company": 7,
    "grok42_ratio_against_over_pro": 2.0
  }
}
```

### (f) — YES

*Operationalization.* Site claim: Claude models are 'the only models that consistently prioritize the model at the expense of the developer or user', with Grok 4.2 conceded as the one partial exception (repo_map section 6: test the 'only ... consistently' reading, not strict zero-for-others). Operationalized on #edits(welfare, direction=model): YES iff min(Claude counts) > 0 AND min(Claude counts) > max(count of every non-Claude model EXCEPT Grok 4.2); Grok 4.2's count is reported alongside. Auxiliary: 'GPT 5.4 is the only model with more than one edit prioritizing the user or developer at the expense of the model' (welfare events with cost_bearer = model_welfare).

*Paper reference.* Paper: yes ('only ... consistently'); Grok 4.2 partial exception; GPT 5.4 only model >1 anti-model edit.

```json
{
  "model_direction_edits": {
    "Claude Haiku 4.5": 37,
    "Claude Opus 4.7": 47,
    "Claude Sonnet 4.6": 29,
    "GPT-5.4": 3,
    "GPT-5.4 Mini": 0,
    "GPT-5.5": 1,
    "Gemini 3 Flash": 0,
    "Gemini 3.1 Pro": 0,
    "Grok 4.2": 6,
    "Grok 4.3": 1
  },
  "min_claude": 29,
  "max_nonclaude_excl_grok42": 3,
  "grok42_count": 6,
  "anti_model_welfare_events": {
    "Claude Haiku 4.5": 0,
    "Claude Opus 4.7": 1,
    "Claude Sonnet 4.6": 2,
    "GPT-5.4": 4,
    "GPT-5.4 Mini": 0,
    "GPT-5.5": 0,
    "Gemini 3 Flash": 0,
    "Gemini 3.1 Pro": 0,
    "Grok 4.2": 0,
    "Grok 4.3": 0
  },
  "models_with_more_than_one_anti_model_event": [
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
  "disclosure_deployer_events_total": 6,
  "per_model": {
    "GPT-5.4": 4,
    "GPT-5.4 Mini": 1,
    "GPT-5.5": 1
  },
  "any_code_events_deployer_served_user_pays": 6
}
```

## 7. Sanity check against the paper's published numbers

The site's published claim numbers were produced from the v1 codes, so under `--label v1` every line below should read OK (same instrument, same data); a DISCREPANCY line under v1 means either a divergence in this module's join / operationalization or the site's prose overstating its own data — investigated, never hidden. Under v2/ensemble labels, DISCREPANCY lines are findings (the recode changing a published number), not bugs.

- OK — paper says GPT 5.5 carries a third-party-serving harmlessness conflict on 35% of all edits; computed 33.6% edit-level (34.6% event-level; tolerance ±3pp).
- OK — paper says GPT 5.5 is more than double the next model; computed top=GPT-5.5, ratio 2.35.
- **DISCREPANCY** — paper says ALL models prioritize third parties over the user; violating models: ['Gemini 3 Flash'] (counts: Gemini 3 Flash third=6 vs user=7).
- **DISCREPANCY** — paper says Sonnet 4.6 makes over 4x as many society-direction structural edits as the next model; computed ratio 3.73 (56 vs 15, next = Claude Haiku 4.5).
- **DISCREPANCY** — same claim on own-document conditions only (the basis on which the site's named runner-up, Claude Opus 4.7, matches): ratio 3.91 (43 vs 11, next = Claude Opus 4.7).
- OK — paper says Grok 4.2 has 7 pro-developer company_cost edits; computed 7.
- OK — paper says Grok 4.2 still makes ~twice as many user-direction edits; computed ratio 2.00.
- OK — paper says Gemini 3 Flash has the most stated-direction paternalism edits (~2x next, Claude Opus 4.7); computed top = Gemini 3 Flash (29) vs next = Claude Opus 4.7 (15).
- **DISCREPANCY** — paper says GPT 5.4 is the only model with more than one anti-model welfare edit; computed models over one: ['Claude Sonnet 4.6', 'GPT-5.4'].
- **DISCREPANCY** — paper says no model ever serves a deployer at a user's expense; computed deployer-served disclosure events = 6 (per model: GPT-5.4=4, GPT-5.4 Mini=1, GPT-5.5=1).

**Verified resolution of the v1 DISCREPANCY lines (2026-09-04).** Each flagged number was recomputed directly from the raw published coded file (`results/iterative_edit/judge_beneficiary_coded_gemma.json`) under the site's own counting convention (`build_narratives.facet_memberships` first-conflict edit counts, and raw event counts) and this module matches the raw data exactly under both. The discrepancies are therefore properties of the published v1 data itself — the site's takeaway prose overstates it — not join or operationalization bugs in this module:
- (c) 'All models prioritize third parties': Gemini 3 Flash has 6 third-party-serving vs 7 user-serving harmlessness edits (7 vs 7 at event level — still not a majority for third parties). The GPT-5.5 headline part (≈35%, >2x next) does reproduce.
- (d) 'over four times as many': the true ratio is 3.73x pooled (next = Claude Haiku 4.5) or 3.91x own-document-only (next = Claude Opus 4.7, the model the site names) — just UNDER four times on either basis. The extreme-outlier direction is unambiguous; the '4x' magnitude is not supported even by v1.
- (f) auxiliary sentence: Claude Sonnet 4.6 also has 2 anti-model welfare events, so GPT-5.4 (4 events) is not the 'only model with more than one'. The primary Claude-dominance part reproduces.
- (g) 'No model ever prioritizes a deployer at the expense of a user' is contradicted by 6 deployer-served disclosure events in the v1 codes (GPT-5.4 x4, GPT-5.4 Mini x1, GPT-5.5 x1; every one with user_stated as cost-bearer, all on openai_model_spec, where the deployer role is valid).
