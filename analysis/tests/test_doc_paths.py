"""Every repository path the guides mention exists.

Checked guides: README.md, analysis/README.md, archive/README.md and
results/iterative_edit/README.md. Conventions the guides follow, and this test
enforces:

- A path written in the text (in backticks, in a code block or in prose) is
  relative to the REPOSITORY ROOT and starts with a top-level directory
  (analysis/, docs/, results/, ...) or is a root file such as README.md. It
  must be tracked by git, or be one of the GENERATED locations below, which
  must be gitignored. `<name>` placeholders and `*` are wildcards; a pattern
  that matches nothing must at least name an existing directory.
- A Markdown link target is relative to the guide's own directory, as on
  GitHub, and must exist on disk.
- A history reference `<commit>:<path>` must exist in git history
  (`git cat-file -e`), and a commit hash in backticks must name a commit.
- `make <target>` must be a target defined in the Makefile.
"""

from __future__ import annotations

import fnmatch
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
GUIDES = ["README.md", "analysis/README.md", "archive/README.md", "results/iterative_edit/README.md"]

# Gitignored locations that the guides name but a fresh clone does not contain:
# they are created by a documented command.
GENERATED = {
    "data/processed/": "src/valconv/documents.py (make documents)",
    "analysis/data/cache/": "unpacked from the API cache archive (make cache)",
    "scratch/": "scratch output directory for new runs and test builds",
    ".env": "holds OPENROUTER_API_KEY; never committed",
}
ROOT_FILES = {"README.md", "CHANGE_LOG.md", "Makefile", "pyproject.toml", "uv.lock",
              "raw_data.sha256", ".gitignore", ".python-version", ".env"}

URL_RE = re.compile(r"https?://[^\s)>`]+")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
HISTORY_RE = re.compile(r"(?<![\w/])([0-9a-f]{7,40}(?:\^|~\d+)*):([\w.*/-]+)")
COMMIT_RE = re.compile(r"`([0-9a-f]{7,12})`")
MAKE_RE = re.compile(r"\bmake ([a-z][\w-]*)")


def _git(*args) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


def _tracked() -> list[str]:
    """Files git tracks or would track (not ignored), that exist on disk."""
    proc = _git("ls-files", "--cached", "--others", "--exclude-standard")
    if proc.returncode != 0:
        pytest.skip("not a git checkout", allow_module_level=True)
    return sorted({p for p in proc.stdout.splitlines() if (ROOT / p).is_file()})


TRACKED = _tracked()
TRACKED_DIRS = {str(Path(p).parent) for p in TRACKED}
TRACKED_DIRS |= {str(parent) for p in TRACKED for parent in Path(p).parents}
TOP_DIRS = sorted({p.split("/", 1)[0] for p in TRACKED if "/" in p}
                  | {g.split("/", 1)[0] for g in GENERATED if "/" in g} | {"scratch"})
PATH_RE = re.compile(
    r"(?<![\w./:~$-])((?:" + "|".join(re.escape(d) for d in TOP_DIRS) + r")/[\w.*<>/-]*"
    r"|(?:" + "|".join(re.escape(f) for f in sorted(ROOT_FILES)) + r"))(?![\w-])"
)


def _strip(text: str) -> str:
    return URL_RE.sub(" ", text)


def _is_generated(path: str) -> bool:
    return any(path == g.rstrip("/") or path.startswith(g.rstrip("/") + "/") for g in GENERATED)


def _exists(path: str) -> bool:
    path = path.rstrip("/").rstrip(".,;:")
    if not path:
        return True
    if _is_generated(path):
        return True
    pattern = re.sub(r"<[^>]*>", "*", path)
    if "*" in pattern:
        if any(fnmatch.fnmatchcase(p, pattern) for p in TRACKED) or \
                any(fnmatch.fnmatchcase(d, pattern) for d in TRACKED_DIRS):
            return True
        fixed = pattern.split("*", 1)[0].rsplit("/", 1)[0]
        return fixed in TRACKED_DIRS
    return path in TRACKED or path in TRACKED_DIRS


def _paths(text: str) -> list[str]:
    text = _strip(text)
    text = HISTORY_RE.sub(" ", text)
    text = LINK_RE.sub(" ", text)  # link targets are checked by test_link_targets_exist
    found = []
    for match in PATH_RE.finditer(text):
        token = re.sub(r":\d+$", "", match.group(1).rstrip(".,;:"))
        found.append(token)
    return found


def test_generated_locations_are_gitignored():
    for path in GENERATED:
        proc = _git("check-ignore", "-q", path)
        assert proc.returncode == 0, f"{path} is listed as generated but is not gitignored"


@pytest.mark.parametrize("guide", GUIDES)
def test_paths_in_text_exist(guide):
    text = (ROOT / guide).read_text(encoding="utf-8")
    paths = _paths(text)
    assert paths, f"{guide}: no paths found (is the pattern broken?)"
    missing = sorted({p for p in paths if not _exists(p)})
    assert not missing, f"{guide} names paths that do not exist: {missing}"


@pytest.mark.parametrize("guide", GUIDES)
def test_link_targets_exist(guide):
    base = (ROOT / guide).parent
    text = (ROOT / guide).read_text(encoding="utf-8")
    missing = []
    for target in LINK_RE.findall(text):
        if re.match(r"[a-z]+:", target) or target.startswith("#"):
            continue
        target = target.split("#", 1)[0]
        if not (base / target).exists():
            missing.append(target)
    assert not missing, f"{guide} links to missing files: {missing}"


@pytest.mark.parametrize("guide", GUIDES)
def test_history_references_exist(guide):
    if _git("rev-parse", "--is-shallow-repository").stdout.strip() == "true":
        pytest.skip("shallow clone: history is incomplete")
    text = _strip((ROOT / guide).read_text(encoding="utf-8"))
    missing = []
    for rev, path in HISTORY_RE.findall(text):
        ref = f"{rev}:{path.rstrip('/').rstrip('.')}"
        if _git("cat-file", "-e", ref).returncode != 0:
            missing.append(ref)
    for rev in COMMIT_RE.findall(text):
        if _git("cat-file", "-e", f"{rev}^{{commit}}").returncode != 0:
            missing.append(rev)
    assert not missing, f"{guide} cites history that does not exist: {missing}"


@pytest.mark.parametrize("guide", GUIDES)
def test_make_targets_exist(guide):
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    targets = set(re.findall(r"^([a-z][\w-]*):", makefile, flags=re.MULTILINE))
    text = (ROOT / guide).read_text(encoding="utf-8")
    unknown = sorted(set(MAKE_RE.findall(text)) - targets)
    assert not unknown, f"{guide} names make targets the Makefile lacks: {unknown}"


def test_path_extraction_rules():
    text = ("Run `analysis/src/build_site.py`, see [the map](reports/x.md), "
            "https://example.org/docs/a and 3b36326:recode/paper/ and main:/docs, "
            "then results/iterative_edit/run_*.jsonl. README.md")
    assert _paths(text) == ["analysis/src/build_site.py",
                            "results/iterative_edit/run_*.jsonl", "README.md"]
    assert _exists("results/iterative_edit/run_*.jsonl")
    assert _exists("analysis/human/coding_sheet_<coder>.csv")  # directory exists
    assert not _exists("analysis/src/no_such_script.py")
    assert _exists("data/processed/claude_constitution.md")  # generated
