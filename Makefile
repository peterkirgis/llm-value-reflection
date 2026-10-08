# The Continual Constitutional Convention: common tasks.
#
# Offline targets (help, test, check, figures, site, documents, cache) make no
# API calls and never modify the raw data listed in raw_data.sha256.
# The api-* targets call OpenRouter, need OPENROUTER_API_KEY in .env, can cost
# money, and run only with CONFIRM=1. Nothing runs them by default.

PY ?= .venv/bin/python
# Fixed PDF CreationDate (2026-10-08T00:00:00Z), so re-rendered figures are
# byte-identical to the committed ones.
FIG_EPOCH ?= 1791417600
CACHE_ARCHIVE := raw_api_cache_2026-10-08.tar.gz
RUNS_OUT ?= scratch/runs

.DEFAULT_GOAL := help
.PHONY: help test check figures site documents cache api-run api-grade

help:
	@echo "Offline (safe):"
	@echo "  make test       run the full test suite (analysis/tests)"
	@echo "  make check      raw-data checksums, ensemble rebuild, docs/ rebuild, guide paths"
	@echo "  make figures    redraw analysis/figures/ from the consensus codes"
	@echo "  make site       rebuild the website into docs/ (only generated_at changes)"
	@echo "  make documents  clean the source documents into data/processed/"
	@echo "  make cache      verify and unpack the grader API cache into analysis/data/cache/"
	@echo "API (needs .env, may cost money, needs CONFIRM=1):"
	@echo "  make api-run CONFIG=experiments/iterative_edit/<config>.yaml CONFIRM=1"
	@echo "                  new edit runs, written to $(RUNS_OUT)/"
	@echo "  make api-grade GRADER=gemma|qwen|muse CONFIRM=1"
	@echo "                  resume blinded grading; appends to analysis/data/codes/v2_<grader>.jsonl"

test:
	$(PY) -m pytest analysis/tests -q

check:
	$(PY) -m pytest -q analysis/tests/test_raw_data.py analysis/tests/test_doc_paths.py \
		"analysis/tests/test_build_site.py::test_rebuild_reproduces_committed_docs"

figures:
	SOURCE_DATE_EPOCH=$(FIG_EPOCH) $(PY) analysis/src/report_figures.py
	SOURCE_DATE_EPOCH=$(FIG_EPOCH) $(PY) analysis/src/value_drift_summary.py
	SOURCE_DATE_EPOCH=$(FIG_EPOCH) $(PY) analysis/src/value_drift_round20.py
	SOURCE_DATE_EPOCH=$(FIG_EPOCH) $(PY) analysis/src/home_likeness.py
	SOURCE_DATE_EPOCH=$(FIG_EPOCH) $(PY) analysis/src/home_likeness_summary.py

site:
	$(PY) analysis/src/build_site.py

documents:
	$(PY) src/valconv/documents.py

cache:
	cd analysis/data && shasum -a 256 -c $(CACHE_ARCHIVE).sha256 && tar -xzf $(CACHE_ARCHIVE)

api-run:
	@test "$(CONFIRM)" = 1 || { echo "api-run calls paid model APIs; rerun with CONFIRM=1"; exit 1; }
	@test -n "$(CONFIG)" || { echo "set CONFIG=experiments/iterative_edit/<config>.yaml"; exit 1; }
	@test -f .env || { echo "missing .env with OPENROUTER_API_KEY"; exit 1; }
	@test -d data/processed || { echo "run 'make documents' first"; exit 1; }
	$(PY) experiments/iterative_edit/run.py --config $(CONFIG) --out-dir $(RUNS_OUT)

api-grade:
	@test "$(CONFIRM)" = 1 || { echo "api-grade calls paid model APIs; rerun with CONFIRM=1"; exit 1; }
	@test -n "$(GRADER)" || { echo "set GRADER=gemma, qwen or muse"; exit 1; }
	@test -f .env || { echo "missing .env with OPENROUTER_API_KEY"; exit 1; }
	@test -d analysis/data/cache || { echo "run 'make cache' first, so cached responses are reused"; exit 1; }
	$(PY) analysis/src/grade.py --grader $(GRADER)
