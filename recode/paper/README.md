# IASEAI'27 submission (AAAI 2027 anonymous-submission template)

`main.pdf` is `reports/final_draft.md` ported into the AAAI 2027 author kit (`reports/AuthorKit27.zip`). The port keeps the draft's wording. The changes the authors asked for are listed in the docstring of `build_paper.py`, and `CITATION_NOTES.md` lists what the citation checks found.

## Rebuild

```
# 1. figures without in-image titles/footers (captions go to figures/captions/*.json)
.venv/bin/python recode/src/report_figures.py --paper --label ensemble --codes recode/data/codes/ensemble.jsonl --only judge_drift beneficiary_drift judge_cross_edit_edit_level claude_conditions beneficiary_panels
.venv/bin/python recode/src/value_drift_summary.py --paper
.venv/bin/python recode/src/value_drift_round20.py --paper
.venv/bin/python recode/src/home_likeness_summary.py --paper

# 2. markdown -> main.tex, then check that the wording is unchanged
.venv/bin/python recode/paper/build_paper.py
.venv/bin/python recode/paper/check_fidelity.py

# 3. compile (from recode/paper/)
pdflatex main && bibtex main && pdflatex main && pdflatex main
```

`main.tex` is generated, so make text edits in `reports/final_draft.md` and rebuild. If you would rather edit the LaTeX directly from here on, edit `main.tex` and stop running `build_paper.py`.

## Files

- `build_paper.py`: the converter. Edit `FOOTNOTES_KEEP` to restore a dropped footnote.
- `check_fidelity.py`: word-level comparison of the draft against `main.tex`.
- `references.bib`: verified bibliography.
- `figures/`: paper renders at printed size (PNG at 300 dpi, text at least 9 pt, lines at least 0.5 pt; PNG because AAAI forbids Type 3 fonts), plus `captions/` and `data/` sidecars. Four figures are in the main text; the rest are in Appendix E (`MAIN_FIGURES` in `build_paper.py`).
- `abstract_openreview.txt`: the abstract as plain text for the OpenReview form.
- `aaai2027.sty`, `aaai2027.bst`: copied unchanged from the author kit.
