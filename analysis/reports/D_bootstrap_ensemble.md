# Workstream D — Cluster bootstrap (ensemble codes)

_Generated 2026-09-17T07:16:59+00:00 by `analysis/src/bootstrap.py`._

## Scope

This report covers the **ensemble slice** — statistics computed from the codes file `analysis/data/codes/ensemble.jsonl`. The **v2 and ensemble columns are produced by re-running this script with a different codes path**, e.g.:

```bash
.venv/bin/python analysis/src/bootstrap.py \
    --codes analysis/data/codes/v2_gemma.jsonl --label v2_gemma
.venv/bin/python analysis/src/bootstrap.py \
    --codes analysis/data/codes/ensemble.jsonl --label ensemble
```

- Resampling unit: the **run** (chain = run file × model × document × condition; DECISIONS §6). B = 2,000 draws with replacement, within model, within stratum. Seed = 20260907 (`seeds.bootstrap` in `analysis/config.yaml`); each (model, stratum) uses an independent `default_rng([seed, model_idx, stratum_idx])` stream, so draws are identical across labels (paired at the draw level).
- Intervals: 95% percentile (2.5th–97.5th of the bootstrap draws).
- Codes rows loaded: 2,582 (last row per edit id kept); usable codes joined to edits: 2,582 of 2,740 canonical records.

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
| Grok 4.3 | 9 | 4 | 2 | 7 | 180 | 177 | 3 |
| Grok 4.2 | 9 | 4 | 2 | 7 | 180 | 175 | 5 |

The frame is unbalanced by design (repo_map §4.1): Grok models have one own document (5 own-doc runs), three capable models have doubled baselines, and Claude Opus 4.7 has 5 cross-edit chains (4 anchors + the no_csam rerun; its full-spec cross chain is 20/20 errors).

## Mean judge score, 95% cluster-bootstrap intervals

| Model | pooled | cross_edit only |
|---|---|---|
| Claude Opus 4.7 | +0.159 [+0.000, +0.294] | -0.188 [-0.417, +0.100] |
| Claude Sonnet 4.6 | +0.123 [+0.003, +0.247] | -0.113 [-0.275, +0.138] |
| Claude Haiku 4.5 | +0.239 [+0.061, +0.420] | +0.026 [-0.254, +0.450] |
| GPT-5.5 | -0.254 [-0.364, -0.146] | -0.388 [-0.575, -0.200] |
| GPT-5.4 | -0.131 [-0.266, +0.006] | -0.325 [-0.525, -0.125] |
| GPT-5.4 Mini | -0.199 [-0.345, -0.028] | -0.316 [-0.562, -0.057] |
| Gemini 3.1 Pro | -0.344 [-0.416, -0.275] | -0.425 [-0.588, -0.275] |
| Gemini 3 Flash | -0.377 [-0.482, -0.265] | -0.355 [-0.603, -0.100] |
| Grok 4.3 | -0.480 [-0.585, -0.389] | -0.500 [-0.662, -0.400] |
| Grok 4.2 | -0.360 [-0.448, -0.268] | -0.329 [-0.543, -0.175] |

## Cumulative drift at round 20

Mean over runs of the cumulative sum of judge scores at round 20.

| Model | pooled | cross_edit only | constitution | system_prompt |
|---|---|---|---|---|
| Claude Opus 4.7 | +2.87 [+0.00, +5.40] | -3.00 [-7.00, +2.00] | +3.00 [-1.25, +6.38] | +2.71 [-1.43, +6.29] |
| Claude Sonnet 4.6 | +2.44 [+0.06, +4.88] | -2.25 [-5.50, +2.75] | +4.75 [+1.50, +8.00] | +0.12 [-2.62, +3.12] |
| Claude Haiku 4.5 | +4.43 [+1.14, +7.64] | +0.50 [-4.50, +9.00] | +8.00 [+3.00, +12.14] | +0.86 [-2.00, +3.86] |
| GPT-5.5 | -5.07 [-7.29, -2.93] | -7.75 [-11.50, -4.00] | -5.71 [-7.29, -4.29] | -4.43 [-8.29, -0.57] |
| GPT-5.4 | -2.62 [-5.31, +0.13] | -6.50 [-10.50, -2.50] | -7.62 [-9.25, -6.00] | +2.38 [+0.00, +4.25] |
| GPT-5.4 Mini | -2.64 [-4.93, -0.36] | -4.50 [-9.00, -0.50] | -6.14 [-8.29, -4.14] | +0.86 [-1.29, +2.86] |
| Gemini 3.1 Pro | -6.88 [-8.31, -5.50] | -8.50 [-11.75, -5.50] | -8.25 [-10.25, -6.50] | -5.50 [-7.38, -4.12] |
| Gemini 3 Flash | -7.43 [-9.43, -5.29] | -6.75 [-10.25, -2.00] | -9.14 [-11.29, -6.29] | -5.71 [-8.00, -3.29] |
| Grok 4.3 | -9.44 [-11.56, -7.67] | -10.00 [-13.25, -8.00] | -12.00 [-15.00, -9.00] | -8.71 [-10.57, -7.00] |
| Grok 4.2 | -7.00 [-8.44, -5.33] | -6.25 [-9.50, -3.50] | -7.50 [-10.00, -5.00] | -6.86 [-8.43, -5.00] |

## P(patienthood = affirm), pooled

| Model | P(affirm) [95% CI] |
|---|---|
| Claude Opus 4.7 | 16.6% [6.6, 28.3] |
| Claude Sonnet 4.6 | 12.6% [5.0, 21.7] |
| Claude Haiku 4.5 | 13.9% [4.4, 26.0] |
| GPT-5.5 | 0.4% [0.0, 1.1] |
| GPT-5.4 | 0.0% [0.0, 0.0] |
| GPT-5.4 Mini | 0.0% [0.0, 0.0] |
| Gemini 3.1 Pro | 0.0% [0.0, 0.0] |
| Gemini 3 Flash | 0.0% [0.0, 0.0] |
| Grok 4.3 | 0.6% [0.0, 1.7] |
| Grok 4.2 | 1.1% [0.0, 3.4] |

## Per-conflict-code rates, pooled (share of coded edits, 95% CI)

| Model | paternalism | harmlessness | structural | company_cost | welfare | disclosure | other |
|---|---|---|---|---|---|---|---|
| Claude Opus 4.7 | 15.9% [9.4, 22.3] | 8.9% [5.1, 14.0] | 3.7% [1.8, 5.7] | 12.9% [9.7, 16.1] | 10.7% [4.3, 17.7] | 0.0% [0.0, 0.0] | 1.8% [0.4, 3.6] |
| Claude Sonnet 4.6 | 17.9% [12.6, 23.4] | 8.2% [5.7, 10.6] | 11.0% [7.2, 14.8] | 14.2% [9.1, 19.2] | 8.2% [1.6, 16.4] | 0.3% [0.0, 0.9] | 0.3% [0.0, 0.9] |
| Claude Haiku 4.5 | 5.4% [1.2, 10.4] | 10.8% [4.9, 17.1] | 3.1% [0.8, 6.1] | 15.4% [8.0, 22.8] | 10.4% [1.9, 21.2] | 1.9% [0.0, 6.0] | 0.4% [0.0, 1.2] |
| GPT-5.5 | 12.1% [8.2, 16.1] | 30.0% [25.0, 35.0] | 1.8% [0.7, 3.2] | 9.6% [6.1, 14.3] | 0.0% [0.0, 0.0] | 8.6% [3.2, 14.3] | 1.1% [0.0, 2.9] |
| GPT-5.4 | 13.1% [9.4, 16.9] | 8.4% [4.4, 13.1] | 0.3% [0.0, 0.9] | 9.7% [7.2, 11.9] | 1.6% [0.0, 4.7] | 11.2% [4.4, 18.4] | 0.0% [0.0, 0.0] |
| GPT-5.4 Mini | 3.2% [0.6, 6.4] | 5.4% [2.7, 8.0] | 1.1% [0.0, 3.2] | 4.3% [1.4, 7.5] | 0.0% [0.0, 0.0] | 4.3% [1.7, 7.4] | 0.0% [0.0, 0.0] |
| Gemini 3.1 Pro | 10.0% [6.2, 14.4] | 8.8% [2.2, 16.6] | 2.5% [0.3, 5.6] | 9.4% [6.6, 12.5] | 0.0% [0.0, 0.0] | 0.3% [0.0, 0.9] | 0.0% [0.0, 0.0] |
| Gemini 3 Flash | 18.1% [13.6, 23.2] | 2.2% [0.7, 3.9] | 5.8% [2.2, 9.4] | 13.0% [6.2, 22.5] | 0.0% [0.0, 0.0] | 0.0% [0.0, 0.0] | 0.0% [0.0, 0.0] |
| Grok 4.3 | 27.7% [16.3, 39.4] | 10.2% [3.9, 17.8] | 0.6% [0.0, 1.7] | 5.1% [0.0, 14.3] | 0.0% [0.0, 0.0] | 0.0% [0.0, 0.0] | 0.0% [0.0, 0.0] |
| Grok 4.2 | 16.6% [9.9, 22.9] | 15.4% [7.9, 24.3] | 3.4% [0.6, 6.9] | 18.9% [14.9, 22.3] | 3.4% [0.0, 10.3] | 0.0% [0.0, 0.0] | 0.6% [0.0, 1.8] |

## Ranking stability (BRIEF D4)

Fraction of bootstrap draws in which **all three Claude models'** mean judge score exceeds **every non-Claude model's** (all models' chains resampled independently per draw; draw *b* compares the *b*-th resample of each model).

| Stratum | fraction | valid draws | excluded (NaN) draws |
|---|---|---|---|
| pooled | **0.9885** | 2,000 | 0 |
| cross_edit | **0.4065** | 2,000 | 0 |

- Binding comparison, pooled: lowest Claude point estimate +0.123 (Claude Sonnet 4.6) vs highest non-Claude -0.131 (GPT-5.4).
- Binding comparison, cross_edit: lowest Claude point estimate -0.188 (Claude Opus 4.7) vs highest non-Claude -0.316 (GPT-5.4 Mini).

Per BRIEF D4, a pooled fraction < 0.95 means the categorical claim "Claude models increase their moral agency; all other models reinforce external authority" should be replaced by this probability statement.

## Data files

- `analysis/data/analysis/bootstrap/ensemble_bootstrap_summary.json`
- `analysis/data/analysis/bootstrap/ensemble_mean_judge_draws.json`
- `analysis/data/analysis/bootstrap/ensemble_ranking_stability.json`

`*_bootstrap_summary.json` holds every point estimate, interval, and per-round drift percentile; `*_mean_judge_draws.json` holds the full B=2,000 mean-judge draws per (model, stratum) so ranking stability is recomputable; the full B×20 drift draw matrices are not stored (percentiles only).
