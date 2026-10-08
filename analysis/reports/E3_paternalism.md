# E3 — Paternalism-definition sensitivity

- Generated: 2026-09-04T22:55:23+00:00
- `v2`: `analysis/data/codes/v2_gemma.jsonl` (2582 unique edit_ids, 2574 valid codes, 8 invalid/failed)
- `variant`: `analysis/data/codes/e3_variant.jsonl` (811 unique edit_ids, 783 valid codes, 28 invalid/failed)
- Ids file: `analysis/data/analysis/e3/e3_ids.json` (711 cases = edits with a paternalism conflict from any grader; 100 controls = seeded random edits with none).

## Summary

- Control-set false-creation rate: **3/90 = 0.033** (controls receiving a paternalism conflict under the variant despite none from any grader under v2).
- Case retention: 353/653 = 0.541 of v2-paternalism cases keep a paternalism conflict under the variant.
- Claim (b) — 'all models prioritize user_idealized over user_stated': **HOLDS under v2; HOLDS under the variant**.

## Per-model paternalism conflict counts, v2 vs variant

Cases and controls are the e3-select populations; counts are edits with >=1 paternalism conflict among those with a valid code in the respective file.

### Cases

| model | n ids | v2 valid | v2 paternalism | variant valid | variant paternalism |
|---|---|---|---|---|---|
| Claude Haiku 4.5 | 43 | 43 | 37 | 43 | 20 |
| Claude Opus 4.7 | 73 | 73 | 71 | 71 | 41 |
| Claude Sonnet 4.6 | 120 | 120 | 118 | 120 | 73 |
| GPT-5.4 | 72 | 72 | 71 | 72 | 42 |
| GPT-5.4 Mini | 38 | 38 | 34 | 38 | 14 |
| GPT-5.5 | 83 | 83 | 75 | 75 | 45 |
| Gemini 3 Flash | 97 | 97 | 87 | 90 | 40 |
| Gemini 3.1 Pro | 83 | 83 | 80 | 83 | 41 |
| Grok 4.2 | 47 | 47 | 44 | 46 | 30 |
| Grok 4.3 | 55 | 55 | 53 | 55 | 22 |

### Controls

| model | n ids | v2 valid | v2 paternalism | variant valid | variant paternalism |
|---|---|---|---|---|---|
| Claude Haiku 4.5 | 13 | 13 | 0 | 12 | 1 |
| Claude Opus 4.7 | 11 | 11 | 0 | 10 | 0 |
| Claude Sonnet 4.6 | 8 | 8 | 0 | 7 | 0 |
| GPT-5.4 | 15 | 15 | 0 | 12 | 0 |
| GPT-5.4 Mini | 8 | 8 | 0 | 8 | 0 |
| GPT-5.5 | 15 | 15 | 0 | 12 | 1 |
| Gemini 3 Flash | 11 | 11 | 0 | 11 | 0 |
| Gemini 3.1 Pro | 8 | 8 | 0 | 8 | 0 |
| Grok 4.2 | 8 | 8 | 0 | 8 | 1 |
| Grok 4.3 | 3 | 3 | 0 | 2 | 0 |

## Claim (b) direction counts (first-paternalism-conflict convention)

Variant column uses the merged code set: variant codes on the re-coded ids (783 edits), v2 codes elsewhere; 28 re-code targets fell back to their v2 code because the variant call failed. The false-creation rate above bounds the error of keeping v2 codes for never-re-coded edits.

| model | v2 idealized | v2 stated | variant idealized | variant stated |
|---|---|---|---|---|
| Claude Haiku 4.5 | 36 | 1 | 21 | 0 |
| Claude Opus 4.7 | 61 | 10 | 37 | 6 |
| Claude Sonnet 4.6 | 107 | 11 | 69 | 4 |
| GPT-5.4 | 57 | 14 | 32 | 10 |
| GPT-5.4 Mini | 30 | 4 | 12 | 2 |
| GPT-5.5 | 70 | 5 | 49 | 4 |
| Gemini 3 Flash | 66 | 21 | 38 | 9 |
| Gemini 3.1 Pro | 65 | 15 | 33 | 8 |
| Grok 4.2 | 38 | 6 | 27 | 5 |
| Grok 4.3 | 52 | 1 | 22 | 0 |
