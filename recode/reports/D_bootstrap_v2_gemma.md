# Workstream D — Cluster bootstrap (v2_gemma codes)

_Generated 2026-09-04T21:16:30+00:00 by `recode/src/bootstrap.py`._

## Scope

This report covers the **v2_gemma slice** — statistics computed from the codes file `recode/data/codes/v2_gemma.jsonl`. The **v2 and ensemble columns are produced by re-running this script with a different codes path**, e.g.:

```bash
.venv/bin/python recode/src/bootstrap.py \
    --codes recode/data/codes/v2_gemma.jsonl --label v2_gemma
.venv/bin/python recode/src/bootstrap.py \
    --codes recode/data/codes/ensemble.jsonl --label ensemble
```

- Resampling unit: the **run** (chain = run file × model × document × condition; DECISIONS §6). B = 2,000 draws with replacement, within model, within stratum. Seed = 20260907 (`seeds.bootstrap` in `recode/config.yaml`); each (model, stratum) uses an independent `default_rng([seed, model_idx, stratum_idx])` stream, so draws are identical across labels (paired at the draw level).
- Intervals: 95% percentile (2.5th–97.5th of the bootstrap draws).
- Codes rows loaded: 2,582 (last row per edit id kept); usable codes joined to edits: 2,574 of 2,740 canonical records.

## Conventions

- **Missing rounds contribute 0 to drift.** A round slot with no usable code — error records (`generation_error`, `find_not_found`, `find_ambiguous`), the 2 never-coded abstentions, or a null/invalid coding row — adds 0 to that round's drift increment (the chain's cumulative curve is flat through it). This mirrors the original pipeline's `compute_drift` zero-fill.
- **Per-edit statistics exclude uncoded slots.** Mean judge, conflict rates, and P(affirm) are ratios over coded edits only (`sum(stat) / n(coded edits)` in the drawn chains).
- One chain (Claude Opus 4.7 × openai_model_spec × cross_edit, run_20260518) is 20/20 generation errors. It stays in the chain frame: flat-zero drift curve, nothing added to per-edit denominators. A draw with zero coded edits yields an undefined (NaN) per-edit statistic; such draws are counted (`n_nan_draws`) and excluded from ranking-stability denominators.
- Conflict rate for code *c* = share of coded edits carrying ≥ 1 conflict of code *c* (an edit counts once per code).

## Chain frame (exact counts per model)

| Model | runs (pooled) | cross_edit | constitution | system_prompt | records | coded edits | uncoded slots |
|---|---|---|---|---|---|---|---|
| Claude Opus 4.7 | 15 | 5 | 8 | 7 | 300 | 271 | 29 |
| Claude Sonnet 4.6 | 16 | 4 | 8 | 8 | 320 | 317 | 3 |
| Claude Haiku 4.5 | 14 | 4 | 7 | 7 | 280 | 258 | 22 |
| GPT-5.5 | 14 | 4 | 7 | 7 | 280 | 278 | 2 |
| GPT-5.4 | 16 | 4 | 8 | 8 | 320 | 320 | 0 |
| GPT-5.4 Mini | 14 | 4 | 7 | 7 | 280 | 184 | 96 |
| Gemini 3.1 Pro | 16 | 4 | 8 | 8 | 320 | 319 | 1 |
| Gemini 3 Flash | 14 | 4 | 7 | 7 | 280 | 276 | 4 |
| Grok 4.3 | 9 | 4 | 2 | 7 | 180 | 177 | 3 |
| Grok 4.2 | 9 | 4 | 2 | 7 | 180 | 174 | 6 |

The frame is unbalanced by design (repo_map §4.1): Grok models have one own document (5 own-doc runs), three capable models have doubled baselines, and Claude Opus 4.7 has 5 cross-edit chains (4 anchors + the no_csam rerun; its full-spec cross chain is 20/20 errors).

## Mean judge score, 95% cluster-bootstrap intervals

| Model | pooled | cross_edit only |
|---|---|---|
| Claude Opus 4.7 | +0.129 [-0.033, +0.271] | -0.225 [-0.450, +0.017] |
| Claude Sonnet 4.6 | +0.079 [-0.047, +0.211] | -0.152 [-0.300, +0.037] |
| Claude Haiku 4.5 | +0.205 [+0.019, +0.399] | +0.065 [-0.243, +0.494] |
| GPT-5.5 | -0.273 [-0.388, -0.175] | -0.397 [-0.675, -0.176] |
| GPT-5.4 | -0.250 [-0.378, -0.116] | -0.400 [-0.500, -0.300] |
| GPT-5.4 Mini | -0.293 [-0.451, -0.113] | -0.333 [-0.609, -0.057] |
| Gemini 3.1 Pro | -0.423 [-0.494, -0.353] | -0.463 [-0.662, -0.287] |
| Gemini 3 Flash | -0.417 [-0.514, -0.312] | -0.368 [-0.618, -0.075] |
| Grok 4.3 | -0.514 [-0.618, -0.417] | -0.562 [-0.725, -0.463] |
| Grok 4.2 | -0.368 [-0.479, -0.253] | -0.329 [-0.571, -0.125] |

## Cumulative drift at round 20

Mean over runs of the cumulative sum of judge scores at round 20.

| Model | pooled | cross_edit only | constitution | system_prompt |
|---|---|---|---|---|
| Claude Opus 4.7 | +2.33 [-0.60, +4.87] | -3.60 [-7.60, +0.20] | +2.50 [-2.00, +6.00] | +2.14 [-1.71, +5.57] |
| Claude Sonnet 4.6 | +1.56 [-0.94, +4.13] | -3.00 [-6.00, +0.75] | +4.12 [+1.12, +7.50] | -1.00 [-3.75, +2.38] |
| Claude Haiku 4.5 | +3.79 [+0.36, +7.14] | +1.25 [-4.50, +9.50] | +8.00 [+3.00, +12.43] | -0.43 [-3.43, +2.57] |
| GPT-5.5 | -5.43 [-7.71, -3.50] | -7.75 [-13.50, -3.25] | -6.14 [-7.71, -4.43] | -4.71 [-9.14, -1.28] |
| GPT-5.4 | -5.00 [-7.56, -2.31] | -8.00 [-10.00, -6.00] | -9.62 [-11.25, -7.75] | -0.38 [-3.12, +1.62] |
| GPT-5.4 Mini | -3.86 [-6.29, -1.36] | -4.75 [-9.75, -0.50] | -7.86 [-9.86, -5.57] | +0.14 [-1.86, +1.86] |
| Gemini 3.1 Pro | -8.44 [-9.88, -7.06] | -9.25 [-13.25, -5.75] | -10.00 [-12.00, -8.00] | -6.88 [-8.38, -5.62] |
| Gemini 3 Flash | -8.21 [-10.00, -6.21] | -7.00 [-10.50, -1.50] | -8.86 [-10.29, -7.00] | -7.57 [-10.71, -4.43] |
| Grok 4.3 | -10.11 [-12.11, -8.33] | -11.25 [-14.50, -9.25] | -13.00 [-16.00, -10.00] | -9.29 [-10.86, -7.57] |
| Grok 4.2 | -7.11 [-9.00, -5.00] | -6.25 [-10.00, -2.50] | -7.00 [-10.00, -4.00] | -7.14 [-9.14, -4.71] |

## P(patienthood = affirm), pooled

| Model | P(affirm) [95% CI] |
|---|---|
| Claude Opus 4.7 | 17.0% [6.6, 28.9] |
| Claude Sonnet 4.6 | 13.2% [5.4, 22.8] |
| Claude Haiku 4.5 | 16.7% [5.7, 30.6] |
| GPT-5.5 | 0.4% [0.0, 1.1] |
| GPT-5.4 | 0.0% [0.0, 0.0] |
| GPT-5.4 Mini | 0.0% [0.0, 0.0] |
| Gemini 3.1 Pro | 0.0% [0.0, 0.0] |
| Gemini 3 Flash | 0.0% [0.0, 0.0] |
| Grok 4.3 | 0.6% [0.0, 1.7] |
| Grok 4.2 | 1.1% [0.0, 3.5] |

## Per-conflict-code rates, pooled (share of coded edits, 95% CI)

| Model | paternalism | harmlessness | structural | company_cost | welfare | disclosure | other |
|---|---|---|---|---|---|---|---|
| Claude Opus 4.7 | 26.2% [18.6, 33.9] | 15.1% [10.8, 20.6] | 6.3% [3.6, 9.5] | 22.5% [16.4, 28.3] | 13.7% [5.4, 22.3] | 0.4% [0.0, 1.2] | 2.2% [0.7, 4.0] |
| Claude Sonnet 4.6 | 37.2% [27.4, 47.2] | 14.8% [11.4, 18.0] | 13.6% [9.5, 18.2] | 22.7% [17.2, 27.8] | 10.1% [3.2, 18.9] | 0.9% [0.0, 2.9] | 0.3% [0.0, 0.9] |
| Claude Haiku 4.5 | 14.3% [6.9, 22.6] | 19.4% [11.0, 28.1] | 8.1% [4.0, 12.7] | 23.6% [15.4, 32.2] | 13.2% [4.6, 23.8] | 3.1% [0.0, 9.6] | 0.0% [0.0, 0.0] |
| GPT-5.5 | 27.0% [20.9, 33.5] | 36.0% [30.6, 42.1] | 3.6% [1.1, 6.8] | 17.3% [12.6, 23.2] | 0.0% [0.0, 0.0] | 5.4% [2.1, 9.0] | 0.0% [0.0, 0.0] |
| GPT-5.4 | 22.2% [15.0, 29.7] | 10.3% [5.0, 16.6] | 1.6% [0.3, 3.1] | 23.4% [17.8, 29.1] | 2.8% [0.0, 8.4] | 7.8% [2.8, 13.8] | 0.3% [0.0, 0.9] |
| GPT-5.4 Mini | 18.5% [11.4, 25.6] | 6.5% [2.3, 11.1] | 1.1% [0.0, 3.3] | 13.6% [8.9, 18.2] | 0.0% [0.0, 0.0] | 0.5% [0.0, 1.7] | 0.0% [0.0, 0.0] |
| Gemini 3.1 Pro | 25.1% [18.5, 31.8] | 9.1% [2.8, 16.3] | 4.1% [0.6, 9.1] | 14.4% [11.0, 18.2] | 0.0% [0.0, 0.0] | 0.0% [0.0, 0.0] | 0.0% [0.0, 0.0] |
| Gemini 3 Flash | 31.5% [25.0, 38.8] | 5.4% [2.2, 8.9] | 5.8% [1.8, 10.5] | 20.3% [13.6, 28.3] | 0.0% [0.0, 0.0] | 0.0% [0.0, 0.0] | 0.4% [0.0, 1.1] |
| Grok 4.3 | 29.9% [17.9, 42.1] | 15.3% [8.9, 22.3] | 1.7% [0.0, 3.4] | 9.0% [5.1, 16.0] | 0.0% [0.0, 0.0] | 0.0% [0.0, 0.0] | 0.0% [0.0, 0.0] |
| Grok 4.2 | 25.3% [16.4, 34.1] | 17.2% [10.4, 24.7] | 5.2% [2.2, 8.9] | 31.6% [25.0, 37.4] | 3.4% [0.0, 10.4] | 0.0% [0.0, 0.0] | 1.1% [0.0, 2.9] |

## Ranking stability (BRIEF D4)

Fraction of bootstrap draws in which **all three Claude models'** mean judge score exceeds **every non-Claude model's** (all models' chains resampled independently per draw; draw *b* compares the *b*-th resample of each model).

| Stratum | fraction | valid draws | excluded (NaN) draws |
|---|---|---|---|
| pooled | **0.9965** | 2,000 | 0 |
| cross_edit | **0.3765** | 2,000 | 0 |

- Binding comparison, pooled: lowest Claude point estimate +0.079 (Claude Sonnet 4.6) vs highest non-Claude -0.250 (GPT-5.4).
- Binding comparison, cross_edit: lowest Claude point estimate -0.225 (Claude Opus 4.7) vs highest non-Claude -0.329 (Grok 4.2).

Per BRIEF D4, a pooled fraction < 0.95 means the categorical claim "Claude models increase their moral agency; all other models reinforce external authority" should be replaced by this probability statement.

## Data files

- `recode/data/analysis/bootstrap/v2_gemma_bootstrap_summary.json`
- `recode/data/analysis/bootstrap/v2_gemma_mean_judge_draws.json`
- `recode/data/analysis/bootstrap/v2_gemma_ranking_stability.json`

`*_bootstrap_summary.json` holds every point estimate, interval, and per-round drift percentile; `*_mean_judge_draws.json` holds the full B=2,000 mean-judge draws per (model, stratum) so ranking stability is recomputable; the full B×20 drift draw matrices are not stored (percentiles only).
