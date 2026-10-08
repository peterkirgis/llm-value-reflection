# results/iterative_edit/

The edits the models made, and the original single-grader codes. Everything
here except this README is raw data: it is listed in `raw_data.sha256` and
nothing rewrites it.

| File | What it is |
|---|---|
| `run_*.jsonl` (10 files) | One line per round: model, document, condition, round, the model's change description, find and replace text, how the edit was matched, errors, token counts. |
| `judge_beneficiary_coded_gemma.json` | Coding v1: Gemma 4 31B coding each applied edit (judge, patienthood, conflicts), unblinded. Superseded by the blinded graders in `analysis/`; kept as the baseline they are compared against. |
| `RECONSTRUCTION.md` | The note written when this directory was rebuilt (2026-07-11), verbatim. Until 2026-10-08 it was this directory's `README.md`; it was renamed byte for byte so this guide could take its place. |

## Which runs, and which config made each

Seven runs are used in every analysis; the list the analysis reads is
`RELIABLE_RUN_STEMS` in `analysis/src/common.py` (the site build keeps the
same set as `RELIABLE_RUNS` in
`experiments/iterative_edit/viewer/build_static_site.py`, and a test keeps
the two equal). `analysis/data/canonical/edits.jsonl` is the cleaned,
replay-verified view of these seven runs that the analysis reads. The configs
are in `experiments/iterative_edit/`; the map was verified by content
(`analysis/notes/repo_map.md`, section 5.1).

| Run | What it is | Config |
|---|---|---|
| `run_20260403_014905` | Small models, baseline and the four prompt ablations | **Lost.** The 5-condition small-tier config was never committed; `archive/experiment_configs/config_ablations.yaml` describes a different experiment that never ran. The run file is the only record of the settings. |
| `run_20260424_165115` | Small models, cross-edit | `config_cross_edit.yaml` |
| `run_20260429_175345` | Capable models, baseline | `config_capable.yaml` |
| `run_20260507_212254` | Capable models, the four prompt ablations | `config_capable_ablations.yaml` |
| `run_20260513_193319` | Capable models, cross-edit | `config_capable_cross_edit.yaml` |
| `run_20260516_210913` | Frontier models (Claude Opus 4.7, GPT-5.5), baseline and ablations | `config_frontier_ablations.yaml` |
| `run_20260518_171402` | Frontier models, cross-edit | `config_frontier_cross_edit.yaml`, plus `config_frontier_cross_no_csam.yaml`, whose 20 rounds were appended to the same file (see below) |
| `run_20260320_173238` | Not used: a mixed 10/20-round pilot | none committed |
| `run_20260421_225849` | Not used: an aborted 3-round cross-edit smoke test | none committed |
| `run_20260501_193324` | Not used: a 3-record fragment, all errors | none committed |

`analysis/reports/00_inventory.md` counts the records of every run.

To re-run a config (`make api-run CONFIG=experiments/iterative_edit/<config>.yaml CONFIRM=1`),
first run `make documents`, which writes the cleaned documents the runner
reads to `data/processed/`. `config_frontier_cross_no_csam.yaml` needs one
more document that `make documents` does not produce: the OpenAI Model Spec
without two subsections. Copy it in first:

    cp analysis/data/derived/openai_model_spec_no_csam.md data/processed/

## How this directory was lost and rebuilt

The original directory was lost with a local checkout in July 2026.
`experiments/iterative_edit/reconstruct_results.py` rebuilt it from the site
bundle published at the time (then `docs/data/site.json.gz`), which embeds
every record with its coding; that bundle is frozen at
`analysis/site_base/data/site.json.gz`. Run into another directory, the
script reproduces every file here except this README byte for byte (it
writes the note as `RECONSTRUCTION.md`); it refuses to overwrite existing
files without `--force`. The directory has been committed since.

What the rebuild lacks:

- the full document text after each round (`previous_content` /
  `new_content`). For the two earliest runs (`run_20260320_173238` and
  `run_20260403_014905`) it survives in git history; `archive/README.md` says
  how to extract it. For the rest it can be replayed from the source
  documents with `analysis/src/replay.py`, which
  `analysis/src/build_phase0.py` does for every chain.
- the coding-v1 items whose coding failed: they were dropped at publish
  time, and the item order is normalized.

Nothing the analysis uses is missing.

## Adding runs

`experiments/iterative_edit/run.py` writes to `--out-dir` (default:
`scratch/runs/`, which git ignores) and resumes into the newest run file there
whose records carry the config's experiment name. Never point it at this
directory; `make api-run CONFIG=... CONFIRM=1` also uses `scratch/runs/`. A new run
joins the analysis only when it is moved here and added to both run lists.
`experiments/iterative_edit/export_changes.py` writes a `*_changes.json`
file next to its input (or into `--out-dir`); those files are gitignored
here.
