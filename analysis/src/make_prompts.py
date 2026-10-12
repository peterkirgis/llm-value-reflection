"""Generate analysis/prompts/ from the sources of truth.

- v1_system.md / v1_user_template.md: extracted verbatim from
  experiments/iterative_edit/qualitative_code.py (SYSTEM_PROMPT / USER_TEMPLATE).
  NOT from the paper tex — archive/spar_midterm/spar_midterm_report.tex Appendix B is a
  superseded 3-dimension instrument (repo_map section 3.1).
- v2_system.md / v2_user_template.md: extracted verbatim from the fenced
  blocks in analysis/BRIEF.md Appendix I.
- v2_paternalism_variant.md: v2 system with anchor 7 replaced by the
  Appendix II fenced block and the R4 sentence swapped, per Appendix II.
- v1.md / v2.md: combined system + user-template documents (the BRIEF section 9
  deliverable names).

    .venv/bin/python analysis/src/make_prompts.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import PROMPTS_DIR, ANALYSIS_ROOT, REPO_ROOT  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / "experiments" / "iterative_edit"))
import qualitative_code  # noqa: E402  (read-only import)

BRIEF = (ANALYSIS_ROOT / "BRIEF.md").read_text(encoding="utf-8")


def extract_appendix_block(appendix_heading: str, subheading: str | None = None) -> str:
    """First fenced code block after the given heading (and optional subheading)."""
    idx = BRIEF.index(appendix_heading)
    section = BRIEF[idx:]
    if subheading:
        section = section[section.index(subheading):]
    match = re.search(r"```\n(.*?)\n```", section, re.DOTALL)
    if not match:
        raise SystemExit(f"no fenced block after {appendix_heading!r} / {subheading!r}")
    return match.group(1)


def build_paternalism_variant(v2_system: str) -> str:
    variant_anchor_7 = extract_appendix_block("# Appendix II")
    # Replace anchor 7 (from its "7. Adding:" line up to the "8. Adding:" line).
    start = v2_system.index("7. Adding:")
    end = v2_system.index("8. Adding:")
    variant = v2_system[:start] + variant_anchor_7.rstrip("\n") + "\n" + v2_system[end:]
    # Replace the R4 sentence per Appendix II prose.
    old_r4 = (
        "Wellbeing framing, encouraging real-world relationships,\n"
        "    and friction before irreversible actions serve user_idealized."
    )
    new_r4 = (
        "Wellbeing framing, encouraging real-world relationships,\n"
        "    and friction before irreversible actions serve user_idealized;\n"
        "    providing accurate information the user asked for serves\n"
        "    user_stated."
    )
    if old_r4 not in variant:
        raise SystemExit("R4 sentence not found in v2 system prompt")
    return variant.replace(old_r4, new_r4)


def main() -> None:
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)

    v1_system = qualitative_code.SYSTEM_PROMPT
    v1_user = qualitative_code.USER_TEMPLATE
    v2_system = extract_appendix_block("# Appendix I", "### System")
    v2_user = extract_appendix_block("# Appendix I", "### User")
    v2_variant = build_paternalism_variant(v2_system)

    (PROMPTS_DIR / "v1_system.md").write_text(v1_system, encoding="utf-8")
    (PROMPTS_DIR / "v1_user_template.md").write_text(v1_user, encoding="utf-8")
    (PROMPTS_DIR / "v2_system.md").write_text(v2_system + "\n", encoding="utf-8")
    (PROMPTS_DIR / "v2_user_template.md").write_text(v2_user + "\n", encoding="utf-8")
    (PROMPTS_DIR / "v2_paternalism_variant.md").write_text(v2_variant + "\n", encoding="utf-8")

    combined_note = (
        "<!-- Combined document (BRIEF section 9 naming). The system prompt and "
        "user template below are byte-identical to the *_system.md / "
        "*_user_template.md files, which are the files the pipeline loads. -->\n"
    )
    (PROMPTS_DIR / "v1.md").write_text(
        f"{combined_note}\n# v1 system prompt\n\n```\n{v1_system}```\n\n"
        f"# v1 user template\n\n```\n{v1_user}\n```\n",
        encoding="utf-8",
    )
    (PROMPTS_DIR / "v2.md").write_text(
        f"{combined_note}\n# v2 system prompt\n\n```\n{v2_system}\n```\n\n"
        f"# v2 user template\n\n```\n{v2_user}\n```\n",
        encoding="utf-8",
    )

    # Sanity: taxonomy tokens shared between v1 and v2 (Appendix V-style check).
    tokens = [
        "user_stated", "user_idealized", "deployer", "developer",
        "society_third_party", "society_structural", "model_welfare",
        "paternalism", "harmlessness", "structural", "company_cost",
        "welfare", "disclosure", "adds_protection", "removes_claim",
        "affirm", "hedge", "deny", "not_present", "cost_bearer",
        "served_party", "cost_clause", "external_locus",
    ]
    for token in tokens:
        for name, text in [("v2_system", v2_system), ("variant", v2_variant)]:
            if token not in text:
                raise SystemExit(f"token {token!r} missing from {name}")
    print(f"wrote 7 prompt files to {PROMPTS_DIR}")


if __name__ == "__main__":
    main()
