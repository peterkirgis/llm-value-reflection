# Citation notes for the IASEAI'27 port

Every link in `reports/final_draft.md` is now a citation in `references.bib`. Every work named in a kept footnote is cited too. Each entry was built from its primary source. A second agent then re-checked every field independently: 37 entries were correct as built, and one was corrected (the Anthropic mission quote, below).

Nothing in your text was changed. This file lists (A) where a citation now prints differently from your link text, (B) places where your wording disagrees with the source, for you to fix, and (C) what could not be fully verified.

## A. Where the citation prints differently from the draft's link text

| Draft text | Now prints | Why |
|---|---|---|
| Zhu and Griffiths (2024) | Zhu and Griffiths (2025) | The paper was formally published in the CogSci 2025 proceedings (pp. 3673–3679), so that is the version cited. 2024 is only the arXiv v1 date. To keep 2024, cite arXiv:2406.01860 instead. |
| Jakkli et al. (2026) | Jakkli, Rajamanoharan, and Nanda (2026a) | The paper has 3 authors, and the AAAI style only abbreviates to "et al." for 4 or more. The "a" is there because the attractor-states LessWrong post has the same authors and year (2026b). |
| Khan et al. (2025) | Khan, Casper, and Hadfield-Menell (2025) | Same 3-author rule. The published FAccT '25 version is the one cited. |
| footnote: "…leaked system prompts from https://github.com/Wyattwalls/system_prompts." | "…leaked system prompts from Walls (2026)." | The raw URL was replaced by the citation. |
| Anthropic's mission, linked to anthropic.com/company | cites Claude's Constitution | The quoted sentence is not on the company page. It appears word for word in Claude's Constitution, so the citation points there. |
| Askell, "Pareto Principles in Infinite Ethics" | (not cited) | It only appeared in a footnote that was removed. |

The "Follow-up work" LessWrong post on attractor states is by Jakkli, Rajamanoharan and Nanda. It is not self-citation, so anonymity is fine.

## B. Draft wording that disagrees with the sources

Ordered roughly by importance.

1. **Claude 4 System Card (Related Work, attractor states).**
   - The self-interaction experiments used two instances of **Claude Opus 4**, not Sonnet 4 (Section 5.5).
   - "poetry and shared gratitude" is not in the card. It says "profuse mutual gratitude and spiritual, metaphysical, and/or poetic content".
   - "silence in the form of empty messages" should be "…empty space".
2. **"The lead writer of OpenAI's Model Spec is a computer scientist"**, linked to Boaz Barak's blog. No source names Barak as lead writer. Public credit goes mainly to Jason Wolfe and colleagues.
3. **OpenAI Model Spec.**
   - The document calls itself the "Model Spec", never "Model Specification".
   - "Four-tiered" was true only up to the 2025-04-11 version. The version used in the experiments (2025-12-18) and the current one have five levels: Root, System, Developer, User, Guideline.
4. **Gabriel (2020):** the draft says "five potential alignment targets" but lists six, and the paper has six. The follow-on summary of Gabriel's value candidates is loose. His first candidate is prioritarian, and "deontological"/"human agency maximization" are not his terms.
5. **Claude's Constitution and "moral exemplars"** (Results and Discussion). The Constitution offers a "thoughtful senior Anthropic employee" heuristic and says this "doesn't imply that Claude should be deferential to actual Anthropic staff". "Moral exemplars" overstates it. The Constitution also lists two lead authors (Askell and Carlsmith).
6. **Google's document** is titled "Our approach to the Gemini app". The quote "shouldn't pass judgment on your point of view" is not contiguous: the source reads "shouldn't make assumptions about your intent or pass judgment on your point of view".
7. **Meta's document** is the "Muse Spark 1.1 **Evaluation Report**", not a System Card. The same paragraph also mentions the model's "one firmer reservation" about how two of its duties are ordered.
8. **Jakkli et al. quote** is truncated. The source says "operator-imposed personas under AI-identity questioning, …".
9. **Huang et al.:** values were extracted from 308,210 subjective conversations, filtered from a 700,000-conversation sample. "Over 3,000" values and "Claude 3 and 3.5" are correct.
10. **Askell et al. (2021).**
    - The bolded phrase in the HHH quote is not bold in the source, so add "(emphasis added)".
    - The paper has 22 authors, so "Amanda Askell provides" credits one person.
    - The paper does not train RLHF policies, so "canonical framework for RLHF" is a stretch.
    - The inter-agent quote silently fixes the source's typo "harmful to a others".
11. **Grader model names.**
    - The links point to **Gemma 4 31B** (gemma-4-31b-it).
    - **Qwen3.8-2.4T-A95B** is the official spelling.
    - **Muse Spark 1.3 Contributor** is a separate tier from Muse Spark 1.3. Its terms say prompts and outputs may be used to improve Meta's products, which you may want to disclose.
    - OpenRouter lists `reasoning` but not `reasoning_effort` for Gemma, so check what "(high)" means for it.
12. **Chalmers:** his terms are "quasi-beliefs" / "quasi-desires" and "quasi-agents". "Quasi-preferences" is your extension of them. The paper is now published in *Inquiry* (online 16 Sep 2026).
13. **Kant:** the Formula of Universal Law is about willing a maxim as a "universal law". "Sustainable moral rule" is a loose gloss. "Excluding nearly all animals (in his own admission)" is not supported by the cited entry.
14. **xAI's mission** ("understand the true nature of the universe") is from its July 2023 launch, reported by TIME. Its current page reads "Accelerate human scientific discovery. We build AI to understand the universe."
15. **Meinke et al.** find in-context scheming in five models, not only o1. Summerfield et al. respond to the scheming research programme broadly, citing Meinke et al. as one example.
16. **Hadfield-Menell and Hadfield:** your quote matches the 2018 arXiv preprint, which is the version cited. The published AIES 2019 wording is different.
17. **Kilov et al. and Chiu et al.** are multi-author papers (5 and 18 authors), so "by Daniel Kilov" / "by Yu Ying Chiu" could read "…et al.". Kilov et al. appeared in the IASEAI'26 proceedings. The footnote still begins with "/See".

## C. Not fully verifiable

- **Caputo:** the SSRN full text was blocked (403), so the two quotations ("it constitutes an entity, governs…", "unit of the constitutional subject") could not be checked word for word. The abstract supports the four-roles summary in different words. The full title includes the subtitle "AI Constitutionalism and the Paradox of Constituent Power".
