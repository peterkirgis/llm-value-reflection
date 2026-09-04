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
