"""Build recode/site_consensus/ — the docs/ site rebuilt on the three-grader
MAJORITY-VOTE consensus codes (recode/data/codes/ensemble.jsonl), the codes
behind every number in the paper and the LessWrong post. Intended to replace
the live site after the author approves.

Thin entry point: all logic lives in the shared variant builder
recode/src/build_site_v2avg.py (see the CONSENSUS variant there) plus
recode/src/draft_highlights.py (statements and highlighted edits read from
reports/final_draft.md). Equivalent to:

    .venv/bin/python recode/src/build_site_v2avg.py --variant consensus

Usage (repo root = /Users/nicholasgannon/peter/llm-value-reflection):
    .venv/bin/python recode/src/build_site_consensus.py
Serve: python3 -m http.server 8097 --directory recode/site_consensus
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_site_v2avg as builder  # noqa: E402


def main() -> None:
    builder.build(builder.CONSENSUS)


if __name__ == "__main__":
    main()
