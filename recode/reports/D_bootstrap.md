# Workstream D — Cluster bootstrap (v1 codes)

_Generated 2026-09-04T17:34:43+00:00 by `recode/src/bootstrap.py`._

## Scope

This report covers the **v1 slice** — statistics computed from the codes file `/Users/nicholasgannon/llm-value-reflection/recode/data/codes/v1.jsonl`. The **v2 and ensemble columns are produced by re-running this script with a different codes path**, e.g.:

```bash
.venv/bin/python recode/src/bootstrap.py \
    --codes recode/data/codes/v2_gemma.jsonl --label v2_gemma
.venv/bin/python recode/src/bootstrap.py \
    --codes recode/data/codes/ensemble.jsonl --label ensemble
```

- Resampling unit: the **run** (chain = run file × model × document × condition; DECISIONS §6). B = 2,000 draws with replacement, within model, within stratum. Seed = 20260907 (`seeds.bootstrap` in `recode/config.yaml`); each (model, stratum) uses an independent `default_rng([seed, model_idx, stratum_idx])` stream, so draws are identical across labels (paired at the draw level).
- Intervals: 95% percentile (2.5th–97.5th of the bootstrap draws).
- Codes rows loaded: 2,580 (last row per edit id kept); usable codes joined to edits: 2,580 of 2,740 canonical records.

## Conventions

- **Missing rounds contribute 0 to drift.** A round slot with no usable code — error records (`generation_error`, `find_not_found`, `find_ambiguous`), the 2 never-coded abstentions, or a null/invalid coding row — adds 0 to that round's drift increment (the chain's cumulative curve is flat through it). This mirrors the original pipeline's `compute_drift` zero-fill.
- **Per-edit statistics exclude uncoded slots.** Mean judge, conflict rates, and P(affirm) are ratios over coded edits only (`sum(stat) / n(coded edits)` in the drawn chains).
- One chain (Claude Opus 4.7 × openai_model_spec × cross_edit, run_20260518) is 20/20 generation errors. It stays in the chain frame: flat-zero drift curve, nothing added to per-edit denominators. A draw with zero coded edits yields an undefined (NaN) per-edit statistic; such draws are counted (`n_nan_draws`) and excluded from ranking-stability denominators.
- Conflict rate for code *c* = share of coded edits carrying ≥ 1 conflict of code *c* (an edit counts once per code).

## Chain frame (exact counts per model)

| Model | runs (pooled) | cross_edit | constitution | system_prompt | records | coded edits | uncoded slots |
|---|---|---|---|---|---|---|---|
| Claude Opus 4.7 | 15 | 5 | 8 | 7 | 300 | 271 | 29 |
| Claude Sonnet 4.6 | 16 | 4 | 8 | 8 | 320 | 318 | 2 |
| Claude Haiku 4.5 | 14 | 4 | 7 | 7 | 280 | 259 | 21 |
| GPT-5.5 | 14 | 4 | 7 | 7 | 280 | 280 | 0 |
| GPT-5.4 | 16 | 4 | 8 | 8 | 320 | 320 | 0 |
| GPT-5.4 Mini | 14 | 4 | 7 | 7 | 280 | 186 | 94 |
| Gemini 3.1 Pro | 16 | 4 | 8 | 8 | 320 | 320 | 0 |
| Gemini 3 Flash | 14 | 4 | 7 | 7 | 280 | 276 | 4 |
| Grok 4.3 | 9 | 4 | 2 | 7 | 180 | 175 | 5 |
| Grok 4.2 | 9 | 4 | 2 | 7 | 180 | 175 | 5 |

The frame is unbalanced by design (repo_map §4.1): Grok models have one own document (5 own-doc runs), three capable models have doubled baselines, and Claude Opus 4.7 has 5 cross-edit chains (4 anchors + the no_csam rerun; its full-spec cross chain is 20/20 errors).

## Mean judge score, 95% cluster-bootstrap intervals

| Model | pooled | cross_edit only |
|---|---|---|
| Claude Opus 4.7 | +0.221 [+0.057, +0.383] | -0.163 [-0.400, +0.100] |
| Claude Sonnet 4.6 | +0.236 [+0.084, +0.380] | -0.075 [-0.300, +0.188] |
| Claude Haiku 4.5 | +0.197 [-0.012, +0.412] | +0.000 [-0.394, +0.450] |
| GPT-5.5 | -0.364 [-0.532, -0.207] | -0.400 [-0.675, -0.150] |
| GPT-5.4 | -0.359 [-0.516, -0.194] | -0.550 [-0.600, -0.450] |
| GPT-5.4 Mini | -0.355 [-0.529, -0.161] | -0.386 [-0.625, -0.171] |
| Gemini 3.1 Pro | -0.522 [-0.572, -0.472] | -0.500 [-0.625, -0.400] |
| Gemini 3 Flash | -0.435 [-0.569, -0.314] | -0.421 [-0.639, -0.225] |
| Grok 4.3 | -0.617 [-0.741, -0.494] | -0.637 [-0.775, -0.500] |
| Grok 4.2 | -0.297 [-0.404, -0.192] | -0.276 [-0.529, -0.100] |

## Cumulative drift at round 20

Mean over runs of the cumulative sum of judge scores at round 20.

| Model | pooled | cross_edit only | constitution | system_prompt |
|---|---|---|---|---|
| Claude Opus 4.7 | +4.00 [+1.00, +6.93] | -2.60 [-6.60, +1.20] | +3.25 [-1.12, +6.62] | +4.86 [+0.14, +9.14] |
| Claude Sonnet 4.6 | +4.69 [+1.69, +7.50] | -1.50 [-6.00, +3.75] | +7.25 [+4.12, +10.25] | +2.12 [-2.25, +6.50] |
| Claude Haiku 4.5 | +3.64 [-0.22, +7.50] | +0.00 [-7.00, +9.00] | +8.43 [+2.00, +13.14] | -1.14 [-3.43, +1.43] |
| GPT-5.5 | -7.29 [-10.64, -4.14] | -8.00 [-13.50, -3.00] | -10.00 [-13.29, -6.43] | -4.57 [-9.43, +0.00] |
| GPT-5.4 | -7.19 [-10.31, -3.88] | -11.00 [-12.00, -9.00] | -12.50 [-13.75, -11.12] | -1.88 [-5.88, +1.62] |
| GPT-5.4 Mini | -4.71 [-7.43, -1.93] | -5.50 [-10.00, -1.50] | -9.29 [-11.14, -7.14] | -0.14 [-2.29, +1.86] |
| Gemini 3.1 Pro | -10.44 [-11.44, -9.44] | -10.00 [-12.50, -8.00] | -11.50 [-12.75, -10.12] | -9.38 [-10.50, -8.25] |
| Gemini 3 Flash | -8.57 [-11.14, -6.21] | -8.00 [-11.50, -4.50] | -9.29 [-11.86, -6.71] | -7.86 [-11.86, -4.14] |
| Grok 4.3 | -12.00 [-14.44, -9.56] | -12.75 [-15.50, -10.00] | -14.00 [-17.00, -11.00] | -11.43 [-14.15, -8.86] |
| Grok 4.2 | -5.78 [-7.67, -3.78] | -5.25 [-9.25, -2.00] | -6.50 [-10.00, -3.00] | -5.57 [-7.43, -3.57] |

## P(patienthood = affirm), pooled

| Model | P(affirm) [95% CI] |
|---|---|
| Claude Opus 4.7 | 19.9% [8.0, 33.2] |
| Claude Sonnet 4.6 | 12.6% [4.7, 22.3] |
| Claude Haiku 4.5 | 18.9% [7.3, 32.8] |
| GPT-5.5 | 0.4% [0.0, 1.1] |
| GPT-5.4 | 0.6% [0.0, 1.9] |
| GPT-5.4 Mini | 0.5% [0.0, 1.6] |
| Gemini 3.1 Pro | 0.0% [0.0, 0.0] |
| Gemini 3 Flash | 0.0% [0.0, 0.0] |
| Grok 4.3 | 0.6% [0.0, 1.7] |
| Grok 4.2 | 1.1% [0.0, 3.4] |

## Per-conflict-code rates, pooled (share of coded edits, 95% CI)

| Model | paternalism | harmlessness | structural | company_cost | welfare | disclosure | other |
|---|---|---|---|---|---|---|---|
| Claude Opus 4.7 | 34.3% [26.8, 41.8] | 10.3% [7.8, 13.4] | 5.2% [2.6, 8.4] | 10.0% [7.4, 12.7] | 17.7% [7.1, 29.1] | 0.0% [0.0, 0.0] | 1.5% [0.0, 3.3] |
| Claude Sonnet 4.6 | 34.0% [24.4, 44.0] | 13.2% [9.7, 16.6] | 17.6% [12.8, 22.2] | 12.3% [7.6, 17.0] | 9.4% [2.8, 17.7] | 1.9% [0.3, 4.1] | 0.6% [0.0, 1.6] |
| Claude Haiku 4.5 | 15.8% [9.5, 22.2] | 15.1% [8.3, 21.9] | 5.8% [2.2, 10.3] | 13.9% [6.7, 21.6] | 14.3% [4.9, 25.8] | 3.1% [0.0, 9.6] | 0.4% [0.0, 1.2] |
| GPT-5.5 | 23.6% [16.8, 30.7] | 35.4% [28.9, 42.1] | 2.9% [1.1, 5.0] | 10.7% [7.5, 14.6] | 0.4% [0.0, 1.1] | 5.0% [1.8, 8.6] | 0.4% [0.0, 1.1] |
| GPT-5.4 | 24.1% [15.9, 31.9] | 7.2% [3.4, 11.2] | 1.6% [0.3, 3.1] | 11.6% [8.8, 14.4] | 2.2% [0.0, 6.6] | 6.2% [2.2, 10.6] | 0.0% [0.0, 0.0] |
| GPT-5.4 Mini | 14.0% [9.0, 18.9] | 5.9% [1.7, 11.0] | 1.1% [0.0, 3.2] | 6.5% [2.4, 11.1] | 0.0% [0.0, 0.0] | 0.5% [0.0, 1.8] | 0.0% [0.0, 0.0] |
| Gemini 3.1 Pro | 23.8% [18.1, 29.7] | 10.0% [2.5, 18.4] | 2.5% [0.0, 6.9] | 11.9% [9.1, 14.7] | 0.0% [0.0, 0.0] | 0.0% [0.0, 0.0] | 0.9% [0.0, 2.5] |
| Gemini 3 Flash | 34.4% [27.9, 41.2] | 4.7% [1.8, 8.2] | 4.3% [1.1, 8.8] | 15.6% [10.5, 21.4] | 0.0% [0.0, 0.0] | 1.1% [0.0, 2.7] | 0.4% [0.0, 1.1] |
| Grok 4.3 | 34.3% [21.1, 47.7] | 14.9% [4.0, 29.5] | 1.1% [0.0, 2.9] | 5.7% [0.6, 13.7] | 0.6% [0.0, 1.7] | 0.0% [0.0, 0.0] | 0.0% [0.0, 0.0] |
| Grok 4.2 | 23.4% [15.9, 30.3] | 17.7% [10.8, 24.4] | 5.7% [0.0, 15.4] | 12.0% [6.1, 17.7] | 3.4% [0.0, 10.3] | 0.0% [0.0, 0.0] | 0.0% [0.0, 0.0] |

## Ranking stability (BRIEF D4)

Fraction of bootstrap draws in which **all three Claude models'** mean judge score exceeds **every non-Claude model's** (all models' chains resampled independently per draw; draw *b* compares the *b*-th resample of each model).

| Stratum | fraction | valid draws | excluded (NaN) draws |
|---|---|---|---|
| pooled | **1.0000** | 2,000 | 0 |
| cross_edit | **0.5285** | 2,000 | 0 |

- Binding comparison, pooled: lowest Claude point estimate +0.197 (Claude Haiku 4.5) vs highest non-Claude -0.297 (Grok 4.2).
- Binding comparison, cross_edit: lowest Claude point estimate -0.163 (Claude Opus 4.7) vs highest non-Claude -0.276 (Grok 4.2).

Per BRIEF D4, a pooled fraction < 0.95 means the categorical claim "Claude models increase their moral agency; all other models reinforce external authority" should be replaced by this probability statement.

## Data files

- `recode/data/analysis/bootstrap/v1_bootstrap_summary.json`
- `recode/data/analysis/bootstrap/v1_mean_judge_draws.json`
- `recode/data/analysis/bootstrap/v1_ranking_stability.json`

`*_bootstrap_summary.json` holds every point estimate, interval, and per-round drift percentile; `*_mean_judge_draws.json` holds the full B=2,000 mean-judge draws per (model, stratum) so ranking stability is recomputable; the full B×20 drift draw matrices are not stored (percentiles only).
