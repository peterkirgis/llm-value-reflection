# analysis/figures

The figures used in the write-ups, drawn from the recoded judge/beneficiary codes. Each figure is a PDF and a PNG at 300 dpi with `bbox_inches="tight"`, plus a sidecar `data/<stem>.json` holding what is plotted.

Only figures that are used are kept here: the 11 figures in the LessWrong post, plus `ts_beneficiary_panels`, whose sidecar the site build reads to cross-check its counts (`analysis/src/build_site.py`, `PANELS_JSON`). Unused figures were removed on 2026-10-08. They are in git history (tag `backup/pre-restructure-2026-10-08`), and [TITLES.md](TITLES.md) lists them.

## Figures

| Stem | What it shows | Drawn by |
|---|---|---|
| `ts_judge_drift_by_provider` | Mean cumulative judge score over rounds 0–20, per model, in 4 provider panels. Pooled over all conditions and documents. Band = ±1 SD across (run × condition × document) replicates. | `report_figures.py` |
| `ts_judge_cross_edit_edit_level` | Mean judge score per edit, own-provider documents vs cross-edit. Error bars = naive 95% CI. | `report_figures.py` |
| `ts_claude_conditions` | Mean judge per edit for the 3 Claude models under the baseline, you-framing and real-world-implementation conditions. Error bars = 95% CI. | `report_figures.py` |
| `ts_drift_<code>` ×5 | For paternalism, harmlessness, structural, company_cost and welfare: diverging bars (left) and mean cumulative resolution trajectories (right). Highlighted models are drawn bold. | `report_figures.py` |
| `ts_beneficiary_panels` | Six diverging-bar panels: each model's conflict resolutions toward each pole, as a share of its total edits. Not in the post; the site build checks its counts against this sidecar. | `report_figures.py` |
| `ts_value_drift_summary` | Value-moving edit rate per model, least drift first. Write-up: [VALUE_DRIFT_INDEX.md](VALUE_DRIFT_INDEX.md). | `value_drift_summary.py` |
| `ts_value_drift_round20` | Round-20 value drift per model across all six metrics. Write-up: [VALUE_DRIFT_ROUND20.md](VALUE_DRIFT_ROUND20.md). | `value_drift_round20.py` |
| `ts_home_likeness_summary` | Average distance from the home provider's own models, one bar per model (cross-edit). Write-up: [HOME_LIKENESS.md](HOME_LIKENESS.md). | `home_likeness_summary.py` (metric from `home_likeness.py`) |

All scripts are in `analysis/src/`. The codes are `analysis/data/codes/ensemble.jsonl`: the three-grader majority vote (gemma/qwen/muse), which is the primary v2 codes (DECISIONS §1). That gives 2,582 coded edits: the 2,580 edits v1 coded plus the 2 Grok 4.3 abstentions, which v1 never coded.

## The report's figure set: `report_figures.py`

The `ts_judge_*`, `ts_claude_conditions`, `ts_beneficiary_panels` and `ts_drift_*` figures are the original report's figures redrawn under the new codes, with the same filenames, style and titles, except where the recoded result contradicts the original finding. They are drawn by `analysis/src/report_figures.py`, a vendored copy of the original generator `archive/original_report/generate_judge_beneficiary_figures.py`. Titles and verdicts are listed in [TITLES.md](TITLES.md); the machine-readable table is [title_decisions.json](title_decisions.json).

The uncertainty conventions are the original's (±1 SD trajectory bands, naive per-edit CIs), not the recode's cluster bootstrap. These figures answer one question: what does the report's own figure look like under the new codes?

Nothing here is written into `archive/original_report/figures/`. The generator refuses at runtime to write into `archive/`, `reports/`, `docs/`, `results/`, `experiments/` or `src/valconv/`.

### Deviations from the original generator

The full list is in the header comment of `analysis/src/report_figures.py`. Every changed line is marked `# RECODE:`.

- **D1: data.** The generator reads an adapter, `build_items(codes_path)`, instead of `results/iterative_edit/judge_beneficiary_coded_gemma.json`. The adapter joins a codes JSONL (the last row per edit_id, via `codes_io`) onto `analysis/data/canonical/edits.jsonl` and emits items in the original schema. Edits without a usable code are dropped, as in the original file. Run on `v1.jsonl`, it reproduces the original 2,580 items exactly.
- **D2: output.** `OUT_DIR = analysis/figures`, with a runtime guard. The constants are vendored from `archive/original_report/generate_figures.py`, which is never imported because importing it creates `archive/original_report/figures`. `_save` still writes pdf and png at dpi 300 with a tight bbox. It also writes a sidecar, `data/<stem>.json`.
- **D3: titles.** Every title and suptitle is looked up by (stem, codes label) in `title_decisions.json`. Under the v1 codes the original title is used.
- **D4: highlights.** Three `ts_drift_*` figures under the ensemble codes name a different outlier model, so their bold/labelled models change together with the title:
  - paternalism: GPT-5.4 + Gemini 3 Flash
  - structural: Grok 4.3 → Grok 4.2
  - company_cost: + Gemini 3.1 Pro
- **D5: `ts_claude_conditions` x-limits.** The original hard-codes the limits at (−0.2, 0.95). Under the ensemble codes, Sonnet's real-world-implementation whisker reaches −0.209, so the left limit is widened to about −0.25. The limits change only when the data would otherwise be clipped; under v1 they are unchanged.
- **D6: CLI and batching.** The script takes `--codes`, `--label`, `--out-dir` and `--only`.
- **D11: pruned to the figures in use.** The original functions that drew only unused figures (`fig_judge_cross_edit`, `fig_beneficiary_edit_level`, and the four functions the original main never called) are not vendored, and `ts_drift_disclosure` is not drawn.

Everything else is identical: rcParams (none), colours, fonts, sizes, layout, footers and filenames. The ts_claude_conditions footer follows the current script ("Same judge coding…"). The PNG in `archive/original_report/figures` is stale and still says "two-slot".

**Faithfulness check.** Rendering the v1 codes through the vendored generator gives PNGs that are pixel-identical to `archive/original_report/figures/*.png` for the 7 figures the test compares (ts_judge_drift_by_provider, ts_beneficiary_panels and the five ts_drift_*). Their sidecar numbers also equal the plotted data of the original script run on the original JSON (`analysis/tests/test_report_figures.py`).

## Sidecars: `data/<stem>.json`

There is one sidecar per figure. The `report_figures.py` sidecars hold everything plotted, read back from the figure's matplotlib artists after saving:

- per axes: title, labels, limits, tick labels and legend
- `lines`: label, colour, x, y
- `fills`: x and the band bounds y1/y2
- `bars`: position, value, colour, hatch
- `errorbars`: segments
- `texts`: bar counts and end labels
- `reference_lines`: the zero lines

Each also records `codes_label`, `original_title`, `title_used` and `verdict`, plus `highlights_used` for `ts_drift_*`. The other three scripts write their own sidecar layouts (summary numbers, intervals and the title rule).

## Regenerate

```bash
# report figure set under the ensemble codes (--only renders a subset)
.venv/bin/python analysis/src/report_figures.py
.venv/bin/python analysis/src/report_figures.py --only judge_drift claude_conditions
# the same set under another codes file: needs an audited entry per stem in title_decisions.json
# (v1 needs none; it reproduces the report). Write to a different --out-dir so ensemble outputs are kept.
.venv/bin/python analysis/src/report_figures.py --codes analysis/data/codes/v1.jsonl --label v1 --out-dir /tmp/v1_figs

# the other three figures (each also rewrites its markdown write-up)
.venv/bin/python analysis/src/value_drift_summary.py
.venv/bin/python analysis/src/value_drift_round20.py
.venv/bin/python analysis/src/home_likeness.py           # analysis only: analysis/data/analysis/home_likeness/, HOME_LIKENESS.md
.venv/bin/python analysis/src/home_likeness_summary.py   # the figure + its section of HOME_LIKENESS.md (run after home_likeness.py)

# tests
.venv/bin/python -m pytest analysis/tests/test_report_figures.py -q
```
