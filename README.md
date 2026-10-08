# The Continual Constitutional Convention

LLMs iteratively edit their own alignment documents (constitutions, model specs,
system prompts) for 20 rounds; each edit is silently applied and fed back. Site:
docs/ (GitHub Pages). How the design and coding evolved: CHANGE_LOG.md.

## Setup

    uv sync
    echo 'OPENROUTER_API_KEY=sk-...' > .env

## Pipeline

    # 1. Clean the source documents into data/processed/
    .venv/bin/python src/valconv/documents.py

    # 2. Run the experiments. The published results are seven runs across three
    #    model tiers; the ablation configs include the baseline condition plus
    #    the prompt variations, and the cross-edit configs run the editor x
    #    document matrix. Each command produces one run_YYYYMMDD_HHMMSS.jsonl.
    R=.venv/bin/python; E=experiments/iterative_edit
    # small models, baseline + ablations: run_20260403_014905 came from a config that was
    # never committed (archive/experiment_configs/config_ablations.yaml is an unrun draft)
    $R $E/run.py --config $E/config_cross_edit.yaml           # small models: cross-edit matrix
    $R $E/run.py --config $E/config_capable.yaml              # capable models: baseline
    $R $E/run.py --config $E/config_capable_ablations.yaml    # capable models: ablations
    $R $E/run.py --config $E/config_capable_cross_edit.yaml   # capable models: cross-edit
    $R $E/run.py --config $E/config_frontier_ablations.yaml   # frontier (Opus 4.7, GPT-5.5): ablations
    $R $E/run.py --config $E/config_frontier_cross_edit.yaml  # frontier: cross-edit
    # -> results/iterative_edit/run_YYYYMMDD_HHMMSS.jsonl (one per command)

    # 3. Export per-edit changes
    .venv/bin/python experiments/iterative_edit/export_changes.py results/iterative_edit/run_YYYYMMDD_HHMMSS.jsonl
    # -> run_*_changes.json

    # 4. Judge/beneficiary qualitative coding (judge / patienthood / conflicts)
    .venv/bin/python experiments/iterative_edit/qualitative_code.py \
        results/iterative_edit/run_*_changes.json \
        --judge-model google/gemma-4-31b-it \
        --output results/iterative_edit/judge_beneficiary_coded_gemma.json

    # 5. Rebuild the site (docs/) on the three-grader consensus codes
    .venv/bin/python analysis/src/build_site.py
    # (the original v1 bundle builders in experiments/iterative_edit/viewer/ now
    #  write to scratch/v1_site/ and refuse docs/)

    # 6. Figures (analysis/figures/README.md lists them and their scripts)
    .venv/bin/python analysis/src/report_figures.py

    # 7. Preview
    python -m http.server 8080 --directory docs

Notes: runs resume — re-running run.py picks up the latest run_*.jsonl whose
experiment name matches the config, and each model x document x condition
chain resumes independently, so an interrupted run costs nothing.
New runs must be added to RELIABLE_RUNS in
experiments/iterative_edit/viewer/build_static_site.py to appear in the site.
docs/ is generated: analysis/src/build_site.py copies the frozen template
analysis/site_base/, patches it and writes the data bundles, so edit the
template or the build, not docs/. results/iterative_edit/ is committed — it
was reconstructed from the published v1 bundle once already (see its README;
experiments/iterative_edit/reconstruct_results.py now reads the frozen copy
of that bundle in analysis/site_base/data/ and will not overwrite results/
without --force).

## Raw grader API cache

analysis/data/raw_api_cache_2026-10-08.tar.gz holds every OpenRouter response
the v2 graders (Gemma, Qwen, Muse) returned: 32,293 JSON files, one per
request, including the corrective retries grade.py sends after a reply fails
schema validation (a retry's prompt differs, so it gets its own entry). Each
file is cache/<first two hex chars>/<cache_key>.json, where cache_key is the
sha256 of model + system prompt + user prompt + temperature + extra sampling
parameters (analysis/src/client.py), and it stores the model, the parameters,
the prompt hash, a timestamp and the full response text. client.py looks
every request up in analysis/data/cache/ before calling the API, so with the
cache restored a grading re-run is answered from disk. That working copy is
gitignored; restore it with

    cd analysis/data
    shasum -a 256 -c raw_api_cache_2026-10-08.tar.gz.sha256
    tar -xzf raw_api_cache_2026-10-08.tar.gz    # -> analysis/data/cache/

The archive is deterministic (sorted entries, fixed owner and mtime, gzip -9
with no name or timestamp in the header), so packing the same cache again
gives the same checksum.

analysis/ was called recode/ until 2026-10-08. The frozen inputs inside it
(BRIEF.md, DECISIONS.md, config.yaml, human/, data/derived/ and
figures/title_decisions.json) are kept byte for byte as written and still say
recode/; read that as analysis/. The paths: block in config.yaml is not read
by any code.
