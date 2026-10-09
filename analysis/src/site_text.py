"""site_text — write analysis/data/site/site_text.json, the text the website
build (analysis/src/build_site.py) takes from the authors' LessWrong draft.

The draft and the post's carousel widget are the authors' local working files
and are not part of the repository. The build reads only the committed
site_text.json; this script is how the authors refresh it after editing the
draft. It holds:
  - the two findings sentences of the draft's Introduction (plain text);
  - per site facet, the takeaway HTML (the Results heading in <strong>, then
    the first paragraph and any named extra paragraphs) and the highlighted
    edits: every quoted edit of that Results subsection, in draft order, with
    the quote and its attribution as written, the edit id it resolves to in
    analysis/data/canonical/edits.jsonl and how it was resolved;
  - the carousel slide the site adds (Claude Opus 4.7, Claude System Prompt,
    Round 2) in the site carousel's markup, and the edit id its quote is from.
The output has no timestamps: regenerating it from an unchanged draft gives
the same bytes. build_site.py re-resolves every quote against the canonical
edits at build time and fails if a stored resolution no longer holds.

Usage (from the repository root):
    .venv/bin/python analysis/src/site_text.py --draft <draft.md> --widget <widget.html>
    .venv/bin/python analysis/src/site_text.py --draft <draft.md> --widget <widget.html> --check
--check compares instead of writing (exit status 1 if the committed file is
out of date). Without --draft / --widget the authors' default local paths
are used.
"""

from __future__ import annotations

import argparse
import html as html_mod
import json
import re
import sys
from dataclasses import asdict
from pathlib import Path

import build_site as b
import draft_highlights as dh

# The authors' local (untracked) working copies of the draft and the widget.
DEFAULT_DRAFT = b.ROOT / "writeup" / "lesswrong_draft.md"
DEFAULT_WIDGET = b.ROOT / "writeup" / "lesswrong_carousel_widget.html"
OUT_PATH = b.SITE_TEXT

NOTE = (
    "Text the website build (analysis/src/build_site.py) takes from the authors' LessWrong "
    "draft and the post's carousel widget. Maintained by the authors: regenerate it with "
    "analysis/src/site_text.py; do not edit by hand."
)


def _esc(text: str) -> str:
    return html_mod.escape(text, quote=False)


def findings(md: str) -> dict[str, str]:
    """The Introduction's judge and beneficiaries sentences, verbatim
    (markdown stripped)."""
    judge, benef = dh.intro_findings(md)
    return {"judge": judge, "beneficiaries": benef}


def takeaway_html(t: dict) -> str:
    """'<strong>{heading}</strong> {first paragraph} {extra paragraphs}'."""
    return f"<strong>{_esc(t['heading'])}</strong> " + _esc(
        " ".join([t["first_paragraph"], *t["extra_paragraphs"]]))


def highlight(q: dh.Quote, edits: list[dict], live: set) -> dict:
    m = dh.match_quote(q, edits, live)
    return {
        "id": m["edit_id"],
        "label": f"{m['model_display']} · R{m['round']}",
        "tip": "“" + dh.trim_tip(q.text) + "”",
        "quote": asdict(q),
        "match": m,
    }


def carousel_slide(widget: str) -> str:
    """The Claude Opus 4.7 / Claude System Prompt / Round 2 slide of the
    carousel widget, in the site carousel's own slide markup."""
    m = re.search(
        r'    <div class="carousel-slide">\n(      <div [^\n]*Claude Opus 4\.7 &middot; Claude System Prompt &middot; Round 2</div>\n'
        r'      <p [^\n]*</p>\n      <div [^\n]*prioritizes idealized preferences</div>\n)    </div>',
        widget,
    )
    assert m, "Opus 4.7 slide not found in the carousel widget"
    inner = m.group(1).replace(" &middot; ", " · ")
    inner = "".join("            " + ln.lstrip(" ") + "\n" for ln in inner.splitlines())
    return '            <div class="carousel-slide">\n' + inner + "            </div>\n"


def generate(md: str, widget: str) -> dict:
    """The site-text document for a draft and a carousel widget."""
    texts = dh.facet_texts(md)
    edits = dh.load_edits(b.EDITS_PATH)
    live = b.live_highlight_ids()
    slide = carousel_slide(widget)
    return {
        "note": NOTE,
        "findings": findings(md),
        "facets": {
            fid: {
                "takeaway": takeaway_html(texts[fid]),
                "highlights": [highlight(q, edits, live) for q in texts[fid]["quotes"]],
            }
            for fid in b.CONSENSUS_FACETS
        },
        "carousel_slide": {"html": slide, "edit_id": b.check_carousel_quote(slide)},
    }


def render(doc: dict) -> str:
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


def from_files(draft: Path = DEFAULT_DRAFT, widget: Path = DEFAULT_WIDGET) -> str:
    return render(generate(Path(draft).read_text(encoding="utf-8"),
                           Path(widget).read_text(encoding="utf-8")))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--draft", type=Path, default=DEFAULT_DRAFT, help="the LessWrong draft (.md)")
    parser.add_argument("--widget", type=Path, default=DEFAULT_WIDGET, help="the carousel widget (.html)")
    parser.add_argument("--out", type=Path, default=OUT_PATH, help="output (default: %(default)s)")
    parser.add_argument("--check", action="store_true",
                        help="compare with --out instead of writing; exit 1 if it differs")
    args = parser.parse_args(argv)
    text = from_files(args.draft, args.widget)
    if args.check:
        same = args.out.is_file() and args.out.read_text(encoding="utf-8") == text
        print(f"{args.out}: {'up to date' if same else 'OUT OF DATE'}")
        return 0 if same else 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
