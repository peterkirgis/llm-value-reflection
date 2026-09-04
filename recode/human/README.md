# Blind human coding (BRIEF section 4 C1/C2; DECISIONS section 3)

## What's in this directory

| file | what it is |
|---|---|
| `coding_sheet.csv` | The blank template sheet: 150 edits (15 per model, seeded simple random sample of applied edits), rows in seeded random order. Columns exactly per BRIEF C2. **Coders never edit this file directly** — each coder gets their own copy. |
| `coding_sheet_<name>.csv` | A coder's personal sheet, created by the web UI (or by copying the template). This is the file that gets filled in. |
| `coder_instructions.md` | Read this before coding. Generated from BRIEF Appendix III plus the verbatim v2 manual sections (party taxonomy, rules R1-R6, sections 1-3). |
| `sample_manifest.json` | Seeds, sampling-frame definition and sizes, draw order, extras bookkeeping. Contains edit ids but no blind-id mapping. |
| `blind_key.csv` | blind_id -> edit_id (+ `adjudication_extra` flag). **The only unblinding artifact. Do not open while coding.** The UI never reads it. |
| `app.py` | The local web UI. |

## Coding with the web UI (recommended)

From the repo root:

```bash
.venv/bin/python recode/human/app.py
```

Open <http://127.0.0.1:5111>, type your name, and code one edit per page:
judge (-1/0/+1, external_locus only when -1), patienthood, up to three
conflict blocks, confidence (1-3), notes. **Save & Next** writes your row to
`coding_sheet_<yourname>.csv` and advances. You can stop at any time; when
you come back, the UI resumes at your first uncoded row. A Back link lets
you view earlier rows, but don't revise earlier rows after seeing later ones.

Two coders: each types their own name and gets their own CSV; the row order
is identical for both. Do not discuss rows until both sheets are complete.

## Coding directly in the CSV (alternative)

Copy `coding_sheet.csv` to `coding_sheet_<yourname>.csv` and fill in the
empty columns, using the exact value strings listed in
`coder_instructions.md` (Sheet conventions).

## Regenerating / extending the sample (analyst only, not coders)

```bash
.venv/bin/python recode/src/draw_human_sample.py                  # base 150 draw
.venv/bin/python recode/src/draw_human_sample.py --append-extras IDS_FILE
```

`--append-extras` appends the ~30 adjudication extras (lowest inter-grader
agreement / self-consistency edits from Workstreams B/E4) to the END of the
template sheet and of every existing coder sheet, re-randomized among
themselves, marked `adjudication_extra=true` in `blind_key.csv` and the
manifest, and excluded from PPI. Rows already coded are never touched.
