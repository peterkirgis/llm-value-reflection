# PATCHES.md — recode/site_v3pool/

Variant: **v2 blinded re-code — Gemma 4 + Qwen 3.8 + Muse Spark 1.3 pooled average (recode pipeline)**

Built by `recode/src/build_site_v3pool.py` (a thin entry point for the shared
variant builder `recode/src/build_site_v2avg.py --variant v3pool`; rerunnable;
every patch is an exact-match splice against a fresh copy of docs/, asserted
unique — the build fails loudly if docs/ drifts). docs/ itself is never modified.
The v2avg variant (recode/site_v2avg/) is built by the same code and is unchanged.

## Data files (regenerated, not copied)

- `data/site.json.gz` — rebuilt from the 10 run files (via the imported
  `build_static_site.summarize_run`/`load_jsonl_records` plus a vendored copy of
  `changed_records` with only the coding join changed). Each record's `coding`
  (schema `v3pool`) carries EVERY grader's v2 coding under `coding.graders`
  (gemma / qwen / muse; null = no valid code) plus pooled per-edit fields:
  `judge_avg` (mean of the valid graders' scores), `n_graders` / `n_graders_valid`
  / `graders_valid`, `single_grader`, categorical weights as fractions
  (`patienthood_weights`, `conflict_weights` = presence, `conflict_direction_weights`;
  each = #valid graders assigning / #valid), `patienthood_by_grader`, and
  `consensus.{judge,patienthood,conflicts}` = {status, label, n_valid, majority,
  dissenter, dissenter_label, valid_agree, votes:[{value, n, graders}]} with
  status unanimous / one_dissent (2–1, dissenter named) / all_differ (3-way) /
  fewer_valid (< 3 valid graders). The conflicts dimension compares the SET of
  conflict codes present. Records with no valid coding from any grader are
  passed through with `coding: null` and an explicit uncoded status
  (this build: {"pooled_all_graders": 2528, "uncoded_generation_error": 191, "pooled_2_of_3_graders": 54, "uncoded_exploratory_run": 176}).
  The top-level `graders` list names the three graders. The uncompressed
  site.json is intentionally not written (the frontend only fetches the .gz).
- `data/narratives.json` — regenerated (build_narratives.py is fully
  deterministic local aggregation with zero LLM calls). Per-grader facet
  semantics are imported unchanged from `build_narratives.py`
  (`facet_memberships`, `facet_net_scores`, `conflict_direction`); the
  aggregation pools the graders: `dirs` weight each edit by
  (#valid graders assigning)/(#valid graders) — 1, 2/3, 1/3 with three valid;
  1, 1/2 with two — `total` counts edits coded by >= 1 v2 grader (2,582), and
  `cum`/`cumsq` accumulate the pooled (fractional) net scores. Stories carry
  every grader's codes plus the per-dimension `consensus` object; the curated
  ride-on is dropped because the highlight links that consumed it are disabled
  (v1-tied). Example texts come from `recode/data/canonical/edits.jsonl`
  (find_text / replace_text_sanitized — the same sanitized text the graders saw).
  For the **System prompts** view the bundle carries the separate top-level
  `sp_stats` table — `{facet: {model_display: cell}}`, the same cell shape and
  model keys as the per-condition `stats` cells, restricted to
  `document_type == "system_prompt"` and pooled over ALL conditions and the four
  system-prompt documents (replicate = each model's (run, condition, document)
  chain), now under three-grader pooling — and a `doc_type` field on every story
  example so the example browser can filter the stratum client-side.
- `data/selfcheck.json` — ground truth computed directly from the three codes
  files (codes_io, LAST row per edit_id): per-model pooled mean judge + N,
  per-model P(affirm), per-model paternalism and welfare presence/direction
  weights, `system_prompt_stratum` per-model means + Ns (per-document table for
  reference), counts of edits by number of valid graders, the valid-grader
  sets, and judge consensus counts (unanimous / 2–1 with dissenter breakdown /
  3-way / fewer than 3 valid). Build-time assertions check that BOTH the
  site.json bundle (full floats, tol 1e-9) and narratives.json (dirs serialized
  to 6 decimals, tol 1e-5; all Ns exact) reproduce it.

## Files copied from docs/ and patched

### index.html

- Title labeled as the v2 re-code variant.
- Variant banner (label + one-line methods note + B_intergrader.md pointer) at the top of the page; defines the .v1-flag style.
- Byline notes the re-analysis so the page is not mistaken for the published v1 site.
- Findings paragraph 1 flagged as v1 narrative text (its claims are not v2 pooled figures).
- Findings paragraph 2 flagged as v1 narrative text.
- Results Explorer heading labeled: all its figures are the v2 three-grader pooled average.

### conversations.html

- Title labeled as the v2 re-code variant.
- Variant banner at the top of the page.

### prompts.html

- Title labeled as the v2 re-code variant.
- Variant banner at the top of the page.
- Coding-tab description rewritten: v2 pipeline is blinded + contextual with three graders, all three listed (the v1 text described the unblinded metadata).
- System prompt replaced with the exact v2 blinded prompt (recode/prompts/v2_system.md): contextual input, synthetic anchors, explicit judge-0 instruction, R6.
- User template replaced with the v2 blinded template (recode/prompts/v2_user_template.md): no editing-model / condition / round metadata; context fields added.
- Coder note names all three v2 graders and the pooling rule instead of the single v1 Gemma coder.

### styles.css

- Copied verbatim (no patches).

### app.js

- renderRecord coding block rewritten: shows all three graders' codes side by side (grid) with per-dimension consensus markers (unanimous / 2–1 split naming the dissenter / 3-way split / fewer than 3 valid graders, with vote counts), a dissent tag on the dissenting grader, and the pooled judge; uncoded records get an explicit graceful note.

### facets.js

- Number formatter for pooled (fractional) counts, plus the embedded grader list and consensus-marker styles used by the per-grader displays.
- Every takeaway (hardcoded v1 numbers/claims) is flagged as v1 text so it is not read as a v2 figure.
- Highlight links disabled: their curated ids and quoted tips are tied to v1 codes and would silently jump to the wrong example under the regenerated v2 stories.
- Example code chips rewritten: pooled judge, per-dimension consensus markers with vote counts, and every grader's codes (dissenter tagged).
- Example evidence/cost-clause blocks rewritten: per-grader evidence for every grader and grader-tagged cost clauses.
- How-to note documents the pooling semantics (1/n_valid weights), the one-decimal display and the denominator.
- Drift note documents pooled (fractional) net scores and the System-prompts view's per-model lines over system-prompt chains.
- Fractional (averaged) counts rendered to one decimal.
- Fractional (averaged) judge counts rendered to one decimal; the mean shown equals the mean of per-edit judge averages.
- Fractional (averaged) conflict counts rendered to one decimal.
- New "System prompts" option appended to the condition-chip list immediately after Cross Edit.
- Chip label for the new view: "System prompts".
- Tooltip/subtitle for the new chip states the fixed semantics: all conditions; system-prompt documents only; rendered per editing model.
- aggStat reads the System-prompts view from the separate sp_stats table (keyed by model_display, the same cell shape as the per-condition cells), leaving real-condition pooling untouched.
- Example browser: the System-prompts view filters stories by the new doc_type field (all conditions) instead of by condition_id.
- Stacked freq-bar branch (unused by the current facets, all diverging): pooled counts rendered to one decimal.
- Stacked freq-bar branch: pooled engaged count rendered to one decimal.
- Stacked freq-bar segment tooltip: pooled count rendered to one decimal.

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
- The JS consensus markers read the precomputed `consensus` objects; nothing in
  the patched JS is hard-wired to three graders (the grader list is embedded by
  the builder as `POOL_GRADERS`).
