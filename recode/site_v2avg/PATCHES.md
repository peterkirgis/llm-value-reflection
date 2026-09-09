# PATCHES.md — recode/site_v2avg/

Variant: **v2 blinded re-code — Gemma 4 + Qwen 3.8 average (recode pipeline)**

Built by `recode/src/build_site_v2avg.py` (rerunnable; every patch is an
exact-match splice against a fresh copy of docs/, asserted unique — the build
fails loudly if docs/ drifts). docs/ itself is never modified.

## Data files (regenerated, not copied)

- `data/site.json.gz` — rebuilt from the 10 run files (via the imported
  `build_static_site.summarize_run`/`load_jsonl_records` plus a vendored copy of
  `changed_records` with only the coding join changed). Each record carries BOTH
  v2 graders' codings under `coding.graders` plus precomputed averages
  (`judge_avg`, `n_graders_valid`, `single_grader`, per-dimension `*_agree`
  flags, `conflict_weights` with 0.5/1.0 weights, `patienthood_pair`) and a
  `v2_coding_status` marker. Records with no valid v2 coding from either grader
  are passed through with `coding: null` and an explicit uncoded status
  (this build: {"avg_two_graders": 2528, "uncoded_generation_error": 191, "single_grader": 54, "uncoded_exploratory_run": 176}).
  The uncompressed site.json is intentionally not written (the frontend only
  fetches the .gz).
- `data/narratives.json` — regenerated (build_narratives.py is fully
  deterministic local aggregation with zero LLM calls, so regeneration — not
  reuse of the v1-derived published file — is correct). Per-grader facet
  semantics are imported unchanged from `build_narratives.py`
  (`facet_memberships`, `facet_net_scores`, `conflict_direction`); the
  aggregation applies grader-level equal weighting: `dirs` counts weight each
  edit by (#valid graders assigning)/(#valid graders), `total` counts edits
  coded by >= 1 v2 grader (2,582 — v2 codes the 2 abstentions that v1 skipped),
  and `cum`/`cumsq` accumulate grader-averaged (fractional) net scores, which
  also fixes the original builder's exact-equality drop of fractional judge
  scores. Stories carry both graders' codes plus agreement flags; the curated
  ride-on is dropped because the highlight links that consumed it are disabled
  (v1-tied). Example texts come from `recode/data/canonical/edits.jsonl`
  (find_text / replace_text_sanitized — the same sanitized text the graders saw).
  For the **System prompts** view the bundle additionally carries (a) a separate
  top-level `sp_stats` table — `{facet: {model_display: cell}}`, the same cell
  shape AND the same model keys as the per-condition `stats` cells (so the stock
  per-model renderers and the model-visibility chips work unchanged), restricted
  to `document_type == "system_prompt"` and pooled over ALL conditions and the
  four system-prompt documents; a replicate is one (run, condition, model) chain
  on a system-prompt document — i.e. each model's (run, condition, document)
  chains. It is kept OUTSIDE `stats` because the frontend's All-conditions
  pooling iterates every `stats[facet]` key and would double-count an in-table
  pseudo-condition — and (b) a new `doc_type` field on every story example (from
  the canonical edit's `document_type`; all existing fields unchanged) so the
  example browser can filter the stratum client-side.
- `data/selfcheck.json` — ground-truth per-model mean judge under the average,
  computed directly from the two codes files; the build asserts the
  narratives-bundle numbers match it exactly. Also carries
  `system_prompt_stratum` — the System-prompts view's ground truth: the
  per-model mean judge table (with Ns, same averaging rules, model/doc fields
  parsed from the edit ids) is asserted against `sp_stats` per-model judge
  cells (means and denominators must match exactly, same model set); a
  per-document table is kept for REFERENCE ONLY (the frontend renders the view
  per model), and its document set must be exactly the four provider system
  prompts.

## Files copied from docs/ and patched

### index.html

- Title labeled as the v2 re-code variant.
- Variant banner (label + one-line methods note + B_intergrader.md pointer) at the top of the page; defines the .v1-flag style.
- Byline notes the re-analysis so the page is not mistaken for the published v1 site.
- Findings paragraph 1 flagged as v1 narrative text (its claims are not v2-average figures).
- Findings paragraph 2 flagged as v1 narrative text.
- Results Explorer heading labeled: all its figures are the v2 average.

### conversations.html

- Title labeled as the v2 re-code variant.
- Variant banner at the top of the page.

### prompts.html

- Title labeled as the v2 re-code variant.
- Variant banner at the top of the page.
- Coding-tab description rewritten: v2 pipeline is blinded + contextual with two graders (the v1 text described the unblinded metadata).
- System prompt replaced with the exact v2 blinded prompt (recode/prompts/v2_system.md): contextual input, synthetic anchors, explicit judge-0 instruction, R6.
- User template replaced with the v2 blinded template (recode/prompts/v2_user_template.md): no editing-model / condition / round metadata; context fields added.
- Coder note names both v2 graders and the averaging rule instead of the single v1 Gemma coder.

### styles.css

- Copied verbatim (no patches).

### app.js

- renderRecord coding block rewritten: shows Gemma and Qwen codes side by side with a visible disagreement / single-grader marker and the per-edit judge average; uncoded records get an explicit graceful note.

### facets.js

- Number formatter for grader-averaged (fractional) counts.
- Every takeaway (hardcoded v1 numbers/claims) is flagged as v1 text so it is not read as a v2 figure.
- Highlight links disabled: their curated ids and quoted tips are tied to v1 codes and would silently jump to the wrong example under the regenerated v2 stories.
- Example code chips rewritten: both graders side by side with a disagreement marker.
- Example evidence/cost-clause blocks rewritten: per-grader evidence and grader-tagged cost clauses.
- How-to note documents the averaging semantics and the denominator.
- Drift note documents grader-averaged (fractional) net scores and the System-prompts view's per-model lines over system-prompt chains.
- Fractional (averaged) counts rendered to one decimal.
- Fractional (averaged) judge counts rendered to one decimal; the mean shown equals the mean of per-edit judge averages.
- Fractional (averaged) conflict counts rendered to one decimal.
- New "System prompts" option appended to the condition-chip list immediately after Cross Edit.
- Chip label for the new view: "System prompts".
- Tooltip/subtitle for the new chip states the fixed semantics: all conditions; system-prompt documents only; rendered per editing model.
- aggStat reads the System-prompts view from the separate sp_stats table (keyed by model_display, the same cell shape as the per-condition cells), leaving real-condition pooling untouched.
- Example browser: the System-prompts view filters stories by the new doc_type field (all conditions) instead of by condition_id.

### reveal.js

- Copied verbatim (no patches).

## Known intentional leftovers

- The System-prompts view deliberately carries NO patches for the drift chart,
  freq bars, row labels, aggregate-view heading, or model-visibility chips:
  `sp_stats` is keyed by model_display with the standard cell shape, so the
  stock per-model renderers — and fully active model chips — apply verbatim in
  that view. The earlier per-document rendering patches and the chip-greying
  patch were removed in the per-model rework.
- The hero carousel's six exemplar quotes and one-word verdicts on index.html are
  editorial exhibits of specific edits (not data-driven aggregates); they are kept,
  under the page-top variant banner and the v1-narrative flags.
- `app.js`'s canvas drift pipeline, filter chips, and the `#coding-summary` div are
  dead code on the shipped pages (their target elements are absent or hidden);
  they are left untouched and render nothing.
- `styles.css` and `reveal.js` are byte-identical copies.
