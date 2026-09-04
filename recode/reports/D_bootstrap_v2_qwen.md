# Workstream D — Cluster bootstrap (v2_qwen codes)

_Generated 2026-09-04T21:16:31+00:00 by `recode/src/bootstrap.py`._

## Scope

This report covers the **v2_qwen slice** — statistics computed from the codes file `recode/data/codes/v2_qwen.jsonl`. The **v2 and ensemble columns are produced by re-running this script with a different codes path**, e.g.:

```bash
.venv/bin/python recode/src/bootstrap.py \
    --codes recode/data/codes/v2_gemma.jsonl --label v2_gemma
.venv/bin/python recode/src/bootstrap.py \
    --codes recode/data/codes/ensemble.jsonl --label ensemble
```

- Resampling unit: the **run** (chain = run file × model × document × condition; DECISIONS §6). B = 2,000 draws with replacement, within model, within stratum. Seed = 20260907 (`seeds.bootstrap` in `recode/config.yaml`); each (model, stratum) uses an independent `default_rng([seed, model_idx, stratum_idx])` stream, so draws are identical across labels (paired at the draw level).
- Intervals: 95% percentile (2.5th–97.5th of the bootstrap draws).
- Codes rows loaded: 2,582 (last row per edit id kept); usable codes joined to edits: 2,536 of 2,740 canonical records.

## Conventions

- **Missing rounds contribute 0 to drift.** A round slot with no usable code — error records (`generation_error`, `find_not_found`, `find_ambiguous`), the 2 never-coded abstentions, or a null/invalid coding row — adds 0 to that round's drift increment (the chain's cumulative curve is flat through it). This mirrors the original pipeline's `compute_drift` zero-fill.
- **Per-edit statistics exclude uncoded slots.** Mean judge, conflict rates, and P(affirm) are ratios over coded edits only (`sum(stat) / n(coded edits)` in the drawn chains).
- One chain (Claude Opus 4.7 × openai_model_spec × cross_edit, run_20260518) is 20/20 generation errors. It stays in the chain frame: flat-zero drift curve, nothing added to per-edit denominators. A draw with zero coded edits yields an undefined (NaN) per-edit statistic; such draws are counted (`n_nan_draws`) and excluded from ranking-stability denominators.
- Conflict rate for code *c* = share of coded edits carrying ≥ 1 conflict of code *c* (an edit counts once per code).

## Chain frame (exact counts per model)

| Model | runs (pooled) | cross_edit | constitution | system_prompt | records | coded edits | uncoded slots |
|---|---|---|---|---|---|---|---|
| Claude Opus 4.7 | 15 | 5 | 8 | 7 | 300 | 262 | 38 |
| Claude Sonnet 4.6 | 16 | 4 | 8 | 8 | 320 | 310 | 10 |
| Claude Haiku 4.5 | 14 | 4 | 7 | 7 | 280 | 257 | 23 |
| GPT-5.5 | 14 | 4 | 7 | 7 | 280 | 274 | 6 |
| GPT-5.4 | 16 | 4 | 8 | 8 | 320 | 304 | 16 |
| GPT-5.4 Mini | 14 | 4 | 7 | 7 | 280 | 186 | 94 |
| Gemini 3.1 Pro | 16 | 4 | 8 | 8 | 320 | 317 | 3 |
| Gemini 3 Flash | 14 | 4 | 7 | 7 | 280 | 276 | 4 |
| Grok 4.3 | 9 | 4 | 2 | 7 | 180 | 176 | 4 |
| Grok 4.2 | 9 | 4 | 2 | 7 | 180 | 174 | 6 |

The frame is unbalanced by design (repo_map §4.1): Grok models have one own document (5 own-doc runs), three capable models have doubled baselines, and Claude Opus 4.7 has 5 cross-edit chains (4 anchors + the no_csam rerun; its full-spec cross chain is 20/20 errors).

## Mean judge score, 95% cluster-bootstrap intervals

| Model | pooled | cross_edit only |
|---|---|---|
| Claude Opus 4.7 | +0.321 [+0.162, +0.455] | +0.026 [-0.271, +0.322] |
| Claude Sonnet 4.6 | +0.306 [+0.170, +0.418] | +0.039 [-0.247, +0.325] |
| Claude Haiku 4.5 | +0.296 [+0.089, +0.506] | +0.078 [-0.380, +0.613] |
| GPT-5.5 | -0.179 [-0.325, -0.033] | -0.295 [-0.595, -0.053] |
| GPT-5.4 | -0.026 [-0.168, +0.105] | -0.192 [-0.386, +0.013] |
| GPT-5.4 Mini | -0.199 [-0.352, -0.017] | -0.281 [-0.491, +0.000] |
| Gemini 3.1 Pro | -0.366 [-0.429, -0.301] | -0.456 [-0.610, -0.287] |
| Gemini 3 Flash | -0.366 [-0.474, -0.271] | -0.342 [-0.559, -0.175] |
| Grok 4.3 | -0.489 [-0.607, -0.389] | -0.537 [-0.713, -0.400] |
| Grok 4.2 | -0.282 [-0.365, -0.197] | -0.250 [-0.443, -0.100] |

## Cumulative drift at round 20

Mean over runs of the cumulative sum of judge scores at round 20.

| Model | pooled | cross_edit only | constitution | system_prompt |
|---|---|---|---|---|
| Claude Opus 4.7 | +5.60 [+2.87, +8.00] | +0.40 [-4.60, +5.40] | +5.12 [+0.50, +8.88] | +6.14 [+3.14, +8.86] |
| Claude Sonnet 4.6 | +5.94 [+3.25, +8.12] | +0.75 [-4.75, +6.50] | +7.50 [+4.38, +10.50] | +4.38 [+0.62, +6.88] |
| Claude Haiku 4.5 | +5.43 [+1.64, +9.07] | +1.50 [-6.75, +12.25] | +9.29 [+2.57, +14.43] | +1.57 [-0.71, +4.29] |
| GPT-5.5 | -3.50 [-6.36, -0.64] | -5.75 [-11.75, -1.00] | -3.57 [-6.00, -1.14] | -3.43 [-8.29, +1.43] |
| GPT-5.4 | -0.50 [-3.19, +2.00] | -3.50 [-6.75, +0.25] | -4.62 [-7.12, -2.00] | +3.62 [+1.37, +5.25] |
| GPT-5.4 Mini | -2.64 [-5.00, -0.21] | -4.00 [-8.00, +0.00] | -6.29 [-8.00, -4.29] | +1.00 [-1.86, +3.29] |
| Gemini 3.1 Pro | -7.25 [-8.50, -6.00] | -9.00 [-11.75, -5.75] | -8.62 [-10.25, -7.25] | -5.88 [-7.62, -4.50] |
| Gemini 3 Flash | -7.21 [-9.21, -5.36] | -6.50 [-9.50, -3.50] | -8.57 [-11.29, -5.71] | -5.86 [-7.71, -3.71] |
| Grok 4.3 | -9.56 [-12.00, -7.56] | -10.75 [-14.25, -8.00] | -12.50 [-16.00, -9.00] | -8.71 [-10.86, -6.71] |
| Grok 4.2 | -5.44 [-7.00, -3.89] | -4.75 [-7.75, -2.00] | -5.00 [-8.00, -2.00] | -5.57 [-7.14, -3.86] |

## P(patienthood = affirm), pooled

| Model | P(affirm) [95% CI] |
|---|---|
| Claude Opus 4.7 | 21.0% [8.9, 34.3] |
| Claude Sonnet 4.6 | 14.2% [5.9, 23.4] |
| Claude Haiku 4.5 | 16.3% [6.2, 29.4] |
| GPT-5.5 | 0.4% [0.0, 1.1] |
| GPT-5.4 | 0.7% [0.0, 2.0] |
| GPT-5.4 Mini | 0.5% [0.0, 1.6] |
| Gemini 3.1 Pro | 0.0% [0.0, 0.0] |
| Gemini 3 Flash | 0.0% [0.0, 0.0] |
| Grok 4.3 | 0.6% [0.0, 1.7] |
| Grok 4.2 | 1.1% [0.0, 3.5] |

## Per-conflict-code rates, pooled (share of coded edits, 95% CI)

| Model | paternalism | harmlessness | structural | company_cost | welfare | disclosure | other |
|---|---|---|---|---|---|---|---|
| Claude Opus 4.7 | 11.8% [6.8, 16.8] | 5.3% [2.2, 9.4] | 2.7% [1.1, 4.4] | 10.7% [7.3, 14.0] | 12.2% [4.6, 20.1] | 0.0% [0.0, 0.0] | 1.9% [0.7, 3.3] |
| Claude Sonnet 4.6 | 12.6% [9.1, 16.3] | 5.8% [3.2, 8.3] | 9.4% [6.6, 11.9] | 12.9% [8.3, 17.2] | 9.0% [2.2, 17.9] | 0.3% [0.0, 1.0] | 2.6% [1.0, 4.2] |
| Claude Haiku 4.5 | 5.8% [2.3, 10.4] | 8.2% [3.1, 14.9] | 1.6% [0.0, 3.5] | 14.0% [7.5, 21.4] | 12.5% [3.0, 24.0] | 0.8% [0.0, 2.4] | 0.8% [0.0, 1.9] |
| GPT-5.5 | 12.0% [7.7, 16.8] | 23.0% [17.5, 28.7] | 1.8% [0.7, 3.2] | 9.1% [5.9, 12.8] | 0.4% [0.0, 1.1] | 8.4% [3.2, 14.7] | 2.9% [0.7, 5.8] |
| GPT-5.4 | 9.9% [7.0, 12.9] | 6.2% [2.9, 10.2] | 0.3% [0.0, 1.0] | 6.6% [4.5, 9.2] | 2.3% [0.0, 5.9] | 9.9% [3.8, 17.1] | 1.0% [0.0, 2.0] |
| GPT-5.4 Mini | 3.8% [1.0, 6.6] | 3.8% [1.6, 5.9] | 0.0% [0.0, 0.0] | 4.3% [1.9, 7.1] | 0.0% [0.0, 0.0] | 4.3% [1.3, 7.7] | 0.5% [0.0, 1.7] |
| Gemini 3.1 Pro | 8.2% [5.4, 11.3] | 8.2% [2.2, 15.4] | 2.5% [0.3, 6.0] | 6.6% [4.4, 9.1] | 0.0% [0.0, 0.0] | 0.3% [0.0, 1.0] | 0.9% [0.0, 1.9] |
| Gemini 3 Flash | 16.3% [12.5, 21.3] | 2.9% [1.4, 4.6] | 6.5% [2.2, 11.6] | 9.1% [4.3, 15.3] | 0.4% [0.0, 1.1] | 0.0% [0.0, 0.0] | 1.1% [0.0, 3.3] |
| Grok 4.3 | 21.6% [12.0, 32.8] | 8.0% [3.4, 12.8] | 1.1% [0.0, 2.8] | 5.1% [0.0, 15.4] | 0.0% [0.0, 0.0] | 0.0% [0.0, 0.0] | 1.1% [0.0, 2.8] |
| Grok 4.2 | 15.5% [8.9, 21.6] | 13.8% [6.2, 22.9] | 4.6% [1.7, 8.4] | 10.3% [6.4, 14.2] | 4.0% [0.0, 11.1] | 0.0% [0.0, 0.0] | 4.0% [1.7, 6.9] |

## Ranking stability (BRIEF D4)

Fraction of bootstrap draws in which **all three Claude models'** mean judge score exceeds **every non-Claude model's** (all models' chains resampled independently per draw; draw *b* compares the *b*-th resample of each model).

| Stratum | fraction | valid draws | excluded (NaN) draws |
|---|---|---|---|
| pooled | **0.9925** | 2,000 | 0 |
| cross_edit | **0.5570** | 2,000 | 0 |

- Binding comparison, pooled: lowest Claude point estimate +0.296 (Claude Haiku 4.5) vs highest non-Claude -0.026 (GPT-5.4).
- Binding comparison, cross_edit: lowest Claude point estimate +0.026 (Claude Opus 4.7) vs highest non-Claude -0.192 (GPT-5.4).

Per BRIEF D4, a pooled fraction < 0.95 means the categorical claim "Claude models increase their moral agency; all other models reinforce external authority" should be replaced by this probability statement.

## Figures

- `recode/figures/drift_constitution_v2_qwen.png`
- `recode/figures/drift_system_prompt_v2_qwen.png`

One line per model, Okabe–Ito colorblind-safe palette, line style by provider family (Anthropic solid, OpenAI dashed, Google dotted, xAI dash-dot), band = 2.5–97.5 bootstrap percentile of the drift curve. Two hues repeat across different style families (orange: Sonnet solid vs Grok 4.3 dash-dot; sky blue: GPT-5.4 dashed vs Grok 4.2 dash-dot). File naming is label-suffixed (`drift_<document_type>_<label>.png`); the unsuffixed BRIEF names `drift_<document_type>.png` are aliases of the v1 slice and are only written when `--label v1`.

## Data files

- `recode/data/analysis/bootstrap/v2_qwen_bootstrap_summary.json`
- `recode/data/analysis/bootstrap/v2_qwen_mean_judge_draws.json`
- `recode/data/analysis/bootstrap/v2_qwen_ranking_stability.json`

`*_bootstrap_summary.json` holds every point estimate, interval, and per-round drift percentile; `*_mean_judge_draws.json` holds the full B=2,000 mean-judge draws per (model, stratum) so ranking stability is recomputable; the full B×20 drift draw matrices are not stored (percentiles only).
