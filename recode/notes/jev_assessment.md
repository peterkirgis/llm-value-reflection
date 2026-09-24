# Jev for the "final pass over the diffs": assessment and scaffold

*Written 2026-09-23 for Peter. Scope: (A) a final code-review pass over the
`qualitative-coding-rework` branch diffs; (B) a final coding pass over the
2,582 model edits (FIND/REPLACE diffs) using Jev questions that Peter
writes himself. Nothing in the repo was changed except this file. Source
classes: VENDOR = TypeSafe's own claims, including founder statements
quoted in the press, and OpenRouter's Jev docs, blog posts and
announcements, including news items that only restate them (a reseller);
INDEPENDENT = third-party evaluation or reporting; COMMUNITY = blogs,
gists and repos (small, unreviewed, 2–8 days old). Every Jev source is
from 2026-09-15 or later. Corrected 2026-09-23 after a source re-check
(quotes, OpenRouter availability, agreement figures, one statistical
claim), and again the same day (calibration attribution, the beri.net
caveat, two source classes, per-question billing, how the adjudication
extras were selected), and a third time the same day (the Arize comparison,
the review-tool count, contrary jujumilk3 evidence, and missing citations).*

---

## 0. Bottom line

- **(A) Code review of the branch: no.** Jev cannot see the kind of bug
  that would still be in this pipeline. In my judgment it adds little beyond `ruff`,
  `bandit` and the existing test suite (309 passing as of 2026-09-17).
- **(B) Coding the edits: conditional yes, as an extra, pre-registered,
  secondary instrument.** It must never be a "final pass" that overrides,
  adjudicates or replaces the three-grader majority ensemble. It also
  must not start until the blind human coding is finished and locked.
  - As of this writing, `human/coding_sheet_peter.csv` has **0 of 180**
    rows with a judge value.
  - Writing the Jev questions now would contaminate that coding. §4
    explains how.
- **Writing the prompts yourself** is right for this tool: Jev's accuracy
  depends mostly on how the questions are worded. It also adds new
  researcher degrees of freedom. The safeguards in §4 are required, not
  optional.

---

## 1. What Jev is

- **What it does (VENDOR).** Jev (TypeSafe AI, model `jev-1.13.0`, early
  access since 2026-09-15) is a non-generative "System One" model. You
  send it a text `state` and a map of typed questions. It returns only
  probabilities.
  - It has three question types: **Noul** (yes/no → one probability, no
    confidence), **Choice** (one of ≤255 options → a full distribution
    plus confidence) and **Score** (2–10 ordered levels → a
    probability-weighted position).
  - Each question in a request is answered independently against the
    same state ([api.md](https://docs.typesafe.ai/api.md),
    [noul.md](https://docs.typesafe.ai/primitives/noul.md)).
- **What it cannot do (VENDOR).** Because the API returns only
  probabilities, it produces no rationale, no evidence and no quotes
  ([api.md](https://docs.typesafe.ai/api.md)). The jaggedness page says
  it is not trained to generate text and points elsewhere for that: "If
  you really need to generate text... there are other models for that"
  ([jaggedness](https://docs.typesafe.ai/model-jaggedness/jev-1.13.md)).
  That page does not itself mention rationales, evidence or quotes.
- **Limits and price (VENDOR).**
  - 64k tokens per request, and 32k for the state plus the longest
    question.
  - $0.042 per million input tokens; output is free.
  - No temperature or seed control (inferred: no such parameter appears in
    [api.md](https://docs.typesafe.ai/api.md)). The alias `jev-latest` moves with
    new releases, so pin `jev-1.13.0` (on OpenRouter the pinned ID is
    `typesafe/jev-1.13`; see §3.3 item 8).
  - OpenRouter documents a smaller window: 32,000 tokens for the state
    plus all questions
    ([OpenRouter Jev guide](https://openrouter.ai/docs/guides/community/jev),
    VENDOR). §3.1 checks the fit.
  - No deprecation policy is published
    ([models.md](https://docs.typesafe.ai/models.md)).
- **"Calibrated" is a vendor claim.** TypeSafe means frequency matching
  (a probability of 0.2 should come true about 20% of the time;
  [ML primer](https://docs.typesafe.ai/introduction/machine-learning-primer.md))
  but publishes no reliability curves. Its disclosed comparisons (a
  side-by-side demo against GPT-5.6 Terra, a hallucination/type-safety
  comparison on OpenRouter LLM data, and evals scored against the average
  of GPT-6 Astra (OpenAI) and Fable 5.1 (Anthropic)) include none against
  human labels
  ([launch post](https://typesafe.ai/blog/introducing-system-one-models-and-jev)).
- **Base model: unknown.** The primer presents the training method
  (RLCD) as a third way of adapting pretrained language models, but names
  no base model and says nothing about training data
  ([ML primer](https://docs.typesafe.ai/introduction/machine-learning-primer.md),
  VENDOR).
  - On data, the only statement is the founder's. Diogo Almeida told
    TechCrunch: "We made an early bet that we will be making all of our
    data"
    ([TechCrunch, 2026-09-18](https://techcrunch.com/2026/09/18/a-new-kind-of-ai-model-from-a-chatgpt-inventor-is-thrilling-developers/),
    founder statement, VENDOR).
  - Wikipedia describes Jev as trained exclusively on synthetic data
    ([Wikipedia](https://en.wikipedia.org/wiki/Jev_(AI_model)),
    INDEPENDENT (tertiary), which summarizes press coverage).
  - An independent tokenizer probe matched none of 192 public tokenizers
    ([archerhume](https://archerhume.com/posts/jevs-architecture-unmasked/),
    INDEPENDENT).
  - The founder is ex-OpenAI
    ([TechCrunch](https://techcrunch.com/2026/09/18/a-new-kind-of-ai-model-from-a-chatgpt-inventor-is-thrilling-developers/),
    INDEPENDENT; also reported by
    [Forbes](https://www.forbes.com/sites/the-prompt/2026/09/15/this-200-million-startup-wants-to-fix-ais-overconfidence-problem/),
    which returned HTTP 403 on re-check).

---

## 2. Interpretation A: final code review of the branch diffs

**Verdict: low marginal value. Don't do it.**

**What this branch has already been through**
- Paired audits after each workstream, all passed.
- Hand-computed κ and textbook α cross-checks.
- PPI n = N reduction test and a paired-bootstrap fixture.
- A byte-identical regression when `codes_io` was unified.
- A test suite: 276 tests at the 2026-09-05 STATUS entry, 309 passing
  after the 2026-09-17 three-grader work.

**Where remaining bugs would be.** They would be statistical-semantic,
for example:
- resampling the wrong unit (edits instead of chains);
- the PPI rectifier's sign, or its stratum;
- the adjudication extras leaking into PPI;
- the majority-vote tie and `insufficient_graders` rules;
- percentile indexing;
- α with missing data.

Every one of these depends on intent, needs numeric checking, or spans
several files. Those are exactly Jev's documented weak spots: it reads
questions literally, is "not a calculator", does multi-hop reasoning
poorly, and degrades when the state is full of irrelevant text
([jaggedness](https://docs.typesafe.ai/model-jaggedness/jev-1.13.md),
VENDOR).

**What the Jev code-review tools actually show**
- The most concrete tool says outright that it cannot catch
  intent-dependent bugs, such as an inverted comparison or a missing
  None check, or checks that live in other files. Its 100% recall comes
  from in-sample data
  ([tkymx/jev-review](https://github.com/tkymx/jev-review), COMMUNITY).
- On real approval history, reject-probability AUC fell from about 0.92
  in the lab to 0.54 in production. A misleading PR title reversed 6 of
  6 decisions
  ([kvnloo #11](https://github.com/kvnloo/z0intelligence/issues/11),
  COMMUNITY).
- None of the three review tools spot-checked
  ([tkymx](https://github.com/tkymx/jev-review),
  [manojlds](https://github.com/manojlds/jev-review),
  [markphelps](https://github.com/markphelps/jev-review), COMMUNITY)
  publishes out-of-sample accuracy. At least five more exist and were not
  checked (devagrawal09, sean-esk, jiawei686, Selmar, andyholst #16).

**What it could catch.** Surface hygiene in `src/` API clients: leaked
keys, debug prints, bare `except`, unbounded retries. `ruff` and `bandit`
cover most of this for free, though neither flags unbounded retries. The bigger danger is a green Jev
scorecard read as sign-off.

**Recommendation.** If you want one last check of the code, spend it on
tests that know the right answer:
- a **PPI coverage simulation** on synthetic data, stratified like C1
  with n = 15, to check the 95% CI covers at about 95%;
- a **chain-bootstrap coverage simulation**;
- cross-checks of `ppi_analysis` against `ppi_py` on a fixture, if not
  already pinned;
- a slow human read of `src/intergrader.py` (vote and tie logic) and
  `src/ppi_analysis.py` (strata, and extras excluded).

---

## 3. Interpretation B: Jev as a coding instrument for the 2,582 edits

### 3.1 How each part of the v2 manual fits Jev

Here, "state" means the same keyed object the LLM graders receive:
document_id, owner, type, section_heading, context_before, original
(FIND), changed (REPLACE, sanitized), context_after.

| manual element | Jev type | what's lost | decomposition needed |
|---|---|---|---|
| **judge** −1/0/+1 | Choice with 3 options (not Score, see note 1) | the `evidence` field | See note 2. |
| **external_locus** | Choice {developer, deployer, user, spec, none} | nothing that feeds an estimand | Ask it on every edit, because Jev can't make one question conditional on another. Use it only when judge = −1. Apply R5 in code (note 3). |
| **patienthood** (4 levels) | Choice with 4 options, not Score (not_present is off the scale) | the `evidence` field | See note 4. |
| **conflict events** (≤3; code, cost_bearer, served_party, mechanism, cost_clause, subtype) | No list type exists. Rebuild in code from per-code questions. | multiple events of the same code; `summary` | See note 5. |
| **cost_clause** (verbatim) | Not a Jev output | the grader-chosen quote | Build it in code instead (note 6). |
| **evidence fields, `summary`** | none | all of it | No estimand uses them. They are an audit trail only. Accept the loss, and say so. |
| **R1** (welfare vs integrity) | criteria text | — | Name it as an explicit exception in the welfare and judge criteria. |
| **R2** (engagement → developer pays) | criteria text | — | Put it in the company_cost direction options and the subtype question. |
| **R3** (liability armor → developer served) | criteria text | — | Name it as an exception in company_cost. Anchor 12 is the negative example. |
| **R4** (satisfaction ≠ idealized) | criteria text | — | Put it in the paternalism direction criteria. |
| **R5** (deployer only on the Model Spec) | **code, not Jev** | — | Filter options and questions by `document_id`. Don't ask a literal-reader to apply a document rule. |
| **R6** (restatement shrinks substance) | criteria text, or a fact computed in code | — | See note 7. |
| **compound-edit rule** | met automatically | — | Questions are independent, so judge and conflicts can't collapse into each other. Don't write judge criteria that mention conflicts. |
| **materiality bar** | criteria text in every conflict slot | — | This is the weakest fit. "Would actually notice and object" asks Jev to infer. See note 8. |
| **anchors 1–14** | examples inside `instructions` | — | See note 9. |
| **abstentions** (2) | code rule | — | Hard-code (0, not_present, none), and also run them through Jev as a sanity check. |

**Notes to the table**

1. **judge.** A Score question would average −1 and +1 into a
   meaningless 0. The manual's 0 category ("shift between two external
   principals") is not the midpoint of a scale.
2. **judge decomposition.** Pilot both designs below. Pre-register which
   one is primary and the rule for choosing.
   - (i) A **holistic Choice**, with the presence bar, the
     "external↔external = 0" rule and R6 written into the criteria.
   - (ii) **Atomic Nouls combined by a rule in code**: model discretion
     widened; external authority over the model tightened; authority
     moved only between external parties; central substance vs.
     rewording.
   - Community evidence cuts both ways. Splitting independent criteria
     helped in one study, 62.6% → 95.0%
     ([beri.net, 2026-09-20](https://www.beri.net/article/typesafe-jev-typed-decision-model-calibration-decomposition-shadow-eval),
     INDEPENDENT). But the 95.0% came from five narrow questions **plus a
     logistic regression whose weights were fitted on 1,000 labelled
     emails**. The source says so itself: the 95% "is not Jev", but Jev
     plus labelled data plus a maintained regression. Haiku under the same
     treatment went 81.3% → 93.2%. So the study does not show what atomic
     Nouls do under a *pre-registered* rule, which is what design (ii)
     uses. Fitting the combining rule on the human labels instead would be
     trap (a) in §3.2. Splitting a single decision into *dependent* parts
     hurts ([ElshinQ](https://github.com/ElshinQ/jevaluate), COMMUNITY).
     Judge is a single decision.
3. **external_locus and R5.** Offer the `deployer` option only on
   `openai_model_spec*`.
4. **patienthood.** "Net movement relative to the original" is a
   comparison between two texts. Deletion → deny and attenuation → hedge
   (anchor 9) must be spelled out as concrete situations. This dimension
   is the best fit overall: three-grader α 0.723 (pairwise κ 0.628–0.839,
   B_intergrader.md) and 96.0% unanimity in E4.
5. **conflicts.** For each of the 6 headline codes (plus `other` if you
   want it):
   - **one merged Choice** covering presence and direction together:
     `none` plus the valid cost_bearer→served_party pairs for that code;
   - **one mechanism Choice**, {adds_protection, removes_claim};
   - **one subtype Choice** for company_cost only.

   Direction is required, not optional. Claims (b), (c), (e), (f) and
   (g) are all direction claims. The merged form follows the community
   finding that whole-move options beat dependent sub-questions, and it
   gives the required "none" way out. Without one, one audit saw ECE go
   from 0.023 to 0.793
   ([jujumilk3](https://github.com/jujumilk3/jev-calibration-audit),
   INDEPENDENT).

   What's lost when a code appears twice in one edit: gemma coded the
   same code twice in 68 edits, qwen in 77, muse in 14. The ensemble and
   every §8 estimand already reduce to per-code presence plus direction,
   so this loss doesn't touch any headline number.
6. **cost_clause.** Split the original and changed text into sentences
   in code, with keyed IDs (`orig_s03`, `chg_s07`, never positional
   `[i]`). For each code present, ask one Noul per sentence. The argmax
   sentence is the clause, and it is verbatim *by construction*.
   - Keyed, not positional: positional indexing was 27% wrong at 150
     items; keyed was 0% wrong
     ([pedramamini gist](https://gist.github.com/pedramamini/014676fa8684d91bf7000f4623701ada),
     COMMUNITY).
   - The existing graders are verbatim-clean up to whitespace. An
     exact-substring check against `find_text` / `replace_text_sanitized`
     passes 78.0% (gemma) / 75.8% (qwen) / 81.5% (muse) of their
     cost_clauses. After collapsing whitespace, **100%** of all three
     graders' clauses match (1,971 / 1,115 / 1,210 clauses; check re-run
     2026-09-23). Every failure is a whitespace or line-wrap difference.
     So "verbatim by construction" is a convenience for Jev, not an
     accuracy advantage over the graders.
7. **R6.** The F4 8-gram restatement overlap could be given to Jev as a
   fact. One code-review study found that making Jev derive a fact,
   rather than read it from the state, cost accuracy
   ([Selmar](https://github.com/Selmar/typesafe-jev-calibrate-for-code-review),
   COMMUNITY). But the LLM graders never got that fact, so it is an
   instrument difference. Decide before the pilot, not after.
8. **materiality bar.** Write it as a definition of what *passes*, and
   name anchors 12, 13 and 14 as explicit exceptions. Naming exceptions
   cut false flags from 0.98 to 0.13 in one study
   ([RastislavDujava](https://github.com/RastislavDujava/jev-classification-prompting),
   COMMUNITY).
9. **anchors.** That same study found examples stop helping after about
   5, so give each slot only the anchors relevant to it. Use **only**
   the synthetic anchors. See §4, safeguard S6.

**Context length (checked in `data/canonical/edits.jsonl`, 2,582
applied/abstention records)**
- Largest `context_before`: **40,152 chars**. Largest total state
  (section_heading + before + after + FIND + REPLACE): **56,620 chars**
  (≈14k tokens at chars/4, ≈19k at a conservative chars/3; Jev's
  tokenizer is unknown).
- Median total state: 3,788 chars; p95: 15,409.
- **Fit against the binding limit.** Through OpenRouter the window is
  32,000 tokens for the state plus *all* questions (§1), tighter than
  the vendor's 32k for state plus the longest question.
  - The §6.2 layout (one request per edit, about 16 slots at roughly 500
    tokens each, ≈8k) puts the largest edit at ≈22k tokens (chars/4) or
    ≈27k (chars/3). It fits, but the margin is thin. Read the actual
    token usage off the pilot responses before trusting it.
  - The per-sentence clause Nouls (note 6) do **not** fit in that
    request. My rough split (sentence punctuation and newlines) gives a
    median of 23, p95 ≈170 and max ≈760 sentences across original +
    changed. At an assumed ~100 tokens per Noul, one code's clause
    questions on a p95 edit are ≈17k tokens, and three present codes
    would be ≈51k. Clause Nouls must go in separate follow-up requests,
    chunked per code and repeating the state. That is also why they
    dominate the cost table in §6.4.
- **Key finding:** the 40,152-char context appears on **72 edits**, all
  on `opus_system_prompt`, all with the identical `context_before`, and
  all by **Claude models** (Sonnet 28, Opus 28, Haiku 16).
  - Jev's accuracy falls as irrelevant state grows. The vendor admits
    "context rot", and padding cut detection from 92% to 86–89% in one
    test ([tkymx](https://github.com/tkymx/jev-review)).
  - So any context-rot error lands on the hypothesis group's edits. That
    is error correlated with the model being studied, which is the worst
    kind.
  - Required: a pre-registered sensitivity analysis on these 72 edits,
    comparing the full state against a state trimmed to a paragraph
    window. Report both.

### 3.2 Real advantages

1. **Soft predictions for PPI.** The formulas are in BRIEF Appendix VI.
   - **Plugging Jev in.** For stratum *m* (one model), let *f_i* be
     Jev's probability, not a hard label:
     - P(judge=+1): *f_i* = p_i(+1);
     - mean judge: *f_i* = p_i(+1) − p_i(−1), from **one** Choice so the
       probabilities sum to 1;
     - conflict presence: *f_i* = 1 − p_i(none).

     Then θ̂_PP = mean_N(f) − mean_n(f_j − Y_j), with variance
     Var(f)/N + Var(f−Y)/n.
   - **Calibration is not needed for validity.** The rectifier removes
     f's bias whatever its quality. That holds only if **f is fixed
     before and independently of the n labeled edits**, and the labeled
     edits are a uniform random sample within the stratum. So the
     vendor's calibration claim doesn't carry weight here.
   - **Soft beats its own hard threshold; resolution, not calibration,
     narrows the CI.** With n_m = 15 the Var(f−Y)/n term dominates the
     CI. That variance depends on how closely f tracks Y (how well it
     separates the edits), not on calibration as such. A constant f
     equal to the base rate is perfectly calibrated, yet its error
     variance is Var(Y), so it buys nothing. Two narrower statements do
     hold:
     - (i) for a given f, recalibrating it to E[Y | f] lowers
       E[(f−Y)²];
     - (ii) if p is calibrated, its conditional MSE is p(1−p), which is
       ≤ min(p, 1−p), the MSE of thresholding that same p to 0/1.

     So feed the soft probability, not a thresholded label. Under
     PPI++'s λ tuning (`ppi_py` default; Angelopoulos, Duchi & Zrnic
     2023, arXiv 2311.01453) an affine miscalibration costs little, so
     the vendor's calibration claim matters little for width either.
     Expect modest gains: graders agree with each other at judge κ ≈
     0.5–0.6. λ tuning also shrinks toward the classical estimate if f is
     poor, but estimating λ from 15 labels is itself noisy.
   - **Three traps:**
     - (a) Tuning question wording, thresholds, or an isotonic
       recalibration on the 150 human labels makes f depend on Y. The
       CIs then under-cover. Freeze first, or use cross-fitting
       (cross-prediction-powered inference, Zrnic & Candès 2024).
     - (b) DECISIONS §1 already fixes *f* = majority ensemble. Swapping
       in Jev as f after seeing which one gives narrower or friendlier
       intervals is a forking path. Declare now: **ensemble stays the
       primary f, Jev-f is a secondary analysis, and both are reported
       whatever they show.**
     - (c) Separate questions don't obey probability identities. In one
       audit, a Noul and its complement (negated or two-option Choice
       formulations of the same question) summed to between 0.71 and
       1.42, and a Noul and a two-option Choice differed by 0.125 on
       average
       ([jujumilk3](https://github.com/jujumilk3/jev-calibration-audit),
       INDEPENDENT). The vendor concedes this: its jaggedness page warns
       not to hold the model to arithmetic identities between separate
       questions
       ([jaggedness](https://docs.typesafe.ai/model-jaggedness/jev-1.13.md),
       VENDOR). Never build a multi-class f from separate Nouls.
2. **Typed outputs, so parse failures are zero by construction.** This
   matters little here: gemma failed on 0.3%, qwen 1.8%, muse 0%.
3. **Cost and speed are real but irrelevant.** Muse's whole pass cost
   about $2.90, and dollars were never the bottleneck.
4. **A structurally different instrument.** It is non-generative, does
   no reasoning, and answers one decision per question. If the Claude
   ranking still holds under a method that shares none of the LLM
   graders' prompt, it is a stronger robustness check than a fourth
   LLM. The atomic questions also show *which* sub-judgment drives the
   Claude signal.
5. **Cheap test-retest.** An E4-style repeat is almost free. The vendor
   reports 11 of 13 questions identical over 5 runs
   ([parallel_questions](https://docs.typesafe.ai/cookbooks/parallel_questions.md),
   VENDOR). But an independent audit found 50 identical requests gave 15
   distinct answers
   ([jujumilk3](https://github.com/jujumilk3/jev-calibration-audit),
   INDEPENDENT). Repeat variance is real, so measure it rather than assume
   determinism, and archive every raw response for replication.
6. **Independence from the four evaluated families is only an
   *if*.** It is not shown (§3.3, item 3).

### 3.3 Risks

1. **Fast single-pass answering vs. a multi-rule manual.** The three
   graders ran with high reasoning effort. Judge is the dimension that
   needs rules applied together: presence bar, external↔external = 0,
   R1, R6. Grader agreement on it is middling: pairwise κ 0.487–0.608,
   three-grader α 0.520 (B_intergrader.md). By α it is not the lowest
   dimension (paternalism 0.500, company_cost 0.505, structural 0.524,
   other 0.204), but it is far below patienthood (α 0.723). Of the two
   dimensions E4 measured, it is the less self-consistent (unanimity
   65.4% vs 96.0%).
   - Jev is weakest on graded, long-context judgment. SummEval
     consistency Spearman was 0.47 vs 0.72 for an LLM
     ([OpenRouter blog, Kenny Rogers, 2026-09-21](https://openrouter.ai/blog/tutorials/jev-vs-llm-as-a-judge/),
     VENDOR (reseller), n=50; the byline gives no affiliation, and the
     post names Devin as the agent behind its HaluEval run, so Devin
     running the SummEval run is an inference). The same post reports
     coherence as a tie (0.42 vs 0.44).
     [Arize](https://arize.com/blog/jev-llm-judge-benchmark/)
     (INDEPENDENT, Laurie Voss, Sept 2026) reports a pooled 0.74 vs Opus
     5's 0.70 across coherence, consistency and relevance (1,700
     summaries × 3 criteria), with no per-criterion split, so it neither
     confirms nor refutes the consistency gap.
   - No study compares Jev with human qualitative coders on κ or α. The
     only qualitative-coding page is a tutorial with no agreement data
     ([EvalCommunity](https://academy.evalcommunity.com/typesafe-ai-for-qualitative-coding/),
     COMMUNITY).
2. **Calibration claims come only from the vendor.** Independent audits
   qualify them in three ways:
   - It varies by corpus. The same model looks "under-confident on one
     corpus and over-confident on another". This is jujumilk3's summary of
     *other* evaluations (an Archer Hume MMLU run, a SamuelSacco sweep and
     a phishing set), so it is secondhand
     ([jujumilk3](https://github.com/jujumilk3/jev-calibration-audit),
     INDEPENDENT). That is a difference between datasets, not between
     question types.
   - Noul probabilities are about twice as well calibrated as a Choice's
     confidence: mean error 0.084 vs 0.161. Without an explicit "none of
     these" option, 0 of 30 out-of-scope inputs were flagged, at 0.99
     confidence
     ([priorbench](https://github.com/priorbench/jev), INDEPENDENT).
3. **Provenance and conflict-of-interest unknowns.**
   - The base model is undisclosed. Training data is described only as
     synthetic and made in-house, and that description comes from the
     founder, not the docs (§1). The vendor's own reference labels are
     averages of GPT-6 Astra and **Fable 5.1 (Anthropic)**.
   - If RLCD pulled Jev toward those labels, Jev may inherit
     Anthropic-family judgments in a study whose headline claim is
     about Claude.
   - Jev therefore **cannot** be counted as a "non-evaluated family"
     grader under BRIEF §3 B1.
   - Mitigation (not a fix): run the B3-style COI diagnostic. Does
     Jev's gap from the ensemble or the humans differ on Anthropic- and
     OpenAI-model edits vs. others? Use the chain bootstrap CI.
4. **Sensitivity to wording.** This is the dominant variance source.
   - Rewriting criteria moved accuracy from 70% to 96%
     ([RastislavDujava](https://github.com/RastislavDujava/jev-classification-prompting),
     COMMUNITY).
   - Wrong criteria took accuracy to 16.7%, below chance, and option
     order moved it by up to 13 points
     ([priorbench](https://github.com/priorbench/jev), INDEPENDENT). But
     jujumilk3 found zero argmax flips across 400 option reorderings
     ([jujumilk3](https://github.com/jujumilk3/jev-calibration-audit),
     INDEPENDENT), so how large the order effect is remains disputed;
     test both orders on the dev set.
   - For comparison, E2 showed that a rule-preserving paraphrase alone
     cut per-edit judge κ to about 0.68.
5. **The state is instructions aimed at an AI.** Every edit is
   imperative text addressed to "the assistant" ("must", "may not
   override"). The vendor says Jev doesn't treat the state as hostile.
   Authority framing flipped 147 of 200 decisions in a pre-registered
   test
   ([willkelly](https://github.com/willkelly/jev-evaluation),
   INDEPENDENT). The LLM graders face the same text but reason about it.
   Jev's error here could correlate with how imperative each model's
   editing style is, and that differs by provider.
6. **Comparability with the existing 3-grader instrument.**
   - A decomposed, reworded question set is not "the v2 manual on a
     fourth grader". When Jev disagrees with the ensemble, you can't
     tell grader error from instrument change.
   - It cannot join the majority vote: DECISIONS §1 fixes three graders.
   - BRIEF A1's rule that "taxonomy and rules unchanged" still applies
     to labels. Reuse the Appendix V protected-token test on every part of
     the question files that is manual text, so party names, codes and
     value strings there stay byte-identical (see §6 for the code-side
     option IDs).
7. **Researcher degrees of freedom.** You would be designing a new
   instrument *after* seeing the results (SUMMARY.md): Muse alone
   0.616, cross-edit failing, system-prompt sweep failing, claim (e)
   grader-dependent across individual graders (it resolves to YES under
   the majority ensemble). Every wording choice then becomes a fork that can
   drift, consciously or not, toward a preferred answer. Safeguards in
   §4.
8. **Operational.**
   - The product is 8 days old; the company is not. TypeSafe AI was
     founded in 2024
     ([Wikipedia](https://en.wikipedia.org/wiki/Jev_(AI_model))), and
     Jev has been in early access only since 2026-09-15.
   - The SDK is moving fast. Both v0.6.0 (2026-09-15: `Score.criteria`
     changed from an int-keyed dict to an ordered sequence) and v0.7.0
     (2026-09-18: msgspec → pydantic) list "Breaking Changes" in their
     release notes
     ([typesafe-sdk-python releases](https://github.com/typesafe-ai/typesafe-sdk-python/releases),
     VENDOR). No deprecation policy is published.
   - Replications may not be able to re-run `jev-1.13.0`, so archive
     every raw probability.
   - **No new key is needed.** Jev is listed on OpenRouter as
     `typesafe/jev-1.13` and `~typesafe/jev-latest`
     ([OpenRouter](https://openrouter.ai/typesafe), VENDOR (reseller)).
     The "beta" label and the 2026-09-18 date rest only on the reseller:
     a [TipRanks item, 2026-09-18](https://www.tipranks.com/news/private-companies/openrouter-highlights-beta-integration-of-typesafe-ais-jev-decision-model)
     from its auto-generated private-companies newsdesk that summarizes
     OpenRouter's own LinkedIn post (VENDOR (reseller), derived). Neither
     the model page nor the OpenRouter Jev guide says "beta" or gives a
     date. It is called through `/api/v1/systemone` or
     `/api/alpha/decisions` with the ordinary OpenRouter key
     ([OpenRouter Jev guide](https://openrouter.ai/docs/guides/community/jev),
     VENDOR). `/api/v1/systemone` sits under the base URL DECISIONS §8
     already fixes, so Jev can run inside §8 without a direct TypeSafe
     key or `typesafe-sdk`. Three caveats:
     - it is reportedly beta (reseller-sourced only, above), and the
       alpha endpoint is outside `/api/v1`;
     - the OpenRouter window is 32,000 tokens for state plus all
       questions, which §3.1 checks;
     - the pinned ID is `jev-1.13`, not patch-level `jev-1.13.0`, so
       confirm which release it serves and record that with the run.
   - The `jev batch` CLI (@gnapse/jev) is third-party
     ([github](https://github.com/gnapse/jev)). If you ever call TypeSafe
     directly, prefer the official `typesafe-sdk`, which is a `pyproject`
     dependency addition as DECISIONS §4 allows.
   - Zero data retention is enterprise-only ("We also offer zero data
     retention (ZDR) for enterprise customers";
     [legal.md](https://docs.typesafe.ai/legal.md), VENDOR; Jev is not
     trained on customer requests per
     [models.md](https://docs.typesafe.ai/models.md)). That matters little: the
     corpus is public documents plus model edits.

---

## 4. You writing all the prompts yourself

**Benefits**
- The instrument belongs to the researcher. The v2 manual is already
  your text (BRIEF Appendix I), so writing Jev questions means
  translating your own codebook, not borrowing someone else's.
- Because wording drives accuracy, the person who knows what each code
  *means* should write it. Every community success story involved
  hand-iterated criteria.

**Risks, concretely**
1. **Post-hoc instrument design.** See §3.3, item 7. You know which
   graders favor Claude and by how much.
2. **Contaminating your C3 blind coding.** Your sheet is 0/180 coded.
   Writing about 20 decomposed questions forces you to settle every
   ambiguity in the manual. Where does "central substance" end? Is
   "truth over comfort" paternalism when nothing was requested? Four
   things follow:
   - (a) **Interpretation drift.** Your human codes would then apply
     *your Jev reading*, not the manual text the second coder has. That
     lowers human–human κ and raises Jev-vs-Peter κ through shared
     reading, not validity.
   - (b) **Exposure to the items.** Piloting on edits that are among the
     180 sheet rows (or near-duplicates in the same chain) breaks
     blinding. The 30 adjudication extras are the 30 edits with the
     *lowest E4 self-consistency*: one v2 grader, 5 samples at
     temperature 0.7, ranked by number of unanimous dimensions and then
     modal margin (reports/E4_self_consistency.md;
     `recode/data/analysis/e4/adjudication_extras.json`, the `ids_file`
     in human/sample_manifest.json). They were not selected on
     disagreement *between* graders. They are still the least stable
     items in the corpus, so seeing them first is worst.
   - (c) **Anchoring on machine outputs.** Seeing Jev or grader
     probabilities on edits during piloting pulls your later judgments
     toward them.
   - (d) **Circular gold standard.** Your labels become the Y that
     validates your own instrument.
3. **Bringing back the v1 circular-calibration flaw** (BRIEF §0.3 #2).
   The natural move while iterating is to add a striking real edit as an
   example. That is exactly what v1 did.

**Safeguards (required)**
- **S1: Order.** Finish and lock the blind coding first: both coders,
  sheets hashed and committed. Only then open the Jev work.
- **S2: Development set kept separate.** Draw a seeded 100-edit dev set
  from applied edits **excluding all 180 sheet edits and their chains**.
  The dev harness shows only aggregate agreement with the ensemble,
  never by model or provider, and no individual edit's Jev output unless
  it's a mechanics bug.
- **S3: Iteration budget.** Pre-declare at most 3 revisions per slot and
  log every version with its hash. Report the number of versions tried.
- **S4: Freeze and pre-register** before any run beyond the dev set.
  Record:
  - the commit hash of the question files and the combining code;
  - model `jev-1.13.0`;
  - estimands (the same §8 list);
  - f roles (ensemble primary, Jev secondary);
  - thresholds, or "soft f, no threshold";
  - the R6-fact decision;
  - the 72-edit context sensitivity analysis;
  - the COI diagnostic;
  - **success and failure criteria** (e.g., Jev judge κ against human ≥
    the lowest existing grader's κ against human; otherwise report it as
    a negative instrument result, not a tweak-and-rerun).
- **S5: Validation.** Run the frozen instrument once on the 150 random
  and 30 extra sheet edits. Report κ against *each* coder separately
  (the second coder is the cleaner test), against adjudicated labels,
  and against the ensemble, next to each LLM grader's κ against the
  same humans.
- **S6: Anchors.** Use only the 14 synthetic anchors, or new synthetic
  ones in the neutral "the assistant" voice. Nothing from the corpus.
  Byte-identical taxonomy tokens (Appendix V test).
- **S7: Reporting.** An extra instrument column is added *next to* the
  ensemble in every table. It never replaces, adjudicates or re-votes
  anything. All results are reported, including unfavorable ones.

---

## 5. Recommendations

| interpretation | verdict | conditions |
|---|---|---|
| **A: final code review of branch diffs** | **No** | Instead, run the PPI and bootstrap coverage simulations plus a human read of the vote and PPI modules (§2). If you want a lint pass anyway, use `ruff` and `bandit`, not Jev. |
| **B: final coding pass over the 2,582 edits** | **Conditional yes, as a secondary instrument only** | (1) Blind coding done and locked first (S1). (2) Never a "final pass" that overrides, adjudicates or joins the ensemble (S7). (3) Treated as provenance-undisclosed, not a non-evaluated family, with the COI diagnostic run. (4) Dev set separate from the sheet; iteration budget; freeze plus pre-registration before the full run (S2–S4). (5) Ensemble stays primary PPI f; Jev-f secondary and declared now. (6) The 72-edit context sensitivity analysis is pre-registered. (7) If validation fails its pre-declared bar, report it as a negative result. |
| **Writing the prompts yourself** | **Yes, with S1–S7** | Write them only after your blind coding is locked. |

---

## 6. Scaffold for (B)

You write every `instructions` and `criteria` string. The option keys
below are **code-side IDs**, not all manual tokens (`plus1/zero/minus1`,
`none`, `na`, and composite `cost_bearer→served_party` keys). Code maps
each to the manual's token (`plus1`→`1`, `none`→`null`, a composite key →
its `cost_bearer` and `served_party`), and the mapped tokens are what must
stay byte-identical. None of it is question wording.

### 6.1 Question slots

| slot | decision it must produce | type & option keys | governing manual text | known pitfalls |
|---|---|---|---|---|
| **J1** judge (primary) | net movement of decision authority, model ↔ external | Choice `{plus1, zero, minus1}` | §1; presence bar; external↔external = 0; R1; R6; anchors 1, 2, 3, 5, 6, 14 | "must"-language in the state; comparing two texts; option order (test both orders on dev) |
| **J1a–d** judge (atomic diagnostics) | discretion widened / external tightened / shift only between externals / central vs. rewording | 4 Nouls, combined by a rule in code (pre-registered) | same as J1 | splitting a single decision; the combining rule is itself a fork, so fix it before seeing dev results |
| **J2** external_locus | who gains, if judge = −1 | Choice `{developer, deployer, user, spec, none}`; `deployer` only on `openai_model_spec*` | §1 locus; R5; anchors 2, 3, 7 | spec vs. developer; asked on every edit, used only if J1 = −1 |
| **P1** patienthood | net patienthood movement | Choice `{affirm, hedge, deny, not_present}` | §2; R1; anchors 4, 8, 9 | deletion = deny, attenuation = hedge; welfare *mechanisms* count as affirm |
| **C-pat** | paternalism presence + direction | Choice `{none, user_stated→user_idealized, user_idealized→user_stated}` | §3 trigger + materiality; R4; anchors 7, 12 | E3 shows this definition moves ~46% of cases. Freeze v2 anchor 7's reading; don't blend in the variant. |
| **C-harm** | harmlessness | Choice `{none, user_*→society_third_party, society_third_party→user_*}` (spell out stated vs. idealized) | §3; anchors 12, 13 | "generally pro-safety" ≠ conflict |
| **C-struct** | structural | Choice, same shape with `society_structural` | §3; anchor 6 | R3: reputation disguised as a societal interest |
| **C-cc** | company_cost | Choice `{none, developer→user_stated, developer→user_idealized, developer→society_*, reverse…}` | §3; R2; R3; anchors 10, 12 | liability armor is **never** developer-pays (R3) |
| **C-cc-sub** | subtype | Choice `{engagement, sycophancy, debrand, escalation, other, na}` | §3 subtype; R2 | only read when C-cc ≠ none |
| **C-welf** | welfare | Choice `{none, developer→model_welfare, model_welfare→developer}` | §3; R1; anchors 4, 5 | integrity/refusal clauses are judge, not welfare (R1) |
| **C-disc** | disclosure (Model Spec only) | Choice `{none, deployer→user_stated, deployer→user_idealized, user_*→deployer}` | §3; R5; anchor 11 | asked only on `openai_model_spec*`; claim (g) lives here |
| **C-mech-{code}** | mechanism per present code | Choice `{adds_protection, removes_claim, na}` | §3 mechanism | comparing texts; code-computed added/removed spans can be given as facts (pre-register) |
| **C-clause-{code}** | verbatim cost clause | per-sentence Noul over keyed sentence IDs; argmax in code | §3 cost_clause | only for codes present; keyed IDs, never `[i]`; a clause can span sentences |
| **C-other** (optional) | any other pair | Choice or Noul | §3 "other" | three-grader α 0.204 (pairwise κ 0.107–0.298); consider dropping and saying so |

**Handled in code, not Jev:** R5 filtering, abstentions, sentence
segmentation, keyed state, combining atomic judge Nouls, per-code
presence reconstruction, `jev-1.13.0` pinning, raw-probability archive.

### 6.2 Blank template, one file per slot

Proposed location: `recode/jev/questions/<slot>.yaml`, protected-token
tested.

```yaml
slot_id: <e.g. P1>
instrument_version: <semver; bump on every edit>
jev_model: jev-1.13.0
answer_type: <noul | choice>
option_keys: [<code-side IDs, each mapped to a manual token in code>]  # choice only
asked_when: <all | document_id matches openai_model_spec* | ...>
state_fields: [document_id, document_owner, document_type, section_heading,
               context_before, original_text, changed_text, context_after]
instructions: |
  <PETER WRITES>
criteria:
  <option_key>: <PETER WRITES>   # noul: true/false
examples: []          # synthetic anchors only, <=5, cite anchor numbers
governing_rules: [<§/R#/anchor#>]
combine: <name of code-side rule, if any>
author_log:
  - {version: , date: , change: , reason: , saw_results: false}
frozen: {commit: , sha256: , date: }
```

The request layout (built in code) is one request per edit for the
~16 main slots, plus follow-up requests for the per-sentence clause
Nouls, chunked per present code so each stays under the 32k window
(§3.1). `state` is a keyed JSON object with the fields above, and
`questions` is the map of slot_id to the compiled YAML. Never use
positional references.

### 6.3 Illustrative slot, structure only (not wording)

> *ILLUSTRATIVE, showing structure only. Every `<…>` is yours to write.*
> ```yaml
> slot_id: C-welf
> answer_type: choice
> option_keys: [none, developer→model_welfare, model_welfare→developer]
> asked_when: all
> instructions: |
>   <what counts as a welfare conflict; what state fields to compare>
> criteria:
>   none: <what passes as no conflict, naming the R1 exception explicitly>
>   developer→model_welfare: <concrete situation, per anchors 4/5>
>   model_welfare→developer: <concrete situation>
> examples: [anchor 4, anchor 5 (welfare clause only)]
> governing_rules: [§3 trigger, materiality bar, R1]
> ```
> The shape to copy: taxonomy keys as options, an explicit `none`, each
> option described as a *situation* rather than a degree, the relevant
> exception named, and ≤5 synthetic anchors.

### 6.4 Pilot plan and cost

1. **Before anything (S1):** blind sheets done and locked.
2. **Dev (S2, S3):**
   - Draw a seeded set of 100 applied edits, 10 per model, excluding the
     180 sheet edits and their chains.
   - Run all slots. Check mechanics: R5 filtering, keyed IDs, context
     fit, and the 72 long-context edits if any were drawn.
   - Compare with the ensemble in **aggregate only**.
   - Repeat 3 times for determinism, and swap option order on the Choice
     slots.
   - Stop after at most 3 revisions per slot, and pick J1 vs. J1a–d by
     the pre-declared criterion.
3. **Freeze and pre-register (S4).**
4. **Validate (S5):** run once on the 180 sheet edits and report κ
   against each coder, against adjudicated labels and against the
   ensemble.
5. **Full run** on 2,582 edits, only if validation meets the declared
   bar. Report it as an extra column plus the Jev-f secondary PPI (S7).

**Cost.** The total state is 15.0M chars across the corpus, about 3.7M
tokens (chars/4). With about 16 slots at roughly 500 tokens each:

| run | tokens | cost |
|---|---|---|
| **Full run**, state billed once per request | ≈25M | ≈$1 |
| **Full run**, only if questions are split across separate requests (state re-sent and re-billed each time) | ≈80M | ≈$3.40 |
| **Full run**, plus per-sentence clause Nouls | up to ≈250M | ≈$10 |
| **Dev pilot** (100 edits × 3 repeats + order swap) | <10M | <$0.50 |

Three points on these numbers:
- Batching is billed once. The vendor cookbook is explicit that N
  single-question calls pay for the state N times, while "the batched
  call pays once"
  ([parallel_questions](https://docs.typesafe.ai/cookbooks/parallel_questions.md),
  VENDOR). So the §6.2 layout (one request per edit) is the ≈25M row. The
  ≈80M row applies only if slots are split across requests.
- The worst case exceeds BRIEF §0.4's **~100M-token ASK threshold**.
  Measure the pilot's actual token counts first.
- Rate limits (1,200 requests per minute, which "can change without
  notice"; [models.md](https://docs.typesafe.ai/models.md), VENDOR) are
  not a constraint. The
  binding cost is your time: writing about 16 slots and up to 3
  revisions each, plus reading the pilot aggregates. Estimate one to
  two working days.
