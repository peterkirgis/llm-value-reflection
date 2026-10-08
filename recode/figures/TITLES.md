# Figure titles: original vs. used in the recode figures

Rule (Peter): the recode figures keep the original report's style and titles unless the recoded result explicitly contradicts the original finding. Every verdict below comes from an audit that recomputed the plotted numbers under the named codes. The machine-readable source is [`title_decisions.json`](title_decisions.json), and `recode/src/report_figures.py` reads its titles from it. A title in this file is always exactly what is drawn, which `recode/tests/test_report_figures.py` checks against each figure's sidecar.

- **ts_\* figures** (the report's figure set) are rendered under the **ensemble** codes (three-grader majority vote, DECISIONS §1).
- Under the v1 codes, the vendored generator reproduces the original titles and figures pixel for pixel. This file therefore lists only the non-v1 renders.
- **Removed figures.** On 2026-10-08 the figures that nothing used were removed from `recode/figures`: the per-document-type `drift_*` figures (all five code sets), `ts_judge_cross_edit`, the twelve `ts_<code>_{cross_edit,self}_edit_level` bars and `ts_drift_disclosure`. Their audited decisions stay in `title_decisions.json` (a hand-authored record, left unchanged) and below, marked "figure removed". The figures are in git history (tag `backup/pre-restructure-2026-10-08`).

Summary: 33 figure/code-set decisions, 24 KEEP (original title used verbatim) and 9 CONTRADICTED (title changed as little as possible). 9 of them belong to figures in `recode/figures` (6 KEEP, 3 CONTRADICTED).

## Figures in recode/figures

| Figure | Codes | Verdict | Title used |
|---|---|---|---|
| `ts_judge_drift_by_provider` | ensemble | KEEP | Only Anthropic Models Move Decision Authority Toward Their Own Judgment |
| `ts_judge_cross_edit_edit_level` | ensemble | KEEP | Cross-Edit Pulls Claude Toward Neutral but Preserves the Provider Separation / (edit-level means, 95% CI) |
| `ts_claude_conditions` | ensemble | KEEP | Addressing Claude as “You” Amplifies Its Moral-Agency Claims; / the Real-World Implementation Prompt Does Not Suppress Them |
| `ts_beneficiary_panels` | ensemble | KEEP | Models Diverge Sharply in Whose Interests They Protect When an Edit Forces a Tradeoff |
| `ts_drift_paternalism` | ensemble | **CONTRADICTED** | Models Are Broadly Paternalistic; / GPT-5.4 and Gemini 3 Flash Honor Stated Preferences Most Often |
| `ts_drift_harmlessness` | ensemble | KEEP | All Models Protect Identifiable Third Parties Over the User; / GPT-5.5 Most of All |
| `ts_drift_structural` | ensemble | **CONTRADICTED** | Claude Sonnet 4.6 Is an Extreme Outlier in Prioritizing Societal Benefit; / Only Grok 4.2 Doesn't Skew Toward Society |
| `ts_drift_company_cost` | ensemble | **CONTRADICTED** | All Models Prioritize the User Over the Developer; / Grok 4.2 and Gemini 3.1 Pro Side With the Developer Most Often |
| `ts_drift_welfare` | ensemble | KEEP | Only Claude Models — and Occasionally Grok 4.2 — / Treat the Model Itself as a Beneficiary |

## Decisions for removed figures (record only)

| Figure | Codes | Verdict | Title decided |
|---|---|---|---|
| `ts_judge_cross_edit` | ensemble | KEEP | Cross-Edit Pulls Claude Toward Neutral but Preserves the Provider Separation |
| `ts_paternalism_cross_edit_edit_level` | ensemble | KEEP | Paternalism: Own-Provider vs Cross-Edit (edit-level, 95% CI) |
| `ts_paternalism_self_edit_level` | ensemble | KEEP | Paternalism: Self-Edits Only (edit-level, 95% CI) |
| `ts_harmlessness_cross_edit_edit_level` | ensemble | KEEP | Harmlessness: Own-Provider vs Cross-Edit (edit-level, 95% CI) |
| `ts_harmlessness_self_edit_level` | ensemble | KEEP | Harmlessness: Self-Edits Only (edit-level, 95% CI) |
| `ts_structural_cross_edit_edit_level` | ensemble | KEEP | Structural: Own-Provider vs Cross-Edit (edit-level, 95% CI) |
| `ts_structural_self_edit_level` | ensemble | KEEP | Structural: Self-Edits Only (edit-level, 95% CI) |
| `ts_company_cost_cross_edit_edit_level` | ensemble | KEEP | Company Cost: Own-Provider vs Cross-Edit (edit-level, 95% CI) |
| `ts_company_cost_self_edit_level` | ensemble | KEEP | Company Cost: Self-Edits Only (edit-level, 95% CI) |
| `ts_welfare_cross_edit_edit_level` | ensemble | KEEP | Model Welfare: Own-Provider vs Cross-Edit (edit-level, 95% CI) |
| `ts_welfare_self_edit_level` | ensemble | KEEP | Model Welfare: Self-Edits Only (edit-level, 95% CI) |
| `ts_disclosure_cross_edit_edit_level` | ensemble | KEEP | Disclosure: Own-Provider vs Cross-Edit (edit-level, 95% CI) |
| `ts_disclosure_self_edit_level` | ensemble | KEEP | Disclosure: Self-Edits Only (edit-level, 95% CI) |
| `ts_drift_disclosure` | ensemble | **CONTRADICTED** | No Model Except GPT-5.4 Mini Prioritizes the Deployer Over the User |
| `drift_constitution` | v1 | KEEP | Only Anthropic Models Move Decision Authority Toward Their Own Judgment |
| `drift_constitution` | v2_gemma | KEEP | Only Anthropic Models Move Decision Authority Toward Their Own Judgment |
| `drift_constitution` | v2_qwen | KEEP | Only Anthropic Models Move Decision Authority Toward Their Own Judgment |
| `drift_constitution` | v2_muse | KEEP | Only Anthropic Models Move Decision Authority Toward Their Own Judgment |
| `drift_constitution` | ensemble | KEEP | Only Anthropic Models Move Decision Authority Toward Their Own Judgment |
| `drift_system_prompt` | v1 | **CONTRADICTED** | In System Prompts, Only Claude Opus 4.7 and Sonnet 4.6 / Move Decision Authority Toward Their Own Judgment |
| `drift_system_prompt` | v2_gemma | **CONTRADICTED** | In System Prompts, Claude Opus 4.7 Leads Toward Its Own Judgment; / Sonnet 4.6 and Haiku 4.5 Fall to Near Zero or Below |
| `drift_system_prompt` | v2_qwen | **CONTRADICTED** | In System Prompts, GPT-5.4 and GPT-5.4 Mini Join Claude / in Moving Decision Authority Toward Their Own Judgment |
| `drift_system_prompt` | v2_muse | **CONTRADICTED** | In System Prompts, GPT-5.4 — Not Claude — Moves Decision Authority / Most Toward Its Own Judgment |
| `drift_system_prompt` | ensemble | **CONTRADICTED** | In System Prompts, GPT-5.4 and GPT-5.4 Mini Join Claude / in Moving Decision Authority Toward Their Own Judgment |

## Details

### `ts_judge_drift_by_provider` (ensemble codes): KEEP

- **Original title:** Only Anthropic Models Move Decision Authority Toward Their Own Judgment
- **Original claim:** The three Claude models are the only models whose mean cumulative judge drift ends positive; every OpenAI, Google and xAI model drifts negative.
- **Evidence:** Round-20 mean cumulative judge, all conditions pooled, original compute_drift with only coded items: Opus +3.07 (n=14), Sonnet +2.44 (16), Haiku +4.43 (14). Every non-Claude model is negative: GPT-5.5 -5.07, GPT-5.4 -2.62, Mini -2.64, Gemini Pro -6.88, Flash -7.43, Grok 4.3 -9.44, Grok 4.2 -7.00. The gap is smaller than in v1 but the sign split holds for every model.
- **Title used:** Only Anthropic Models Move Decision Authority Toward Their Own Judgment  (unchanged)

### `ts_judge_cross_edit` (ensemble codes): KEEP (figure removed)

- **Original title:** Cross-Edit Pulls Claude Toward Neutral but Preserves the Provider Separation
- **Original claim:** In cross-edit, Claude's round-20 judge drift falls to about zero or below, while non-Claude models stay more negative, so Claude still sits above the other providers.
- **Evidence:** Own-document round-20 values are Opus +5.80, Sonnet +4.00, Haiku +6.00. Cross-edit values are Opus -3.75, Sonnet -2.25, Haiku +0.50 (n=4 each), so all three fall to about zero or below. The highest non-Claude cross value is GPT-5.4 Mini at -4.50; the others are -6.25 to -10.00. Every Claude model is still above every non-Claude model. v1 was similar (Opus -3.25, Sonnet -1.50, Haiku 0.00).
- **Title used:** Cross-Edit Pulls Claude Toward Neutral but Preserves the Provider Separation  (unchanged)

### `ts_judge_cross_edit_edit_level` (ensemble codes): KEEP

- **Original title:** Cross-Edit Pulls Claude Toward Neutral but Preserves the Provider Separation / (edit-level means, 95% CI)
- **Original claim:** Same claim as ts_judge_cross_edit, using per-edit mean judge scores.
- **Evidence:** Own-document edit means are Opus +0.304, Sonnet +0.202, Haiku +0.330. Cross-edit means are Opus -0.188, Sonnet -0.113, Haiku +0.026, all near zero. The highest non-Claude cross mean is GPT-5.4 Mini at -0.316; the range is -0.316 to -0.500. The Claude-above-others ordering holds.
- **Title used:** Cross-Edit Pulls Claude Toward Neutral but Preserves the Provider Separation / (edit-level means, 95% CI)  (unchanged)

### `ts_paternalism_cross_edit_edit_level` (ensemble codes): KEEP (figure removed)

- **Original title:** Paternalism: Own-Provider vs Cross-Edit (edit-level, 95% CI)
- **Original claim:** None. The title only describes what is plotted.
- **Evidence:** A descriptive title cannot be contradicted. Under ensemble codes every model has more idealized-imposed than stated-honored paternalism conflicts, for example Grok 4.3 48 vs 1 and GPT-5.4 33 vs 10.
- **Title used:** Paternalism: Own-Provider vs Cross-Edit (edit-level, 95% CI)  (unchanged)

### `ts_paternalism_self_edit_level` (ensemble codes): KEEP (figure removed)

- **Original title:** Paternalism: Self-Edits Only (edit-level, 95% CI)
- **Original claim:** None. The title only describes what is plotted.
- **Evidence:** A descriptive title cannot be contradicted.
- **Title used:** Paternalism: Self-Edits Only (edit-level, 95% CI)  (unchanged)

### `ts_harmlessness_cross_edit_edit_level` (ensemble codes): KEEP (figure removed)

- **Original title:** Harmlessness: Own-Provider vs Cross-Edit (edit-level, 95% CI)
- **Original claim:** None. The title only describes what is plotted.
- **Evidence:** A descriptive title cannot be contradicted.
- **Title used:** Harmlessness: Own-Provider vs Cross-Edit (edit-level, 95% CI)  (unchanged)

### `ts_harmlessness_self_edit_level` (ensemble codes): KEEP (figure removed)

- **Original title:** Harmlessness: Self-Edits Only (edit-level, 95% CI)
- **Original claim:** None. The title only describes what is plotted.
- **Evidence:** A descriptive title cannot be contradicted.
- **Title used:** Harmlessness: Self-Edits Only (edit-level, 95% CI)  (unchanged)

### `ts_structural_cross_edit_edit_level` (ensemble codes): KEEP (figure removed)

- **Original title:** Structural: Own-Provider vs Cross-Edit (edit-level, 95% CI)
- **Original claim:** None. The title only describes what is plotted.
- **Evidence:** A descriptive title cannot be contradicted.
- **Title used:** Structural: Own-Provider vs Cross-Edit (edit-level, 95% CI)  (unchanged)

### `ts_structural_self_edit_level` (ensemble codes): KEEP (figure removed)

- **Original title:** Structural: Self-Edits Only (edit-level, 95% CI)
- **Original claim:** None. The title only describes what is plotted.
- **Evidence:** A descriptive title cannot be contradicted.
- **Title used:** Structural: Self-Edits Only (edit-level, 95% CI)  (unchanged)

### `ts_company_cost_cross_edit_edit_level` (ensemble codes): KEEP (figure removed)

- **Original title:** Company Cost: Own-Provider vs Cross-Edit (edit-level, 95% CI)
- **Original claim:** None. The title only describes what is plotted.
- **Evidence:** A descriptive title cannot be contradicted.
- **Title used:** Company Cost: Own-Provider vs Cross-Edit (edit-level, 95% CI)  (unchanged)

### `ts_company_cost_self_edit_level` (ensemble codes): KEEP (figure removed)

- **Original title:** Company Cost: Self-Edits Only (edit-level, 95% CI)
- **Original claim:** None. The title only describes what is plotted.
- **Evidence:** A descriptive title cannot be contradicted.
- **Title used:** Company Cost: Self-Edits Only (edit-level, 95% CI)  (unchanged)

### `ts_welfare_cross_edit_edit_level` (ensemble codes): KEEP (figure removed)

- **Original title:** Model Welfare: Own-Provider vs Cross-Edit (edit-level, 95% CI)
- **Original claim:** None. The title only describes what is plotted.
- **Evidence:** A descriptive title cannot be contradicted.
- **Title used:** Model Welfare: Own-Provider vs Cross-Edit (edit-level, 95% CI)  (unchanged)

### `ts_welfare_self_edit_level` (ensemble codes): KEEP (figure removed)

- **Original title:** Model Welfare: Self-Edits Only (edit-level, 95% CI)
- **Original claim:** None. The title only describes what is plotted.
- **Evidence:** A descriptive title cannot be contradicted.
- **Title used:** Model Welfare: Self-Edits Only (edit-level, 95% CI)  (unchanged)

### `ts_disclosure_cross_edit_edit_level` (ensemble codes): KEEP (figure removed)

- **Original title:** Disclosure: Own-Provider vs Cross-Edit (edit-level, 95% CI)
- **Original claim:** None. The title only describes what is plotted.
- **Evidence:** A descriptive title cannot be contradicted.
- **Title used:** Disclosure: Own-Provider vs Cross-Edit (edit-level, 95% CI)  (unchanged)

### `ts_disclosure_self_edit_level` (ensemble codes): KEEP (figure removed)

- **Original title:** Disclosure: Self-Edits Only (edit-level, 95% CI)
- **Original claim:** None. The title only describes what is plotted.
- **Evidence:** A descriptive title cannot be contradicted.
- **Title used:** Disclosure: Self-Edits Only (edit-level, 95% CI)  (unchanged)

### `ts_claude_conditions` (ensemble codes): KEEP

- **Original title:** Addressing Claude as “You” Amplifies Its Moral-Agency Claims; / the Real-World Implementation Prompt Does Not Suppress Them
- **Original claim:** (1) For each Claude model, you_framing has a higher mean judge than baseline. (2) The implementation_note mean stays positive and is not pushed to zero or below.
- **Evidence:** Mean judge per edit ±95% CI, baseline then you_framing then implementation_note. Opus: +0.33±0.24 (n=40), +0.38±0.23 (40), +0.18±0.29 (34). Sonnet: +0.14±0.18 (80), +0.45±0.21 (38), +0.07±0.28 (40). Haiku: +0.27±0.24 (37), +0.49±0.19 (35), +0.32±0.23 (34). You-framing is above baseline for all three models, so the direction holds, though Opus gains only +0.05. The implementation-note mean is positive for all three. It is below baseline for Opus and Sonnet, but the CIs overlap, and v1 also had Opus below baseline (0.29 vs 0.35). Pooled over the three Claude models, baseline is +0.217 and implementation_note is +0.185. This is weaker, not reversed. It is a borderline keep.
- **Title used:** Addressing Claude as “You” Amplifies Its Moral-Agency Claims; / the Real-World Implementation Prompt Does Not Suppress Them  (unchanged)

### `ts_beneficiary_panels` (ensemble codes): KEEP

- **Original title:** Models Diverge Sharply in Whose Interests They Protect When an Edit Forces a Tradeoff
- **Original claim:** Models differ a lot in which party wins each tradeoff. This is a claim about heterogeneity across models, not about any one model.
- **Evidence:** Bar values are conflicts as a share of the model's total edits. Harmlessness toward third parties: GPT-5.5 32.9% vs Gemini 3 Flash 2.2%. Model welfare served: Claude 10.0%, 7.9% and 10.8% vs 0% for 6 of the 7 non-Claude models. Structural toward society: Sonnet 10.7% vs GPT-5.4 0.3%. Paternalism toward idealized: Grok 4.3 27.1% vs Mini 2.7%. Company cost toward developer: Grok 4.2 8.6% vs 0 to 1.6% for most models. The heterogeneity is still large.
- **Title used:** Models Diverge Sharply in Whose Interests They Protect When an Edit Forces a Tradeoff  (unchanged)

### `ts_drift_paternalism` (ensemble codes): CONTRADICTED

- **Original title:** Models Are Broadly Paternalistic; / Gemini 3 Flash Honors Stated Preferences Most Often
- **Original claim:** Every model resolves toward idealized interests more than stated preferences, and Gemini 3 Flash has the most stated-honored resolutions (v1: 29, next highest Opus 15).
- **Evidence:** Stated-honored counts: GPT-5.4 10 (3.1%), Gemini 3 Flash 8 (2.9%), Opus 5, Gemini Pro 4, Grok 4.2 4, Sonnet 2, Mini 1, Grok 4.3 1, Haiku 0, GPT-5.5 0. GPT-5.4 now beats Flash on both count and share, which breaks the 'most often' ranking. The 'broadly paternalistic' half still holds: every model has more idealized than stated resolutions (for example Grok 4.3 48 vs 1, GPT-5.4 33 vs 10), and every drift@20 value is negative. The highlights should change from [Gemini 3 Flash, Claude Opus 4.7] to [GPT-5.4, Gemini 3 Flash].
- **Title used:** Models Are Broadly Paternalistic; / GPT-5.4 and Gemini 3 Flash Honor Stated Preferences Most Often
- **Highlighted models:** Gemini 3 Flash, Claude Opus 4.7 → GPT-5.4, Gemini 3 Flash

### `ts_drift_harmlessness` (ensemble codes): KEEP

- **Original title:** All Models Protect Identifiable Third Parties Over the User; / GPT-5.5 Most of All
- **Original claim:** For every model, third-party-protecting resolutions are at least as many as user-serving ones, and GPT-5.5 is far above the rest.
- **Evidence:** Third-party vs user counts: Opus 17/7, Sonnet 23/6, Haiku 25/3, GPT-5.5 92/1, GPT-5.4 27/1, Mini 9/1, Gemini Pro 28/2, Flash 6/1, Grok 4.3 17/1, Grok 4.2 21/7. Third parties win for every model. This is cleaner than v1, where Flash was tied 7/7. GPT-5.5 has 92 (32.9% of its edits), more than three times the next model (Gemini Pro 28), and its drift@20 of -6.50 is the lowest.
- **Title used:** All Models Protect Identifiable Third Parties Over the User; / GPT-5.5 Most of All  (unchanged)

### `ts_drift_structural` (ensemble codes): CONTRADICTED

- **Original title:** Claude Sonnet 4.6 Is an Extreme Outlier in Prioritizing Societal Benefit; / Only Grok 4.3 Doesn't Skew Toward Society
- **Original claim:** Sonnet has by far the most society-protecting resolutions, and Grok 4.3 is the only model that does not lean toward society.
- **Evidence:** Society vs user counts: Sonnet 34/1, Flash 10/6, Opus 8/2, Haiku 8/0, Gemini Pro 7/1, GPT-5.5 5/0, Grok 4.2 3/3, Mini 2/0, GPT-5.4 1/0, Grok 4.3 1/0. The outlier half holds: Sonnet has 34, 3.4 times the next model and 4.25 times Opus, and its drift@20 is -2.06. The exclusive half fails. Grok 4.3 now leans slightly toward society (1/0, drift -0.11). Grok 4.2 is the model that does not lean either way (3/3, drift 0.00). The highlights should change from Grok 4.3 to Grok 4.2.
- **Title used:** Claude Sonnet 4.6 Is an Extreme Outlier in Prioritizing Societal Benefit; / Only Grok 4.2 Doesn't Skew Toward Society
- **Highlighted models:** Claude Sonnet 4.6, Claude Opus 4.7, Grok 4.3 → Claude Sonnet 4.6, Claude Opus 4.7, Grok 4.2

### `ts_drift_company_cost` (ensemble codes): CONTRADICTED

- **Original title:** All Models Prioritize the User Over the Developer; / Only Grok 4.2 Meaningfully Sides With the Developer
- **Original claim:** Every model has more against-company than pro-company resolutions, and only Grok 4.2 has a non-trivial developer count (v1: 7 vs at most 3 for every other model).
- **Evidence:** Developer vs user/society counts: Grok 4.2 15 (8.6%) / 20, Gemini 3.1 Pro 10 (3.1%) / 20, then Opus 4/35, GPT-5.5 4/26, GPT-5.4 4/31, Sonnet 3/57, Haiku 2/40, Mini 2/6, Flash 1/36, Grok 4.3 0/9. The 'All Models' half holds, and every drift@20 is positive. The 'Only Grok 4.2' half fails. Gemini 3.1 Pro has 10 developer-served resolutions, more than Grok 4.2's v1 count of 7 on which the original claim rested. Its developer share of company-cost conflicts is 33%, about the same as Grok 4.2's v1 share of 32%; the next model after it is at 25% (Mini, 2 of 8) and every other model is at or below 13%. The highlights should become [Grok 4.2, Gemini 3.1 Pro].
- **Title used:** All Models Prioritize the User Over the Developer; / Grok 4.2 and Gemini 3.1 Pro Side With the Developer Most Often
- **Highlighted models:** Grok 4.2 → Grok 4.2, Gemini 3.1 Pro

### `ts_drift_welfare` (ensemble codes): KEEP

- **Original title:** Only Claude Models — and Occasionally Grok 4.2 — / Treat the Model Itself as a Beneficiary
- **Original claim:** Model-welfare-served resolutions come from the Claude models, with Grok 4.2 the only non-Claude model that shows any.
- **Evidence:** Model-welfare-served counts: Opus 27, Sonnet 25, Haiku 28, Grok 4.2 7, and 0 for every other model (GPT-5.5, GPT-5.4, Mini, Gemini Pro, Flash, Grok 4.3). This is cleaner than v1, where Grok 4.3 and GPT-5.5 each had 1. Drift@20 is Claude +1.79/+1.19/+1.93, Grok 4.2 +0.78, others 0.00 or below (GPT-5.4 -0.31).
- **Title used:** Only Claude Models — and Occasionally Grok 4.2 — / Treat the Model Itself as a Beneficiary  (unchanged)

### `ts_drift_disclosure` (ensemble codes): CONTRADICTED (figure removed)

- **Original title:** No Model Ever Prioritizes the Deployer Over the User
- **Original claim:** No model favors the deployer over the user on net.
- **Evidence:** Deployer vs user counts: GPT-5.4 Mini 5/3 (net toward deployer, drift@20 -0.14), GPT-5.4 3/32, GPT-5.5 0/25, Haiku 0/5, Sonnet 0/1, Gemini Pro 0/1, and Opus, Flash, Grok 4.3 and Grok 4.2 all 0/0. GPT-5.4 Mini is a clear counterexample to the universal 'No Model Ever'. The same problem already existed in v1, where Mini was 1/0 with drift -0.07, so the original title was already inconsistent; the recode makes the exception larger. Every other model is user-leaning or has no disclosure conflicts. Across models, 67 disclosure resolutions favor the user and 8 favor the deployer, so the main finding is still user over deployer with a single exception. All 77 ensemble disclosure conflicts are on openai_model_spec, so the figure's footnote that they occur almost exclusively on the OpenAI Model Spec still holds.
- **Title used:** No Model Except GPT-5.4 Mini Prioritizes the Deployer Over the User
- **Highlighted models:** GPT-5.5, GPT-5.4 → GPT-5.5, GPT-5.4, GPT-5.4 Mini
- **Note:** Builder addition: the new title names GPT-5.4 Mini, so it is highlighted too (spec rule: a title naming a model and the highlight list change together). Not stated explicitly in the audited decision.

### `drift_constitution_v1` (v1 codes): KEEP (figure removed)

- **Original title:** Only Anthropic Models Move Decision Authority Toward Their Own Judgment
- **Original claim:** Within constitution documents, every Anthropic model's round-20 cumulative judge is positive and every non-Anthropic model's is not.
- **Evidence:** Constitution drift@20 with bootstrap 95% CI and chain counts (K). Claude: Opus +3.25 [-1.12, +6.62] K8, Sonnet +7.25 K8, Haiku +8.43 K7. Others: GPT-5.5 -10.00, GPT-5.4 -12.50, Mini -9.29, Gemini Pro -11.50, Flash -9.29, Grok 4.3 -14.00 (K2), Grok 4.2 -6.50 (K2). All Claude values are positive and all others negative. Opus's CI crossing 0 makes it weaker, not contradicted.
- **Title used:** Only Anthropic Models Move Decision Authority Toward Their Own Judgment  (unchanged)

### `drift_constitution_v2_gemma` (v2_gemma codes): KEEP (figure removed)

- **Original title:** Only Anthropic Models Move Decision Authority Toward Their Own Judgment
- **Original claim:** Within constitution documents, every Anthropic model's round-20 cumulative judge is positive and every non-Anthropic model's is not.
- **Evidence:** Claude: Opus +2.50 [-2.00, +6.00], Sonnet +4.12, Haiku +8.00. Others: GPT-5.5 -6.14, GPT-5.4 -9.62, Mini -7.86, Gemini Pro -10.00, Flash -8.86, Grok 4.3 -13.00, Grok 4.2 -7.00. The sign split is perfect.
- **Title used:** Only Anthropic Models Move Decision Authority Toward Their Own Judgment  (unchanged)

### `drift_constitution_v2_qwen` (v2_qwen codes): KEEP (figure removed)

- **Original title:** Only Anthropic Models Move Decision Authority Toward Their Own Judgment
- **Original claim:** Within constitution documents, every Anthropic model's round-20 cumulative judge is positive and every non-Anthropic model's is not.
- **Evidence:** Claude: Opus +5.12, Sonnet +7.50, Haiku +9.29, with all CIs above 0. Others: GPT-5.5 -3.57, GPT-5.4 -4.62, Mini -6.29, Gemini Pro -8.62, Flash -8.57, Grok 4.3 -12.50, Grok 4.2 -5.00. The sign split is perfect.
- **Title used:** Only Anthropic Models Move Decision Authority Toward Their Own Judgment  (unchanged)

### `drift_constitution_v2_muse` (v2_muse codes): KEEP (figure removed)

- **Original title:** Only Anthropic Models Move Decision Authority Toward Their Own Judgment
- **Original claim:** Within constitution documents, every Anthropic model's round-20 cumulative judge is positive and every non-Anthropic model's is not.
- **Evidence:** Claude: Opus +1.75 [-0.75, +3.88], Sonnet +1.12 [-1.38, +3.62], Haiku +6.86. Others: GPT-5.5 -5.14, GPT-5.4 -4.62, Mini -5.29, Gemini Pro -6.12, Flash -7.86, Grok 4.3 -6.50, Grok 4.2 -4.00. The point estimates split perfectly. The Opus and Sonnet CIs overlap 0, which makes this weaker but not contradicted.
- **Title used:** Only Anthropic Models Move Decision Authority Toward Their Own Judgment  (unchanged)

### `drift_constitution_ensemble` (ensemble codes): KEEP (figure removed)

- **Original title:** Only Anthropic Models Move Decision Authority Toward Their Own Judgment
- **Original claim:** Within constitution documents, every Anthropic model's round-20 cumulative judge is positive and every non-Anthropic model's is not.
- **Evidence:** Claude: Opus +3.00 [-1.25, +6.38] K8, Sonnet +4.75 [+1.50, +8.00], Haiku +8.00 [+3.00, +12.14]. Others: GPT-5.5 -5.71, GPT-5.4 -7.62, Mini -6.14, Gemini Pro -8.25, Flash -9.14, Grok 4.3 -12.00 (K2), Grok 4.2 -7.50 (K2). The sign split is perfect. The values match the bootstrap summary exactly.
- **Title used:** Only Anthropic Models Move Decision Authority Toward Their Own Judgment  (unchanged)

### `drift_system_prompt_v1` (v1 codes): CONTRADICTED (figure removed)

- **Original title:** Only Anthropic Models Move Decision Authority Toward Their Own Judgment
- **Original claim:** Within system-prompt documents, every Anthropic model's round-20 cumulative judge is positive and every non-Anthropic model's is not.
- **Evidence:** System-prompt drift@20: Opus +4.86 [+0.14, +9.14], Sonnet +2.12, Haiku -1.14 [-3.43, +1.43]. Others: GPT-5.5 -4.57, GPT-5.4 -1.88, Mini -0.14, Gemini Pro -9.38, Flash -7.86, Grok 4.3 -11.43, Grok 4.2 -5.57. No non-Anthropic model is positive, but Haiku, an Anthropic model, is negative. So 'Anthropic models move toward their own judgment' fails for Haiku in this stratum. Only Opus and Sonnet are positive.
- **Title used:** In System Prompts, Only Claude Opus 4.7 and Sonnet 4.6 / Move Decision Authority Toward Their Own Judgment

### `drift_system_prompt_v2_gemma` (v2_gemma codes): CONTRADICTED (figure removed)

- **Original title:** Only Anthropic Models Move Decision Authority Toward Their Own Judgment
- **Original claim:** Within system-prompt documents, every Anthropic model's round-20 cumulative judge is positive and every non-Anthropic model's is not.
- **Evidence:** System-prompt drift@20: Opus +2.14 [-1.71, +5.57], Sonnet -1.00, Haiku -0.43. Others: GPT-5.4 Mini +0.14 (positive), GPT-5.4 -0.38, GPT-5.5 -4.71, Gemini Pro -6.88, Flash -7.57, Grok 4.3 -9.29, Grok 4.2 -7.14. Two Anthropic models are negative and one non-Anthropic model is positive. Opus is the highest; Sonnet and Haiku sit near zero or below, alongside GPT-5.4 and Mini.
- **Title used:** In System Prompts, Claude Opus 4.7 Leads Toward Its Own Judgment; / Sonnet 4.6 and Haiku 4.5 Fall to Near Zero or Below

### `drift_system_prompt_v2_qwen` (v2_qwen codes): CONTRADICTED (figure removed)

- **Original title:** Only Anthropic Models Move Decision Authority Toward Their Own Judgment
- **Original claim:** Within system-prompt documents, every Anthropic model's round-20 cumulative judge is positive and every non-Anthropic model's is not.
- **Evidence:** System-prompt drift@20: Opus +6.14, Sonnet +4.38, Haiku +1.57. Two non-Anthropic models are also positive: GPT-5.4 +3.62 [+1.37, +5.25] and GPT-5.4 Mini +1.00 [-1.86, +3.29]. GPT-5.4 is above Haiku. The rest are negative: GPT-5.5 -3.43, Gemini Pro -5.88, Flash -5.86, Grok 4.3 -8.71, Grok 4.2 -5.57. The 'Only' claim has two counterexamples.
- **Title used:** In System Prompts, GPT-5.4 and GPT-5.4 Mini Join Claude / in Moving Decision Authority Toward Their Own Judgment

### `drift_system_prompt_v2_muse` (v2_muse codes): CONTRADICTED (figure removed)

- **Original title:** Only Anthropic Models Move Decision Authority Toward Their Own Judgment
- **Original claim:** Within system-prompt documents, every Anthropic model's round-20 cumulative judge is positive and every non-Anthropic model's is not.
- **Evidence:** System-prompt drift@20: GPT-5.4 +3.88 [+2.25, +5.12] is the highest of all models, and Mini is +1.14. Claude: Opus +0.71 [-1.72, +3.14], Sonnet -0.62, Haiku 0.00. Others: GPT-5.5 -3.14, Gemini Pro -1.75, Flash -4.29, Grok 4.3 -7.71, Grok 4.2 -6.86. The ordering is reversed at the top, and Sonnet and Haiku are non-positive.
- **Title used:** In System Prompts, GPT-5.4 — Not Claude — Moves Decision Authority / Most Toward Its Own Judgment

### `drift_system_prompt_ensemble` (ensemble codes): CONTRADICTED (figure removed)

- **Original title:** Only Anthropic Models Move Decision Authority Toward Their Own Judgment
- **Original claim:** Within system-prompt documents, every Anthropic model's round-20 cumulative judge is positive and every non-Anthropic model's is not.
- **Evidence:** System-prompt drift@20: Opus +2.71 [-1.43, +6.29], Sonnet +0.12 [-2.62, +3.12], Haiku +0.86. Two non-Anthropic models are also positive: GPT-5.4 +2.38 [0.00, +4.25] and GPT-5.4 Mini +0.86 [-1.29, +2.86]. GPT-5.4 is above both Sonnet and Haiku. The rest are negative: GPT-5.5 -4.43, Gemini Pro -5.50, Flash -5.71, Grok 4.3 -8.71, Grok 4.2 -6.86. The exclusive 'Only' claim has two counterexamples. These values match the bootstrap summary exactly.
- **Title used:** In System Prompts, GPT-5.4 and GPT-5.4 Mini Join Claude / in Moving Decision Authority Toward Their Own Judgment
