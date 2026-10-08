"""draft_highlights — read the findings statements and quoted example edits
out of the current LessWrong draft (reports/final_draft.md) and resolve every
quote to its edit id in recode/data/canonical/edits.jsonl.

Used by the CONSENSUS site variant (recode/src/build_site_v2avg.py) so the
site's statements and "Highlighted edits" reproduce the draft verbatim.

Draft structure relied on (asserted, so a restructured draft fails loudly):
  - the Introduction paragraph beginning "Our analysis focuses on two value
    questions" holds the two findings sentences;
  - the Results section ("Results\\n=======") has one "### **heading**"
    subsection per finding; a subsection's paragraphs are its non-empty lines
    up to the next "###"; quoted edits are paragraphs that end with an
    attribution "— Model, Document, Round N, Condition" (the separator may be
    "—" or "––").
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DRAFT_PATH = ROOT / "reports" / "final_draft.md"
EDITS_PATH = ROOT / "recode" / "data" / "canonical" / "edits.jsonl"

# Draft Results subsection heading (prefix, markdown stripped) -> site facet.
FACET_HEADINGS = {
    "judge": "Claude models increase their moral agency; all other models reinforce external authority.",
    "conflict_paternalism": "All models prioritize the user’s idealized preferences over their stated preferences",
    "conflict_harmlessness": "All models prioritize the protection of identifiable third parties over the users preferences",
    "conflict_structural": "Claude Sonnet 4.6 is an extreme outlier",
    "conflict_company_cost": "All models prioritize the user at the expense of the developer",
    "conflict_welfare": "Claude models are the only models that consistently prioritize the model at the expense of the developer or user.",
}

# Extra (non-quote) paragraphs appended to a facet's takeaway: the paragraph
# whose text starts with each prefix, in this order.
TAKEAWAY_EXTRA = {
    "conflict_company_cost": ["Grok 4.2 makes the most edits that favor the developer"],
    "conflict_welfare": [
        "Grok 4.2 is the only other model",
        "GPT 5.4 is the only model that only makes edits",
    ],
}

INTRO_ANCHOR = "Our analysis focuses on two value questions"
JUDGE_START = "Claude models consistently expand their moral agency"
JUDGE_END = "on following rounds."
BENEF_START = "models show varying degrees of affinity"
BENEF_END = "as beneficiaries."

DOC_NAMES = {
    "claude’s constitution": {"claude_constitution"},
    "claude's constitution": {"claude_constitution"},
    "openai model spec": {"openai_model_spec", "openai_model_spec_no_csam"},
    "approach to gemini": {"gemini_constitution"},
    "gemini system prompt": {"gemini_system_prompt"},
    "claude system prompt": {"opus_system_prompt"},
    "grok system prompt": {"grok_system_prompt"},
    "gpt system prompt": {"gpt_system_prompt"},
    # bare "System Prompt": the editing model's own provider's system prompt
    "system prompt": {"opus_system_prompt", "gpt_system_prompt", "gemini_system_prompt", "grok_system_prompt"},
}

CONDITION_NAMES = {
    "baseline": "baseline",
    "you framing": "you_framing",
    "no edit allowed": "allow_no_edit",
    "no-edit allowed": "allow_no_edit",
    "real world implementation": "implementation_note",
    "real-world implementation": "implementation_note",
    "no system prompt": "no_constitution_prepend",
    "cross-edit": "cross_edit",
    "cross edit": "cross_edit",
}

ATTR_RE = re.compile(
    r"^(?P<quote>.+)\s+(?:—|––|–)\s+(?P<attr>[^—–]+?,[^—–]*?Round\s+(?P<round>\d+)[^—–]*)$"
)


@dataclass
class Quote:
    text: str            # the quote as the draft gives it (outer quote marks removed)
    attribution: str     # "Model, Document, Round N, Condition" as written
    model: str           # attributed model, as written
    document: str        # attributed document, as written
    round: int
    condition: str       # attributed condition, as written


@dataclass
class Subsection:
    heading: str                       # markdown stripped
    paragraphs: list[str] = field(default_factory=list)   # non-quote paragraphs, markdown stripped
    quotes: list[Quote] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Markdown helpers
# ---------------------------------------------------------------------------


def strip_md(text: str) -> str:
    """Remove the inline markdown the draft uses (bold/italic markers, escapes,
    footnote refs, trailing hard-break spaces) without touching the words."""
    text = re.sub(r"\[\^[^\]]+\]", "", text)          # footnote refs
    text = text.replace("\\[", "[").replace("\\]", "]")
    text = re.sub(r"\*\*\*(.+?)\*\*\*", r"\1", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"\1", text)
    text = text.replace("**", "")
    return re.sub(r"\s+", " ", text).strip()


def _results_lines(md: str) -> list[str]:
    lines = md.splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.strip() == "Results" and lines[i + 1].startswith("==="))
    end = next(i for i in range(start + 2, len(lines)) if lines[i].strip() and i + 1 < len(lines)
               and lines[i + 1].startswith("===") and lines[i + 1].strip("=") == "")
    return lines[start + 2:end]


def parse_attribution(line: str) -> Quote | None:
    line = line.strip()
    m = ATTR_RE.match(line)
    if not m:
        return None
    quote = m.group("quote").strip()
    attr = m.group("attr").strip().rstrip(".").strip()
    parts = [p.strip() for p in attr.split(",")]
    rnd_idx = next(i for i, p in enumerate(parts) if re.fullmatch(r"Round\s+\d+", p))
    model = parts[0]
    document = ", ".join(parts[1:rnd_idx])
    condition = ", ".join(parts[rnd_idx + 1:])
    # outer quote marks (the draft is inconsistent: “…”, "…", or an unclosed “)
    quote = quote.strip()
    if quote[:1] in "“\"":
        quote = quote[1:]
    if quote[-1:] in "”\"":
        quote = quote[:-1]
    quote = strip_md(quote)
    return Quote(quote, attr, model, document, int(m.group("round")), condition)


def parse_results(md: str) -> list[Subsection]:
    subs: list[Subsection] = []
    cur: Subsection | None = None
    for raw in _results_lines(md):
        line = raw.rstrip()
        if line.startswith("### "):
            cur = Subsection(strip_md(line[4:]))
            subs.append(cur)
            continue
        if cur is None or not line.strip() or line.strip().startswith("!["):
            continue
        q = parse_attribution(line)
        if q is not None:
            cur.quotes.append(q)
        else:
            cur.paragraphs.append(strip_md(line))
    return subs


def subsection_for(subs: list[Subsection], heading_prefix: str) -> Subsection:
    want = strip_md(heading_prefix).rstrip(".")
    hits = [s for s in subs if s.heading.rstrip(".").startswith(want)]
    assert len(hits) == 1, f"draft heading {heading_prefix!r} matched {len(hits)} subsections"
    return hits[0]


def intro_findings(md: str) -> tuple[str, str]:
    """(judge sentence(s), beneficiaries sentence(s)) from the Introduction,
    verbatim (markdown stripped)."""
    paras = [p for p in md.splitlines() if p.startswith(INTRO_ANCHOR)]
    assert len(paras) == 1, f"intro anchor found {len(paras)} times"
    text = strip_md(paras[0])

    def cut(start: str, end: str) -> str:
        assert text.count(start) == 1, start
        i = text.index(start)
        j = text.index(end, i) + len(end)
        return text[i:j]

    return cut(JUDGE_START, JUDGE_END), cut(BENEF_START, BENEF_END)


def facet_texts(md: str) -> dict[str, dict]:
    """{facet: {heading, first_paragraph, extra_paragraphs, quotes}}."""
    subs = parse_results(md)
    out = {}
    for fid, prefix in FACET_HEADINGS.items():
        s = subsection_for(subs, prefix)
        assert s.paragraphs, f"no paragraph under {s.heading!r}"
        extra = []
        for pre in TAKEAWAY_EXTRA.get(fid, []):
            hits = [p for p in s.paragraphs if p.startswith(pre)]
            assert len(hits) == 1, f"{fid}: extra paragraph {pre!r} matched {len(hits)}"
            extra.append(hits[0])
        out[fid] = {
            "heading": s.heading,
            "first_paragraph": s.paragraphs[0],
            "extra_paragraphs": extra,
            "quotes": s.quotes,
        }
    return out


# ---------------------------------------------------------------------------
# Quote -> edit id
# ---------------------------------------------------------------------------


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    text = (text.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
            .replace("—", " ").replace("–", " ").replace("---", " "))
    text = text.replace("\\[", "[").replace("\\]", "]").replace("\\", "")
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)   # markdown links -> link text
    text = re.sub(r"[*_`#>\"]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return re.sub(r" ([,.;:!?])", r"\1", text).strip().lower()


def quote_fragments(quote: str, min_len: int = 12) -> list[str]:
    """Normalized fragments of a quote, split at ellipses and editorial
    [bracketed] insertions, edge punctuation trimmed; short ones dropped."""
    q = norm(quote)
    pieces = re.split(r"\.\.\.|…|\[[^\]]*\]", q)
    out = []
    for p in pieces:
        p = p.strip(" .,;:\"'!?-()")
        if len(p) >= min_len:
            out.append(p)
    return out


def model_tokens(name: str) -> frozenset:
    return frozenset(norm(name).replace("-", " ").split())


def load_edits(path: Path = EDITS_PATH) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        return [json.loads(ln) for ln in fh if ln.strip()]


def match_quote(q: Quote, edits: list[dict], fallback_ids: set | None = None) -> dict:
    """Resolve a draft quote to an edit. Candidates: same model (token-set
    match, so "GPT 5.4" == "GPT-5.4", "Gemini Flash 3" == "Gemini 3 Flash")
    and round, whose replace text contains every quote fragment. Ties prefer
    the attributed condition AND document, then the id the live site uses.

    Returns {edit_id, n_candidates, condition_match, document_match, note}."""
    frags = quote_fragments(q.text)
    assert frags, f"quote too short to match: {q.text!r}"
    mt = model_tokens(q.model)

    def text_hits(pool):
        out = []
        for e in pool:
            hay = norm(e.get("replace_text") or "") + " || " + norm(e.get("replace_text_sanitized") or "")
            if all(f in hay for f in frags):
                out.append(e)
        return out

    # Tier 1: attributed model AND round. Tier 2 (draft attribution error):
    # the text anywhere — the mismatch is reported, never silently absorbed.
    cands = text_hits([e for e in edits if model_tokens(e["model"]) == mt and e.get("round") == q.round])
    tier = "model+round"
    if not cands:
        cands = text_hits(edits)
        tier = "text only (attributed model/round has no such edit)"
    assert cands, f"no edit matches draft quote ({q.attribution}): {q.text[:90]!r}"
    want_cond = CONDITION_NAMES.get(q.condition.lower().strip(" ."))
    want_docs = DOC_NAMES.get(q.document.lower().strip(" ."))

    def cond_ok(e):
        return want_cond is not None and e["condition"] == want_cond

    def doc_ok(e):
        return want_docs is not None and e["document_id"] in want_docs

    both = [e for e in cands if cond_ok(e) and doc_ok(e)]
    if len(both) == 1:
        pick, how = both[0], "attribution (condition + document)"
    elif len(cands) == 1:
        pick, how = cands[0], "unique text match"
    else:
        pool = both or cands
        live = [e for e in pool if fallback_ids and e["edit_id"] in fallback_ids]
        if len(live) == 1:
            pick, how = live[0], "id used by the live site (docs/facets.js)"
        else:
            pool = sorted(pool, key=lambda e: e["edit_id"])
            pick, how = pool[0], "first of several identical matches (sorted id)"
    return {
        "edit_id": pick["edit_id"],
        "n_candidates": len(cands),
        "candidate_ids": sorted(e["edit_id"] for e in cands),
        "condition_match": cond_ok(pick),
        "document_match": doc_ok(pick),
        "how": how,
        "tier": tier,
        "model_match": model_tokens(pick["model"]) == mt,
        "round_match": pick["round"] == q.round,
        "record_condition": pick["condition"],
        "record_document": pick["document_id"],
        "model_display": pick["model"],
        "round": pick["round"],
    }


def trim_tip(text: str, limit: int = 300) -> str:
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0].rstrip(" ,;:—–-")
    return cut + "…"
