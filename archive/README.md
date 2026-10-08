# archive/

Files that are no longer part of the pipeline but are kept for the record: earlier write-ups, the original report's figure generators, and experiment configs that produced no surviving run. Nothing outside `archive/` runs or imports anything in here, except `recode/tests/test_report_figures.py` and `recode/tests/test_home_likeness.py`, which compare the vendored figure code in `recode/src/` against the original generators.

Everything here was moved with `git mv` on 2026-10-08, so `git log --follow <path>` shows each file's earlier history. The full pre-restructure tree is at tag `backup/pre-restructure-2026-10-08`.

## Contents

| Path | Was | What it is |
|---|---|---|
| `spar_midterm/spar_midterm_report.tex`, `.pdf` | `reports/` | The SPAR midterm report (v1 coding scheme). The `.tex` no longer compiles: the `drift_*.pdf` figures it includes from `figures/` were deleted from the repo before this archive was made (commit 06a3cbc). |
| `spar_midterm/presentation.qmd`, `.md`, `.css` | `reports/` | The midterm presentation (Quarto source, a plain-text outline, and its stylesheet). The `.qmd` points at `figures/drift_*.png` images that were never committed. |
| `original_report/generate_judge_beneficiary_figures.py` | `reports/` | The original generator of the report's `ts_*` figures. `recode/src/report_figures.py` is a vendored copy of it, run on the recoded data. |
| `original_report/generate_figures.py` | `reports/` | The original shared constants (`MODEL_COLORS`, `MODEL_ORDER`, `FAMILY_TO_MODELS`) and `_save`, imported by the generator above. |
| `original_report/figures/` | `reports/figures/` | The 23 `ts_*` figures (png + pdf) as the original generator drew them from the v1 codes. The `ts_claude_conditions` PNG is stale: its footer still says "two-slot". |
| `experiment_configs/` | `experiments/iterative_edit/` | Configs that map to no run in `results/iterative_edit/`: `config.yaml`, `config_ablations.yaml` (it describes an experiment that never ran: old models, 4 conditions, 10 rounds), `config_frontier_baseline.yaml` (frontier baseline data exists only as the baseline condition inside `run_20260516_210913`), and the `*_test.yaml` smoke-test configs. The configs behind the published runs stay in `experiments/iterative_edit/`; `recode/notes/repo_map.md` §5.1 maps runs to configs. |
| `iterative_edit/pattern_code.py` | `experiments/iterative_edit/` | The second v1 coding pass (binary behaviour flags such as moral_agency_claim; see `CHANGE_LOG.md`). Its inputs, the `run_*_changes_coded.json` files, were lost with the July 2026 checkout, so it cannot be rerun. |
| `grading_smoke_test/smoke_test_results.json` | `recode/data/codes/` | Output of the v2 graders' pre-flight check (`recode/src/grade.py --smoke`): per-call tokens, latency and parsed judge/patienthood for a few edits per grader. It is not a codes file. A new `--smoke` run writes to `recode/data/codes/` again. |

## Running the archived scripts

They are kept as they were, so paths inside them resolve relative to their old location. The generators look for their input one directory up from their own folder (`archive/results/...` from here) and write into `archive/original_report/figures/`. To rerun one, copy it back to `reports/` first. `recode/tests/test_report_figures.py` instead execs the original generator with its input path pointed at `results/iterative_edit/judge_beneficiary_coded_gemma.json` and a stand-in `_save` that writes nothing.

## Deleted rather than archived (2026-10-08)

These are in git history only:

- `reports/spar_midterm_report.fls`, `.out`: LaTeX build by-products.
- `experiments/iterative_edit/debug_gpt_response.py`: a one-off debugging script.
- `render.yaml`: a Render deployment config for `experiments/iterative_edit/viewer/server.py`, which no longer exists.
- `.gitmodules` and the `the-artificial-self-experiments` submodule: never initialised, and nothing used it.
- `recode/human/coding_sheet_peter.csv`: a byte-identical copy of the blank template `recode/human/coding_sheet.csv`, with no codes entered. The coding UI (`recode/human/app.py`) creates a coder's own sheet when they start.
