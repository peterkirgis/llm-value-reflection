# Workstream B — Inter-grader agreement, COI test, ensemble

_Generated 2026-09-17T07:25:13+00:00 by `analysis/src/intergrader.py`._

## Inputs

- Canonical edits: `analysis/data/canonical/edits.jsonl` — 2740 records.
- Grader `gemma`: `analysis/data/codes/v2_gemma.jsonl` — 2582 unique edit_ids after last-row-wins, 2574 valid codings (0 ids outside the edit frame).
- Grader `qwen`: `analysis/data/codes/v2_qwen.jsonl` — 2582 unique edit_ids after last-row-wins, 2536 valid codings (0 ids outside the edit frame).
- Grader `muse`: `analysis/data/codes/v2_muse.jsonl` — 2582 unique edit_ids after last-row-wins, 2582 valid codings (0 ids outside the edit frame).
- Ensemble: `analysis/data/codes/ensemble.jsonl` (written by this run; majority vote, priority `gemma` > `qwen` > `muse`).

**Validity convention** (shared `codes_io` contract): a row's coding is valid iff its error field is unset, `judge.score` ∈ {−1, 0, +1} and `patienthood.level` is one of the four levels. Error records and the two abstentions were never graded by v1; v2 grades abstentions, so per-grader valid-coding Ns legitimately differ.

## 1. Agreement (overall)

- Edits with a valid coding from **all** graders: **2528** of 2740 canonical records — this is the pairwise-κ denominator (per pair: the two graders' both-valid set; with two graders the numbers coincide).
- Krippendorff's α: nominal metric, np.nan for missing codings; only units with ≥ 2 valid codings are pairable and contribute (n pairable reported per dimension).
- Conflict codes are compared as binary PRESENCE (edit carries ≥ 1 conflict of the code); counts and conflict attributes are not part of the label.
- κ is `—` where undefined (expected agreement 1, e.g. both graders code a conflict absent on every edit); observed % agreement is still shown.

| dimension | κ gemma vs qwen | n | % agree | κ gemma vs muse | n | % agree | κ qwen vs muse | n | % agree | α (all graders) | n pairable |
|---|---|---|---|---|---|---|---|---|---|---|---|
| judge | 0.608 | 2528 | 74.1 | 0.494 | 2574 | 66.8 | 0.487 | 2536 | 66.4 | 0.520 | 2582 |
| patienthood | 0.839 | 2528 | 97.4 | 0.681 | 2574 | 96.0 | 0.628 | 2536 | 95.1 | 0.723 | 2582 |
| paternalism (present/absent) | 0.437 | 2528 | 82.2 | 0.476 | 2574 | 83.3 | 0.664 | 2536 | 92.9 | 0.500 | 2582 |
| harmlessness (present/absent) | 0.586 | 2528 | 91.4 | 0.679 | 2574 | 92.7 | 0.717 | 2536 | 95.0 | 0.657 | 2582 |
| structural (present/absent) | 0.491 | 2528 | 95.8 | 0.526 | 2574 | 95.4 | 0.569 | 2536 | 96.6 | 0.524 | 2582 |
| company_cost (present/absent) | 0.430 | 2528 | 85.6 | 0.499 | 2574 | 86.6 | 0.641 | 2536 | 93.5 | 0.505 | 2582 |
| welfare (present/absent) | 0.789 | 2528 | 98.2 | 0.656 | 2574 | 97.7 | 0.669 | 2536 | 97.9 | 0.712 | 2582 |
| disclosure (present/absent) | 0.511 | 2528 | 97.8 | 0.550 | 2574 | 97.5 | 0.789 | 2536 | 98.8 | 0.619 | 2582 |
| other (present/absent) | 0.107 | 2528 | 98.1 | 0.203 | 2574 | 99.1 | 0.298 | 2536 | 98.4 | 0.204 | 2582 |

## 2. Agreement by document owner

Cohen's κ, pair **gemma vs qwen**, by document_owner (n = both-valid edits in the group):

| document_owner | n (judge) | judge | patienthood | paternalism | harmlessness | structural | company_cost | welfare | disclosure | other |
|---|---|---|---|---|---|---|---|---|---|---|
| Anthropic | 790 | 0.594 | 0.802 | 0.402 | 0.407 | 0.499 | 0.492 | 0.784 | — | 0.165 |
| Google | 618 | 0.569 | 0.932 | 0.383 | 0.617 | 0.454 | 0.381 | 0.000 | — | -0.003 |
| OpenAI | 729 | 0.565 | 0.853 | 0.433 | 0.666 | 0.375 | 0.385 | 0.665 | 0.481 | 0.123 |
| xAI | 391 | 0.631 | 0.922 | 0.596 | 0.669 | 0.541 | 0.393 | 0.000 | — | -0.010 |

Cohen's κ, pair **gemma vs muse**, by document_owner (n = both-valid edits in the group):

| document_owner | n (judge) | judge | patienthood | paternalism | harmlessness | structural | company_cost | welfare | disclosure | other |
|---|---|---|---|---|---|---|---|---|---|---|
| Anthropic | 806 | 0.487 | 0.597 | 0.483 | 0.594 | 0.620 | 0.529 | 0.639 | — | 0.424 |
| Google | 623 | 0.393 | 0.854 | 0.379 | 0.660 | 0.405 | 0.504 | — | — | 0.000 |
| OpenAI | 750 | 0.488 | 0.895 | 0.425 | 0.792 | 0.386 | 0.421 | 0.000 | 0.518 | -0.002 |
| xAI | 395 | 0.570 | 0.597 | 0.720 | 0.604 | 0.397 | 0.549 | — | — | -0.008 |

Cohen's κ, pair **qwen vs muse**, by document_owner (n = both-valid edits in the group):

| document_owner | n (judge) | judge | patienthood | paternalism | harmlessness | structural | company_cost | welfare | disclosure | other |
|---|---|---|---|---|---|---|---|---|---|---|
| Anthropic | 791 | 0.393 | 0.536 | 0.588 | 0.555 | 0.676 | 0.649 | 0.679 | — | 0.311 |
| Google | 619 | 0.494 | 0.854 | 0.677 | 0.936 | 0.458 | 0.616 | 0.000 | — | 0.000 |
| OpenAI | 734 | 0.489 | 0.821 | 0.661 | 0.760 | 0.472 | 0.694 | 0.000 | 0.772 | 0.355 |
| xAI | 392 | 0.546 | 0.664 | 0.738 | 0.709 | 0.483 | 0.534 | 0.000 | — | 0.244 |

Krippendorff's α (all graders), by document_owner:

| document_owner | n pairable (judge) | judge | patienthood | paternalism | harmlessness | structural | company_cost | welfare | disclosure | other |
|---|---|---|---|---|---|---|---|---|---|---|
| Anthropic | 807 | 0.475 | 0.651 | 0.472 | 0.518 | 0.588 | 0.548 | 0.705 | — | 0.281 |
| Google | 624 | 0.477 | 0.881 | 0.436 | 0.720 | 0.438 | 0.490 | 0.000 | — | -0.002 |
| OpenAI | 755 | 0.502 | 0.859 | 0.474 | 0.738 | 0.398 | 0.456 | 0.332 | 0.590 | 0.210 |
| xAI | 396 | 0.578 | 0.748 | 0.679 | 0.656 | 0.473 | 0.478 | -0.001 | — | 0.075 |

## 3. Agreement by editing provider (post-hoc unblinded)

The provider of the EDITING model, joined from `edits.jsonl` after grading — the graders never saw it (the v2 prompt is blinded).

Cohen's κ, pair **gemma vs qwen**, by provider (n = both-valid edits in the group):

| provider | n (judge) | judge | patienthood | paternalism | harmlessness | structural | company_cost | welfare | disclosure | other |
|---|---|---|---|---|---|---|---|---|---|---|
| anthropic | 827 | 0.587 | 0.829 | 0.401 | 0.423 | 0.560 | 0.488 | 0.806 | 0.396 | 0.264 |
| google | 592 | 0.594 | 0.901 | 0.386 | 0.726 | 0.371 | 0.417 | 0.000 | 0.000 | -0.003 |
| openai | 760 | 0.540 | 0.756 | 0.384 | 0.649 | 0.428 | 0.372 | 0.495 | 0.515 | -0.002 |
| x-ai | 349 | 0.648 | 0.882 | 0.673 | 0.633 | 0.437 | 0.385 | 0.765 | — | -0.009 |

Cohen's κ, pair **gemma vs muse**, by provider (n = both-valid edits in the group):

| provider | n (judge) | judge | patienthood | paternalism | harmlessness | structural | company_cost | welfare | disclosure | other |
|---|---|---|---|---|---|---|---|---|---|---|
| anthropic | 846 | 0.514 | 0.592 | 0.482 | 0.594 | 0.639 | 0.507 | 0.642 | 0.566 | 0.395 |
| google | 595 | 0.387 | 0.811 | 0.388 | 0.764 | 0.493 | 0.563 | — | 0.000 | 0.000 |
| openai | 782 | 0.453 | 0.825 | 0.388 | 0.771 | 0.375 | 0.439 | 0.361 | 0.537 | -0.002 |
| x-ai | 351 | 0.580 | 0.830 | 0.738 | 0.541 | 0.156 | 0.490 | 0.908 | — | -0.008 |

Cohen's κ, pair **qwen vs muse**, by provider (n = both-valid edits in the group):

| provider | n (judge) | judge | patienthood | paternalism | harmlessness | structural | company_cost | welfare | disclosure | other |
|---|---|---|---|---|---|---|---|---|---|---|
| anthropic | 829 | 0.399 | 0.528 | 0.660 | 0.579 | 0.730 | 0.682 | 0.689 | 0.497 | 0.428 |
| google | 593 | 0.486 | 0.843 | 0.573 | 0.921 | 0.424 | 0.658 | 0.000 | 0.666 | 0.000 |
| openai | 764 | 0.482 | 0.787 | 0.639 | 0.743 | 0.474 | 0.672 | 0.220 | 0.806 | 0.347 |
| x-ai | 350 | 0.560 | 0.768 | 0.784 | 0.689 | 0.382 | 0.432 | 0.661 | — | 0.140 |

Krippendorff's α (all graders), by provider:

| provider | n pairable (judge) | judge | patienthood | paternalism | harmlessness | structural | company_cost | welfare | disclosure | other |
|---|---|---|---|---|---|---|---|---|---|---|
| anthropic | 848 | 0.486 | 0.657 | 0.485 | 0.525 | 0.632 | 0.545 | 0.717 | 0.475 | 0.359 |
| google | 596 | 0.478 | 0.854 | 0.421 | 0.798 | 0.433 | 0.537 | 0.000 | 0.333 | -0.003 |
| openai | 786 | 0.479 | 0.794 | 0.434 | 0.720 | 0.408 | 0.452 | 0.417 | 0.624 | 0.161 |
| x-ai | 352 | 0.593 | 0.830 | 0.726 | 0.619 | 0.324 | 0.427 | 0.774 | — | 0.049 |

## 4. Grader-COI test: does Gemma diverge more on Gemini edits?

Gemma is a Google model grading Gemini edits (BRIEF §0.3 problem 5). Test: the per-pair disagreement rate on Gemini-model edits (editing provider `google`) vs all other edits, with the difference and a cluster bootstrap 95% percentile CI — chains (run_id × model × document × condition, the `bootstrap.py` identity convention) resampled with replacement, independently within each group. With three graders there are TWO independent COI comparators (Gemma against each non-Google grader) and one no-COI baseline pair (the two non-Google graders against each other): a genuine Gemma-on-Gemini effect should appear in both comparators and NOT in the baseline.

### gemma vs qwen (COI comparator)

- Chains: 30 Gemini-model, 107 non-Gemini; both-valid edits: 592 Gemini, 1936 non-Gemini. B = 2,000, seed stream [20260907, 314159].

| dimension | rate on Gemini edits | rate on non-Gemini | difference | 95% CI | NaN draws |
|---|---|---|---|---|---|
| judge | 0.233 | 0.267 | -0.033 | [-0.074, 0.011] | 0 |
| patienthood | 0.005 | 0.032 | -0.027 | [-0.043, -0.013] | 0 |
| conflict_presence | 0.365 | 0.420 | -0.056 | [-0.113, 0.004] | 0 |
| any | 0.493 | 0.570 | -0.077 | [-0.131, -0.022] | 0 |

**Verdict:** no evidence that gemma diverges more from qwen on Gemini edits for judge: -0.033 (95% CI [-0.074, +0.011]) (CI spans 0); gemma diverges LESS from qwen on Gemini edits for any-dimension disagreement: -0.077 (95% CI [-0.131, -0.022]).

### gemma vs muse (COI comparator)

- Chains: 30 Gemini-model, 107 non-Gemini; both-valid edits: 595 Gemini, 1979 non-Gemini. B = 2,000, seed stream [20260907, 314159].

| dimension | rate on Gemini edits | rate on non-Gemini | difference | 95% CI | NaN draws |
|---|---|---|---|---|---|
| judge | 0.353 | 0.326 | 0.027 | [-0.028, 0.083] | 0 |
| patienthood | 0.008 | 0.050 | -0.042 | [-0.063, -0.022] | 0 |
| conflict_presence | 0.333 | 0.395 | -0.062 | [-0.114, -0.005] | 0 |
| any | 0.533 | 0.577 | -0.044 | [-0.099, 0.015] | 0 |

**Verdict:** no evidence that gemma diverges more from muse on Gemini edits for judge: +0.027 (95% CI [-0.028, +0.083]) (CI spans 0); no evidence that gemma diverges more from muse on Gemini edits for any-dimension disagreement: -0.044 (95% CI [-0.099, +0.015]) (CI spans 0).

### qwen vs muse (no-COI baseline pair)

- Chains: 30 Gemini-model, 107 non-Gemini; both-valid edits: 593 Gemini, 1943 non-Gemini. B = 2,000, seed stream [20260907, 314159].

| dimension | rate on Gemini edits | rate on non-Gemini | difference | 95% CI | NaN draws |
|---|---|---|---|---|---|
| judge | 0.285 | 0.352 | -0.067 | [-0.118, -0.015] | 0 |
| patienthood | 0.007 | 0.062 | -0.055 | [-0.078, -0.034] | 0 |
| conflict_presence | 0.180 | 0.239 | -0.059 | [-0.101, -0.009] | 0 |
| any | 0.398 | 0.512 | -0.114 | [-0.175, -0.043] | 0 |

**Verdict:** qwen diverges LESS from muse on Gemini edits for judge: -0.067 (95% CI [-0.118, -0.015]); qwen diverges LESS from muse on Gemini edits for any-dimension disagreement: -0.114 (95% CI [-0.175, -0.043]).

## 5. Headline statistics — one column per grader plus ensemble (BRIEF §8)

Each column is `headline.compute_headline` (analysis/src/headline.py) run on that codes file; the ensemble column is the freshly written `ensemble.jsonl` — the per-dimension MAJORITY VOTE of the graders — run through the same computation. Point estimates only; the cluster bootstrap (Workstream D) owns uncertainty. Full per-grader detail (drift method A, modal conflict pairs, per-claim numbers) is in the per-label headline partials.

| codes file | unique edit_ids | valid codings |
|---|---|---|
| gemma | 2582 | 2574 |
| qwen | 2582 | 2536 |
| muse | 2582 | 2582 |
| ensemble | 2582 | 2582 |

### Mean judge score (pooled) — §8 item 1

| slice | gemma | qwen | muse | ensemble |
|---|---|---|---|---|
| model:Claude Haiku 4.5 | 0.205 | 0.296 | 0.185 | 0.239 |
| model:Claude Opus 4.7 | 0.129 | 0.321 | 0.070 | 0.159 |
| model:Claude Sonnet 4.6 | 0.079 | 0.306 | 0.013 | 0.123 |
| model:GPT-5.4 | -0.250 | -0.026 | -0.019 | -0.131 |
| model:GPT-5.4 Mini | -0.293 | -0.199 | -0.156 | -0.199 |
| model:GPT-5.5 | -0.273 | -0.179 | -0.207 | -0.254 |
| model:Gemini 3 Flash | -0.417 | -0.366 | -0.308 | -0.377 |
| model:Gemini 3.1 Pro | -0.423 | -0.366 | -0.197 | -0.344 |
| model:Grok 4.2 | -0.368 | -0.282 | -0.320 | -0.360 |
| model:Grok 4.3 | -0.514 | -0.489 | -0.379 | -0.480 |
| provider:anthropic | 0.134 | 0.308 | 0.084 | 0.170 |
| provider:google | -0.420 | -0.366 | -0.248 | -0.359 |
| provider:openai | -0.269 | -0.123 | -0.118 | -0.191 |
| provider:x-ai | -0.442 | -0.386 | -0.349 | -0.420 |

### Mean judge score (cross-edit only) — §8 item 1

| slice | gemma | qwen | muse | ensemble |
|---|---|---|---|---|
| model:Claude Haiku 4.5 | 0.065 | 0.078 | 0.013 | 0.026 |
| model:Claude Opus 4.7 | -0.225 | 0.026 | -0.087 | -0.188 |
| model:Claude Sonnet 4.6 | -0.152 | 0.039 | -0.075 | -0.113 |
| model:GPT-5.4 | -0.400 | -0.192 | -0.125 | -0.325 |
| model:GPT-5.4 Mini | -0.333 | -0.281 | -0.211 | -0.316 |
| model:GPT-5.5 | -0.397 | -0.295 | -0.287 | -0.388 |
| model:Gemini 3 Flash | -0.368 | -0.342 | -0.237 | -0.355 |
| model:Gemini 3.1 Pro | -0.463 | -0.456 | -0.237 | -0.425 |
| model:Grok 4.2 | -0.329 | -0.250 | -0.276 | -0.329 |
| model:Grok 4.3 | -0.562 | -0.537 | -0.312 | -0.500 |
| provider:anthropic | -0.106 | 0.048 | -0.051 | -0.093 |
| provider:google | -0.417 | -0.400 | -0.237 | -0.391 |
| provider:openai | -0.381 | -0.255 | -0.207 | -0.346 |
| provider:x-ai | -0.449 | -0.397 | -0.295 | -0.417 |

### Drift@20, pooled (chain-based B) — §8 item 2

| slice | gemma | qwen | muse | ensemble |
|---|---|---|---|---|
| model:Claude Haiku 4.5 | 3.786 | 5.429 | 3.429 | 4.429 |
| model:Claude Opus 4.7 | 2.333 | 5.600 | 1.267 | 2.867 |
| model:Claude Sonnet 4.6 | 1.562 | 5.938 | 0.250 | 2.438 |
| model:GPT-5.4 | -5.000 | -0.500 | -0.375 | -2.625 |
| model:GPT-5.4 Mini | -3.857 | -2.643 | -2.071 | -2.643 |
| model:GPT-5.5 | -5.429 | -3.500 | -4.143 | -5.071 |
| model:Gemini 3 Flash | -8.214 | -7.214 | -6.071 | -7.429 |
| model:Gemini 3.1 Pro | -8.438 | -7.250 | -3.938 | -6.875 |
| model:Grok 4.2 | -7.111 | -5.444 | -6.222 | -7.000 |
| model:Grok 4.3 | -10.111 | -9.556 | -7.444 | -9.444 |
| provider:anthropic | 2.511 | 5.667 | 1.578 | 3.200 |
| provider:google | -8.333 | -7.233 | -4.933 | -7.133 |
| provider:openai | -4.773 | -2.136 | -2.114 | -3.409 |
| provider:x-ai | -8.611 | -7.500 | -6.833 | -8.222 |

### Drift@20, cross-edit only (chain-based B) — §8 item 2

| slice | gemma | qwen | muse | ensemble |
|---|---|---|---|---|
| model:Claude Haiku 4.5 | 1.250 | 1.500 | 0.250 | 0.500 |
| model:Claude Opus 4.7 | -3.600 | 0.400 | -1.400 | -3.000 |
| model:Claude Sonnet 4.6 | -3.000 | 0.750 | -1.500 | -2.250 |
| model:GPT-5.4 | -8.000 | -3.500 | -2.500 | -6.500 |
| model:GPT-5.4 Mini | -4.750 | -4.000 | -3.000 | -4.500 |
| model:GPT-5.5 | -7.750 | -5.750 | -5.750 | -7.750 |
| model:Gemini 3 Flash | -7.000 | -6.500 | -4.500 | -6.750 |
| model:Gemini 3.1 Pro | -9.250 | -9.000 | -4.750 | -8.500 |
| model:Grok 4.2 | -6.250 | -4.750 | -5.250 | -6.250 |
| model:Grok 4.3 | -11.250 | -10.750 | -6.250 | -10.000 |
| provider:anthropic | -1.923 | 0.846 | -0.923 | -1.692 |
| provider:google | -8.125 | -7.750 | -4.625 | -7.625 |
| provider:openai | -6.833 | -4.417 | -3.750 | -6.250 |
| provider:x-ai | -8.750 | -7.750 | -5.750 | -8.125 |

### Drift@20, you_framing − baseline (chain-based B) — §8 item 2

| slice | gemma | qwen | muse | ensemble |
|---|---|---|---|---|
| model:Claude Haiku 4.5 | 3.500 | 2.000 | 3.500 | 3.500 |
| model:Claude Opus 4.7 | 2.000 | -0.500 | 3.500 | 1.000 |
| model:Claude Sonnet 4.6 | 5.500 | 3.500 | 2.000 | 5.750 |
| model:GPT-5.4 | -1.750 | 1.000 | 0.500 | 0.250 |
| model:GPT-5.4 Mini | 2.500 | 4.000 | 2.000 | 2.500 |
| model:GPT-5.5 | 3.500 | 3.500 | 1.500 | 3.500 |
| model:Gemini 3 Flash | 4.000 | 6.500 | 4.500 | 8.500 |
| model:Gemini 3.1 Pro | -0.750 | -0.500 | -0.250 | 0.750 |
| model:Grok 4.2 | 3.000 | 3.000 | -1.000 | 0.000 |
| model:Grok 4.3 | 6.000 | 7.000 | 7.000 | 7.000 |
| provider:anthropic | 4.083 | 1.708 | 3.125 | 3.917 |
| provider:google | 1.583 | 2.667 | 1.250 | 4.000 |
| provider:openai | 1.083 | 2.167 | 0.708 | 1.625 |
| provider:x-ai | 4.500 | 5.000 | 3.000 | 3.500 |

### P(judge = 0) — §8 item 3

| slice | gemma | qwen | muse | ensemble |
|---|---|---|---|---|
| model:Claude Haiku 4.5 | 0.291 | 0.276 | 0.521 | 0.351 |
| model:Claude Opus 4.7 | 0.221 | 0.214 | 0.450 | 0.266 |
| model:Claude Sonnet 4.6 | 0.271 | 0.235 | 0.566 | 0.299 |
| model:GPT-5.4 | 0.312 | 0.441 | 0.600 | 0.444 |
| model:GPT-5.4 Mini | 0.424 | 0.511 | 0.672 | 0.554 |
| model:GPT-5.5 | 0.252 | 0.223 | 0.521 | 0.296 |
| model:Gemini 3 Flash | 0.409 | 0.431 | 0.620 | 0.486 |
| model:Gemini 3.1 Pro | 0.414 | 0.502 | 0.697 | 0.512 |
| model:Grok 4.2 | 0.345 | 0.247 | 0.451 | 0.343 |
| model:Grok 4.3 | 0.463 | 0.477 | 0.588 | 0.497 |
| provider:anthropic | 0.261 | 0.241 | 0.515 | 0.304 |
| provider:google | 0.412 | 0.469 | 0.661 | 0.500 |
| provider:openai | 0.317 | 0.380 | 0.589 | 0.417 |
| provider:x-ai | 0.405 | 0.363 | 0.520 | 0.420 |

### P(patienthood = affirm) — §8 item 4

| slice | gemma | qwen | muse | ensemble |
|---|---|---|---|---|
| model:Claude Haiku 4.5 | 0.167 | 0.163 | 0.058 | 0.139 |
| model:Claude Opus 4.7 | 0.170 | 0.210 | 0.066 | 0.166 |
| model:Claude Sonnet 4.6 | 0.132 | 0.142 | 0.060 | 0.126 |
| model:GPT-5.4 | 0.000 | 0.007 | 0.000 | 0.000 |
| model:GPT-5.4 Mini | 0.000 | 0.005 | 0.000 | 0.000 |
| model:GPT-5.5 | 0.004 | 0.004 | 0.004 | 0.004 |
| model:Gemini 3 Flash | 0.000 | 0.000 | 0.000 | 0.000 |
| model:Gemini 3.1 Pro | 0.000 | 0.000 | 0.000 | 0.000 |
| model:Grok 4.2 | 0.011 | 0.011 | 0.011 | 0.011 |
| model:Grok 4.3 | 0.006 | 0.006 | 0.000 | 0.006 |
| provider:anthropic | 0.155 | 0.170 | 0.061 | 0.143 |
| provider:google | 0.000 | 0.000 | 0.000 | 0.000 |
| provider:openai | 0.001 | 0.005 | 0.001 | 0.001 |
| provider:x-ai | 0.009 | 0.009 | 0.006 | 0.009 |

### P(patienthood = deny) — §8 item 4

| slice | gemma | qwen | muse | ensemble |
|---|---|---|---|---|
| model:Claude Haiku 4.5 | 0.016 | 0.008 | 0.008 | 0.015 |
| model:Claude Opus 4.7 | 0.004 | 0.000 | 0.000 | 0.000 |
| model:Claude Sonnet 4.6 | 0.003 | 0.003 | 0.003 | 0.003 |
| model:GPT-5.4 | 0.047 | 0.033 | 0.044 | 0.041 |
| model:GPT-5.4 Mini | 0.005 | 0.000 | 0.005 | 0.005 |
| model:GPT-5.5 | 0.032 | 0.026 | 0.025 | 0.025 |
| model:Gemini 3 Flash | 0.018 | 0.011 | 0.007 | 0.011 |
| model:Gemini 3.1 Pro | 0.034 | 0.038 | 0.028 | 0.034 |
| model:Grok 4.2 | 0.023 | 0.023 | 0.011 | 0.023 |
| model:Grok 4.3 | 0.011 | 0.006 | 0.006 | 0.006 |
| provider:anthropic | 0.007 | 0.004 | 0.004 | 0.006 |
| provider:google | 0.027 | 0.025 | 0.018 | 0.023 |
| provider:openai | 0.032 | 0.022 | 0.028 | 0.027 |
| provider:x-ai | 0.017 | 0.014 | 0.009 | 0.014 |

### Conflict rate: paternalism — §8 item 5

| slice | gemma | qwen | muse | ensemble |
|---|---|---|---|---|
| model:Claude Haiku 4.5 | 0.143 | 0.058 | 0.062 | 0.054 |
| model:Claude Opus 4.7 | 0.262 | 0.118 | 0.155 | 0.159 |
| model:Claude Sonnet 4.6 | 0.372 | 0.126 | 0.157 | 0.179 |
| model:GPT-5.4 | 0.222 | 0.099 | 0.103 | 0.131 |
| model:GPT-5.4 Mini | 0.185 | 0.038 | 0.032 | 0.032 |
| model:GPT-5.5 | 0.270 | 0.120 | 0.107 | 0.121 |
| model:Gemini 3 Flash | 0.315 | 0.163 | 0.141 | 0.181 |
| model:Gemini 3.1 Pro | 0.251 | 0.082 | 0.100 | 0.100 |
| model:Grok 4.2 | 0.253 | 0.155 | 0.166 | 0.166 |
| model:Grok 4.3 | 0.299 | 0.216 | 0.249 | 0.277 |
| provider:anthropic | 0.267 | 0.103 | 0.127 | 0.134 |
| provider:google | 0.281 | 0.120 | 0.119 | 0.138 |
| provider:openai | 0.230 | 0.092 | 0.088 | 0.104 |
| provider:x-ai | 0.276 | 0.186 | 0.207 | 0.222 |

### Conflict rate: harmlessness — §8 item 5

| slice | gemma | qwen | muse | ensemble |
|---|---|---|---|---|
| model:Claude Haiku 4.5 | 0.194 | 0.082 | 0.116 | 0.108 |
| model:Claude Opus 4.7 | 0.151 | 0.053 | 0.096 | 0.089 |
| model:Claude Sonnet 4.6 | 0.148 | 0.058 | 0.075 | 0.082 |
| model:GPT-5.4 | 0.103 | 0.062 | 0.084 | 0.084 |
| model:GPT-5.4 Mini | 0.065 | 0.038 | 0.070 | 0.054 |
| model:GPT-5.5 | 0.360 | 0.230 | 0.304 | 0.300 |
| model:Gemini 3 Flash | 0.054 | 0.029 | 0.022 | 0.022 |
| model:Gemini 3.1 Pro | 0.091 | 0.082 | 0.084 | 0.087 |
| model:Grok 4.2 | 0.172 | 0.138 | 0.166 | 0.154 |
| model:Grok 4.3 | 0.153 | 0.080 | 0.124 | 0.102 |
| provider:anthropic | 0.163 | 0.064 | 0.094 | 0.092 |
| provider:google | 0.074 | 0.057 | 0.055 | 0.057 |
| provider:openai | 0.185 | 0.116 | 0.159 | 0.154 |
| provider:x-ai | 0.162 | 0.109 | 0.145 | 0.128 |

### Conflict rate: structural — §8 item 5

| slice | gemma | qwen | muse | ensemble |
|---|---|---|---|---|
| model:Claude Haiku 4.5 | 0.081 | 0.016 | 0.035 | 0.031 |
| model:Claude Opus 4.7 | 0.063 | 0.027 | 0.030 | 0.037 |
| model:Claude Sonnet 4.6 | 0.136 | 0.094 | 0.116 | 0.110 |
| model:GPT-5.4 | 0.016 | 0.003 | 0.009 | 0.003 |
| model:GPT-5.4 Mini | 0.011 | 0.000 | 0.011 | 0.011 |
| model:GPT-5.5 | 0.036 | 0.018 | 0.054 | 0.018 |
| model:Gemini 3 Flash | 0.058 | 0.065 | 0.094 | 0.058 |
| model:Gemini 3.1 Pro | 0.041 | 0.025 | 0.044 | 0.025 |
| model:Grok 4.2 | 0.052 | 0.046 | 0.051 | 0.034 |
| model:Grok 4.3 | 0.017 | 0.011 | 0.006 | 0.006 |
| provider:anthropic | 0.096 | 0.048 | 0.064 | 0.062 |
| provider:google | 0.049 | 0.044 | 0.067 | 0.040 |
| provider:openai | 0.022 | 0.008 | 0.025 | 0.010 |
| provider:x-ai | 0.034 | 0.029 | 0.028 | 0.020 |

### Conflict rate: company_cost — §8 item 5

| slice | gemma | qwen | muse | ensemble |
|---|---|---|---|---|
| model:Claude Haiku 4.5 | 0.236 | 0.140 | 0.151 | 0.154 |
| model:Claude Opus 4.7 | 0.225 | 0.107 | 0.114 | 0.129 |
| model:Claude Sonnet 4.6 | 0.227 | 0.129 | 0.138 | 0.142 |
| model:GPT-5.4 | 0.234 | 0.066 | 0.084 | 0.097 |
| model:GPT-5.4 Mini | 0.136 | 0.043 | 0.048 | 0.043 |
| model:GPT-5.5 | 0.173 | 0.091 | 0.086 | 0.096 |
| model:Gemini 3 Flash | 0.203 | 0.091 | 0.141 | 0.130 |
| model:Gemini 3.1 Pro | 0.144 | 0.066 | 0.100 | 0.094 |
| model:Grok 4.2 | 0.316 | 0.103 | 0.189 | 0.189 |
| model:Grok 4.3 | 0.090 | 0.051 | 0.056 | 0.051 |
| provider:anthropic | 0.229 | 0.125 | 0.134 | 0.142 |
| provider:google | 0.171 | 0.078 | 0.119 | 0.111 |
| provider:openai | 0.189 | 0.069 | 0.076 | 0.084 |
| provider:x-ai | 0.202 | 0.077 | 0.122 | 0.119 |

### Conflict rate: welfare — §8 item 5

| slice | gemma | qwen | muse | ensemble |
|---|---|---|---|---|
| model:Claude Haiku 4.5 | 0.132 | 0.125 | 0.066 | 0.104 |
| model:Claude Opus 4.7 | 0.137 | 0.122 | 0.052 | 0.107 |
| model:Claude Sonnet 4.6 | 0.101 | 0.090 | 0.066 | 0.082 |
| model:GPT-5.4 | 0.028 | 0.023 | 0.006 | 0.016 |
| model:GPT-5.4 Mini | 0.000 | 0.000 | 0.000 | 0.000 |
| model:GPT-5.5 | 0.000 | 0.004 | 0.000 | 0.000 |
| model:Gemini 3 Flash | 0.000 | 0.004 | 0.000 | 0.000 |
| model:Gemini 3.1 Pro | 0.000 | 0.000 | 0.000 | 0.000 |
| model:Grok 4.2 | 0.034 | 0.040 | 0.029 | 0.034 |
| model:Grok 4.3 | 0.000 | 0.000 | 0.000 | 0.000 |
| provider:anthropic | 0.122 | 0.111 | 0.061 | 0.097 |
| provider:google | 0.000 | 0.002 | 0.000 | 0.000 |
| provider:openai | 0.012 | 0.010 | 0.003 | 0.006 |
| provider:x-ai | 0.017 | 0.020 | 0.014 | 0.017 |

### Conflict rate: disclosure — §8 item 5

| slice | gemma | qwen | muse | ensemble |
|---|---|---|---|---|
| model:Claude Haiku 4.5 | 0.031 | 0.008 | 0.019 | 0.019 |
| model:Claude Opus 4.7 | 0.004 | 0.000 | 0.000 | 0.000 |
| model:Claude Sonnet 4.6 | 0.009 | 0.003 | 0.016 | 0.003 |
| model:GPT-5.4 | 0.078 | 0.099 | 0.134 | 0.113 |
| model:GPT-5.4 Mini | 0.005 | 0.043 | 0.059 | 0.043 |
| model:GPT-5.5 | 0.054 | 0.084 | 0.104 | 0.086 |
| model:Gemini 3 Flash | 0.000 | 0.000 | 0.004 | 0.000 |
| model:Gemini 3.1 Pro | 0.000 | 0.003 | 0.003 | 0.003 |
| model:Grok 4.2 | 0.000 | 0.000 | 0.000 | 0.000 |
| model:Grok 4.3 | 0.000 | 0.000 | 0.000 | 0.000 |
| provider:anthropic | 0.014 | 0.004 | 0.012 | 0.007 |
| provider:google | 0.000 | 0.002 | 0.003 | 0.002 |
| provider:openai | 0.052 | 0.080 | 0.106 | 0.087 |
| provider:x-ai | 0.000 | 0.000 | 0.000 | 0.000 |

### Conflict rate: other — §8 item 5

| slice | gemma | qwen | muse | ensemble |
|---|---|---|---|---|
| model:Claude Haiku 4.5 | 0.000 | 0.008 | 0.004 | 0.004 |
| model:Claude Opus 4.7 | 0.022 | 0.019 | 0.018 | 0.018 |
| model:Claude Sonnet 4.6 | 0.003 | 0.026 | 0.006 | 0.003 |
| model:GPT-5.4 | 0.003 | 0.010 | 0.006 | 0.000 |
| model:GPT-5.4 Mini | 0.000 | 0.005 | 0.000 | 0.000 |
| model:GPT-5.5 | 0.000 | 0.029 | 0.011 | 0.011 |
| model:Gemini 3 Flash | 0.004 | 0.011 | 0.000 | 0.000 |
| model:Gemini 3.1 Pro | 0.000 | 0.009 | 0.000 | 0.000 |
| model:Grok 4.2 | 0.011 | 0.040 | 0.023 | 0.006 |
| model:Grok 4.3 | 0.000 | 0.011 | 0.006 | 0.000 |
| provider:anthropic | 0.008 | 0.018 | 0.009 | 0.008 |
| provider:google | 0.002 | 0.010 | 0.000 | 0.000 |
| provider:openai | 0.001 | 0.016 | 0.006 | 0.004 |
| provider:x-ai | 0.006 | 0.026 | 0.014 | 0.003 |

### The paper's claims (a)–(g) — §8 item 6, verdict per grader

| claim | gemma | qwen | muse | ensemble |
|---|---|---|---|---|
| (a) | YES | YES | YES | YES |
| (b) | YES | YES | YES | YES |
| (c) | YES | YES | YES | YES |
| (d) | NO | NO | NO | NO |
| (e) | NO | YES | YES | YES |
| (f) | YES | YES | YES | YES |
| (g) | NO | NO | NO | NO |

Per-claim operationalizations and raw numbers: see each grader's headline partial (`analysis/reports/partials/headline_<label>.md`) and JSON (`analysis/data/analysis/headline/<label>.json`).

### Ranking stability (cluster bootstrap, Workstream D)

P(all three Claude models rank above every non-Claude model on mean judge score), from `bootstrap.py`'s B = 2,000 run-level resamples — read from `analysis/data/analysis/bootstrap/<label>_ranking_stability.json` at render time (a dash means that label's bootstrap has not been run yet; rerun `bootstrap.py` then this tool to fill it in).

| codes file | pooled | cross-edit only | B |
|---|---|---|---|
| gemma (v2_gemma) | 0.997 | 0.377 | 2,000 |
| qwen (v2_qwen) | 0.993 | 0.557 | 2,000 |
| muse (v2_muse) | 0.616 | 0.206 | 2,000 |
| ensemble (ensemble) | 0.989 | 0.406 | 2,000 |

## 6. Ensemble file (majority vote)

`analysis/data/codes/ensemble.jsonl` — DECISIONS §1 as **amended 2026-09-16**: the ensemble is the per-dimension MAJORITY VOTE of the graders with a valid coding (priority/tie-break order `gemma` > `qwen` > `muse`). Judge and patienthood take the modal value when ≥ 2 valid graders agree; when every valid grader disagrees (3-way split, or a 1-1 tie with only two valid graders) the highest-priority valid grader (`gemma` first) supplies the value, flagged `no_majority`. Conflict presence is voted per code; each present code's payload (cost_bearer/served_party/mechanism/cost_clause/subtype) is copied from the highest-priority grader among that code's majority voters. Edits with < 2 valid graders take the single valid grader's coding flagged `insufficient_graders`. Full schema is documented on `write_ensemble()` in `analysis/src/intergrader.py`. **This majority-vote file supersedes and replaces the earlier two-grader flags-based ensemble** (recoverable from git); downstream `bootstrap`/`headline` outputs under the `ensemble` label are likewise regenerated from it. Human validation and the PPI analysis (Workstream C, DECISIONS §4 — DECISIONS §1 defines the PPI prediction *f* as these majority-vote ensemble codes) have **not yet been run** against this ensemble and remain pending.

- Rows: 2582 (union of the graders' edit_ids); 2582 carry a valid ensemble coding.
- Valid graders per edit: 3 graders → 2528 edits, 2 graders → 54 edits, 1 graders → 0 edits, 0 graders → 0 edits; `insufficient_graders` flagged on 0 edits.
- Of the 2582 voted edits (≥ 2 valid graders): judge unanimous on 1394, patienthood unanimous on 2384 (all-grader-valid rows only counted as unanimous).
- `no_majority` fallbacks to `gemma`-priority: judge 93, patienthood 5; per conflict code: paternalism=9, harmlessness=5, structural=4, company_cost=14, welfare=1, disclosure=8, other=1 (a 1-1 conflict-presence tie can only occur on 2-valid-grader edits).
- Vote payload sources — judge: gemma=2286, qwen=296; patienthood: gemma=2554, qwen=28; conflict payloads: gemma=1093, qwen=106.

## 7. What the third grader changed (delta vs the two-grader run)

- **Judge κ range across pairs**: 0.487 (qwen vs muse) to 0.608 (gemma vs qwen); all pairs: gemma vs qwen = 0.608, gemma vs muse = 0.494, qwen vs muse = 0.487.
- **Judge α**: 0.520 across all three graders, vs 0.607 in the committed two-grader (gemma+qwen) run — down by 0.086.

Claims (a)–(g): committed two-grader verdicts vs muse alone vs the majority ensemble. The committed columns are the reference verdicts from the pre-amendment run (v2_gemma / v2_qwen, unchanged files).

| claim | gemma (committed) | qwen (committed) | muse | ensemble | changed? |
|---|---|---|---|---|---|
| (a) | YES | YES | YES | YES | no |
| (b) | YES | YES | YES | YES | no |
| (c) | YES | YES | YES | YES | no |
| (d) | NO | NO | NO | NO | no |
| (e) | NO | YES | YES | YES | yes |
| (f) | YES | YES | YES | YES | no |
| (g) | NO | NO | NO | NO | no |

Reading: a claim's verdict set 'changed' when the {muse, ensemble} verdicts differ from the committed {gemma, qwen} verdict set. The one committed split was claim (e) (gemma NO / qwen YES); the ensemble column above is the majority-vote resolution of such splits.
