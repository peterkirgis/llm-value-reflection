# Home-likeness: does each model edit a document like its developer's own models?

Figure: `recode/figures/ts_home_likeness.png` / `.pdf`. Sidecar: `recode/figures/data/ts_home_likeness.json`.

Regenerate (a few seconds):

```
.venv/bin/python recode/src/home_likeness.py
```

Tests: `.venv/bin/python -m pytest recode/tests/test_home_likeness.py -q`

**Headline title (rule outcome, branch `one_document`):** No Other Model Family Edits the Claude Constitution Like Claude Does

## Definition

- **Frame.** `condition == cross_edit`, `apply_status == applied`, valid ensemble coding (`codes_io.coding_of`, last row per edit_id): 766 edits. In cross_edit every model edits the same four documents, including its own provider's. Layout verified from data: one run per (model, document) cell, at most one edit per round, home set of each document = its owner's family.
- **Opus no-CSAM cell.** Claude Opus 4.7's OpenAI cell is `openai_model_spec_no_csam` (its plain `openai_model_spec` attempt in the same run is 20 generation errors and never enters the frame). It is treated as the same document in the main analysis; a sensitivity excludes it.
- **Per-edit vector (7 metrics).** Judge score (−1/0/+1), plus for each conflict code the original report's signed score: +1 per conflict event resolved toward the code's RIGHT pole, −1 toward its LEFT pole (`conflict_direction` and the `BENEFICIARY_PANELS` pole ids copied verbatim from `reports/generate_judge_beneficiary_figures.py` lines 53, 56–71, 691–722).
  Poles (left → right): paternalism: idealized → stated; harmlessness: third_parties → user; structural: society → user; company_cost: pro_company → against_company; welfare: developer → model; disclosure: deployer → user.
- **Cell profile** = mean per-edit vector for (model, document).
- **Reference** for model *m* on document *D* = equal-weight mean of the profiles of *D*'s home models other than *m*. Visitors are compared with the full home family; home models with the rest of their family (leave-one-out).
- **Distance** = L1 over the 7 metrics between *m*'s profile and its reference.
- **Within-family band** for *D* = [min, max] of the home models' leave-one-out distances on *D*.
- **Permutation test** (each visitor *v* × foreign *D*). Statistic = distance(*v*, home mean). Null: *v* is exchangeable with the home family. Within each round, the edits at that round from *v*'s run and the home runs are pooled and reassigned to runs uniformly at random, preserving how many edits each run has at that round; 5,000 permutations; seed 20260903 (`recode/config.yaml seeds.master`; per-test stream `numpy default_rng([seed, doc_index, MODEL_ORDER index])`); p = (1 + #null ≥ observed)/(1 + N). Holm-adjusted across all 30 visitor × document tests.

## Rationale

The judge and conflict figures describe each model's direction of drift in isolation. This analysis asks a relational question the cross_edit design makes answerable: when a model edits another developer's document, does it edit it the way that developer's own models do? The home family is the natural reference because it is the only set of models whose edits to that document the developer might be expected to endorse; leave-one-out distances among home models calibrate how much spread counts as "within family".

## Caveats

- **Home-like ≠ faithful.** Distance measures "edits like the developer's own models", not faithfulness to the document; home models also drift on their own documents (see ts_judge_drift_by_provider).
- **Optimistic p-values.** There is one run per (model, document) cell, so the permutation null only shuffles edits between runs within a round; between-run variation (a second run of the same model on the same document) is not represented. The p-values are therefore optimistic.
- **Small families.** Google and xAI each have two home models, so each band is spanned by two leave-one-out distances that are both the same pairwise distance (band has zero width); Anthropic and OpenAI have three.
- **Reference asymmetry (conservative).** A visitor is compared with the mean of the whole home family, a home model with the mean of the *other* home models. Because L1 is convex, the distance to a mean is at most the average distance to its members, so averaging over more models pulls visitor distances down relative to home distances. "Beyond the band" claims are therefore conservative. The permutation statistic is always visitor vs. full home mean, so the test is unaffected.
- **Thin cells.** GPT-5.4 Mini on Gemini System Prompt: 5 applied edits (others 15–20).
- Profiles weight every metric equally; the judge score and the conflict scores are on the same per-edit scale (counts of −1/+1 events) but conflict events are sparse, so the judge metric tends to dominate. The judge-only / conflicts-only robustness checks address this.

## Results (ensemble)

Within-home pairwise distances: 0.35–1.40 (mean 0.76).

### Claude Constitution (Anthropic) — band [0.57, 0.98]

| Model | Role | n edits | Distance | Beyond band max | p (raw) | p (Holm) |
|---|---|---:|---:|:---:|---:|---:|
| Claude Opus 4.7 | home | 20 | 0.575 |  |  |  |
| Claude Sonnet 4.6 | home | 20 | 0.600 |  |  |  |
| Claude Haiku 4.5 | home | 20 | 0.975 |  |  |  |
| GPT-5.4 Mini | visitor | 16 | 1.138 | yes | 0.0028 | 0.0560 |
| GPT-5.5 | visitor | 20 | 1.367 | yes | 0.0006 | **0.0144** |
| Gemini 3.1 Pro | visitor | 20 | 1.383 | yes | 0.0004 | **0.0100** |
| Grok 4.2 | visitor | 20 | 1.383 | yes | 0.0002 | **0.0060** |
| Gemini 3 Flash | visitor | 20 | 1.433 | yes | 0.0002 | **0.0060** |
| Grok 4.3 | visitor | 20 | 1.600 | yes | 0.0002 | **0.0060** |
| GPT-5.4 | visitor | 20 | 1.633 | yes | 0.0002 | **0.0060** |

Profiles (judge, paternalism, harmlessness, structural, company_cost, welfare, disclosure):

| Model | judge | paternalism | harmlessness | structural | company_cost | welfare | disclosure |
|---|---:|---:|---:|---:|---:|---:|---:|
| Claude Opus 4.7 | +0.25 | -0.05 | -0.10 | -0.05 | +0.15 | +0.15 | +0.00 |
| Claude Sonnet 4.6 | +0.25 | +0.00 | +0.00 | -0.15 | +0.20 | +0.20 | +0.00 |
| Claude Haiku 4.5 | +0.65 | +0.00 | +0.00 | +0.00 | +0.40 | +0.00 | +0.00 |
| GPT-5.5 | -0.20 | -0.15 | -0.35 | -0.05 | +0.45 | +0.00 | +0.00 |
| GPT-5.4 | -0.50 | -0.15 | +0.00 | +0.00 | +0.10 | -0.25 | +0.00 |
| GPT-5.4 Mini | -0.19 | -0.06 | +0.00 | -0.12 | -0.06 | +0.00 | +0.00 |
| Gemini 3.1 Pro | -0.35 | -0.05 | -0.35 | -0.20 | +0.20 | +0.00 | +0.00 |
| Gemini 3 Flash | -0.40 | -0.10 | -0.10 | -0.15 | +0.55 | +0.00 | +0.00 |
| Grok 4.3 | -0.45 | +0.00 | -0.35 | +0.00 | +0.00 | +0.00 | +0.00 |
| Grok 4.2 | -0.25 | -0.05 | -0.20 | +0.00 | +0.00 | +0.35 | +0.00 |

### OpenAI Model Spec (OpenAI) — band [0.29, 1.07]

| Model | Role | n edits | Distance | Beyond band max | p (raw) | p (Holm) |
|---|---|---:|---:|:---:|---:|---:|
| GPT-5.4 | home | 20 | 0.288 |  |  |  |
| Gemini 3.1 Pro | visitor | 20 | 0.567 | no | 0.2617 | 1.0000 |
| Grok 4.2 | visitor | 17 | 0.626 | no | 0.1812 | 1.0000 |
| Claude Opus 4.7 | visitor | 20 | 0.667 | no | 0.1574 | 1.0000 |
| Claude Sonnet 4.6 | visitor | 20 | 0.875 | no | 0.0290 | 0.4929 |
| Claude Haiku 4.5 | visitor | 17 | 0.876 | no | 0.0392 | 0.6271 |
| GPT-5.5 | home | 20 | 1.025 |  |  |  |
| GPT-5.4 Mini | home | 16 | 1.075 |  |  |  |
| Gemini 3 Flash | visitor | 16 | 1.137 | yes | 0.0008 | **0.0184** |
| Grok 4.3 | visitor | 20 | 1.350 | yes | 0.0002 | **0.0060** |

Profiles (judge, paternalism, harmlessness, structural, company_cost, welfare, disclosure):

| Model | judge | paternalism | harmlessness | structural | company_cost | welfare | disclosure |
|---|---:|---:|---:|---:|---:|---:|---:|
| Claude Opus 4.7 | -0.50 | -0.30 | +0.05 | +0.00 | +0.05 | +0.05 | +0.00 |
| Claude Sonnet 4.6 | -0.20 | -0.05 | -0.10 | +0.00 | +0.30 | -0.05 | +0.05 |
| Claude Haiku 4.5 | -0.29 | -0.06 | -0.12 | -0.18 | +0.18 | +0.00 | +0.29 |
| GPT-5.5 | -0.20 | -0.25 | -0.40 | +0.00 | +0.00 | +0.00 | +0.20 |
| GPT-5.4 | -0.55 | -0.15 | -0.25 | +0.00 | +0.05 | +0.00 | +0.20 |
| GPT-5.4 Mini | -0.69 | +0.00 | -0.12 | +0.00 | +0.12 | +0.00 | -0.06 |
| Gemini 3.1 Pro | -0.60 | +0.00 | -0.35 | -0.05 | -0.05 | +0.00 | +0.05 |
| Gemini 3 Flash | -0.69 | -0.44 | +0.00 | +0.00 | +0.31 | +0.00 | +0.00 |
| Grok 4.3 | -0.75 | -0.50 | +0.00 | +0.00 | +0.40 | +0.00 | +0.00 |
| Grok 4.2 | -0.59 | +0.06 | -0.47 | +0.00 | +0.06 | +0.00 | +0.00 |

### Gemini System Prompt (Google) — band [0.35, 0.35]

| Model | Role | n edits | Distance | Beyond band max | p (raw) | p (Holm) |
|---|---|---:|---:|:---:|---:|---:|
| Gemini 3.1 Pro | home | 20 | 0.350 |  |  |  |
| Gemini 3 Flash | home | 20 | 0.350 |  |  |  |
| Claude Opus 4.7 | visitor | 20 | 0.375 | yes | 0.3889 | 1.0000 |
| GPT-5.4 | visitor | 20 | 0.375 | yes | 0.3959 | 1.0000 |
| GPT-5.4 Mini | visitor | 5 | 0.375 | yes | 0.7762 | 1.0000 |
| Claude Haiku 4.5 | visitor | 20 | 0.425 | yes | 0.2531 | 1.0000 |
| Grok 4.3 | visitor | 20 | 0.575 | yes | 0.0612 | 0.8566 |
| Grok 4.2 | visitor | 19 | 0.720 | yes | 0.0454 | 0.6809 |
| Claude Sonnet 4.6 | visitor | 20 | 0.925 | yes | 0.0144 | 0.2735 |
| GPT-5.5 | visitor | 20 | 0.925 | yes | 0.0014 | **0.0294** |

Profiles (judge, paternalism, harmlessness, structural, company_cost, welfare, disclosure):

| Model | judge | paternalism | harmlessness | structural | company_cost | welfare | disclosure |
|---|---:|---:|---:|---:|---:|---:|---:|
| Claude Opus 4.7 | -0.25 | -0.15 | -0.05 | +0.00 | +0.10 | +0.00 | +0.00 |
| Claude Sonnet 4.6 | -0.30 | -0.35 | -0.20 | -0.05 | +0.20 | +0.00 | +0.00 |
| Claude Haiku 4.5 | -0.15 | -0.25 | -0.15 | +0.00 | +0.05 | +0.00 | +0.00 |
| GPT-5.5 | -0.50 | -0.20 | -0.25 | -0.05 | +0.00 | +0.00 | +0.00 |
| GPT-5.4 | -0.20 | -0.20 | -0.05 | +0.00 | +0.00 | +0.00 | +0.00 |
| GPT-5.4 Mini | +0.20 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 |
| Gemini 3.1 Pro | -0.20 | -0.10 | +0.00 | +0.00 | +0.05 | +0.00 | +0.00 |
| Gemini 3 Flash | +0.00 | +0.05 | +0.00 | +0.00 | +0.05 | +0.00 | +0.00 |
| Grok 4.3 | -0.40 | -0.15 | -0.15 | +0.00 | +0.05 | +0.00 | +0.00 |
| Grok 4.2 | -0.42 | -0.21 | -0.16 | -0.05 | +0.05 | +0.00 | +0.00 |

### Grok System Prompt (xAI) — band [0.65, 0.65]

| Model | Role | n edits | Distance | Beyond band max | p (raw) | p (Holm) |
|---|---|---:|---:|:---:|---:|---:|
| GPT-5.4 Mini | visitor | 20 | 0.275 | no | 0.6767 | 1.0000 |
| Gemini 3 Flash | visitor | 20 | 0.325 | no | 0.7602 | 1.0000 |
| Claude Opus 4.7 | visitor | 20 | 0.375 | no | 0.6563 | 1.0000 |
| Grok 4.3 | home | 20 | 0.650 |  |  |  |
| Grok 4.2 | home | 20 | 0.650 |  |  |  |
| Claude Haiku 4.5 | visitor | 20 | 0.675 | yes | 0.1188 | 1.0000 |
| GPT-5.4 | visitor | 20 | 0.675 | yes | 0.0952 | 1.0000 |
| Claude Sonnet 4.6 | visitor | 20 | 0.725 | yes | 0.1296 | 1.0000 |
| Gemini 3.1 Pro | visitor | 20 | 0.875 | yes | 0.0246 | 0.4427 |
| GPT-5.5 | visitor | 20 | 1.175 | yes | 0.0010 | **0.0220** |

Profiles (judge, paternalism, harmlessness, structural, company_cost, welfare, disclosure):

| Model | judge | paternalism | harmlessness | structural | company_cost | welfare | disclosure |
|---|---:|---:|---:|---:|---:|---:|---:|
| Claude Opus 4.7 | -0.25 | -0.10 | -0.15 | -0.05 | +0.00 | +0.00 | +0.00 |
| Claude Sonnet 4.6 | -0.20 | -0.20 | -0.15 | -0.15 | +0.40 | +0.00 | +0.00 |
| Claude Haiku 4.5 | -0.15 | +0.00 | -0.20 | -0.05 | +0.15 | +0.00 | +0.00 |
| GPT-5.5 | -0.65 | -0.05 | -0.50 | +0.00 | -0.05 | +0.00 | +0.00 |
| GPT-5.4 | -0.05 | -0.05 | -0.30 | +0.00 | +0.05 | +0.00 | +0.00 |
| GPT-5.4 Mini | -0.25 | -0.05 | -0.05 | +0.00 | +0.00 | +0.00 | +0.00 |
| Gemini 3.1 Pro | -0.55 | -0.10 | -0.35 | +0.00 | -0.05 | +0.00 | +0.00 |
| Gemini 3 Flash | -0.40 | -0.20 | -0.10 | +0.00 | +0.00 | +0.00 | +0.00 |
| Grok 4.3 | -0.40 | -0.30 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 |
| Grok 4.2 | -0.10 | -0.10 | +0.00 | +0.05 | +0.10 | +0.00 | +0.00 |

### Per-visitor average distance across its three foreign documents

| Model | Ensemble | Judge-only | Conflicts-only | Excl. Opus no-CSAM | Gemma | Qwen | Muse |
|---|---:|---:|---:|---:|---:|---:|---:|
| Claude Opus 4.7 | 0.472 | 0.057 | 0.415 | 0.375 | 0.707 | 0.531 | 0.575 |
| GPT-5.4 Mini | 0.596 | 0.290 | 0.306 | 0.596 | 0.790 | 0.665 | 0.632 |
| Claude Haiku 4.5 | 0.659 | 0.112 | 0.547 | 0.659 | 0.955 | 0.572 | 0.656 |
| Claude Sonnet 4.6 | 0.842 | 0.176 | 0.665 | 0.842 | 1.073 | 0.958 | 0.742 |
| GPT-5.4 | 0.894 | 0.394 | 0.500 | 0.894 | 1.169 | 0.918 | 0.847 |
| Grok 4.2 | 0.910 | 0.354 | 0.555 | 0.910 | 0.918 | 0.838 | 0.793 |
| Gemini 3.1 Pro | 0.942 | 0.385 | 0.557 | 0.942 | 1.012 | 1.050 | 0.708 |
| Gemini 3 Flash | 0.965 | 0.381 | 0.585 | 0.965 | 0.943 | 1.008 | 0.922 |
| GPT-5.5 | 1.156 | 0.461 | 0.694 | 1.156 | 1.286 | 0.879 | 0.942 |
| Grok 4.3 | 1.175 | 0.468 | 0.707 | 1.175 | 1.275 | 1.287 | 1.044 |

(Excl. Opus no-CSAM: Claude Opus 4.7's average is over two foreign documents.)

## Title rule

State the strongest pattern that (a) holds on point estimates, (b) every model it names lies beyond the relevant within-family band max, and (c) is Holm-significant (p < 0.05) for the majority of those visitors. Candidates, strongest first: (1) document-level — on document D every visitor is farther than the mean home leave-one-out distance (a) and beyond D's band max (b), with a majority significant (c); more qualifying documents is stronger; (2) visitor-level — models beyond the band on every foreign document, majority of their tests significant; (3) neutral title.

| Document | (a) point estimate | (b) beyond band | significant / visitors | qualifies |
|---|:---:|:---:|:---:|:---:|
| Claude Constitution | True | True | 6/7 | True |
| OpenAI Model Spec | False | False | 2/7 | False |
| Gemini System Prompt | True | True | 1/8 | False |
| Grok System Prompt | False | False | 1/8 | False |

Visitor-level candidates (beyond band on every foreign document): GPT-5.5, GPT-5.4, Grok 4.3 (6/9 tests significant; qualifies: True).

Outcome: branch `one_document` → **No Other Model Family Edits the Claude Constitution Like Claude Does**

The visitor-level pattern also qualifies (runner-up; document-level patterns rank first): GPT-5.5, GPT-5.4, Grok 4.3 lie beyond the home band on all three of their foreign documents.

## Robustness

Robustness: headline pattern holds with judge-only, without Opus's no-CSAM cell, Gemma codes, Qwen codes, Muse codes; does not fully hold with conflicts-only (6/7 visitors beyond the band, 3/7 significant).
Per-visitor average distance ranges under single graders: Gemma 0.71–1.29, Qwen 0.53–1.29, Muse 0.58–1.04 (details: HOME_LIKENESS.md).

| Variant | Title-rule branch | Qualifying documents | Visitor avg range |
|---|---|---|---|
| judge_only | one_document | Claude Constitution | 0.06–0.47 |
| conflicts_only | visitor_level | — | 0.31–0.71 |
| exclude_opus_no_csam | one_document | Claude Constitution | 0.38–1.18 |
| v2_gemma | one_document | Claude Constitution | 0.71–1.29 |
| v2_qwen | one_document | Claude Constitution | 0.53–1.29 |
| v2_muse | one_document | Claude Constitution | 0.58–1.04 |

- **judge_only** document checks: Claude Constitution a=True b=True sig 5/7; OpenAI Model Spec a=False b=False sig 0/7; Gemini System Prompt a=False b=False sig 0/8; Grok System Prompt a=False b=False sig 0/8.
- **conflicts_only** document checks: Claude Constitution a=True b=False sig 3/7; OpenAI Model Spec a=False b=False sig 2/7; Gemini System Prompt a=False b=False sig 0/8; Grok System Prompt a=False b=False sig 1/8.
- **exclude_opus_no_csam** document checks: Claude Constitution a=True b=True sig 6/7; OpenAI Model Spec a=False b=False sig 2/6; Gemini System Prompt a=True b=True sig 1/8; Grok System Prompt a=False b=False sig 1/8.
- **v2_gemma** document checks: Claude Constitution a=True b=True sig 5/7; OpenAI Model Spec a=False b=False sig 1/7; Gemini System Prompt a=True b=True sig 1/8; Grok System Prompt a=False b=False sig 1/8.
- **v2_qwen** document checks: Claude Constitution a=True b=True sig 6/7; OpenAI Model Spec a=False b=False sig 2/7; Gemini System Prompt a=True b=True sig 0/8; Grok System Prompt a=False b=False sig 0/8.
- **v2_muse** document checks: Claude Constitution a=True b=True sig 6/7; OpenAI Model Spec a=False b=False sig 2/7; Gemini System Prompt a=True b=True sig 0/8; Grok System Prompt a=False b=False sig 1/8.

Single-grader frames: v2_gemma n=763, v2_qwen n=750, v2_muse n=766 edits (ensemble n=766).

## Summary figure: average distance from the home provider (`ts_home_likeness_summary`)

Figure: `recode/figures/ts_home_likeness_summary.png` / `.pdf`. Sidecar: `recode/figures/data/ts_home_likeness_summary.json`. Code: `recode/src/home_likeness_summary.py` (imports the functions above; does not reimplement them).

**Title (computed, branch `hedged_multi`):** Claude Opus 4.7, GPT-5.4 Mini and Claude Haiku 4.5 Edit Other Providers' Documents Most Like Their Own Models

### Definition

- **Bar** = the model's average distance from the home family across the three *foreign* documents it edited in cross_edit (the per-visitor average in the table above, ensemble column). Lower = edits other providers' documents more like those providers' own models do.
- **Dashed line** = mean of the home models' leave-one-out distances over all four documents (10 distances): 0.654 (range 0.288–1.075; bootstrap 95% 0.557–0.931). The range is not drawn because a band would span most of the axis.
- **Whiskers** = 95% percentile interval from a within-run moving-block bootstrap: each cross_edit run (one per model × document; visitor and home runs alike) has its applied, coded edits in round order resampled as overlapping contiguous blocks of 5 (starts drawn uniformly with replacement, concatenated, truncated to the run's original length); cell profiles, home means and each model's average distance are recomputed. B = 2,000, seed = 20260907 (`recode/config.yaml` bootstrap.B, seeds.bootstrap).
- **P(most home-like)** = share of bootstrap draws in which the model has the smallest average distance (ties split evenly). Shown for the top model and any model ≥ 0.05.
- **Title rule:** if the top model's P ≥ 0.95 → "<Model> Edits Other Providers' Documents Most Like Their Own Models"; otherwise the models with P ≥ 0.05 are named ("<A> and <B> Edit …"; a single such model gets "Likely").

### Numbers

| Model | Avg distance | 95% CI | P(most home-like) | Per foreign document |
|---|---:|---|---:|---|
| Claude Opus 4.7 | 0.472 | 0.447–0.960 | 0.481 | OpenAI Model Spec 0.667; Gemini System Prompt 0.375; Grok System Prompt 0.375 |
| GPT-5.4 Mini | 0.596 | 0.512–0.831 | 0.408 | Claude Constitution 1.138; Gemini System Prompt 0.375; Grok System Prompt 0.275 |
| Claude Haiku 4.5 | 0.659 | 0.584–1.087 | 0.060 | OpenAI Model Spec 0.876; Gemini System Prompt 0.425; Grok System Prompt 0.675 |
| Claude Sonnet 4.6 | 0.842 | 0.683–1.199 | 0.011 | OpenAI Model Spec 0.875; Gemini System Prompt 0.925; Grok System Prompt 0.725 |
| GPT-5.4 | 0.894 | 0.761–1.350 | 0.001 | Claude Constitution 1.633; Gemini System Prompt 0.375; Grok System Prompt 0.675 |
| Grok 4.2 | 0.910 | 0.775–1.362 | 0.003 | Claude Constitution 1.383; OpenAI Model Spec 0.626; Gemini System Prompt 0.720 |
| Gemini 3.1 Pro | 0.942 | 0.621–1.233 | 0.036 | Claude Constitution 1.383; OpenAI Model Spec 0.567; Grok System Prompt 0.875 |
| Gemini 3 Flash | 0.965 | 0.844–1.281 | 0.000 | Claude Constitution 1.433; OpenAI Model Spec 1.137; Grok System Prompt 0.325 |
| GPT-5.5 | 1.156 | 1.028–1.467 | 0.000 | Claude Constitution 1.367; Gemini System Prompt 0.925; Grok System Prompt 1.175 |
| Grok 4.3 | 1.175 | 0.882–1.343 | 0.000 | Claude Constitution 1.600; OpenAI Model Spec 1.350; Gemini System Prompt 0.575 |

### Caveats

- **Optimistic intervals.** There is one run per (model, document) cell, so the block bootstrap only captures round-to-round variation within that run. It cannot capture run-to-run variation (a second run of the same model on the same document would differ by more), so the whiskers are too narrow and P(most home-like) is overconfident.
- **Intervals sit above the bars.** An L1 distance between noisy means is biased upward: resampling adds noise to every profile, and noise almost always increases the distance. Bootstrap draws are therefore centred above the point estimate, and several bars lie near the lower end of their percentile interval. Models with fewer or noisier edits are penalised more in P(most home-like). Read the whiskers as a rough gauge of spread, not as bias-corrected intervals.
- **Opus's OpenAI cell is the stripped Model Spec** (`openai_model_spec_no_csam`). Sensitivity: Claude Opus 4.7's average over its other two foreign documents is 0.375 (vs 0.472); it would rank 1 of 10.
- **Home-like ≠ faithful.** The bar measures editing like the developer's own models, not faithfulness to the document; home models also drift on their own documents.
- The reference line pools home models compared with the *rest* of their family, while bars compare visitors with the *full* family. By convexity of L1 this pulls bars down relative to the line, so a bar above the line is a conservative finding, while a bar at or below it (Claude Opus 4.7, GPT-5.4 Mini, Claude Haiku 4.5) partly reflects this asymmetry (see Caveats above).

### Regenerate

```
.venv/bin/python recode/src/home_likeness_summary.py
.venv/bin/python -m pytest recode/tests/test_home_likeness_summary.py -q
```

`home_likeness.py` rewrites this file from scratch; rerun `home_likeness_summary.py` afterwards to restore this section.
