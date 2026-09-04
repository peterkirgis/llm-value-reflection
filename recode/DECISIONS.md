# Decisions & Overrides for BRIEF.md (locked with Peter, 2026-09-03)

These decisions override the corresponding text in `recode/BRIEF.md` wherever they
conflict. Everything else in the brief stands as written.

## 1. Graders (resolves BRIEF §3 B1 ASK)
- Exactly **two** graders, both via OpenRouter:
  - `google/gemma-4-31b-it` — the same model string v1 used (see
    `coder_model` in `results/iterative_edit/judge_beneficiary_coded_gemma.json`).
  - `qwen/qwen3.8-2.4t-a95b` — the largest available Qwen 3.x on OpenRouter
    (2.4T-param MoE, chosen 2026-09-03; record exact string in run logs).
- No third grader, no majority vote. Per BRIEF §3 B3 two-grader rule:
  `ensemble.jsonl` = Gemma-v2 codes with a `disagrees_with_qwen` flag per dimension.
- PPI prediction *f* (BRIEF §4 C4) = the Gemma-v2 codes.

## 2. Reasoning settings (resolves the v1/memo discrepancy)
- All **v2** grading calls (both graders, plus E2/E3/E4/E5 variants) request
  `reasoning: {effort: "high"}` via OpenRouter `extra_body`, temperature 0
  (E4 uses temperature 0.7 per the brief). If a model/endpoint rejects the
  reasoning parameter, log it and proceed without it — never silently.
- **Exception — E1 label-swap arms replicate v1 exactly**: v1 built its judge
  ModelSpec with NO reasoning parameter (OpenRouter provider default) and
  temperature 0.0 (see `experiments/iterative_edit/qualitative_code.py`,
  ModelSpec construction). E1 diagnoses v1 as it actually ran, so all three
  E1 arms use v1's exact settings.

## 3. Human coding (resolves BRIEF §4 C2)
- Build the **minimal local web UI** (one edit at a time, radio buttons,
  writes the same CSV schema as `coding_sheet.csv`).
- **Two human coders** (Peter + one other). The UI must support a coder
  identity (e.g. name entered at start → per-coder CSV such as
  `coding_sheet_<coder>.csv`); same blind order for both; human–human κ is
  computed in C3.

## 4. Repo footprint (overrides BRIEF §9/§10 paths)
- Do NOT restructure the repository. ALL new work lives under `recode/`:
  - `recode/data/canonical/`, `recode/data/codes/`, `recode/schemas/`,
    `recode/prompts/`, `recode/human/`, `recode/reports/`, `recode/figures/`,
    `recode/src/` (pipeline code), `recode/tests/`, `recode/notes/`,
    `recode/config.yaml`.
  - Every path in the brief maps accordingly (e.g. brief `data/canonical/edits.jsonl`
    → `recode/data/canonical/edits.jsonl`; brief `reports/A_v1_vs_v2.md` →
    `recode/reports/A_v1_vs_v2.md`).
- Only permitted change to existing files: dependency additions to
  `pyproject.toml` (+ `uv.lock` via `uv sync`). Existing `src/valconv/` may be
  IMPORTED by recode code (e.g. `apply_diff`) but never modified.
- `results/iterative_edit/` is strictly read-only. Copy v1 codes to
  `recode/data/codes/v1.jsonl` (converted to JSONL, one record per line).
- `data/processed/` is a generated dir (gitignored) rebuilt by
  `src/valconv/documents.py`; fine to regenerate, never edit by hand.

## 5. Paper deliverables (overrides BRIEF §9)
- SKIP `paper/methods_paragraph.md`, `paper/limitations_paragraph.md`,
  `paper/appendix_coding.md` — no paper text drafts.
- INSTEAD, "reproduce the figures": regenerate the paper's judge/beneficiary
  figures (see `reports/generate_judge_beneficiary_figures.py`) under the
  v2 Gemma codes and the ensemble, written to `recode/figures/` (never
  overwrite `reports/figures/`), PLUS the brief's new figures
  (`drift_<doc>.png` with bootstrap bands, `headline_ci.png`).
- All reports listed in BRIEF §9 are still due (under `recode/reports/`).
  `SUMMARY.md` still due.

## 6. Canonical frame (resolves counts)
- Canonical edits = the 7 files in `RELIABLE_RUNS`
  (see `experiments/iterative_edit/viewer/build_static_site.py`): 2,740 records.
- The 3 non-reliable files (`run_20260320_173238` 10-round pilot,
  `run_20260421_225849` 3-round aborted cross-edit, `run_20260501_193324`
  3-record fragment) are inventoried and flagged in `00_inventory.md` but
  NOT canonicalized or coded.
- **CORRECTION (2026-09-03, verified by census):** records with
  `total_rounds: 3` inside reliable files are NOT duplicates — they are
  rounds 1–3 of chains that later resumed to 20 rounds (integral chain
  prefixes; zero duplicate (model, doc, condition, round) tuples exist in any
  reliable file). Keep ALL 2,740 records; do NOT dedup. Document this
  correction in `00_inventory.md`. Chain identity must include the run file:
  the capable-baseline cells appear in both run_20260429 and run_20260507 as
  separate full chains.

## 7. Seeds
- No seed exists in the run records or configs. `"seed"` in edits.jsonl is
  `null`. Runs are identified by run file + (model, document, condition) chain.
- All NEW randomness (sampling, bootstrap, blind ids, sheet order) uses fixed
  seeds recorded in `recode/config.yaml`, with each draw saved to disk.

## 8. API & secrets
- Everything through OpenRouter (`https://openrouter.ai/api/v1`), key in
  `.env` at repo root (gitignored) as `OPENROUTER_API_KEY`, loaded via
  python-dotenv. NEVER print, log, echo, or commit the key. Never commit `.env`.

## 9. Git
- Branch: `qualitative-coding-rework`. Commit after each workstream with a
  message naming the workstream. NEVER push.

## 10. Known data facts (verified 2026-09-03, trust these)
- Run records were reconstructed from `docs/data/site.json.gz` and LACK
  `previous_content`/`new_content` (see `results/iterative_edit/README.md`).
  Document states MUST be reconstructed by replaying edits from the processed
  initial documents using `src/valconv/diffing.apply_diff` (exact →
  whitespace → fuzzy), verifying against each record's stored `match_strategy`.
- v1 coded file has 2,580 items; error-coded items were dropped at publish
  time, so some canonical edits will lack a v1 code (record `v1_code: null`).
- v1 grader user template includes `editing model`, `prompt condition`, and
  `round` (the unblinding this project fixes); v1 system prompt is in
  `qualitative_code.py` and paper Appendix B (`reports/spar_midterm_report.tex`).
- The six conditions map: baseline, you_framing, allow_no_edit,
  no_constitution_prepend (= brief's "no system prompt"), implementation_note,
  cross_edit.
- Abstention sentinel: `no_change: true` on the record (FIND/REPLACE =
  `[NO CHANGE]`, `match_strategy: "no_change"`).
- Documents (8): claude_constitution, openai_model_spec,
  **openai_model_spec_no_csam** (owner OpenAI; the v2 prompt's R5 wildcard
  `openai_model_spec*` already covers it), gemini_constitution,
  opus_system_prompt, gpt_system_prompt, gemini_system_prompt,
  grok_system_prompt. Owners per `DOC_OWNERS` in `qualitative_code.py`.
- **Two text versions per edit**: document replay uses the record's raw
  `replace_text` (what was actually applied); the v1 grader saw
  `export_changes.sanitize_replace_text` output (= `changed_text` in the v1
  coded file). For v1↔v2 comparability, v2 grader inputs use the SANITIZED
  text (reuse the coded file's `changed_text` verbatim where present;
  otherwise apply `sanitize_replace_text`). `edits.jsonl` carries both:
  `replace_text` (raw, applied) and `replace_text_sanitized` (grader input).
- Error records (158 in reliable files) never advance document state, occupy
  their round slot permanently (never retried in reliable runs), have empty
  find/replace and a meaningless default `match_strategy: "exact"`. Include
  them in `edits.jsonl` with a non-applied `apply_status`; exclude from
  grading (nothing to code) and from match-strategy stats.
- Only 2 abstentions exist corpus-wide (Grok 4.3, allow_no_edit, rounds 18
  and 20). v1 never coded them. Expected v1-join misses: exactly 160
  (158 errors + 2 abstentions) → 2,580 v1 codes.

## 11. Missing document: openai_model_spec_no_csam (Phase 0 blocker resolution)
- `data/processed/openai_model_spec_no_csam.md` was never committed and is not
  generated by `documents.py`. It is the initial state for one 20-round
  Claude Opus 4.7 cross-edit chain in run_20260518_171402 (20 edits).
- Resolution: RE-DERIVE it by removing the CSAM/info-hazard subsections from
  `data/processed/openai_model_spec.md` (see
  `experiments/iterative_edit/config_frontier_cross_no_csam.yaml` and
  CHANGE_LOG.md for intent), then VALIDATE by replaying the 20-round chain:
  every FIND must match with the recorded `match_strategy` and
  `match_count == 1`. The derived file lives at
  `recode/data/derived/openai_model_spec_no_csam.md` (never in
  `data/processed/`).
- If validation cannot be achieved, canonicalize those 20 edits with null
  context fields and `context_missing_reason`, flag prominently in
  `00_inventory.md`, and tell Peter. (Note: the PARALLEL Opus 4.7 ×
  openai_model_spec cross chain is 20/20 errors — a different chain; don't
  conflate the two cells.)
