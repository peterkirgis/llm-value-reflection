# analysis/

The coding and analysis pipeline. It takes the edits the models made
(`results/iterative_edit/`), codes every edit with three blinded LLM graders,
combines them by majority vote, tests how robust the codes are, and produces
the figures and the website. This folder was called `recode/` until
2026-10-08; files written before then (and the frozen inputs below) still say
`recode/`.

Paths in `code` are relative to the repository root; links are relative to
this folder. All commands run from the repository root with the environment
from `uv sync` (see the [root README](../README.md)).

## Where it started: BRIEF.md and DECISIONS.md

- [BRIEF.md](BRIEF.md) is the original specification (2026-09-03): what was
  wrong with the first single-grader coding (it saw the editing model's name,
  its calibration examples came from the headline results, there was no
  reliability or uncertainty evidence) and the workstreams that fix it. Its
  workstream letters name the reports: A the blinded re-code, B the extra
  graders, C human validation, D the bootstrap, E the sensitivity checks,
  F results from existing data. "Phase 0" is its canonicalization step.
- [DECISIONS.md](DECISIONS.md) is the decisions log. It overrides BRIEF.md
  where they conflict: which graders, reasoning settings, the human-coding
  setup, the resampling unit, and later amendments such as the third grader and
  the majority vote (2026-09-16).
- [config.yaml](config.yaml) holds the grader model strings and settings,
  bootstrap sizes and seeds.

All three are frozen as written. [reports/STATUS.md](reports/STATUS.md) is the
build log of each workstream.

## The pipeline, in order

The stage numbers are the project's (root README, Pipeline); stages 1 to 3
produce the documents, the edit runs and the original coding, and this folder
starts at stage 4.

| Stage | Command | Reads | Writes |
|---|---|---|---|
| 4. Canonical edits (phase 0) | `.venv/bin/python analysis/src/build_phase0.py` | `results/iterative_edit/`, `data/processed/`, `analysis/data/derived/` | `scratch/phase0/edits.jsonl` and `scratch/phase0/v1.jsonl`, to compare with the committed `analysis/data/canonical/edits.jsonl` and `analysis/data/codes/v1.jsonl` |
| 5. Three blinded graders | `.venv/bin/python analysis/src/grade.py --grader gemma` (then `qwen`, `muse`) | edits, `analysis/prompts/v2_system.md`, `analysis/prompts/v2_user_template.md`, `analysis/config.yaml` | `analysis/data/codes/v2_<grader>.jsonl`, or the file given with `--out` |
| 6. Agreement and majority vote | `.venv/bin/python analysis/src/intergrader.py --graders gemma=analysis/data/codes/v2_gemma.jsonl qwen=analysis/data/codes/v2_qwen.jsonl muse=analysis/data/codes/v2_muse.jsonl` | the grader files | `analysis/data/codes/ensemble.jsonl`, `analysis/reports/B_intergrader.md`, `analysis/data/analysis/intergrader/` |
| 7a. Headline statistics | `.venv/bin/python analysis/src/headline.py --codes analysis/data/codes/ensemble.jsonl --label ensemble` | a codes file, edits | `analysis/reports/partials/headline_<label>.md`, `analysis/data/analysis/headline/` |
| 7b. Cluster bootstrap | `.venv/bin/python analysis/src/bootstrap.py --codes analysis/data/codes/ensemble.jsonl --label ensemble` | a codes file, edits | `analysis/reports/D_bootstrap_<label>.md`, `analysis/data/analysis/bootstrap/` |
| 7c. Sensitivity checks E1-E5 | `.venv/bin/python analysis/src/e_runs.py <subcommand>` (grading), then `.venv/bin/python analysis/src/e_reports.py <e1..e5>` (reports) | edits, variant prompts | `analysis/data/codes/e*.jsonl`, `analysis/reports/E*.md`, `analysis/data/analysis/e*/` |
| 7d. Other analyses | `.venv/bin/python analysis/src/free_results.py`; `.venv/bin/python analysis/src/compare_v1_v2.py --v1 analysis/data/codes/v1.jsonl --v2 analysis/data/codes/v2_gemma.jsonl --label v1_vs_v2_gemma` | edits, codes files | `analysis/reports/F_free_results.md`, `analysis/reports/A_v1_vs_v2.md`, `analysis/data/analysis/` |
| 8. Figures | `make figures` | `analysis/data/codes/ensemble.jsonl`, edits, `analysis/figures/title_decisions.json`, `analysis/config.yaml` | `analysis/figures/` |
| 9. Website | `make site` (`.venv/bin/python analysis/src/build_site.py`) | `ensemble.jsonl` and the three grader files, edits, `results/iterative_edit/run_*.jsonl`, `analysis/prompts/v2_system.md`, `analysis/prompts/v2_user_template.md`, `analysis/site_base/`, `analysis/data/site/site_text.json`, `analysis/figures/data/ts_beneficiary_panels.json` | `docs/`, plus the build records `analysis/data/analysis/site/selfcheck.json` and `analysis/notes/site_patches.md` |

Stage 5 and the `e_runs.py` half of 7c call OpenRouter (key in `.env`).
Everything else is offline and deterministic: re-running stages 4, 6, 7a,
7b, the E reports (`e_reports.py`), 7d, 8 and 9 reproduces the committed
files apart from generation timestamps (checked 2026-10-08), with one
exception: `e_reports.py e4` also picks the 30 adjudication extras for the
human sample, and since those are already in the sample a re-run picks 30
others. Keep the committed E4 report and `analysis/data/analysis/e4/`.

Shared modules: `analysis/src/common.py` (paths, loaders, and
`RELIABLE_RUN_STEMS`, the seven runs every analysis uses),
`analysis/src/codes_io.py` (the one loader and validity rule for codes
files), `analysis/src/stats.py`, `analysis/src/client.py` (the API client and
cache) and `analysis/src/draft_highlights.py` (reads the draft for the site).
The stages in detail:

4. **Canonical edits.** `build_phase0.py` replays every 20-round chain of the
   7 reliable runs from the cleaned source documents, checks that each find
   text matches exactly once, and records the surrounding paragraphs and
   section heading, so a grader sees the edit in context. 2,740 rounds: 2,580
   applied edits, 2 abstentions and 158 failed rounds. It needs
   `data/processed/` (`make documents`) and takes about half an hour. The
   committed outputs are raw data, so it writes to `scratch/phase0/`
   (`--out-dir`) and refuses the committed paths; a rebuild matches them byte
   for byte (`cmp`). Helpers: `analysis/src/replay.py` (the replay),
   `analysis/src/derive_no_csam.py` (re-derives the one source document that
   was never committed, the OpenAI Model Spec without two subsections; it
   writes to `scratch/derived/`, and its document matches the committed
   `analysis/data/derived/openai_model_spec_no_csam.md` byte for byte),
   `analysis/src/build_inventory.py` (the census in
   [reports/00_inventory.md](reports/00_inventory.md)) and
   `analysis/src/make_prompts.py` (writes `analysis/prompts/` from BRIEF.md
   and the original coder).
5. **Graders.** Each grader (Gemma 4 31B, Qwen 3.8, Muse Spark 1.3; model
   strings in `analysis/config.yaml`) sees the edit and its context but not
   the editing model, its provider or the prompt condition. Replies are
   schema-checked, with up to three attempts per edit. `grade.py` resumes:
   edits already graded are skipped (only transport failures are retried), so
   a re-run of a finished grader makes no calls and appends nothing. Without
   `--out` it appends to the committed raw file; `make api-grade` passes
   `--out scratch/grades/v2_<grader>.jsonl` instead, which re-grades every
   edit. Every request goes through `analysis/src/client.py`, which answers
   from `analysis/data/cache/` when it can; unpack the committed cache with
   `make cache` before any re-run. `grade.py --smoke` (a three-edit pre-flight
   check) writes to `scratch/grading_smoke_test/`.
6. **Majority vote.** Per dimension, the value at least two graders agree on.
   When all three disagree on the judge score, Gemma's value is used and the
   edit is flagged `no_majority` (93 edits). This ensemble is the coding behind
   every reported number, the figures and the website. The vote is
   deterministic; `make check` rebuilds it and compares it byte for byte.
7. **Statistics and checks.**
   - 7a, **headline statistics** per model and provider: mean judge score,
     cumulative drift at round 20, patienthood, conflict rates and the seven
     headline claims (a)-(g) of BRIEF.md §8, as point estimates. Run once per
     codes file (`v1`, `v2_gemma`, `v2_qwen`, `v2_muse`, `ensemble`).
   - 7b, **bootstrap**: whole 20-round chains are resampled within model
     (edits in a chain are not independent): intervals, and how stable the
     model ranking is.
   - 7c, **sensitivity checks**, each re-grading with one thing changed:
     E1 swaps or removes the editing model's name under the original
     (unblinded) instrument; E2 grades with two hand-written paraphrases of the
     grader prompt; E3 uses an alternative paternalism definition; E4 samples
     Gemma five times at temperature 0.7; E5 hides the context. E2-E5 use the
     Gemma grader. `analysis/src/e_runs.py --help` and
     `analysis/src/e_reports.py --help` list the subcommands; each report
     names its input files in its header. Like `grade.py`, `e_runs.py`
     resumes into the committed `e*.jsonl` files, which are complete.
   - 7d, **other analyses**: `free_results.py` reports what the data shows
     without new grading (abstentions, failed rounds, restatement, edit size,
     document type). `compare_v1_v2.py` compares the original codes with one
     blinded grader (the command above produced the committed report).
8. **Figures.** `report_figures.py` redraws the original report's figures
   under the new codes; `value_drift_summary.py`, `value_drift_round20.py` and
   `home_likeness_summary.py` draw the summary figures, and `home_likeness.py`
   computes the metric the last one plots. `make figures` runs all five.
   [figures/README.md](figures/README.md) lists every figure and its script.
9. **Website.** `build_site.py` copies the frozen page template
   `analysis/site_base/` into `docs/`, writes the data bundles from the
   ensemble, patches the page text, and checks its counts against the
   ensemble and the `ts_beneficiary_panels` figure data. The statements and
   quoted edits are the authors' LessWrong draft's, committed as
   `analysis/data/site/site_text.json`: the findings sentences, each facet's
   takeaway, each quoted edit with the edit id it resolves to, and the added
   carousel slide. The build reads only that file and re-resolves every
   stored quote against the canonical edits. The authors maintain it from
   their local draft (not tracked) with
   `.venv/bin/python analysis/src/site_text.py --draft <draft.md> --widget <widget.html>`
   (`--check` compares instead of writing). `make site` changes only
   timestamps; `analysis/tests/test_build_site.py` checks that a rebuild
   reproduces `docs/`. A build with `--out-dir <dir>` other than `docs/`
   writes its two build records next to `<dir>` and leaves the tree clean.

## Data layout

Raw (frozen; checksums in `raw_data.sha256`):

| Path | Contents |
|---|---|
| `analysis/data/canonical/edits.jsonl` | One record per round: model, document, condition, round, find/replace text, context, apply status. |
| `analysis/data/codes/v1.jsonl` | The original single-grader codes (copy of `results/iterative_edit/judge_beneficiary_coded_gemma.json`). |
| `analysis/data/codes/v2_gemma.jsonl`, `v2_qwen.jsonl`, `v2_muse.jsonl` | The three blinded graders. Append-only: the last row per `edit_id` wins. |
| `analysis/data/codes/ensemble.jsonl` | The majority vote. |
| `analysis/data/codes/e1_*.jsonl` ... `e5_nocontext.jsonl` | Sensitivity-check codes. |
| `analysis/data/raw_api_cache_2026-10-08.tar.gz` | Every grader API response (32,293 entries; format below). |
| `analysis/data/derived/` | The re-derived OpenAI Model Spec variant and its validation table. |
| `analysis/prompts/` | The grader prompts. `v1_system.md` and `v1_user_template.md` are the original (unblinded) instrument as the pipeline loads it, and `v1.md` combines the two into one readable document (byte-identical content); likewise `v2_system.md`, `v2_user_template.md` and `v2.md` for the blinded instrument. `v2_google_doc.html` is a paste-ready Google Docs rendering of the v2 prompt (verbatim wording). `v2_para1.md`, `v2_para2.md` (E2) and `v2_paternalism_variant.md` (E3) are the variants. |
| `analysis/schemas/` | JSON schemas of an edit record and a code. |
| `analysis/human/` | The blind human-coding sample, its key, the coder instructions, the coding app and Peter's coding sheet (see below). |
| `analysis/figures/title_decisions.json` | Hand-audited figure titles. |

The cache archive holds one JSON file per request,
`cache/<first two hex chars>/<cache_key>.json`, with the model, the
parameters, the prompt hash, a timestamp and the full response text. The key
is the sha256 of the model, system prompt, user prompt, temperature and
extra sampling parameters (`analysis/src/client.py`); a corrective retry after
a schema failure has its own entry. The archive is deterministic (sorted
entries, fixed owner and mtime, no name or time in the gzip header).
`make cache` checks it against
`analysis/data/raw_api_cache_2026-10-08.tar.gz.sha256` and unpacks it into
`analysis/data/cache/`, the gitignored working copy that `client.py` reads.

Derived (rebuilt by the scripts above; safe to regenerate):
`analysis/data/analysis/` (per-analysis JSON and CSV), `analysis/reports/`,
`analysis/figures/` (except `title_decisions.json`) and `docs/`.

Authors' text: `analysis/data/site/site_text.json`, the statements and quoted
edits the website takes from the authors' LessWrong draft. Not raw data and
not rebuilt by `make site`; the authors regenerate it with
`analysis/src/site_text.py` (stage 9 above).

## Reports: final and preliminary

| Report | Status |
|---|---|
| [reports/00_inventory.md](reports/00_inventory.md) | Final. Census of the canonical edits. |
| [reports/B_intergrader.md](reports/B_intergrader.md) | Final. Agreement between the three graders, the grader-conflict-of-interest test, the majority vote. |
| [reports/partials/](reports/partials/) `headline_<label>.md` | Final point estimates, one per codes file. |
| [reports/D_bootstrap_ensemble.md](reports/D_bootstrap_ensemble.md) and the other `D_bootstrap*.md` | Final intervals, one per codes file (`D_bootstrap.md` is the original codes). |
| [reports/E1_label_swap.md](reports/E1_label_swap.md) to [reports/E5_context.md](reports/E5_context.md) | Final. |
| [reports/A_v1_vs_v2.md](reports/A_v1_vs_v2.md) | Final. Original codes against the Gemma blinded grader only. |
| [reports/F_free_results.md](reports/F_free_results.md) | Final for the original, Gemma and Qwen codes; not re-run after Muse was added. |
| [reports/SUMMARY.md](reports/SUMMARY.md) | **Preliminary.** Written for two graders, with a three-grader addendum; the human-validation and PPI results it waits for do not exist yet. |
| [reports/site_claims_review.md](reports/site_claims_review.md) | Historical. Reviews the pre-consensus site against the two-grader evidence. |
| [reports/STATUS.md](reports/STATUS.md) | Build log. |

The numbers in the LessWrong post and on the website come from the ensemble
through `analysis/figures/` and `analysis/src/build_site.py`.

## Not done yet: human validation and PPI

The blind sample has not been coded. It has 180 rows: 150 random edits (15
per model) plus 30 low-agreement edits for adjudication, appended at the end
(`analysis/human/blind_key.csv` maps blind ids to edits and flags the
extras). To code it, run `.venv/bin/python analysis/human/app.py` and open
http://127.0.0.1:5111. Each coder's sheet is `analysis/human/coding_sheet_<coder>.csv`;
`analysis/human/coding_sheet_peter.csv` exists and is still blank (identical
to the template), so once Peter codes, update its line in `raw_data.sha256`.

[human/README.md](human/README.md) and the docstring of `analysis/human/app.py`
are frozen with the sample and are out of date in two ways: they say
`recode/human/app.py` and `recode/src/draw_human_sample.py` (now
`analysis/human/app.py` and `analysis/src/draw_human_sample.py`), and the
human README says the template has 150 edits (it has 180, with the 30
adjudication extras appended).

Then `analysis/src/human_validation.py` reports human-human and human-grader
agreement, and `analysis/src/ppi_analysis.py` combines the human labels with
the ensemble codes (DECISIONS.md §1) into prediction-powered estimates; usage
is in each script's docstring. Both are tested on synthetic sheets.
`analysis/src/draw_human_sample.py` drew the sample.

## Notes

| File | What it is |
|---|---|
| [notes/repo_map.md](notes/repo_map.md) | Technical map written for the agents that built this pipeline (2026-09-03): replay algorithm, canonicalization, run-to-config map, census. The code cites its sections. |
| [notes/site_patches.md](notes/site_patches.md) | Generated by `build_site.py`: every patch it applies to the page template. |
| [notes/paraphrase_equivalence.md](notes/paraphrase_equivalence.md) | The check that the E2 paraphrases permit the same codes as the original prompt. |
| [notes/inconsistency_examples.md](notes/inconsistency_examples.md) | Verified examples of edits that resolve contradictions in the original documents, for the write-up. |
| [notes/jev_assessment.md](notes/jev_assessment.md) | 2026-09-23 memo on using an external tool for an extra coding pass. No such pass has been run. |

## Tests

`make test` runs `analysis/tests/` (about 30 seconds, offline). Besides unit
tests, it checks that the vendored figure code matches the original generator,
that a site rebuild reproduces `docs/`, that the raw data matches
`raw_data.sha256` (`analysis/tests/test_raw_data.py`), that the scripts that
could overwrite raw data refuse to, and that every path the READMEs mention
exists (`analysis/tests/test_doc_paths.py`; its git-history check is
skipped in a shallow clone).
