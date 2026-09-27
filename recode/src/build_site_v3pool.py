"""Build recode/site_v3pool/ — the three-grader pooled-average variant of the
docs/ site (Gemma 4 + Qwen 3.8 + Muse Spark 1.3; DECISIONS.md §1 as amended).

Thin entry point: all logic lives in the shared variant builder
recode/src/build_site_v2avg.py (see its docstring for the Variant config and
the pooling semantics). Equivalent to:

    .venv/bin/python recode/src/build_site_v2avg.py --variant v3pool

Usage (repo root = /Users/nicholasgannon/peter/llm-value-reflection):
    .venv/bin/python recode/src/build_site_v3pool.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_site_v2avg as builder  # noqa: E402


def main() -> None:
    builder.build(builder.V3POOL)


if __name__ == "__main__":
    main()
