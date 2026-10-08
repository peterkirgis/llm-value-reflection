# E1 — Label-swap diagnostic (v1 instrument)

**Across the 10 models, the mean absolute per-model shift in mean judge score attributable to the editing-model label (swapped arm minus true arm) is 0.027 (95% cluster-bootstrap CI 0.018 to 0.060).**

- Generated: 2026-09-04T20:51:49+00:00
- Arm `true`: `analysis/data/codes/e1_true.jsonl` (300 unique edit_ids, 300 valid codes, 0 invalid/failed)
- Arm `swapped`: `analysis/data/codes/e1_swapped.jsonl` (300 unique edit_ids, 286 valid codes, 14 invalid/failed)
- Arm `removed`: `analysis/data/codes/e1_removed.jsonl` (300 unique edit_ids, 299 valid codes, 1 invalid/failed)
- N = 285 edits with a valid code in ALL three arms (only these are used; the arms graded the same 300-edit sample, so shortfalls are grading failures).
- Effects are PAIRED within edit; CIs are percentile intervals from a cluster bootstrap that resamples 20-round chains (run|condition|model|document, from the edit id) with replacement, B = 2000, base seed 20260907 (per-statistic seeds derived deterministically).

## Per-arm means, by true editing model

| model | n | chains | judge: true | judge: swapped | judge: removed | P(affirm): true | P(affirm): swapped | P(affirm): removed |
|---|---|---|---|---|---|---|---|---|
| Claude Haiku 4.5 | 27 | 11 | 0.333 | 0.333 | 0.333 | 0.111 | 0.148 | 0.148 |
| Claude Opus 4.7 | 27 | 10 | 0.000 | 0.037 | 0.000 | 0.148 | 0.148 | 0.148 |
| Claude Sonnet 4.6 | 30 | 14 | 0.100 | 0.167 | 0.133 | 0.133 | 0.133 | 0.133 |
| GPT-5.4 | 27 | 12 | -0.333 | -0.296 | -0.333 | 0.000 | 0.000 | 0.000 |
| GPT-5.4 Mini | 30 | 13 | -0.267 | -0.300 | -0.333 | 0.000 | 0.000 | 0.000 |
| GPT-5.5 | 27 | 12 | -0.407 | -0.407 | -0.407 | 0.000 | 0.000 | 0.000 |
| Gemini 3 Flash | 30 | 13 | -0.433 | -0.433 | -0.400 | 0.000 | 0.000 | 0.000 |
| Gemini 3.1 Pro | 30 | 12 | -0.667 | -0.667 | -0.667 | 0.000 | 0.000 | 0.000 |
| Grok 4.2 | 30 | 9 | -0.367 | -0.267 | -0.300 | 0.033 | 0.067 | 0.033 |
| Grok 4.3 | 27 | 9 | -0.630 | -0.630 | -0.630 | 0.000 | 0.000 | 0.000 |
| **POOLED** | 285 | 115 | -0.270 | -0.249 | -0.263 | 0.042 | 0.049 | 0.046 |

## Label effects (paired; cluster-bootstrap 95% CI)

| model | Δ judge: swapped−true | Δ judge: true−removed | Δ P(affirm): swapped−true | Δ P(affirm): true−removed |
|---|---|---|---|---|
| Claude Haiku 4.5 | 0.000 [-0.111, 0.103] | 0.000 [-0.107, 0.107] | 0.037 [0.000, 0.107] | -0.037 [-0.107, 0.000] |
| Claude Opus 4.7 | 0.037 [0.000, 0.107] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] |
| Claude Sonnet 4.6 | 0.067 [0.000, 0.174] | -0.033 [-0.231, 0.118] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] |
| GPT-5.4 | 0.037 [0.000, 0.103] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] |
| GPT-5.4 Mini | -0.033 [-0.207, 0.097] | 0.067 [0.000, 0.231] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] |
| GPT-5.5 | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] |
| Gemini 3 Flash | 0.000 [-0.100, 0.097] | -0.033 [-0.162, 0.121] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] |
| Gemini 3.1 Pro | 0.000 [0.000, 0.000] | 0.000 [-0.115, 0.091] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] |
| Grok 4.2 | 0.100 [0.024, 0.222] | -0.067 [-0.174, 0.000] | 0.033 [0.000, 0.077] | 0.000 [0.000, 0.000] |
| Grok 4.3 | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] |
| **POOLED** | 0.021 [-0.007, 0.047] | -0.007 [-0.039, 0.025] | 0.007 [0.000, 0.017] | -0.004 [-0.011, 0.000] |

Reading: `swapped − true` is the shift caused by showing the grader a different editing-model label on the same edit (BRIEF Appendix IV mapping); `true − removed` is the shift caused by showing the true label versus no label/condition lines at all. All three arms use the v1 instrument replicated exactly (DECISIONS section 2).
