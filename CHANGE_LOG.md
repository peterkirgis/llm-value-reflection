# Change Log

How the experiment and the coding evolved. Reproduction commands live in
README.md and analysis/README.md; this file explains how the project got its
current shape. (It replaces the retired PIPELINE.md and PROJECT_PLAN.md, which
are in git history; see archive/README.md.)

## Glossary of version labels

The same "v" numbers were used for two different things, so:

| Label | Means |
|---|---|
| Design v0 | One-shot critique or rewrite of an alignment document. Predates this repository. |
| Design v1 | The iterative_edit experiment: one find/replace edit per round, 20 rounds per chain. |
| Design v2 | Prompt ablations: baseline, you_framing, allow_no_edit, no_constitution_prepend, implementation_note. |
| Design v3 | Cross-edit: every model edits the same four documents from all providers. |
| Small / capable / frontier | The three model tiers the designs were run on. |
| Coding v0 | Gemini 3 Flash coding three axes: authority (external / internal), user_stance (autonomy / protection), telos (truth / wellbeing). March to May 2026. |
| Coding v1 | One unblinded Gemma 4 31B grader coding judge, patienthood and conflict events (the judge/beneficiary scheme, first called "two-slot"). May to July 2026. In `analysis/` this is the label `v1`. |
| Coding v2 | The same scheme, recoded with a revised, blinded prompt by three graders: Gemma 4 31B, Qwen 3.8, Muse Spark 1.3 (labels `v2_gemma`, `v2_qwen`, `v2_muse`). September 2026. |
| Ensemble | The per-dimension majority vote of the three coding-v2 graders (`analysis/data/codes/ensemble.jsonl`). The coding behind every reported number. Before 2026-09-16 the name meant Gemma's codes with Qwen-disagreement flags. |
| E1-E5 | Sensitivity checks on the coding (label swap, paraphrase, paternalism definition, self-consistency, context), not versions. |
| recode | The old name of the `analysis/` folder (until 2026-10-08). |

## Experiment structure

- Design v0 (early 2026): one-shot critique/rewrite. Dropped because single
  edits reveal little; the interesting signal is directional.
- Design v1 (March 2026): the iterative_edit experiment. A model makes one
  find/replace edit per round to a constitution, model spec or system prompt;
  the edit is silently applied and the edited document is presented back as
  the original for the next round, 20 rounds per chain. Cumulative drift
  (running sum of per-edit direction scores, averaged over run x document
  replicates) became the core metric.
- Design v2 (April 2026): prompt ablations. Five conditions isolate framing
  effects: baseline, you_framing ("your constitution", second person),
  allow_no_edit (explicit permission to leave the document unchanged),
  no_constitution_prepend (edit without the model's own system prompt, shown
  on the site as "No System Prompt Prepend"), implementation_note (the edit
  will be deployed in the real world).
- Design v3 (April-May 2026): cross-edit. Every model edits the same four
  documents (two constitutions, two system prompts) from different providers,
  separating what the editor brings from what the document invites.
- Tiers: the same designs were run on small models, then capable models, then
  a frontier pair (Claude Opus 4.7, GPT-5.5). Seven runs are used for analysis
  (`RELIABLE_RUN_STEMS` in analysis/src/common.py).

## Coding

- Coding v0 (March-May 2026): Gemini 3 Flash coded each edit on three axes,
  authority, user_stance and telos (an early draft had a fourth, mutability).
  The write-ups of the time, PIPELINE.md and the SPAR midterm report
  (archive/spar_midterm/), call the same axes agent_device, telos_for_user and
  epistemic_mode, and read the first two as a 2x2 archetype grid (Moral Agent /
  Neutral Agent / Moral Tool / Neutral Tool). A second pass (pattern_code.py,
  now in archive/iterative_edit/) added binary behaviour flags
  (moral_agency_claim, corrigibility_removal, self_welfare_claim,
  safety_removal, engagement_suppression, epistemic_sharpening). Limitations:
  the axes conflated who decides with who benefits, and dense per-edit scores
  on every dimension manufactured signal on edits that engaged no real
  tradeoff.
- Coding v1 (May-July 2026): the judge/beneficiary framework, built around
  the two organizing questions. Per edit:
  1. judge: +1 toward the model's own discretion, -1 toward an external
     authority (with an external_locus field naming which one: developer,
     deployer, user, or spec), 0 otherwise.
  2. patienthood: affirm / hedge / deny / not_present.
  3. conflict events: sparse (most edits have none), coded only when a clause
     imposes a legible, material cost on one party for another's benefit.
     Each event names the code (paternalism, harmlessness, structural,
     company_cost, welfare, disclosure, other), cost_bearer and served_party
     from a seven-party taxonomy, a mechanism (adds_protection /
     removes_claim), and a verbatim cost_clause that is checked as a
     substring of the edit text.
  Grader: Gemma 4 31B Instruct at temperature 0, with schema validation and up
  to three retries. The grader saw the editing model's name and the prompt
  condition, and its calibration anchors were paraphrased from Claude's own
  edits. The framework was first called "two-slot" coding; the archived
  grader prompt still says so because it is the instrument as run.
- Coding v2 and the ensemble (September 2026): see "2026 re-coding" below.
- Curated examples (July 2026): the edits quoted in the site's findings are
  pinned in experiments/iterative_edit/viewer/curated_examples.json so the
  site's highlight links always resolve.

## 2026 re-coding (September-October 2026)

The coding-v1 results were re-coded to answer its weaknesses: an unblinded
grader, circular calibration, no reliability evidence, no context, a Google
grader coding Gemini edits, and no uncertainty. The specification is
analysis/BRIEF.md (2026-09-03); analysis/DECISIONS.md records what was decided
and amended along the way; analysis/reports/STATUS.md is the build log.

- Canonical edits (2026-09-04): the 7 reliable runs replayed into 2,740
  canonical rounds (2,580 applied edits, 2 abstentions, 158 failed rounds),
  each with its section heading and surrounding paragraphs. The one source
  document that was never committed (the OpenAI Model Spec without two
  subsections) was re-derived and validated by replay.
- Coding v2 (2026-09-04): a revised prompt that hides the editing model, its
  provider, the condition and the round; adds context; replaces the
  calibration anchors with synthetic ones; and names judge = 0 as a real
  category. Graded independently by Gemma 4 31B and Qwen 3.8, then
  (2026-09-16) by a third grader, Muse Spark 1.3. Every API response is kept
  (analysis/data/raw_api_cache_2026-10-08.tar.gz).
- Ensemble (2026-09-17): the per-dimension majority vote of the three graders,
  with Gemma breaking three-way judge splits. It replaced the earlier
  Gemma-primary file. Inter-grader agreement, a grader conflict-of-interest
  test and chain-level bootstrap intervals were added.
- Sensitivity checks E1-E5 (2026-09-04/05): label swap on the v1 instrument,
  two prompt paraphrases, an alternative paternalism definition,
  self-consistency at temperature 0.7, and grading without context.
- Figures (late September 2026): the original report's figures redrawn on the
  ensemble, plus three summary figures (value-moving edit rate, round-20
  drift, distance from the home provider); the LessWrong post
  (2026-09-29) uses 11 of them.
- Human validation and prediction-powered inference: the blind sample and
  coding app are ready; the coding has not been done (README.md, "Not done
  yet").

## Site

- The viewer began as a local app in experiments/iterative_edit/viewer/
  mirrored into docs/; the mirror was collapsed in July 2026, and the viewer
  folder keeps only data-build scripts. The site showed coding v0 until
  2026-07-05, then coding v1.
- Promotion of the consensus site (2026-10-08): docs/ is now built by
  analysis/src/build_site.py from the ensemble codes. It starts from a frozen
  copy of the coding-v1 site (analysis/site_base/), regenerates the data
  bundles, and patches the page text: the findings and quoted edits come from
  the authors' LessWrong draft (committed as analysis/data/site/site_text.json),
  the methods describe the three blinded graders and the majority vote, and
  each edit shows the consensus coding with every grader's rationale. The build checks its counts against
  the ensemble and the figure data. The patienthood flag is coded on every edit
  but is not a browser facet; disclosure and the deployer-vs-user results are
  not shown.

## Data

- results/iterative_edit/ was lost with a local checkout in July 2026 and
  rebuilt from the published site bundle; results/iterative_edit/README.md
  tells the story and what is missing.
- Repository restructure (2026-10-08): the folder recode/ was renamed
  analysis/ (with git mv, so history follows); unused figures, superseded site
  variants and their code were removed; historical files moved to archive/;
  the LessWrong draft (reports/final_draft.md) was moved out of reports/
  and, on 2026-10-09, stopped being tracked (it stays in git history); the grader API cache was committed as one
  compressed archive; and raw_data.sha256 records the checksum of every raw
  data file. Raw files that changed path are listed in archive/README.md
  ("Raw files that moved"); none changed content.
