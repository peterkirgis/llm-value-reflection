"""Provenance paths in committed outputs are repo-relative, never a local checkout.

repo_rel() is what every writer (headline, bootstrap, intergrader, e_reports,
compare_v1_v2, draw_human_sample, human_validation, report_figures) puts into
its *_path fields and report text. The scan below guards the committed tree.
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

from common import ANALYSIS_ROOT, REPO_ROOT, repo_rel

# Raw-data files kept byte-identical (raw-data manifest of 2026-10-08); they
# were written before the writers were fixed and may not be edited.
FROZEN = {"analysis/human/sample_manifest.json"}

# A macOS home-directory prefix (/Users/<name>/), the form the stripped paths
# had. /home/... is not checked: the documents in system_prompts/ quote
# sandbox paths such as /home/oai/skills/.
LOCAL_PATH = re.compile(r"/Users/[A-Za-z0-9._-]+/")


def test_repo_rel_absolute_inside_repo():
    p = ANALYSIS_ROOT / "data" / "codes" / "ensemble.jsonl"
    assert repo_rel(p) == "analysis/data/codes/ensemble.jsonl"
    assert repo_rel(str(p)) == "analysis/data/codes/ensemble.jsonl"


def test_repo_rel_keeps_relative_and_outside_paths(tmp_path):
    assert repo_rel("analysis/data/codes/v1.jsonl") == "analysis/data/codes/v1.jsonl"
    assert repo_rel(Path("analysis") / "human") == "analysis/human"
    outside = tmp_path / "x.jsonl"
    assert repo_rel(outside) == str(outside)


@pytest.mark.skipif(shutil.which("git") is None, reason="needs git")
def test_no_local_checkout_paths_in_tracked_files():
    try:
        out = subprocess.run(
            ["git", "ls-files", "-z"], cwd=REPO_ROOT, check=True,
            capture_output=True,
        ).stdout.decode("utf-8")
    except (subprocess.CalledProcessError, OSError):
        pytest.skip("not a git checkout")
    offenders = []
    for rel in filter(None, out.split("\0")):
        if rel in FROZEN:
            continue
        path = REPO_ROOT / rel
        if not path.is_file():
            continue
        data = path.read_bytes()
        if b"\0" in data[:8192]:  # binary (PNG, PDF, gzip)
            continue
        text = data.decode("utf-8", errors="replace")
        if LOCAL_PATH.search(text) or str(REPO_ROOT) in text:
            offenders.append(rel)
    assert offenders == [], f"local absolute paths in: {offenders}"
