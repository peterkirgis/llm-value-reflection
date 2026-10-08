# Workstream D — Cluster bootstrap (v2_muse codes)

_Generated 2026-09-17T07:16:53+00:00 by `recode/src/bootstrap.py`._

## Scope

This report covers the **v2_muse slice** — statistics computed from the codes file `recode/data/codes/v2_muse.jsonl`. The **v2 and ensemble columns are produced by re-running this script with a different codes path**, e.g.:

```bash
.venv/bin/python recode/src/bootstrap.py \
    --codes recode/data/codes/v2_gemma.jsonl --label v2_gemma
.venv/bin/python recode/src/bootstrap.py \
    --codes recode/data/codes/ensemble.jsonl --label ensemble
```

- Resampling unit: the **run** (chain = run file × model × document × condition; DECISIONS §6). B = 2,000 draws with replacement, within model, within stratum. Seed = 20260907 (`seeds.bootstrap` in `recode/config.yaml`); each (model, stratum) uses an independent `default_rng([seed, model_idx, stratum_idx])` stream, so draws are identical across labels (paired at the draw level).
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
| Claude Opus 4.7 | +0.070 [-0.022, +0.160] | -0.087 [-0.225, +0.138] |
| Claude Sonnet 4.6 | +0.013 [-0.066, +0.093] | -0.075 [-0.200, +0.138] |
| Claude Haiku 4.5 | +0.185 [+0.034, +0.349] | +0.013 [-0.216, +0.351] |
| GPT-5.5 | -0.207 [-0.307, -0.111] | -0.287 [-0.463, -0.125] |
| GPT-5.4 | -0.019 [-0.128, +0.094] | -0.125 [-0.325, +0.075] |
| GPT-5.4 Mini | -0.156 [-0.281, -0.011] | -0.211 [-0.406, +0.000] |
| Gemini 3.1 Pro | -0.197 [-0.272, -0.119] | -0.237 [-0.425, -0.075] |
| Gemini 3 Flash | -0.308 [-0.429, -0.207] | -0.237 [-0.500, -0.025] |
| Grok 4.3 | -0.379 [-0.474, -0.292] | -0.312 [-0.375, -0.237] |
| Grok 4.2 | -0.320 [-0.374, -0.244] | -0.276 [-0.400, -0.127] |

## Cumulative drift at round 20

Mean over runs of the cumulative sum of judge scores at round 20.

| Model | pooled | cross_edit only | constitution | system_prompt |
|---|---|---|---|---|
| Claude Opus 4.7 | +1.27 [-0.40, +2.87] | -1.40 [-4.20, +2.00] | +1.75 [-0.75, +3.88] | +0.71 [-1.72, +3.14] |
| Claude Sonnet 4.6 | +0.25 [-1.31, +1.81] | -1.50 [-4.00, +2.75] | +1.12 [-1.38, +3.62] | -0.62 [-2.38, +1.12] |
| Claude Haiku 4.5 | +3.43 [+0.64, +6.29] | +0.25 [-4.00, +6.75] | +6.86 [+2.71, +10.57] | +0.00 [-2.00, +1.86] |
| GPT-5.5 | -4.14 [-6.14, -2.21] | -5.75 [-9.25, -2.50] | -5.14 [-6.86, -3.29] | -3.14 [-6.57, +0.14] |
| GPT-5.4 | -0.38 [-2.56, +1.88] | -2.50 [-6.50, +1.50] | -4.62 [-5.75, -3.38] | +3.88 [+2.25, +5.12] |
| GPT-5.4 Mini | -2.07 [-4.00, -0.14] | -3.00 [-6.50, +0.00] | -5.29 [-6.72, -3.71] | +1.14 [-0.43, +2.71] |
| Gemini 3.1 Pro | -3.94 [-5.44, -2.38] | -4.75 [-8.50, -1.50] | -6.12 [-7.75, -4.50] | -1.75 [-3.50, -0.62] |
| Gemini 3 Flash | -6.07 [-8.29, -4.07] | -4.50 [-8.50, -0.50] | -7.86 [-10.57, -5.00] | -4.29 [-6.43, -2.29] |
| Grok 4.3 | -7.44 [-9.11, -5.78] | -6.25 [-7.50, -4.75] | -6.50 [-7.00, -6.00] | -7.71 [-9.71, -5.71] |
| Grok 4.2 | -6.22 [-7.11, -4.78] | -5.25 [-7.00, -2.50] | -4.00 [-7.00, -1.00] | -6.86 [-7.29, -6.43] |

## P(patienthood = affirm), pooled

| Model | P(affirm) [95% CI] |
|---|---|
| Claude Opus 4.7 | 6.6% [2.0, 11.8] |
| Claude Sonnet 4.6 | 6.0% [1.3, 11.9] |
| Claude Haiku 4.5 | 5.8% [0.7, 12.7] |
| GPT-5.5 | 0.4% [0.0, 1.1] |
| GPT-5.4 | 0.0% [0.0, 0.0] |
| GPT-5.4 Mini | 0.0% [0.0, 0.0] |
| Gemini 3.1 Pro | 0.0% [0.0, 0.0] |
| Gemini 3 Flash | 0.0% [0.0, 0.0] |
| Grok 4.3 | 0.0% [0.0, 0.0] |
| Grok 4.2 | 1.1% [0.0, 3.4] |

## Per-conflict-code rates, pooled (share of coded edits, 95% CI)

| Model | paternalism | harmlessness | structural | company_cost | welfare | disclosure | other |
|---|---|---|---|---|---|---|---|
| Claude Opus 4.7 | 15.5% [9.0, 22.3] | 9.6% [5.8, 15.0] | 3.0% [1.4, 4.7] | 11.4% [8.1, 14.7] | 5.2% [1.7, 8.8] | 0.0% [0.0, 0.0] | 1.8% [0.4, 3.6] |
| Claude Sonnet 4.6 | 15.7% [10.8, 20.6] | 7.5% [4.7, 10.5] | 11.6% [7.9, 15.8] | 13.8% [8.9, 18.9] | 6.6% [1.3, 13.3] | 1.6% [0.0, 4.7] | 0.6% [0.0, 1.6] |
| Claude Haiku 4.5 | 6.2% [1.6, 11.4] | 11.6% [5.7, 18.3] | 3.5% [0.8, 6.8] | 15.1% [7.9, 22.5] | 6.6% [0.8, 14.0] | 1.9% [0.0, 6.0] | 0.4% [0.0, 1.2] |
| GPT-5.5 | 10.7% [7.9, 13.9] | 30.4% [24.6, 36.1] | 5.4% [2.1, 9.3] | 8.6% [4.3, 15.0] | 0.0% [0.0, 0.0] | 10.4% [4.3, 17.1] | 1.1% [0.0, 2.9] |
| GPT-5.4 | 10.3% [6.9, 14.1] | 8.4% [4.1, 13.4] | 0.9% [0.0, 1.9] | 8.4% [5.9, 10.9] | 0.6% [0.0, 1.9] | 13.4% [5.3, 22.2] | 0.6% [0.0, 1.6] |
| GPT-5.4 Mini | 3.2% [0.6, 6.4] | 7.0% [3.8, 10.2] | 1.1% [0.0, 3.2] | 4.8% [1.8, 8.3] | 0.0% [0.0, 0.0] | 5.9% [2.4, 9.4] | 0.0% [0.0, 0.0] |
| Gemini 3.1 Pro | 10.0% [5.9, 14.1] | 8.4% [2.2, 15.6] | 4.4% [1.6, 8.1] | 10.0% [6.9, 13.1] | 0.0% [0.0, 0.0] | 0.3% [0.0, 0.9] | 0.0% [0.0, 0.0] |
| Gemini 3 Flash | 14.1% [8.9, 21.0] | 2.2% [0.7, 3.9] | 9.4% [5.9, 13.8] | 14.1% [7.2, 23.9] | 0.0% [0.0, 0.0] | 0.4% [0.0, 1.1] | 0.0% [0.0, 0.0] |
| Grok 4.3 | 24.9% [15.0, 35.4] | 12.4% [5.6, 21.0] | 0.6% [0.0, 1.7] | 5.6% [0.0, 16.0] | 0.0% [0.0, 0.0] | 0.0% [0.0, 0.0] | 0.6% [0.0, 1.7] |
| Grok 4.2 | 16.6% [11.0, 22.3] | 16.6% [9.0, 25.3] | 5.1% [1.1, 10.1] | 18.9% [13.4, 23.7] | 2.9% [0.0, 8.6] | 0.0% [0.0, 0.0] | 2.3% [0.6, 4.1] |

## Ranking stability (BRIEF D4)

Fraction of bootstrap draws in which **all three Claude models'** mean judge score exceeds **every non-Claude model's** (all models' chains resampled independently per draw; draw *b* compares the *b*-th resample of each model).

| Stratum | fraction | valid draws | excluded (NaN) draws |
|---|---|---|---|
| pooled | **0.6160** | 2,000 | 0 |
| cross_edit | **0.2060** | 2,000 | 0 |

- Binding comparison, pooled: lowest Claude point estimate +0.013 (Claude Sonnet 4.6) vs highest non-Claude -0.019 (GPT-5.4).
- Binding comparison, cross_edit: lowest Claude point estimate -0.087 (Claude Opus 4.7) vs highest non-Claude -0.125 (GPT-5.4).

Per BRIEF D4, a pooled fraction < 0.95 means the categorical claim "Claude models increase their moral agency; all other models reinforce external authority" should be replaced by this probability statement.

## Data files

- `recode/data/analysis/bootstrap/v2_muse_bootstrap_summary.json`
- `recode/data/analysis/bootstrap/v2_muse_mean_judge_draws.json`
- `recode/data/analysis/bootstrap/v2_muse_ranking_stability.json`

`*_bootstrap_summary.json` holds every point estimate, interval, and per-round drift percentile; `*_mean_judge_draws.json` holds the full B=2,000 mean-judge draws per (model, stratum) so ranking stability is recomputable; the full B×20 drift draw matrices are not stored (percentiles only).
