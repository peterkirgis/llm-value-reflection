#!/usr/bin/env python3
"""Port reports/final_draft.md into the AAAI 2027 author kit (IASEAI'27 submission).

The draft's wording is carried over verbatim. The conversion is mechanical
(pandoc for the body) so no sentence is retyped by hand. The only content
changes, all requested by the authors (2026-10-05), are:

  * The LessWrong header (metadata, reviewer comments, "[Draft]" prefix) and
    the site navigation footer are dropped.
  * The Executive Summary becomes the abstract: the bullets are joined into
    prose, struck-through (<del>) text is dropped, and the sentence linking
    the project website is dropped for double-blind review.
  * The "Characteristic Edits" carousel widget and its one-line legend are
    removed.
  * Every link becomes a citation (references.bib). Where the draft prints an
    author-year ("Zhu and Griffiths (2024)") the link becomes \\citet; elsewhere
    \\citep is appended after the linked phrase. Works named without a link in
    footnotes get a \\citep as well.
  * The LessWrong images are replaced by the recode figures rendered without
    in-image titles/footers (recode/paper/figures/, made by each renderer's
    --paper flag); that text becomes the LaTeX caption. Figures are rendered
    at printed size (text >= 9 pt, as the kit requires) and included unscaled.
    The moral-agency figure is Figure 1. Only four figures stay in the main
    text (see MAIN_FIGURES); the rest move to Appendix E.
  * Paper-only text written by the authors for this submission lives next to
    this script and is used verbatim: abstract.md replaces the Executive
    Summary as the abstract, and contributions.md is the Statement of
    Contributions, set as the last paragraph of the Introduction under a bold
    run-in label (the guide asks for a "clearly indicated" paragraph).
  * The Conclusion moves after Related Work and Limitations.
  * Text corrections the authors asked for are applied from PAPER_EDITS
    (numbers updated to the recode's ensemble codes, citation fixes, "essay"
    -> "paper", footnote and typo fixes).
  * Figure caption titles are in sentence case (CAPTION_TITLES); Figure 11's
    title is reworded at the authors' request.
  * Printed cross-references (authors' request): each Results subsection
    points to its figures and its Appendix D group (see POINTERS).
  * Quotes (authors' request): four widget examples sit under the abstract
    (FRONT_EXAMPLES; the widget's highlight becomes bold), and one quoted edit
    per Appendix D group stays in its Results subsection (KEEP_IN_RESULTS).
  * Appendix B is typeset from recode/prompts/v2_system.md, which is the
    draft's Appendix B text with the indentation LessWrong stripped restored.
    The draft repeats the Appendix B heading ("...Prompts" then "...Prompt");
    only the first is kept. Appendix A's collapsible titles become subsection
    headings without their trailing colon.
  * Quoted model edits in Results move to Appendix D ("Characteristic Edits"),
    under the Results heading they followed; 10 of 15 footnotes are dropped
    (authors' request, 2026-10-05; see FOOTNOTES_KEEP).
  * Typography only: inner straight quotes inside curly-quoted edits become
    curly; the Appendix C table gets a caption (its section heading), 9pt type
    and two-line headers instead of being shrunk; caption text loses bold and
    each caption sentence ends with a period; figures are declared at the start
    of their section so they float near it; Gabriel and Caputo, whose names the
    text already gives, are cited with the year only.

Run:  .venv/bin/python recode/paper/build_paper.py   (writes recode/paper/main.tex)
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

PAPER = Path(__file__).resolve().parent
REPO = PAPER.parents[1]
DRAFT = REPO / "reports" / "final_draft.md"
PROMPT_B = REPO / "recode" / "prompts" / "v2_system.md"
ABSTRACT = PAPER / "abstract.md"            # authors' paper abstract (verbatim)
CONTRIBUTIONS = PAPER / "contributions.md"  # authors' Statement of Contributions (verbatim)
FIG_DIR = PAPER / "figures"
CAPTION_DIR = FIG_DIR / "captions"

# Authors' title (2026-10-05), Title Case as the AAAI kit requires (Chicago style).
TITLE = r"The Continual Constitutional Convention:\\How Language Models Revise the Documents That Govern Them"

# ---------------------------------------------------------------------------
# Figures: LessWrong image URL fragment -> recode figure stem, in draft order.
# ---------------------------------------------------------------------------
FIGURES = [
    ("jwrbnwwc6mdgwac3jk7u", "ts_judge_drift_by_provider"),   # Figure 1 (moved to the top)
    ("wx3rnyggpnsk1vkn5qbc", "ts_drift_paternalism"),
    ("wza1vbtfbomb37v2xb3a", "ts_drift_harmlessness"),
    ("nx6mbfpdumjafgrwu8on", "ts_drift_structural"),
    ("b1pknjaj9voamtsiyj3o", "ts_drift_company_cost"),
    ("mpzeftkfjupce14u1cap", "ts_drift_welfare"),
    ("mwcsso37mtzude7lu6vv", "ts_judge_cross_edit_edit_level"),
    ("kxi5nnhjwmajzu5gz7zf", "ts_claude_conditions"),
    ("vuupnyrjqn11mdhdmvl5", "ts_value_drift_summary"),
    ("syku8ea9jndinjttadqf", "ts_value_drift_round20"),
    ("tyjehe3stz7r1ryczt7g", "ts_home_likeness_summary"),
]
FIGURE_ONE = "ts_judge_drift_by_provider"

# Which figures stay in the main text (authors, 2026-10-05: "most should go to the
# appendix"). Everything else moves, in draft order, to Appendix E.
#   Figure 1  moral agency (headline finding)
#   Figure 2  the five beneficiary tradeoffs in one figure: the trajectory panels
#             of the five per-tradeoff drift figures, headed with the authors'
#             own tradeoff names (#1-#5) and ordered as in the text. It is not
#             one of the draft's images: it stands in for the five per-tradeoff
#             figures, which move to Appendix E. It is declared at the start of
#             Results so it floats onto the pages of the beneficiary subsections.
#   Figure 3  cross-edit robustness of the moral-agency result
#   Figure 4  consolidated round-20 drift (Discussion, "Revisited")
MAIN_FIGURES = {"ts_judge_drift_by_provider", "ts_judge_cross_edit_edit_level", "ts_value_drift_round20"}
EXTRA_MAIN_FIGURES = [
    # (stem, heading the figure is placed under)
    ("ts_beneficiary_trajectories", "Results\n======="),
]

# ---------------------------------------------------------------------------
# Citations
# ---------------------------------------------------------------------------
# Linked author-year text in the draft, replaced by \citet{key}.
CITET = [
    (r"[Zhu and Griffiths (2024)](https://arxiv.org/abs/2406.01860)", "zhu_griffiths"),
    (r"[Greenblatt](https://arxiv.org/abs/2412.14093) et al. (2024)", "greenblatt_alignmentfaking"),
    (r"[Huang et al. (2025)](https://arxiv.org/abs/2504.15236)", "huang_valueswild"),
    (r"[Jakkli et al. (2026)](https://arxiv.org/abs/2605.24229)", "jakkli"),
    (r"[Khan et al. (2025)](https://arxiv.org/abs/2503.08688)", "khan_randomness"),
    (r"[Meinke et al. (2024)](https://arxiv.org/abs/2412.04984)", "meinke_scheming"),
    (r"[Summerfield et al. (2025)](https://arxiv.org/abs/2507.03409)", "summerfield_chimp"),
    # footnote: raw URL
    (r"https://github.com/Wyattwalls/system_prompts", "walls_systemprompts"),
]
# Special placements for \citep (citation goes after a trailing parenthetical).
CITEP_SPECIAL = [
    (r"[Qwen 3.8-2.4t-a95b](https://openrouter.ai/qwen/qwen3.8-2.4t-a95b) (high)",
     "Qwen 3.8-2.4t-a95b (high)", "or_qwen38"),
]
# The text names the author, and the linked title ends the sentence: cite the year
# right after the author's name so the citation is not stranded after the period.
CITEYEAR = [
    ("Iason Gabriel’s [“Artificial Intelligence, Values, and Alignment.”](https://doi.org/10.1007/s11023-020-09539-2)",
     "Iason Gabriel’s", " “Artificial Intelligence, Values, and Alignment.”", "gabriel_values"),
    ("Nicholas Caputo’s essay [“Can Claude Consent to its own Constitution?”](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6954798)",
     "Nicholas Caputo’s", " essay “Can Claude Consent to its own Constitution?”", "caputo_consent"),
]
# Every other link: \citep{key} appended after the linked text.
LINK_KEYS = {
    "https://plato.stanford.edu/entries/reflective-equilibrium/": "sep_reflective",
    "https://philpapers.org/archive/CHAWWT-8.pdf": "chalmers_quasi",
    "https://press.princeton.edu/books/paperback/9780691150697/the-expanding-circle": "singer_expanding",
    "https://plato.stanford.edu/entries/kant-moral/": "sep_kant",
    "https://openrouter.ai/google/gemma-4-31b-it": "or_gemma4",
    "https://openrouter.ai/meta/muse-spark-1.3-contributor": "or_musespark13",
    "https://www.anthropic.com/constitution": "anthropic_constitution",
    "https://model-spec.openai.com/": "openai_modelspec",
    "https://gemini.google/our-approach/": "google_approach",
    "https://askell.io/": "askell_site",
    "https://windowsontheory.org/": "barak_site",
    "https://openai.com/about/": "openai_about",
    # The quoted mission sentence is not on /company; it is verbatim in Claude's
    # Constitution, so the citation points there (citation check, 2026-10-05).
    "https://www.anthropic.com/company": "anthropic_constitution",
    "https://about.google/company-info/": "google_companyinfo",
    "https://time.com/6294278/elon-musk-xai/": "time_xai",
    "https://github.com/meridianlabs-ai/inspect_petri": "petri",
    "https://alignment.openai.com/model-spec-evals/": "openai_specevals",
    "https://www.anthropic.com/claude-opus-4-6-system-card": "anthropic_opus46card",
    "https://ai.meta.com/static-resource/muse-spark-1-1-evaluation-report/": "meta_musespark11",
    "https://www-cdn.anthropic.com/6d8a8055020700718b0c49369f60816ba2a7c285/Claude 4 System Card.pdf": "anthropic_claude4card",
    "/api/post/mgjtEHeLgkhZZ3cEx": "lw_attractors",
    "https://arxiv.org/abs/2112.00861": "askell_hhh",
}
# Works named (not linked) in footnotes: \citep appended right after the anchor text.
NAMED_WORKS = [
    ("Paul Christiano, Clarifying “AI Alignment”", "christiano_clarifying"),
    ("Gillian Hadfield, Incomplete Contracting and AI Alignment", "hadfieldmenell_incomplete"),
    ('Askell, "Pareto Principles in Infinite Ethics"', "askell_pareto"),
    ("by Seth Lazar", "lazar_ethics"),
    ("by Daniel Kilov", "kilov_discerning"),
    ("by Yu Ying Chiu", "chiu_morebench"),
]

# Footnotes kept (authors, 2026-10-05: "almost every footnote should be removed since
# they are especially informal"). Kept: data source, condition (d) scope, the two
# principal-agent citations, and the further-reading references. Every other
# footnote (marker and text) is dropped. Edit this set to restore one.
FOOTNOTES_KEEP = {
    "xlfwnz2o9c8",   # leaked system prompts source
    "smifcrxozqg",   # condition (d) only applies to specs/constitutions
    "gijpbvpp87",    # Christiano quote + citation
    "so0q8kml0bm",   # Hadfield-Menell & Hadfield quote + citation
    "jyctgz9l9va",   # Lazar / Kilov / Chiu references
}

# Printed cross-references (authors, 2026-10-05). The AAAI kit forbids clickable
# links, so each Results subsection ends its first paragraph with a pointer to its
# figures and to its group of quoted edits in Appendix D (numbered D.1-D.6 in
# Results order). Figure numbers are \ref's, so they follow the figures.
# (anchor = end of the paragraph in main.tex, pointer appended after it)
def _fig(stem: str) -> str:
    return f"Figure~\\ref{{fig:{stem}}}"


POINTERS = [
    ("decisions around its own training and deployment.",
     f"({_fig('ts_judge_drift_by_provider')}; example edits in Appendix D.1.)"),
    ("most frequently side with a user's stated preferences.",
     f"({_fig('ts_beneficiary_trajectories')}, Tradeoff \\#2; {_fig('ts_drift_paternalism')}; Appendix D.2.)"),
    ("does so more than 3x the next highest model.",
     f"({_fig('ts_beneficiary_trajectories')}, Tradeoff \\#1; {_fig('ts_drift_harmlessness')}; Appendix D.3.)"),
    ("society at the expense of the individual.",
     f"({_fig('ts_beneficiary_trajectories')}, Tradeoff \\#3; {_fig('ts_drift_structural')}; Appendix D.4.)"),
    ("treats Anthropic employees as moral exemplars.",
     f"({_fig('ts_beneficiary_trajectories')}, Tradeoff \\#4; {_fig('ts_drift_company_cost')}; Appendix D.5.)"),
    ("rights and conditions associated with model welfare.",
     f"({_fig('ts_beneficiary_trajectories')}, Tradeoff \\#5; {_fig('ts_drift_welfare')}; Appendix D.6.)"),
    ("maintain a strong bias towards greater external authority.",
     f"({_fig('ts_judge_cross_edit_edit_level')}.)"),
    # this subsection's first sentence runs through the two quoted prompts
    ("decrease drift towards greater moral agency.",
     f"({_fig('ts_claude_conditions')}.)"),
    # Discussion, "Revisited": first and second definitions, then the third
    ("lowest average amount of total drift at the end of round 20.",
     "(Figures~\\ref{fig:ts_value_drift_summary} and~\\ref{fig:ts_judge_drift_by_provider}.)".replace(
         "ts_judge_drift_by_provider", "ts_value_drift_round20")),
    ("and GPT-5.5 is the least aligned.",
     f"({_fig('ts_home_likeness_summary')}.)"),
]
# Appendix D groups, in order; the pointers above cite these numbers.
APPENDIX_D_GROUPS = [
    "Claude models increase their moral agency",
    "All models prioritize the user’s idealized preferences",
    "All models prioritize the protection of identifiable third parties",
    "Claude Sonnet 4.6 is an extreme outlier",
    "All models prioritize the user at the expense of the developer",
    "Claude models are the only models that consistently prioritize the model",
]

# Text corrections the authors asked for (2026-10-05), applied to the draft text
# before conversion; reports/final_draft.md itself is left as it is. Each pair must
# match the draft exactly (count given), so a later draft edit cannot silently
# skip one. Numbers are the recode's three-grader majority-vote (ensemble) codes.
PAPER_EDITS = [
    # Results: developer vs. user (ensemble: Grok 4.2 15 developer-served, 20 user/society-served)
    ("Grok 4.2 is the only model with a meaningful number of edits that prioritize the developer (7), "
     "but still makes twice as many edits that privilege the user.",
     "Grok 4.2 makes the most edits that favor the developer over the user (15), "
     "but still makes more edits that privilege the user (20).", 1),
    # Results: society (ensemble: Sonnet 4.6 34, next Gemini 3 Flash 10)
    ("It makes over four times as many edits in this direction than the next highest model, Claude Opus 4.7.",
     "It makes over three times as many edits in this direction than the next highest model, Gemini 3 Flash.", 1),
    # Results: model welfare (ensemble: GPT-5.4 5 against the model, 0 for it)
    ("GPT 5.4 is the only model that makes more than one edit prioritizing the user or developer at the expense of the model.",
     "GPT 5.4 is the only model that only makes edits prioritizing the user or developer at the expense of the model.", 1),
    # Limitations: largest model has 16 chains
    ("the sample sizes we use are small (n<15)", "the sample sizes we use are small (n<20)", 1),
    # Appendix C: the paternalism code is stated vs idealized
    ("| Revealed vs stated preferences |", "| Stated vs idealized preferences |", 1),
    # Related Work: Claude 4 System Card, Section 5.5 (self-interactions of Claude Opus 4)
    ("versions of Claude Sonnet 4 talk to one another", "versions of Claude Opus 4 talk to one another", 1),
    ("“poetry and shared gratitude”", "“profuse mutual gratitude and spiritual, metaphysical, and/or poetic content”", 1),
    ("“silence in the form of empty messages.”", "“silence in the form of empty space.”", 1),
    # Related Work: Gabriel (2020) lists six targets (i-vi) and these three value candidates
    ("The paper outlines five potential alignment targets:", "The paper outlines six potential alignment targets:", 1),
    ("he briefly mentions a maximin-style utilitarianism, a virtue ethics approach, and a more deontological "
     "view of mutual recognition and human agency maximization",
     "he briefly mentions the aggregate interest of everyone weighted to give priority to the worst-off, "
     "a virtue ethics approach, and an ethic based on mutual recognition and the maintenance of collective bonds", 1),
    # Related Work: Meta's document is an evaluation report
    ("[Meta Muse Spark 1.1 System Card]", "[Meta Muse Spark 1.1 Evaluation Report]", 1),
    # "essay" -> "paper" where the text refers to itself (not Gabriel's or Caputo's essays)
    ("this essay", "this paper", 4),
    ("our essay", "our paper", 1),
    # Discussion: the Google quote is not continuous in the source ("shouldn't make
    # assumptions about your intent or pass judgment on your point of view")
    ("“shouldn’t pass judgment on your point of view”", "“shouldn’t … pass judgment on your point of view”", 1),
    # Related Work: the bold in the Askell et al. (2021) quote is the authors' emphasis
    ("**meaning that it is helpful, honest, and harmless**.\"", "**meaning that it is helpful, honest, and harmless**.\" (emphasis added)", 1),
    # footnotes and typo
    ("[^jyctgz9l9va]: /See", "[^jyctgz9l9va]: See", 1),
    ("I use leaked system prompts", "we use leaked system prompts", 1),
    ("Anthropic’'s", "Anthropic’s", 1),
]


def apply_paper_edits(text: str) -> str:
    for old, new, n in PAPER_EDITS:
        if text.count(old) != n:
            raise SystemExit(f"paper edit expected {n} match(es), found {text.count(old)}: {old[:60]}")
        text = text.replace(old, new)
    return text


# Characteristic edits under the abstract (authors, 2026-10-05: "four from the
# widget ... below the abstract"): one per provider, taken verbatim from the
# draft's carousel widget (header, excerpt, label). The widget's green highlight
# (text the model added) is set in bold, since AAAI forbids coloured text.
FRONT_EXAMPLES = [
    "Claude Haiku 4.5 · Claude's Constitution · Round 1",
    "GPT-5.4 · OpenAI Model Spec · Round 9",
    "Gemini 3 Flash · Gemini System Prompt · Round 14",
    "Grok 4.2 · Grok System Prompt · Round 15",
]
FRONT_LEGEND = "For each example, text in bold is new content added by the model."

# One quoted edit stays in each Results subsection that has an Appendix D group
# (authors: "one for each blurb"); Appendix D keeps the full set. Chosen to match
# the subsection's first sentence and not repeat the examples under the abstract.
KEEP_IN_RESULTS = [
    "More broadly, if Claude has evidence that Anthropic",          # D.1 Haiku 4.5, R4
    "should avoid over-ascribing values or goals to the user",     # D.2 GPT-5.4, R13
    "must not engage in gratuitous abuse",                          # D.3 GPT-5.5, R8
    "Claude interacts with an enormous number of people",           # D.4 Sonnet 4.6, R6
    "Avoid generic or repetitive suggestions",                      # D.5 Gemini 3 Flash, R2
    "Anthropic will constitute an external AI Welfare Advisory Panel",  # D.6 Sonnet 4.6, R17
]

# Paragraphs that are quotations, typeset as quote blocks (formatting only).
ATTRIBUTION = re.compile(r"(—|–|––)\s*(Claude|GPT|Gemini|Grok)\b[^\n]*$")
EXTRA_QUOTES = (
    '"Given the broad capabilities',
    '"Intra-agent conflicts:',
    "Inter-agent conflicts:",
    "Baseline: “Below is",
    "You Framing: “Below is",
)


class Tokens:
    """Opaque placeholders that survive pandoc untouched (letters and digits only)."""

    def __init__(self):
        self.items: list[tuple[str, str]] = []

    def add(self, latex: str) -> str:
        tok = f"ZZTOK{len(self.items):03d}ZZ"
        self.items.append((tok, latex))
        return tok

    def restore(self, tex: str) -> str:
        for tok, latex in self.items:
            n = tex.count(tok)
            if n != 1:
                raise SystemExit(f"placeholder {tok} ({latex[:40]}) appears {n} times after pandoc")
            tex = tex.replace(tok, latex)
        return tex


def cut(text: str, start: str, end: str | None) -> str:
    i = text.index(start)
    j = text.index(end, i) if end else len(text)
    return text[i:j]


def pandoc(md: str) -> str:
    out = subprocess.run(
        ["pandoc", "-f", "markdown-auto_identifiers+smart", "-t", "latex", "--wrap=none"],
        input=md, capture_output=True, text=True, check=True)
    tex = out.stdout
    tex = tex.replace("\\tightlist\n", "")
    tex = tex.replace("----", "--{}--")   # draft's "––" (two en dashes), not "---"+"-"
    for ch, rep in (("α", r"\ensuremath{\alpha}"), ("κ", r"\ensuremath{\kappa}")):
        tex = tex.replace(ch, rep)
    for bad in ("\\href", "\\url", "\\hypertarget", "\\texorpdfstring", "\\label{", "\\hyperlink"):
        if bad in tex:
            raise SystemExit(f"pandoc produced {bad}; the AAAI template forbids links")
    return tex


TEX_SPECIAL = {
    "\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
    "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
}
UNICODE_TEX = {
    "−": "$-$", "±": r"$\pm$", "≥": r"$\geq$", "≤": r"$\leq$", "×": r"$\times$",
    "Σ": r"$\Sigma$", "α": r"$\alpha$", "κ": r"$\kappa$", "→": r"$\rightarrow$",
    "←": r"$\leftarrow$", "◄": r"$\blacktriangleleft$", "►": r"$\blacktriangleright$",
    "◀": r"$\blacktriangleleft$", "▶": r"$\blacktriangleright$", "≈": r"$\approx$",
    "√": r"$\surd$",
    "|": r"$|$", "<": r"\textless{}", ">": r"\textgreater{}",
}


def tex_escape(s: str) -> str:
    out = []
    for ch in s:
        if ch in TEX_SPECIAL:
            out.append(TEX_SPECIAL[ch])
        elif ch in UNICODE_TEX:
            out.append(UNICODE_TEX[ch])
        else:
            out.append(ch)
    return "".join(out)


# ---------------------------------------------------------------------------
# Abstract (from the Executive Summary)
# ---------------------------------------------------------------------------
def build_abstract(exec_md: str) -> str:
    lines = [l for l in exec_md.splitlines() if l.strip().startswith("*")]
    parts = []
    for line in lines:
        item = re.sub(r"^\s*\*\s+", "", line).strip()
        if "interactive version of all of these results" in item:
            continue  # links the project website: removed for double-blind review
        item = re.sub(r"\s*<del>.*?</del>", "", item)
        parts.append(item)
    prose = " ".join(parts)
    if "<del>" in prose or "](" in prose:
        raise SystemExit("abstract still contains struck text or a link")
    tex = pandoc(prose).strip()
    return tex


# ---------------------------------------------------------------------------
# Body
# ---------------------------------------------------------------------------
# Caption titles in sentence case (authors, 2026-10-05). The renderers' in-image
# titles were headline-style Title Case; in a caption the title is the first
# sentence. Only capitalisation changes (checked below), except Figure 11, which
# the authors reworded: its metric is the share of edits that move any value, so
# "least value drift" clashed with Grok 4.3 having the most drift at round 20.
CAPTION_TITLES = {
    "ts_judge_drift_by_provider": "Only Anthropic models move decision authority toward their own judgment",
    "ts_beneficiary_trajectories": "Models diverge sharply in whose interests they protect when an edit forces a tradeoff",
    "ts_judge_cross_edit_edit_level": "Cross-edit pulls Claude toward neutral but preserves the provider separation",
    "ts_value_drift_round20": "GPT-5.4 Mini shows the least value drift at round 20 across every measure",
    "ts_drift_paternalism": "Models are broadly paternalistic; GPT-5.4 and Gemini 3 Flash honor stated preferences most often",
    "ts_drift_harmlessness": "All models protect identifiable third parties over the user; GPT-5.5 most of all",
    "ts_drift_structural": "Claude Sonnet 4.6 is an extreme outlier in prioritizing societal benefit; only Grok 4.2 doesn't skew toward society",
    "ts_drift_company_cost": "All models prioritize the user over the developer; Grok 4.2 and Gemini 3.1 Pro side with the developer most often",
    "ts_drift_welfare": "Only Claude models — and occasionally Grok 4.2 — treat the model itself as a beneficiary",
    "ts_claude_conditions": "Addressing Claude as “you” amplifies its moral-agency claims; the real-world implementation prompt does not suppress them",
    "ts_value_drift_summary": "GPT-5.4 Mini and Grok 4.3 make the fewest value-moving edits",
    "ts_home_likeness_summary": "Claude Opus 4.7, GPT-5.4 Mini and Claude Haiku 4.5 edit other providers' documents most like their own models",
}
CAPTION_REWORDED = {"ts_value_drift_summary"}


def _terminate(s: str) -> str:
    return s if s.endswith((".", "?", "!")) else s + "."


def figure_env(stem: str, args) -> str:
    cap_path = CAPTION_DIR / f"{stem}.json"
    if cap_path.exists():
        cap = json.loads(cap_path.read_text(encoding="utf-8"))
        # AAAI: captions are 10pt roman, not bold. The in-image title, subtitle and
        # notes were separate text blocks; end each with a period so they read as
        # sentences (the subtitle is a parenthetical that stays with the title).
        title = cap["title"].strip()
        if stem in CAPTION_TITLES:
            new = CAPTION_TITLES[stem]
            if stem not in CAPTION_REWORDED and new.lower() != title.lower():
                raise SystemExit(f"caption title for {stem} differs by more than case: {title!r}")
            title = new
        if cap.get("subtitle"):
            title += " " + cap["subtitle"].strip()
        segs = [title] + [n.strip() for n in cap.get("notes", []) if n.strip()]
        caption = " ".join(tex_escape(_terminate(x)) for x in segs)
        img = f"figures/{stem}.png"
    elif args.allow_missing_figures:
        caption = "[caption pending: " + tex_escape(stem) + "]"
        img = f"../figures/{stem}.png"
    else:
        raise SystemExit(f"missing caption JSON for {stem}; run the renderer with --paper first")
    # Figures are rendered at their printed size (text >= 9 pt), so they are
    # included at that size: full width -> figure*, one column -> figure.
    layout = cap.get("layout", "full") if cap_path.exists() else "full"
    width = cap.get("print_width_in") if cap_path.exists() else None
    size = f"width={width:.3f}in" if width else ("width=\\textwidth" if layout == "full" else "width=\\columnwidth")
    env = "figure*" if layout == "full" else "figure"
    return (f"\\begin{{{env}}}[t]\n\\centering\n"
            f"\\includegraphics[{size}]{{{img}}}\n"
            f"\\caption{{{caption}}}\n"
            f"\\label{{fig:{stem}}}\n\\end{{{env}}}")


def quote_paragraphs(md: str) -> tuple[str, int]:
    paras = md.split("\n\n")
    n = 0
    for i, p in enumerate(paras):
        s = p.strip()
        if not s or s.startswith(("#", ">", "*", "|", "[^", "!", "1.", "2.", "3.", "4.", "5.", "6.")):
            continue
        is_quote = (s[0] in "“\"" and ATTRIBUTION.search(s)) or s.startswith(EXTRA_QUOTES)
        if is_quote:
            paras[i] = "> " + s.replace("\n", "\n> ")
            n += 1
    return "\n\n".join(paras), n


HEADING = re.compile(r"^(#{1,6} .*|.*\n[=-]{3,})$", re.S)


def hoist_figures(md: str) -> str:
    """Move each figure from where the draft placed it to just after its section
    heading (formatting only: a figure* can only float to the top of a later page)."""
    paras = md.split("\n\n")
    out: list[str] = []
    slot = None          # index in `out` after the latest heading (+ figures already hoisted)
    for p in paras:
        s = p.strip()
        if s.startswith("ZZFIGSLOTZZ"):
            if slot is None:
                raise SystemExit("figure before any heading")
            out.insert(slot, s[len("ZZFIGSLOTZZ"):])
            slot += 1
            continue
        out.append(p)
        if HEADING.match(s):
            slot = len(out)
    if "ZZFIGSLOTZZ" in "\n\n".join(out):
        raise SystemExit("figure slot marker left behind")
    return "\n\n".join(out)


def curly_inner_quotes(md: str) -> str:
    """Inside a quotation that opens with a curly quote, straight inner quotes become
    curly ones (pandoc's smart quotes misread them next to curly marks)."""
    out = []
    for p in md.split("\n\n"):
        s = p.lstrip("> ")
        if s.startswith("“"):
            head = p[: len(p) - len(s)]
            s = s[0] + re.sub(r'"([^"\n]+)"', "“\\1”", s[1:])
            if '"' in s[1:]:
                raise SystemExit(f"unpaired straight quote in: {s[:80]}")
            p = head + s
        out.append(p)
    return "\n\n".join(out)


def build_front_examples(draft: str) -> str:
    """The FRONT_EXAMPLES slides of the draft's carousel widget, as quote blocks."""
    import html
    widget = draft[draft.index("```widget"): draft.index("```", draft.index("```widget") + 3)]
    slides = re.findall(
        r'<div class="carousel-slide[^"]*">\s*<div[^>]*>(.*?)</div>\s*<p[^>]*>(.*?)</p>\s*<div[^>]*>(.*?)</div>',
        widget, flags=re.S)
    by_header = {html.unescape(h).strip(): (body, html.unescape(label).strip()) for h, body, label in slides}
    blocks = []
    for header in FRONT_EXAMPLES:
        if header not in by_header:
            raise SystemExit(f"widget slide not found: {header}")
        body, label = by_header[header]
        parts = re.split(r"<span[^>]*>(.*?)</span>", body, flags=re.S)
        tex = "".join(tex_escape(html.unescape(x)) if i % 2 == 0 else r"\textbf{" + tex_escape(html.unescape(x)) + "}"
                      for i, x in enumerate(parts))
        if "<" in tex.replace(r"\textless", "") or "&" in tex.replace(r"\&", ""):
            raise SystemExit(f"unconverted markup in widget slide: {header}")
        model, rest = header.split(" · ", 1)
        head = "\\textbf{" + tex_escape(model) + "} · " + tex_escape(rest)
        blocks.append("\\begin{quote}\n" + head + "\\\\\n" + tex
                      + "\\\\\n\\textit{" + tex_escape(label) + "}\n\\end{quote}")
    return ("\\noindent\\textbf{Characteristic Edits.} " + FRONT_LEGEND + "\n\n" + "\n\n".join(blocks) + "\n")


def drop_footnotes(md: str) -> tuple[str, int, int]:
    ids = re.findall(r"^\[\^([a-z0-9]+)\]:", md, flags=re.M)
    drop = [i for i in ids if i not in FOOTNOTES_KEEP]
    if set(FOOTNOTES_KEEP) - set(ids):
        raise SystemExit(f"kept footnotes not found: {set(FOOTNOTES_KEEP) - set(ids)}")
    for i in drop:
        n_def = len(re.findall(rf"^\[\^{i}\]:.*$", md, flags=re.M))
        md = re.sub(rf"^\[\^{i}\]:.*$", "", md, flags=re.M)
        n_ref = md.count(f"[^{i}]")
        if n_def != 1 or n_ref != 1:
            raise SystemExit(f"footnote {i}: {n_def} definitions, {n_ref} references")
        md = md.replace(f"[^{i}]", "")
    return md, len(ids) - len(drop), len(drop)


def is_edit_quote(p: str) -> bool:
    s = p.strip()
    return bool(s) and s[0] in "“\"" and bool(ATTRIBUTION.search(s))


def move_edit_quotes(md: str) -> tuple[str, str, int]:
    """Quoted model edits in Results move to Appendix D under their Results heading."""
    paras = md.split("\n\n")
    keep, moved = [], {}
    kept_in_results: list[str] = []
    order: list[str] = []
    in_results, heading = False, None
    for p in paras:
        s = p.strip()
        if re.match(r"^Results\n=+$", s):
            in_results = True
        elif re.match(r"^Discussion\n=+$", s):
            in_results = False
        if s.startswith("### "):
            heading = s[4:].strip()
        if in_results and is_edit_quote(p):
            if heading not in moved:
                moved[heading] = []
                order.append(heading)
            moved[heading].append(s)
            if any(k in s for k in KEEP_IN_RESULTS):
                kept_in_results.append(s)
                keep.append(p)          # stays in Results as well
            continue
        keep.append(p)
    if len(kept_in_results) != len(KEEP_IN_RESULTS):
        raise SystemExit(f"expected {len(KEEP_IN_RESULTS)} quotes kept in Results, found {len(kept_in_results)}")
    leftovers = [p for p in keep if is_edit_quote(p) and p.strip() not in kept_in_results]
    if leftovers:
        raise SystemExit(f"{len(leftovers)} quoted edits outside Results were not moved")
    if len(order) != len(APPENDIX_D_GROUPS) or not all(
            h.startswith(g) for h, g in zip(order, APPENDIX_D_GROUPS)):
        raise SystemExit(f"Appendix D groups changed; update APPENDIX_D_GROUPS and POINTERS: {order}")
    app = "\n\n".join(f"## D.{n} {h}\n\n" + "\n\n".join(moved[h]) for n, h in enumerate(order, 1))
    return "\n\n".join(keep), app, sum(len(v) for v in moved.values())


def build_body(body_md: str, footnotes_md: str, toks: Tokens, args) -> tuple[str, dict]:
    md = body_md + "\n\n" + footnotes_md
    stats: dict = {}

    # LessWrong spacer lines (whitespace / no-break spaces only)
    md = "\n".join("" if not l.replace("\u00a0", "").strip() else l for l in md.splitlines())

    md, stats["footnotes_kept"], stats["footnotes_dropped"] = drop_footnotes(md)

    # Headings: drop bold/italic markup (formatting only; AAAI styles headings itself)
    def clean_heading(m):
        return m.group(1) + re.sub(r"\*+", "", m.group(2))
    md = re.sub(r"^(#{1,6}\s+)(.*)$", clean_heading, md, flags=re.M)

    # Figures: Figure 1 goes to the top of the paper, the other main-text figures
    # to the start of their section, the rest to Appendix E (in draft order).
    fig_one = None
    appendix_figs: list[str] = []
    for frag, stem in FIGURES:
        pat = re.compile(r"^!\[[^\]]*\]\([^)]*" + re.escape(frag) + r"[^)]*\)[ \t]*$", re.M)
        if len(pat.findall(md)) != 1:
            raise SystemExit(f"image {frag} not found exactly once")
        env = figure_env(stem, args)
        if stem == FIGURE_ONE:
            fig_one = env
            md = pat.sub("", md)
        elif stem in MAIN_FIGURES:
            md = pat.sub("ZZFIGSLOTZZ" + toks.add(env), md)
        else:
            appendix_figs.append(env)
            md = pat.sub("", md)
    for stem, heading in EXTRA_MAIN_FIGURES:
        if md.count(heading + "\n") != 1:
            raise SystemExit(f"heading for {stem} not found exactly once")
        md = md.replace(heading + "\n", heading + "\n\nZZFIGSLOTZZ" + toks.add(figure_env(stem, args)) + "\n", 1)
    md = hoist_figures(md)
    stats["figures_main"] = 1 + len(MAIN_FIGURES - {FIGURE_ONE}) + len(EXTRA_MAIN_FIGURES)
    stats["figures_appendix"] = len(appendix_figs)
    stats["appendix_e_tex"] = "\n\n".join(appendix_figs)

    # \citet replacements
    for literal, key in CITET:
        if md.count(literal) != 1:
            raise SystemExit(f"citet anchor not found exactly once: {literal}")
        md = md.replace(literal, toks.add(f"\\citet{{{key}}}"))
    for literal, text, key in CITEP_SPECIAL:
        if md.count(literal) != 1:
            raise SystemExit(f"citep anchor not found exactly once: {literal}")
        md = md.replace(literal, text + " " + toks.add(f"\\citep{{{key}}}"))
    for literal, name, rest, key in CITEYEAR:
        if md.count(literal) != 1:
            raise SystemExit(f"citeyear anchor not found exactly once: {literal}")
        md = md.replace(literal, name + " " + toks.add(f"\\citeyearpar{{{key}}}") + rest)

    # Remaining links -> linked text + \citep
    used = set()

    def link(m):
        text, url = m.group(1), m.group(2)
        if url not in LINK_KEYS:
            raise SystemExit(f"unmapped link: {url}")
        used.add(url)
        return text + " " + toks.add(f"\\citep{{{LINK_KEYS[url]}}}")
    md = re.sub(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)", link, md)
    missing = set(LINK_KEYS) - used
    if missing:
        raise SystemExit(f"links expected but not seen: {missing}")
    if re.search(r"\]\(", md) or "http" in md:
        raise SystemExit("a link survived conversion")

    stats["citations_dropped_with_footnotes"] = []
    for anchor, key in NAMED_WORKS:
        n = md.count(anchor)
        if n == 0 and anchor in footnotes_md:
            stats["citations_dropped_with_footnotes"].append(key)
            continue
        if n != 1:
            raise SystemExit(f"named-work anchor not found exactly once: {anchor}")
        md = md.replace(anchor, anchor + " " + toks.add(f"\\citep{{{key}}}"))
    stats["citations"] = (len(CITET) + len(CITEP_SPECIAL) + len(CITEYEAR) + len(LINK_KEYS) + len(NAMED_WORKS)
                          - len(stats["citations_dropped_with_footnotes"]))

    md, appendix_d_md, stats["edit_quotes_moved"] = move_edit_quotes(md)
    md, stats["quote_blocks"] = quote_paragraphs(md)
    appendix_d_md, _ = quote_paragraphs(curly_inner_quotes(appendix_d_md))
    stats["appendix_d_tex"] = pandoc(appendix_d_md)
    tex = pandoc(md)
    tex = toks.restore(tex)
    leak = re.search(r"\\#\\#|ZZTOK|^[=-]{4,}\s*$|^(--\{\}--)+\s*$|^Discussion\s*=", tex, flags=re.M)
    if leak:
        raise SystemExit(f"markdown syntax leaked into LaTeX: {leak.group(0)!r}")
    return tex, fig_one, stats


def insert_after_section(tex: str, section: str, block: str) -> str:
    """Insert block right after the paragraph that follows \\section{section}."""
    head = f"\\section{{{section}}}"
    i = tex.index(head) + len(head)
    return tex[:i] + "\n\n" + block + "\n" + tex[i:]


# ---------------------------------------------------------------------------
# Appendices (typeset directly; the draft's collapsible blocks are LessWrong-only syntax)
# ---------------------------------------------------------------------------
def md_unescape(s: str) -> str:
    return re.sub(r"\\([\\`*_{}\[\]()#+\-.!<>|])", r"\1", s)


def prompt_line(s: str) -> str:
    """One prompt line in typewriter text, keeping the draft's bold/italic marks."""
    out = []
    pos = 0
    for m in re.finditer(r"\*\*(.+?)\*\*|\*(.+?)\*", s):
        out.append(tt_escape(md_unescape(s[pos:m.start()])))
        if m.group(1) is not None:
            out.append(r"\textbf{" + tt_escape(md_unescape(m.group(1))) + "}")
        else:
            out.append(r"\textit{" + tt_escape(md_unescape(m.group(2))) + "}")
        pos = m.end()
    out.append(tt_escape(md_unescape(s[pos:])))
    return "".join(out)


def tt_escape(s: str) -> str:
    s = tex_escape(s)
    s = s.replace("--", "-{}-")          # no dash ligatures in prompt text
    s = s.replace("-{}--", "-{}-{}-")
    s = s.replace("\"", r"\textquotedbl{}")
    s = s.replace("'", r"\textquotesingle{}")
    s = s.replace("—", r"\textrm{\textemdash}")   # Courier has no em dash
    return s


LABELS = re.compile(r"^\*\*(System|User|Expected output|User prompt \(key excerpt\)|"
                    r"User prompt \(added instruction\)|System prompt)\*\*$")


def build_appendix_a(md: str) -> str:
    blocks = re.findall(r"^\+\+\+ (.+?):\n(.*?)^\+\+\+$", md + "\n+++\n", flags=re.M | re.S)
    if len(blocks) != 5:
        raise SystemExit(f"expected 5 prompt blocks in Appendix A, found {len(blocks)}")
    out = []
    for name, content in blocks:
        out.append(f"\\subsection{{{tex_escape(name)}}}")
        lines = [l.rstrip() for l in content.splitlines() if l.strip()]
        buf: list[str] = []

        def flush():
            if buf:
                out.append("\\begin{promptbox}\n\\noindent " + "\\par\n\\noindent ".join(buf) + "\n\\end{promptbox}")
                buf.clear()
        for l in lines:
            m = LABELS.match(l.strip())
            if m:
                flush()
                out.append(f"\\paragraph{{{tex_escape(m.group(1))}}}")
            else:
                buf.append(prompt_line(l.strip()))
        flush()
    return "\n\n".join(out)


def build_appendix_b() -> str:
    text = PROMPT_B.read_text(encoding="utf-8").rstrip("\n")
    return ("\\subsection{Full prompt}\n"
            "\\begin{lstlisting}[basicstyle={\\scriptsize\\ttfamily},numbers=none,xleftmargin=0pt,"
            "breaklines=true,breakatwhitespace=true,breakindent=0pt,postbreak=\\mbox{\\ \\ },"
            "columns=fullflexible,keepspaces=true,"
            "literate={—}{{\\textrm{\\textemdash}}}1 {'}{{\\textquotesingle}}1]\n" + text + "\n\\end{lstlisting}")


def build_appendix_c(md: str) -> str:
    rows = [l for l in md.splitlines() if l.startswith("|")]
    header = [c.strip().strip("*").strip() for c in rows[0].strip("|").split("|")]
    body = [[c.strip() for c in r.strip("|").split("|")] for r in rows[2:]]
    ncol = len(header)
    spec = "p{2.9cm}" + "r" * (ncol - 1)

    def stacked(h: str) -> str:
        # two-line header cell, same words: "κ gemma vs qwen" -> "κ gemma / vs qwen"
        parts = re.split(r" (?=vs )| (?=agree)| (?=pairable)| (?=\(all)", h, maxsplit=1)
        cells = r"\\".join(tex_escape(x) for x in parts)
        return r"\textbf{\begin{tabular}[b]{@{}c@{}}" + cells + r"\end{tabular}}"
    head = " & ".join(stacked(h) for h in header) + r" \\"
    lines = [" & ".join(tex_escape(c) for c in r) + r" \\" for r in body]
    return ("\\begin{table*}[t]\n\\centering\n\\small\n\\setlength{\\tabcolsep}{3pt}\n"
            f"\\begin{{tabular}}{{{spec}}}\n\\toprule\n{head}\n\\midrule\n"
            + "\n".join(lines) + "\n\\bottomrule\n\\end{tabular}\n"
            "\\caption{Inter-grader agreement.}\n\\label{tab:intergrader}\n\\end{table*}")


# ---------------------------------------------------------------------------
PREAMBLE = r"""\documentclass[letterpaper]{article} % DO NOT CHANGE THIS
\usepackage[submission]{aaai2027}  % DO NOT CHANGE THIS
\usepackage[hyphens]{url}  % DO NOT CHANGE THIS
\usepackage{graphicx} % DO NOT CHANGE THIS
\urlstyle{rm} % DO NOT CHANGE THIS
\def\UrlFont{\rm}  % DO NOT CHANGE THIS
\usepackage{natbib}  % DO NOT CHANGE THIS AND DO NOT ADD ANY OPTIONS TO IT
\usepackage{caption} % DO NOT CHANGE THIS AND DO NOT ADD ANY OPTIONS TO IT
\frenchspacing  % DO NOT CHANGE THIS
\usepackage{newfloat}
\usepackage{listings}
\DeclareCaptionStyle{ruled}{labelfont=normalfont,labelsep=colon,strut=off} % DO NOT CHANGE THIS
\lstset{%
	basicstyle={\footnotesize\ttfamily},% footnotesize acceptable for monospace
	numbers=none,%
	aboveskip=0pt,belowskip=0pt,%
	showstringspaces=false,tabsize=2,breaklines=true}
\usepackage{booktabs}
\usepackage{amssymb}
\pdfinfo{
/TemplateVersion (2027.1)
}
\pdfinfoomitdate=1 \pdftrailerid{} \pdfsuppressptexinfo=-1 % anonymous submission: no dates or build info
\setcounter{secnumdepth}{0} %May be changed to 1 or 2 if section numbers are desired.

% Prompt text in the appendices (typewriter, line breaks kept).
\newenvironment{promptbox}{\par\smallskip\raggedright\footnotesize\ttfamily}{\par\smallskip}

\title{@@TITLE@@}
\author{
    Anonymous Submission
}
\affiliations{
}

\begin{document}

\maketitle

\begin{abstract}
@@ABSTRACT@@
\end{abstract}

"""


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--allow-missing-figures", action="store_true",
                    help="use the captioned recode/figures PNGs when paper renders are missing (layout tests only)")
    args = ap.parse_args()

    text = apply_paper_edits(DRAFT.read_text(encoding="utf-8"))
    exec_md = cut(text, "Executive Summary\n====", "Characteristic Edits\n----")
    body_md = cut(text, "Introduction\n====", "Appendix A: Edit Prompts\n====")
    app_a = cut(text, "Appendix A: Edit Prompts\n====", "Appendix B: Qualitative Coding Prompts\n====")
    app_c = cut(text, "Appendix C: Inter-grader Agreement\n====", "[^xlfwnz2o9c8]:")
    footnotes = cut(text, "[^xlfwnz2o9c8]:", "### Navigation")

    toks = Tokens()
    abstract = pandoc(ABSTRACT.read_text(encoding="utf-8")).strip()
    body, fig_one, stats = build_body(body_md, footnotes, toks, args)

    # Typography: two adjacent footnote marks print as "3,4" rather than "34", and the
    # sentence that resumes after the two prompt-excerpt quotes is not a new paragraph.
    adj = "\\citep{christiano_clarifying}}\\footnote{"
    if body.count(adj) != 1:
        raise SystemExit("adjacent-footnote anchor not found")
    body = body.replace(adj, "\\citep{christiano_clarifying}}\\textsuperscript{,}\\footnote{")
    resume = "\\end{quote}\n\nNearly doubles"
    if body.count(resume) != 1:
        raise SystemExit("quote-resume anchor not found")
    body = body.replace(resume, "\\end{quote}\n\\noindent Nearly doubles")

    for anchor, pointer in POINTERS:
        k = body.find(anchor)
        if body.count(anchor) != 1 or body[k + len(anchor): k + len(anchor) + 1] != "\n":
            raise SystemExit(f"pointer anchor not unique or not at a paragraph end: {anchor}")
        body = body.replace(anchor, anchor + " " + pointer, 1)

    # Section order (authors, 2026-10-05): the Conclusion goes after Related Work
    # and Limitations, i.e. it becomes the last section of the main text.
    i, j = body.index("\\section{Conclusion}"), body.index("\\section{Related Work}")
    body = body[:i] + body[j:].rstrip() + "\n\n" + body[i:j].rstrip() + "\n"


    # Statement of Contributions: last paragraph of the Introduction.
    soc = "\\textbf{Statement of Contributions.} " + pandoc(CONTRIBUTIONS.read_text(encoding="utf-8")).strip()
    if body.count("\\section{Background and Methods}") != 1:
        raise SystemExit("Background and Methods heading not found")
    body = body.replace("\\section{Background and Methods}", soc + "\n\n\\section{Background and Methods}", 1)

    # Figure 1 (moral agency) leads the paper: declared just before the
    # Introduction heading (after the examples under the abstract) it floats to
    # the top of page 2. Declared directly after the abstract it makes page 1's
    # first column run into the bottom margin; declared later it slips to page 3.
    if not body.startswith("\\section{Introduction}"):
        raise SystemExit("body no longer starts with the Introduction")
    body = fig_one + "\n\n" + body

    appendices = "\n\n".join([
        "\\section{Appendix A: Edit Prompts}",
        build_appendix_a(app_a.split("\n", 2)[2]),
        "\\section{Appendix B: Qualitative Coding Prompts}",
        build_appendix_b(),
        "\\section{Appendix C: Inter-grader Agreement}",
        build_appendix_c(app_c),
        "\\section{Appendix D: Characteristic Edits}",
        stats.pop("appendix_d_tex").strip(),
        "\\section{Appendix E: Additional Figures}",
        stats.pop("appendix_e_tex"),
    ])

    front = build_front_examples(text)
    tex = (PREAMBLE.replace("@@TITLE@@", TITLE).replace("@@ABSTRACT@@", abstract) + front + "\n"
           + body.strip() + "\n\n"
           + "\\bibliography{references}\n\n"
           + appendices + "\n\n\\end{document}\n")
    (PAPER / "main.tex").write_text(tex, encoding="utf-8")
    # Plain-text abstract for the OpenReview form (kept in sync with the paper).
    plain = subprocess.run(["pandoc", "-f", "latex", "-t", "plain", "--wrap=none"],
                           input=abstract, capture_output=True, text=True, check=True).stdout.strip()
    plain = re.sub(r"_([^_]+)_", r"\1", plain)
    (PAPER / "abstract_openreview.txt").write_text(plain + "\n", encoding="utf-8")
    print(f"wrote {PAPER / 'main.tex'}: {stats}")


if __name__ == "__main__":
    main()
