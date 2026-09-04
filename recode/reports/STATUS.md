# Workstream status log

## Phase 0 — Inventory and canonicalize (+ A2 infrastructure) — DONE (2026-09-04)
- `data/canonical/edits.jsonl`: 2,740 records (137 chains × rounds 1..20), all
  schema-valid; 2,580 applied / 158 errors / 2 abstentions; v1 join exactly
  2,580 with the expected 160 misses; every applied edit replayed with
  match_count == 1 and the recorded match_strategy reproduced.
- `openai_model_spec_no_csam.md` re-derived and replay-validated 20/20
  (`data/derived/openai_model_spec_no_csam_derivation.md`).
- `data/codes/v1.jsonl` (2,580 lines, payload-identical to the read-only
  original); schemas, prompts (v1/v2/variant), `reports/00_inventory.md` written.
- Unit tests: 40 passed (replay/context, parsing/validation, kappa/alpha,
  bootstrap, PPI). Live smoke test: 3 edits × 2 graders via OpenRouter, all
  valid JSON on attempt 1, abstention coded (0, not_present, no conflicts) by
  both graders, reasoning accepted, cache hits verified; projected full pass
  ≈ 11M in + 5M out tokens per grader (well under the 100M ASK threshold).

## Fixer round 2 — per-document section_heading detection (2026-09-04)
- Root-cause fix for the audit must-fix: the heading extractor only knew ATX
  '#' headings, leaving section_heading == '' on all 1,211 applied records in
  claude_constitution / opus_system_prompt / gemini_system_prompt (plus 5
  gpt_system_prompt preamble records). `src/replay.py` now detects headings
  per document: standalone bare-line headings (claude_constitution,
  gpt_system_prompt), nesting-aware pseudo-XML bracket tags + blank-above
  bare lines (opus_system_prompt), full-line bold headings incl. mangled
  variants (gemini_system_prompt); ATX (outside code fences) everywhere.
  Heading = nearest heading line at or above the span's first line.
- `data/canonical/edits.jsonl` regenerated (all Phase 0 acceptance checks
  re-passed: 2,740 records, 2,580 applied, 160 expected v1 misses); empty
  headings now 49/2,580 (all genuine: 46 Gemini preamble, 1 GPT preamble,
  2 opus restructured-state edges). BRIEF §1.3's example ("Being broadly
  safe") is now producible; all three audit-named edit_ids carry headings.
- `reports/00_inventory.md` regenerated with the detection conventions,
  their known noise, and a per-document heading-coverage table.
- Tests: 55 passed (15 new heading-style tests). No grader tokens spent;
  the smoke-test artifact predates this fix (prompt cache keys change for
  the affected records, so stale cache entries are inert).

## Workstream F — Free results — DONE (2026-09-04)
- `reports/F_free_results.md` + `data/analysis/free_results/*`. Abstention:
  2/360 allow_no_edit round slots (both Grok 4.3, rounds 18/20); every other
  model 0/40. judge=0 share under v1: 23.0% overall (12.1%–31.2% by model).
  Apply failures: 158 (94 GPT-5.4 Mini). Restatement >50% 8-gram overlap:
  3.1% of scored edits (Grok 4.2 11.9%, Haiku 10.9%). Doc-type control: the
  Claude judge-score sweep holds within constitutions but NOT within system
  prompts under v1. All numbers audit-verified by independent recomputation.

## Workstream D — Cluster bootstrap (v1 slice) — DONE (2026-09-04)
- `reports/D_bootstrap.md`, `figures/drift_*.png`, `data/analysis/bootstrap/*`.
  B=2000, seeded, chain-level resampling (137 chains). Pooled ranking
  stability (all 3 Claude > every non-Claude, mean judge) = 1.0000;
  cross-edit-only = 0.5285 — the cross-edit robustness claim does NOT
  survive at 0.95 under v1. Re-runnable for v2/ensemble via --codes/--label.

## Headline module (§8) — v1 baseline — DONE (2026-09-04)
- `src/headline.py`, `reports/partials/headline_v1.md`. Claims under v1:
  a YES, b YES, c NO (Gemini 3 Flash violates "all models"), d NO (Sonnet
  structural 3.73–3.91×, not >4×), e YES, f YES (primary part), g NO
  (6 deployer-served disclosure events exist). Discrepancies verified against
  the raw published coded file under the site's own counting convention.
- Known cross-module wart (audit warning, fix before v2 analyses): the three
  modules differ slightly in which codings count as valid when an 'error'
  key is present. Unify in the A3/B3 workstream.

## E-infrastructure + human UI — DONE (2026-09-04)
- `src/e_runs.py`: E1 arms (exact v1 instrument replication, Appendix IV swap
  map asserted in tests), E2/E3/E4/E5 drivers with resume + caching; E1 300-id
  seeded sample drawn. Live 4-call check produced valid v1-instrument codes.
- `prompts/v2_para1.md` / `v2_para2.md`: hand-authored Appendix V paraphrases;
  protected-token inventories byte-identical (62 tests), 5-gram prose overlap
  16.2% / 15.4% (bar: <60%), OUTPUT FORMAT byte-identical by construction;
  live Qwen equivalence verdicts NO/NO (`notes/paraphrase_equivalence.md`).
- `human/`: Flask blind-coding UI (per-coder sheets, resume, taxonomy-exact
  values), seeded 150-edit C1 draw (15/model, applied-only), blind key,
  coder instructions (v2 manual sections verbatim, no anchors per Appendix
  III), 18 UI tests. Blinding audit: no model/provider/condition/round or
  blind-key content in any HTTP response. Awaiting the 30 adjudication
  extras (B3 + E4) before hand-off to Peter.
- Both audits passed. Full test suite: 171 passing.

## A3/B3/C/E analysis machinery + unified codes IO — DONE (2026-09-04)
- `src/codes_io.py`: single validity predicate + loader (last-row-wins),
  now used by bootstrap/headline/free_results — zero numeric drift proven
  against committed v1 outputs (byte-identical artifacts).
- `src/compare_v1_v2.py` (A3), `src/intergrader.py` (B3: kappa/alpha,
  COI test with cluster-bootstrap CI, ensemble.jsonl per DECISIONS §1),
  `src/human_validation.py` + `src/ppi_analysis.py` (C3/C4, ppi_py with
  Appendix VI fallback, adjudication extras excluded from PPI),
  `src/e_reports.py` (E1–E5 report generators; E4 exports the 30
  adjudication extras in --append-extras format).
- Both audits passed (hand-computed kappa, textbook alpha cross-check,
  PPI n=N reduction, paired-bootstrap fixture). Suite: 276 passed.
- All runnable with one command each once v2_gemma/v2_qwen complete.
