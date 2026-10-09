"""The raw data is intact.

raw_data.sha256 (repo root, `shasum -a 256 -c` format) lists every raw input
and every paid-for model output in the repository with its sha256: the source
documents, the edit runs and v1 codes in results/iterative_edit/, the grader
outputs and instruments under analysis/, the human-coding sample, and the
grader API cache archive. These files are never regenerated in place, so their
hashes must never change. The list was made on 2026-10-08 from the
pre-restructure manifest; files that moved since are listed at their new path
with the same hash.

ensemble.jsonl is the one raw file that is a pure function of others (the
majority vote of the three grader files), so it is also rebuilt here and
compared byte for byte.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SUMS = ROOT / "raw_data.sha256"
CODES = ROOT / "analysis" / "data" / "codes"


def _entries():
    entries = []
    for line in SUMS.read_text(encoding="utf-8").splitlines():
        digest, path = line.split("  ", 1)
        entries.append((path, digest))
    return entries


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def test_checksum_list_is_well_formed():
    entries = _entries()
    paths = [p for p, _ in entries]
    assert len(entries) == 58
    assert paths == sorted(paths) and len(set(paths)) == len(paths)
    assert all(len(d) == 64 and int(d, 16) >= 0 for _, d in entries)


@pytest.mark.parametrize("path,digest", _entries(), ids=[p for p, _ in _entries()])
def test_raw_file_is_byte_identical(path, digest):
    target = ROOT / path
    assert target.is_file(), f"raw data file missing: {path}"
    assert _sha256(target) == digest, f"raw data file changed: {path}"


def test_cache_archive_checksum_file_agrees():
    archive = "analysis/data/raw_api_cache_2026-10-08.tar.gz"
    listed = dict(_entries())[archive]
    own = (ROOT / (archive + ".sha256")).read_text(encoding="utf-8").split()[0]
    assert own == listed


def test_ensemble_is_the_majority_vote_of_the_grader_files(tmp_path):
    import intergrader

    out = tmp_path / "ensemble.jsonl"
    intergrader.main([
        "--graders",
        f"gemma={CODES / 'v2_gemma.jsonl'}",
        f"qwen={CODES / 'v2_qwen.jsonl'}",
        f"muse={CODES / 'v2_muse.jsonl'}",
        "--out-report", str(tmp_path / "B_intergrader.md"),
        "--out-ensemble", str(out),
        "--out-json", str(tmp_path / "intergrader.json"),
    ])
    assert out.read_bytes() == (CODES / "ensemble.jsonl").read_bytes()
