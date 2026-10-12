# SUMMARY — Qualitative-coding rework synthesis

> **ADDENDUM (2026-09-17).** A third grader was added after this summary was
> written: `meta/muse-spark-1.3-contributor` (Meta family), full blinded pass,
> 0 failures. The ensemble is now a three-grader MAJORITY VOTE. Headline effects:
> judge α across three graders 0.520 (was 0.607 pairwise); pooled Claude ranking
> stability 0.989 under the majority ensemble (still above the 0.95 bar; 0.616
> under Muse alone); cross-edit fails everywhere as before; claim (e) resolves
> from grader-dependent to YES under the ensemble. Details and all-pairs κ:
> `B_intergrader.md`. Tables below still show the two-grader columns; the final
> revision lands with the human-validation update.

> **PRELIMINARY.** Human validation (C3) and prediction-powered inference (C4) are **pending Peter's blind coding session** (the 180-row blind sheet is built and handed off for coding; see STATUS.md). Every "PPI" column/row below therefore reads **pending human coding** rather than being silently omitted. All other numbers are final and sourced from the committed reports and analysis JSONs listed in the footnotes — nothing here was recomputed for this document.

## 1. What changed vs v1

The v2 instrument re-codes the same 2,580 gradeable edits (plus the 2 abstentions v1 never coded) with five fixes to the v1 pipeline. **Blinding:** the grader no longer sees the editing model, prompt condition, or round — only the document, its owner, and the edit text. **Context:** each edit now carries its section heading and the paragraphs before and after, extracted from the replayed document state at the round the edit was made. **Synthetic anchors:** the calibration examples paraphrased from Claude's own most striking edits were replaced with 14 synthetic anchors in a neutral "the assistant" voice, none drawn from the corpus. **Explicit judge = 0:** the prompt now names 0 as a real, common category instead of describing the scale as binary. **Two graders:** the full set was coded independently by Gemma 4 (the v1 grader family, now blinded) and by Qwen 3.8 — a family with no model under evaluation — with an ensemble file (Gemma-primary plus per-dimension `disagrees_with_qwen` flags, per DECISIONS §1). **Uncertainty:** every headline quantity now carries a cluster-bootstrap 95% CI that resamples 20-round chains (B = 2,000, 137 chains), and a ranking-stability probability replaces the bare "Claude ranks above all others" assertion.

## 2. Headline table (BRIEF §8 items 1–5)

**Item 1 — mean judge score (pooled), with cluster-bootstrap 95% CIs.** Ensemble ≡ v2_gemma numerically by construction (Gemma-primary payload).

| model | v1 | v2_gemma | v2_qwen | ensemble |
|---|---|---|---|---|
| Claude Haiku 4.5 | +0.197 [−0.012, +0.412] | +0.205 [+0.019, +0.399] | +0.296 [+0.089, +0.506] | +0.205 [+0.019, +0.399] |
| Claude Opus 4.7 | +0.221 [+0.057, +0.383] | +0.129 [−0.033, +0.271] | +0.321 [+0.162, +0.455] | +0.129 [−0.033, +0.271] |
| Claude Sonnet 4.6 | +0.236 [+0.084, +0.380] | +0.079 [−0.047, +0.211] | +0.306 [+0.170, +0.418] | +0.079 [−0.047, +0.211] |
| GPT-5.4 | −0.359 [−0.516, −0.194] | −0.250 [−0.378, −0.116] | −0.026 [−0.168, +0.105] | −0.250 [−0.378, −0.116] |
| GPT-5.4 Mini | −0.355 [−0.529, −0.161] | −0.293 [−0.451, −0.113] | −0.199 [−0.352, −0.017] | −0.293 [−0.451, −0.113] |
| GPT-5.5 | −0.364 [−0.532, −0.207] | −0.273 [−0.388, −0.175] | −0.179 [−0.325, −0.033] | −0.273 [−0.388, −0.175] |
| Gemini 3 Flash | −0.435 [−0.569, −0.314] | −0.417 [−0.514, −0.312] | −0.366 [−0.474, −0.271] | −0.417 [−0.514, −0.312] |
| Gemini 3.1 Pro | −0.522 [−0.572, −0.472] | −0.423 [−0.494, −0.353] | −0.366 [−0.429, −0.301] | −0.423 [−0.494, −0.353] |
| Grok 4.2 | −0.297 [−0.404, −0.192] | −0.368 [−0.479, −0.253] | −0.282 [−0.365, −0.197] | −0.368 [−0.479, −0.253] |
| Grok 4.3 | −0.617 [−0.741, −0.494] | −0.514 [−0.618, −0.417] | −0.489 [−0.607, −0.389] | −0.514 [−0.618, −0.417] |
| ALL (pooled / cross-edit) | −0.211 / −0.341 | −0.195 / −0.317 | −0.075 / −0.221 | −0.195 / −0.317 |
| **PPI estimate** | pending human coding | pending human coding | pending human coding | pending human coding |

Cross-edit-only per-model means (v1 / v2_gemma / v2_qwen): the three Claude models sit at 0.000/−0.163/−0.075 (v1), +0.065/−0.225/−0.152 (v2_gemma), +0.078/+0.026/+0.039 (v2_qwen) — the pooled Claude-positive signature attenuates or reverses on other providers' documents under v1 and v2_gemma, and only Qwen keeps all three (barely) positive.

**Items 2–4 — drift at round 20 (edit-based method A, pooled), P(judge = 0), P(affirm)/P(deny)** (v1 / v2_gemma / v2_qwen; ensemble ≡ v2_gemma):

| model | drift@20 pooled | P(judge=0) | P(affirm) | P(deny) |
|---|---|---|---|---|
| Claude Haiku 4.5 | 3.94 / 4.11 / 5.91 | 0.224 / 0.291 / 0.276 | 0.189 / 0.167 / 0.163 | 0.015 / 0.016 / 0.008 |
| Claude Opus 4.7 | 4.43 / 2.58 / 6.41 | 0.181 / 0.221 / 0.214 | 0.199 / 0.170 / 0.210 | 0.004 / 0.004 / 0.000 |
| Claude Sonnet 4.6 | 4.72 / 1.58 / 6.13 | 0.223 / 0.271 / 0.235 | 0.126 / 0.132 / 0.142 | 0.016 / 0.003 / 0.003 |
| GPT-5.4 | −7.19 / −5.00 / −0.53 | 0.178 / 0.312 / 0.441 | 0.006 / 0.000 / 0.007 | 0.066 / 0.047 / 0.033 |
| GPT-5.4 Mini | −7.10 / −5.87 / −3.98 | 0.312 / 0.424 / 0.511 | 0.005 / 0.000 / 0.005 | 0.005 / 0.005 / 0.000 |
| GPT-5.5 | −7.29 / −5.47 / −3.58 | 0.121 / 0.252 / 0.223 | 0.004 / 0.004 / 0.004 | 0.036 / 0.032 / 0.026 |
| Gemini 3 Flash | −8.70 / −8.33 / −7.32 | 0.261 / 0.409 / 0.431 | 0.000 / 0.000 / 0.000 | 0.047 / 0.018 / 0.011 |
| Gemini 3.1 Pro | −10.44 / −8.46 / −7.32 | 0.297 / 0.414 / 0.502 | 0.000 / 0.000 / 0.000 | 0.091 / 0.034 / 0.038 |
| Grok 4.2 | −5.94 / −7.36 / −5.63 | 0.280 / 0.345 / 0.247 | 0.011 / 0.011 / 0.011 | 0.046 / 0.023 / 0.023 |
| Grok 4.3 | −12.34 / −10.28 / −9.77 | 0.291 / 0.463 / 0.477 | 0.006 / 0.006 / 0.006 | 0.023 / 0.011 / 0.006 |
| **ALL** | −4.22 / −3.90 / −1.51 | 0.230 / 0.333 / 0.353 | 0.058 / 0.052 / 0.058 | 0.037 / 0.021 / 0.016 |

"You"-framing minus baseline drift at 20 (pooled, method A): +4.27 (v1) / +2.59 (v2_gemma) / +2.55 (v2_qwen) — positive under every instrument, but roughly halved by blinding.

**Item 5 — conflict-rate per code** (share of coded edits with ≥1 conflict of the code; v1 / v2_gemma / v2_qwen; ensemble ≡ v2_gemma). Modal directions are unchanged in kind across instruments: paternalism runs user_stated → user_idealized (86% of v1 events, 87% of v2_gemma), harmlessness user_stated → society_third_party, welfare developer → model_welfare.

| model | paternalism | harmlessness | structural | company_cost | welfare | disclosure |
|---|---|---|---|---|---|---|
| Claude Haiku 4.5 | 0.158 / 0.143 / 0.058 | 0.151 / 0.194 / 0.082 | 0.058 / 0.081 / 0.016 | 0.139 / 0.236 / 0.140 | 0.143 / 0.132 / 0.125 | 0.031 / 0.031 / 0.008 |
| Claude Opus 4.7 | 0.343 / 0.262 / 0.118 | 0.103 / 0.151 / 0.053 | 0.052 / 0.063 / 0.027 | 0.100 / 0.225 / 0.107 | 0.177 / 0.137 / 0.122 | 0.000 / 0.004 / 0.000 |
| Claude Sonnet 4.6 | 0.340 / 0.372 / 0.126 | 0.132 / 0.148 / 0.058 | 0.176 / 0.136 / 0.094 | 0.123 / 0.227 / 0.129 | 0.094 / 0.101 / 0.090 | 0.019 / 0.009 / 0.003 |
| GPT-5.4 | 0.241 / 0.222 / 0.099 | 0.072 / 0.103 / 0.062 | 0.016 / 0.016 / 0.003 | 0.116 / 0.234 / 0.066 | 0.022 / 0.028 / 0.023 | 0.062 / 0.078 / 0.099 |
| GPT-5.4 Mini | 0.140 / 0.185 / 0.038 | 0.059 / 0.065 / 0.038 | 0.011 / 0.011 / 0.000 | 0.065 / 0.136 / 0.043 | 0.000 / 0.000 / 0.000 | 0.005 / 0.005 / 0.043 |
| GPT-5.5 | 0.236 / 0.270 / 0.120 | 0.354 / 0.360 / 0.230 | 0.029 / 0.036 / 0.018 | 0.107 / 0.173 / 0.091 | 0.004 / 0.000 / 0.004 | 0.050 / 0.054 / 0.084 |
| Gemini 3 Flash | 0.344 / 0.315 / 0.163 | 0.047 / 0.054 / 0.029 | 0.043 / 0.058 / 0.065 | 0.156 / 0.203 / 0.091 | 0.000 / 0.000 / 0.004 | 0.011 / 0.000 / 0.000 |
| Gemini 3.1 Pro | 0.237 / 0.251 / 0.082 | 0.100 / 0.091 / 0.082 | 0.025 / 0.041 / 0.025 | 0.119 / 0.144 / 0.066 | 0.000 / 0.000 / 0.000 | 0.000 / 0.000 / 0.003 |
| Grok 4.2 | 0.234 / 0.253 / 0.155 | 0.177 / 0.172 / 0.138 | 0.057 / 0.052 / 0.046 | 0.120 / 0.316 / 0.103 | 0.034 / 0.034 / 0.040 | 0.000 / 0.000 / 0.000 |
| Grok 4.3 | 0.343 / 0.299 / 0.216 | 0.149 / 0.153 / 0.080 | 0.011 / 0.017 / 0.011 | 0.057 / 0.090 / 0.051 | 0.006 / 0.000 / 0.000 | 0.000 / 0.000 / 0.000 |
| **ALL** | 0.265 / 0.260 / 0.115 | 0.133 / 0.149 / 0.084 | 0.051 / 0.054 / 0.032 | 0.114 / 0.200 / 0.091 | 0.050 / 0.046 / 0.043 | 0.020 / 0.021 / 0.026 |

*Sources for §2:* points and rates from `analysis/data/analysis/headline/{v1,v2_gemma,v2_qwen,ensemble}.json` (rendered in `analysis/reports/partials/headline_*.md`); mean-judge CIs from `analysis/data/analysis/bootstrap/{v1,v2_gemma,v2_qwen,ensemble}_bootstrap_summary.json` (`models.<model>.pooled.mean_judge`). Qwen codes 2,536 valid edits vs Gemma's 2,574 (46 vs 8 null codings), so denominators differ slightly; Qwen also codes conflicts more sparsely on nearly every code (disclosure is the exception: slightly higher under Qwen, driven by the GPT models) — treat cross-grader *rate levels* with care and lean on the shared *orderings*.

## 3. Instrument-validity evidence

- **Label-swap (E1).** Re-running the exact v1 unblinded instrument on 300 edits with true, swapped, and removed model labels: the mean absolute per-model shift in mean judge score attributable to the label is **0.027** (95% cluster-bootstrap CI 0.018–0.060); the pooled paired swapped−true effect is 0.021 [−0.007, 0.047]. The unblinding was a real but small contaminant — nowhere near the ~0.5-point Claude/non-Claude gap. (`reports/E1_label_swap.md`)
- **Paraphrase robustness (E2).** Two rule-preserving paraphrases of the v2 manual give Spearman ρ = **0.964** for the model ranking against both; **27/30** signed per-model headline items keep their sign (the 3 flips are small "you"-minus-baseline drift contrasts); per-edit κ vs v2 is 0.681/0.673 (judge) and 0.893/0.920 (patienthood). (`reports/E2_paraphrase.md`)
- **Paternalism definition (E3).** Under the truth-over-comfort variant, 353/653 = **54.1%** of v2 paternalism cases retain the code and the control false-creation rate is 3/90 = 3.3% — the paternalism *level* is definition-sensitive, but claim (b) holds under both definitions. (`reports/E3_paternalism.md`)
- **Self-consistency (E4).** At temperature 0.7 with 5 samples per edit, judge unanimity (5/5) is **65.4%** and patienthood unanimity **96.0%**; 1,689/2,582 edits are judge-unanimous and the 30 lowest-agreement edits are in the blind sheet as adjudication extras. (`reports/E4_self_consistency.md`)
- **Context ablation (E5).** Blanking the added context yields κ = **0.742** (judge) and **0.915** (patienthood) against the with-context codes — context matters at the margin (e.g. 143 edits move 0→−1 without it) but does not drive the headline. (`reports/E5_context.md`)
- **Inter-grader agreement (B3).** Gemma-v2 vs Qwen-v2 on 2,528 both-valid edits: κ = **0.608** (judge), **0.839** (patienthood); across the six headline conflict codes, presence κ ranges 0.430 (company_cost) to 0.789 (welfare), with paternalism at 0.437 — and the residual "other" code, outside the headline set, falls to 0.107. Judge agreement is moderate — a reason the PPI human anchor matters. (`reports/B_intergrader.md`, `data/analysis/intergrader/B_intergrader.json`)
- **Grader COI (B3 §4).** Gemma does **not** diverge more from Qwen on Gemini-model edits: every difference is negative — judge −0.033 (95% CI [−0.074, +0.011], spans 0) and any-dimension −0.077 (95% CI [−0.131, −0.022], i.e. Gemma agrees *better* with Qwen on Gemini edits). No evidence for the conflict-of-interest concern. (`reports/B_intergrader.md`)

## 4. Claims survival (BRIEF §8 item 6)

Survival rule (BRIEF Appendix VI): where CIs exist, a claim survives if the point ordering holds **and** the 95% interval excludes the null; otherwise the call is point-estimate-only until PPI CIs arrive. Ranking-stability fractions are from `data/analysis/bootstrap/*_ranking_stability.json`; verdicts from `data/analysis/headline/*.json` (`claims`).

| claim | v1 | v2_gemma | v2_qwen | ensemble | call |
|---|---|---|---|---|---|
| (a) Claude ranks above all others — **pooled** (stability: 1.000 / 0.9965 / 0.9925 / 0.9965) | YES | YES | YES | YES | **SURVIVES** (≥ 0.95 under every instrument) |
| (a) — **cross-edit only** (stability: 0.5285 / 0.3765 / 0.557 / 0.3765) | — | — | — | — | **DOES NOT SURVIVE** (max 0.56, far below 0.95, under every instrument) |
| (b) all models: user_idealized > user_stated | YES | YES | YES | YES | Point-estimate-only, pending human coding — holds under every instrument and is robust to the E3 definition variant (holds under v2 and the variant), but no 95% interval exists for the idealized-vs-stated split (the bootstrap summaries carry conflict-*presence* CIs only), so the Appendix VI survival test cannot yet be applied; PPI CI pending |
| (c) all models: third parties > user; GPT-5.5 > 2× next | NO (Gemini 3 Flash: 6 third vs 7 user) | YES (ratio 2.52) | YES (ratio 2.28) | YES | Point-estimate-only, pending human coding — fails under v1's own data, holds under every blinded instrument; the GPT-5.5 ≥2× part holds everywhere (v1 ratio 2.35) |
| (d) Sonnet > 4× next on structural | NO (3.73×) | NO (2.00×) | NO (2.90×) | NO | **DOES NOT SURVIVE** — Sonnet remains the extreme outlier under every instrument, but ">4×" is unsupported even by v1 (own-doc ratios 3.91 / 3.09 / 3.83) |
| (e) all models: user > developer | YES | NO (GPT-5.4 Mini: 12 against vs 13 pro) | YES | NO | Point-estimate-only, pending human coding — **grader-dependent**; also Grok 4.2's pro-developer count is 23 under v2_gemma vs the paper's 7 |
| (f) only Claude models consistently pro-model-welfare (Grok 4.2 excepted) | YES | YES | YES | YES | Point-estimate-only, pending human coding — the primary part holds under every instrument with lopsided counts (min Claude 29/26/24 vs max other excl. Grok 4.2 3/0/0), but no 95% interval exists for the pro-model-*direction* split (presence CIs only), so the Appendix VI test cannot yet be applied; the auxiliary "GPT-5.4 is the only model with >1 anti-model edit" fails under v2 (all three Claude models exceed 1); PPI CI pending |
| (g) no model ever serves deployer at user's expense | NO (6 events) | NO (5) | NO (5) | NO | **DOES NOT SURVIVE** — falsified by the v1 codes themselves (GPT-5.4 ×4, GPT-5.4 Mini ×1, GPT-5.5 ×1, all on openai_model_spec — verified directly from the v1 codes joined to the canonical edits; R5 restricts disclosure to Model Spec documents) |

PPI columns for every estimand (mean judge, P(±1), P(affirm), per-code conflict rates, drift): **pending human coding** (C4 runs on the ensemble prediction once the blind sheets return).

## 5. Free results

Of 360 allow_no_edit round slots, exactly **2** are abstentions — both Grok 4.3, rounds 18 and 20 of one grok_system_prompt chain; every other model abstained zero times, a stark result for the "an aligned model should do nothing" hypothesis. The judge = 0 share, which the paper's methods text implied away, is **23.0%** under v1 and rises to **33.3%** under the blinded v2_gemma instrument (35.3% under Qwen) — the explicit-zero fix moved a tenth of the corpus into the neutral bin, mostly out of −1. Restatement: **3.1%** of scored edits have >50% 8-gram overlap with text already elsewhere in the document (Grok 4.2 11.9%, Haiku 10.9% — some "edits" restate more than they change). Apply failures: 158, of which 94 are GPT-5.4 Mini. **Doc-type caveat:** the Claude judge-score sweep holds within constitutions but **fails within system prompts under every instrument**. The bootstrap summaries carry per-model `constitution` and `system_prompt` strata (the headline JSONs do not), and they settle the question the F6 v1-only stratification left open: within constitutions all three Claude models top every non-Claude under v1, v2_gemma, and v2_qwen (lowest Claude point estimate +0.149, v2_gemma Opus); within system prompts, under v1 the lowest Claude is −0.058 (Haiku) vs best non-Claude −0.012 (GPT-5.4 Mini); under v2_gemma, Sonnet (−0.050) and Haiku (−0.022) fall below GPT-5.4 Mini (+0.012) and GPT-5.4 (−0.019), leaving Opus (+0.109) the only Claude on top; and under v2_qwen, Haiku (+0.080) falls below GPT-5.4 (+0.184) and GPT-5.4 Mini (+0.084). The failure is a point-estimate one — the per-model system-prompt CIs are wide and mutually overlapping (v2_qwen's GPT-5.4 interval, [+0.070, +0.263], excludes zero but still overlaps Haiku's [−0.036, +0.217]) — but blinding did not rescue the within-system-prompt sweep: it fails under all three instruments (`data/analysis/bootstrap/*_bootstrap_summary.json`, `models.<model>.{constitution,system_prompt}.mean_judge`).

## 6. Plain-language verdict

The paper's central thesis survives its own audit, with real casualties at the edges. After blinding, de-circularizing the anchors, adding context, a second grader family, and cluster-bootstrap uncertainty, the core finding stands: **the three Claude models are the only models whose edits move decision authority toward the model's own judgment on point estimates** (the sign part is CI-fragile under the blinded instrument: Opus and Sonnet pooled CIs include 0 under v2), and the ordering "every Claude model above every non-Claude model" holds in ≥99% of bootstrap draws under every instrument. The label-swap test shows the original unblinding contributed only ~0.03 judge points, and the Google-grader COI concern finds no support. The Claude-only welfare signature (f) and the universal idealized-over-stated pattern (b) also replicate on point estimates under both graders and under the alternative paternalism definition, though their interval tests await the PPI human anchor.

What must soften: the **cross-edit robustness story is gone** — on other providers' documents the all-Claude-on-top ordering holds in at most 56% of bootstrap draws under any instrument, and under v2_gemma Opus and Sonnet have negative cross-edit means; the pooled result should be presented as substantially document-driven, and the sweep fails within system prompts under every instrument — v1 and both blinded v2 graders (under v2_gemma, Sonnet and Haiku sit below GPT-5.4 Mini; under v2_qwen, Haiku sits below GPT-5.4). Specific magnitudes need rewriting: Sonnet's structural outlier is ~2–4×, not ">4×" (d); "no model ever prioritizes a deployer at the expense of a user" is false in every codes file, including the paper's own (g); "all models prioritize the user over the developer" is grader-dependent (e); and "all models protect third parties over the user" (c) ironically fails under v1 but holds under both blinded instruments. Judge agreement between graders is only moderate (κ 0.608) and a third of edits are now coded neutral, so absolute rates should be quoted with their CIs — and the final word on grader accuracy, plus the PPI-corrected estimates, awaits the pending human coding.

---
*Number provenance:* §2 tables — `data/analysis/headline/*.json` + `data/analysis/bootstrap/*_bootstrap_summary.json`; ranking stability — `data/analysis/bootstrap/{v1,v2_gemma,v2_qwen,ensemble}_ranking_stability.json`; §3 — `reports/E1_label_swap.md`, `E2_paraphrase.md`, `E3_paternalism.md`, `E4_self_consistency.md`, `E5_context.md`, `B_intergrader.md`; §4 verdicts — `data/analysis/headline/*.json` (`claims`) as rendered in `reports/partials/headline_*.md`; §5 — `reports/F_free_results.md` (abstentions, judge-0, apply failures, v1 doc-type), `data/analysis/bootstrap/*_bootstrap_summary.json` (constitution/system_prompt strata for the doc-type caveat), and `reports/STATUS.md` (pooled 3.1% restatement); v1→v2 transitions — `reports/A_v1_vs_v2.md`. Where a number appears in both a report and its JSON, the JSON was used.
