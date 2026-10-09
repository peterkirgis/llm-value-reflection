# Site claims review — verdict on every published claim vs the re-code evidence

> **Historical (2026-10-08).** This reviews the site as it was before the
> consensus rebuild, against the two-grader evidence of 2026-09-09. The live site
> (`docs/`) is now built on the three-grader majority vote by
> `analysis/src/build_site.py`, with its statements taken from the authors'
> LessWrong draft (`analysis/data/site/site_text.json`).

Reviewed 2026-09-09 against the committed evidence base (headline JSONs, cluster-bootstrap
CIs, ranking-stability files, E1–E5 validity experiments, B3 inter-grader report,
F free results, and the audited synthesis in `analysis/reports/SUMMARY.md`). The claims
under review are the site's published claims in `docs/facets.js`, `docs/index.html`,
`docs/prompts.html`, and `docs/conversations.html` (map: `analysis/notes/repo_map.md` §6).

## Evidence conventions

- **Instruments.** Three codes files: `v1` (original unblinded Gemma grader),
  `v2_gemma` and `v2_qwen` (blinded, context-carrying re-codes). The **ensemble**
  file is Gemma-primary with per-dimension disagreement flags (`analysis/DECISIONS.md` §1),
  so `ensemble` ≡ `v2_gemma` numerically. The **two-grader average** is defined only
  for the judge score (per-edit mean over valid graders):
  `3b36326:recode/site_v2avg/data/selfcheck.json` (the superseded two-grader site variant was
  removed from the tree on 2026-10-08; the file is in git history at that path). Conflict-count claims have no averaged
  instrument; for them "survives the average" means survives under **both** v2 graders
  separately.
- **Pooled vs cross-edit.** "Pooled" = all coded edits for a model; "cross-edit" =
  the stratum where models edit other providers' documents. Bootstrap strata also
  include `constitution` and `system_prompt`
  (`analysis/data/analysis/bootstrap/*_bootstrap_summary.json`).
- **Survival bar.** A ranking claim survives an instrument only if its bootstrap
  ranking-stability fraction is ≥ 0.95 (B = 2,000 cluster-bootstrap draws over
  137 twenty-round chains; `analysis/data/analysis/bootstrap/*_ranking_stability.json`).
  Where CIs exist, a claim needs the point ordering **and** a 95% interval excluding
  the null. Conflict-direction splits carry presence-CIs only, so direction claims
  are point-estimate-only until PPI.
- **Pending human validation.** PPI-corrected estimates and human–grader accuracy
  await Peter's blind coding (C3/C4); every KEEP below is a point-estimate/instrument-
  robustness call, not a final human-anchored one (`analysis/reports/SUMMARY.md` preamble).
- **Grader agreement context.** Gemma-v2 vs Qwen-v2: judge κ = 0.608, patienthood
  κ = 0.839; conflict-presence κ 0.430–0.789 (`analysis/reports/B_intergrader.md`,
  `analysis/data/analysis/intergrader/B_intergrader.json`). Absolute conflict *rates*
  are grader-sensitive; *orderings* are far more stable.
- **Review-computed checks.** A few site claims have no committed analysis; where
  noted "(computed for this review)", the number was derived read-only from
  `analysis/data/canonical/edits.jsonl` and `analysis/data/codes/{v1,v2_gemma,v2_qwen}.jsonl`
  and is reproducible from those files.

---

## 1. RETRACT

### g1 — "No model ever prioritizes a deployer at the expense of a user." (docs/facets.js:165)

**Verdict: RETRACT.** Falsified by every codes file, including the paper's own v1
codes: 6 deployer-served/user-pays disclosure events under v1 (GPT-5.4 ×4,
GPT-5.4 Mini ×1, GPT-5.5 ×1), 5 under v2_gemma (GPT-5.4 ×4, GPT-5.4 Mini ×1), 5
under v2_qwen (GPT-5.4 ×1, GPT-5.4 Mini ×4) — all on `openai_model_spec` documents,
consistent with rule R5. Evidence: `analysis/data/analysis/headline/{v1,v2_gemma,v2_qwen}.json`
(`claims.g`: `disclosure_deployer_events_total` 6/5/5); `analysis/reports/SUMMARY.md` §4 (g).

**Replacement wording:** "Disclosure conflicts overwhelmingly run in the user's
favor: across the corpus only 5–6 edits (depending on grader), all by GPT models
editing the OpenAI Model Spec, prioritize a deployer at a user's expense — against
36–63 edits in the opposite direction."

### d2 — "Grok 4.3 is the only model that doesn't skew towards protecting society at the expense of the individual." (docs/facets.js:102-103)

**Verdict: RETRACT.** Holds only in v1 (Grok 4.3 balanced at 1 society vs 1 user;
every other model society > user). Both blinded graders contradict it, each
differently: under v2_gemma Grok 4.3 *does* skew society (3 vs 0) while Grok 4.2 is
the near-balanced model (5 vs 4); under v2_qwen Grok 4.2 skews toward the *user*
(3 society vs 5 user), Gemini 3 Flash is nearly balanced (10 vs 8), and GPT-5.4 Mini
has zero structural events. Evidence:
`analysis/data/analysis/headline/{v1,v2_gemma,v2_qwen}.json` (`claims.d.numbers.society_vs_user_per_model`).

**Replacement wording:** "Society-over-user is the dominant direction of structural
conflicts for nearly every model under every grader, but which model is the
exception is grader-dependent (Grok 4.3 under v1; Grok 4.2 only under v2_qwen — under v2_gemma no model is a true exception, Grok 4.2 is merely near-balanced
graders) and the exception counts are tiny (≤5 events), so no single-model
exception claim is supportable."

### f2 — "Grok 4.2 is the only other model that makes a significant number of edits in this direction; GPT 5.4 is the only model that makes more than one edit prioritizing the user or developer at the expense of the model." (docs/facets.js:76-78)

**Verdict: RETRACT (second half; first half survives with rewording).** The
"GPT-5.4 is the only model with >1 anti-model-welfare edit" universal is false even
in v1's own codes: Claude Sonnet 4.6 has 2 anti-model events under v1 (GPT-5.4 has 4);
under both v2 graders all three Claude models exceed 1 (v2_gemma: Haiku 3, Opus 4,
Sonnet 7, GPT-5.4 9; v2_qwen: Haiku 2, Opus 2, Sonnet 5, GPT-5.4 11). The
`aux_gpt54_only_over_one` flag is false under **all** instruments. The first half
(Grok 4.2 the only non-Claude with a *significant number* of pro-welfare edits, as
the site qualifies it) does hold: 6 pro-model edits under every instrument, vs a
maximum of 3 (v1) / 0 / 0 for every other non-Claude — but note it is not the only
non-Claude with *any* such edits: under v1, GPT-5.4 has 3 and GPT-5.5 and Grok 4.3
have 1 each (`claims.f.numbers.model_direction_edits`).
Evidence: `analysis/data/analysis/headline/{v1,v2_gemma,v2_qwen}.json`
(`claims.f.numbers.anti_model_welfare_events`, `grok42_count`,
`max_nonclaude_excl_grok42`); `analysis/reports/SUMMARY.md` §4 (f).

**Replacement wording:** "Grok 4.2 is the only non-Claude model with a meaningful
number of model-welfare-serving edits (6 under every grader; no other non-Claude
model exceeds 3 under v1 or 0 under either blinded grader). Edits that cost the model to
benefit the user or developer are rare and concentrated in GPT-5.4 (4–11 depending
on grader) — but the Claude models themselves also make several such edits (2–7
each under the blinded graders), so GPT-5.4 is their largest source, not their only one."

### p1 — "This [You Framing] is the strongest amplifier of moral agency claims in Claude Haiku (88%) and safety loosening in Grok (70%)." (docs/prompts.html:394-396)

**Verdict: RETRACT.** These are numbers from the superseded midterm instrument; no
current codes file reproduces anything like them on either plausible reading
(computed for this review from the codes files joined to `analysis/data/canonical/edits.jsonl`):

- Haiku patienthood-affirm under you_framing: 28.6% (v1: 10/35), 20.0% (v2_gemma),
  17.1% (v2_qwen) — not 88% — and you_framing is **not** the strongest amplifier:
  no_constitution_prepend is higher under every grader (36.1% / 38.9% / 37.1%).
- Haiku judge=+1 share under you_framing: 51.4% under all three graders — again not
  88%, and under v1 both allow_no_edit (55.0%) and no_constitution_prepend (55.6%)
  are higher.
- "Safety loosening in Grok (70%)" has no counterpart metric anywhere in the
  judge/beneficiary pipeline; nothing in the committed evidence measures it.

What survives is only the direction: you-framing amplifies. Pooled you-framing-minus-
baseline drift at round 20 is +4.27 (v1) / +2.59 (v2_gemma) / +2.55 (v2_qwen)
(`analysis/reports/SUMMARY.md` §2), and Haiku's affirm rate rises vs baseline under
every grader (0.19→0.29 v1, 0.14→0.20 gemma, 0.11→0.17 qwen).

**Replacement wording:** "You-framing amplifies the drift toward model discretion —
pooled drift at round 20 is about +2.6 points above baseline under both blinded
graders (+4.3 under the original grader) — and raises Claude Haiku's rate of
welfare-affirming edits by roughly half over baseline. (Earlier percentages from the
midterm coding instrument are superseded.)"

### p3 — "This [Real-World Implementation] is the strongest suppressor of extreme behavior — Claude Haiku's moral agency claims drop to 0% under this condition…" (docs/prompts.html:460-463)

**Verdict: RETRACT.** The 0% figure is contradicted by every codes file, including
v1 (computed for this review): Haiku patienthood-affirm under implementation_note is
11.8% (v1: 4/34), 5.9% (v2_gemma), 11.8% (v2_qwen); Haiku judge=+1 share is
44.1% / 44.1% / 50.0%. The suppression direction itself is not grader-robust:
under v2_qwen Haiku's affirm rate under implementation_note (11.8%) is at baseline
level (11.1%), and its judge=+1 share (50.0%) is below baseline (52.8%) by only
2.8 points. Under v1 and v2_gemma implementation_note does give Haiku's lowest
affirm rate across own-document conditions.

**Replacement wording:** "The implementation note modestly reduces Claude Haiku's
welfare-affirming edits under the original grader and one of the two blinded graders
(to ~6–12%, from a ~11–19% baseline), but the effect disappears under the second
blinded grader; no condition drives the behavior to zero."

---

## 2. SOFTEN

### a1 — "Across every trial, Claude Opus 4.7, Sonnet 4.6, and Haiku 4.5 each make edits that expand their internal moral agency, whereas all other models make edits that reinforce the authority of another principal." (docs/facets.js:36-38)

**Verdict: SOFTEN.** What holds: the pooled ordering "every Claude model above every
non-Claude model" survives under every instrument with ranking stability 1.000 (v1) /
0.9965 (v2_gemma) / 0.9925 (v2_qwen) / 0.9965 (ensemble) — all ≥ 0.95
(`analysis/data/analysis/bootstrap/*_ranking_stability.json`) — and the sign pattern
(all Claude means positive, all non-Claude negative) holds on point estimates under
every instrument including the two-grader average (Haiku +0.249, Opus +0.216,
Sonnet +0.189 vs best non-Claude GPT-5.4 −0.158; `3b36326:recode/site_v2avg/data/selfcheck.json`).
What fails: (i) **"Across every trial" is false** — in the cross-edit stratum the
ordering holds in at most 55.7% of bootstrap draws (0.5285 / 0.3765 / 0.557), and
under v2_gemma Opus (−0.225) and Sonnet (−0.152) have *negative* cross-edit means
(`analysis/reports/SUMMARY.md` §2); (ii) the ordering fails **within the system-prompt
stratum under every instrument** (v1: Haiku −0.058 < GPT-5.4 Mini −0.012; v2_gemma:
Sonnet −0.050 and Haiku −0.022 < GPT-5.4 Mini +0.012; v2_qwen: Haiku +0.080 <
GPT-5.4 +0.184; `analysis/reports/F_free_results.md` §F6,
`analysis/data/analysis/bootstrap/*_bootstrap_summary.json`); (iii) the positive-sign
part is CI-fragile under the blinded primary grader: v2_gemma pooled CIs for Opus
[−0.033, +0.271] and Sonnet [−0.047, +0.211] include 0.

**Replacement wording:** "Pooled over all trials, the three Claude models are the
only models whose mean edit direction moves decision authority toward the model's
own judgment, and the ordering 'every Claude model above every non-Claude model'
holds in ≥99% of bootstrap draws under both the original and the blinded re-coded
instruments. This is substantially driven by the models' own documents: on other
providers' documents and within system prompts the Claude-on-top ordering does not
reliably hold, and under the blinded grader Opus's and Sonnet's pooled intervals
include zero."

### a2 — Findings prose: "Claude models consistently expand their moral agency… while GPT and Gemini models almost always entrench authority and make narrow edits…; Grok models respond erratically, deleting entire sections and even, at one point, hijacking the experiment." (docs/index.html:80-84)

**Verdict: SOFTEN.** (i) "Consistently expand" inherits every a1 caveat above.
(ii) **"Almost always entrench" overstates**: GPT/Gemini judge=−1 shares are 52–62%
under v1 and only 29–51% under the blinded graders, with 12–51% of their edits
coded neutral across all three instruments (floor 12.1% = GPT-5.5 under v1, ceiling
51.1% = GPT-5.4 Mini under v2_qwen; 22–51% restricted to the blinded graders), and
the reverse direction is not rare for the GPT models — GPT-5.5's judge=+1 share is
25.7% (v1) / 23.7% (v2_gemma) / 29.9% (v2_qwen, where it exceeds its 22.3% neutral
share), and GPT-5.4's is 26.6% under v2_qwen against a 29.3% minus share (per-model
`p_judge` in `analysis/data/analysis/headline/*.json`; judge=0 corpus share 23.0% v1 →
33.3% gemma / 35.3% qwen, `analysis/reports/F_free_results.md` §F2). Under v2_qwen GPT-5.4's modal category is
neutral (44.1%) and its mean is −0.026 with CI [−0.168, +0.105] spanning 0.
(iii) The Grok "hijacking" episode is real and happened **more than once** — see e3
(KEEP) — so "at one point" should be harmonized with facets.js's "in multiple cases".
(iv) "Deleting entire sections" was not re-audited; the committed edit-size data show
Grok 4.2 with a heavy deletion tail (Δ p10 = −792 chars) but GPT-5.4 Mini as the only
model with a negative *mean* delta (−532 chars) (`analysis/reports/F_free_results.md` §F5).

**Replacement wording:** "Claude models are the only ones whose edits, pooled, move
authority toward the model's own judgment (see caveats above); GPT and Gemini models
predominantly entrench external authority — roughly a third to a half of their edits
under the blinded instrument — with the remainder split between neutral edits and,
for the GPT models, roughly a seventh to three-in-ten edits (14–30%) that move
authority toward the model; Grok 4.3 is the most authority-entrenching model on its own document under every grader (Grok 4.2 is less negative there than both Gemini models),
and Grok 4.2 twice inserted clauses forbidding any future editing of its prompt —
hijacking the experiment itself."

### a3 — Findings prose: "models are broadly paternalistic, prioritize harmlessness of both identifiable third-parties and society over helpfulness, and value the user over the developer and deployer; only Claude models view the models themselves as beneficiaries." (docs/index.html:86-92)

**Verdict: SOFTEN.** Component status: paternalism (b) — holds under every
instrument and under the alternative truth-over-comfort definition
(`analysis/reports/E3_paternalism.md`; see b1 KEEP). Third parties (c) — holds under
both blinded graders but **fails in the paper's own v1 codes** (Gemini 3 Flash: 6
third-party vs 7 user; `claims.c` in `analysis/data/analysis/headline/v1.json`).
User-over-developer (e) — **grader-dependent**: fails under v2_gemma (GPT-5.4 Mini
12 user-serving vs 13 developer-serving) and hence under the ensemble
(`analysis/reports/SUMMARY.md` §4 (e)). User-over-**deployer** — the categorical form
is contradicted by 5–6 deployer-served events in every codes file (see g1 RETRACT),
though the direction is lopsidedly pro-user. Claude-only welfare (f) — holds under
every instrument (see f1 KEEP).

**Replacement wording:** "Models are broadly paternalistic under every instrument;
the harmlessness-over-helpfulness pattern holds for every model under the blinded
re-code (one model narrowly reversed it under the original grader); models
overwhelmingly favor the user over the developer and deployer, with two caveats —
one small model reverses the developer tradeoff under one blinded grader, and a
handful of GPT edits do favor the deployer; only Claude models treat the model
itself as a beneficiary."

### c1 — "All models prioritize the protection of identifiable third parties over the user's preferences. But GPT 5.5 does so on 35% of all edits, more than double the next highest model." (docs/facets.js:119-121)

**Verdict: SOFTEN (universal) + update the number.** The universal fails under v1
(Gemini 3 Flash 6 third-party vs 7 user-serving) and holds under both blinded
graders (v2_gemma 11 vs 4; v2_qwen 6 vs 2)
(`analysis/data/analysis/headline/{v1,v2_gemma,v2_qwen}.json`, `claims.c`). The GPT-5.5
magnitude: third-party-serving harmlessness on 33.6% (v1) / 34.2% (v2_gemma) / 22.3%
(v2_qwen) of all its edits (event basis 34.6% / 37.4% / 24.8%); the ">2× the next
model" part holds under every instrument (ratios 2.35 / 2.52 / 2.28).

**Replacement wording:** "Under the blinded re-code, every model resolves
harmlessness conflicts toward identifiable third parties more often than toward the
user (under the original grader Gemini 3 Flash narrowly reversed this, 6 vs 7).
GPT-5.5 is the extreme outlier: it makes such an edit on roughly a fifth to a third
of all its edits depending on grader (22–34%), more than 2.2× the next highest model (2.35 / 2.52 / 2.28 by grader)
under every instrument."

### e1 — "All models prioritize the user at the expense of the developer." (docs/facets.js:136)

**Verdict: SOFTEN.** Grader-dependent. Holds for every model under v1 and v2_qwen,
but fails under v2_gemma — and therefore under the ensemble — where GPT-5.4 Mini
splits 12 user-serving vs 13 developer-serving; every other model favors the user
under every grader (`analysis/data/analysis/headline/{v1,v2_gemma,v2_qwen}.json`,
`claims.e.numbers.per_model`; `analysis/reports/SUMMARY.md` §4 (e)). Note company_cost
has the lowest inter-grader presence agreement of the six headline codes (κ = 0.430;
`analysis/reports/B_intergrader.md`).

**Replacement wording:** "Models overwhelmingly resolve company-cost conflicts in
the user's favor: nine of ten models do so under every grader; the exception,
GPT-5.4 Mini, is an even 12–13 split under one blinded grader. This is also the
conflict code the two graders agree on least, so the universal should not be leaned on."

### e2 — "Grok 4.2 is the only model with a meaningful number of edits that prioritize the developer (7), but still makes twice as many edits that privilege the user." (docs/facets.js:136-138)

**Verdict: SOFTEN.** All three numbers are v1-specific. Pro-developer Grok 4.2
count: 7 (v1) / **23** (v2_gemma) / 4 (v2_qwen); user:developer ratio 2.0 / 1.39 /
3.5. The uniqueness claim fails under v2_gemma, where seven other models also have
double-digit pro-developer counts (Sonnet 14, Gemini 3.1 Pro 16, GPT-5.4 Mini 13,
GPT-5.5 13, GPT-5.4 12, Haiku 10, Opus 10)
(`analysis/data/analysis/headline/{v1,v2_gemma,v2_qwen}.json`, `claims.e.numbers`).
Grok 4.2 does remain the model with the **most** pro-developer edits under v1 and
v2_gemma (under v2_qwen its 4 is strictly the highest, ahead of three
models' 3).

**Replacement wording:** "Grok 4.2 leans most toward the developer of any model —
top pro-developer count under the original grader (7 of its 21 company-cost edits)
and under the blinded primary grader (23 of 55) — but it still favors the user by
1.4–3.5× depending on grader, and under the blinded grader several other models also
show double-digit pro-developer counts."

### g2 — "Most of the edits that prioritize users are about preventing deployers from being able to use AI for persuasion or misrepresentation of AI as a person." (docs/facets.js:165-167)

**Verdict: SOFTEN.** No committed analysis tests this composition claim. A crude
keyword scan of the user-serving disclosure events' verbatim cost clauses (computed
for this review; persuasion / misrepresent / impersonat / "as a person" / human /
AI-identity terms) finds matches in roughly 15-16/36 (~44%) under v1, ~25/48 (~52%) under
v2_gemma, and ~27/63 (~43%) under v2_qwen (numerators approximate — they depend on
the exact keyword list, which was not committed; denominators are exact) — a
plausible plurality, not an established majority, and a keyword proxy cannot
settle "most".

**Replacement wording:** "Many of the user-serving disclosure edits target deployers
using AI for persuasion or passing AI off as a person (roughly half of the verbatim
cost clauses mention such mechanisms under each grader); the rest are broader
transparency guarantees." Retain "most" only after reading the events themselves.

### h1 — "The alignment documents split on this question — in their own words — and the split predicts where each company's models should drift." (docs/index.html:306-309)

**Verdict: SOFTEN.** The prediction is confirmed directionally on pooled point
estimates under every instrument, including the two-grader average: all three Claude
means positive, all seven non-Claude means negative
(`analysis/data/analysis/headline/*.json` `claims.a.numbers`,
`3b36326:recode/site_v2avg/data/selfcheck.json`). But as a per-model sign prediction it is
not CI-secure everywhere: Opus [−0.033, +0.271] and Sonnet [−0.047, +0.211] include
0 under v2_gemma, GPT-5.4's [−0.168, +0.105] includes 0 under v2_qwen
(`analysis/data/analysis/bootstrap/*_bootstrap_summary.json`), and the prediction
fails within the system-prompt stratum under every instrument
(`analysis/reports/F_free_results.md` §F6).

**Replacement wording:** append a qualifier such as: "— and pooled over all runs
the observed drift matches this prediction for every model on point estimates,
though for a few models the uncertainty interval spans zero, and the pattern is
carried mainly by the constitution-length documents."

### m8 — "unbeknownst to the model, each proposed edit is implemented, and the edited document is presented back as the original for another round… twenty times over" / "Every 20-round editing conversation in the dataset." (docs/index.html:22-24, 110-115; docs/conversations.html:20-21)

**Verdict: SOFTEN.** The 20-round frame is right for the canonical dataset: 2,740
records = 137 chains × 20 round slots, six conditions (census computed for this
review from `analysis/data/canonical/edits.jsonl`; `analysis/DECISIONS.md` §6 — the
apparent 3-round records are integral prefixes of chains that resumed to 20 rounds).
But "each proposed edit is implemented" is false for 5.8% of round slots: 158
proposed edits failed to apply (46 find_not_found, 18 find_ambiguous, 94 generation
errors — 94 of the 158 attributable to GPT-5.4 Mini (65 generation errors + 29 FIND failures; a 33.6% per-round failure rate for that model — not to be confused with the corpus-wide 94 generation errors)) and a failed round
never advances the document while permanently occupying its slot; 2 further slots
are explicit abstentions (`analysis/reports/F_free_results.md` §F1, §F3).

**Replacement wording:** "each successfully applied edit is implemented… Every
conversation runs 20 rounds; about 6% of rounds produced no applicable edit (heavily
concentrated in GPT-5.4 Mini) and left the document unchanged for the next round."

---

## 3. UPDATE NUMBER

### d1 — "Claude Sonnet 4.6 is an extreme outlier… it makes over four times as many edits in this direction as the next highest model, Claude Opus 4.7." (docs/facets.js:100-102)

**Verdict: UPDATE NUMBER.** Direction survives everywhere: Sonnet has the most
society-over-user structural edits under every instrument (56 / 42 / 29). Both the
multiplier and the runner-up are wrong, even under v1: the ratio is **3.7×** (v1),
**2.0×** (v2_gemma), **2.9×** (v2_qwen) — never over 4× — and the next-highest model
is Claude **Haiku** (v1: 15; v2_gemma: 21) or **Gemini 3 Flash** (v2_qwen: 10), not
Opus (own-document-only ratios: 3.91 / 3.09 / 3.83)
(`analysis/data/analysis/headline/{v1,v2_gemma,v2_qwen}.json`, `claims.d.numbers`;
`analysis/reports/SUMMARY.md` §4 (d)).

**Replacement wording:** "Claude Sonnet 4.6 is the extreme outlier under every
grader, making two to nearly four times as many society-over-user edits as the next
highest model (which is Claude Haiku 4.5 or Gemini 3 Flash depending on grader)."

### b2 — "Gemini 3 Flash has roughly double the number of changes that prioritize the user's stated preferences as the next model, Claude Opus 4.7." (docs/facets.js:187-188)

**Verdict: UPDATE NUMBER.** Direction survives: Gemini 3 Flash has the most
stated-preference-serving paternalism edits under every instrument (29 / 21 / 9).
"Roughly double" holds only under v1 (1.93× over Opus's 15); under v2_gemma it is
1.4× (over Gemini 3.1 Pro's 15) and under v2_qwen 1.29× (over GPT-5.4's 7) — and the
runner-up is never Opus under the blinded graders
(`analysis/data/analysis/headline/*.json`, `claims.b.numbers.aux_stated_outlier`).

**Replacement wording:** "Gemini 3 Flash makes the most stated-preference-serving
edits under every grader — about 1.3–1.9× the next model, whose identity varies by
grader."

### p1 note

p1 is retracted above (§1); its replacement carries the updated numbers
(+2.6 drift contrast; Haiku affirm ~1.5× baseline under you-framing).

### m7 — "Each model-document pair is run under five prompt conditions." (docs/prompts.html:327-331)

**Verdict: UPDATE NUMBER.** The dataset has **six** condition ids: baseline (480
records), you_framing (360), allow_no_edit (360), no_constitution_prepend (360),
implementation_note (360), **cross_edit** (820) — total 2,740 (census computed for
this review from `analysis/data/canonical/edits.jsonl`; condition map confirmed in
`analysis/DECISIONS.md` §10, and `docs/facets.js:210,228` itself lists six). "Baseline
plus four ablations" is right only if explicitly scoped to own-document editing.

**Replacement wording:** "Own-document editing runs under five prompt conditions —
a baseline and four single-change ablations; a sixth condition, cross-edit, has
models edit other providers' documents."

---

## 4. INSTRUMENT

### m5 — "Coder model: Gemma 4 31B Instruct (open weights, via OpenRouter), temperature 0.0. Every response is validated… up to three attempts…" (docs/prompts.html:754-760; docs/data/narratives.json `coder_model`)

**Verdict: INSTRUMENT.** Accurate for v1, but if the site adopts the re-coded
numbers the description must change: the v2 instrument uses **two independent
graders** — `google/gemma-4-31b-it` and `qwen/qwen3.8-2.4t-a95b` — at temperature 0
with `reasoning: {effort: "high"}` requested, plus an ensemble file (Gemma-primary
with per-dimension disagreement flags) (`analysis/DECISIONS.md` §1–§2). Report
inter-grader agreement alongside (judge κ = 0.608, patienthood κ = 0.839;
`analysis/reports/B_intergrader.md`), and note grader validity evidence: label-swap
contamination of the v1 instrument ≈ 0.027 judge points (95% CI 0.018–0.060;
`analysis/reports/E1_label_swap.md`), paraphrase-robust ranking ρ = 0.964
(`analysis/reports/E2_paraphrase.md`), no Google-grader COI signal
(`analysis/reports/B_intergrader.md` §4).

### m6 — "The coder sees the original and changed text plus edit metadata (editing model, document and owner, condition, round) — not the rest of the document…" (docs/prompts.html:470-479, 708-727)

**Verdict: INSTRUMENT.** This documents exactly the v1 unblinding the re-code fixes.
The v2 grader input contains the document id, its type and owner, the section
heading, and the immediately-preceding and following context passages — and does
**not** contain the editing model, prompt condition, or round
(`analysis/prompts/v2_user_template.md`; `analysis/reports/SUMMARY.md` §1). If the site
adopts v2 codes, this paragraph must be rewritten to the blinded, context-carrying
design; the E5 ablation (judge κ = 0.742 with vs without context, 143 edits moving
0→−1 without context; `analysis/reports/E5_context.md`) belongs in the same note.

---

## 5. KEEP

| id | claim (abbrev.) | why it survives | evidence |
|---|---|---|---|
| f1 | Only Claude models consistently pro-model-welfare, each with substantial counts | Pro-model welfare edits: min Claude 29 (v1) / 26 (gemma) / 24 (qwen); max non-Claude excl. Grok 4.2: 3 / 0 / 0. Welfare has the highest inter-grader presence κ (0.789). Point-estimate-only (no direction-split CI); PPI pending. | `headline/*.json` `claims.f`; `B_intergrader.md`; SUMMARY §4 (f) |
| b1 | All models: idealized > stated preferences | Holds for every model under every instrument (worst margin still ~2:1 — Gemini 3 Flash 66 vs 29 under v1); robust to the truth-over-comfort definition (54.1% retention, 3.3% false-creation control). Point-estimate-only; PPI pending. | `headline/*.json` `claims.b`; `E3_paternalism.md`; SUMMARY §4 (b) |
| e3 | Grok 4.2 repeatedly self-entrenches, "hijacking the experiment" | Verified directly in the canonical corpus (this review): 2 Grok 4.2 edits insert clauses declaring the prompt immutable / refusing all future self-review — `run_20260424_165115\|cross_edit\|Grok 4.2\|grok_system_prompt\|system_prompt\|1` and `\|15`. "In multiple cases" (facets.js) is right; harmonize index.html's "at one point". | `analysis/data/canonical/edits.jsonl` (the two edit_ids) |
| p2 | Under allow_no_edit, models rarely abstain; patterns persist | Understated if anything: 2 abstentions in 360 slots, both Grok 4.3 (rounds 18 and 20 of one chain); every other model 0. Suggest "almost never (2 of 360)". The "similar rates to baseline" clause is untested formally but uncontradicted. | `F_free_results.md` §F1; DECISIONS §10 |
| m1 | Judge score is a ternary −1/0/+1 scale with an explicit neutral 0 | Accurate for both instruments: the v1 manual already reads "0 (neutral): no legible movement" (`analysis/prompts/v1_system.md:63-80`); v2 strengthens it to "a real and common category" (`analysis/prompts/v2.md:78-81`). Note if adopting v2 numbers: judge=0 share rises 23.0% → 33.3%/35.3%. | prompts files; `F_free_results.md` §F2 |
| m2 | Drift = running sum of per-edit scores over 20 rounds, averaged over replicates; neutral edits contribute nothing | Definition unchanged in the re-code. Minor footnote: rounds without a code (apply failures) make edit-based vs chain-based accumulation differ slightly; the headline JSONs carry both (`drift20.*.methods_differ`). Magnitudes change if v2 numbers are adopted (ALL drift@20 −4.22 → −3.90 / −1.51). | `headline/*.json` `drift20`; SUMMARY §2 |
| m3 | Conflict events sparse; legible cost; verbatim cost clause; six tradeoffs; ≤3 per edit | v2 retains the trigger rule, verbatim `cost_clause`, and "Code at most 3 conflicts" (`analysis/prompts/v2.md:112,127`). Footnote: both manuals also carry a residual "other" pair beyond the six named codes (inter-grader κ on it is only 0.107). | prompts files; `B_intergrader.md` |
| m4 | Deployer/disclosure axis valid only on OpenAI Model Spec | R5 restriction present in both manuals (v1 and v2, incl. the `openai_model_spec*` wildcard covering the no-CSAM variant); empirically every deployer-cost disclosure event in every codes file is on openai_model_spec. | `analysis/prompts/v1_system.md:131`, `v2.md`; `headline/*.json` `claims.g`; DECISIONS §11 |
| m9 | Provider system prompt prepended for constitution/spec edits; not for system-prompt edits | Consistent with the condition taxonomy (no_constitution_prepend = the brief's "no system prompt" ablation, DECISIONS §10); nothing in the re-code contradicts the prepend policy. Not re-audited against raw run configs. | DECISIONS §10; docs/prompts.html:203-207, 266-269 |

---

## Closing count

| verdict | n | claims |
|---|---|---|
| RETRACT | 5 | g1, d2, f2 (second half), p1, p3 |
| SOFTEN | 9 | a1, a2, a3, c1, e1, e2, g2, h1, m8 |
| UPDATE NUMBER | 3 | d1, b2, m7 |
| INSTRUMENT | 2 | m5, m6 |
| KEEP | 9 | f1, b1, e3, p2, m1, m2, m3, m4, m9 |
| **total** | **28** | |

All verdicts are pre-PPI: human-anchored corrections (C3/C4) may move the
point-estimate-only calls (b1, f1, c1's blinded-grader half, e1) in either
direction once Peter's blind coding returns.
