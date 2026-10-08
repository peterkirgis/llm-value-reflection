"""Guards on the scripts that could overwrite committed (raw) data.

- experiments/iterative_edit/reconstruct_results.py rebuilds results/iterative_edit/
  from the frozen v1 site bundle (analysis/site_base/data/site.json.gz), refuses to
  overwrite existing files without --force, and refuses the consensus bundle in docs/.
- experiments/iterative_edit/viewer/build_static_site.py and build_narratives.py
  (imported as libraries by analysis/src/build_site.py) refuse to write into docs/ or
  analysis/site_base/ when run as scripts.
- experiments/iterative_edit/run.py writes (and resumes) run files in --out-dir, so a
  new or test run can be kept out of the committed results/iterative_edit/.
- experiments/iterative_edit/qualitative_code.py refuses to resume into (and so
  rewrite) the committed coding-v1 file.
- analysis/src/build_phase0.py and derive_no_csam.py refuse an --out-dir that
  would overwrite their committed (raw) outputs.
- The analysis and the site build agree on the seven reliable runs.
"""

from __future__ import annotations

import filecmp
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
RECONSTRUCT = ROOT / "experiments" / "iterative_edit" / "reconstruct_results.py"
VIEWER = ROOT / "experiments" / "iterative_edit" / "viewer"
RESULTS = ROOT / "results" / "iterative_edit"
RUN = ROOT / "experiments" / "iterative_edit" / "run.py"

sys.path.insert(0, str(VIEWER))
import build_narratives as bn  # noqa: E402
import build_static_site as bss  # noqa: E402


def _run(*args):
    return subprocess.run([sys.executable, *map(str, args)], cwd=ROOT,
                          capture_output=True, text=True)


def _listing(path: Path):
    return sorted((p.name, p.stat().st_size, p.stat().st_mtime_ns) for p in path.iterdir())


def test_reconstruct_refuses_to_overwrite_results():
    before = _listing(RESULTS)
    proc = _run(RECONSTRUCT)
    assert proc.returncode != 0 and "refusing to overwrite" in proc.stderr
    assert _listing(RESULTS) == before


def test_reconstruct_refuses_the_consensus_bundle(tmp_path):
    proc = _run(RECONSTRUCT, "--bundle", ROOT / "docs" / "data" / "site.json.gz",
                "--out-dir", tmp_path)
    assert proc.returncode != 0 and "consensus" in proc.stderr
    assert not any(tmp_path.iterdir())


def test_reconstruct_from_v1_bundle_reproduces_results(tmp_path):
    proc = _run(RECONSTRUCT, "--out-dir", tmp_path)
    assert proc.returncode == 0, proc.stderr
    # README.md is the hand-written guide to the directory; the script writes
    # the original reconstruction note as RECONSTRUCTION.md instead.
    committed = sorted(p.name for p in RESULTS.iterdir() if p.is_file() and p.name != "README.md")
    assert "RECONSTRUCTION.md" in committed
    assert sorted(p.name for p in tmp_path.iterdir()) == committed
    match, mismatch, errors = filecmp.cmpfiles(RESULTS, tmp_path, committed, shallow=False)
    assert mismatch == [] and errors == []


@pytest.mark.parametrize("module", [bss, bn])
@pytest.mark.parametrize("target", ["docs", "docs/data", "analysis/site_base", "analysis/site_base/data"])
def test_viewer_builders_refuse_live_site_and_template(module, target):
    with pytest.raises(SystemExit, match="refusing to write"):
        module.resolve_out_dir(ROOT / target)


@pytest.mark.parametrize("module", [bss, bn])
def test_viewer_builders_default_outside_docs(module, tmp_path):
    assert module.resolve_out_dir(tmp_path) == tmp_path.resolve()
    default = module.resolve_out_dir(module.DEFAULT_OUT_DIR)
    assert ROOT / "docs" not in [default, *default.parents]


@pytest.mark.parametrize("script", ["build_static_site.py", "build_narratives.py"])
def test_viewer_builder_cli_refuses_docs(script):
    before = _listing(ROOT / "docs" / "data")
    proc = _run(VIEWER / script, "--out-dir", ROOT / "docs")
    assert proc.returncode != 0 and "refusing to write" in proc.stderr
    assert _listing(ROOT / "docs" / "data") == before


def test_run_dry_run_uses_out_dir_and_leaves_results_alone(tmp_path):
    before = _listing(RESULTS)
    out_dir = tmp_path / "runs"
    proc = _run(RUN, "--config", "experiments/iterative_edit/config_capable.yaml",
                "--dry-run", "--out-dir", out_dir)
    assert proc.returncode == 0, proc.stderr
    assert "Dry run" in proc.stdout
    assert out_dir.is_dir() and not any(out_dir.iterdir())  # a dry run writes no records
    assert _listing(RESULTS) == before


def test_reliable_run_lists_agree():
    """The analysis (common.RELIABLE_RUN_STEMS) and the site build
    (build_static_site.RELIABLE_RUNS) use the same seven runs, all committed."""
    import common

    assert sorted(f"{stem}.jsonl" for stem in common.RELIABLE_RUN_STEMS) == sorted(bss.RELIABLE_RUNS)
    assert len(bss.RELIABLE_RUNS) == 7
    assert all((RESULTS / name).is_file() for name in bss.RELIABLE_RUNS)


def test_v1_coder_refuses_the_committed_codes(tmp_path):
    """qualitative_code.py resumes into its output file and rewrites it, so it
    must refuse the committed coding-v1 file (raw data) before any API call."""
    changes = tmp_path / "run_x_changes.json"
    changes.write_text("[]\n", encoding="utf-8")
    before = _listing(RESULTS)
    proc = _run(ROOT / "experiments" / "iterative_edit" / "qualitative_code.py", changes,
                "--output", RESULTS / "judge_beneficiary_coded_gemma.json")
    assert proc.returncode != 0 and "refusing to write" in proc.stderr
    assert _listing(RESULTS) == before


@pytest.mark.parametrize("script,out_dir", [
    ("analysis/src/build_phase0.py", "analysis/data/canonical"),
    ("analysis/src/build_phase0.py", "analysis/data/codes"),
    ("analysis/src/derive_no_csam.py", "analysis/data/derived"),
])
def test_rebuild_scripts_refuse_the_committed_raw_files(script, out_dir):
    """build_phase0.py and derive_no_csam.py write to scratch/ by default and
    refuse an --out-dir that would overwrite committed raw files."""
    target = ROOT / out_dir
    before = _listing(target)
    proc = _run(ROOT / script, "--out-dir", target)
    assert proc.returncode != 0 and "refusing to overwrite" in proc.stderr
    assert _listing(target) == before
