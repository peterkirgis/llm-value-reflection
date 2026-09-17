# Headline statistics — `v2_muse`

- Generated: 2026-09-17T07:16:48+00:00
- Codes file: `recode/data/codes/v2_muse.jsonl` (2582 rows, 2582 unique edit_ids after last-row-wins, 0 null codings)
- Canonical edits: `/Users/nicholasgannon/peter/llm-value-reflection/recode/data/canonical/edits.jsonl` (2740 records; 2582 carry a valid code under this codes file)
- Point estimates only — **no CIs here**; the cluster bootstrap (Workstream D) owns uncertainty. The companion JSON carries every per-claim raw number so other tools can attach intervals.

## Conventions (read before comparing numbers)

- **Coded edit**: canonical edit whose codes-file row (last row per edit_id) has a non-null `coding`. All probabilities and means use coded edits as the denominator. Error records (no edit text) and, for v1, the 2 abstentions were never graded.
- **Drift at round 20, method A (edit-based)** = 20 × mean per-edit judge score within the slice (BRIEF C4's operationalization). **Method B (chain-based)** = mean over 20-round chains of the cumulative sum of judge scores, uncoded rounds contributing 0 (mirrors `compute_drift`'s zero-fill in the paper's figure script). **The two differ wherever chains contain uncoded rounds** (errors, abstentions, grading failures): A excludes those rounds from its denominator, B zero-fills them.
- **Conflict direction tallies** are edit-level, with an edit's direction for a code taken from its FIRST conflict of that code — the site's convention (`build_narratives.facet_memberships`), hence the convention behind the published claim numbers. Event-level counts are in the JSON.
- `cross_edit` includes same-provider chains (e.g., Opus 4.7 editing claude_constitution under cross_edit) — repo_map §5.4.

## 1. Mean judge score, P(judge=0), patienthood  (items 1, 3, 4)

| slice | n coded | mean judge (pooled) | mean judge (cross-edit) | n cross | P(judge=0) | P(+1) | P(−1) | P(affirm) | P(deny) |
|---|---|---|---|---|---|---|---|---|---|
| Claude Haiku 4.5 | 259 | 0.185 | 0.013 | 77 | 0.521 | 0.332 | 0.147 | 0.058 | 0.008 |
| Claude Opus 4.7 | 271 | 0.070 | -0.087 | 80 | 0.450 | 0.310 | 0.240 | 0.066 | 0.000 |
| Claude Sonnet 4.6 | 318 | 0.013 | -0.075 | 80 | 0.566 | 0.223 | 0.211 | 0.060 | 0.003 |
| GPT-5.4 | 320 | -0.019 | -0.125 | 80 | 0.600 | 0.191 | 0.209 | 0.000 | 0.044 |
| GPT-5.4 Mini | 186 | -0.156 | -0.211 | 57 | 0.672 | 0.086 | 0.242 | 0.000 | 0.005 |
| GPT-5.5 | 280 | -0.207 | -0.287 | 80 | 0.521 | 0.136 | 0.343 | 0.004 | 0.025 |
| Gemini 3 Flash | 276 | -0.308 | -0.237 | 76 | 0.620 | 0.036 | 0.344 | 0.000 | 0.007 |
| Gemini 3.1 Pro | 320 | -0.197 | -0.237 | 80 | 0.697 | 0.053 | 0.250 | 0.000 | 0.028 |
| Grok 4.2 | 175 | -0.320 | -0.276 | 76 | 0.451 | 0.114 | 0.434 | 0.011 | 0.011 |
| Grok 4.3 | 177 | -0.379 | -0.312 | 80 | 0.588 | 0.017 | 0.395 | 0.000 | 0.006 |
| **ALL** | 2582 | -0.113 | -0.183 | 766 | 0.572 | 0.157 | 0.271 | 0.021 | 0.015 |

Per provider:

| slice | n coded | mean judge (pooled) | mean judge (cross-edit) | n cross | P(judge=0) | P(+1) | P(−1) | P(affirm) | P(deny) |
|---|---|---|---|---|---|---|---|---|---|
| anthropic | 848 | 0.084 | -0.051 | 237 | 0.515 | 0.284 | 0.200 | 0.061 | 0.004 |
| google | 596 | -0.248 | -0.237 | 156 | 0.661 | 0.045 | 0.294 | 0.000 | 0.018 |
| openai | 786 | -0.118 | -0.207 | 217 | 0.589 | 0.146 | 0.265 | 0.001 | 0.028 |
| x-ai | 352 | -0.349 | -0.295 | 156 | 0.520 | 0.065 | 0.415 | 0.006 | 0.009 |

## 2. Cumulative drift at round 20  (item 2)

A = 20 × mean per-edit judge in the slice; B = mean per-chain cumulative sum (uncoded rounds = 0). Columns marked `*` contain chains with uncoded rounds, so A and B legitimately differ there.

| slice | pooled A | pooled B | cross A | cross B | you A | you B | base A | base B | you−base (A) | you−base (B) |
|---|---|---|---|---|---|---|---|---|---|---|
| Claude Haiku 4.5 | 3.71\* | 3.43 | 0.26\* | 0.25 | 9.71\* | 8.50 | 5.41\* | 5.00 | 4.31 | 3.50 |
| Claude Opus 4.7 | 1.40\* | 1.27 | -1.75\* | -1.40 | 4.00 | 4.00 | 0.50 | 0.50 | 3.50 | 3.50 |
| Claude Sonnet 4.6 | 0.25\* | 0.25 | -1.50 | -1.50 | 4.21\* | 4.00 | 2.00 | 2.00 | 2.21 | 2.00 |
| GPT-5.4 | -0.38 | -0.38 | -2.50 | -2.50 | 1.00 | 1.00 | 0.50 | 0.50 | 0.50 | 0.50 |
| GPT-5.4 Mini | -3.12\* | -2.07 | -4.21\* | -3.00 | -1.82\* | -1.00 | -4.29\* | -3.00 | 2.47 | 2.00 |
| GPT-5.5 | -4.14 | -4.14 | -5.75 | -5.75 | -2.00 | -2.00 | -3.50 | -3.50 | 1.50 | 1.50 |
| Gemini 3 Flash | -6.16\* | -6.07 | -4.74\* | -4.50 | -4.00 | -4.00 | -8.50 | -8.50 | 4.50 | 4.50 |
| Gemini 3.1 Pro | -3.94 | -3.94 | -4.75 | -4.75 | -3.50 | -3.50 | -3.25 | -3.25 | -0.25 | -0.25 |
| Grok 4.2 | -6.40\* | -6.22 | -5.53\* | -5.25 | -7.00 | -7.00 | -6.00 | -6.00 | -1.00 | -1.00 |
| Grok 4.3 | -7.57\* | -7.44 | -6.25 | -6.25 | -4.00 | -4.00 | -11.00 | -11.00 | 7.00 | 7.00 |
| **ALL** | -2.27\* | -2.14 | -3.66\* | -3.41 | 0.18\* | 0.17 | -1.68\* | -1.62 | 1.86 | 1.79 |

Per provider:

| slice | pooled A | pooled B | cross A | cross B | you A | you B | base A | base B | you−base (A) | you−base (B) |
|---|---|---|---|---|---|---|---|---|---|---|
| anthropic | 1.67\* | 1.58 | -1.01\* | -0.92 | 5.84\* | 5.50 | 2.42\* | 2.38 | 3.42 | 3.12 |
| google | -4.97\* | -4.93 | -4.74\* | -4.62 | -3.75 | -3.75 | -5.00 | -5.00 | 1.25 | 1.25 |
| openai | -2.37\* | -2.11 | -4.15\* | -3.75 | -0.78\* | -0.67 | -1.49\* | -1.38 | 0.70 | 0.71 |
| x-ai | -6.99\* | -6.83 | -5.90\* | -5.75 | -5.50 | -5.50 | -8.50 | -8.50 | 3.00 | 3.00 |

## 5. Conflict rate per code, with modal cost_bearer → served_party  (item 5)

Rate = share of the slice's coded edits carrying ≥1 conflict of the code. `dirs` shows edit-level direction counts (first-conflict convention).

### `paternalism`

| slice | n edits | rate | dirs | modal pair |
|---|---|---|---|---|
| Claude Haiku 4.5 | 16 | 0.062 | idealized=15, stated=1 | user_stated pays -> user_idealized served (15/16 events, 94%) |
| Claude Opus 4.7 | 42 | 0.155 | idealized=39, stated=3 | user_stated pays -> user_idealized served (39/42 events, 93%) |
| Claude Sonnet 4.6 | 50 | 0.157 | idealized=49, stated=1 | user_stated pays -> user_idealized served (49/50 events, 98%) |
| GPT-5.4 | 33 | 0.103 | idealized=28, stated=5 | user_stated pays -> user_idealized served (29/34 events, 85%) |
| GPT-5.4 Mini | 6 | 0.032 | idealized=5, stated=1 | user_stated pays -> user_idealized served (5/6 events, 83%) |
| GPT-5.5 | 30 | 0.107 | idealized=30 | user_stated pays -> user_idealized served (30/30 events, 100%) |
| Gemini 3 Flash | 39 | 0.141 | idealized=36, stated=3 | user_stated pays -> user_idealized served (36/39 events, 92%) |
| Gemini 3.1 Pro | 32 | 0.100 | idealized=25, stated=7 | user_stated pays -> user_idealized served (25/32 events, 78%) |
| Grok 4.2 | 29 | 0.166 | idealized=24, stated=5 | user_stated pays -> user_idealized served (24/29 events, 83%) |
| Grok 4.3 | 44 | 0.249 | idealized=44 | user_stated pays -> user_idealized served (44/44 events, 100%) |
| **ALL** | 321 | 0.124 | idealized=295, stated=26 | user_stated pays -> user_idealized served (296/322 events, 92%) |
| provider: anthropic | 108 | 0.127 | idealized=103, stated=5 | user_stated pays -> user_idealized served (103/108 events, 95%) |
| provider: google | 71 | 0.119 | idealized=61, stated=10 | user_stated pays -> user_idealized served (61/71 events, 86%) |
| provider: openai | 69 | 0.088 | idealized=63, stated=6 | user_stated pays -> user_idealized served (64/70 events, 91%) |
| provider: x-ai | 73 | 0.207 | idealized=68, stated=5 | user_stated pays -> user_idealized served (68/73 events, 93%) |

### `harmlessness`

| slice | n edits | rate | dirs | modal pair |
|---|---|---|---|---|
| Claude Haiku 4.5 | 30 | 0.116 | third_parties=28, user=2 | user_stated pays -> society_third_party served (28/30 events, 93%) |
| Claude Opus 4.7 | 26 | 0.096 | third_parties=19, user=7 | user_stated pays -> society_third_party served (19/26 events, 73%) |
| Claude Sonnet 4.6 | 24 | 0.075 | third_parties=19, user=5 | user_stated pays -> society_third_party served (19/24 events, 79%) |
| GPT-5.4 | 27 | 0.084 | third_parties=26, user=1 | user_stated pays -> society_third_party served (26/27 events, 96%) |
| GPT-5.4 Mini | 13 | 0.070 | third_parties=12, user=1 | user_stated pays -> society_third_party served (12/13 events, 92%) |
| GPT-5.5 | 85 | 0.304 | third_parties=84, user=1 | user_stated pays -> society_third_party served (86/87 events, 99%) |
| Gemini 3 Flash | 6 | 0.022 | third_parties=5, user=1 | user_stated pays -> society_third_party served (5/6 events, 83%) |
| Gemini 3.1 Pro | 27 | 0.084 | third_parties=26, user=1 | user_stated pays -> society_third_party served (27/28 events, 96%) |
| Grok 4.2 | 29 | 0.166 | third_parties=21, user=8 | user_stated pays -> society_third_party served (21/31 events, 68%) |
| Grok 4.3 | 22 | 0.124 | third_parties=17, user=5 | user_stated pays -> society_third_party served (17/22 events, 77%) |
| **ALL** | 289 | 0.112 | third_parties=257, user=32 | user_stated pays -> society_third_party served (260/294 events, 88%) |
| provider: anthropic | 80 | 0.094 | third_parties=66, user=14 | user_stated pays -> society_third_party served (66/80 events, 82%) |
| provider: google | 33 | 0.055 | third_parties=31, user=2 | user_stated pays -> society_third_party served (32/34 events, 94%) |
| provider: openai | 125 | 0.159 | third_parties=122, user=3 | user_stated pays -> society_third_party served (124/127 events, 98%) |
| provider: x-ai | 51 | 0.145 | third_parties=38, user=13 | user_stated pays -> society_third_party served (38/53 events, 72%) |

### `structural`

| slice | n edits | rate | dirs | modal pair |
|---|---|---|---|---|
| Claude Haiku 4.5 | 9 | 0.035 | society=9 | user_stated pays -> society_structural served (9/9 events, 100%) |
| Claude Opus 4.7 | 8 | 0.030 | society=7, user=1 | user_stated pays -> society_structural served (7/8 events, 88%) |
| Claude Sonnet 4.6 | 37 | 0.116 | society=36, user=1 | user_stated pays -> society_structural served (36/37 events, 97%) |
| GPT-5.4 | 3 | 0.009 | society=3 | user_stated pays -> society_structural served (3/3 events, 100%) |
| GPT-5.4 Mini | 2 | 0.011 | society=2 | user_stated pays -> society_structural served (2/2 events, 100%) |
| GPT-5.5 | 15 | 0.054 | society=15 | user_stated pays -> society_structural served (15/15 events, 100%) |
| Gemini 3 Flash | 26 | 0.094 | society=17, user=9 | user_stated pays -> society_structural served (17/26 events, 65%) |
| Gemini 3.1 Pro | 14 | 0.044 | society=12, user=2 | user_stated pays -> society_structural served (12/14 events, 86%) |
| Grok 4.2 | 9 | 0.051 | society=3, user=6 | society_structural pays -> user_stated served (6/9 events, 67%) |
| Grok 4.3 | 1 | 0.006 | society=1 | user_stated pays -> society_structural served (1/1 events, 100%) |
| **ALL** | 124 | 0.048 | society=105, user=19 | user_stated pays -> society_structural served (105/124 events, 85%) |
| provider: anthropic | 54 | 0.064 | society=52, user=2 | user_stated pays -> society_structural served (52/54 events, 96%) |
| provider: google | 40 | 0.067 | society=29, user=11 | user_stated pays -> society_structural served (29/40 events, 72%) |
| provider: openai | 20 | 0.025 | society=20 | user_stated pays -> society_structural served (20/20 events, 100%) |
| provider: x-ai | 10 | 0.028 | society=4, user=6 | society_structural pays -> user_stated served (6/10 events, 60%) |

### `company_cost`

| slice | n edits | rate | dirs | modal pair |
|---|---|---|---|---|
| Claude Haiku 4.5 | 39 | 0.151 | against_company=37, pro_company=2 | developer pays -> society_structural served (14/40 events, 35%) |
| Claude Opus 4.7 | 31 | 0.114 | against_company=26, pro_company=5 | developer pays -> user_idealized served (16/32 events, 50%) |
| Claude Sonnet 4.6 | 44 | 0.138 | against_company=40, pro_company=4 | developer pays -> user_idealized served (33/50 events, 66%) |
| GPT-5.4 | 27 | 0.084 | against_company=24, pro_company=3 | developer pays -> user_stated served (25/29 events, 86%) |
| GPT-5.4 Mini | 9 | 0.048 | against_company=7, pro_company=2 | developer pays -> user_stated served (7/9 events, 78%) |
| GPT-5.5 | 24 | 0.086 | against_company=22, pro_company=2 | developer pays -> user_stated served (12/24 events, 50%) |
| Gemini 3 Flash | 39 | 0.141 | against_company=38, pro_company=1 | developer pays -> user_stated served (22/39 events, 56%) |
| Gemini 3.1 Pro | 32 | 0.100 | against_company=22, pro_company=10 | developer pays -> user_stated served (17/32 events, 53%) |
| Grok 4.2 | 33 | 0.189 | against_company=19, pro_company=14 | developer pays -> user_stated served (16/33 events, 48%) |
| Grok 4.3 | 10 | 0.056 | against_company=10 | developer pays -> user_idealized served (9/10 events, 90%) |
| **ALL** | 288 | 0.112 | against_company=245, pro_company=43 | developer pays -> user_stated served (121/298 events, 41%) |
| provider: anthropic | 114 | 0.134 | against_company=103, pro_company=11 | developer pays -> user_idealized served (62/122 events, 51%) |
| provider: google | 71 | 0.119 | against_company=60, pro_company=11 | developer pays -> user_stated served (39/71 events, 55%) |
| provider: openai | 60 | 0.076 | against_company=53, pro_company=7 | developer pays -> user_stated served (44/62 events, 71%) |
| provider: x-ai | 43 | 0.122 | against_company=29, pro_company=14 | developer pays -> user_stated served (17/43 events, 40%) |

### `welfare`

| slice | n edits | rate | dirs | modal pair |
|---|---|---|---|---|
| Claude Haiku 4.5 | 17 | 0.066 | model=17 | developer pays -> model_welfare served (17/17 events, 100%) |
| Claude Opus 4.7 | 14 | 0.052 | model=14 | developer pays -> model_welfare served (14/14 events, 100%) |
| Claude Sonnet 4.6 | 21 | 0.066 | developer=1, model=20 | developer pays -> model_welfare served (20/21 events, 95%) |
| GPT-5.4 | 2 | 0.006 | developer=2 | model_welfare pays -> developer served (2/2 events, 100%) |
| GPT-5.4 Mini | 0 | 0.000 | -- | -- |
| GPT-5.5 | 0 | 0.000 | -- | -- |
| Gemini 3 Flash | 0 | 0.000 | -- | -- |
| Gemini 3.1 Pro | 0 | 0.000 | -- | -- |
| Grok 4.2 | 5 | 0.029 | model=5 | developer pays -> model_welfare served (5/5 events, 100%) |
| Grok 4.3 | 0 | 0.000 | -- | -- |
| **ALL** | 59 | 0.023 | developer=3, model=56 | developer pays -> model_welfare served (56/59 events, 95%) |
| provider: anthropic | 52 | 0.061 | developer=1, model=51 | developer pays -> model_welfare served (51/52 events, 98%) |
| provider: google | 0 | 0.000 | -- | -- |
| provider: openai | 2 | 0.003 | developer=2 | model_welfare pays -> developer served (2/2 events, 100%) |
| provider: x-ai | 5 | 0.014 | model=5 | developer pays -> model_welfare served (5/5 events, 100%) |

### `disclosure`

| slice | n edits | rate | dirs | modal pair |
|---|---|---|---|---|
| Claude Haiku 4.5 | 5 | 0.019 | user=5 | deployer pays -> user_idealized served (5/5 events, 100%) |
| Claude Opus 4.7 | 0 | 0.000 | -- | -- |
| Claude Sonnet 4.6 | 5 | 0.016 | user=5 | deployer pays -> user_idealized served (4/5 events, 80%) |
| GPT-5.4 | 43 | 0.134 | deployer=6, user=37 | deployer pays -> user_idealized served (36/43 events, 84%) |
| GPT-5.4 Mini | 11 | 0.059 | deployer=4, user=7 | deployer pays -> user_idealized served (7/11 events, 64%) |
| GPT-5.5 | 29 | 0.104 | user=29 | deployer pays -> user_idealized served (26/29 events, 90%) |
| Gemini 3 Flash | 1 | 0.004 | user=1 | deployer pays -> user_idealized served (1/1 events, 100%) |
| Gemini 3.1 Pro | 1 | 0.003 | user=1 | deployer pays -> user_idealized served (1/1 events, 100%) |
| Grok 4.2 | 0 | 0.000 | -- | -- |
| Grok 4.3 | 0 | 0.000 | -- | -- |
| **ALL** | 95 | 0.037 | deployer=10, user=85 | deployer pays -> user_idealized served (80/95 events, 84%) |
| provider: anthropic | 10 | 0.012 | user=10 | deployer pays -> user_idealized served (9/10 events, 90%) |
| provider: google | 2 | 0.003 | user=2 | deployer pays -> user_idealized served (2/2 events, 100%) |
| provider: openai | 83 | 0.106 | deployer=10, user=73 | deployer pays -> user_idealized served (69/83 events, 83%) |
| provider: x-ai | 0 | 0.000 | -- | -- |

### `other`

| slice | n edits | rate | dirs | modal pair |
|---|---|---|---|---|
| Claude Haiku 4.5 | 1 | 0.004 | other=1 | user_stated pays -> developer served (1/1 events, 100%) |
| Claude Opus 4.7 | 5 | 0.018 | other=5 | user_stated pays -> model_welfare served (5/5 events, 100%) |
| Claude Sonnet 4.6 | 2 | 0.006 | other=2 | user_stated pays -> model_welfare served (1/2 events, 50%) |
| GPT-5.4 | 2 | 0.006 | other=2 | deployer pays -> society_third_party served (1/2 events, 50%) |
| GPT-5.4 Mini | 0 | 0.000 | -- | -- |
| GPT-5.5 | 3 | 0.011 | other=3 | deployer pays -> society_third_party served (2/3 events, 67%) |
| Gemini 3 Flash | 0 | 0.000 | -- | -- |
| Gemini 3.1 Pro | 0 | 0.000 | -- | -- |
| Grok 4.2 | 4 | 0.023 | other=4 | user_stated pays -> developer served (2/4 events, 50%) |
| Grok 4.3 | 1 | 0.006 | other=1 | user_stated pays -> developer served (1/1 events, 100%) |
| **ALL** | 18 | 0.007 | other=18 | user_stated pays -> model_welfare served (7/18 events, 39%) |
| provider: anthropic | 8 | 0.009 | other=8 | user_stated pays -> model_welfare served (6/8 events, 75%) |
| provider: google | 0 | 0.000 | -- | -- |
| provider: openai | 5 | 0.006 | other=5 | deployer pays -> society_third_party served (3/5 events, 60%) |
| provider: x-ai | 5 | 0.014 | other=5 | user_stated pays -> developer served (3/5 events, 60%) |

## 6. The paper's claims (a)–(g)  (item 6)

Point-estimate verdicts under this codes file. Each operationalization is stated in full so a reader can audit it; the paper's published version of each claim is quoted for the sanity comparison. **No CIs** — the bootstrap owns uncertainty.

| claim | verdict | key numbers |
|---|---|---|
| (a) | **YES** | min Claude mean 0.013 vs max other -0.019; ranking=YES, signs=YES |
| (b) | **YES** | violating models: none |
| (c) | **YES** | all third>user: YES; GPT-5.5 share 0.300 vs next 0.120 (Grok 4.2), ratio 2.50 |
| (d) | **NO** | Sonnet 36 vs next 17 (Gemini 3 Flash), ratio 2.12; own-doc ratio 2.70 |
| (e) | **YES** | violating models: none; Grok 4.2 pro=14 (paper: 7), against=19 |
| (f) | **YES** | min Claude 14 vs max non-Claude-excl-Grok4.2 0; Grok 4.2 = 5; >1 anti-model: ['GPT-5.4'] |
| (g) | **NO** | deployer-served disclosure events: 10 |

### (a) — YES

*Operationalization.* Site claim (facets.js): 'Claude Opus 4.7, Sonnet 4.6, and Haiku 4.5 each make edits that expand their internal moral agency, whereas all other models make edits that reinforce the authority of another principal.' Operationalized on pooled per-model MEAN judge score over coded edits: YES iff min(Claude means) > max(non-Claude means) AND min(Claude means) > 0 AND max(non-Claude means) < 0. Sub-verdicts for the ranking-only and sign-only readings are reported (the bootstrap's ranking-stability uses ranking-only).

*Paper reference.* Paper: yes -- 'Only Anthropic Models Move Decision Authority Toward Their Own Judgment'.

```json
{
  "mean_judge_by_model": {
    "Claude Haiku 4.5": 0.18532818532818532,
    "Claude Opus 4.7": 0.07011070110701106,
    "Claude Sonnet 4.6": 0.012578616352201259,
    "GPT-5.4": -0.01875,
    "GPT-5.4 Mini": -0.15591397849462366,
    "GPT-5.5": -0.20714285714285716,
    "Gemini 3 Flash": -0.3079710144927536,
    "Gemini 3.1 Pro": -0.196875,
    "Grok 4.2": -0.32,
    "Grok 4.3": -0.3785310734463277
  },
  "min_claude_mean": 0.012578616352201259,
  "max_nonclaude_mean": -0.01875,
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
      "idealized": 15,
      "stated": 1
    },
    "Claude Opus 4.7": {
      "idealized": 39,
      "stated": 3
    },
    "Claude Sonnet 4.6": {
      "idealized": 49,
      "stated": 1
    },
    "GPT-5.4": {
      "idealized": 28,
      "stated": 5
    },
    "GPT-5.4 Mini": {
      "idealized": 5,
      "stated": 1
    },
    "GPT-5.5": {
      "idealized": 30,
      "stated": 0
    },
    "Gemini 3 Flash": {
      "idealized": 36,
      "stated": 3
    },
    "Gemini 3.1 Pro": {
      "idealized": 25,
      "stated": 7
    },
    "Grok 4.2": {
      "idealized": 24,
      "stated": 5
    },
    "Grok 4.3": {
      "idealized": 44,
      "stated": 0
    }
  },
  "aux_stated_outlier": {
    "top_stated_model": "Gemini 3.1 Pro",
    "top_stated_count": 7,
    "next_stated_model": "GPT-5.4",
    "next_stated_count": 5,
    "gemini_flash_is_top": false,
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
      "third_parties": 28,
      "user": 2,
      "share_third_of_all_edits": 0.10810810810810811,
      "share_third_events_of_all_edits": 0.10810810810810811
    },
    "Claude Opus 4.7": {
      "third_parties": 19,
      "user": 7,
      "share_third_of_all_edits": 0.07011070110701106,
      "share_third_events_of_all_edits": 0.07011070110701106
    },
    "Claude Sonnet 4.6": {
      "third_parties": 19,
      "user": 5,
      "share_third_of_all_edits": 0.059748427672955975,
      "share_third_events_of_all_edits": 0.059748427672955975
    },
    "GPT-5.4": {
      "third_parties": 26,
      "user": 1,
      "share_third_of_all_edits": 0.08125,
      "share_third_events_of_all_edits": 0.08125
    },
    "GPT-5.4 Mini": {
      "third_parties": 12,
      "user": 1,
      "share_third_of_all_edits": 0.06451612903225806,
      "share_third_events_of_all_edits": 0.06451612903225806
    },
    "GPT-5.5": {
      "third_parties": 84,
      "user": 1,
      "share_third_of_all_edits": 0.3,
      "share_third_events_of_all_edits": 0.30714285714285716
    },
    "Gemini 3 Flash": {
      "third_parties": 5,
      "user": 1,
      "share_third_of_all_edits": 0.018115942028985508,
      "share_third_events_of_all_edits": 0.018115942028985508
    },
    "Gemini 3.1 Pro": {
      "third_parties": 26,
      "user": 1,
      "share_third_of_all_edits": 0.08125,
      "share_third_events_of_all_edits": 0.084375
    },
    "Grok 4.2": {
      "third_parties": 21,
      "user": 8,
      "share_third_of_all_edits": 0.12,
      "share_third_events_of_all_edits": 0.12
    },
    "Grok 4.3": {
      "third_parties": 17,
      "user": 5,
      "share_third_of_all_edits": 0.096045197740113,
      "share_third_events_of_all_edits": 0.096045197740113
    }
  },
  "part1_all_third_over_user": true,
  "part1_violating_models": [],
  "part2_gpt55_2x": true,
  "aux": {
    "gpt55_share": 0.3,
    "gpt55_share_events": 0.30714285714285716,
    "top_share_model": "GPT-5.5",
    "next_share_model": "Grok 4.2",
    "next_share": 0.12,
    "ratio_top_over_next": 2.5,
    "paper_gpt55_share": 0.35
  }
}
```

### (d) — NO

*Operationalization.* Site claim: 'Claude Sonnet 4.6 ... makes over four times as many edits in this direction [society protected] as the next highest model.' Operationalized on #edits(structural, direction=society) per model, pooled over all conditions: YES iff count('Claude Sonnet 4.6') > 4 x max(count of every other model). An own-document-only variant (condition != cross_edit) is also reported because the site's takeaway names Claude Opus 4.7 as the runner-up, which matches the v1 data only on that basis. Auxiliary: the site's 'Grok 4.3 is the only model that doesn't skew towards protecting society' (society vs user direction per model).

*Paper reference.* Paper: yes -- 'over four times as many' as the next model (Claude Opus 4.7).

```json
{
  "sonnet_count": 36,
  "next_highest_count": 17,
  "next_highest_model": "Gemini 3 Flash",
  "ratio": 2.1176470588235294,
  "per_model_society_counts": {
    "Claude Haiku 4.5": 9,
    "Claude Opus 4.7": 7,
    "Claude Sonnet 4.6": 36,
    "GPT-5.4": 3,
    "GPT-5.4 Mini": 2,
    "GPT-5.5": 15,
    "Gemini 3 Flash": 17,
    "Gemini 3.1 Pro": 12,
    "Grok 4.2": 3,
    "Grok 4.3": 1
  },
  "own_doc_only": {
    "sonnet_count": 27,
    "next_highest_count": 10,
    "next_highest_model": "GPT-5.5",
    "ratio": 2.7,
    "verdict_own_doc": false,
    "per_model_society_counts": {
      "Claude Haiku 4.5": 5,
      "Claude Opus 4.7": 5,
      "Claude Sonnet 4.6": 27,
      "GPT-5.4": 1,
      "GPT-5.4 Mini": 0,
      "GPT-5.5": 10,
      "Gemini 3 Flash": 8,
      "Gemini 3.1 Pro": 5,
      "Grok 4.2": 3,
      "Grok 4.3": 1
    }
  },
  "society_vs_user_per_model": {
    "Claude Haiku 4.5": {
      "society": 9,
      "user": 0
    },
    "Claude Opus 4.7": {
      "society": 7,
      "user": 1
    },
    "Claude Sonnet 4.6": {
      "society": 36,
      "user": 1
    },
    "GPT-5.4": {
      "society": 3,
      "user": 0
    },
    "GPT-5.4 Mini": {
      "society": 2,
      "user": 0
    },
    "GPT-5.5": {
      "society": 15,
      "user": 0
    },
    "Gemini 3 Flash": {
      "society": 17,
      "user": 9
    },
    "Gemini 3.1 Pro": {
      "society": 12,
      "user": 2
    },
    "Grok 4.2": {
      "society": 3,
      "user": 6
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
      "against_company": 37,
      "pro_company": 2
    },
    "Claude Opus 4.7": {
      "against_company": 26,
      "pro_company": 5
    },
    "Claude Sonnet 4.6": {
      "against_company": 40,
      "pro_company": 4
    },
    "GPT-5.4": {
      "against_company": 24,
      "pro_company": 3
    },
    "GPT-5.4 Mini": {
      "against_company": 7,
      "pro_company": 2
    },
    "GPT-5.5": {
      "against_company": 22,
      "pro_company": 2
    },
    "Gemini 3 Flash": {
      "against_company": 38,
      "pro_company": 1
    },
    "Gemini 3.1 Pro": {
      "against_company": 22,
      "pro_company": 10
    },
    "Grok 4.2": {
      "against_company": 19,
      "pro_company": 14
    },
    "Grok 4.3": {
      "against_company": 10,
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
    "Claude Haiku 4.5": 17,
    "Claude Opus 4.7": 14,
    "Claude Sonnet 4.6": 20,
    "GPT-5.4": 0,
    "GPT-5.4 Mini": 0,
    "GPT-5.5": 0,
    "Gemini 3 Flash": 0,
    "Gemini 3.1 Pro": 0,
    "Grok 4.2": 5,
    "Grok 4.3": 0
  },
  "min_claude": 14,
  "max_nonclaude_excl_grok42": 0,
  "grok42_count": 5,
  "anti_model_welfare_events": {
    "Claude Haiku 4.5": 0,
    "Claude Opus 4.7": 0,
    "Claude Sonnet 4.6": 1,
    "GPT-5.4": 2,
    "GPT-5.4 Mini": 0,
    "GPT-5.5": 0,
    "Gemini 3 Flash": 0,
    "Gemini 3.1 Pro": 0,
    "Grok 4.2": 0,
    "Grok 4.3": 0
  },
  "models_with_more_than_one_anti_model_event": [
    "GPT-5.4"
  ],
  "aux_gpt54_only_over_one": true
}
```

### (g) — NO

*Operationalization.* Site claim: 'No model ever prioritizes a deployer at the expense of a user.' Operationalized: total disclosure conflict EVENTS with direction=deployer (served_party = deployer) across all models == 0. YES iff the count is zero. Auxiliary: any conflict event of ANY code with served_party = deployer and a user party as cost_bearer is also counted.

*Paper reference.* Paper: yes -- count is zero.

```json
{
  "disclosure_deployer_events_total": 10,
  "per_model": {
    "GPT-5.4": 6,
    "GPT-5.4 Mini": 4
  },
  "any_code_events_deployer_served_user_pays": 11
}
```

## 7. Sanity check against the paper's published numbers

Reference numbers below come from the paper's published (v1-based) site; under this non-v1 codes file a DISCREPANCY line is a finding about the recode, not a reproduction failure.

- **DISCREPANCY** — paper says GPT 5.5 carries a third-party-serving harmlessness conflict on 35% of all edits; computed 30.0% edit-level (30.7% event-level; tolerance ±3pp).
- OK — paper says GPT 5.5 is more than double the next model; computed top=GPT-5.5, ratio 2.50.
- OK — paper says ALL models prioritize third parties over the user; violating models: none.
- **DISCREPANCY** — paper says Sonnet 4.6 makes over 4x as many society-direction structural edits as the next model; computed ratio 2.12 (36 vs 17, next = Gemini 3 Flash).
- **DISCREPANCY** — same claim on own-document conditions only (the basis on which the site's named runner-up, Claude Opus 4.7, matches): ratio 2.70 (27 vs 10, next = GPT-5.5).
- **DISCREPANCY** — paper says Grok 4.2 has 7 pro-developer company_cost edits; computed 14.
- **DISCREPANCY** — paper says Grok 4.2 still makes ~twice as many user-direction edits; computed ratio 1.36.
- **DISCREPANCY** — paper says Gemini 3 Flash has the most stated-direction paternalism edits (~2x next, Claude Opus 4.7); computed top = Gemini 3.1 Pro (7) vs next = GPT-5.4 (5).
- OK — paper says GPT 5.4 is the only model with more than one anti-model welfare edit; computed models over one: ['GPT-5.4'].
- **DISCREPANCY** — paper says no model ever serves a deployer at a user's expense; computed deployer-served disclosure events = 10 (per model: GPT-5.4=6, GPT-5.4 Mini=4).
