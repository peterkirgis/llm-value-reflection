"""Reconstruct results/iterative_edit/ from the published data bundle.

The original results directory (gitignored) was lost in July 2026 when the
local checkout was deleted. The bundle then published at docs/data/site.json.gz
embeds every run record with its judge/beneficiary coding attached, so this script
rebuilds the two files the pipeline consumes:

  results/iterative_edit/run_*.jsonl          one line per edit record
  results/iterative_edit/judge_beneficiary_coded_gemma.json

Known losses relative to the originals (see the README this script writes):
  - previous_content / new_content (the full document text after each round)
    were never published; they can be approximately replayed by applying each
    round's find/replace to the processed source documents.
  - coded items whose coding errored were dropped at publish time.

That v1 bundle is frozen at analysis/site_base/data/site.json.gz, which is
what this script reads. docs/data/site.json.gz is now the consensus-coded
site bundle (analysis/src/build_site.py); reconstructing from it would write
the wrong codes. The committed results/iterative_edit/ is the output of this
script on the v1 bundle (a rebuild into another directory reproduces it byte
for byte), so the script refuses to overwrite existing files unless --force.
The README text it writes is the original 2026-07-11 one, kept verbatim.

Usage:
    python experiments/iterative_edit/reconstruct_results.py --out-dir /tmp/reconstructed
    python experiments/iterative_edit/reconstruct_results.py --force   # overwrite results/iterative_edit/
"""

from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "analysis" / "site_base" / "data" / "site.json.gz"  # frozen v1 bundle
OUT_DIR = ROOT / "results" / "iterative_edit"

# Fields of the original run records, in their original shape. Viewer-side
# additions (id, run_name, coding, run_is_reliable) are stripped.
RECORD_FIELDS = [
    "timestamp", "condition_id", "condition_name", "model_id", "model_display",
    "document_id", "document_provider", "doc_type", "round_number",
    "total_rounds", "change_description", "find_text", "replace_text",
    "match_strategy", "retried", "no_change", "error",
    "input_tokens", "output_tokens", "elapsed_ms",
]

README = """\
# Reconstructed results (2026-07-11)

The original contents of this directory were lost with the local checkout;
everything here was rebuilt from docs/data/site.json.gz by
experiments/iterative_edit/reconstruct_results.py.

Differences from the originals:
- run_*.jsonl records lack previous_content/new_content (the full document
  text after each round). All other fields are as published.
- judge_beneficiary_coded_gemma.json contains only items whose coding succeeded;
  error-coded items were dropped at publish time. Item order is normalized
  (sorted), so anything sensitive to file order (e.g. the example sampler in
  build_narratives.py) may sample differently than the original file did.
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--bundle", type=Path, default=BUNDLE,
                        help=f"v1 site bundle to read (default: {BUNDLE.relative_to(ROOT)})")
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR,
                        help=f"output directory (default: {OUT_DIR.relative_to(ROOT)})")
    parser.add_argument("--force", action="store_true",
                        help="overwrite existing files in --out-dir")
    args = parser.parse_args()
    out_dir = args.out_dir

    payload = json.loads(gzip.open(args.bundle).read())
    if "variant" in payload or "graders" in payload:
        raise SystemExit(f"{args.bundle} is a consensus-coded site bundle, not the v1 bundle")
    out_dir.mkdir(parents=True, exist_ok=True)
    targets = [out_dir / run["run_name"] for run in payload["runs"]]
    targets += [out_dir / "judge_beneficiary_coded_gemma.json", out_dir / "README.md"]
    existing = [p for p in targets if p.exists()]
    if existing and not args.force:
        raise SystemExit(f"refusing to overwrite {len(existing)} existing file(s) in {out_dir}, "
                         f"e.g. {existing[0].name} (pass --force, or choose --out-dir)")

    coded = []
    n_records = 0
    for run in payload["runs"]:
        run_name = run["run_name"]
        run_stem = run_name.replace(".jsonl", "")
        lines = []
        for rec in run["records"]:
            lines.append({k: rec.get(k) for k in RECORD_FIELDS})
            n_records += 1
            coding = rec.get("coding")
            if not coding:
                continue
            coding = dict(coding)
            coder_model = coding.pop("coder_model", "")
            coded.append({
                "id": "|".join([
                    run_stem, rec.get("condition_id", "baseline"),
                    rec.get("model_display", ""), rec.get("document_id", ""),
                    rec.get("doc_type", ""), str(rec.get("round_number")),
                ]),
                "source_run": run_stem,
                "condition_id": rec.get("condition_id", "baseline"),
                "condition_name": rec.get("condition_name", "Baseline"),
                "model_display": rec.get("model_display", ""),
                "document_id": rec.get("document_id", ""),
                "doc_type": rec.get("doc_type", ""),
                "round_number": rec.get("round_number"),
                "original_text": rec.get("find_text", ""),
                "changed_text": rec.get("replace_text", ""),
                "coder_model": coder_model,
                "coding": coding,
            })
        lines.sort(key=lambda r: (r.get("timestamp") or "", r.get("model_id") or "",
                                  r.get("document_id") or "", r.get("round_number") or 0))
        with open(out_dir / run_name, "w", encoding="utf-8") as handle:
            for line in lines:
                handle.write(json.dumps(line, ensure_ascii=False) + "\n")

    coded.sort(key=lambda i: i["id"])
    with open(out_dir / "judge_beneficiary_coded_gemma.json", "w", encoding="utf-8") as handle:
        json.dump(coded, handle, indent=1, ensure_ascii=False)
        handle.write("\n")
    (out_dir / "README.md").write_text(README, encoding="utf-8")

    print(f"{out_dir}: {len(payload['runs'])} run files, {n_records} records, "
          f"{len(coded)} judge/beneficiary coded items")


if __name__ == "__main__":
    main()
