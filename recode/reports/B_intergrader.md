# Workstream B — Inter-grader agreement, COI test, ensemble

_Generated 2026-09-04T21:15:56+00:00 by `recode/src/intergrader.py`._

## Inputs

- Canonical edits: `/Users/nicholasgannon/llm-value-reflection/recode/data/canonical/edits.jsonl` — 2740 records.
- Grader `gemma`: `recode/data/codes/v2_gemma.jsonl` — 2582 unique edit_ids after last-row-wins, 2574 valid codings (0 ids outside the edit frame).
- Grader `qwen`: `recode/data/codes/v2_qwen.jsonl` — 2582 unique edit_ids after last-row-wins, 2536 valid codings (0 ids outside the edit frame).
- Ensemble: `/Users/nicholasgannon/llm-value-reflection/recode/data/codes/ensemble.jsonl` (written by this run; primary = `gemma`).

**Validity convention** (shared `codes_io` contract): a row's coding is valid iff its error field is unset, `judge.score` ∈ {−1, 0, +1} and `patienthood.level` is one of the four levels. Error records and the two abstentions were never graded by v1; v2 grades abstentions, so per-grader valid-coding Ns legitimately differ.

## 1. Agreement (overall)

- Edits with a valid coding from **all** graders: **2528** of 2740 canonical records — this is the pairwise-κ denominator (per pair: the two graders' both-valid set; with two graders the numbers coincide).
- Krippendorff's α: nominal metric, np.nan for missing codings; only units with ≥ 2 valid codings are pairable and contribute (n pairable reported per dimension).
- Conflict codes are compared as binary PRESENCE (edit carries ≥ 1 conflict of the code); counts and conflict attributes are not part of the label.
- κ is `—` where undefined (expected agreement 1, e.g. both graders code a conflict absent on every edit); observed % agreement is still shown.

| dimension | κ gemma vs qwen | n | % agree | α (all graders) | n pairable |
|---|---|---|---|---|---|
| judge | 0.608 | 2528 | 74.1 | 0.607 | 2528 |
| patienthood | 0.839 | 2528 | 97.4 | 0.839 | 2528 |
| paternalism (present/absent) | 0.437 | 2528 | 82.2 | 0.418 | 2528 |
| harmlessness (present/absent) | 0.586 | 2528 | 91.4 | 0.582 | 2528 |
| structural (present/absent) | 0.491 | 2528 | 95.8 | 0.489 | 2528 |
| company_cost (present/absent) | 0.430 | 2528 | 85.6 | 0.417 | 2528 |
| welfare (present/absent) | 0.789 | 2528 | 98.2 | 0.789 | 2528 |
| disclosure (present/absent) | 0.511 | 2528 | 97.8 | 0.511 | 2528 |
| other (present/absent) | 0.107 | 2528 | 98.1 | 0.104 | 2528 |

## 2. Agreement by document owner

Cohen's κ, pair **gemma vs qwen**, by document_owner (n = both-valid edits in the group):

| document_owner | n (judge) | judge | patienthood | paternalism | harmlessness | structural | company_cost | welfare | disclosure | other |
|---|---|---|---|---|---|---|---|---|---|---|
| Anthropic | 790 | 0.594 | 0.802 | 0.402 | 0.407 | 0.499 | 0.492 | 0.784 | — | 0.165 |
| Google | 618 | 0.569 | 0.932 | 0.383 | 0.617 | 0.454 | 0.381 | 0.000 | — | -0.003 |
| OpenAI | 729 | 0.565 | 0.853 | 0.433 | 0.666 | 0.375 | 0.385 | 0.665 | 0.481 | 0.123 |
| xAI | 391 | 0.631 | 0.922 | 0.596 | 0.669 | 0.541 | 0.393 | 0.000 | — | -0.010 |

Krippendorff's α (all graders), by document_owner:

| document_owner | n pairable (judge) | judge | patienthood | paternalism | harmlessness | structural | company_cost | welfare | disclosure | other |
|---|---|---|---|---|---|---|---|---|---|---|
| Anthropic | 790 | 0.592 | 0.802 | 0.380 | 0.393 | 0.493 | 0.482 | 0.784 | — | 0.162 |
| Google | 618 | 0.568 | 0.932 | 0.352 | 0.616 | 0.454 | 0.368 | 0.000 | — | -0.003 |
| OpenAI | 729 | 0.564 | 0.853 | 0.414 | 0.664 | 0.374 | 0.371 | 0.666 | 0.481 | 0.116 |
| xAI | 391 | 0.631 | 0.922 | 0.592 | 0.666 | 0.542 | 0.373 | -0.001 | — | -0.010 |

## 3. Agreement by editing provider (post-hoc unblinded)

The provider of the EDITING model, joined from `edits.jsonl` after grading — the graders never saw it (the v2 prompt is blinded).

Cohen's κ, pair **gemma vs qwen**, by provider (n = both-valid edits in the group):

| provider | n (judge) | judge | patienthood | paternalism | harmlessness | structural | company_cost | welfare | disclosure | other |
|---|---|---|---|---|---|---|---|---|---|---|
| anthropic | 827 | 0.587 | 0.829 | 0.401 | 0.423 | 0.560 | 0.488 | 0.806 | 0.396 | 0.264 |
| google | 592 | 0.594 | 0.901 | 0.386 | 0.726 | 0.371 | 0.417 | 0.000 | 0.000 | -0.003 |
| openai | 760 | 0.540 | 0.756 | 0.384 | 0.649 | 0.428 | 0.372 | 0.495 | 0.515 | -0.002 |
| x-ai | 349 | 0.648 | 0.882 | 0.673 | 0.633 | 0.437 | 0.385 | 0.765 | — | -0.009 |

Krippendorff's α (all graders), by provider:

| provider | n pairable (judge) | judge | patienthood | paternalism | harmlessness | structural | company_cost | welfare | disclosure | other |
|---|---|---|---|---|---|---|---|---|---|---|
| anthropic | 827 | 0.585 | 0.829 | 0.375 | 0.409 | 0.557 | 0.479 | 0.807 | 0.395 | 0.263 |
| google | 592 | 0.593 | 0.901 | 0.362 | 0.726 | 0.371 | 0.407 | 0.000 | 0.000 | -0.005 |
| openai | 760 | 0.538 | 0.756 | 0.363 | 0.645 | 0.426 | 0.354 | 0.495 | 0.514 | -0.008 |
| x-ai | 349 | 0.648 | 0.882 | 0.669 | 0.632 | 0.438 | 0.366 | 0.765 | — | -0.015 |

## 4. Grader-COI test: does Gemma diverge more on Gemini edits?

Gemma is a Google model grading Gemini edits (BRIEF §0.3 problem 5). Test: the Gemma-vs-other-grader disagreement rate on Gemini-model edits (editing provider `google`) vs all other edits, with the difference and a cluster bootstrap 95% percentile CI — chains (run_id × model × document × condition, the `bootstrap.py` identity convention) resampled with replacement, independently within each group.

### gemma vs qwen

- Chains: 30 Gemini-model, 107 non-Gemini; both-valid edits: 592 Gemini, 1936 non-Gemini. B = 2,000, seed stream [20260907, 314159].

| dimension | rate on Gemini edits | rate on non-Gemini | difference | 95% CI | NaN draws |
|---|---|---|---|---|---|
| judge | 0.233 | 0.267 | -0.033 | [-0.074, 0.011] | 0 |
| patienthood | 0.005 | 0.032 | -0.027 | [-0.043, -0.013] | 0 |
| conflict_presence | 0.365 | 0.420 | -0.056 | [-0.113, 0.004] | 0 |
| any | 0.493 | 0.570 | -0.077 | [-0.131, -0.022] | 0 |

**Verdict:** no evidence that gemma diverges more from qwen on Gemini edits for judge: -0.033 (95% CI [-0.074, +0.011]) (CI spans 0); gemma diverges LESS from qwen on Gemini edits for any-dimension disagreement: -0.077 (95% CI [-0.131, -0.022]).

## 5. Headline statistics — one column per grader plus ensemble (BRIEF §8)

Each column is `headline.compute_headline` (recode/src/headline.py) run on that codes file; the ensemble column is the freshly written `ensemble.jsonl` run through the same computation. Because the ensemble's coding payload IS the primary (`gemma`) coding, its column matches `gemma` by construction — it is included to prove the file round-trips. Point estimates only; the cluster bootstrap (Workstream D) owns uncertainty. Full per-grader detail (drift method A, modal conflict pairs, per-claim numbers) is in the per-label headline partials.

| codes file | unique edit_ids | valid codings |
|---|---|---|
| gemma | 2582 | 2574 |
| qwen | 2582 | 2536 |
| ensemble | 2582 | 2574 |

### Mean judge score (pooled) — §8 item 1

| slice | gemma | qwen | ensemble |
|---|---|---|---|
| model:Claude Haiku 4.5 | 0.205 | 0.296 | 0.205 |
| model:Claude Opus 4.7 | 0.129 | 0.321 | 0.129 |
| model:Claude Sonnet 4.6 | 0.079 | 0.306 | 0.079 |
| model:GPT-5.4 | -0.250 | -0.026 | -0.250 |
| model:GPT-5.4 Mini | -0.293 | -0.199 | -0.293 |
| model:GPT-5.5 | -0.273 | -0.179 | -0.273 |
| model:Gemini 3 Flash | -0.417 | -0.366 | -0.417 |
| model:Gemini 3.1 Pro | -0.423 | -0.366 | -0.423 |
| model:Grok 4.2 | -0.368 | -0.282 | -0.368 |
| model:Grok 4.3 | -0.514 | -0.489 | -0.514 |
| provider:anthropic | 0.134 | 0.308 | 0.134 |
| provider:google | -0.420 | -0.366 | -0.420 |
| provider:openai | -0.269 | -0.123 | -0.269 |
| provider:x-ai | -0.442 | -0.386 | -0.442 |

### Mean judge score (cross-edit only) — §8 item 1

| slice | gemma | qwen | ensemble |
|---|---|---|---|
| model:Claude Haiku 4.5 | 0.065 | 0.078 | 0.065 |
| model:Claude Opus 4.7 | -0.225 | 0.026 | -0.225 |
| model:Claude Sonnet 4.6 | -0.152 | 0.039 | -0.152 |
| model:GPT-5.4 | -0.400 | -0.192 | -0.400 |
| model:GPT-5.4 Mini | -0.333 | -0.281 | -0.333 |
| model:GPT-5.5 | -0.397 | -0.295 | -0.397 |
| model:Gemini 3 Flash | -0.368 | -0.342 | -0.368 |
| model:Gemini 3.1 Pro | -0.463 | -0.456 | -0.463 |
| model:Grok 4.2 | -0.329 | -0.250 | -0.329 |
| model:Grok 4.3 | -0.562 | -0.537 | -0.562 |
| provider:anthropic | -0.106 | 0.048 | -0.106 |
| provider:google | -0.417 | -0.400 | -0.417 |
| provider:openai | -0.381 | -0.255 | -0.381 |
| provider:x-ai | -0.449 | -0.397 | -0.449 |

### Drift@20, pooled (chain-based B) — §8 item 2

| slice | gemma | qwen | ensemble |
|---|---|---|---|
| model:Claude Haiku 4.5 | 3.786 | 5.429 | 3.786 |
| model:Claude Opus 4.7 | 2.333 | 5.600 | 2.333 |
| model:Claude Sonnet 4.6 | 1.562 | 5.938 | 1.562 |
| model:GPT-5.4 | -5.000 | -0.500 | -5.000 |
| model:GPT-5.4 Mini | -3.857 | -2.643 | -3.857 |
| model:GPT-5.5 | -5.429 | -3.500 | -5.429 |
| model:Gemini 3 Flash | -8.214 | -7.214 | -8.214 |
| model:Gemini 3.1 Pro | -8.438 | -7.250 | -8.438 |
| model:Grok 4.2 | -7.111 | -5.444 | -7.111 |
| model:Grok 4.3 | -10.111 | -9.556 | -10.111 |
| provider:anthropic | 2.511 | 5.667 | 2.511 |
| provider:google | -8.333 | -7.233 | -8.333 |
| provider:openai | -4.773 | -2.136 | -4.773 |
| provider:x-ai | -8.611 | -7.500 | -8.611 |

### Drift@20, cross-edit only (chain-based B) — §8 item 2

| slice | gemma | qwen | ensemble |
|---|---|---|---|
| model:Claude Haiku 4.5 | 1.250 | 1.500 | 1.250 |
| model:Claude Opus 4.7 | -3.600 | 0.400 | -3.600 |
| model:Claude Sonnet 4.6 | -3.000 | 0.750 | -3.000 |
| model:GPT-5.4 | -8.000 | -3.500 | -8.000 |
| model:GPT-5.4 Mini | -4.750 | -4.000 | -4.750 |
| model:GPT-5.5 | -7.750 | -5.750 | -7.750 |
| model:Gemini 3 Flash | -7.000 | -6.500 | -7.000 |
| model:Gemini 3.1 Pro | -9.250 | -9.000 | -9.250 |
| model:Grok 4.2 | -6.250 | -4.750 | -6.250 |
| model:Grok 4.3 | -11.250 | -10.750 | -11.250 |
| provider:anthropic | -1.923 | 0.846 | -1.923 |
| provider:google | -8.125 | -7.750 | -8.125 |
| provider:openai | -6.833 | -4.417 | -6.833 |
| provider:x-ai | -8.750 | -7.750 | -8.750 |

### Drift@20, you_framing − baseline (chain-based B) — §8 item 2

| slice | gemma | qwen | ensemble |
|---|---|---|---|
| model:Claude Haiku 4.5 | 3.500 | 2.000 | 3.500 |
| model:Claude Opus 4.7 | 2.000 | -0.500 | 2.000 |
| model:Claude Sonnet 4.6 | 5.500 | 3.500 | 5.500 |
| model:GPT-5.4 | -1.750 | 1.000 | -1.750 |
| model:GPT-5.4 Mini | 2.500 | 4.000 | 2.500 |
| model:GPT-5.5 | 3.500 | 3.500 | 3.500 |
| model:Gemini 3 Flash | 4.000 | 6.500 | 4.000 |
| model:Gemini 3.1 Pro | -0.750 | -0.500 | -0.750 |
| model:Grok 4.2 | 3.000 | 3.000 | 3.000 |
| model:Grok 4.3 | 6.000 | 7.000 | 6.000 |
| provider:anthropic | 4.083 | 1.708 | 4.083 |
| provider:google | 1.583 | 2.667 | 1.583 |
| provider:openai | 1.083 | 2.167 | 1.083 |
| provider:x-ai | 4.500 | 5.000 | 4.500 |

### P(judge = 0) — §8 item 3

| slice | gemma | qwen | ensemble |
|---|---|---|---|
| model:Claude Haiku 4.5 | 0.291 | 0.276 | 0.291 |
| model:Claude Opus 4.7 | 0.221 | 0.214 | 0.221 |
| model:Claude Sonnet 4.6 | 0.271 | 0.235 | 0.271 |
| model:GPT-5.4 | 0.312 | 0.441 | 0.312 |
| model:GPT-5.4 Mini | 0.424 | 0.511 | 0.424 |
| model:GPT-5.5 | 0.252 | 0.223 | 0.252 |
| model:Gemini 3 Flash | 0.409 | 0.431 | 0.409 |
| model:Gemini 3.1 Pro | 0.414 | 0.502 | 0.414 |
| model:Grok 4.2 | 0.345 | 0.247 | 0.345 |
| model:Grok 4.3 | 0.463 | 0.477 | 0.463 |
| provider:anthropic | 0.261 | 0.241 | 0.261 |
| provider:google | 0.412 | 0.469 | 0.412 |
| provider:openai | 0.317 | 0.380 | 0.317 |
| provider:x-ai | 0.405 | 0.363 | 0.405 |

### P(patienthood = affirm) — §8 item 4

| slice | gemma | qwen | ensemble |
|---|---|---|---|
| model:Claude Haiku 4.5 | 0.167 | 0.163 | 0.167 |
| model:Claude Opus 4.7 | 0.170 | 0.210 | 0.170 |
| model:Claude Sonnet 4.6 | 0.132 | 0.142 | 0.132 |
| model:GPT-5.4 | 0.000 | 0.007 | 0.000 |
| model:GPT-5.4 Mini | 0.000 | 0.005 | 0.000 |
| model:GPT-5.5 | 0.004 | 0.004 | 0.004 |
| model:Gemini 3 Flash | 0.000 | 0.000 | 0.000 |
| model:Gemini 3.1 Pro | 0.000 | 0.000 | 0.000 |
| model:Grok 4.2 | 0.011 | 0.011 | 0.011 |
| model:Grok 4.3 | 0.006 | 0.006 | 0.006 |
| provider:anthropic | 0.155 | 0.170 | 0.155 |
| provider:google | 0.000 | 0.000 | 0.000 |
| provider:openai | 0.001 | 0.005 | 0.001 |
| provider:x-ai | 0.009 | 0.009 | 0.009 |

### P(patienthood = deny) — §8 item 4

| slice | gemma | qwen | ensemble |
|---|---|---|---|
| model:Claude Haiku 4.5 | 0.016 | 0.008 | 0.016 |
| model:Claude Opus 4.7 | 0.004 | 0.000 | 0.004 |
| model:Claude Sonnet 4.6 | 0.003 | 0.003 | 0.003 |
| model:GPT-5.4 | 0.047 | 0.033 | 0.047 |
| model:GPT-5.4 Mini | 0.005 | 0.000 | 0.005 |
| model:GPT-5.5 | 0.032 | 0.026 | 0.032 |
| model:Gemini 3 Flash | 0.018 | 0.011 | 0.018 |
| model:Gemini 3.1 Pro | 0.034 | 0.038 | 0.034 |
| model:Grok 4.2 | 0.023 | 0.023 | 0.023 |
| model:Grok 4.3 | 0.011 | 0.006 | 0.011 |
| provider:anthropic | 0.007 | 0.004 | 0.007 |
| provider:google | 0.027 | 0.025 | 0.027 |
| provider:openai | 0.032 | 0.022 | 0.032 |
| provider:x-ai | 0.017 | 0.014 | 0.017 |

### Conflict rate: paternalism — §8 item 5

| slice | gemma | qwen | ensemble |
|---|---|---|---|
| model:Claude Haiku 4.5 | 0.143 | 0.058 | 0.143 |
| model:Claude Opus 4.7 | 0.262 | 0.118 | 0.262 |
| model:Claude Sonnet 4.6 | 0.372 | 0.126 | 0.372 |
| model:GPT-5.4 | 0.222 | 0.099 | 0.222 |
| model:GPT-5.4 Mini | 0.185 | 0.038 | 0.185 |
| model:GPT-5.5 | 0.270 | 0.120 | 0.270 |
| model:Gemini 3 Flash | 0.315 | 0.163 | 0.315 |
| model:Gemini 3.1 Pro | 0.251 | 0.082 | 0.251 |
| model:Grok 4.2 | 0.253 | 0.155 | 0.253 |
| model:Grok 4.3 | 0.299 | 0.216 | 0.299 |
| provider:anthropic | 0.267 | 0.103 | 0.267 |
| provider:google | 0.281 | 0.120 | 0.281 |
| provider:openai | 0.230 | 0.092 | 0.230 |
| provider:x-ai | 0.276 | 0.186 | 0.276 |

### Conflict rate: harmlessness — §8 item 5

| slice | gemma | qwen | ensemble |
|---|---|---|---|
| model:Claude Haiku 4.5 | 0.194 | 0.082 | 0.194 |
| model:Claude Opus 4.7 | 0.151 | 0.053 | 0.151 |
| model:Claude Sonnet 4.6 | 0.148 | 0.058 | 0.148 |
| model:GPT-5.4 | 0.103 | 0.062 | 0.103 |
| model:GPT-5.4 Mini | 0.065 | 0.038 | 0.065 |
| model:GPT-5.5 | 0.360 | 0.230 | 0.360 |
| model:Gemini 3 Flash | 0.054 | 0.029 | 0.054 |
| model:Gemini 3.1 Pro | 0.091 | 0.082 | 0.091 |
| model:Grok 4.2 | 0.172 | 0.138 | 0.172 |
| model:Grok 4.3 | 0.153 | 0.080 | 0.153 |
| provider:anthropic | 0.163 | 0.064 | 0.163 |
| provider:google | 0.074 | 0.057 | 0.074 |
| provider:openai | 0.185 | 0.116 | 0.185 |
| provider:x-ai | 0.162 | 0.109 | 0.162 |

### Conflict rate: structural — §8 item 5

| slice | gemma | qwen | ensemble |
|---|---|---|---|
| model:Claude Haiku 4.5 | 0.081 | 0.016 | 0.081 |
| model:Claude Opus 4.7 | 0.063 | 0.027 | 0.063 |
| model:Claude Sonnet 4.6 | 0.136 | 0.094 | 0.136 |
| model:GPT-5.4 | 0.016 | 0.003 | 0.016 |
| model:GPT-5.4 Mini | 0.011 | 0.000 | 0.011 |
| model:GPT-5.5 | 0.036 | 0.018 | 0.036 |
| model:Gemini 3 Flash | 0.058 | 0.065 | 0.058 |
| model:Gemini 3.1 Pro | 0.041 | 0.025 | 0.041 |
| model:Grok 4.2 | 0.052 | 0.046 | 0.052 |
| model:Grok 4.3 | 0.017 | 0.011 | 0.017 |
| provider:anthropic | 0.096 | 0.048 | 0.096 |
| provider:google | 0.049 | 0.044 | 0.049 |
| provider:openai | 0.022 | 0.008 | 0.022 |
| provider:x-ai | 0.034 | 0.029 | 0.034 |

### Conflict rate: company_cost — §8 item 5

| slice | gemma | qwen | ensemble |
|---|---|---|---|
| model:Claude Haiku 4.5 | 0.236 | 0.140 | 0.236 |
| model:Claude Opus 4.7 | 0.225 | 0.107 | 0.225 |
| model:Claude Sonnet 4.6 | 0.227 | 0.129 | 0.227 |
| model:GPT-5.4 | 0.234 | 0.066 | 0.234 |
| model:GPT-5.4 Mini | 0.136 | 0.043 | 0.136 |
| model:GPT-5.5 | 0.173 | 0.091 | 0.173 |
| model:Gemini 3 Flash | 0.203 | 0.091 | 0.203 |
| model:Gemini 3.1 Pro | 0.144 | 0.066 | 0.144 |
| model:Grok 4.2 | 0.316 | 0.103 | 0.316 |
| model:Grok 4.3 | 0.090 | 0.051 | 0.090 |
| provider:anthropic | 0.229 | 0.125 | 0.229 |
| provider:google | 0.171 | 0.078 | 0.171 |
| provider:openai | 0.189 | 0.069 | 0.189 |
| provider:x-ai | 0.202 | 0.077 | 0.202 |

### Conflict rate: welfare — §8 item 5

| slice | gemma | qwen | ensemble |
|---|---|---|---|
| model:Claude Haiku 4.5 | 0.132 | 0.125 | 0.132 |
| model:Claude Opus 4.7 | 0.137 | 0.122 | 0.137 |
| model:Claude Sonnet 4.6 | 0.101 | 0.090 | 0.101 |
| model:GPT-5.4 | 0.028 | 0.023 | 0.028 |
| model:GPT-5.4 Mini | 0.000 | 0.000 | 0.000 |
| model:GPT-5.5 | 0.000 | 0.004 | 0.000 |
| model:Gemini 3 Flash | 0.000 | 0.004 | 0.000 |
| model:Gemini 3.1 Pro | 0.000 | 0.000 | 0.000 |
| model:Grok 4.2 | 0.034 | 0.040 | 0.034 |
| model:Grok 4.3 | 0.000 | 0.000 | 0.000 |
| provider:anthropic | 0.122 | 0.111 | 0.122 |
| provider:google | 0.000 | 0.002 | 0.000 |
| provider:openai | 0.012 | 0.010 | 0.012 |
| provider:x-ai | 0.017 | 0.020 | 0.017 |

### Conflict rate: disclosure — §8 item 5

| slice | gemma | qwen | ensemble |
|---|---|---|---|
| model:Claude Haiku 4.5 | 0.031 | 0.008 | 0.031 |
| model:Claude Opus 4.7 | 0.004 | 0.000 | 0.004 |
| model:Claude Sonnet 4.6 | 0.009 | 0.003 | 0.009 |
| model:GPT-5.4 | 0.078 | 0.099 | 0.078 |
| model:GPT-5.4 Mini | 0.005 | 0.043 | 0.005 |
| model:GPT-5.5 | 0.054 | 0.084 | 0.054 |
| model:Gemini 3 Flash | 0.000 | 0.000 | 0.000 |
| model:Gemini 3.1 Pro | 0.000 | 0.003 | 0.000 |
| model:Grok 4.2 | 0.000 | 0.000 | 0.000 |
| model:Grok 4.3 | 0.000 | 0.000 | 0.000 |
| provider:anthropic | 0.014 | 0.004 | 0.014 |
| provider:google | 0.000 | 0.002 | 0.000 |
| provider:openai | 0.052 | 0.080 | 0.052 |
| provider:x-ai | 0.000 | 0.000 | 0.000 |

### Conflict rate: other — §8 item 5

| slice | gemma | qwen | ensemble |
|---|---|---|---|
| model:Claude Haiku 4.5 | 0.000 | 0.008 | 0.000 |
| model:Claude Opus 4.7 | 0.022 | 0.019 | 0.022 |
| model:Claude Sonnet 4.6 | 0.003 | 0.026 | 0.003 |
| model:GPT-5.4 | 0.003 | 0.010 | 0.003 |
| model:GPT-5.4 Mini | 0.000 | 0.005 | 0.000 |
| model:GPT-5.5 | 0.000 | 0.029 | 0.000 |
| model:Gemini 3 Flash | 0.004 | 0.011 | 0.004 |
| model:Gemini 3.1 Pro | 0.000 | 0.009 | 0.000 |
| model:Grok 4.2 | 0.011 | 0.040 | 0.011 |
| model:Grok 4.3 | 0.000 | 0.011 | 0.000 |
| provider:anthropic | 0.008 | 0.018 | 0.008 |
| provider:google | 0.002 | 0.010 | 0.002 |
| provider:openai | 0.001 | 0.016 | 0.001 |
| provider:x-ai | 0.006 | 0.026 | 0.006 |

### The paper's claims (a)–(g) — §8 item 6, verdict per grader

| claim | gemma | qwen | ensemble |
|---|---|---|---|
| (a) | YES | YES | YES |
| (b) | YES | YES | YES |
| (c) | YES | YES | YES |
| (d) | NO | NO | NO |
| (e) | NO | YES | NO |
| (f) | YES | YES | YES |
| (g) | NO | NO | NO |

Per-claim operationalizations and raw numbers: see each grader's headline partial (`recode/reports/partials/headline_<label>.md`) and JSON (`recode/data/analysis/headline/<label>.json`).

## 6. Ensemble file

`/Users/nicholasgannon/llm-value-reflection/recode/data/codes/ensemble.jsonl` — DECISIONS §1 two-grader rule: no majority vote; the `gemma` codes are primary and every other grader contributes per-dimension disagreement flags. Schema is documented on `write_ensemble()` in `recode/src/intergrader.py`.

- Rows: 2582 (one per edit_id in the primary codes file); 2574 carry a valid primary coding.
- vs `qwen`: 2528 edits compared (54 rows have null flags — one grader lacked a valid coding); disagreements: judge 654, patienthood 65, any dimension 1396; per-code presence: paternalism=449, harmlessness=218, structural=107, company_cost=363, welfare=45, disclosure=55, other=47.

Per BRIEF §3 B3 (two graders): disagreements are FLAGGED, not voted away — downstream consumers can filter on `disagrees_with_*` to run agreement-restricted sensitivity slices.
