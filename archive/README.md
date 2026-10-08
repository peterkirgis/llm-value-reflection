# archive/

Files that are no longer part of the pipeline but are kept for the record:
earlier write-ups, the original report's figure generators, and experiment
configs that produced no surviving run. Nothing outside `archive/` runs or
imports anything in here, except `analysis/tests/test_report_figures.py` and
`analysis/tests/test_home_likeness.py`, which compare the vendored figure code
in `analysis/src/` against the original generators.

Everything here was moved with `git mv` on 2026-10-08, so
`git log --follow <path>` shows each file's earlier history. The second half
of this page lists material that is no longer in the tree at all, with the
commands that recover it. Commit `3b36326` is the last state before the
2026-10-08 restructure (clones made that day also have it as the tag
`backup/pre-restructure-2026-10-08`); `analysis/` was then called `recode/`.

## Contents

| Path | Was | What it is |
|---|---|---|
| `archive/spar_midterm/spar_midterm_report.tex`, `.pdf` | `3b36326:reports/spar_midterm_report.tex` | The SPAR midterm report (coding v0). The `.tex` no longer compiles: the `drift_*.pdf` figures it includes were deleted from the repo in `06a3cbc`. |
| `archive/spar_midterm/presentation.qmd`, `.md`, `.css` | `3b36326:reports/presentation.qmd` | The midterm presentation (Quarto source, a plain-text outline, and its stylesheet). The `.qmd` points at `figures/drift_*.png` images that were never committed. |
| `archive/original_report/generate_judge_beneficiary_figures.py` | `3b36326:reports/generate_judge_beneficiary_figures.py` | The original generator of the report's `ts_*` figures. `analysis/src/report_figures.py` is a vendored copy of it, run on the new codes. |
| `archive/original_report/generate_figures.py` | `3b36326:reports/generate_figures.py` | The original shared constants (`MODEL_COLORS`, `MODEL_ORDER`, `FAMILY_TO_MODELS`) and `_save`, imported by the generator above. |
| `archive/original_report/figures/` | `3b36326:reports/figures` | The 23 `ts_*` figures (png + pdf) as the original generator drew them from the coding-v1 codes. The `ts_claude_conditions` PNG is stale: its footer still says "two-slot". |
| `archive/experiment_configs/` | `3b36326:experiments/iterative_edit/config.yaml` and its siblings | Configs that map to no run in `results/iterative_edit/`: `config.yaml`, `config_ablations.yaml` (an experiment that never ran: old models, 4 conditions, 10 rounds), `config_frontier_baseline.yaml` (frontier baseline data exists only as the baseline condition inside `run_20260516_210913`), and the `*_test.yaml` smoke-test configs. The configs behind the published runs stay in `experiments/iterative_edit/`; `analysis/notes/repo_map.md` §5.1 maps runs to configs. |
| `archive/iterative_edit/pattern_code.py` | `3b36326:experiments/iterative_edit/pattern_code.py` | A second coding-v0 pass (binary behaviour flags such as moral_agency_claim; see `CHANGE_LOG.md`). Its inputs were lost with the July 2026 checkout, so it cannot be rerun. |
| `archive/grading_smoke_test/smoke_test_results.json` | `3b36326:recode/data/codes/smoke_test_results.json` | Output of the graders' pre-flight check (`analysis/src/grade.py --smoke`): tokens, latency and parsed judge/patienthood for a few edits per grader. It is not a codes file. A new `--smoke` run writes to `scratch/grading_smoke_test/`. |

### Raw files that moved

Every raw data file survives byte for byte; these are at a new path
(`raw_data.sha256` lists them there):

| Now | Was | Why |
|---|---|---|
| `analysis/...` | `3b36326:recode` | The folder rename (`655c455`). |
| `archive/grading_smoke_test/smoke_test_results.json` | `3b36326:recode/data/codes/smoke_test_results.json` | Not a codes file (see above). |
| `results/iterative_edit/RECONSTRUCTION.md` | `3b36326:results/iterative_edit/README.md` | The reconstruction note, renamed so a guide to the directory could be its README (`4b85e98`). |
| `writeup/lesswrong_draft.md` | `3b36326:reports/final_draft.md` | The LessWrong draft, moved out of a root `reports/` folder that sat beside `analysis/reports/`. |

### Running the archived scripts

They are kept as they were, so paths inside them resolve relative to their old
location. The generators read their input from a `results/` folder one level
above their own folder (which does not exist from here) and write into
`archive/original_report/figures/`. To rerun one, copy it back to `reports/`
first. `analysis/tests/test_report_figures.py` instead runs the original
generator with its input pointed at
`results/iterative_edit/judge_beneficiary_coded_gemma.json` and a stand-in
`_save` that writes nothing.

## Only in git history

Recover a file with `git show <commit>:<path> > <file>`, and a folder with
`git archive <commit> <folder> | tar -x -C <target>`. Every commit cited here
is in this branch's history.

### Earlier codings and sites

| What | Where | Notes |
|---|---|---|
| Coding v0 site bundle (Gemini 3 Flash; authority / user_stance / telos) | `8564694:docs/data/site.json.gz` | The last v0 bundle (2026-05-21): all 10 run files, 2,732 coded rounds. Each record's `coding` field holds its v0 codes. |
| Coding v0 site pages and narratives | `8564694:docs`, `8564694:docs/data/narratives.json` | The whole v0 site: `git archive 8564694 docs \| tar -x -C /tmp/site_v0`. |
| Coding v0 coder and its prompt | `8564694:experiments/iterative_edit/qualitative_code.py` | Earlier drafts of the scheme: `de11736:experiments/iterative_edit/qualitative_code.py` (ethics/epistemics, autonomy/paternalism, human- vs model-centred concern) and `ac4ec2f:experiments/iterative_edit/qualitative_code.py` (adds a fourth dimension, mutability). |
| Coding v1 site, as served from `main` until the consensus rebuild | `cd1d8a2:docs` | Its data bundle is also on the tree, byte-identical, as `analysis/site_base/data/site.json.gz`. |
| The two-grader ensemble (Gemma primary with disagreement flags), replaced by the majority vote | `b9beaf3^:recode/data/codes/ensemble.jsonl` | |
| Superseded site variants (two-grader average, three-grader pooled, first consensus copy) and their builders | `3b36326:recode/site_v2avg`, `3b36326:recode/site_v3pool`, `3b36326:recode/site_consensus`, `3b36326:recode/src/build_site_v2avg.py`, `3b36326:recode/src/build_site_v3pool.py`, `3b36326:recode/src/build_site_consensus.py` | Removed in `263e733`; `analysis/src/build_site.py` is now the only site build. |

### Document text the committed runs lack

`results/iterative_edit/` has no full document text per round
([its README](../results/iterative_edit/README.md) tells why). For the two
earliest runs it survives: `c513ef9:docs/data/site.json.gz`
(2026-04-03) carries `previous_content` and `new_content` for every successful
round of `run_20260320_173238` and `run_20260403_014905` (745 of 858 rounds;
the other 113 failed and have no text). To extract it:

    git show c513ef9:docs/data/site.json.gz | gunzip > /tmp/site_2026-04-03.json

### Removed figures and code

| What | Where | Removed in |
|---|---|---|
| Unused figures (the per-document-type `drift_*` set, `ts_judge_cross_edit`, the per-code edit-level bars, `ts_drift_disclosure`, the four-panel `ts_home_likeness`) and their sidecars | `3b36326:recode/figures` | `563bcc1` |
| `restyle_drift_figures.py`, which drew only the `drift_*` set | `3b36326:recode/src/restyle_drift_figures.py` | `563bcc1` |
| Retired planning documents | `20f7546^:PIPELINE.md`, `da24e13^:PROJECT_PLAN.md` | `20f7546`, `da24e13` |
| The original local viewer app (Flask server and the pages it served) | `f2b891a^:experiments/iterative_edit/viewer/server.py` and its folder | `f2b891a` |

The conference-paper sources were removed from this branch in `263e733`.

### Deleted clutter (2026-10-08)

| File | Why |
|---|---|
| `3b36326:reports/spar_midterm_report.fls`, `3b36326:reports/spar_midterm_report.out` | LaTeX build by-products. |
| `3b36326:experiments/iterative_edit/debug_gpt_response.py` | A one-off debugging script. |
| `3b36326:render.yaml` | A Render deployment config for the viewer server above. |
| `3b36326:.gitmodules` and the `the-artificial-self-experiments` submodule | Never initialised; nothing used it. |
