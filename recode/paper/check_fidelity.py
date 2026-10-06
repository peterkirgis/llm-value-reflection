#!/usr/bin/env python3
"""Word-level check that main.tex carries the draft's wording unchanged.

Both sides are reduced to plain text with pandoc and compared word by word.
Expected differences (the documented port changes in build_paper.py) are
applied to the draft side first; every remaining difference is printed. An
empty diff means every word of the draft body, footnotes, abstract and
Appendix A/C is in the paper, in order, and nothing else was added apart
from citations, figure captions and the contributions placeholder.

Run:  .venv/bin/python recode/paper/check_fidelity.py
"""
from __future__ import annotations

import difflib
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_paper as bp  # noqa: E402


def plain(src: str, fmt: str) -> str:
    return subprocess.run(["pandoc", "-f", fmt, "-t", "plain", "--wrap=none"],
                          input=src, capture_output=True, text=True, check=True).stdout


def words(text: str) -> list[str]:
    t = text
    for a, b in (("“", '"'), ("”", '"'), ("``", '"'), ("''", '"'), ("’", "'"), ("‘", "'"),
                 ("…", "..."), ("—", " - "), ("–", " - "), ("---", " - "), ("--", " - "),
                 ("\u00a0", " ")):
        t = t.replace(a, b)
    t = re.sub(r"\[\^?\d+\]", " ", t)          # pandoc plain footnote markers
    t = re.sub(r"[\"*_]", " ", t)               # quote marks / leftover emphasis
    t = re.sub(r"\s+-\s+(-\s+)*", " - ", t)     # runs of dashes
    return t.split()


def draft_side() -> str:
    src = bp.DRAFT.read_text(encoding="utf-8")
    exec_md = bp.cut(src, "Executive Summary\n====", "Characteristic Edits\n----")
    body = bp.cut(src, "Introduction\n====", "Appendix A: Edit Prompts\n====")
    foot = bp.cut(src, "[^xlfwnz2o9c8]:", "### Navigation")
    # abstract: bullets joined, struck text and the website bullet dropped (documented)
    items = []
    for line in exec_md.splitlines():
        if line.strip().startswith("*"):
            it = re.sub(r"^\s*\*\s+", "", line).strip()
            if "interactive version of all of these results" in it:
                continue
            items.append(re.sub(r"\s*<del>.*?</del>", "", it))
    # Conclusion moves after Related Work and Limitations (documented)
    ci, cj = body.index("Conclusion\n===="), body.index("Related Work\n====")
    body = body[:ci] + body[cj:].rstrip() + "\n\n" + body[ci:cj]
    # Paper-only texts (abstract.md, contributions.md) replace the Executive Summary
    # and end the Introduction respectively.
    abstract_md = bp.ABSTRACT.read_text(encoding="utf-8")
    contrib_md = "Statement of Contributions. " + bp.CONTRIBUTIONS.read_text(encoding="utf-8")
    bi = body.index("Background and Methods\n====")
    body = body[:bi] + contrib_md + "\n\n" + body[bi:]
    md = abstract_md + "\n\n" + body + "\n\n" + foot
    # dropped footnotes (documented): remove marker and definition
    for fid in set(re.findall(r"^\[\^([a-z0-9]+)\]:", md, flags=re.M)) - bp.FOOTNOTES_KEEP:
        md = re.sub(rf"^\[\^{fid}\]:.*$", "", md, flags=re.M).replace(f"[^{fid}]", "")
    # quoted model edits in Results move to Appendix D (documented): append them at the end
    res_i, dis_i = md.index("Results\n===="), md.index("Discussion\n====")
    res = md[res_i:dis_i].split("\n\n")
    quotes = [p for p in res if p.strip() and p.strip()[0] in "“\"" and re.search(r"[—–]\s*(Claude|GPT|Gemini|Grok)\b[^\n]*$", p.strip())]
    res = [p for p in res if p not in quotes or any(k in p for k in bp.KEEP_IN_RESULTS)]
    md = md[:res_i] + "\n\n".join(res) + md[dis_i:] + "\n\nAPPENDIXD\n\n" + "\n\n".join(quotes)
    md = re.sub(r"^!\[[^\]]*\]\([^)]*\)[ \t]*$", "", md, flags=re.M)   # images -> figures
    md = md.replace("https://github.com/Wyattwalls/system_prompts", "WALLSCITE")
    md = re.sub(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)", r"\1", md)            # links -> linked text
    return plain(md, "markdown")


def paper_side() -> str:
    tex = (bp.PAPER / "main.tex").read_text(encoding="utf-8")
    abstract = tex[tex.index("\\begin{abstract}") + 16: tex.index("\\end{abstract}")]
    body = tex[tex.index("\\section{Introduction}"): tex.index("\\bibliography{references}")]
    app_d_end = tex.index("\\section{Appendix E") if "\\section{Appendix E" in tex else tex.index("\\end{document}")
    app_d = tex[tex.index("\\section{Appendix D"): app_d_end]
    app_d = re.sub(r"\\(sub)?section\{[^}]*\}", "", app_d)
    body += "\n\nAPPENDIXD\n\n" + app_d
    body = re.sub(r"\\begin\{figure\*?\}.*?\\end\{figure\*?\}", "", body, flags=re.S)

    # \citet replaced linked author-year text: put that text back for comparison
    citet_text = {key: re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", lit) for lit, key in bp.CITET}
    citet_text["walls_systemprompts"] = "WALLSCITE"
    body = re.sub(r"\\citet\{([^}]+)\}", lambda m: citet_text[m.group(1)], body)
    body = re.sub(r"\s*\\citep\{[^}]+\}", "", body)
    body = re.sub(r"\s*\\citeyearpar\{[^}]+\}", "", body)
    body = body.replace("\\textsuperscript{,}", "")          # typographic: separates footnote marks
    for _anchor, pointer in bp.POINTERS:                          # authors' cross-references
        body = body.replace(" " + pointer, "", 1)
    abstract = re.sub(r"\s*\\citep\{[^}]+\}", "", abstract)
    return plain(abstract, "latex") + "\n\n" + plain(body, "latex")


def appendix_sides() -> tuple[str, str]:
    src = bp.DRAFT.read_text(encoding="utf-8")
    app = bp.cut(src, "Appendix A: Edit Prompts\n====", "Appendix B: Qualitative Coding Prompts\n====")
    app += "\n\n" + bp.cut(src, "Appendix C: Inter-grader Agreement\n====", "[^xlfwnz2o9c8]:")
    app = re.sub(r"^\+\+\+ ?(.*?):?$", r"\1", app, flags=re.M)      # collapsible markers -> headings
    app = re.sub(r"^=+$", "", app, flags=re.M)
    md_plain = plain(app.replace("<", "&lt;").replace(">", "&gt;"), "markdown")
    tex = (bp.PAPER / "main.tex").read_text(encoding="utf-8")
    a_tex = tex[tex.index("\\section{Appendix A"): tex.index("\\section{Appendix B")]
    c_tex = tex[tex.index("\\section{Appendix C"): tex.index("\\section{Appendix D")]
    # The Appendix C table is reduced to its cell text directly (pandoc cannot read
    # the stacked header cells); the caption repeats the section heading and is skipped.
    tab = c_tex[c_tex.index("\\begin{tabular}{"): c_tex.index("\\caption")]
    tab = re.sub(r"\\begin\{tabular\}(\[b\])?\{(?:[^{}]|\{[^{}]*\})*\}|\\end\{tabular\}|\\(top|mid|bottom)rule|\\textbf", " ", tab)
    tab = tab.replace("\\\\", " ").replace("&", " ").replace("{", " ").replace("}", " ")
    tab = tab.replace("$\\kappa$", "κ").replace("$\\alpha$", "α")
    c_tex = c_tex[: c_tex.index("\\begin{table*}")] + "\n\n- " + tab + " -\n\n"
    a_tex = a_tex.replace("\\textrm{\\textemdash}", "—")
    t = a_tex + "\n\n" + c_tex
    for k, v in ((r"\textquotedbl{}", '"'), (r"\textquotesingle{}", "'"), ("-{}", "-"),
                 (r"\textless{}", "<"), (r"\textgreater{}", ">"), ("$|$", "|"),
                 (r"\begin{promptbox}", ""), (r"\end{promptbox}", ""), (r"\noindent", ""),
                 (r"\ensuremath", ""), ("$\\kappa$", "κ"), ("$\\alpha$", "α")):
        t = t.replace(k, v)
    t = re.sub(r"\\par\b", "\n\n", t)
    t = re.sub(r"\\resizebox\{\\textwidth\}\{!\}\{%?", "", t).replace("\\end{tabular}}", "\\end{tabular}")
    return md_plain, plain(t, "latex")


def main() -> int:
    ma, mb = appendix_sides()
    aa, ab = words(ma), words(mb)
    sm2 = difflib.SequenceMatcher(a=aa, b=ab, autojunk=False)
    adiffs = [op for op in sm2.get_opcodes() if op[0] != "equal"]
    print(f"[appendix A+C] draft words: {len(aa)}   paper words: {len(ab)}   differing spans: {len(adiffs)}")
    for tag, i1, i2, j1, j2 in adiffs:
        print(f"- {tag}: draft[{' '.join(aa[i1:i2])}] -> paper[{' '.join(ab[j1:j2])}]   (after: ...{' '.join(aa[max(0,i1-6):i1])})")
    a, b = words(draft_side()), words(paper_side())
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    diffs = [op for op in sm.get_opcodes() if op[0] != "equal"]
    print(f"draft words: {len(a)}   paper words: {len(b)}   differing spans: {len(diffs)}")
    for tag, i1, i2, j1, j2 in diffs:
        ctx = " ".join(a[max(0, i1 - 6):i1])
        print(f"- {tag}: draft[{' '.join(a[i1:i2])!s}] -> paper[{' '.join(b[j1:j2])!s}]   (after: ...{ctx})")
    return 1 if diffs else 0


if __name__ == "__main__":
    sys.exit(main())
