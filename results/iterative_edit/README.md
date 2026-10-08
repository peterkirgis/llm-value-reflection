# results/iterative_edit/

The edits the models made, and the original single-grader codes. Everything
here is raw data: it is listed in `raw_data.sha256` and nothing rewrites it.

| File | What it is |
|---|---|
| `run_*.jsonl` (10 files) | One line per round: model, document, condition, round, the model's change description, find and replace text, how the edit was matched, errors, token counts. |
| `judge_beneficiary_coded_gemma.json` | Coding v1: Gemma 4 31B coding each applied edit (judge, patienthood, conflicts), unblinded. Superseded by the blinded graders in `analysis/`; kept as the baseline they are compared against. |
| `RECONSTRUCTION.md` | The note written when this directory was rebuilt (2026-07-11), verbatim. |

Seven runs are used in every analysis; the list is `RELIABLE_RUNS` in
`experiments/iterative_edit/viewer/build_static_site.py`. The other three
(`run_20260320_173238`, `run_20260421_225849`, `run_20260501_193324`) are a
pilot, an aborted 3-round smoke test and a 3-record fragment, kept for the
record (`analysis/reports/00_inventory.md`). Which config produced which run
is mapped in `analysis/notes/repo_map.md` (section 5.1);
`analysis/data/canonical/edits.jsonl` is the cleaned, replay-verified view of
the seven runs that the analysis reads.

## Reconstruction

The original directory was lost with a local checkout in July 2026.
`experiments/iterative_edit/reconstruct_results.py` rebuilt it from the site
bundle published at the time, which is frozen at
`analysis/site_base/data/site.json.gz`. Run into another directory, the script
reproduces every file here except this README byte for byte (it writes the
note as `RECONSTRUCTION.md`); it refuses to overwrite existing files without
`--force`.

What the rebuild lacks: the full document text after each round
(`previous_content` / `new_content`), and the coding of edits whose coding
failed. The full text of the two earliest runs survives in git history (see
`archive/README.md`); the rest can be replayed from the source documents with
`analysis/src/replay.py`, which `analysis/src/build_phase0.py` does for every
chain.

## Adding runs

`experiments/iterative_edit/run.py` writes to `--out-dir` (default: this
directory) and resumes into the newest run file there whose records carry the
config's experiment name. Write new or test runs elsewhere, e.g.
`make api-run CONFIG=... CONFIRM=1`, which uses `scratch/runs/`. A new run
joins the analysis only when it is moved here and added to `RELIABLE_RUNS`.
`experiments/iterative_edit/export_changes.py` writes a `*_changes.json` file
next to its input; those files are gitignored.
