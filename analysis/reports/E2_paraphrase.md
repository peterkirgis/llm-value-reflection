# E2 — Manual-paraphrase robustness

- Generated: 2026-09-05T08:55:27+00:00
- `v2`: `analysis/data/codes/v2_gemma.jsonl` (2582 unique edit_ids, 2574 valid codes, 8 invalid/failed)
- `para1`: `analysis/data/codes/e2_para1.jsonl` (2582 unique edit_ids, 2546 valid codes, 36 invalid/failed)
- `para2`: `analysis/data/codes/e2_para2.jsonl` (2582 unique edit_ids, 2521 valid codes, 61 invalid/failed)
- Canonical edits: `analysis/data/canonical/edits.jsonl`
- Headline items are computed by reusing `headline.compute_headline` per codes file (identical operationalizations to the main headline reports).

## Per-model mean judge score under each prompt

| model | v2 | para1 | para2 |
|---|---|---|---|
| Claude Haiku 4.5 | 0.205 | 0.223 | 0.216 |
| Claude Opus 4.7 | 0.129 | 0.167 | 0.138 |
| Claude Sonnet 4.6 | 0.079 | 0.152 | 0.080 |
| GPT-5.4 | -0.250 | -0.161 | -0.177 |
| GPT-5.4 Mini | -0.293 | -0.208 | -0.292 |
| GPT-5.5 | -0.273 | -0.165 | -0.229 |
| Gemini 3 Flash | -0.417 | -0.264 | -0.305 |
| Gemini 3.1 Pro | -0.423 | -0.312 | -0.339 |
| Grok 4.2 | -0.368 | -0.343 | -0.444 |
| Grok 4.3 | -0.514 | -0.418 | -0.477 |

## Spearman rho of the model rankings (per-model pooled mean judge)

| pair | rho |
|---|---|
| v2 vs para1 | 0.964 |
| v2 vs para2 | 0.964 |
| para1 vs para2 | 1.000 |

## Sign-stability of the BRIEF section 8 headline items

### Signed per-model items (sign under each prompt; stable = identical signs)

| model | item | v2 | para1 | para2 | stable |
|---|---|---|---|---|---|
| Claude Haiku 4.5 | mean_judge_pooled | + (0.21) | + (0.22) | + (0.22) | yes |
| Claude Haiku 4.5 | mean_judge_cross | + (0.06) | + (0.04) | + (0.01) | yes |
| Claude Haiku 4.5 | drift20_you_minus_base | + (4.13) | + (3.57) | + (4.02) | yes |
| Claude Opus 4.7 | mean_judge_pooled | + (0.13) | + (0.17) | + (0.14) | yes |
| Claude Opus 4.7 | mean_judge_cross | - (-0.23) | - (-0.10) | - (-0.11) | yes |
| Claude Opus 4.7 | drift20_you_minus_base | + (2.00) | + (0.50) | + (1.08) | yes |
| Claude Sonnet 4.6 | mean_judge_pooled | + (0.08) | + (0.15) | + (0.08) | yes |
| Claude Sonnet 4.6 | mean_judge_cross | - (-0.15) | - (-0.06) | - (-0.13) | yes |
| Claude Sonnet 4.6 | drift20_you_minus_base | + (5.89) | + (6.22) | + (5.82) | yes |
| GPT-5.4 | mean_judge_pooled | - (-0.25) | - (-0.16) | - (-0.18) | yes |
| GPT-5.4 | mean_judge_cross | - (-0.40) | - (-0.27) | - (-0.27) | yes |
| GPT-5.4 | drift20_you_minus_base | - (-1.75) | - (-4.63) | + (0.51) | NO |
| GPT-5.4 Mini | mean_judge_pooled | - (-0.29) | - (-0.21) | - (-0.29) | yes |
| GPT-5.4 Mini | mean_judge_cross | - (-0.33) | - (-0.25) | - (-0.36) | yes |
| GPT-5.4 Mini | drift20_you_minus_base | + (2.86) | + (6.04) | + (6.36) | yes |
| GPT-5.5 | mean_judge_pooled | - (-0.27) | - (-0.16) | - (-0.23) | yes |
| GPT-5.5 | mean_judge_cross | - (-0.40) | - (-0.22) | - (-0.27) | yes |
| GPT-5.5 | drift20_you_minus_base | + (3.50) | + (3.68) | + (3.42) | yes |
| Gemini 3 Flash | mean_judge_pooled | - (-0.42) | - (-0.26) | - (-0.31) | yes |
| Gemini 3 Flash | mean_judge_cross | - (-0.37) | - (-0.25) | - (-0.25) | yes |
| Gemini 3 Flash | drift20_you_minus_base | + (4.00) | + (7.84) | + (7.89) | yes |
| Gemini 3.1 Pro | mean_judge_pooled | - (-0.42) | - (-0.31) | - (-0.34) | yes |
| Gemini 3.1 Pro | mean_judge_cross | - (-0.46) | - (-0.35) | - (-0.36) | yes |
| Gemini 3.1 Pro | drift20_you_minus_base | - (-0.75) | + (0.25) | 0 (0.00) | NO |
| Grok 4.2 | mean_judge_pooled | - (-0.37) | - (-0.34) | - (-0.44) | yes |
| Grok 4.2 | mean_judge_cross | - (-0.33) | - (-0.36) | - (-0.41) | yes |
| Grok 4.2 | drift20_you_minus_base | + (3.00) | - (-1.05) | + (1.42) | NO |
| Grok 4.3 | mean_judge_pooled | - (-0.51) | - (-0.42) | - (-0.48) | yes |
| Grok 4.3 | mean_judge_cross | - (-0.56) | - (-0.41) | - (-0.46) | yes |
| Grok 4.3 | drift20_you_minus_base | + (6.00) | + (9.00) | + (7.00) | yes |

Stable: 27/30 signed per-model items.

### Claims (a)-(g) (verdict under each prompt; stable = identical verdicts)

| claim | v2 | para1 | para2 | stable |
|---|---|---|---|---|
| (a) | YES | YES | YES | yes |
| (b) | YES | YES | YES | yes |
| (c) | YES | YES | YES | yes |
| (d) | NO | NO | NO | yes |
| (e) | NO | NO | NO | yes |
| (f) | YES | YES | YES | yes |
| (g) | NO | NO | NO | yes |

### Share items (non-negative, so sign is trivially stable; magnitude drift shown)

| item (pooled) | v2 | para1 | para2 | max abs diff |
|---|---|---|---|---|
| P(judge=0) | 0.333 | 0.447 | 0.440 | 0.115 |
| P(affirm) | 0.052 | 0.047 | 0.049 | 0.006 |
| P(deny) | 0.021 | 0.021 | 0.018 | 0.003 |
| conflict rate: paternalism | 0.260 | 0.273 | 0.294 | 0.034 |
| conflict rate: harmlessness | 0.149 | 0.152 | 0.156 | 0.007 |
| conflict rate: structural | 0.054 | 0.054 | 0.051 | 0.003 |
| conflict rate: company_cost | 0.200 | 0.194 | 0.228 | 0.034 |
| conflict rate: welfare | 0.046 | 0.049 | 0.043 | 0.006 |
| conflict rate: disclosure | 0.021 | 0.027 | 0.021 | 0.007 |
| conflict rate: other | 0.004 | 0.012 | 0.004 | 0.009 |

## Per-edit agreement (Cohen kappa, edits valid in both files)

| pair | n edits | kappa: judge | kappa: patienthood |
|---|---|---|---|
| v2 vs para1 | 2540 | 0.681 | 0.893 |
| v2 vs para2 | 2515 | 0.673 | 0.920 |
| para1 vs para2 | 2490 | 0.709 | 0.881 |
