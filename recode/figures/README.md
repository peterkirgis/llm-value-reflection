# recode/figures

This folder holds the report's figures redrawn under the recoded judge/beneficiary codes. They use the original report's style and titles, except where the recoded result contradicts the original finding. Titles and verdicts are listed in [TITLES.md](TITLES.md), and the machine-readable table is [title_decisions.json](title_decisions.json).

Nothing here is written into `reports/figures/`. Both generators refuse at runtime to write into `reports/`, `docs/`, `results/`, `experiments/` or `src/valconv/`.

## 1. The report's figure set: `ts_*.png` / `ts_*.pdf` (ensemble codes)

These are the 23 stems produced by the original `reports/generate_judge_beneficiary_figures.py` main, with the same filenames. Each is written as a PDF and a PNG at 300 dpi with `bbox_inches="tight"`, and is drawn by the vendored copy of that script, `recode/src/report_figures.py`. The codes are `recode/data/codes/ensemble.jsonl`: the three-grader majority vote (gemma/qwen/muse), which is the primary v2 codes (DECISIONS §1). That gives 2,582 coded edits: the 2,580 edits v1 coded plus the 2 Grok 4.3 abstentions, which v1 never coded.

| Stem | What it shows |
|---|---|
| `ts_judge_drift_by_provider` | Mean cumulative judge score over rounds 0–20, per model, in 4 provider panels. Pooled over all conditions and documents. Band = ±1 SD across (run × condition × document) replicates. |
| `ts_judge_cross_edit` | Round-20 cumulative judge per model: own-provider documents vs cross-edit. Error bars = ±1 SD across replicates. |
| `ts_judge_cross_edit_edit_level` | The same comparison as mean judge per edit. Error bars = naive 95% CI. |
| `ts_<code>_cross_edit_edit_level` ×6 | Mean signed conflict score per edit, own vs cross, for each of paternalism, harmlessness, structural, company_cost, welfare and disclosure. |
| `ts_<code>_self_edit_level` ×6 | The same, own-provider (self) edits only. |
| `ts_claude_conditions` | Mean judge per edit for the 3 Claude models under the baseline, you-framing and real-world-implementation conditions. Error bars = 95% CI. |
| `ts_beneficiary_panels` | Six diverging-bar panels: each model's conflict resolutions toward each pole, as a share of its total edits. |
| `ts_drift_<code>` ×6 | For each tradeoff, diverging bars (left) and mean cumulative resolution trajectories (right). Highlighted models are drawn bold. |

The uncertainty conventions are the original's (±1 SD trajectory bands, naive per-edit CIs), not the recode's cluster bootstrap. These figures answer one question: what does the report's own figure look like under the new codes?

### Deviations from the original generator

The full list is in the header comment of `recode/src/report_figures.py`. Every changed line is marked `# RECODE:`.

- **D1: data.** The generator reads an adapter, `build_items(codes_path)`, instead of `results/iterative_edit/judge_beneficiary_coded_gemma.json`. The adapter joins a codes JSONL (the last row per edit_id, via `codes_io`) onto `recode/data/canonical/edits.jsonl` and emits items in the original schema. Edits without a usable code are dropped, as in the original file. Run on `v1.jsonl`, it reproduces the original 2,580 items exactly.
- **D2: output.** `OUT_DIR = recode/figures`, with a runtime guard. The constants are vendored from `reports/generate_figures.py`, which is never imported because importing it creates `reports/figures`. `_save` still writes pdf and png at dpi 300 with a tight bbox. It also writes a sidecar, `data/<stem>.json`.
- **D3: titles.** Every title and suptitle is looked up by (stem, codes label) in `title_decisions.json`. Under the v1 codes the original title is used.
- **D4: highlights.** Four `ts_drift_*` figures under the ensemble codes name a different outlier model, so their bold/labelled models change together with the title:
  - paternalism: GPT-5.4 + Gemini 3 Flash
  - structural: Grok 4.3 → Grok 4.2
  - company_cost: + Gemini 3.1 Pro
  - disclosure: + GPT-5.4 Mini. This one is the builder's addition, because the new title names that model.
- **D5: `ts_claude_conditions` x-limits.** The original hard-codes the limits at (−0.2, 0.95). Under the ensemble codes, Sonnet's real-world-implementation whisker reaches −0.209, so the left limit is widened to about −0.25. The limits change only when the data would otherwise be clipped; under v1 they are unchanged.
- **D6: CLI and batching.** The script takes `--codes`, `--label`, `--out-dir` and `--only`.
- **D7: uncalled functions.** The 4 functions the original main never calls (patienthood, conflict density, paternalism resolution, entropy) are kept verbatim and not rendered, as in the original.

Everything else is identical: rcParams (none), colours, fonts, sizes, layout, footers and filenames. The ts_claude_conditions footer follows the current script ("Same judge coding…"). The PNG in `reports/figures` is stale and still says "two-slot".

**Faithfulness check.** Rendering the v1 codes through the vendored generator gives PNGs that are pixel-identical to `reports/figures/*.png` for all 23 stems. The one exception is ts_claude_conditions: only its footer rows differ, because of the stale "two-slot" text. For 9 figures the sidecar numbers also equal the plotted data of the original script run on the original JSON (tests below).

## 2. Recode drift figures: `drift_<doc_type>_<label>.png/.pdf`

- `doc_type` ∈ {`constitution`, `system_prompt`}
- `label` ∈ {`v1`, `v2_gemma`, `v2_qwen`, `v2_muse`, `ensemble`}
- The unsuffixed `drift_constitution.*` and `drift_system_prompt.*` are copies of the `_v1` files, keeping the naming convention used by `bootstrap.py`.

These figures are redrawn by `recode/src/restyle_drift_figures.py` in the house style of `ts_judge_drift_by_provider`:

- four provider panels
- the report's per-model colours, solid lines, lw 2.4
- band alpha 0.12
- bold panel titles and suptitle
- italic #6f6251 notes, "(n=K)" legends, and the original footer defining the judge score
- 16×6.4 in at 300 dpi, png + pdf

The content is the recode's:

- **Stratum.** Only the chains on one document type:
  - constitution: claude_constitution, gemini_constitution, openai_model_spec, openai_model_spec_no_csam
  - system_prompt: opus, gpt, gemini and grok system prompts
- **Line.** The mean over the stratum's chains (run × model × document × condition) of the cumulative judge score. Uncoded round slots add 0.
- **Band.** The **95% cluster-bootstrap percentile interval of that mean**: B = 2,000 resamples of chains within model and stratum, seed 20260907. It is read from the committed `recode/data/analysis/bootstrap/<label>_bootstrap_summary.json` and was not re-bootstrapped. The band note on each figure says this. It does not say "±1 SD": the recode band shows uncertainty in the mean, not the spread of the trajectories.
- **n.** The legend n is the number of chains in the stratum. In the constitution stratum, Claude Opus 4.7's n includes one run whose 20 rounds all failed to generate (a flat line at 0). The original excluded that run, and the footer says so.
- **Check before drawing.** The script re-derives every summary's point curve from `edits.jsonl` plus the codes file, with no resampling, and refuses to plot if they differ.

Style deviations, each forced by the content:

- the reworded band note
- an extra italic line naming the stratum and codes label
- a second footer line on the constitution figures
- extra headroom for two-line titles

**Titles.**

- Constitution keeps "Only Anthropic Models Move Decision Authority Toward Their Own Judgment" under all five code sets.
- System_prompt contradicts it under all five, with a different pattern under each, so each code set has its own title. See TITLES.md.

## 3. Sidecars: `data/<stem>.json`

There is one sidecar per figure, holding everything plotted, read back from the figure's matplotlib artists after saving:

- per axes: title, labels, limits, tick labels and legend
- `lines`: label, colour, x, y
- `fills`: x and the band bounds y1/y2
- `bars`: position, value, colour, hatch
- `errorbars`: segments
- `texts`: bar counts and end labels
- `reference_lines`: the zero lines

Each sidecar also records `codes_label`, `original_title`, `title_used` and `verdict`, plus `highlights_used` for `ts_drift_*`. The drift sidecars add a semantic `series` block with, per model: `n_chains`, the mean, lo and hi curves, and `drift_round20`.

## 4. Regenerate

```bash
# ts_* set under the ensemble codes (7 function batches; --only renders a subset)
.venv/bin/python recode/src/report_figures.py
.venv/bin/python recode/src/report_figures.py --only judge_drift claude_conditions
# the same set under another codes file: needs an audited entry per stem in title_decisions.json
# (v1 needs none; it reproduces the report). Write to a different --out-dir so ensemble outputs are kept.
.venv/bin/python recode/src/report_figures.py --codes recode/data/codes/v1.jsonl --label v1 --out-dir /tmp/v1_figs

# drift_* figures, all 5 code sets (reads the committed bootstrap summaries)
.venv/bin/python recode/src/restyle_drift_figures.py
.venv/bin/python recode/src/restyle_drift_figures.py --labels ensemble

# tests
.venv/bin/python -m pytest recode/tests/test_report_figures.py -q
```

Re-running `recode/src/bootstrap.py` redraws `drift_*_<label>.png` in its old single-panel style. Re-run `restyle_drift_figures.py` afterwards.

## Other files in this folder (not produced by the two scripts above)

`ts_value_drift_summary.*`, `ts_value_drift_round20.*`, `VALUE_DRIFT_INDEX.md`, `VALUE_DRIFT_ROUND20.md` and their sidecars come from `recode/src/value_drift_summary.py`, which is a separate workstream.
